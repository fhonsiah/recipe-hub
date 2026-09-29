/** RecipeHub — recipe detail page. */
(function () {
  "use strict";

  var API = window.API, UI = window.UI, $ = UI.$, el = UI.el, clear = UI.clear;
  var root = $("#detail-root");

  function recipeId() {
    var match = window.location.pathname.match(/\/recipes\/(\d+)\/?/);
    return match ? Number(match[1]) : null;
  }

  function statBox(label, value) {
    return el("div", { class: "stat" }, [
      el("span", { class: "stat-label", text: label }),
      el("span", { class: "stat-value", text: value })
    ]);
  }

  function favoriteButton(recipe) {
    var button = el("button", {
      type: "button",
      class: "btn btn-outline btn-block" + (recipe.is_favorited ? " is-active" : ""),
      "data-fav": recipe.id,
      "data-fav-entry": recipe.favorite_id || "",
      "aria-pressed": recipe.is_favorited ? "true" : "false",
      html: '<svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20.5l-1.4-1.3C5.6 14.7 2.5 11.9 2.5 8.6 2.5 6 4.5 4 7.1 4c1.5 0 2.9.7 3.9 1.8C12 4.7 13.4 4 14.9 4c2.6 0 4.6 2 4.6 4.6 0 3.3-3.1 6.1-8.1 10.6L12 20.5z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></svg> <span></span>'
    });
    $("span", button).textContent = recipe.is_favorited
      ? "Saved (" + recipe.favorited_count + ")"
      : "Save to favorites (" + recipe.favorited_count + ")";
    return button;
  }

  function renderIngredients(ingredients) {
    if (!ingredients || !ingredients.length) {
      return el("p", { class: "muted", text: "No ingredients listed for this recipe." });
    }
    var list = el("div", { class: "ingredient-list" });
    ingredients.forEach(function (ingredient) {
      list.appendChild(el("div", { class: "ingredient-row" }, [
        el("span", { class: "ingredient-qty", text: (UI.formatQuantity(ingredient.quantity) + " " + (ingredient.unit || "")).trim() }),
        el("span", { class: "ingredient-name", text: ingredient.name }),
        ingredient.optional ? el("span", { class: "badge optional-tag", text: "optional" }) : null
      ]));
    });
    return list;
  }

  function renderInstructions(instructions) {
    if (!instructions || !instructions.length) {
      return el("p", { class: "muted", text: "No preparation steps were provided." });
    }
    var steps = el("div", { class: "steps" });
    instructions.forEach(function (instruction) {
      steps.appendChild(el("div", { class: "step" }, [
        el("span", { class: "step-number", "aria-hidden": "true" }),
        el("p", { text: instruction.description })
      ]));
    });
    return steps;
  }

  function renderImage(recipe) {
    if (recipe.image) {
      return el("img", { class: "detail-image", src: recipe.image, alt: recipe.title });
    }
    var node = el("div", { class: "detail-image", style: "display:grid;place-items:center;font-size:3rem" });
    node.style.background = UI.placeholderArt(recipe.title);
    node.textContent = UI.categoryEmoji(recipe.category ? recipe.category.name : "");
    return node;
  }

  function render(recipe) {
    document.title = recipe.title + " — RecipeHub";
    clear(root);

    var authorName = recipe.author ? recipe.author.username : "Unknown";
    var categoryName = recipe.category ? recipe.category.name : null;
    var total = (recipe.preparation_time || 0) + (recipe.cooking_time || 0);

    var badges = el("div", { class: "detail-badges" }, [
      categoryName ? el("span", { class: "badge badge-brand", text: categoryName }) : null,
      recipe.cuisine ? el("span", { class: "badge", text: recipe.cuisine }) : null,
      el("span", { class: "badge " + (UI.DIFFICULTY_CLASS[recipe.difficulty] || ""), text: recipe.difficulty }),
      recipe.published ? null : el("span", { class: "badge badge-draft badge-dot", text: "Draft — only you can see this" })
    ]);

    var left = el("div", {}, [
      renderImage(recipe),
      el("div", { class: "detail-body", style: "padding-top:1.5rem" }, [
        badges,
        el("h1", { class: "detail-title", text: recipe.title }),
        el("p", { class: "detail-desc", text: recipe.description }),
        el("div", { class: "detail-byline" }, [
          el("a", { class: "recipe-author", href: "/recipes/?author=" + encodeURIComponent(authorName) }, [
            el("span", { class: "avatar", text: UI.initials(authorName) }),
            el("span", {}, [
              el("strong", { text: authorName }),
              el("span", { class: "muted small", style: "display:block", text: "Published " + UI.formatDate(recipe.created_at) })
            ])
          ])
        ]),
        el("div", { class: "stat-row" }, [
          statBox("Prep", UI.formatMinutes(recipe.preparation_time)),
          statBox("Cook", UI.formatMinutes(recipe.cooking_time)),
          statBox("Total", UI.formatMinutes(total)),
          statBox("Serves", String(recipe.servings)),
          statBox("Likes", String(recipe.favorited_count))
        ]),
        el("h2", { text: "Ingredients" }),
        renderIngredients(recipe.ingredients),
        el("h2", { style: "margin-top:2.25rem", text: "Method" }),
        renderInstructions(recipe.instructions)
      ])
    ]);

    var sideActions = el("div", { class: "side-actions" }, [favoriteButton(recipe)]);
    if (recipe.can_edit) {
      sideActions.appendChild(el("a", {
        class: "btn btn-primary btn-block",
        href: "/recipes/" + recipe.id + "/edit/",
        text: recipe.is_owner ? "Edit recipe" : "Edit as moderator"
      }));
      if (!recipe.is_owner) {
        sideActions.appendChild(el("p", {
          class: "hint",
          text: "You can edit this recipe because you moderate. The author will see the change."
        }));
      }
      sideActions.appendChild(el("a", { class: "btn btn-ghost btn-block", href: "/dashboard/", text: "Manage in dashboard" }));
    } else if (API.isAuthenticated()) {
      sideActions.appendChild(el("a", { class: "btn btn-primary btn-block", href: "/recipes/add/", text: "+ Add your own recipe" }));
    } else {
      sideActions.appendChild(el("a", { class: "btn btn-primary btn-block", href: "/login/?next=" + encodeURIComponent(location.pathname), text: "Log in to save" }));
      sideActions.appendChild(el("a", { class: "btn btn-outline btn-block", href: "/register/", text: "Create an account" }));
    }

    var aside = el("aside", {}, [
      el("div", { class: "side-card" }, [
        el("h3", { text: "About this recipe" }),
        el("div", { class: "side-actions" }, sideActions.children.length ? Array.prototype.slice.call(sideActions.children) : [])
      ])
    ]);

    if (recipe.updated_at && recipe.updated_at !== recipe.created_at) {
      aside.appendChild(el("div", { class: "side-card" }, [
        el("h3", { text: "Last updated" }),
        el("p", { class: "muted small", text: UI.formatDate(recipe.updated_at) })
      ]));
    }

    var page = el("div", {}, [
      el("div", { class: "container" }, [
        el("nav", { class: "breadcrumbs", style: "padding-top:1.5rem", "aria-label": "Breadcrumb" }, [
          el("a", { href: "/", text: "Home" }), " / ",
          el("a", { href: "/recipes/", text: "Recipes" }), " / ",
          el("span", { "aria-current": "page", text: recipe.title })
        ])
      ]),
      el("div", { class: "detail-hero" }, [
        el("div", { class: "container detail-grid" }, [left, aside])
      ])
    ]);

    if (recipe.related_recipes && recipe.related_recipes.length) {
      var relatedGrid = el("div", { class: "related-grid" });
      recipe.related_recipes.forEach(function (item) {
        relatedGrid.appendChild(UI.recipeCard(item));
      });
      page.appendChild(el("section", { class: "container section" }, [
        el("div", { class: "section-head" }, el("div", {}, [
          el("span", { class: "eyebrow", text: "More like this" }),
          el("h2", { text: "Related recipes" })
        ])),
        relatedGrid
      ]));
    }

    root.appendChild(page);
    UI.bindFavoriteButtons(root);
  }

  function renderError(message) {
    clear(root);
    root.appendChild(el("div", { class: "container section" }, [
      el("div", { class: "empty-state" }, [
        el("div", { class: "empty-icon", text: "\u0001F373" }),
        el("h3", { text: "Recipe unavailable" }),
        el("p", { text: message }),
        el("a", { class: "btn btn-primary", href: "/recipes/", text: "Browse all recipes" })
      ])
    ]));
  }

  document.addEventListener("DOMContentLoaded", function () {
    var id = recipeId();
    if (!id) { renderError("That recipe link is not valid."); return; }

    API.recipe(id)
      .then(render)
      .catch(function (error) {
        if (error.status === 404) renderError("This recipe does not exist, or it is not published.");
        else renderError(error.message);
      });
  });
})();
