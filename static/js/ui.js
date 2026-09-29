/**
 * RecipeHub — shared UI utilities.
 * DOM helpers, formatting, toasts, and the recipe-card renderer used by
 * the home page, listing, detail and favorites pages.
 */
(function (global) {
  "use strict";

  /* ---------- DOM ---------- */
  function $(selector, scope) { return (scope || document).querySelector(selector); }
  function $$(selector, scope) { return Array.prototype.slice.call((scope || document).querySelectorAll(selector)); }

  /** Create an element from a tag, attributes and children. */
  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (key) {
        var value = attrs[key];
        if (value === null || value === undefined || value === false) return;
        if (key === "class") node.className = value;
        else if (key === "text") node.textContent = value;
        else if (key === "html") node.innerHTML = value;
        else if (key.indexOf("on") === 0 && typeof value === "function") {
          node.addEventListener(key.slice(2).toLowerCase(), value);
        } else node.setAttribute(key, value === true ? "" : value);
      });
    }
    (Array.isArray(children) ? children : children ? [children] : []).forEach(function (child) {
      if (child === null || child === undefined || child === false) return;
      node.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
    });
    return node;
  }

  /** Escape a string for safe interpolation into innerHTML. */
  function escapeHtml(value) {
    if (value === null || value === undefined) return "";
    return String(value)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function clear(node) { while (node && node.firstChild) node.removeChild(node.firstChild); }

  /* ---------- formatting ---------- */
  function formatMinutes(total) {
    var minutes = Number(total) || 0;
    if (minutes < 60) return minutes + " min";
    var hours = Math.floor(minutes / 60);
    var rest = minutes % 60;
    return rest ? hours + "h " + rest + "m" : hours + "h";
  }

  function formatQuantity(value) {
    if (value === null || value === undefined || value === "") return "";
    var num = Number(value);
    if (isNaN(num)) return String(value);
    return Number.isInteger(num) ? String(num) : String(Math.round(num * 100) / 100);
  }

  function formatDate(iso) {
    if (!iso) return "";
    var date = new Date(iso);
    if (isNaN(date.getTime())) return "";
    return date.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  }

  function initials(name) {
    if (!name) return "?";
    return name.trim().charAt(0).toUpperCase() || "?";
  }

  /** Deterministic placeholder gradient per recipe, used when no image exists. */
  function placeholderArt(seed) {
    var text = String(seed || "recipe");
    var hash = 0;
    for (var i = 0; i < text.length; i++) hash = (hash * 31 + text.charCodeAt(i)) % 360;
    var hue = hash;
    return "linear-gradient(135deg, hsl(" + hue + ",72%,72%), hsl(" + ((hue + 40) % 360) + ",68%,52%))";
  }

  var CATEGORY_EMOJI = {
    breakfast: "\u2615", lunch: "\u0001F957", dinner: "\u0001F372",
    dessert: "\u0001F370", snack: "\u0001F36A", beverage: "\u0001F964",
    vegetarian: "\u0001F331", baking: "\u0001F35E", healthy: "\u0001F957"
  };

  function categoryEmoji(name) {
    if (!name) return "\u0001F372";
    var key = String(name).toLowerCase();
    var keys = Object.keys(CATEGORY_EMOJI);
    for (var i = 0; i < keys.length; i++) {
      if (key.indexOf(keys[i]) !== -1) return CATEGORY_EMOJI[keys[i]];
    }
    return "\u0001F372";
  }

  var DIFFICULTY_CLASS = { easy: "badge-easy", medium: "badge-medium", hard: "badge-hard" };

  /* ---------- toasts ---------- */
  var TOAST_ICONS = { success: "✓", error: "!", info: "i" };

  function toast(message, type) {
    var region = $("#toast-region");
    if (!region) return;
    var kind = type || "info";
    var node = el("div", { class: "toast toast-" + kind }, [
      el("span", { class: "toast-icon", text: TOAST_ICONS[kind] || "i" }),
      el("span", { text: message })
    ]);
    region.appendChild(node);
    window.setTimeout(function () {
      node.classList.add("is-leaving");
      window.setTimeout(function () { node.remove(); }, 220);
    }, 3600);
  }

  /* ---------- favorites ---------- */
  /**
   * Toggle a favorite for a recipe, updating every button bound to that id.
   * @param {number} recipeId
   * @param {HTMLElement} button the clicked button
   * @param {boolean} nextState
   */
  function toggleFavorite(recipeId, button, nextState) {
    if (!global.API.isAuthenticated()) {
      toast("Log in to save recipes to your favorites.", "info");
      window.setTimeout(function () { window.location.href = "/login/?next=" + encodeURIComponent(location.pathname); }, 900);
      return Promise.resolve(false);
    }

    var buttons = $$('[data-fav="' + recipeId + '"]');
    buttons.forEach(function (b) { b.classList.toggle("is-loading", true); });

    var call = nextState
      ? global.API.addFavorite(recipeId).then(function (data) { return { state: true, id: data ? data.id : null }; })
      : global.API.removeFavorite(Number(button.dataset.favEntry || 0)).then(function () { return { state: false, id: null }; });

    return call.then(function (result) {
      buttons.forEach(function (b) {
        b.classList.remove("is-loading");
        b.classList.toggle("is-active", result.state);
        b.setAttribute("aria-pressed", result.state ? "true" : "false");
        b.setAttribute("aria-label", (result.state ? "Remove from" : "Save to") + " favorites");
        if (result.state) {
          b.dataset.favEntry = result.id || "";
        } else {
          delete b.dataset.favEntry;
        }
      });
      if (button) {
        button.classList.remove("fav-btn-pop");
        void button.offsetWidth;
        button.classList.add("fav-btn-pop");
      }
      toast(result.state ? "Saved to your favorites." : "Removed from favorites.", "success");
      document.dispatchEvent(new CustomEvent("recipehub:favorite-change", {
        detail: { recipeId: recipeId, favorited: result.state }
      }));
      return result.state;
    }).catch(function (error) {
      buttons.forEach(function (b) { b.classList.remove("is-loading"); });
      toast(error.message, "error");
      return false;
    });
  }

  /** Wire every `[data-fav]` button inside a container. */
  function bindFavoriteButtons(container) {
    $$("[data-fav]", container).forEach(function (button) {
      if (button.dataset.bound) return;
      button.dataset.bound = "1";
      button.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();
        var active = button.classList.contains("is-active");
        var nextState = button.dataset.favExplicit ? button.dataset.favExplicit === "true" : !active;
        toggleFavorite(Number(button.dataset.fav), button, nextState);
      });
    });
  }

  /* ---------- recipe card ---------- */
  /**
   * Render a recipe card.
   * @param {object} recipe
   * @param {object} opts { showFavorite, showStatus }
   */
  function recipeCard(recipe, opts) {
    opts = opts || {};
    var showFavorite = opts.showFavorite !== false;
    var total = (recipe.preparation_time || 0) + (recipe.cooking_time || 0);
    var categoryName = recipe.category ? recipe.category.name : "Uncategorized";
    var authorName = recipe.author ? recipe.author.username : "Unknown";

    var media = el("div", { class: "recipe-card-media" });
    if (recipe.image) {
      media.appendChild(el("img", { src: recipe.image, alt: recipe.title, loading: "lazy" }));
    } else {
      media.style.background = placeholderArt(recipe.title);
      media.appendChild(el("div", {
        style: "display:grid;place-items:center;width:100%;height:100%;font-size:2.5rem",
        text: categoryEmoji(categoryName)
      }));
    }

    if (showFavorite) {
      var favBtn = el("button", {
        type: "button",
        class: "fav-btn fav-btn-media" + (recipe.is_favorited ? " is-active" : ""),
        "data-fav": recipe.id,
        "data-fav-entry": recipe.favorite_id || "",
        "aria-pressed": recipe.is_favorited ? "true" : "false",
        "aria-label": (recipe.is_favorited ? "Remove from" : "Save to") + " favorites"
      });
      favBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20.5l-1.4-1.3C5.6 14.7 2.5 11.9 2.5 8.6 2.5 6 4.5 4 7.1 4c1.5 0 2.9.7 3.9 1.8C12 4.7 13.4 4 14.9 4c2.6 0 4.6 2 4.6 4.6 0 3.3-3.1 6.1-8.1 10.6L12 20.5z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></svg>';
      media.appendChild(favBtn);
    }

    var meta = el("div", { class: "recipe-card-meta" }, [
      el("span", { text: "\u23F1 " + formatMinutes(total) }),
      el("span", { text: "\uD83E\uDD57 " + recipe.servings + " servings" }),
      el("span", { class: "badge " + (DIFFICULTY_CLASS[recipe.difficulty] || ""), text: recipe.difficulty })
    ]);

    var body = el("div", { class: "recipe-card-body" }, [
      el("h3", {}, el("a", { href: "/recipes/" + recipe.id + "/", text: recipe.title })),
      el("p", { class: "recipe-card-desc", text: recipe.description }),
      meta,
      el("div", { class: "recipe-card-footer" }, [
        el("a", { class: "recipe-author", href: "/recipes/?author=" + encodeURIComponent(authorName) }, [
          el("span", { class: "avatar", text: initials(authorName) }),
          el("span", { text: authorName })
        ]),
        el("span", { class: "badge badge-brand", text: categoryName })
      ])
    ]);

    if (opts.showStatus && recipe.published === false) {
      body.insertBefore(el("span", { class: "badge badge-draft badge-dot", text: "Draft" }), meta);
    }

    return el("article", { class: "recipe-card" }, [media, body]);
  }

  function renderCards(container, recipes, opts) {
    clear(container);
    if (!recipes || !recipes.length) return false;
    var fragment = document.createDocumentFragment();
    recipes.forEach(function (recipe) { fragment.appendChild(recipeCard(recipe, opts)); });
    container.appendChild(fragment);
    bindFavoriteButtons(container);
    return true;
  }

  function renderSkeletons(container, count) {
    clear(container);
    for (var i = 0; i < (count || 6); i++) {
      container.appendChild(el("div", { class: "skeleton-card" }, [
        el("div", { class: "skeleton sk-media" }),
        el("div", { class: "sk-body" }, [
          el("div", { class: "skeleton sk-line", style: "width:70%;height:1.1rem" }),
          el("div", { class: "skeleton sk-line" }),
          el("div", { class: "skeleton sk-line", style: "width:45%" })
        ])
      ]));
    }
  }

  function renderEmpty(container, options) {
    options = options || {};
    clear(container);
    container.appendChild(el("div", { class: "empty-state" }, [
      el("div", { class: "empty-icon", text: options.icon || "\u0001F957" }),
      el("h3", { text: options.title || "Nothing here yet" }),
      el("p", { text: options.message || "" }),
      options.actionHref ? el("a", { class: "btn btn-primary", href: options.actionHref, text: options.actionLabel || "Browse recipes" }) : null
    ]));
  }

  /* ---------- misc ---------- */
  function debounce(fn, wait) {
    var timer;
    return function () {
      var args = arguments, ctx = this;
      window.clearTimeout(timer);
      timer = window.setTimeout(function () { fn.apply(ctx, args); }, wait || 300);
    };
  }

  function setBusy(button, busy) {
    if (!button) return;
    button.classList.toggle("is-loading", !!busy);
    button.disabled = !!busy;
  }

  /** Render DRF field errors under their inputs. */
  function applyFieldErrors(form, data) {
    $$("[data-error-for]", form).forEach(function (node) { node.textContent = ""; });
    $$(".field", form).forEach(function (node) { node.classList.remove("has-error"); });
    if (!data || typeof data !== "object") return false;

    var found = false;
    Object.keys(data).forEach(function (key) {
      var target = $('[data-error-for="' + key + '"]', form);
      if (!target) return;
      var value = data[key];
      target.textContent = Array.isArray(value) ? value.join(" ") : String(value);
      var field = target.closest(".field");
      if (field) field.classList.add("has-error");
      found = true;
    });
    return found;
  }

  global.UI = {
    $: $, $$: $$, el: el, clear: clear, escapeHtml: escapeHtml,
    formatMinutes: formatMinutes, formatQuantity: formatQuantity, formatDate: formatDate,
    initials: initials, placeholderArt: placeholderArt, categoryEmoji: categoryEmoji,
    DIFFICULTY_CLASS: DIFFICULTY_CLASS,
    toast: toast, recipeCard: recipeCard, renderCards: renderCards,
    renderSkeletons: renderSkeletons, renderEmpty: renderEmpty,
    bindFavoriteButtons: bindFavoriteButtons, toggleFavorite: toggleFavorite,
    debounce: debounce, setBusy: setBusy, applyFieldErrors: applyFieldErrors
  };
})(window);
