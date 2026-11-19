# Hosted verification — 2026-11-19

## Language directions and audio

- Generated hosted UI tests cover all 20 language pairs, five options per menu,
  swapping text and invalidating saved-result actions, custom dictionary creation,
  recording permission denial, stop/error track cleanup, file preview/discard,
  explicit audio submission and missing-voice feedback. Devices and providers are
  mocked; these checks do not establish physical microphone or voice quality.
- Six new standard-library API tests cover direction/script contracts, empty
  dictionary persistence, immutable metadata, owner isolation, export metadata,
  reverse imports, Kannada combining marks, audio auth/CSRF/origin/quota denial,
  payload limits, uncertain speech and private history without automatic saving.
- Automated checks make no paid provider calls. No original protected datasets,
  historical weights or recorded accuracy scores are changed.
- All 85 Python tests and three JavaScript state suites passed, as did syntax,
  repository security and staged/full-history Gitleaks checks. Implementation
  commit: `9e45e35`. Production deployment `dpl_2R9WDykPRB9zJnpiUiHD6tBgDfKf`
  was READY and aliased to https://kanglish-web.vercel.app.
- Live HTTPS checks verified the deployed controls/JavaScript, local-blob media
  CSP and same-origin microphone permission header. Authenticated checks verified
  all five language codes and 20 default directions, empty named dictionaries,
  immutable direction metadata, private reverse imports, exact saved translation
  reuse from English to Kanglish, Tuluglish, Kannada and Tulu, export metadata and cross-owner
  denial. Invalid audio MIME, CSRF and cross-origin requests were rejected before
  provider calls. Both disposable synthetic accounts and their data were removed.
- No live speech/provider quality check was performed. Automatic approval review
  stopped browser inspection because the current browser URL could not be
  verified. Physical microphone capture and installed voice quality remain
  unverified; recording/upload state and provider integration are mocked above.

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

## Password recovery and account security

- Added email recovery with PKCE and a signed, expiring, HttpOnly verifier;
  password reset requires separate signed recovery proof. A normal session or
  client-supplied recovery token cannot bypass current-password verification.
- Eight synthetic password-security tests cover fixed redirects, account-neutral
  messages, cookies, CSRF/origins, quota failure, forged/expired/reused proofs,
  current-password verification, owner matching and refresh-session revocation.
  JavaScript state checks cover URL-code removal, recovery isolation, email-only
  reset requests and password-confirmation mismatch.
- A disposable account on the real Supabase service verified wrong-current-
  password rejection, password update, old-password rejection, new-password login,
  cookie clearing and previous refresh-token revocation. Only that newly created
  account was removed. No personal account password was set or inspected.
- The real recovery API accepted the PKCE request for a randomized nonexistent
  account and returned a generic response with a secure verifier cookie. This
  check sent no email; delivery and an inbox-click reset require the account owner
  to open their email in the requesting browser.
- All 62 desktop tests and 17 hosted tests passed, together with both JavaScript
  state checks. Initial runs encountered intermittent Windows loopback socket
  aborts; subsequent complete runs passed. No model or paid provider was called.
