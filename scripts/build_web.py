"""Generate the hosted UI from the desktop assets without changing the local app."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

def build():
    source = ROOT / 'mobile/desktop'
    destination = ROOT / 'public'
    destination.mkdir(exist_ok=True)
    html = (source / 'index.html').read_text(encoding='utf-8')
    replacements = {
        'Kanglish · Desktop': 'Kanglish · Online',
        'YOUR DESKTOP COMPANION': 'YOUR WORDS, UNDERSTOOD',
        '<div class="shell">': '<div class="shell" id="workspace" hidden>',
        'data-view="batch"': 'data-view="batch" hidden',
        'Local translation.<br>Your words stay on this laptop.': 'Online translation.<br>Your dictionary is private.',
        'Verification sends the message, context, and relevant corrections to Google when requested.': 'Online translation sends your message and context to Google. Your saved dictionary is private.',
        'Loading your model…': 'Connecting…',
        'On this laptop': 'Online model',
        'maxlength="4000" placeholder="Try:': 'maxlength="1000" placeholder="Try:',
        'maxlength="1200"': 'maxlength="500"',
        '0 / 4,000': '0 / 1,000',
        'Saved meanings are reused locally': 'Saved meanings are reused in your account',
        'Corrections saved on this laptop.': 'Corrections saved in your private account.',
        'maxlength="640000"': 'maxlength="64000"',
        'Up to 500 sentences and 10,000 word mappings per batch.': 'Up to 20 sentences and 400 word mappings per import.',
        'Kanglish Desktop · Gemma 1B': 'Kanglish Online · 10 translations/minute, 100/day',
        '<script src="/app.js"></script>': '<script src="/auth.js"></script>',
        '<span id="log-location"></span>': '<span id="log-location"></span><button id="logout-button">Sign out</button>',
    }
    for before, after in replacements.items():
        html = html.replace(before, after)
    login = '''
<main class="auth-page" id="auth-page">
  <div class="card auth-card">
    <div class="eyebrow">KANGLISH ONLINE</div>
    <h1>Your words, understood.</h1>
    <p>Sign in to translate Kanglish and Tuluglish and keep a private dictionary.</p>
    <form id="auth-form">
      <label for="auth-email">Email</label>
      <input id="auth-email" type="email" autocomplete="email" required maxlength="254">
      <label for="auth-password">Password</label>
      <input id="auth-password" type="password" autocomplete="current-password" required minlength="12" maxlength="1024">
      <div class="auth-actions"><button class="primary" type="submit" data-action="login">Sign in</button><button type="submit" data-action="signup">Create account</button></div>
    </form>
    <p id="auth-message" role="status">Connecting securely…</p>
    <p class="subtle" id="provider-privacy">Online translation sends your message and context to the model provider. Your saved dictionary is private to your account.</p>
    <p class="subtle">New accounts require email confirmation. Use a password of at least 12 characters.</p>
  </div>
</main>
'''
    html = html.replace('<body>', '<body>' + login)
    html = html.replace('<link rel="stylesheet" href="/glossary.css">', '<link rel="stylesheet" href="/glossary.css"><link rel="stylesheet" href="/auth.css">')
    html = re.sub(r'<p class="footnote">Desktop and phone dictionaries are separate.*?</p>', '<p class="footnote">Your online dictionary is separate from the desktop and phone dictionaries. Export it to transfer approved meanings.</p>', html)
    (destination / 'index.html').write_text(html, encoding='utf-8')
    js = (source / 'app.js').read_text(encoding='utf-8')
    for before, after in {
        'let token = ""': 'let token = window.KanglishAuth.csrf',
        'On this laptop': 'Online model', 'on this laptop': 'in your private account',
        'approved locally': 'approved by you', 'Agrees with local result': 'Agrees with translation',
        'Offline ready': 'Online ready', 'Local GPU model': 'Hosted model', 'Local CPU model': 'Hosted model',
        'Loading your model…': 'Connecting…', 'Loading model': 'Connecting',
        'Session logs saved locally': 'History is private to your account',
        'Configure GEMINI_API_KEY in your local .env file': 'Verification is unavailable for this deployment',
        '/ 4,000': '/ 1,000', 'setInterval(pollStatus, 3000)': 'setInterval(pollStatus, 30000)',
    }.items():
        js = js.replace(before, after)
    js = js.replace('$("run-batch").disabled = !status.ready || busy || batchRunning;', '$("run-batch").disabled = true;')
    js = js.replace('status.ready ? status.gpu_layers ? "Online ready · GPU" : "Online ready · CPU" : "Connecting"', 'status.ready ? "Online ready" : "Connecting"')
    js = js.replace('const response = await fetch(path, body === undefined ? {} : {', 'let response = await fetch(path, body === undefined ? {} : {', 1)
    marker = '  const result = await response.json();'
    js = js.replace(marker, '''  if (response.status === 401) {
    const refreshed = await window.KanglishAuth.refresh();
    token = refreshed.csrf;
    response = await fetch(path, body === undefined ? {} : {
      method: "POST", headers: {"Content-Type": "application/json", "X-Kanglish-Token": token}, body: JSON.stringify(body)
    });
  }
''' + marker, 1)
    (destination / 'app.js').write_text(js, encoding='utf-8')
    for name in ('style.css', 'glossary.css'):
        (destination / name).write_bytes((source / name).read_bytes())
    print('Built hosted website in public/.')

if __name__ == '__main__':
    build()
