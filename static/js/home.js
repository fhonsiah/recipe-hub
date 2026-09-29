/** RecipeHub — home page. */
(function () {
  "use strict";

  var API = window.API, UI = window.UI, $ = UI.$, el = UI.el, clear = UI.clear;

  function loadFeatured() {
    var grid = $("#featured-grid");
    if (!grid) return;
    UI.renderSkeletons(grid, 3);
    API.recipes({ page_size: 3, ordering: "-created_at" })
      .then(function (data) {
        var results = data.results || data;
        if (!UI.renderCards(grid, results)) {
          UI.renderEmpty(grid, { icon: "\u0001F372", title: "No recipes yet", message: "Be the first to publish one." });
        }
      })
      .catch(function (error) {
        UI.renderEmpty(grid, { icon: "!", title: "Could not load recipes", message: error.message });
      });
  }

  function loadLatest() {
    var grid = $("#latest-grid");
    if (!grid) return;
    UI.renderSkeletons(grid, 6);
    API.recipes({ page_size: 6, ordering: "-created_at", page: 1 })
      .then(function (data) {
        var results = data.results || data;
        if (!UI.renderCards(grid, results)) {
          UI.renderEmpty(grid, { icon: "\u0001F330", title: "Nothing published yet", message: "Check back soon or add the first recipe yourself." });
        }
      })
      .catch(function (error) {
        UI.renderEmpty(grid, { icon: "!", title: "Could not load recipes", message: error.message });
      });
  }

  function loadCategories() {
    var grid = $("#category-grid");
    if (!grid) return;
    API.categories()
      .then(function (categories) {
        clear(grid);
        if (!categories.length) return;
        categories.forEach(function (category) {
          grid.appendChild(el("a", { class: "category-card", href: "/recipes/?category=" + category.id }, [
            el("span", { class: "cat-emoji", "aria-hidden": "true", text: UI.categoryEmoji(category.name) }),
            el("h3", { text: category.name }),
            el("span", { text: category.recipe_count + (category.recipe_count === 1 ? " recipe" : " recipes") })
          ]));
        });
        var countNode = $("#stat-categories");
        if (countNode) countNode.textContent = String(categories.length);
      })
      .catch(function () { clear(grid); });
  }

  function loadStats() {
    API.recipes({ page_size: 1 })
      .then(function (data) {
        var node = $("#stat-recipes");
        if (node && data && typeof data.count === "number") node.textContent = String(data.count);
      })
      .catch(function () { /* the hero stats are decorative */ });
  }

  document.addEventListener("DOMContentLoaded", function () {
    loadStats();
    loadCategories();
    loadFeatured();
    loadLatest();
  });
})();
