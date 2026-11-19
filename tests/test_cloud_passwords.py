"""Password recovery and reauthentication controls; synthetic transport, no email."""
import base64
import hashlib
from http.cookies import SimpleCookie
import json
import time
import unittest
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen
from unittest.mock import patch

import test_cloud_security as security_controls
from test_cloud_security import A, B, ENV
from scripts.cloud.api import ACCESS, CSRF, REFRESH, RECOVERY_VERIFIER, RECOVERY_SESSION, APIError, open_auth, seal_auth


class PasswordSecurityTests(unittest.TestCase):
    setUp = security_controls.HostedSecurityTests.setUp
    tearDown = security_controls.HostedSecurityTests.tearDown
    server = security_controls.HostedSecurityTests.server

    def transport(self, url, method='GET', body=None, headers=None, **kwargs):
        path = urlsplit(url).path
        if path.endswith('/web_reserve'):
            self.assertTrue(all(bucket['seconds'] in (60, 86400) for bucket in body['p_buckets']),
                            'Quota windows must match the deployed SQL function contract')
        if not hasattr(self, 'auth_calls'):
            self.auth_calls = []
        if path.startswith('/auth/v1/'):
            self.auth_calls.append((url, method, body, headers))
        if path == '/auth/v1/recover':
            return {}
        if path == '/auth/v1/token':
            grant = parse_qs(urlsplit(url).query)['grant_type'][0]
            if grant == 'pkce':
                if body['auth_code'] != 'single-use-control-code' or getattr(self, 'exchanged', False):
                    raise APIError('Invalid control code', 401)
                self.exchanged = True
            else:
                if body['password'] != 'Current-password-control':
                    raise APIError('Invalid control password', 401)
                self.assertEqual(body['email'], 'synthetic@example.invalid')
            return {'access_token': 'user-b' if getattr(self, 'wrong_owner', False) else 'user-a',
                    'refresh_token': 'synthetic-refresh', 'expires_in': 3600}
        if path == '/auth/v1/user' and method == 'PUT':
            self.updated = body['password']
            self.account_revision = '2026-11-19T01:00:00.000Z'
            return {'id': A}
        if path == '/auth/v1/user' and getattr(self, 'revoked', False):
            raise APIError('Session ended', 401)
        if path == '/auth/v1/logout':
            self.assertEqual(parse_qs(urlsplit(url).query)['scope'], ['global'])
            self.revoked = True
            return None
        if path == '/auth/v1/user':
            user = security_controls.HostedSecurityTests.transport(self, url, method, body, headers, **kwargs)
            user['updated_at'] = getattr(self, 'account_revision', '2026-11-19T00:00:00.000Z')
            return user
        return security_controls.HostedSecurityTests.transport(self, url, method, body, headers, **kwargs)

    def send(self, base, path, body=None, cookies=None, origin='https://app.example', csrf='synthetic-csrf'):
        headers = {'Cookie': cookies or f'{CSRF}=synthetic-csrf', 'Origin': origin,
                   'X-Kanglish-Token': csrf, 'Content-Type': 'application/json'}
        request = Request(base + path, None if body is None else json.dumps(body).encode(), headers)
        try:
            response = urlopen(request, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            return response.code, response.headers, json.loads(response.read())

    def response_cookies(self, headers):
        jar = SimpleCookie()
        for value in headers.get_all('Set-Cookie', []):
            jar.load(value)
        return jar

    def request_cookies(self, jar):
        return '; '.join(f'{name}={morsel.value}' for name, morsel in jar.items())

    def test_reset_email_uses_pkce_fixed_redirect_and_generic_response(self):
        with self.server() as base:
            code, headers, result = self.send(base, '/api/auth/forgot-password', {'email': 'Existing@example.invalid', 'redirect_to': 'https://evil.example'})
            self.assertEqual(code, 200)
            url, _, body, _ = self.auth_calls[-1]
            self.assertEqual(parse_qs(urlsplit(url).query)['redirect_to'], ['https://app.example/?auth=recovery'])
            self.assertEqual(body['email'], 'existing@example.invalid')
            verifier = open_auth(self.response_cookies(headers)[RECOVERY_VERIFIER].value, 'verifier', ENV['SUPABASE_SERVICE_ROLE_KEY'], 3600)
            expected = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
            self.assertEqual(body['code_challenge'], expected)
            self.assertEqual(body['code_challenge_method'], 's256')
            self.assertNotIn(verifier, json.dumps(result))
            missing = self.send(base, '/api/auth/forgot-password', {'email': 'missing@example.invalid'})
            self.assertEqual(missing[2], result)
            for flag in ('Secure', 'HttpOnly', 'SameSite=Lax', 'Path=/'):
                self.assertIn(flag, self.response_cookies(headers)[RECOVERY_VERIFIER].OutputString())

    def test_mail_is_not_sent_without_csrf_origin_valid_email_or_quota(self):
        with self.server() as base:
            path, body = '/api/auth/forgot-password', {'email': 'control@example.invalid'}
            self.assertEqual(self.send(base, path, body, origin='https://evil.example')[0], 403)
            self.assertEqual(self.send(base, path, body, csrf='wrong')[0], 403)
            self.assertEqual(self.send(base, path, {'email': 'invalid'})[0], 400)
            self.denied = True
            self.assertEqual(self.send(base, path, body)[0], 429)
            self.denied, self.failed = False, True
            self.assertEqual(self.send(base, path, body)[0], 503)
            self.assertFalse(any('/auth/v1/recover' in call[0] for call in getattr(self, 'auth_calls', [])))

    def test_reset_requires_signed_recovery_proof_not_normal_login(self):
        with self.server() as base:
            normal = f'{ACCESS}=user-a; {CSRF}=synthetic-csrf'
            forged = normal + f'; {RECOVERY_SESSION}=user-a'
            for cookies in (normal, forged):
                self.assertEqual(self.send(base, '/api/auth/reset-password', {'password': 'New-password-control'}, cookies)[0], 400)
            self.assertFalse(hasattr(self, 'updated'))

    def test_recovery_requires_matching_browser_and_one_time_exchange(self):
        with self.server() as base:
            self.assertEqual(self.send(base, '/api/auth/recovery', {'code': 'single-use-control-code'})[0], 400)
            _, headers, _ = self.send(base, '/api/auth/forgot-password', {'email': 'control@example.invalid'})
            jar = self.response_cookies(headers)
            jar.load(f'{CSRF}=synthetic-csrf')
            cookies = self.request_cookies(jar)
            self.assertEqual(self.send(base, '/api/auth/recovery', {'code': 'wrong-code'}, cookies)[0], 400)
            code, headers, result = self.send(base, '/api/auth/recovery', {'code': 'single-use-control-code'}, cookies)
            self.assertEqual(code, 200)
            self.assertTrue(result['recovery_ready'])
            self.assertNotIn('user-a', json.dumps(result))
            self.assertEqual(self.send(base, '/api/auth/recovery', {'code': 'single-use-control-code'}, cookies)[0], 400)
            self.assertIn(RECOVERY_SESSION, self.response_cookies(headers))

    def test_verified_recovery_updates_password_revokes_sessions_and_clears_cookies(self):
        with self.server() as base:
            record = json.dumps({'access': 'user-a', 'updated_at': '2026-11-19T00:00:00.000Z'})
            proof = seal_auth(record, 'recovery', ENV['SUPABASE_SERVICE_ROLE_KEY'])
            cookies = f'{RECOVERY_SESSION}={proof}; {CSRF}=synthetic-csrf'
            session = self.send(base, '/api/auth/session', cookies=cookies)[2]
            self.assertTrue(session['recovery_ready'])
            self.assertFalse(session['authenticated'])
            code, headers, result = self.send(base, '/api/auth/reset-password', {'password': 'New-password-control'}, cookies)
            self.assertEqual(code, 200)
            self.assertTrue(result['password_changed'])
            self.assertEqual(self.updated, 'New-password-control')
            self.assertTrue(self.revoked)
            cleared = self.response_cookies(headers)
            for name in (ACCESS, REFRESH, CSRF, RECOVERY_SESSION, RECOVERY_VERIFIER):
                self.assertEqual(cleared[name]['max-age'], '0')
            self.assertEqual(self.send(base, '/api/auth/reset-password', {'password': 'Other-password-control'}, cookies)[0], 401)
            # Supabase JWTs can survive refresh-session revocation until expiry.
            # Account revision binding must still reject reused recovery proof.
            self.revoked = False
            self.assertEqual(self.send(base, '/api/auth/reset-password', {'password': 'Other-password-control'}, cookies)[0], 400)
            self.assertEqual(self.updated, 'New-password-control')

    def test_password_change_requires_current_password_and_same_owner(self):
        with self.server() as base:
            cookies = f'{ACCESS}=user-a; {CSRF}=synthetic-csrf'
            path = '/api/auth/change-password'
            body = {'password': 'New-password-control', 'current_password': 'Wrong-password-control', 'email': 'another@example.invalid', 'user_id': B}
            self.assertEqual(self.send(base, path, body, cookies)[0], 400)
            self.assertFalse(hasattr(self, 'updated'))
            body['current_password'] = 'Current-password-control'
            self.wrong_owner = True
            self.assertEqual(self.send(base, path, body, cookies)[0], 403)
            self.assertFalse(hasattr(self, 'updated'))
            self.wrong_owner = False
            self.assertEqual(self.send(base, path, body, cookies)[0], 200)
            self.assertTrue(self.revoked)

    def test_password_change_quota_and_password_policy_prevent_update(self):
        with self.server() as base:
            cookies = f'{ACCESS}=user-a; {CSRF}=synthetic-csrf'
            for password in ('short', 'x' * 1025, None):
                self.assertEqual(self.send(base, '/api/auth/change-password', {'password': password}, cookies)[0], 400)
            self.denied = True
            body = {'password': 'New-password-control', 'current_password': 'Current-password-control'}
            self.assertEqual(self.send(base, '/api/auth/change-password', body, cookies)[0], 429)
            self.assertFalse(hasattr(self, 'updated'))

    def test_signed_proof_cannot_be_tampered_repurposed_or_reused_after_expiry(self):
        secret = ENV['SUPABASE_SERVICE_ROLE_KEY']
        proof = seal_auth('synthetic-control', 'verifier', secret)
        for value, purpose in ((proof + 'x', 'verifier'), (proof, 'recovery')):
            with self.assertRaises(APIError):
                open_auth(value, purpose, secret, 3600)
        with patch('scripts.cloud.api.time.time', return_value=time.time() + 3601):
            with self.assertRaises(APIError):
                open_auth(proof, 'verifier', secret, 3600)


if __name__ == '__main__':
    unittest.main()
