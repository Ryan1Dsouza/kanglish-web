# Hosted Kanglish

The hosted UI runs on Vercel. The Python API validates Supabase sessions before
accessing private data. Supabase provides authentication, durable owner-scoped
dictionaries and history, and atomic shared quotas. Google Gemini 3.5 Flash Lite
is the selected external translation/review service. The site's privacy text
explains that messages, context and relevant saved examples can be sent to Google.
The API supports a separately hosted private llama.cpp server through an explicit
`TRANSLATION_PROVIDER=llama` configuration; it never exposes the local desktop server.

## Security behavior

- Supabase access/refresh tokens are in Secure, HttpOnly, SameSite=Lax, host-only
  cookies. They are never returned to browser JavaScript or kept in localStorage.
  Every private read, write, run lookup and export validates the session and
  uses the owner's identity. Database RLS provides an additional boundary.
- Writes require an exact allowed origin and matching random CSRF cookie/header.
  Responses disable private caching; site headers restrict scripts/connections
  to the same origin and prevent framing. Provider URLs come only from server
  configuration; HTTPS, response-size limits, timeouts and redirect refusal apply.
- Translation: 10/minute and 100/day per user. Verification: 5/minute and 20/day
  per user. A global cap of 200 inference/review reservations per UTC day protects
  the provider budget. IP/auth/API burst limits apply separately. Quotas are
  transactional fixed windows; failed attempts count and there are no automatic
  provider retries. Quota-store failures block inference.
- Shared database leases allow one inference per user and four globally. Leases
  expire after 90 seconds, including when a function stops before releasing one.
- Online inputs are limited to 1,000 message characters, 500 context characters,
  bounded output tokens, and 100 KB JSON bodies. Automated inference batches are
  disabled. Dictionary imports allow 20 sentences/400 mappings/64,000 characters.
- Each dictionary is bounded to 1 MB/1,000 entries, with at most 10 dictionaries
  per account. Dictionaries use version checks and transactionally commit saved
  result updates, preserving import semantics and supplied source/review fields.
- Personal history retains the latest 100 results for up to seven days. Private
  dictionaries persist until their owner removes entries or the account is deleted.
  Maintenance pruning happens during history writes. Raw messages are not printed
  in function logs. CSV downloads escape spreadsheet formulas.
- Preview deployments do not receive provider or database production credentials.
  The Supabase integration is connected to production and development only.

## Provision or reproduce

1. Create/link the Vercel project: `vercel link --yes --project kanglish-web`.
2. Provision a dedicated Supabase project on the free plan, in Mumbai:
   `vercel integration add supabase --plan free --name kanglish-web-db -m region=bom1 -e production -e development`.
3. Pull credentials into an ignored file:
   `vercel env pull .env.cloud.local --environment production`.
4. Apply the schema: `python scripts/apply_cloud_schema.py`. This standard-library
   utility verifies the pooler's TLS hostname and the pinned official Supabase CA;
   it never disables certificate checks or prints connection credentials.
5. Set secrets using `python scripts/configure_cloud.py --provider gemini --model
   gemini-3.5-flash-lite --provider-env-file <ignored-env-file>`. The utility sends
   values through Vercel stdin. Supabase credentials come from the integration.
6. Set `APP_ORIGIN` to the production HTTPS origin, and set Supabase Auth's Site
   URL/allowed redirect URL to the same site for email confirmations.
7. Run `python scripts/build_web.py`, all desktop/cloud tests, JavaScript checks,
   the security guard, and Gitleaks staged/history scans before deploying.
8. Deploy with `vercel --prod`, then test sign-in, private dictionary persistence,
   a labelled synthetic translation, cross-user denial and quota behavior.

Real environment files, provider keys, database credentials, local models,
personal corrections and captures remain excluded from Git/Vercel uploads.
Local directory scans also detect credentials in ignored development env files;
scan the Git index and full history before pushing, without allowing secrets in
commits. CI scans the clean checkout and full history independently.

## Comparability

This is an explicit provider/runtime change for the hosted version. Gemini online
translations are not the local trained Gemma model and do not reuse its accuracy
claims, weights or latency scores. Prompts and quotas also differ. Local model,
training selections and historical evidence remain in the original repository.
Memory changes only approved meanings/examples; it does not train the model.

References:
- [Vercel Python functions](https://vercel.com/docs/functions/runtimes/python)
- [Vercel trusted client headers](https://vercel.com/docs/headers/request-headers)
- [Supabase authentication](https://supabase.com/docs/guides/auth)
- [Supabase database TLS](https://supabase.com/docs/guides/platform/ssl-enforcement)
