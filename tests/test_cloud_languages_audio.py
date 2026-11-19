"""Labelled synthetic controls for hosted directions/audio; no paid calls."""
import base64
import json
import unittest
from urllib.parse import parse_qs, urlsplit

from scripts.cloud.api import APIError
from scripts.cloud.languages import DEFAULTS, LANGUAGES, check_script
import test_cloud_security as security

A, B = security.A, security.B


class HostedLanguageAudioTests(unittest.TestCase):
    setUp = security.HostedSecurityTests.setUp
    tearDown = security.HostedSecurityTests.tearDown
    server = security.HostedSecurityTests.server
    send = security.HostedSecurityTests.send

    def transport(self, url, method='GET', body=None, headers=None, **kwargs):
        path = urlsplit(url).path
        owner = {'Bearer user-a': A, 'Bearer user-b': B}.get(headers.get('Authorization', ''))
        if path.endswith('/web_dictionaries'):
            self.calls.append((path, body, headers))
            query = parse_qs(urlsplit(url).query)
            self.assertEqual(query['user_id'], ['eq.' + owner])
            dictionaries = self.data[owner].get('dictionaries', {})
            if 'dialect' not in query:
                return [{'dialect': name, 'dictionary': saved['payload'].get('dictionary')} for name, saved in dictionaries.items()]
            name = query['dialect'][0].removeprefix('eq.')
            return [dictionaries[name]] if name in dictionaries else []
        if path.endswith('/web_commit_dictionary'):
            self.calls.append((path, body, headers))
            dictionaries = self.data[owner].setdefault('dictionaries', {})
            old = dictionaries.get(body['p_dialect'], {'version': 0})
            if old['version'] != body['p_version']:
                return {'conflict': True}
            dictionaries[body['p_dialect']] = {'payload': body['p_payload'], 'version': old['version'] + 1}
            return {'conflict': False}
        if path.endswith('/web_dictionary_counts'):
            return {name: len(saved['payload']['corrections']) for name, saved in self.data[owner].get('dictionaries', {}).items()}
        if path.endswith('/web_delete_dictionary'):
            dictionaries = self.data[owner].get('dictionaries', {})
            if dictionaries.get(body['p_dialect'], {'version': 0})['version'] != body['p_version']:
                return {'conflict': True}
            dictionaries.pop(body['p_dialect'], None)
            return {'conflict': False}
        if 'generativelanguage.googleapis.com' in url:
            self.provider_calls += 1
            self.calls.append((path, body, headers))
            prompt = body['systemInstruction']['parts'][0]['text']
            target = next(code for code in LANGUAGES if '(' + code + ').' in prompt)
            output = 'ನೀರು' if target.endswith('Knda') else 'Synthetic control.'
            if 'inline_data' in body['contents'][0]['parts'][-1]:
                source = next(code for code in LANGUAGES if '(' + code + ') to' in prompt)
                output = json.dumps(getattr(self, 'audio_result', {
                    'transcript': 'ನೀರು' if source.endswith('Knda') else 'Synthetic speech.',
                    'translation': output, 'confident': True}))
            return {'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': output}]}}]}
        return security.HostedSecurityTests.transport(self, url, method, body, headers, **kwargs)

    def audio(self, **values):
        return {'audio': base64.b64encode(b'synthetic-audio-control' * 10).decode(), 'mime_type': 'audio/webm;codecs=opus', **values}

    def test_all_twenty_directions_and_scripts(self):
        self.assertEqual(len(DEFAULTS), 20)
        with self.server() as base:
            for name, pair in DEFAULTS.items():
                with self.subTest(name=name):
                    code, _, row = self.send(base, '/api/translate', {'text': 'Synthetic source.', **pair, 'dialect': name})
                    self.assertEqual(code, 200, row)
                    self.assertEqual(row['source_language'], pair['source_language'])
                    self.assertEqual(row['target_language'], pair['target_language'])
                    check_script(row['translation'], pair['target_language'])
            self.assertEqual(self.provider_calls, 20)
            self.assertEqual(self.send(base, '/api/translate', {'text': 'Control.', 'dialect': 'english-tulu', 'target_language': 'en'})[0], 400)
            self.assertEqual(self.provider_calls, 20)
        for code, text in [('kn-Knda', 'Latin only'), ('tcy-Knda', 'Latin only'), ('kn-Latn', 'ನೀರು'), ('tcy-Latn', 'ನೀರು')]:
            with self.assertRaises(ValueError):
                check_script(text, code)

    def test_empty_custom_dictionary_persists_direction_owner_and_exports(self):
        pair = {'name': 'synthetic-travel', 'label': 'Synthetic travel', 'source_language': 'en', 'target_language': 'tcy-Knda'}
        with self.server() as base:
            self.assertEqual(self.send(base, '/api/dictionaries/create', pair, token='wrong')[0], 403)
            code, _, created = self.send(base, '/api/dictionaries/create', {**pair, 'user_id': B})
            self.assertEqual((code, created['count']), (200, 0))
            catalog = self.send(base, '/api/dictionaries/details')[2]
            self.assertIn(pair, [{k: row[k] for k in pair} for row in catalog])
            self.assertNotIn(pair['name'], [row['name'] for row in self.send(base, '/api/dictionaries/details', user='user-b')[2]])
            self.assertEqual(self.send(base, '/api/dictionaries/create', {**pair, 'target_language': 'kn-Latn'})[0], 400)
            self.assertEqual(self.send(base, '/api/dictionary/save', {'dialect': pair['name'], 'original': 'water', 'english': 'ನೀರ್'})[0], 200)
            exported = self.send(base, '/api/corrections.json?dialect=' + pair['name'])[2][0]
            self.assertEqual((exported['source_language'], exported['target_language'], exported['dictionary']), ('en', 'tcy-Knda', pair['name']))
            self.assertEqual(exported['source_label'], 'user_input_unreviewed')
            self.assertEqual(self.send(base, '/api/dictionaries/create', {**pair, 'source_language': 'bogus'})[0], 400)
            self.assertEqual(self.send(base, '/api/dictionaries/create', {**pair, 'target_language': 'en'})[0], 400)

    def test_reverse_imports_and_kannada_word_mappings(self):
        with self.server() as base:
            code, _, result = self.send(base, '/api/dictionary/bulk-import', {'dialect': 'english-kanglish', 'text': 'English: water\nKanglish: neeru'})
            self.assertEqual((code, result['sentences']), (200, 1))
            row = self.send(base, '/api/dictionary?dialect=english-kanglish')[2][0]
            self.assertEqual((row['original'], row['english']), ('water', 'neeru'))
            code, _, result = self.send(base, '/api/dictionary/bulk-import', {'dialect': 'kannada', 'text': 'Kannada: ನನಗೆ ನೀರು ಬೇಕು\nEnglish: I want water.\nWord Mapping: ನೀರು -> water'})
            self.assertEqual((code, result['word_meanings']), (200, 1))
            self.assertEqual(self.provider_calls, 0)

    def test_deleted_dictionary_is_not_stored_in_reloaded_catalog(self):
        with self.server() as base:
            self.assertFalse(any(row['stored'] for row in self.send(base, '/api/dictionaries/details')[2]))
            for name in ('kanglish', 'synthetic-custom'):
                pair = {'name': name, 'source_language': 'kn-Latn', 'target_language': 'en'}
                self.assertEqual(self.send(base, '/api/dictionaries/create', pair)[0], 200)
                self.assertEqual(self.send(base, '/api/dictionaries/create', pair, user='user-b')[0], 200)
                self.assertTrue(next(row for row in self.send(base, '/api/dictionaries/details')[2] if row['name'] == name)['stored'])
                info = self.send(base, '/api/dictionary/info?dialect=' + name)[2]
                self.assertEqual(self.send(base, '/api/dictionaries/delete', {'dialect': name, 'confirm_name': name, 'version': info['version']})[0], 200)
                catalog = {row['name']: row for row in self.send(base, '/api/dictionaries/details')[2]}
                if name == 'kanglish':
                    self.assertFalse(catalog[name]['stored'])
                else:
                    self.assertNotIn(name, catalog)
                self.assertTrue(next(row for row in self.send(base, '/api/dictionaries/details', user='user-b')[2] if row['name'] == name)['stored'])
            self.assertEqual(self.provider_calls, 0)

    def test_audio_auth_origin_csrf_and_quotas_block_provider(self):
        with self.server() as base:
            for extra, expected in [({'user': 'forged'}, 401), ({'origin': 'https://evil.example'}, 403), ({'token': 'wrong'}, 403)]:
                self.assertEqual(self.send(base, '/api/audio/translate', self.audio(), **extra)[0], expected)
            self.denied = True
            self.assertEqual(self.send(base, '/api/audio/translate', self.audio())[0], 429)
            self.denied, self.failed = False, True
            self.assertEqual(self.send(base, '/api/audio/translate', self.audio())[0], 503)
            self.assertEqual(self.provider_calls, 0)

    def test_audio_payload_validation_and_uncertain_results(self):
        with self.server() as base:
            for changes in [{'mime_type': 'video/mp4'}, {'audio': '!!'}, {'audio': base64.b64encode(b'x').decode()}, {'audio': base64.b64encode(b'x' * 1000001).decode()}]:
                self.assertEqual(self.send(base, '/api/audio/translate', self.audio(**changes))[0], 400)
            self.assertEqual(self.send(base, '/api/audio/translate', {}, header_only=True, **{'Content-Length': '1500001'})[0], 413)
            self.assertEqual(self.provider_calls, 0)
            for result in [{'confident': False, 'transcript': '', 'translation': ''}, {'confident': True, 'transcript': '', 'translation': 'Invented'}, {'confident': True, 'transcript': 'Synthetic', 'translation': '[Unknown/Untranslatable]'}]:
                self.audio_result = result
                self.assertEqual(self.send(base, '/api/audio/translate', self.audio())[0], 400)
            self.assertEqual(self.runs[A], {})

    def test_audio_history_private_not_automatic_dictionary_save(self):
        with self.server() as base:
            code, _, row = self.send(base, '/api/audio/translate', self.audio(dialect='english-tulu', source_language='en', target_language='tcy-Knda'))
            self.assertEqual(code, 200, row)
            self.assertEqual(row['source_label'], 'user_audio_unreviewed')
            self.assertEqual(row['target_language'], 'tcy-Knda')
            self.assertEqual(self.runs[A][row['id']], row)
            self.assertEqual(self.data[A].get('dictionaries', {}), {})
            self.assertEqual(self.send(base, '/api/glossary/' + row['id'], user='user-b')[0], 404)
            reserve = next(body for path, body, _ in self.calls if path.endswith('/web_reserve') and body['p_inference'])
            self.assertEqual([(bucket['seconds'], bucket['limit']) for bucket in reserve['p_buckets'] if bucket['key'] == 'user:' + A + ':audio'], [(60, 5), (86400, 20)])
            self.assertIn({'key': 'inference:global', 'seconds': 86400, 'limit': 200}, reserve['p_buckets'])
