/**
 * RecipeHub — API client.
 * Thin fetch wrapper: base URL, JSON encoding, auth header, error normalisation.
 */
(function (global) {
  "use strict";

  var BASE = "/api";
  var TOKEN_KEY = "recipehub.token";
  var USER_KEY = "recipehub.user";

  function getToken() {
    try { return localStorage.getItem(TOKEN_KEY); } catch (e) { return null; }
  }

  function setToken(token) {
    try {
      if (token) localStorage.setItem(TOKEN_KEY, token);
      else localStorage.removeItem(TOKEN_KEY);
    } catch (e) { /* storage unavailable (private mode) */ }
  }

  function getUser() {
    try {
      var raw = localStorage.getItem(USER_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) { return null; }
  }

  function setUser(user) {
    try {
      if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
      else localStorage.removeItem(USER_KEY);
    } catch (e) { /* ignore */ }
  }

  /** Error carrying the HTTP status and DRF field-error map. */
  function ApiError(message, status, data) {
    this.name = "ApiError";
    this.message = message;
    this.status = status;
    this.data = data || {};
  }
  ApiError.prototype = Object.create(Error.prototype);
  ApiError.prototype.constructor = ApiError;

  /** Turn a DRF error body into a readable sentence. */
  function describe(data, fallback) {
    if (!data) return fallback;
    if (typeof data === "string") return data;
    if (data.detail) return data.detail;
    var parts = [];
    Object.keys(data).forEach(function (key) {
      var value = data[key];
      if (Array.isArray(value)) {
        parts.push(value.join(" "));
      } else if (typeof value === "object" && value !== null) {
        parts.push(JSON.stringify(value));
      } else {
        parts.push(String(value));
      }
    });
    return parts.length ? parts.join(" ") : fallback;
  }

  function buildQuery(params) {
    if (!params) return "";
    var usp = new URLSearchParams();
    Object.keys(params).forEach(function (key) {
      var value = params[key];
      if (value === undefined || value === null || value === "") return;
      if (Array.isArray(value)) {
        if (!value.length) return;
        usp.set(key, value.join(","));
      } else {
        usp.set(key, value);
      }
    });
    var qs = usp.toString();
    return qs ? "?" + qs : "";
  }

  function request(path, options) {
    options = options || {};
    var url = BASE + path;
    var headers = options.headers || {};
    var isForm = options.body instanceof FormData;

    if (!isForm && options.body !== undefined) {
      headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(options.body);
    }
    var token = getToken();
    if (token) headers.Authorization = "Token " + token;

    return fetch(url, {
      method: options.method || "GET",
      headers: headers,
      body: options.body
    }).then(function (response) {
      if (response.status === 204) return null;

      var isJson = (response.headers.get("content-type") || "").indexOf("application/json") !== -1;
      return (isJson ? response.json() : response.text()).then(function (data) {
        if (!response.ok) {
          if (response.status === 401) {
            setToken(null);
            setUser(null);
            global.dispatchEvent(new CustomEvent("recipehub:unauthorized"));
          }
          throw new ApiError(describe(data, "Request failed."), response.status, data);
        }
        return data;
      });
    }, function () {
      throw new ApiError("Network error. Check that the server is running.", 0, {});
    });
  }

  var api = {
    ApiError: ApiError,
    getToken: getToken,
    setToken: setToken,
    getUser: getUser,
    setUser: setUser,
    isAuthenticated: function () { return !!getToken(); },

    /* ---------- auth ---------- */
    register: function (data) { return request("/auth/register/", { method: "POST", body: data }); },
    login: function (data) { return request("/auth/login/", { method: "POST", body: data }); },
    logout: function () { return request("/auth/logout/", { method: "POST" }); },
    currentUser: function () { return request("/auth/user/"); },

    /* ---------- meta ---------- */
    categories: function (params) { return request("/categories/" + buildQuery(params)); },

    /* ---------- recipes ---------- */
    recipes: function (params) { return request("/recipes/" + buildQuery(params)); },
    recipe: function (id) { return request("/recipes/" + id + "/"); },
    relatedRecipes: function (id) { return request("/recipes/" + id + "/related/"); },
    myRecipes: function (params) { return request("/recipes/my_recipes/" + buildQuery(params)); },
    createRecipe: function (data) { return request("/recipes/", { method: "POST", body: data }); },
    updateRecipe: function (id, data) { return request("/recipes/" + id + "/", { method: "PATCH", body: data }); },
    deleteRecipe: function (id) { return request("/recipes/" + id + "/", { method: "DELETE" }); },

    /* ---------- favorites ---------- */
    favorites: function (params) { return request("/favorites/" + buildQuery(params)); },
    addFavorite: function (recipeId) { return request("/favorites/", { method: "POST", body: { recipe_id: recipeId } }); },
    removeFavorite: function (id) { return request("/favorites/" + id + "/", { method: "DELETE" }); }
  };

  global.API = api;
})(window);
