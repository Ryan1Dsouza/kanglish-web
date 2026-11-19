"""Synthetic hosted API controls; no network, real credentials or paid models."""
from contextlib import contextmanager
from http.server import ThreadingHTTPServer
import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen
from unittest.mock import patch

from scripts.cloud.api import ACCESS, CSRF, APIError, CloudHandler, Config, Service, cookie, safe_endpoint
from scripts.cloud.storage import MemoryStore
from scripts.run_desktop import parse_sentence_batch

A = '11111111-1111-4111-8111-111111111111'
B = '22222222-2222-4222-8222-222222222222'
ENV = {'SUPABASE_URL': 'https://synthetic.supabase.co', 'SUPABASE_ANON_KEY': 'synthetic-anon',
       'SUPABASE_SERVICE_ROLE_KEY': 'synthetic-service', 'APP_ORIGIN': 'https://app.example',
       'TRANSLATION_PROVIDER': 'gemini', 'GEMINI_API_KEY': 'synthetic-provider'}

class HostedSecurityTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict('os.environ', ENV, clear=True)
        self.env.start()
        self.data = {A: {'corrections': [], 'links': []}, B: {'corrections': [], 'links': []}}
        self.runs = {A: {}, B: {'b' * 32: {'id': 'b' * 32, 'input': 'private-control', 'dialect': 'kanglish'}}}
        self.denied = False
        self.failed = False
        self.calls = []
        self.provider_calls = 0

    def tearDown(self):
        self.env.stop()

    def transport(self, url, method='GET', body=None, headers=None, **kwargs):
        path = urlsplit(url).path
        self.calls.append((path, body, headers))
        authorization = headers.get('Authorization', '')
        owner = A if authorization == 'Bearer user-a' else B if authorization == 'Bearer user-b' else None
        if path == '/auth/v1/user':
            if not owner:
                raise APIError('Sign in to continue.', 401)
            return {'id': owner, 'email': 'synthetic@example.invalid'}
        if path.endswith('/web_reserve'):
            if self.failed:
                raise APIError('Quota storage unavailable.', 503)
            return {'allowed': not self.denied, 'retry_after': 30, 'lease': None}
        if path.endswith('/web_release'):
            return None
        if path.endswith('/web_dictionaries'):
            query = parse_qs(urlsplit(url).query)
            self.assertEqual(query['user_id'], ['eq.' + owner])
            return [{'payload': self.data[owner], 'version': 1}]
        if path.endswith('/web_runs'):
            query = parse_qs(urlsplit(url).query)
            self.assertEqual(query['user_id'], ['eq.' + owner])
            requested = query.get('id', [''])[0].removeprefix('eq.')
            return [{'payload': row} for id_, row in self.runs[owner].items() if not requested or requested == id_]
        if path.endswith('/web_commit_dictionary'):
            self.data[owner] = body['p_payload']
            return {'conflict': False}
        if path.endswith('/web_put_run'):
            self.runs[owner][body['p_payload']['id']] = body['p_payload']
            return None
        if 'generativelanguage.googleapis.com' in url:
            self.provider_calls += 1
            return {'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': 'Synthetic English control.'}]}}]}
        self.fail('Unexpected synthetic request: ' + path)

    @contextmanager
    def server(self):
        with patch('scripts.cloud.api.remote', side_effect=self.transport):
            server = ThreadingHTTPServer(('127.0.0.1', 0), CloudHandler)
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                yield f'http://127.0.0.1:{server.server_port}'
            finally:
                server.shutdown()
                server.server_close()
                worker.join(timeout=5)

    def send(self, base, path, body=None, user='user-a', origin='https://app.example', token='synthetic-csrf', **extra):
        headers = {'Cookie': f'{ACCESS}={user}; {CSRF}=synthetic-csrf', 'Origin': origin,
                   'X-Kanglish-Token': token, 'Content-Type': 'application/json', **extra}
        request = Request(base + path, None if body is None else json.dumps(body).encode(), headers)
        try:
            response = urlopen(request, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            raw = response.read()
            return response.code, dict(response.headers), json.loads(raw) if 'application/json' in response.headers.get('Content-Type', '') else raw

    def test_auth_csrf_origin_and_quota_fail_before_provider_calls(self):
        with self.server() as base:
            self.assertEqual(self.send(base, '/api/translate', {'text': 'synthetic'}, user='forged')[0], 401)
            self.assertEqual(self.send(base, '/api/translate', {'text': 'synthetic'}, origin='https://evil.example')[0], 403)
            self.assertEqual(self.send(base, '/api/translate', {'text': 'synthetic'}, token='wrong')[0], 403)
            self.denied = True
            code, headers, _ = self.send(base, '/api/translate', {'text': 'synthetic'})
            self.assertEqual(code, 429)
            self.assertEqual(headers['Retry-After'], '30')
            self.denied, self.failed = False, True
            self.assertEqual(self.send(base, '/api/translate', {'text': 'synthetic'})[0], 503)
            self.assertEqual(self.provider_calls, 0)

    def test_ownership_filters_ignore_client_user_id_and_private_run_ids(self):
        with self.server() as base:
            self.assertEqual(self.send(base, '/api/dictionary/save', {'original': 'control', 'english': 'meaning', 'user_id': B})[0], 200)
            rows = self.send(base, '/api/dictionary')[2]
            self.assertEqual([r['original'] for r in rows], ['control'])
            self.assertEqual(self.send(base, '/api/dictionary', user='user-b')[2], [])
            self.assertEqual(self.send(base, '/api/verify', {'id': 'b' * 32, 'user_id': B})[0], 404)
            self.assertEqual(self.provider_calls, 0)

    def test_automated_batches_and_oversized_inputs_are_rejected(self):
        with self.server() as base:
            self.assertEqual(self.send(base, '/api/translate', {'text': 'control', 'batch': True})[0], 400)
            self.assertEqual(self.send(base, '/api/translate', {'text': 'x' * 1001})[0], 400)
            self.assertEqual(self.send(base, '/api/translate', {'text': 'control', 'context': 'x' * 501})[0], 400)
            self.assertEqual(self.provider_calls, 0)

    def test_cookie_flags_and_no_access_credentials_in_bootstrap(self):
        value = cookie(ACCESS, 'synthetic-access')
        for flag in ('Secure', 'HttpOnly', 'SameSite=Lax', 'Path=/'):
            self.assertIn(flag, value)
        self.assertNotIn('Domain=', value)
        with self.server() as base:
            code, _, result = self.send(base, '/api/auth/session')
            self.assertEqual(code, 200)
            self.assertTrue(result['authenticated'])
            self.assertNotIn('access_token', result)
            self.assertNotIn('refresh_token', result)

    def test_snapshot_roundtrip_keeps_review_labels_and_contextual_meanings(self):
        store = MemoryStore()
        try:
            parsed = parse_sentence_batch('Kanglish: control word\nEnglish: Synthetic sentence.\nWord Mapping: control -> test')
            store.import_sentence_batch(parsed, source_label='synthetic_control')
            snapshot = store.snapshot()
        finally:
            store.close()
        reopened = MemoryStore(snapshot)
        try:
            self.assertEqual(reopened.export()[0]['source_label'], 'synthetic_control')
            self.assertEqual(reopened.glossary_for('control word')[0]['english'], 'test')
            old = next(row for row in reopened.corrections() if row['kind'] == 'glossary')
            reopened.db.execute("UPDATE corrections SET review_status='human_reviewed' WHERE key=?", (old['key'],))
            reopened.save(old['original'], 'Updated control.', 'web_user_dictionary', kind='glossary')
            new = next(row for row in reopened.corrections() if row['key'] == old['key'])
            self.assertEqual((new['source_label'], new['review_status']), ('synthetic_control', 'human_reviewed'))
        finally:
            reopened.close()

    def test_retry_on_dictionary_version_conflict_preserves_new_snapshot(self):
        service = Service(Config())
        snapshots = [{'payload': None, 'version': 0}, {'payload': {'corrections': [], 'links': []}, 'version': 1}]
        with patch.object(service, 'dictionary', side_effect=snapshots), patch.object(service, 'supabase', side_effect=[{'conflict': True}, {'conflict': False}]) as rpc:
            result = service.mutate({'id': A}, 'user-a', 'kanglish', lambda store: (store.save('control', 'test', 'synthetic'), {'saved': True})[1])
        self.assertTrue(result['saved'])
        self.assertEqual(rpc.call_args_list[-1].args[2]['p_version'], 1)

    def test_public_endpoint_validation_and_csv_formula_escape(self):
        for value in ('http://example.com', 'https://127.0.0.1', 'https://localhost', 'https://u:p@example.com', 'https://example.com?secret=x'):
            with self.assertRaises(APIError):
                safe_endpoint(value)
        self.runs[A]['a' * 32] = {'id': 'a' * 32, 'input': '=1+1', 'translation': 'Synthetic control.'}
        with self.server() as base:
            code, _, csv_data = self.send(base, '/api/log.csv')
            self.assertEqual(code, 200)
            self.assertIn(b"'=1+1", csv_data)

    def test_vercel_rewrite_and_bounded_public_import(self):
        with self.server() as base:
            self.assertEqual(self.send(base, '/api/index?__route=status')[0], 200)
            paste = '\n'.join(f'Kanglish: control{i}\nEnglish: Test.' for i in range(21))
            self.assertEqual(self.send(base, '/api/dictionary/bulk-import', {'text': paste})[0], 400)

if __name__ == '__main__':
    unittest.main()
