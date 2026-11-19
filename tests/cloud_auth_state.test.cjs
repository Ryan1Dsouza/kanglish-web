"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

async function setup(search = "", authenticated = false) {
  const elements = new Map(), calls = [], scripts = [], history = [];
  const storage = new Map();
  const element = id => {
    if (!elements.has(id)) elements.set(id, {value: "", hidden: false, disabled: false, textContent: "",
      classList: {toggle() {}}, handlers: {}, addEventListener(name, fn) {this.handlers[name] = fn;}, focus() {},
      reset() {}, querySelectorAll() {return [];}});
    return elements.get(id);
  };
  const context = {URLSearchParams, window: {}, location: {search, pathname: "/", reload() {}, replace() {}},
    history: {replaceState(...args) {history.push(args);}},
    sessionStorage: {getItem: key => storage.get(key), setItem: (key, value) => storage.set(key, value), removeItem: key => storage.delete(key)},
    document: {getElementById: element, createElement: () => ({}), body: {append(script) {scripts.push(script);}}},
    async fetch(path, options) {
      calls.push({path, options, removedCode: history.length > 0});
      const result = path === "/api/auth/session" ? {authenticated, csrf: "synthetic-csrf"} :
        path === "/api/auth/recovery" ? {recovery_ready: true, csrf: "new-synthetic-csrf"} : {message: "Synthetic sent control."};
      return {ok: true, async json() {return result;}};
    }};
  vm.runInNewContext(fs.readFileSync("public/auth.js", "utf8"), context);
  await new Promise(resolve => setImmediate(resolve));
  return {element, calls, scripts, history};
}

(async () => {
  const reset = await setup("?auth=recovery&code=synthetic-one-time-code");
  assert.equal(reset.calls[0].removedCode, true, "Remove reset code before requesting session");
  assert.equal(reset.calls[1].path, "/api/auth/recovery");
  assert.equal(reset.element("security-page").hidden, false);
  assert.equal(reset.element("current-password").disabled, true);
  assert.equal(reset.scripts.length, 0, "Recovery must not load authenticated workspace");
  const fallback = await setup("?code=synthetic-one-time-code");
  assert.equal(fallback.calls[1].path, "/api/auth/recovery", "Handle Supabase Site URL fallback without auth query");

  const login = await setup();
  login.element("forgot-password-button").handlers.click();
  assert.equal(login.element("auth-password").disabled, true);
  login.element("auth-email").value = "synthetic@example.invalid";
  await login.element("auth-form").handlers.submit({preventDefault() {}, currentTarget: login.element("auth-form")});
  assert.equal(login.calls.at(-1).path, "/api/auth/forgot-password");
  assert.equal(JSON.parse(login.calls.at(-1).options.body).email, "synthetic@example.invalid");
  assert.equal(Object.hasOwn(JSON.parse(login.calls.at(-1).options.body), "password"), false);

  const account = await setup("", true);
  account.element("change-password-button").handlers.click();
  assert.equal(account.element("current-password").disabled, false);
  account.element("new-password").value = "Synthetic-password-1";
  account.element("confirm-password").value = "Synthetic-password-2";
  const before = account.calls.length;
  await account.element("password-form").handlers.submit({preventDefault() {}, currentTarget: account.element("password-form")});
  assert.equal(account.calls.length, before, "Mismatch must not submit password change");
  assert.match(account.element("security-message").textContent, /don't match/);
  console.log("Hosted authentication UI controls passed.");
})().catch(error => {console.error(error); process.exitCode = 1;});
