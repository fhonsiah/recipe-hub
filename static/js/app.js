/**
 * RecipeHub — application bootstrap.
 * Auth state in the header/nav, mobile menu, user menu, logout,
 * and a guard for pages that require authentication.
 */
(function (global) {
  "use strict";

  var API = global.API;
  var UI = global.UI;
  var $ = UI.$;
  var $$ = UI.$$;

  function setAuthState(authenticated, user) {
    $$("[data-auth]").forEach(function (node) {
      var kind = node.dataset.auth;
      var show = kind === "user" ? authenticated : !authenticated;
      node.hidden = !show;
    });
    $$("[data-auth-only]").forEach(function (node) { node.hidden = !authenticated; });

    var role = user ? user.role || "cook" : null;
    $$("[data-role-only]").forEach(function (node) {
      node.hidden = !(authenticated && node.dataset.roleOnly === role);
    });
    $$("[data-role-badge]").forEach(function (node) {
      if (!role || role === "cook") { node.hidden = true; return; }
      node.hidden = false;
      node.textContent = user.role_label || role;
      node.classList.add("role-" + role);
    });

    if (authenticated && user) {
      var usernameNode = $("[data-username]");
      if (usernameNode) usernameNode.textContent = user.username;
      $$("[data-avatar]").forEach(function (node) { node.textContent = UI.initials(user.username); });
    }

    document.dispatchEvent(new CustomEvent("recipehub:auth-change", {
      detail: { authenticated: authenticated, user: user || null, role: role }
    }));
  }

  function markActiveNav() {
    var path = window.location.pathname;
    $$("[data-nav]").forEach(function (link) {
      var target = link.dataset.nav;
      var isActive =
        (target === "recipes" && path.indexOf("/recipes") === 0) ||
        (target === "dashboard" && path.indexOf("/dashboard") === 0) ||
        (target === "favorites" && path.indexOf("/favorites") === 0);
      link.classList.toggle("is-active", isActive);
    });
  }

  function initMobileNav() {
    var toggle = $(".nav-toggle");
    var nav = $("#primary-nav");
    if (!toggle || !nav) return;
    toggle.addEventListener("click", function () {
      var open = toggle.getAttribute("aria-expanded") === "true";
      toggle.setAttribute("aria-expanded", open ? "false" : "true");
      nav.classList.toggle("is-open", !open);
    });
  }

  function initUserMenu() {
    var menu = $(".user-menu");
    var trigger = $(".user-menu-trigger");
    if (!menu || !trigger) return;

    trigger.addEventListener("click", function (event) {
      event.stopPropagation();
      var open = menu.classList.toggle("is-open");
      trigger.setAttribute("aria-expanded", open ? "true" : "false");
    });
    document.addEventListener("click", function (event) {
      if (!menu.contains(event.target)) {
        menu.classList.remove("is-open");
        trigger.setAttribute("aria-expanded", "false");
      }
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        menu.classList.remove("is-open");
        trigger.setAttribute("aria-expanded", "false");
      }
    });

    var logout = $("[data-logout]", menu);
    if (logout) {
      logout.addEventListener("click", function () {
        UI.setBusy(logout, true);
        API.logout()
          .catch(function () { /* token may already be gone */ })
          .then(function () {
            API.setToken(null);
            API.setUser(null);
            setAuthState(false, null);
            window.location.href = "/";
          });
      });
    }
  }

  function initYear() {
    $$("[data-year]").forEach(function (node) {
      node.textContent = String(new Date().getFullYear());
    });
  }

  /**
   * Redirect to login when a page needs a session. Returns the user
   * (or null) once the current auth state is settled.
   */
  function requireAuth() {
    return new Promise(function (resolve) {
      if (!API.isAuthenticated()) {
        window.location.replace("/login/?next=" + encodeURIComponent(window.location.pathname + window.location.search));
        resolve(null);
        return;
      }
      var cached = API.getUser();
      if (cached) { setAuthState(true, cached); resolve(cached); return; }

      API.currentUser()
        .then(function (user) {
          API.setUser(user);
          setAuthState(true, user);
          resolve(user);
        })
        .catch(function () {
          API.setToken(null);
          API.setUser(null);
          setAuthState(false, null);
          window.location.replace("/login/?next=" + encodeURIComponent(window.location.pathname));
          resolve(null);
        });
    });
  }

  document.addEventListener("recipehub:unauthorized", function () {
    setAuthState(false, null);
  });

  document.addEventListener("DOMContentLoaded", function () {
    initMobileNav();
    initUserMenu();
    initYear();
    markActiveNav();

    var user = API.getUser();
    if (API.isAuthenticated() && user) {
      setAuthState(true, user);
    } else if (API.isAuthenticated()) {
      API.currentUser()
        .then(function (fresh) {
          API.setUser(fresh);
          setAuthState(true, fresh);
        })
        .catch(function () {
          API.setToken(null);
          API.setUser(null);
          setAuthState(false, null);
        });
    } else {
      setAuthState(false, null);
    }

    if (document.body.dataset.requiresAuth === "1") requireAuth();
  });

  global.App = { setAuthState: setAuthState, requireAuth: requireAuth };
})(window);
