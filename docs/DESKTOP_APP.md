# Kanglish on localhost

Run the existing Gemma GGUF on your laptop through a small browser interface.
Python uses only its standard library. NVIDIA inference uses an official pinned
llama.cpp CUDA release. The GGUF is reused, not downloaded or copied.

```powershell
python scripts/setup_desktop_runtime.py
python scripts/run_desktop.py
```

Open <http://localhost:8000>. Ctrl+C stops the Python service and the llama.cpp
child it started. Both bind only to 127.0.0.1. An occupied port produces an error;
the launcher never stops another application's process. To change the browser
port use `--port 8010`; change `runtime_port` in the ignored config if needed.
To stop a background workbench, use `python scripts/run_desktop.py --stop`.
The inference endpoint uses a per-launch private key and the browser server
requires its own same-origin page token for writes.

The setup verifies GitHub's SHA-256 for both Windows x64 CUDA 13.5 packages from
release `b12478`, then verifies the supplied three-epoch Gemma export. Runtime
files and the download manifest live under `.tools/desktop/b12478`. Your driver
must support CUDA 13.5. Use `gpu_layers: 0` with a compatible installed runtime
for CPU inference. No Python CUDA, PyTorch, or training dependencies are needed.

## Translation and corrections

Translate Kannada in English letters into English. Add the previous message as
context when useful. The interface shows elapsed local inference time and marks
exact saved translations separately. Unchecking **Use saved meanings** bypasses
both exact correction recall and personal correction examples; bundled glossary
hints remain part of the shared translation prompt.

**Verify translation** sends the current input, candidate, supplied context and
relevant saved corrections to Google. It reads `GEMINI_API_KEY` from the process
environment or the repository's ignored `.env`; the key is never returned to the
browser or placed in a URL. `verification_model` in `configs/desktop.local.json`
defaults to `gemini-3.5-flash-lite`. Errors, incomplete JSON, verbose results and
uncertain guesses cannot be accepted as verified corrections. No automatic
retries or model/provider substitutions consume additional quota.

Saving a local result, a verified correction, or your own wording requires a
button click. Saved entries are durable SQLite transactions under
`.tools/desktop/state/translations.sqlite3`. This is desktop correction memory,
not a weight update or phone synchronization. Existing phone memory is untouched.
My dictionary supports search, manual entries and removal. Export produces
Kannada/English pairs with approval/source metadata. Android's dictionary
import accepts the `original`/`english` pair representation; imported entries
are subject to Android's own import/source handling.

After **Use your own correction → Save correction**, an optional **Teach the
words in this sentence** editor appears. **Split sentence into words** fills the
Kanglish columns without guessing English meanings. Enter a meaning for each
word you know, or edit a row to hold a multi-word phrase. Blank meanings are
skipped. Names can use the same spelling as their English meaning. Saving a
breakdown requires the latest sentence correction to be saved first. All filled
rows are validated before the word batch is committed.

Splitting also reveals a bulk-paste box. Paste explicit mappings such as
`maadu->do, hotel-alli->in the restaurant`, then click **Extract into rows**.
Commas, semicolons or new lines separate mappings; `->`, `=>` and `→` are
supported. Commas inside a meaning are preserved. Markdown bullets/code fences
are tolerated. Space/hyphen differences between complete adjacent words are
aligned to the actual sentence spelling: `Ee milkshake` matches `Ee milk shake`,
and `ice cream` matches `icecream`. The letters must match; this does not guess
phonetic spellings, accept substrings, or join across sentence punctuation.
Technical tokens such as `.env`, `.env.local`, `C++`, `C#`, `config.json`,
`foo_bar` and `src/main.py` keep their symbols during matching and splitting.
They are indivisible: `.env` does not match `env`, `C++` does not match `C`,
and `file .env` does not match `file.env`.
Mappings outside the sentence are reported
and ignored. Conflicting duplicates or missing meanings are rejected.
Extraction merges into the current draft without saving or calling an AI.
Hyphenated words stay together when splitting. A mapping such as
`WhatsApp-alli -> on WhatsApp` fills a combined word/phrase row and replaces
its blank component rows; manually entered component meanings are preserved.
Review the rows, then click **Save word meanings**. Pasted origins remain marked
in the export after approval.

