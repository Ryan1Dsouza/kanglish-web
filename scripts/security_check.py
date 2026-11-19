"""Reject sensitive tracked/staged files and recognizable credentials, without printing values."""
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SENSITIVE = re.compile(r"(?:^|/)(?:\.env(?:\..*)?|\.tools|\.vercel|results|node_modules)(?:/|$)|"
                       r"(?:\.local\.json|\.env|\.sqlite[^/]*|\.db|\.gguf|\.safetensors|\.key|\.pem|\.p12|\.pfx|\.jks|\.keystore|\.log|\.csv|\.jsonl|\.exe|\.dll)$|"
                       r"(?:corrections|credentials|service-account).*\.json$", re.I)
PATTERNS = {
    'Google API credential': re.compile(rb'AIza[0-9A-Za-z_-]{35}'),
    'GitHub credential': re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})'),
    'OpenAI credential': re.compile(rb'sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{32,}'),
    'AWS access identifier': re.compile(rb'(?:AKIA|ASIA)[A-Z0-9]{16}'),
    'private key': re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----'),
}

def findings(name, payload):
    found = []
    if name != '.env.example' and SENSITIVE.search(name):
        found.append('sensitive file path')
    if name.startswith('tmp/') and name != 'tmp/.gitkeep':
        found.append('local scratch file')
    for label, pattern in PATTERNS.items():
        if pattern.search(payload):
            found.append(label)
    if name == '.env.example':
        for line in payload.decode('utf-8').splitlines():
            if line.strip() and not line.lstrip().startswith('#') and '=' in line and line.split('=', 1)[1].strip():
                found.append('nonempty example environment value')
    return found

def main():
    result = subprocess.run(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
                            cwd=ROOT, capture_output=True, check=True)
    names = sorted(set(result.stdout.decode('utf-8').split('\0')) - {''})
    failures = []
    for name in names:
        path = ROOT / name
        if path.is_symlink() or not path.resolve().is_relative_to(ROOT):
            failures.append((name, 'symlink or path outside repository'))
            continue
        if path.is_file():
            failures.extend((name, label) for label in findings(name, path.read_bytes()))
        # Also inspect the staged payload, which can differ from the working copy.
        staged = subprocess.run(['git', 'show', ':' + name], cwd=ROOT, capture_output=True)
        if staged.returncode == 0:
            failures.extend((name, label) for label in findings(name, staged.stdout))
    for name, label in sorted(set(failures)):
        print(f'REJECTED {name}: {label}')
    if failures:
        return 1
    print(f'Security guard passed for {len(names)} repository files (working copy and index).')
    return 0

if __name__ == '__main__':
    sys.exit(main())
