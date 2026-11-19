# Extraction security checks — 2026-11-19

- Fresh private GitHub repository, with no original Git history copied.
- 28 explicitly selected source files, plus security code, docs and checks.
- Gitleaks 8.30.1 Windows x64 release verified against its published SHA-256:
  `d29144deff3a68aa93ced33dddf84b7fdc26070add4aa0f4513094c8332afc4e`.
- Gitleaks directory scan: no secrets detected. Full new-history scan is run
  before the initial push and on every GitHub Actions run.
- Standard-library path/content guard passed for the working copy and Git index.
  Real environment files, local config, SQLite state, correction exports, session
  logs and model files were confirmed ignored. An empty environment example is
  the only environment file included.
- 54 existing Python storage/import tests passed. Six additional security tests
  passed, covering rate budgets, failed attempts, concurrent verification, HTTP
  authorization/origin/Host checks, private file access and redirect refusal.
- JavaScript syntax and existing browser-independent state checks passed.
- Existing source/review fields and Alar attribution were preserved. No model
  inference, paid API calls, training, or historical accuracy recalculation ran.
- GitHub dependency alerts were enabled. GitHub rejected the request to enable
  its managed secret-scanning/push-protection features with HTTP 422; those
  features are not claimed as enabled. The independent Gitleaks workflow and
  local pre-commit guard provide the repository's secret checks.

These are extraction and automated security checks, not a penetration test or
approval to expose the localhost backend. See SECURITY.md for deployment controls.