For multiple sentences, open **My dictionary → Bulk Import / Paste Batch**.
Paste numbered blocks with `Kanglish:`, `English:`, and optional `Word Mapping:`
fields. Mappings may continue on following lines and use the same arrow formats.
**Preview** parses without saving; **Import batch** parses and saves the complete
batch in one click. Limits are 500 sentences, 80 mappings per sentence, and
10,000 mappings overall, with up to 640,000 characters of pasted text and a
5 MB JSON request limit. Invalid fields and missing word meanings reject the
entire import. Conflicting full-sentence translations or entry types within a
batch keep the first occurrence and skip later conflicts. Preview and import
report each skipped item, its supplied translation/type, and the earlier item
that was kept. Skipped sentences contribute no word mappings or contextual
links; a conflicting mapping skips only that mapping. Identical duplicate
sentences can still supply additional mappings. **Replace existing meanings**
applies only to stored entries; it does not resolve contradictions inside the
paste. Original sentence spelling and English wording are preserved without
assessing semantic equivalence or correcting typos. A word may
have different supplied meanings: `thumba -> very` and `thumba -> very much`
become shared alternatives `very / very much`, with each exact meaning retained
on its parent-sentence link. Preview shows these combined alternatives; it does
not assess whether supplied meanings are accurate.

The 2026-11-19 duplicate-conflict update changes import acceptance and reports,
not model weights or historical scores. Earlier imports rejected the whole
batch on the first conflicting duplicate; now valid entries can be saved while
all later conflicts remain available for review in the report and pasted text.

Existing sentence translations are kept by default, and new word alternatives
are added without discarding previous word meanings. **Replace existing meanings**
permits replacing the supplied entries, retaining existing source labels and review
status. A source spelling
cannot change between a sentence and glossary entry during import: such existing
entries are skipped and reported, while the rest of the valid batch is saved.
Different existing sentence translations are also skipped when replacement is
off. Identical entries count as already saved. Skipped entries keep their text
and metadata, and no contextual links are written to or from skipped entries.
Malformed input still rejects the whole batch before any writes. New entries
are marked `user_supplied_bulk`, with `user_approved` review status and an explicit
desktop bulk source. Import uses one SQLite transaction and calls no model or
cloud validator. Both entry types appear in dictionary export for Android import
and later training preparation; saving does not change model weights.

Well-formed mappings that are absent, noncontiguous, or repeat the entire sentence
are skipped in bulk import, with the item number and source phrase reported in
Preview and after saving. Other matching words and the full sentence translation
are still saved, even when every mapping in one sentence is skipped. No missing
words are inferred or removed from the source to force a match. A mapping with
no English meaning or no arrow still requires correction before importing.

The contextual-word update adds an `english` field to `glossary_links`; existing
links have no recorded contextual meaning until one is supplied. Dictionary
export adds `parent_meanings` only where exact mappings are recorded. Older
Android importers use the combined English alternatives and parent-sentence
list; they do not consume this new contextual field. This is a memory/export
format change, not a model accuracy improvement or a historical score change.

Word meanings are marked `kind: glossary`; full sentence pairs keep
`kind: sentence`. Word entries retain their parent sentence(s) and source/review
labels. **Export dictionary** includes both in one JSON array. Matching glossary
entries enter future desktop prompts as word meanings; exact entries can be
recalled directly. Unchecking saved meanings bypasses personal glossary hints
too. A new word meaning updates that dictionary key; it does not replace the
full sentence correction.

Transfer the exported file to Android and import it in **My dictionary**. The
updated app preserves word/sentence types, parent sentences, original source
labels and supplied review status through imports and training exports. Imported
words are available for exact recall and as relevant vocabulary for other
sentences and cloud checks. Existing meanings are kept by default; the import
preview offers **Replace existing meanings** for deliberate updates. Desktop
and phone do not automatically synchronize. The app must be updated to this
build to retain the new metadata and replacement option; older builds can still
import the plain pairs.

These approved sentence and glossary pairs are suitable inputs for a later
explicit, checksummed training-data selection. Saving or importing them changes
memory and translation hints, not GGUF model weights. Protected repository data
files and training selections are never modified by this interface.

## Batch tests and evidence

