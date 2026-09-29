/** RecipeHub — favorites page. */
(function () {
  "use strict";

  var API = window.API, UI = window.UI, $ = UI.$, el = UI.el, clear = UI.clear;

  var grid = $("#favorites-grid");
  var pagination = $("#pagination-favorites") || $("#favorites-pagination");
  var summary = $("#favorites-summary");

  function renderPagination(data) {
    if (!pagination) return;
    clear(pagination);
    var totalPages = data.count ? Math.ceil(data.count / (data.results || [1]).length) : 1;
    if (totalPages <= 1) return;

    var current = data.current || 1;
    function button(label, target, options) {
      options = options || {};
      return el("button", {
        type: "button",
        class: options.current ? "is-current" : "",
        disabled: !!options.disabled,
        text: label,
        "aria-label": options.label,
        onclick: function () { load(target); window.scrollTo({ top: 0, behavior: "smooth" }); }
      });
    }

    pagination.appendChild(button("\u2039", current - 1, { disabled: !data.previous, label: "Previous page" }));
    for (var page = 1; page <= totalPages; page++) {
      pagination.appendChild(button(String(page), page, { current: page === current, label: "Go to page " + page }));
    }
    pagination.appendChild(button("\u203A", current + 1, { disabled: !data.next, label: "Next page" }));
  }

  function load(page) {
    UI.renderSkeletons(grid, 6);
    if (summary) summary.textContent = "Loading your saved recipes…";

    API.favorites({ page_size: 12, page: page || 1 })
      .then(function (data) {
        var results = (data.results || []).map(function (entry) {
          var recipe = entry.recipe;
          recipe.favorite_id = entry.id;
          recipe.is_favorited = true;
          return recipe;
        });

        if (!UI.renderCards(grid, results)) {
          UI.renderEmpty(grid, {
            icon: "\u2764",
            title: "No favorites yet",
            message: "Tap the heart on any recipe and it will be waiting for you here.",
            actionHref: "/recipes/",
            actionLabel: "Browse recipes"
          });
          if (summary) summary.textContent = "Nothing saved yet.";
        } else {
          var total = typeof data.count === "number" ? data.count : results.length;
          if (summary) {
            summary.textContent = total + (total === 1 ? " recipe" : " recipes") + " saved to your collection.";
          }
          renderPagination(data);
        }
      })
      .catch(function (error) {
        UI.renderEmpty(grid, { icon: "!", title: "Could not load favorites", message: error.message });
        if (summary) summary.textContent = "Could not load your favorites.";
      });
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (!grid) return;
    load();
    // Un-hearting a card here should empty the list without a page reload.
    document.addEventListener("recipehub:favorite-change", function (event) {
      if (!event.detail.favorited) load();
    });
  });
})();
