/** RecipeHub — add / edit recipe form with dynamic ingredient and step rows. */
(function () {
  "use strict";

  var API = window.API, UI = window.UI, $ = UI.$, $$ = UI.$$, el = UI.el;

  var form = $("#recipe-form");
  if (!form) return;

  var UNITS = ["g", "kg", "ml", "l", "tsp", "tbsp", "cup", "cups", "piece", "pieces", "clove", "cloves", "pinch", "handful", "to taste"];
  var CUISINES = ["American", "Chinese", "French", "Indian", "Italian", "Japanese", "Korean", "Lebanese", "Mexican", "Mediterranean", "Moroccan", "Spanish", "Thai", "Vietnamese"];

  var ingredientHost = $("#ingredient-rows");
  var instructionHost = $("#instruction-rows");
  var editId = (window.location.pathname.match(/\/recipes\/(\d+)\/edit\//) || [])[1];
  var editing = !!editId;

  /* ---------- dynamic rows ---------- */
  function ingredientRow(values) {
    values = values || {};
    var nameInput = el("input", { type: "text", placeholder: "Ingredient", value: values.name || "", "aria-label": "Ingredient name", class: "repeat-name" });
    var qtyInput = el("input", { type: "text", inputmode: "decimal", placeholder: "Qty", value: values.quantity === undefined ? "" : values.quantity, "aria-label": "Quantity" });
    var unitSelect = el("select", { "aria-label": "Unit" },
      [el("option", { value: "", text: "Unit" })].concat(UNITS.map(function (unit) {
        return el("option", { value: unit, text: unit, selected: values.unit === unit });
      }))
    );

    var remove = el("button", {
      type: "button", class: "row-remove", "aria-label": "Remove ingredient",
      html: '<svg width="14" height="14" viewBox="0 0 14 14"><path d="M3 3l8 8M11 3l-8 8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>'
    });
    remove.addEventListener("click", function () {
      if (ingredientHost.children.length <= 1) {
        UI.toast("A recipe needs at least one ingredient row.", "info");
        return;
      }
      row.remove();
    });

    return el("div", { class: "repeat-row" }, [
      el("div", {}, [el("label", { class: "row-label", text: "Ingredient" }), nameInput]),
      el("div", {}, [el("label", { class: "row-label", text: "Qty" }), qtyInput]),
      el("div", {}, [el("label", { class: "row-label", text: "Unit" }), unitSelect]),
      el("label", { class: "checkbox-row row-tail", style: "align-self:center;min-height:2.1rem" }, [
        el("input", { type: "checkbox", checked: !!values.optional }),
        el("span", { text: "optional" })
      ]),
      el("div", { class: "row-tail", style: "display:flex;align-items:center;gap:.5rem" }, [remove])
    ]);
  }

  function instructionRow(values) {
    values = values || {};
    var textarea = el("textarea", { placeholder: "Describe this step…", "aria-label": "Step description", rows: 2 }, values.description || "");
    var index = el("span", { class: "step-index" });
    var remove = el("button", { type: "button", class: "row-remove", "aria-label": "Remove step", html: '<svg width="14" height="14" viewBox="0 0 14 14"><path d="M3 3l8 8M11 3l-8 8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>' });

    var row = el("div", { class: "step-row" }, [index, textarea, remove]);
    row._indexNode = index;
    remove.addEventListener("click", function () {
      if (instructionHost.children.length <= 1) {
        UI.toast("A recipe needs at least one step.", "info");
        return;
      }
      row.remove();
      renumberSteps();
    });
    return row;
  }

  function renumberSteps() {
    Array.prototype.forEach.call(instructionHost.children, function (row, index) {
      row._indexNode.textContent = String(index + 1);
    });
  }

  function addIngredient(values) { ingredientHost.appendChild(ingredientRow(values)); }
  function addInstruction(values) {
    instructionHost.appendChild(instructionRow(values));
    renumberSteps();
  }

  /* ---------- helpers ---------- */
  function readIngredients() {
    return Array.prototype.map.call(ingredientHost.querySelectorAll(".repeat-row"), function (row) {
      var name = row.querySelector("input[type='text']").value.trim();
      if (!name) return null;
      var qty = row.querySelectorAll("input[type='text']")[1].value.trim();
      var unit = row.querySelector("select").value;
      return {
        name: name,
        quantity: qty === "" ? "0" : qty,
        unit: unit || "to taste",
        optional: row.querySelector("input[type='checkbox']").checked
      };
    }).filter(Boolean);
  }

  function readInstructions() {
    return Array.prototype.map.call(instructionHost.querySelectorAll("textarea"), function (area) {
      return area.value.trim();
    }).filter(Boolean);
  }

  function updateTotalTime() {
    var prep = Number($("#preparation_time").value) || 0;
    var cook = Number($("#cooking_time").value) || 0;
    $("#total-time-hint").textContent = "Total time: " + UI.formatMinutes(prep + cook);
  }

  /* ---------- load options ---------- */
  function loadCategories() {
    return API.categories().then(function (categories) {
      var select = $("#category");
      categories.forEach(function (category) {
        select.appendChild(el("option", { value: String(category.id), text: category.name }));
      });
    }).catch(function () { /* the field stays optional */ });
  }

  function loadCuisineDatalist() {
    var list = $("#cuisine-list");
    CUISINES.forEach(function (cuisine) {
      list.appendChild(el("option", { value: cuisine }));
    });
  }

  /* ---------- edit mode ---------- */
  function populate(recipe) {
    $("#title").value = recipe.title;
    $("#description").value = recipe.description;
    if (recipe.category) $("#category").value = String(recipe.category.id);
    $("#cuisine").value = recipe.cuisine || "";
    $("#preparation_time").value = recipe.preparation_time;
    $("#cooking_time").value = recipe.cooking_time;
    $("#servings").value = recipe.servings;
    $("#difficulty").value = recipe.difficulty;
    $("#published").checked = !!recipe.published;

    ingredientHost.innerHTML = "";
    (recipe.ingredients || []).forEach(function (ingredient) {
      addIngredient({
        name: ingredient.name,
        quantity: UI.formatQuantity(ingredient.quantity),
        unit: ingredient.unit,
        optional: ingredient.optional
      });
    });
    if (!recipe.ingredients || !recipe.ingredients.length) addIngredient();

    instructionHost.innerHTML = "";
    (recipe.instructions || []).forEach(function (instruction) {
      addInstruction({ description: instruction.description });
    });
    if (!recipe.instructions || !recipe.instructions.length) addInstruction();

    if (recipe.image) setPreview(recipe.image);
    updateTotalTime();
    updateDescriptionCount();
  }

  function setPreview(src) {
    var preview = $("#image-preview");
    preview.innerHTML = "";
    preview.appendChild(el("img", { src: src, alt: "Selected recipe image" }));
  }

  function updateDescriptionCount() {
    var length = $("#description").value.trim().length;
    $("#description-count").textContent = length + (length === 1 ? " character" : " characters");
  }

  /* ---------- submit ---------- */
  function submit(event) {
    event.preventDefault();
    var alertNode = $("#form-error");
    var submitButton = $("#submit-recipe");
    alertNode.hidden = true;
    UI.setBusy(submitButton, true);

    var data = new FormData();
    data.append("title", $("#title").value.trim());
    data.append("description", $("#description").value.trim());
    data.append("category", $("#category").value);
    data.append("cuisine", $("#cuisine").value.trim());
    data.append("preparation_time", $("#preparation_time").value || "0");
    data.append("cooking_time", $("#cooking_time").value || "0");
    data.append("servings", $("#servings").value || "1");
    data.append("difficulty", $("#difficulty").value);
    data.append("published", $("#published").checked ? "true" : "false");

    readIngredients().forEach(function (ingredient) {
      data.append("ingredients", JSON.stringify(ingredient));
    });
    readInstructions().forEach(function (step, index) {
      data.append("instructions", JSON.stringify({ step_number: index + 1, description: step }));
    });

    var file = $("#image").files[0];
    if (file) data.append("image", file);

    var call = editing ? API.updateRecipe(editId, data) : API.createRecipe(data);
    call
      .then(function (recipe) {
        UI.toast(editing ? "Recipe updated." : "Recipe published.", "success");
        window.location.href = "/recipes/" + recipe.id + "/";
      })
      .catch(function (error) {
        UI.setBusy(submitButton, false);
        var handled = UI.applyFieldErrors(form, error.data);
        if (!handled || error.status === 500) {
          alertNode.textContent = error.message;
          alertNode.hidden = false;
        }
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
  }

  /* ---------- init ---------- */
  document.addEventListener("DOMContentLoaded", function () {
    if (editing) {
      $("#form-title").textContent = "Edit recipe";
      $("#form-subtitle").textContent = "Update the details, ingredients and steps for this recipe.";
      $("#submit-recipe").textContent = "Save changes";
      $("[data-breadcrumb-current]").textContent = "Edit recipe";
    }

    loadCuisineDatalist();
    loadCategories().then(function () {
      if (editing) {
        API.recipe(editId)
          .then(populate)
          .catch(function (error) {
            UI.toast(error.message, "error");
            if (error.status === 403) window.setTimeout(function () { window.location.href = "/dashboard/"; }, 1200);
          });
      }
    });

    if (!editing) { addIngredient(); addInstruction(); }

    $("#add-ingredient").addEventListener("click", function () {
      addIngredient();
      var rows = ingredientHost.querySelectorAll(".repeat-row");
      rows[rows.length - 1].querySelector("input").focus();
    });
    $("#add-instruction").addEventListener("click", function () {
      addInstruction();
      var areas = instructionHost.querySelectorAll("textarea");
      areas[areas.length - 1].focus();
    });

    $("#preparation_time").addEventListener("input", updateTotalTime);
    $("#cooking_time").addEventListener("input", updateTotalTime);
    $("#description").addEventListener("input", updateDescriptionCount);

    $("#image").addEventListener("change", function (event) {
      var file = event.target.files[0];
      if (!file) return;
      if (file.size > 5 * 1024 * 1024) {
        UI.toast("That image is larger than 5 MB. Please choose a smaller file.", "error");
        event.target.value = "";
        return;
      }
      var reader = new FileReader();
      reader.onload = function (e) { setPreview(e.target.result); };
      reader.readAsDataURL(file);
    });

    $("#cancel-recipe").addEventListener("click", function () {
      if (window.history.length > 1) window.history.back();
      else window.location.href = editing ? "/dashboard/" : "/recipes/";
    });

    form.addEventListener("submit", submit);
  });
})();
