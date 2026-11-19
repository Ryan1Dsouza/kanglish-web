"""Durable Supabase snapshots; SQLite is used only in memory for existing import semantics."""
from contextlib import contextmanager
import json
import sqlite3

from scripts.run_desktop import App, Store
from scripts.cloud.languages import direction

class MemoryStore(Store):
    def __init__(self, payload=None, run=None):
        self.db = sqlite3.connect(':memory:')
        super().__init__(':memory:')
        payload = payload or {'corrections': [], 'links': []}
        self.metadata = payload.get('dictionary')
        for table, rows in (('corrections', payload['corrections']), ('glossary_links', payload['links'])):
            for row in rows:
                columns = list(row)
                allowed = {r[1] for r in self.db.execute(f'PRAGMA table_info({table})')}
                if not set(columns) <= allowed:
                    raise ValueError('Invalid dictionary snapshot')
                self.db.execute(f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})", list(row.values()))
        self.db.commit()
        if run:
            self.put_run(run)

    @contextmanager
    def connect(self):
        with self.db:
            yield self.db

    def close(self):
        self.db.close()

    def snapshot(self):
        result = {}
        for table, field in (('corrections', 'corrections'), ('glossary_links', 'links')):
            cursor = self.db.execute(f'SELECT * FROM {table}')
            columns = [column[0] for column in cursor.description]
            result[field] = [dict(zip(columns, row)) for row in cursor.fetchall()]
        if self.metadata:
            result['dictionary'] = self.metadata
        if len(result['corrections']) > 5000 or len(result['links']) > 10000 or len(json.dumps(result).encode()) > 2097152:
            raise ValueError('Your dictionary has reached its storage limit. Export and remove older entries first.')
        return result

    def set_direction(self, name, source, target, label):
        candidate = {'name': name, 'label': label, 'source_language': source, 'target_language': target}
        validated = direction(name, candidate)
        if self.metadata and any(validated[k] != self.metadata[k] for k in ('source_language', 'target_language')):
            raise ValueError('This dictionary already has a different translation direction.')
        if self.corrections(name):
            direction(name, self.metadata, candidate)
        self.metadata = validated
        return {**validated, 'count': len(self.corrections(name))}

    def export(self, dialect='kanglish'):
        result = super().export(dialect)
        pair = direction(dialect, self.metadata)
        for row in result:
            row.update(source_language=pair['source_language'], target_language=pair['target_language'], dictionary=dialect)
        return result

    def save(self, original, english, source, source_label='user_input_unreviewed', kind='sentence', dialect='kanglish'):
        old = next((row for row in self.corrections(dialect) if row['key'] == ' '.join(original.lower().split())), None)
        if old and old['kind'] != kind:
            raise ValueError('This spelling already has a different dictionary entry type.')
        super().save(original, english, source.replace('desktop_', 'web_', 1), old['source_label'] if old else source_label, kind, dialect)

    def save_glossary(self, parent, terms, source_label, pasted_keys=(), dialect='kanglish'):
        originals = {' '.join(term.lower().split()) for term, _ in terms}
        previous = {r['key']: r for r in self.corrections(dialect) if r['key'] in originals}
        if any(row['kind'] != 'glossary' for row in previous.values()):
            raise ValueError('A sentence entry cannot be replaced by a word meaning.')
        super().save_glossary(parent, terms, source_label, pasted_keys, dialect)
        with self.connect() as db:
            for normalized, old in previous.items():
                db.execute('UPDATE corrections SET source_label=?,review_status=? WHERE key=?',
                           (old['source_label'], old['review_status'], normalized))
            for normalized in originals - set(previous):
                db.execute("UPDATE corrections SET source=replace(source,'desktop_','web_') WHERE key=?", (normalized,))

    def action(self, name, body):
        app = object.__new__(App)
        app.store = self
        app.record = lambda *args, **kwargs: None
        return getattr(app, name)(body)
