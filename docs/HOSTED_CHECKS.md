# Hosted verification — 2026-11-19

- Provisioned a dedicated Supabase Free Plan database in Mumbai, connected to
  Vercel production/development only. Model/provider secrets are server-only.
- Deployed production at https://kanglish-web.vercel.app.
- All 68 standard-library Python tests passed, plus the existing JavaScript
  state test and syntax checks for desktop and hosted assets.
- Real Supabase checks confirmed authenticated owner isolation, atomic snapshot
  version conflicts, service-only quota permissions, exhausted quotas, and shared
  concurrency leases. Disposable synthetic accounts were removed afterward.
- Live HTTPS checks confirmed session cookies, unauthorized/cross-origin denial,
  private dictionary and word-meaning persistence, metadata retention, cross-user
  run/dictionary denial, private-file 404s, and logout.
- A labelled synthetic online translation returned `Let's meet tomorrow morning.`
  for `naale beligge sigona`. A separate verification request completed. These
  two paid model calls are functional checks, not an accuracy benchmark.
- Live synthetic accounts and their dictionary/history rows were removed through
  verified account IDs created only for the checks. Personal desktop data was
  never uploaded. No training or original protected CSV changes occurred.
- Staged-content and full Git-history secret scans passed. Local env files contain
  required development credentials, stay ignored, and are excluded from Vercel
  uploads. GitHub CI passed for the hosted implementation commit `ed7d8e3`.
- Browser visual inspection was blocked because automatic approval review did
  not approve Computer Use for Google Chrome. The live HTTPS API was verified.

- Verified Supabase Auth's production redirect is
  `https://kanglish-web.vercel.app` after the Site URL was saved. The check generated
  a recovery link for a disposable synthetic account without sending email,
  inspected its redirect destination, and removed that exact account afterward.
