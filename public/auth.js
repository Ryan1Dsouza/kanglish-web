"use strict";
(() => {
  let csrf = "", refreshing = null, forgot = false, recovering = false;
  const $ = id => document.getElementById(id);
  const query = new URLSearchParams(location.search);
  const resetLink = query.get("auth") === "recovery" || query.has("code");
  const resetCode = resetLink ? query.get("code") : null;
  const resetError = resetLink && query.has("error");
  // Remove the one-time code before any API calls or workspace scripts run.
  if (resetLink) history.replaceState(null, "", location.pathname);
  const message = (text, error = false, id = "auth-message") => {
    const element = $(id);
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
  function forgotMode(value) {
    forgot = value;
    $("auth-password").hidden = value; $("auth-password").disabled = value;
    $("auth-password-label").hidden = value; $("signin-actions").hidden = value;
    $("send-reset-button").hidden = !value; $("back-to-signin-button").hidden = !value;
    $("forgot-password-button").hidden = value;
    $("auth-intro").textContent = value ? "Enter your account email. Open the reset link in this browser to choose a new password." : "Sign in to translate Kanglish and Tuluglish and keep a private dictionary.";
    $("auth-password").value = "";
    message(value ? "We'll email you a password reset link." : "Sign in or create an account to continue.");
    $("auth-email").focus();
  }
  function securityMode(reset) {
    recovering = reset;
    $("auth-page").hidden = true; $("workspace").hidden = true; $("security-page").hidden = false;
    $("password-form").reset();
    $("current-password").hidden = reset; $("current-password").disabled = reset;
    $("current-password-label").hidden = reset;
    $("security-heading").textContent = reset ? "Reset your password" : "Change password";
    $("security-intro").textContent = reset ? "Your email link is verified. Choose a new password." : "Confirm your current password and choose a new one.";
    message("", false, "security-message");
    $(reset ? "new-password" : "current-password").focus();
  }
  window.KanglishAuth = {
    get csrf() {return csrf;},
    refresh() {
      if (!refreshing) refreshing = request("/api/auth/refresh", {}).catch(error => {
        $("workspace").hidden = true; $("security-page").hidden = true; $("auth-page").hidden = false;
        message("Your session ended. Please sign in again.", true);
        throw error;
      }).finally(() => {refreshing = null;});
      return refreshing;
    }
  };
  $("forgot-password-button").addEventListener("click", () => forgotMode(true));
  $("back-to-signin-button").addEventListener("click", () => forgotMode(false));
  $("change-password-button").addEventListener("click", () => securityMode(false));
  $("auth-form").addEventListener("submit", async event => {
    event.preventDefault();
    const form = event.currentTarget, buttons = [...form.querySelectorAll("button")];
    buttons.forEach(button => {button.disabled = true;});
    const action = forgot ? "forgot-password" : event.submitter?.dataset.action || "login";
    message(action === "forgot-password" ? "Sending reset link…" : action === "signup" ? "Creating your account…" : "Signing in…");
    try {
      const body = {email: $("auth-email").value.trim()};
      if (action !== "forgot-password") body.password = $("auth-password").value;
      const result = await request(`/api/auth/${action}`, body);
      $("auth-password").value = "";
      if (result.authenticated) location.reload();
      else message(result.message);
    } catch (error) {message(error.message, true);}
    finally {buttons.forEach(button => {button.disabled = false;});}
  });
  $("password-form").addEventListener("submit", async event => {
    event.preventDefault();
    if ($("new-password").value !== $("confirm-password").value) {
      return message("The new passwords don't match.", true, "security-message");
    }
    const buttons = [...event.currentTarget.querySelectorAll("button")];
    buttons.forEach(button => {button.disabled = true;});
    message("Saving your new password…", false, "security-message");
    try {
      const body = {password: $("new-password").value};
      if (!recovering) body.current_password = $("current-password").value;
      const result = await request(recovering ? "/api/auth/reset-password" : "/api/auth/change-password", body);
      $("password-form").reset();
      if (result.password_changed) {
        sessionStorage.setItem("kanglish-password-changed", "1");
        location.replace("/");
      }
    } catch (error) {message(error.message, true, "security-message");}
    finally {buttons.forEach(button => {button.disabled = false;});}
  });
  $("cancel-password-button").addEventListener("click", async () => {
    $("password-form").reset();
    if (recovering) {
      try {await request("/api/auth/logout", {}); location.replace("/");}
      catch (error) {message(error.message, true, "security-message");}
    } else {$("security-page").hidden = true; $("workspace").hidden = false;}
  });
  $("logout-button").addEventListener("click", async () => {
    try {await request("/api/auth/logout", {}); location.reload();}
    catch (error) {message(error.message, true);}
  });
  (async () => {
    try {
      let session = await request("/api/auth/session");
      if (resetLink) {
        if (resetError || !resetCode) {
          forgotMode(true);
          return message("This reset link is invalid or expired. Request a new one.", true);
        }
        await request("/api/auth/recovery", {code: resetCode});
        return securityMode(true);
      }
      if (session.recovery_ready) return securityMode(true);
      if (!session.authenticated && session.can_refresh) session = await window.KanglishAuth.refresh();
      if (!session.authenticated) {
        if (sessionStorage.getItem("kanglish-password-changed")) {
          sessionStorage.removeItem("kanglish-password-changed");
          return message("Password changed. Sign in with your new password.");
        }
        return message("Sign in or create an account to continue.");
      }
      $("auth-page").hidden = true; $("workspace").hidden = false;
      const script = document.createElement("script"); script.src = "/app.js"; document.body.append(script);
    } catch (error) {
      if (resetLink) forgotMode(true);
      message(error.message, true);
    }
  })();
})();
