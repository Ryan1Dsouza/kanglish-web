"use strict";
(() => {
  let csrf = "", refreshing = null;
  const message = (text, error = false) => {
    const element = document.getElementById("auth-message");
    element.textContent = text; element.classList.toggle("error", error);
  };
  async function request(path, body) {
    const response = await fetch(path, body === undefined ? {} : {
      method: "POST", headers: {"Content-Type": "application/json", "X-Kanglish-Token": csrf}, body: JSON.stringify(body)
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Request failed. Please try again.");
    if (result.csrf) csrf = result.csrf;
    return result;
  }
  window.KanglishAuth = {
    get csrf() {return csrf;},
    refresh() {
      if (!refreshing) refreshing = request("/api/auth/refresh", {}).catch(error => {
        document.getElementById("workspace").hidden = true;
        document.getElementById("auth-page").hidden = false;
        message("Your session ended. Please sign in again.", true);
        throw error;
      }).finally(() => {refreshing = null;});
      return refreshing;
    }
  };
  document.getElementById("auth-form").addEventListener("submit", async event => {
    event.preventDefault();
    const form = event.currentTarget, buttons = [...form.querySelectorAll("button")];
    buttons.forEach(button => {button.disabled = true;});
    const action = event.submitter?.dataset.action || "login";
    message(action === "signup" ? "Creating your account…" : "Signing in…");
    try {
      const result = await request(`/api/auth/${action}`, {
        email: document.getElementById("auth-email").value.trim(), password: document.getElementById("auth-password").value
      });
      document.getElementById("auth-password").value = "";
      if (result.authenticated) location.reload();
      else message(result.message);
    } catch (error) {message(error.message, true);}
    finally {buttons.forEach(button => {button.disabled = false;});}
  });
  document.getElementById("logout-button").addEventListener("click", async () => {
    try {await request("/api/auth/logout", {}); location.reload();}
    catch (error) {message(error.message, true);}
  });
  (async () => {
    try {
      let session = await request("/api/auth/session");
      if (!session.authenticated && session.can_refresh) session = await window.KanglishAuth.refresh();
      if (!session.authenticated) return message("Sign in or create an account to continue.");
      document.getElementById("auth-page").hidden = true;
      document.getElementById("workspace").hidden = false;
      const script = document.createElement("script"); script.src = "/app.js"; document.body.append(script);
    } catch (error) {message(error.message, true);}
  })();
})();
