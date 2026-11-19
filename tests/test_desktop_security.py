"""Synthetic security controls; no real provider requests or private data."""
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from scripts.run_desktop import (NoRedirect, VerificationBudget, VerificationBusy,
                                 VerificationLimit, make_handler, request_json)
from scripts.security_check import findings


class SecurityTests(unittest.TestCase):
    def test_minute_and_launch_budgets_count_failures_and_release_slot(self):
        now = [0]
        budget = VerificationBudget(per_minute=1, per_launch=2, clock=lambda: now[0])
        with self.assertRaises(ValueError):
            with budget.reserve():
                raise ValueError('Synthetic provider failure')
        with self.assertRaises(VerificationLimit) as error:
            with budget.reserve():
                self.fail('Exhausted minute budget must block paid calls')
        self.assertGreater(error.exception.retry_after, 0)
        now[0] = 60
        with budget.reserve():
            pass
        now[0] = 120
        with self.assertRaises(VerificationLimit):
            with budget.reserve():
                self.fail('Exhausted launch budget must stay exhausted')

    def test_parallel_verification_is_blocked_without_consuming_budget(self):
        budget = VerificationBudget()
        with budget.reserve():
            with self.assertRaises(VerificationBusy):
                with budget.reserve():
                    self.fail('Parallel paid verification must be blocked')
        self.assertEqual(budget.total, 1)
        with budget.reserve():
            pass

    def test_redirects_are_refused_without_exposing_url_or_headers(self):
        credential = 'synthetic-secret'
        request = Request('http://127.0.0.1:8001/completion', headers={'Authorization': credential})
        with self.assertRaises(RuntimeError) as error:
            NoRedirect().redirect_request(request, None, 302, 'Redirect', {}, 'https://example.invalid/leak')
        self.assertNotIn(credential, str(error.exception))
        self.assertNotIn('example.invalid', str(error.exception))

    def test_guard_covers_sensitive_paths_and_empty_example(self):
        for name in ('.env.local', 'configs/desktop.local.json', 'state.sqlite3',
                     'kanglish-corrections.json', 'runtime.key', 'results/log.txt', 'data/test.csv'):
            self.assertIn('sensitive file path', findings(name, b''), name)
        self.assertEqual(findings('.env.example', b'GEMINI_API_KEY=\n'), [])
        self.assertTrue(findings('.env.example', b'GEMINI_API_KEY=synthetic\n'))
        google_key = ('AI' + 'za' + 'x' * 35).encode()
        self.assertIn('Google API credential', findings('app.js', google_key))

    def test_http_redirect_does_not_forward_sensitive_headers(self):
        calls = []
        class Redirect(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass
            def do_POST(self):
                calls.append(self.path)
                self.send_response(302)
                self.send_header('Location', f'http://127.0.0.1:{self.server.server_port}/untrusted')
                self.end_headers()
            def do_GET(self):
                calls.append(self.path)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{}')
        server = ThreadingHTTPServer(('127.0.0.1', 0), Redirect)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            with self.assertRaisesRegex(RuntimeError, 'redirect refused'):
                request_json(f'http://127.0.0.1:{server.server_port}/trusted', {},
                             {'Authorization': 'synthetic-control'}, timeout=5)
            self.assertEqual(calls, ['/trusted'])
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=5)

    def test_http_rate_limit_auth_origin_headers_and_private_static_boundary(self):
        app = SimpleNamespace(config={'port': 0}, token='synthetic-control', verify=Mock(return_value={'verdict': 'match'}))
        with patch('scripts.run_desktop.VerificationBudget', return_value=VerificationBudget(per_minute=1)):
            handler = make_handler(app)
        handler.log_message = lambda *_: None
        server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
        app.config['port'] = server.server_port
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        base = f'http://127.0.0.1:{server.server_port}'

        def send(path, body=None, **headers):
            request = Request(base + path, None if body is None else json.dumps(body).encode(),
                              {'Content-Type': 'application/json', 'X-Kanglish-Token': app.token, **headers})
            try:
                response = urlopen(request, timeout=5)
            except HTTPError as error:
                response = error
            with response:
                payload = response.read()
                return response.code, dict(response.headers), payload
        try:
            self.assertEqual(send('/api/verify', {}, **{'X-Kanglish-Token': 'wrong'})[0], 403)
            self.assertEqual(send('/api/verify', {}, Origin='https://example.invalid')[0], 403)
            self.assertEqual(send('/api/verify', {}, Host='example.invalid')[0], 403)
            self.assertEqual(send('/api/verify', {})[0], 200)
            code, headers, _ = send('/api/verify', {})
            self.assertEqual(code, 429)
            self.assertGreater(int(headers['Retry-After']), 0)
            self.assertEqual(app.verify.call_count, 1)
            code, headers, _ = send('/')
            self.assertEqual(code, 200)
            self.assertIn("frame-ancestors 'none'", headers['Content-Security-Policy'])
            self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
            for path in ('/.env', '/configs/desktop.local.json', '/.tools/state.sqlite3', '/../../.env'):
                self.assertEqual(send(path)[0], 404)
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=5)


if __name__ == '__main__':
    unittest.main()
