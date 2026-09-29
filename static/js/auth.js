/** RecipeHub — login and registration. */
(function () {
  "use strict";

  var API = window.API, UI = window.UI, $ = UI.$, $$ = UI.$$;

  /** Only allow same-origin relative paths as a post-login destination. */
  function safeNext() {
    var next = new URLSearchParams(window.location.search).get("next") || "";
    if (next && next.charAt(0) === "/" && next.charAt(1) !== "/") return next;
    return "";
  }

  function showError(form, alertNode, message) {
    UI.applyFieldErrors(form, {});
    if (!alertNode) return;
    alertNode.textContent = message;
    alertNode.hidden = false;
  }

  function initPasswordToggles() {
    $$("[data-toggle-password]").forEach(function (button) {
      button.addEventListener("click", function () {
        var input = document.getElementById(button.dataset.togglePassword);
        if (!input) return;
        var revealing = input.type === "password";
        input.type = revealing ? "text" : "password";
        button.setAttribute("aria-label", revealing ? "Hide password" : "Show password");
      });
    });
  }

  function initLogin() {
    var form = $("#login-form");
    if (!form) return;
    var alertNode = $("#login-error");
    var submit = $("#login-submit");

    if (API.isAuthenticated()) {
      window.location.replace(safeNext() || "/dashboard/");
      return;
    }

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      alertNode.hidden = true;
      UI.setBusy(submit, true);

      var payload = {
        username: form.username.value.trim(),
        password: form.password.value
      };

      API.login(payload)
        .then(function (data) {
          API.setToken(data.token);
          API.setUser(data.user);
          UI.toast("Welcome back, " + data.user.username + "!", "success");
          window.location.href = safeNext() || "/dashboard/";
        })
        .catch(function (error) {
          UI.setBusy(submit, false);
          var handled = UI.applyFieldErrors(form, error.data);
          if (!handled) showError(form, alertNode, error.message);
          else alertNode.hidden = true;
        });
    });
  }

  function initRegister() {
    var form = $("#register-form");
    if (!form) return;
    var alertNode = $("#register-error");
    var submit = $("#register-submit");

    if (API.isAuthenticated()) {
      window.location.replace(safeNext() || "/dashboard/");
      return;
    }

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      alertNode.hidden = true;
      UI.setBusy(submit, true);

      var payload = {
        username: form.username.value.trim(),
        email: form.email.value.trim(),
        password: form.password.value,
        confirm_password: form.confirm_password.value
      };

      // Client-side check for an instant message; the server validates too.
      if (payload.password !== payload.confirm_password) {
        UI.setBusy(submit, false);
        UI.applyFieldErrors(form, { confirm_password: ["Passwords do not match."] });
        return;
      }

      API.register(payload)
        .then(function () {
          return API.login({ username: payload.username, password: payload.password });
        })
        .then(function (data) {
          API.setToken(data.token);
          API.setUser(data.user);
          UI.toast("Account created. Welcome to RecipeHub!", "success");
          window.location.href = safeNext() || "/dashboard/";
        })
        .catch(function (error) {
          UI.setBusy(submit, false);
          var handled = UI.applyFieldErrors(form, error.data);
          if (!handled) showError(form, alertNode, error.message);
          else alertNode.hidden = true;
        });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initPasswordToggles();
    initLogin();
    initRegister();
  });
})();