Enter one message per line, optionally followed by a tab and expected meaning.
The example button supplies 10 synthetic controls, labelled independently of
training data. Human-entered cases are labelled `user_input_unreviewed`.
Cloud checking is off by default and never saves corrections automatically.
Use Review on a completed row to choose a result on the Translate page.

Batches run sequentially with progress, an interval, a timer of at most 60
minutes, and a stop-after-current-case button. The server permits at most 500
automated case attempts per launch, within 60 minutes of launch. Repeated cloud
failures skip later cloud checks and preserve the local outputs. A browser reload
ends the browser-driven batch; completed outputs remain in SQLite and the CSV.

The user increased the desktop batch limit from 10 to 100 cases on 2026-11-18.
They subsequently increased it to 500, with paste and mapping limits scaled to
fit larger imports. The 60-minute limit remains. This changes session capacity; historical scores
and the ten supplied synthetic examples are unchanged.

Each launch creates `results/desktop_sessions/<timestamp>/test_log.csv` plus a
manifest containing model, executable, prompt, glossary and initial-memory
hashes. CSV rows are events: translation, verification, saving or failure.
The app can download its session CSV and exported dictionary. Raw model output
and native generation timings are preserved in SQLite for diagnostics.

## Comparability

This is a desktop inference harness, not an Android UI or JNI emulator. It uses
the existing Python Gemma prompt/glossary adapter and equivalent bounded personal
examples. It does not execute every Android routing, name-preservation or voice
shortcut. Desktop latency includes local HTTP/tokenization and differs from
phone latency. Runtime build and hardware differ from Android.

The active export SHA-256 is
`12d2c4c56b583d58cea93ca0201516d873d5db389eb8690a26ea3cf3c07f0945`.
The supplied adapter describes a merged-data continuation but does not supply
an explicit checksummed dataset selection for it. Training coverage remains
unknown. The interface never creates or edits protected CSVs or training data.
Saved memory can change later outputs; compare raw runs with separate fresh
desktop state if a controlled model-only experiment is required.

## Verification on this laptop, 2026-11-17

Eight standard-library tests passed for persistence, source labels, uncertainty,
truncated/verbose review rejection, stored-result approval, relevant examples,
memory bypass and the automated session limit. Python compilation and JavaScript
syntax checks passed. Static assets and all JavaScript DOM IDs were checked.
Local HTTP checks confirmed host/origin rejection and authenticated inference.

Real RTX 3050 6 GB inference loaded successfully, using about 941 MiB VRAM.
The fresh `ninna hesaru Rachit` case returned `Your name is Rachit.` in 0.514 s;
cloud verification agreed in 2.484 s. Three sequential raw-model batch cases
completed in 0.117–0.378 s with the runtime already loaded and prompt caching.
These are small functional examples, not an accuracy benchmark.

The model mistranslated `oota aayta` as `The food is not available.` The cloud
review returned `Have you eaten?`; that reviewed correction was saved and recalled
successfully. Both verified and manual saving, CSV output and dictionary export
were exercised. Three synthetic smoke corrections persisted across restarts.
`--stop` terminated both owned servers, and the workbench was restarted for use.
Protected repository CSV hashes remained identical to the recorded baseline.

Chrome rendering and actual button clicks were **not** inspected: the browser
connector was unavailable and the Windows helper stopped because it could not
confidently determine the browser URL. Service behavior was tested through HTTP;
visual layout and browser-driven interval/cancellation need a manual browser check.
Detailed local evidence lives in
`results/desktop_sessions/20261117_234902/smoke_results.json` and that session's CSV.

The 2026-11-18 word-editor addition passed 14 desktop storage/validation tests,
a browser-independent JavaScript state test (reveal after successful saving,
splitting, submission and stale-input hiding), and 16 focused Android tests.
The Android debug APK built successfully. A live synthetic Kannada sentence was
corrected to `Vihana, I want warm water.` and linked to `bechagina → warm`.
Both types exported with their original labels, the word recalled immediately,
and its meaning entered a new-sentence prompt. An invalid mixed word batch left
the dictionary unchanged. A local SQLite backup preceded the schema migration.
Browser visual inspection remained blocked by the Windows helper's URL check;
no phone interaction or model weight training was performed for this change.
