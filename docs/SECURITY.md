# Security and public translation deployment

## Repository boundary

This is a fresh repository: the original Git history, private correction exports,
databases, environment files, local configs, logs, datasets, models and runtimes
are excluded. Required packaged glossaries keep their source and review metadata.
The empty `.env.example` contains no credential. `.gitignore` and `.vercelignore`
exclude local state; the standard-library security guard rejects sensitive paths
and known credential shapes. Gitleaks independently scans content and Git history.
These checks reduce accidental exposure; they are not a full penetration test.

## Current localhost boundary

The Python and llama.cpp servers bind to 127.0.0.1. Host/origin checks and a random
page token protect writes; the model has a separate per-launch private key.
These are local access controls, not user authentication. `/api/status` returns
the page token, and dictionaries/history belong to the local owner. Publicly
proxying these endpoints would expose that owner's data and paid verification.
Do not change the bind address to deploy this backend.

No browser code contains provider credentials. Provider errors omit upstream
headers and URLs. The exported backend rejects HTTP redirects so request headers
cannot be forwarded to an unexpected origin. Response headers restrict scripts
and connections to the same origin, prevent framing and disable content sniffing.
Untrusted translations are inserted through textContent/DOM text, not HTML.

Paid `/api/verify` requests are limited in this single local server to 10 per
minute and 200 per launch, with one verification in flight. Rejected requests
return 429 (with Retry-After for the minute limit), or 503 while another verification is running. These
limits are a local safeguard; restarting resets them. They are not a distributed
quota or a public-deployment guarantee.

## Before a public Vercel deployment

1. Serve the frontend on Vercel and keep provider/inference credentials exclusively
   in server environment variables. Never use a public-prefixed variable for a
   secret. Use a fixed allowlisted inference URL, TLS, authentication, no redirects,
   bounded responses, a timeout and an output-token cap. Keep llama.cpp private.
2. Add real session authentication with secure HttpOnly cookies and CSRF checks.
   Authorize every dictionary, history, run, save and export by user ownership.
   Use a persistent database with per-user isolation. Do not share one SQLite file
   across public users or depend on a function's local filesystem for durable state.
3. Rate-limit `/api/translate` and `/api/verify` on the server **before** inference
   or paid provider calls. Suggested initial policy: 10 translations/minute/user,
   100/day/user, plus an IP burst limit and a global daily request/token budget.
   Verification should have a stricter independent quota, such as 5/minute/user
   and 20/day/user. Tune these from measured demand and the provider budget.
4. Use atomic shared counters (for example Redis) across instances. Account for
   both successful and failed attempts; reject with 429 and Retry-After. Fail
   closed if the quota store is unavailable. Derive identities from authenticated
   sessions and trusted platform metadata, not client-supplied forwarding headers.
   Set a global concurrency cap and provider spending limit. IP limits alone are
   insufficient and can penalize people on shared networks.
5. Add a Vercel WAF rule for API bursts and bot abuse, then enforce account quotas
   inside the API. Browser button disabling, debouncing, a page token and CORS
   do not stop scripted requests. Protect preview deployments too.
6. Keep public payload limits lower than the desktop's 5 MB batch-import limit.
   Validate language/direction, context length and output size; disable automated
   batches unless authenticated and separately budgeted. Test ownership boundaries,
   exhausted quotas, concurrency, proxy spoofing and quota-store outages.
7. Avoid raw translation text in production logs. Define retention/deletion rules
   and explain when messages are sent to an external model. Document hosted-model
   changes as a comparability change rather than reusing local accuracy claims.

Reference documentation, checked 2026-11-19:
- [Vercel WAF rate limiting](https://vercel.com/docs/vercel-firewall/vercel-waf/rate-limiting)
- [Vercel Functions limits](https://vercel.com/docs/functions/limitations)

Rate limiting is needed for a public translation service even if inference is
self-hosted: it protects GPU capacity, availability and any paid fallback/review
API. Vercel firewall availability and pricing depend on the selected plan.
