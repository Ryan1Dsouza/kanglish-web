"""Apply the Supabase migration over verified TLS using the Python standard library."""
import argparse
import base64
import hashlib
import hmac
import json
from pathlib import Path
import secrets
import socket
import ssl
import struct
from urllib.parse import unquote, urlsplit
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CA_URL = 'https://supabase-downloads.s3-ap-southeast-1.amazonaws.com/prod/ssl/prod-ca-2021.crt'
CA_SHA256 = '700723581420dd1ac98fd7e9ac529f0ef210eadcaf87fc868a3ad7d114c2f3b7'

def read_env(path):
    values = {}
    for line in Path(path).read_text(encoding='utf-8-sig').splitlines():
        if not line.strip() or line.lstrip().startswith('#') or '=' not in line:
            continue
        name, value = line.split('=', 1)
        value = value.strip()
        values[name.strip()] = json.loads(value) if value.startswith('"') else value.strip("'")
    return values

class Postgres:
    def __init__(self, url):
        parsed = urlsplit(url)
        if parsed.scheme not in ('postgres', 'postgresql') or not parsed.hostname or not parsed.username or not parsed.password:
            raise RuntimeError('A PostgreSQL connection is required')
        if not parsed.hostname.endswith(('.pooler.supabase.com', '.supabase.co')):
            raise RuntimeError('This migration utility targets Supabase only')
        self.socket = socket.create_connection((parsed.hostname, parsed.port or 5432), timeout=30)
        self.socket.sendall(struct.pack('!II', 8, 80877103))
        if self.receive(1) != b'S':
            raise RuntimeError('Database TLS is required')
        certificate = urllib.request.urlopen(CA_URL, timeout=30).read(100000)
        if hashlib.sha256(certificate).hexdigest() != CA_SHA256:
            raise RuntimeError('Supabase CA certificate changed; review it before updating the checksum')
        context = ssl.create_default_context()
        context.load_verify_locations(cadata=certificate.decode())
        self.socket = context.wrap_socket(self.socket, server_hostname=parsed.hostname)
        username, password = unquote(parsed.username), unquote(parsed.password)
        database = unquote(parsed.path.lstrip('/')) or 'postgres'
        payload = b'user\0' + username.encode() + b'\0database\0' + database.encode() + b'\0application_name\0kanglish-schema\0\0'
        self.socket.sendall(struct.pack('!II', len(payload) + 8, 196608) + payload)
        nonce = bare = expected = None
        while True:
            kind, data = self.message()
            if kind == b'R':
                code = struct.unpack('!I', data[:4])[0]
                if code == 0:
                    continue
                if code == 3:
                    self.send(b'p', password.encode() + b'\0')
                elif code == 5:
                    inner = hashlib.md5((password + username).encode()).hexdigest().encode()
                    self.send(b'p', b'md5' + hashlib.md5(inner + data[4:8]).hexdigest().encode() + b'\0')
                elif code == 10:
                    if b'SCRAM-SHA-256\0' not in data[4:]:
                        raise RuntimeError('Unsupported database authentication')
                    nonce = secrets.token_urlsafe(24)
                    bare = 'n=' + username.replace('=', '=3D').replace(',', '=2C') + ',r=' + nonce
                    first = ('n,,' + bare).encode()
                    self.send(b'p', b'SCRAM-SHA-256\0' + struct.pack('!I', len(first)) + first)
                elif code == 11:
                    challenge = data[4:].decode()
                    attrs = dict(piece.split('=', 1) for piece in challenge.split(','))
                    iterations = int(attrs['i'])
                    if not attrs['r'].startswith(nonce) or not 4096 <= iterations <= 1000000:
                        raise RuntimeError('Invalid database authentication challenge')
                    final = 'c=biws,r=' + attrs['r']
                    auth = (bare + ',' + challenge + ',' + final).encode()
                    salted = hashlib.pbkdf2_hmac('sha256', password.encode(), base64.b64decode(attrs['s']), iterations)
                    client_key = hmac.new(salted, b'Client Key', hashlib.sha256).digest()
                    signature = hmac.new(hashlib.sha256(client_key).digest(), auth, hashlib.sha256).digest()
                    proof = base64.b64encode(bytes(a ^ b for a, b in zip(client_key, signature))).decode()
                    server_key = hmac.new(salted, b'Server Key', hashlib.sha256).digest()
                    expected = base64.b64encode(hmac.new(server_key, auth, hashlib.sha256).digest()).decode()
                    self.send(b'p', (final + ',p=' + proof).encode())
                elif code == 12:
                    attrs = dict(piece.split('=', 1) for piece in data[4:].decode().split(','))
                    if not expected or not hmac.compare_digest(attrs.get('v', ''), expected):
                        raise RuntimeError('Database authentication proof failed')
                else:
                    raise RuntimeError('Unsupported database authentication')
            elif kind == b'E':
                raise self.error(data)
            elif kind == b'Z':
                break

    def receive(self, size):
        result = bytearray()
        while len(result) < size:
            block = self.socket.recv(size - len(result))
            if not block:
                raise RuntimeError('Database connection closed')
            result.extend(block)
        return bytes(result)

    def message(self):
        kind = self.receive(1)
        size = struct.unpack('!I', self.receive(4))[0]
        if not 4 <= size <= 10000000:
            raise RuntimeError('Invalid database response size')
        return kind, self.receive(size - 4)

    def send(self, kind, data):
        self.socket.sendall(kind + struct.pack('!I', len(data) + 4) + data)

    def error(self, data):
        fields = {part[:1].decode(): part[1:].decode(errors='replace') for part in data.split(b'\0') if part}
        return RuntimeError('Database operation failed (' + fields.get('C', 'unknown') + '): ' + fields.get('M', 'Unknown error'))

    def query(self, sql):
        self.send(b'Q', sql.encode() + b'\0')
        rows, error = [], None
        while True:
            kind, data = self.message()
            if kind == b'D':
                count, offset, row = struct.unpack('!H', data[:2])[0], 2, []
                for _ in range(count):
                    size = struct.unpack('!i', data[offset:offset + 4])[0]
                    offset += 4
                    row.append(None if size == -1 else data[offset:offset + size].decode())
                    if size != -1:
                        offset += size
                rows.append(row)
            elif kind == b'E':
                error = self.error(data)
            elif kind == b'Z':
                if error:
                    raise error
                return rows

    def close(self):
        self.send(b'X', b'')
        self.socket.close()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path, default=ROOT / '.env.cloud.local')
    args = parser.parse_args()
    connection = Postgres(read_env(args.env_file)['POSTGRES_URL'])
    try:
        migration = '\n'.join(path.read_text(encoding='utf-8') for path in sorted((ROOT / 'supabase/migrations').glob('*.sql')))
        connection.query('BEGIN;\n' + migration + '\nCOMMIT;')
        print('Applied private storage policies and shared quota functions.')
    finally:
        connection.close()

if __name__ == '__main__':
    main()
