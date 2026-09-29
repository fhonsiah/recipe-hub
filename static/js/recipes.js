/** RecipeHub — recipe listing: filters, search, sorting, pagination. */
(function () {
  "use strict";

  var API = window.API, UI = window.UI, $ = UI.$, $$ = UI.$$, el = UI.el, clear = UI.clear;

  var form = $("#filter-panel");
  var grid = $("#recipe-grid");
  var pagination = $("#pagination");
  var resultCount = $("#result-count");
  var activeFilters = $("#active-filters");
  var searchForm = $("#listing-search");
  var searchInput = $("#search-input");

  var TOTAL_TIME_CHOICES = { "15": 15, "30": 30, "60": 60, "120": 120 };
  var filterToggle = $("#filter-toggle");

  /** Read the form into API query params. */
  function readParams() {
    var data = new FormData(form);
    var params = {};

    var difficulty = data.getAll("difficulty");
    if (difficulty.length) params.difficulty = difficulty;

    var categories = data.getAll("category");
    if (categories.length) params.category = categories;

    var cuisines = data.getAll("cuisine");
    if (cuisines.length) params.cuisine = cuisines;

    var maxTime = TOTAL_TIME_CHOICES[data.get("max_time")];
    if (maxTime) params.total_time = maxTime;

    var ordering = data.get("ordering");
    if (ordering) params.ordering = ordering;

    return params;
  }

  function currentQuery() {
    var params = new URLSearchParams(window.location.search);
    return {
      q: params.get("q") || "",
      author: params.get("author") || "",
      category: params.get("category") || "",
      difficulty: params.get("difficulty") || ""
    };
  }

  function syncFormFromUrl() {
    var query = currentQuery();
    if (searchInput) searchInput.value = query.q;
    if (!form) return;

    if (query.difficulty) {
      var box = form.querySelector('input[name="difficulty"][value="' + query.difficulty + '"]');
      if (box) box.checked = true;
    }
    if (query.category) {
      // The category list is loaded asynchronously; it checks itself once ready.
      document.dispatchEvent(new CustomEvent("recipehub:pending-category", { detail: query.category }));
    }
  }

  /** Fetch recipes for the current filters and page. */
  function load(page) {
    var params = readParams();
    var query = currentQuery();

    if (query.q) params.search = query.q;
    if (query.author) params.author__username = query.author;
    if (page) params.page = page;

    UI.renderSkeletons(grid, 9);
    resultCount.textContent = "Loading recipes…";
    clear(pagination);

    API.recipes(params)
      .then(function (data) {
        var results = data.results || [];
        if (!UI.renderCards(grid, results)) {
          UI.renderEmpty(grid, {
            icon: "\u0001F957",
            title: "No recipes match those filters",
            message: "Try removing a filter or searching for something broader.",
            actionHref: "/recipes/",
            actionLabel: "Reset the listing"
          });
          resultCount.textContent = "No recipes found";
        } else {
          var total = typeof data.count === "number" ? data.count : results.length;
          resultCount.textContent = total + (total === 1 ? " recipe" : " recipes") + (query.q ? " for “" + query.q + "”" : "");
          renderPagination(data);
        }
        renderActiveChips(params, query);
      })
      .catch(function (error) {
        UI.renderEmpty(grid, { icon: "!", title: "Could not load recipes", message: error.message });
        resultCount.textContent = "Error";
      });
  }

  function renderActiveChips(params, query) {
    if (!activeFilters) return;
    clear(activeFilters);

    var chips = [];
    (params.difficulty || []).forEach(function (value) {
      chips.push({ label: "Difficulty: " + value, key: "difficulty", value: value });
    });
    (params.category || []).forEach(function (value) {
      chips.push({ label: "Category #" + value, key: "category", value: value });
    });
    (params.cuisine || []).forEach(function (value) {
      chips.push({ label: "Cuisine: " + value, key: "cuisine", value: value });
    });
    if (params.total_time) {
      chips.push({ label: "Under " + UI.formatMinutes(params.total_time), key: "max_time", value: "" });
    }
    if (query.q) chips.push({ label: "Search: " + query.q, key: "q", value: query.q });
    if (query.author) chips.push({ label: "By " + query.author, key: "author", value: query.author });

    chips.forEach(function (chip) {
      var node = el("span", { class: "chip" }, [
        el("span", { text: chip.label }),
        el("button", {
          type: "button",
          "aria-label": "Remove filter: " + chip.label,
          html: '<svg width="12" height="12" viewBox="0 0 12 12"><path d="M3 3l6 6M9 3l-6 6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>',
          onclick: function () { removeChip(chip); }
        })
      ]);
      activeFilters.appendChild(node);
    });
  }

  function removeChip(chip) {
    if (chip.key === "q" || chip.key === "author") {
      var url = new URL(window.location.href);
      url.searchParams.delete(chip.key);
      window.history.pushState({}, "", url);
      window.location.reload();
      return;
    }
    if (chip.key === "max_time") form.querySelector('[name="max_time"]').value = "";
    else {
      var box = form.querySelector('input[name="' + chip.key + '"][value="' + chip.value + '"]');
      if (box) box.checked = false;
    }
    load();
  }

  function renderPagination(data) {
    clear(pagination);
    if (!data.count || !data.next) return;

    var current = data.current || 1;
    var totalPages = data.count ? Math.ceil(data.count / (data.results || [1]).length) : 1;
    if (totalPages <= 1) return;

    function pageButton(label, target, options) {
      options = options || {};
      return el("button", {
        type: "button",
        class: options.current ? "is-current" : "",
        disabled: !!options.disabled,
        "aria-current": options.current ? "page" : null,
        "aria-label": options.label || ("Go to page " + target),
        text: label,
        onclick: function () { load(target); window.scrollTo({ top: 0, behavior: "smooth" }); }
      });
    }

    pagination.appendChild(pageButton("‹", current - 1, { disabled: !data.previous, label: "Previous page" }));

    var pages = [1, totalPages];
    for (var p = current - 1; p <= current + 1; p++) {
      if (p > 1 && p < totalPages) pages.push(p);
    }
    pages.sort(function (a, b) { return a - b; });

    var previous = 0;
    pages.forEach(function (page) {
      if (page - previous > 1) {
        pagination.appendChild(el("span", { class: "ellipsis", text: "…" }));
      }
      pagination.appendChild(pageButton(String(page), page, { current: page === current }));
      previous = page;
    });

    pagination.appendChild(pageButton("›", current + 1, { disabled: !data.next, label: "Next page" }));
  }

  /* ---------- filter option loading ---------- */
  function loadCategoryOptions() {
    var container = $("#category-options");
    if (!container) return;
    API.categories()
      .then(function (categories) {
        clear(container);
        categories.forEach(function (category) {
          container.appendChild(el("label", { class: "check" }, [
            el("input", { type: "checkbox", name: "category", value: String(category.id) }),
            el("span", { text: category.name }),
            el("span", { class: "count", text: String(category.recipe_count) })
          ]));
        });
        // A category may have been requested in the URL before options existed.
        var pending = currentQuery().category;
        if (pending) {
          var target = container.querySelector('input[value="' + pending + '"]');
          if (target) target.checked = true;
        }
      })
      .catch(function () { clear(container); });
  }

  function loadCuisineOptions() {
    var container = $("#cuisine-options");
    if (!container) return;
    // There is no cuisine endpoint; offer a curated set and keep it in sync
    // with whatever the user types in the add-recipe form.
    var cuisines = ["American", "Chinese", "French", "Indian", "Italian", "Japanese", "Korean", "Lebanese", "Mexican", "Mediterranean", "Moroccan", "Spanish", "Thai", "Vietnamese"];
    clear(container);
    cuisines.forEach(function (cuisine) {
      container.appendChild(el("label", { class: "check" }, [
        el("input", { type: "checkbox", name: "cuisine", value: cuisine }),
        el("span", { text: cuisine })
      ]));
    });
  }

  /* ---------- wiring ---------- */
  document.addEventListener("DOMContentLoaded", function () {
    if (!form || !grid) return;

    loadCategoryOptions();
    loadCuisineOptions();
    syncFormFromUrl();
    load();

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      load();
      if (filterToggle) {
        filterToggle.setAttribute("aria-expanded", "false");
        form.classList.remove("is-open");
      }
    });

    form.addEventListener("reset", function () {
      window.setTimeout(function () { load(); }, 0);
    });

    if (searchForm) {
      searchForm.addEventListener("submit", function (event) {
        event.preventDefault();
        var value = searchInput.value.trim();
        var url = new URL(window.location.href);
        if (value) url.searchParams.set("q", value);
        else url.searchParams.delete("q");
        window.history.pushState({}, "", url);
        load();
      });
    }

    if (filterToggle) {
      filterToggle.addEventListener("click", function () {
        var open = form.classList.toggle("is-open");
        filterToggle.setAttribute("aria-expanded", open ? "true" : "false");
      });
    }

    window.addEventListener("popstate", function () { window.location.reload(); });
  });
})();
