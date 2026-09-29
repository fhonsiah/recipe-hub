/** RecipeHub — user dashboard. */
(function () {
  "use strict";

  var API = window.API, UI = window.UI, $ = UI.$, $$ = UI.$$, el = UI.el, clear = UI.clear;

  var tableWrap = $("#mine-table-wrap");
  var favGrid = $("#fav-grid");
  var deleteModal = $("#delete-modal");
  var pendingDeleteId = null;
  var pendingDeleteScope = "mine";

  /* ---------- my recipes ---------- */
  function recipeThumb(recipe) {
    if (recipe.image) return el("img", { class: "cell-thumb", src: recipe.image, alt: "", loading: "lazy" });
    var box = el("div", { class: "cell-thumb", style: "display:grid;place-items:center;font-size:1.1rem" });
    box.style.background = UI.placeholderArt(recipe.title);
    box.textContent = UI.categoryEmoji(recipe.category ? recipe.category.name : "");
    return box;
  }

  function renderTable(recipes) {
    clear(tableWrap);
    if (!recipes.length) {
      tableWrap.appendChild(el("div", { style: "padding:1.25rem" },
        el("div", { class: "empty-state" }, [
          el("div", { class: "empty-icon", text: "\u0001F372" }),
          el("h3", { text: "You have not published a recipe yet" }),
          el("p", { text: "Share a dish you cook often and it will show up here." }),
          el("a", { class: "btn btn-primary", href: "/recipes/add/", text: "+ Add your first recipe" })
        ])
      ));
      return;
    }

    var tbody = el("tbody");
    recipes.forEach(function (recipe) {
      var titleCell = el("td", { class: "cell-main", "data-label": "Recipe" },
        el("div", { class: "cell-title" }, [
          recipeThumb(recipe),
          el("div", {}, [
            el("a", { href: "/recipes/" + recipe.id + "/", style: "font-weight:600", text: recipe.title }),
            el("span", { class: "muted small", style: "display:block", text: recipe.category ? recipe.category.name : "Uncategorized" })
          ])
        ])
      );

      tbody.appendChild(el("tr", {}, [
        titleCell,
        el("td", { "data-label": "Status" },
          el("span", {
            class: "badge " + (recipe.published ? "badge-easy" : "badge-draft"),
            text: recipe.published ? "Published" : "Draft"
          })
        ),
        el("td", { "data-label": "Time" }, UI.formatMinutes((recipe.preparation_time || 0) + (recipe.cooking_time || 0))),
        el("td", { "data-label": "Added" }, UI.formatDate(recipe.created_at)),
        el("td", {}, el("div", { class: "row-actions" }, [
          el("a", { class: "btn btn-sm btn-outline", href: "/recipes/" + recipe.id + "/", text: "View" }),
          el("a", { class: "btn btn-sm", href: "/recipes/" + recipe.id + "/edit/", text: "Edit" }),
          el("button", {
            type: "button", class: "btn btn-sm btn-danger", text: "Delete",
            onclick: function () { openDelete(recipe); }
          })
        ]))
      ]));
    });

    tableWrap.appendChild(el("table", { class: "data-table" }, [
      el("thead", {}, el("tr", {}, [
        el("th", { text: "Recipe" }),
        el("th", { text: "Status" }),
        el("th", { text: "Time" }),
        el("th", { text: "Added" }),
        el("th", { text: "", style: "text-align:right" })
      ])),
      tbody
    ]));
  }

  function renderMyRecipes() {
    $("#mine-count").textContent = "Loading your recipes…";
    API.myRecipes({ page_size: 100, ordering: "-created_at" })
      .then(function (data) {
        var results = data.results || [];
        renderTable(results);
        $("#mine-count").textContent = results.length + (results.length === 1 ? " recipe" : " recipes") + " submitted";
        $("#stat-total").textContent = String(results.length);
        $("#stat-published").textContent = String(results.filter(function (r) { return r.published; }).length);
        return results;
      })
      .catch(function (error) {
        $("#mine-count").textContent = "Could not load your recipes.";
        UI.renderEmpty(tableWrap, { icon: "!", title: "Something went wrong", message: error.message });
      });
  }

  /* ---------- favorites ---------- */
  function renderFavorites() {
    UI.renderSkeletons(favGrid, 3);
    API.favorites({ page_size: 48 })
      .then(function (data) {
        var results = (data.results || []).map(function (entry) {
          // Carry the favorite id so the heart can be un-pressed from here.
          var recipe = entry.recipe;
          recipe.favorite_id = entry.id;
          recipe.is_favorited = true;
          return recipe;
        });
        if (!UI.renderCards(favGrid, results)) {
          UI.renderEmpty(favGrid, {
            icon: "\u2764",
            title: "No favorites yet",
            message: "Tap the heart on any recipe to save it here.",
            actionHref: "/recipes/",
            actionLabel: "Browse recipes"
          });
        }
        $("#fav-count").textContent = results.length === 1 ? "1 saved recipe" : results.length + " saved recipes";
        $("#stat-favorites").textContent = String(results.length);
        return results;
      })
      .catch(function (error) {
        UI.renderEmpty(favGrid, { icon: "!", title: "Could not load favorites", message: error.message });
      });
  }

  /* ---------- moderation ---------- */
  function renderModeration() {
    var wrap = $("#mod-table-wrap");
    UI.renderSkeletons(wrap, 3);
    // A moderator sees every recipe, drafts included, so unpublished work
    // can be reviewed and published or removed.
    API.recipes({ page_size: 100, ordering: "-created_at" })
      .then(function (data) {
        var results = data.results || [];
        clear(wrap);
        $("#mod-count").textContent = results.length ? "(" + results.length + ")" : "";

        if (!results.length) {
          wrap.appendChild(el("div", { style: "padding:1.25rem" },
            el("div", { class: "empty-state" }, [
              el("div", { class: "empty-icon", text: "\u0001F4CA" }),
              el("h3", { text: "Nothing to moderate" }),
              el("p", { text: "Recipes submitted by the community will appear here." })
            ])
          ));
          return;
        }

        var drafts = results.filter(function (r) { return !r.published; }).length;
        $("#mod-summary").textContent =
          results.length + " recipe(s) across the community, " + drafts + " awaiting review.";

        var tbody = el("tbody");
        results.forEach(function (recipe) {
          tbody.appendChild(el("tr", {}, [
            el("td", { class: "cell-main", "data-label": "Recipe" },
              el("div", { class: "cell-title" }, [
                recipeThumb(recipe),
                el("div", {}, [
                  el("a", { href: "/recipes/" + recipe.id + "/", style: "font-weight:600", text: recipe.title }),
                  el("span", {
                    class: "muted small", style: "display:block",
                    text: "by " + (recipe.author ? recipe.author.username : "unknown")
                  })
                ])
              ])),
            el("td", { "data-label": "Status" }, el("span", {
              class: "badge " + (recipe.published ? "badge-easy" : "badge-draft"),
              text: recipe.published ? "Published" : "Draft"
            })),
            el("td", { "data-label": "Added" }, UI.formatDate(recipe.created_at)),
            el("td", {}, el("div", { class: "row-actions" }, [
              el("a", { class: "btn btn-sm btn-outline", href: "/recipes/" + recipe.id + "/edit/", text: "Edit" }),
          el("button", {
            type: "button", class: "btn btn-sm btn-danger", text: "Remove",
            onclick: function () { openDelete(recipe, "moderation"); }
          })
            ]))
          ]));
        });

        wrap.appendChild(el("table", { class: "data-table" }, [
          el("thead", {}, el("tr", {}, [
            el("th", { text: "Recipe" }),
            el("th", { text: "Status" }),
            el("th", { text: "Added" }),
            el("th", { text: "", style: "text-align:right" })
          ])),
          tbody
        ]));
      })
      .catch(function (error) {
        UI.renderEmpty(wrap, { icon: "!", title: "Could not load recipes", message: error.message });
      });
  }

  /* ---------- delete ---------- */
  function openDelete(recipe, scope) {
    pendingDeleteId = recipe.id;
    pendingDeleteScope = scope || "mine";
    $("#delete-modal-text").textContent = 'Delete "' + recipe.title + '"? This permanently removes the recipe, its ingredients and its instructions.';
    deleteModal.hidden = false;
    $("#delete-confirm").focus();
  }

  function closeDelete() {
    deleteModal.hidden = true;
    pendingDeleteId = null;
  }

  function confirmDelete() {
    if (!pendingDeleteId) return;
    var button = $("#delete-confirm");
    var wasModeration = pendingDeleteScope === "moderation";
    UI.setBusy(button, true);
    API.deleteRecipe(pendingDeleteId)
      .then(function () {
        UI.toast("Recipe deleted.", "success");
        closeDelete();
        renderMyRecipes();
        if (wasModeration) renderModeration();
      })
      .catch(function (error) {
        UI.setBusy(button, false);
        UI.toast(error.message, "error");
        closeDelete();
      });
  }

  /* ---------- tabs ---------- */
  function initTabs() {
    $$("[data-tab]").forEach(function (button) {
      button.addEventListener("click", function () {
        $$("[data-tab]").forEach(function (b) {
          var active = b === button;
          b.classList.toggle("is-active", active);
          b.setAttribute("aria-selected", active ? "true" : "false");
        });
        $$("[role='tabpanel']").forEach(function (panel) { panel.hidden = true; });
        var target = $("#panel-" + button.dataset.tab);
        if (target) target.hidden = false;
        if (button.dataset.tab === "moderation") renderModeration();
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initTabs();
    renderMyRecipes();
    renderFavorites();
    var emailNode = $("[data-user-email]");
    var user = API.getUser();
    if (user && emailNode) emailNode.textContent = user.email || "Manage the recipes you have shared with the community.";

    if (deleteModal) {
      $("[data-modal-cancel]", deleteModal).addEventListener("click", closeDelete);
      $("#delete-confirm").addEventListener("click", confirmDelete);
      deleteModal.addEventListener("click", function (event) {
        if (event.target === deleteModal) closeDelete();
      });
      document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && !deleteModal.hidden) closeDelete();
      });
    }

    // Removing a favorite on this page updates the stat without a reload.
    document.addEventListener("recipehub:favorite-change", function (event) {
      if (!event.detail.favorited) renderFavorites();
    });
  });
})();
