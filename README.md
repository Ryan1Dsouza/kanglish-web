# Kanglish Web

Browser interface for translating Kanglish and Tuluglish to English with a local
llama.cpp model, reviewing optional Gemini checks, and saving approved sentence
translations and word meanings. Includes dictionary import/export and batch testing.

This repository was extracted from [Kanglish](https://github.com/Ryan1Dsouza/Kanglish).
It contains the website, its Python backend, runtime setup, required prompt/glossary
dependencies and tests. Historical paths under `mobile/android` contain runtime
reference files, not an Android app build. Training remains in the original repo.

## Run locally

Requires Python 3.11+. No pip packages or npm dependencies are required. The
automated runtime installer targets Windows x64 with a CUDA 13.5-compatible driver.

1. Make the existing GGUF available locally at the model path in
   `configs/desktop.example.json`. Weights are intentionally excluded from Git.
2. Run `python scripts/setup_desktop_runtime.py`. It verifies the runtime download
   and model SHA-256, then creates ignored `configs/desktop.local.json`.
3. Run `python scripts/run_desktop.py` and open <http://localhost:8000>.

Alternatively, copy the example config to `configs/desktop.local.json` and point
`binary` and `model` at locally available files. Absolute paths are supported.
Retain the expected model checksum. Set `gpu_layers` to `0` for a compatible CPU
runtime. Python compilation and tests do not require the model.

For optional **Verify translation**, set `GEMINI_API_KEY` in the server environment
or an ignored `.env` file, using `.env.example` as a template. Never put it in
browser JavaScript. Verification sends the current message, candidate, context and
relevant saved meanings to Google. Saving corrections requires an explicit click.
Local memory is in `.tools/desktop/state`; logs are under `results/desktop_sessions`.

## Check changes

```sh
python scripts/security_check.py
python -m unittest discover -s tests -p "test_desktop_*.py"
node --check mobile/desktop/app.js
node tests/desktop_web_state.test.cjs
gitleaks dir . --redact --no-banner
```

The tests use synthetic controls and mocks. They do not run inference or paid API
calls. GitHub Actions also scans the complete new Git history for secrets.
After cloning, install the local commit guard with
`git config core.hooksPath .githooks`.
See [the recorded security checks](docs/SECURITY_CHECKS.md).

## Vercel

The current app runs a long-lived local model process and shares one local
dictionary. Importing this repo into Vercel does **not** create a working, secure
public translation service. There is no production Vercel deployment configured.

The intended architecture is a Vercel frontend and authenticated server API, with
a separate authenticated inference host (or an explicitly selected hosted model)
and persistent per-user storage. See [the deployment and rate-limit plan](docs/SECURITY.md).

## Provenance and data licenses

[EXTRACTION.json](docs/EXTRACTION.json) records source paths and SHA-256 values
before website-specific hardening. [DESKTOP_APP.md](docs/DESKTOP_APP.md) is the
original operating/history document; its historical training and result paths
refer to the original Kanglish repo and were not copied. Security changes here
do not change the model weights, prompt or historical accuracy scores.

The Alar subset retains its source/review fields and
[ODbL attribution](mobile/android/app/src/main/assets/alar_conversational_glossary.LICENSE.md).
The original repository did not include a root source-code license; this
extraction does not invent one or change the dictionary data license.
