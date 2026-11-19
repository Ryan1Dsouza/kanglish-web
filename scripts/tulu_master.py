"""Owner-provided Tulu senses; preserve ambiguous aliases rather than guessing."""
from collections import Counter, defaultdict
from functools import lru_cache
import json
from pathlib import Path
import re

from scripts.trusted_pipeline.quality import normalized

ROOT = Path(__file__).resolve().parents[1]
MASTER = 'data/corpus/tulu_master_glossary.json'
ASSET = 'mobile/android/app/src/main/assets/tulu_master_glossary.json'
NEGATIVE = re.compile(r"\b(?:no|not|never|without|cannot)\b|n['’]t\b", re.I)


@lru_cache(maxsize=8)
def _index(path, modified):
    raw = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    indexed = defaultdict(list)
    for category, groups in raw.items():
        if not isinstance(groups, dict):
            raise ValueError('Master glossary categories must contain term/meaning objects')
        for group, meaning in groups.items():
            if not isinstance(meaning, str) or not meaning.strip():
                raise ValueError('Master glossary meanings must be nonempty strings')
            for alias in group.split(' / '):
                key = normalized(alias)
                if not key:
                    raise ValueError('Empty master glossary alias')
                entry = {'source': alias.strip(), 'meaning': meaning, 'category': category, 'group': group}
                if entry not in indexed[key]:
                    indexed[key].append(entry)
    return dict(indexed)


def master_index(root=ROOT):
    path = Path(root) / MASTER
    return _index(str(path.resolve()), path.stat().st_mtime_ns) if path.exists() else {}


def mixed_polarity(meaning):
    parts = meaning.split(' / ')
    return len(parts) > 1 and bool(NEGATIVE.search(parts[0])) != any(bool(NEGATIVE.search(p)) for p in parts[1:])


def standalone_entries(root=ROOT):
    indexed = master_index(root)
    path = Path(root) / 'mobile/android/app/src/main/assets/glossary.json'
    base_keys = {normalized(r['kanglish']) for r in json.loads(path.read_text(encoding='utf-8-sig'))} if path.exists() else set()
    corpus_path = Path(root) / 'data/corpus/mangalore_glossary.json'
    corpus = json.loads(corpus_path.read_text(encoding='utf-8-sig')) if corpus_path.exists() else {}
    tulu_keys = {normalized(alias) for groups in corpus.values() for term, meaning in groups.items()
                 if meaning.endswith(('(Tulu)', '(Tulu/Kannada)', '(Coastal slang)')) for alias in term.split(' / ')}
    accepted, excluded = [], []
    for alias, senses in indexed.items():
        meanings = {s['meaning'] for s in senses}
        reason = ('multiple_contextual_senses' if len(meanings) != 1 else
                  'mixed_polarity_group' if mixed_polarity(senses[0]['meaning']) else
                  'cross_language_standalone_collision' if alias in base_keys and alias not in tulu_keys else None)
        if reason:
            excluded.append({'source': senses[0]['source'], 'reason': reason, 'senses': senses})
        else:
            accepted.append(senses[0])
    return accepted, excluded


def runtime_entries(language='tcy-Latn', root=ROOT):
    """Mirror CoastalGlossary: master Tulu senses; conservative mixed-mode terms."""
    root = Path(root)
    legacy = [(r['source'], r['meaning']) for r in json.loads((root / 'mobile/android/app/src/main/assets/coastal_glossary.json').read_text(encoding='utf-8'))]
    base = json.loads((root / 'mobile/android/app/src/main/assets/glossary.json').read_text(encoding='utf-8-sig'))
    base_keys = {normalized(r['kanglish']) for r in base}
    indexed = master_index(root)
    entries = []
    for alias, senses in indexed.items():
        if language != 'tcy-Latn' and alias in base_keys:
            continue
        meanings = sorted({s['meaning'] for s in senses})
        meaning = meanings[0] if len(meanings) == 1 else 'Context-dependent Tulu senses: ' + ' | '.join(meanings)
        entries.append((alias, meaning))
    seen = {s for s, _ in entries}
    entries.extend((s, m) for s, m in legacy if s not in seen)
    return sorted(entries, key=lambda p: (-len(p[0]), p[0]))


@lru_cache(maxsize=8)
def _runtime_patterns(language, root, versions):
    return [(source, meaning, re.compile(r'(?<![^\W_])' + re.escape(source) + r'(?![^\W_])', re.I))
            for source, meaning in runtime_entries(language, Path(root))]


def runtime_hints(source, language='tcy-Latn', root=ROOT):
    root = Path(root)
    files = (MASTER, 'mobile/android/app/src/main/assets/glossary.json',
             'mobile/android/app/src/main/assets/coastal_glossary.json')
    versions = tuple((root / p).stat().st_mtime_ns if (root / p).exists() else 0 for p in files)
    return [(s, m) for s, m, pattern in _runtime_patterns(language, str(root.resolve()), versions) if pattern.search(source)]


def main():
    indexed = master_index()
    entries, excluded = standalone_entries()
    destination = ROOT / ASSET
    destination.write_bytes((ROOT / MASTER).read_bytes())
    report = {'categories': len(json.loads((ROOT / MASTER).read_text(encoding='utf-8'))),
              'groups': sum(len(groups) for groups in json.loads((ROOT / MASTER).read_text(encoding='utf-8')).values()),
              'aliases': len(indexed), 'standalone_candidates': len(entries),
              'excluded_reasons': dict(Counter(r['reason'] for r in excluded)), 'excluded': excluded,
              'policy': 'Owner text preserved; ambiguous forms remain contextual hints; no inferred English labels'}
    directory = ROOT / 'results/tulu_master_20261108'
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'glossary_import.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'excluded'}, indent=2))


if __name__ == '__main__':
    main()
