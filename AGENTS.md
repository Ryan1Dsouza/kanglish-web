# Website repository rules

- Never commit secrets, environment values, local configs, personal translations,
  SQLite databases, logs, model weights or downloaded runtimes.
- Keep supplied source labels, review status and dictionary license attribution.
- Keep runtime and maintenance code in the Python standard library.
- Run the repository security guard and Gitleaks before pushing.
- This backend is for localhost. Do not expose it publicly by changing its bind
  address or proxying it: implement the controls in docs/SECURITY.md first.
- The hosted API lives in scripts/cloud/ and api/index.py. It uses validated
  Supabase sessions, owner-scoped storage/RLS, CSRF cookies and shared SQL quotas.
  Never replace those checks with the desktop page token or in-memory quotas.
- Build public/ from scripts/build_web.py; keep the original desktop interface.
- Keep extraction provenance; document changes to prompt or runtime behavior.
- Limit experiment sessions to 60 minutes or 10 experiments unless the user
  explicitly changes that limit. Automated tests do not call paid APIs or models.
