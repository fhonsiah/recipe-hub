# RecipeHub

A full-stack recipe platform built as a portfolio project: **Django REST Framework** on the
backend, **vanilla HTML/CSS/JavaScript** on the frontend. No React, no Vue, no Bootstrap —
every pixel and every line of JavaScript in this repository is hand-written.

Guests can browse, search and filter recipes. Registered users can publish their own
recipes with images, ingredients and step-by-step instructions, and save favorites.

---

## Table of contents

- [Pages](#pages)
- [Tech stack](#tech-stack)
- [Features](#features)
- [Project structure](#project-structure)
- [Getting started](#getting-started)
- [Demo accounts](#demo-accounts)
- [Data model](#data-model)
- [API reference](#api-reference)
- [Frontend architecture](#frontend-architecture)
- [Testing](#testing)
- [Design decisions](#design-decisions)
- [Deployment](#deployment)
- [Future improvements](#future-improvements)

---

## Pages

| Page | Route |
| --- | --- |
| Home | `/` |
| Recipe listing with filters | `/recipes/` |
| Recipe detail | `/recipes/<id>/` |
| Log in / Register | `/login/`, `/register/` |
| Dashboard | `/dashboard/` |
| Add / edit recipe | `/recipes/add/`, `/recipes/<id>/edit/` |
| Favorites | `/favorites/` |

---

## Tech stack

### Frontend

| Technology | Role |
| --- | --- |
| HTML5 | Semantic page shells, one Django template per route |
| CSS3 | Custom design system — custom properties, fluid type with `clamp()`, CSS grid |
| Vanilla JavaScript (ES6+) | Modules, promises, classes-free IIFE scoping |
| Fetch API | Every request to the JSON API |
| Django templates | `{% static %}` and `{% url %}` only — no server-rendered data |

**No frontend framework, no CSS framework, no jQuery, no build step.** Files are served
straight from `static/`.

### Backend

| Technology | Role |
| --- | --- |
| Python 3 | Runtime |
| Django 4.2 | Web framework |
| Django REST Framework | JSON API, serializers, token auth |
| django-filter | Search, filtering, ordering |
| Pillow | Recipe and category image handling |
| SQLite | Local development |
| PostgreSQL | Production (`config/settings/prod.py`) |
| Token authentication | `Authorization: Token <key>` |
| WhiteNoise | Compressed, hashed static files in production |

### Tooling

Git, GitHub, VS Code, `venv`, `pip`, `requirements.txt`, `.env` with `python-dotenv`.

---

## Features

### For guests
- Browse, search and filter every published recipe
- Search across titles, descriptions, cuisines **and ingredient names**
- Filter by difficulty, category, cuisine and total time
- Sort by newest, oldest, title, or preparation/cooking time
- Paginated listings and a full recipe detail page with related recipes

### For registered users
- Register, log in, log out (token-based, persisted in `localStorage`)
- Personal dashboard with recipe counts and totals
- Add recipes with a dynamically repeating ingredient / step form
- Upload a recipe image with client-side size checking and preview
- Edit or delete **only your own** recipes
- Publish immediately or keep as a private draft
- Save and unsave favorites from any card, detail page or dashboard
- Pagination, skeleton loaders, toasts, and inline form validation

### Notable implementation details
- **Guest and author visibility**: unpublished recipes are invisible to everyone except
  their author, enforced in `RecipeViewSet.get_queryset()`.
- **Optimized queries**: `select_related` for authors/categories, `prefetch_related` for
  ingredients, instructions and favorites — favorite state is read from the prefetch
  cache rather than firing a query per row.
- **Total-time filtering** is done server-side with an annotation on
  `preparation_time + cooking_time`, not in JavaScript.

---

## Project structure

```
RecipeHub/
├── api/                        # Django app: models + JSON API
│   ├── models.py               # Category, Recipe, Ingredient, Instruction, Favorite
│   ├── roles.py                # RBAC: role constants, group -> permission map
│   ├── permissions.py          # RBAC-aware DRF permission classes
│   ├── serializers.py          # Read / write / favorite serializers
│   ├── views.py                # ViewSets, role-aware filtering, pagination
│   ├── urls.py                 # Router + auth endpoints
│   ├── admin.py                # Admin with autocomplete and filters
│   ├── tests.py                # 86 API and view tests
│   ├── migrations/
│   └── management/commands/
│       ├── seed_data.py        # Demo categories, users, recipes, role accounts
│       └── assign_role.py      # Inspect / assign / clear roles from the CLI
├── config/                     # Project configuration
│   ├── settings/
│   │   ├── base.py             # Shared settings
│   │   ├── dev.py              # SQLite (default)
│   │   └── prod.py             # PostgreSQL, HSTS, WhiteNoise
│   ├── urls.py
│   ├── asgi.py / wsgi.py
├── core/                       # Serves the HTML shells
│   ├── views.py
│   └── urls.py
├── templates/core/             # One template per page, extending base.html
│   ├── base.html
│   ├── home.html
│   ├── recipes.html
│   ├── recipe_detail.html
│   ├── recipe_form.html        # Shared by add + edit
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   └── favorites.html
├── static/
│   ├── css/styles.css          # The whole design system, hand-written
│   └── js/
│       ├── api.js              # Fetch wrapper, token storage, error handling
│       ├── ui.js               # DOM helpers, formatting, cards, toasts
│       ├── app.js              # Auth state, nav, user menu, route guards
│       ├── home.js
│       ├── recipes.js          # Filters, search, sorting, pagination
│       ├── recipe-detail.js
│       ├── recipe-form.js      # Dynamic ingredient / step rows
│       ├── dashboard.js        # Stats, tabs, delete modal
│       ├── favorites.js
│       └── auth.js             # Login and registration
├── media/                      # Uploaded images (git-ignored)
├── .env.example
├── requirements.txt
├── requirements-dev.txt
└── manage.py
```

---

## Getting started

### Prerequisites
- Python 3.9 or newer
- pip

### 1. Clone and create a virtual environment

```bash
git clone https://github.com/<your-username>/RecipeHub.git
cd RecipeHub

python -m venv venv
```

Activate it:

```bash
# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure the environment

```bash
cp .env.example .env      # macOS / Linux
copy .env.example .env    # Windows
```

For local development the defaults are fine. Generate a proper secret key with:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 4. Prepare the database

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py seed_data
```

`seed_data` is idempotent — re-running it will not duplicate anything. Pass `--flush` to
wipe the demo data and start over.

### 5. Create an admin account (optional)

```bash
python manage.py createsuperuser
```

### 6. Run the development server

```bash
python manage.py runserver
```

Open <http://127.0.0.1:8000/>.

---

## Demo accounts

See [Roles and credentials](#roles-and-credentials) above. `seed_data` creates four
cooks, one moderator (`editor`) and one admin (`chief`), all with the password
`recipehub123`.

You can also register a fresh account through the UI; new accounts default to the
**Cook** role.

---

## Roles and credentials

Access control is role-based. Roles are stored as Django auth **Groups** with real
**Permission** objects attached (see `api/roles.py`), so the role model is editable from
the Django admin rather than hard-coded in view logic.

| Role | Group | Permissions | Sees drafts | Edits others' recipes | Curates categories | Django admin |
| --- | --- | --- | --- | --- | --- | --- |
| **Guest** | — | read published | no | no | no | no |
| **Cook** | `Cooks` | `add_recipe`, `view_*` | own only | no | no | no |
| **Moderator** | `Moderators` | cook + `change_recipe`, `delete_recipe`, `*_category` | **all** | **yes** | **yes** | no |
| **Admin** | `Administrators` | all app permissions | **all** | **yes** | **yes** | **yes** |

`is_staff` / `is_superuser` are kept in sync with the `admin` role, and any staff or
superuser account is treated as an admin regardless of group membership.

### Demo accounts

`seed_data` creates one account per role. **Every account uses the password
`recipehub123`** — these are throwaway demo credentials; change or delete them before
deploying anywhere public.

| Username | Email | Role | What it demonstrates |
| --- | --- | --- | --- |
| *(not signed in)* | — | Guest | Browsing, searching, filtering |
| `mara` | mara@example.com | Cook | Owns recipes; sees her own drafts only |
| `tomas` | tomas@example.com | Cook | Cannot touch another cook's recipe |
| `aiko` | aiko@example.com | Cook | Same |
| `sam` | sam@example.com | Cook | Same |
| `editor` | editor@example.com | **Moderator** | Edits/removes anyone's recipe, sees every draft, curates categories |
| `chief` | chief@example.com | **Admin** | Everything above, plus `/admin/` |

To try it out: sign in as `tomas` and open a recipe owned by `mara` — the sidebar offers
no edit button and a `PATCH` returns `403`. Sign in as `editor` instead and the same
recipe offers **Edit as moderator**. The dashboard gains a third **Moderation** tab
listing every recipe in the community, drafts included.

The seed also creates two unpublished drafts (`[Needs review] …`) so the moderation
queue is not empty on a fresh database.

### Managing roles

```bash
python manage.py assign_role --list              # show every account and its role
python manage.py assign_role --sync              # create/resync groups + permissions
python manage.py assign_role tomas moderator     # promote
python manage.py assign_role chief cook          # demote (revokes superuser)
python manage.py assign_role mara --clear        # remove from all role groups
```

Roles can also be assigned from the Django admin under **Auth → Groups** and
**Auth → Users**.

### How enforcement works

- **Class level** — `RecipeViewSet.get_permissions()` picks a permission class per
  action: `CanCreateRecipe` for create, `IsAuthorOrModeratorOrReadOnly` for
  update/delete, `IsAuthenticatedOrReadOnly` for reads.
- **Object level** — `IsAuthorOrModeratorOrReadOnly.has_object_permission()` allows the
  author always, and anyone holding `api.change_recipe` / `api.delete_recipe` (i.e. a
  moderator or admin).
- **Visibility** — `RecipeViewSet.get_queryset()` returns everything to moderators and
  admins, `published=True | author=request.user` to cooks, and `published=True` to
  guests. Filtering at the queryset level means drafts cannot leak through the list,
  the detail endpoint or `related`.
- **Client signalling** — `UserSerializer` returns `role`, `role_label` and `is_staff`,
  and recipe detail returns `can_edit`, so the UI never offers an action the API will
  refuse. The UI hides controls for convenience only; the API is the boundary.

---

## Data model

```
User  (Django's built-in auth.User)
 └── 1:N ──> Recipe  (author)
 └── 1:N ──> Favorite

Category
 └── 1:N ──> Recipe  (category, nullable)

Recipe
 ├── 1:N ──> Ingredient
 └── 1:N ──> Instruction

Favorite (unique_together: user, recipe)
```

| Model | Fields |
| --- | --- |
| **Category** | `name` (unique), `description`, `image`, `created_at` |
| **Recipe** | `title`, `description`, `author`, `category`, `cuisine`, `preparation_time`, `cooking_time`, `servings`, `difficulty`, `image`, `created_at`, `updated_at`, `published` |
| **Ingredient** | `recipe`, `name`, `quantity`, `unit`, `optional` |
| **Instruction** | `recipe`, `step_number`, `description` |
| **Favorite** | `user`, `recipe`, `created_at` |

`Recipe` also exposes a `total_time` property (`preparation_time + cooking_time`) used in
the UI. Django's authentication system is used as-is; no custom user model.

---

## API reference

Base URL: `/api/`. All request and response bodies are JSON unless noted.

### Authentication

| Method | Endpoint | Auth | Description |
| --- | --- | --- | --- |
| `POST` | `/api/auth/register/` | No | Create an account. Returns `201`. |
| `POST` | `/api/auth/login/` | No | Returns `{ token, user }`. |
| `POST` | `/api/auth/logout/` | Yes | Deletes the current token. |
| `GET` | `/api/auth/user/` | Yes | The current user's profile. |

```jsonc
// POST /api/auth/register/
{
  "username": "newcook",
  "email": "newcook@example.com",
  "password": "strongpass123",
  "confirm_password": "strongpass123"
}

// POST /api/auth/login/  ->  200
{
  "token": "985fdebf8680a1c...",
  "user": {
    "id": 5,
    "username": "newcook",
    "email": "newcook@example.com",
    "role": "cook",
    "role_label": "Cook",
    "is_staff": false
  }
}
```

`role`, `role_label` and `is_staff` are returned by both `/api/auth/login/` and
`/api/auth/user/`, so the frontend can adapt its chrome to the caller's role.

Send the token on every authenticated request:

```
Authorization: Token 985fdebf8680a1c...
```

### Categories

| Method | Endpoint | Auth | Description |
| --- | --- | --- | --- |
| `GET` | `/api/categories/` | No | All categories, unpaginated, each with `recipe_count`. |
| `GET` | `/api/categories/<id>/` | No | A single category. |

Read-only for guests and cooks. Moderators and admins (`change_category` /
`delete_category`) may create, edit and remove categories; other roles get `403`.

### Recipes

| Method | Endpoint | Auth | Description |
| --- | --- | --- | --- |
| `GET` | `/api/recipes/` | No | Paginated list. Cooks also see their own drafts; moderators and admins see every recipe including drafts. |
| `POST` | `/api/recipes/` | Yes | Create a recipe with nested ingredients and instructions. |
| `GET` | `/api/recipes/<id>/` | No | Full detail including ingredients, instructions and related recipes. |
| `PATCH` | `/api/recipes/<id>/` | Author or moderator | Partial update. Omitted children are left untouched. |
| `PUT` | `/api/recipes/<id>/` | Author or moderator | Full update. |
| `DELETE` | `/api/recipes/<id>/` | Author or moderator | Deletes the recipe, its ingredients and its instructions. |
| `GET` | `/api/recipes/my_recipes/` | Yes | The current user's recipes, drafts included. |
| `GET` | `/api/recipes/<id>/related/` | No | Up to 4 recipes from the same category (or cuisine). |

**Query parameters for `GET /api/recipes/`**

| Parameter | Example | Notes |
| --- | --- | --- |
| `search` | `?search=curry` | Title, description, cuisine, ingredient names. |
| `difficulty` | `?difficulty=easy&difficulty=hard` | Repeat for any-of. |
| `category` | `?category=3` | Category id; repeatable. |
| `cuisine` | `?cuisine=Thai` | Case-insensitive partial match. |
| `author__username` | `?author__username=mara` | Exact. |
| `total_time` | `?total_time=30` | Upper bound on prep + cook, in minutes. |
| `ordering` | `?ordering=-created_at` | `created_at`, `preparation_time`, `cooking_time`, `title`, `total_minutes`. |
| `page` / `page_size` | `?page=2&page_size=24` | `page_size` maxes out at 48. |

```jsonc
// GET /api/recipes/?difficulty=easy&total_time=30
{
  "count": 6,
  "next": "http://.../api/recipes/?difficulty=easy&total_time=30&page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "title": "Charred Tomato Basil Pasta",
      "description": "Burst cherry tomatoes, plenty of basil...",
      "author": { "id": 1, "username": "mara", "email": "mara@example.com" },
      "category": { "id": 3, "name": "Dinner" },
      "cuisine": "Italian",
      "preparation_time": 10,
      "cooking_time": 20,
      "servings": 4,
      "difficulty": "easy",
      "image": null,
      "created_at": "2026-09-29T10:24:56.677972Z",
      "published": true,
      "is_favorited": true,
      "favorite_id": 14
    }
  ]
}
```

The detail endpoint adds `updated_at`, `ingredients`, `instructions`,
`favorited_count`, `is_owner`, `can_edit` and `related_recipes`. `is_owner` is true for
the author; `can_edit` is also true for a moderator or admin, and is what the frontend
uses to decide whether to offer an edit button.

**Creating or updating a recipe**

`ingredients` and `instructions` are write-only nested lists. Because the frontend
submits `multipart/form-data` (it may include an image), each child row is sent as one
JSON string. The API also accepts a single JSON array, and plain JSON bodies work as
expected.

```jsonc
// POST /api/recipes/  (Content-Type: application/json)
{
  "title": "Garlic Butter Shrimp",
  "description": "Fast, garlicky and impossible to get wrong.",
  "cuisine": "Spanish",
  "preparation_time": 10,
  "cooking_time": 10,
  "servings": 2,
  "difficulty": "easy",
  "category": 3,
  "published": true,
  "ingredients": [
    { "name": "Shrimp", "quantity": "400", "unit": "g", "optional": false }
  ],
  "instructions": [
    { "description": "Marinate the shrimp." }
  ]
}
```

With `multipart/form-data`, send the same nested rows as repeated fields:

```
ingredients={"name":"Shrimp","quantity":"400","unit":"g","optional":false}
ingredients={"name":"Garlic","quantity":"6","unit":"cloves","optional":true}
instructions={"description":"Marinate the shrimp."}
instructions={"description":"Sear until pink."}
image=<binary>
```

Notes:
- `step_number` is always reassigned server-side from the submitted order, so numbering
  can never drift out of sequence.
- A `PATCH` that omits `ingredients` or `instructions` leaves the existing rows alone;
  sending them replaces them wholesale.
- Creating a recipe requires at least one ingredient and one step.
- At least one ingredient and one step must be present; errors are returned per field.

### Favorites

| Method | Endpoint | Auth | Description |
| --- | --- | --- | --- |
| `GET` | `/api/favorites/` | Yes | The current user's favorites, paginated. |
| `POST` | `/api/favorites/` | Yes | `{"recipe_id": 3}`. Idempotent. |
| `DELETE` | `/api/favorites/<id>/` | Owner | Removes a favorite. |

`is_favorited` and `favorite_id` are included on recipe payloads when authenticated, so
the UI can toggle without a second request.

---

## Frontend architecture

### The shell/JSON split

Django's `core` app serves one HTML shell per route using `TemplateView`. The templates
contain structure and nothing else — no recipe data is rendered server-side. Each page
loads its own JavaScript module, which fetches from `/api/` and renders with the DOM API.

This keeps one code path for the data and avoids duplicating rendering logic between
Django templates and JavaScript.

### Module responsibilities

| File | Responsibility |
| --- | --- |
| `api.js` | `fetch` wrapper: base URL, JSON encoding, `Authorization` header, 401 handling that clears the stored token, and an `ApiError` that normalizes DRF's error shapes into a message plus a field-error map. |
| `ui.js` | `el()` element builder, formatters, the shared recipe-card renderer, skeleton and empty states, toasts, and favorite toggling. |
| `app.js` | Auth state in the header, mobile nav, user menu, logout, and `requireAuth()` for protected pages. |
| Page modules | One per page, each initializing on `DOMContentLoaded`. |

### State and events

Modules communicate through DOM events rather than a shared store:

- `recipehub:auth-change` — the header re-renders when login state changes.
- `recipehub:favorite-change` — the favorites and dashboard pages refresh in place when a
  heart is toggled.
- `recipehub:unauthorized` — a 401 anywhere clears the token and updates the header.

`localStorage` holds the token and a cached copy of the user profile, so a page load
renders the header correctly before any request is made.

### Progressive enhancement

- `prefers-reduced-motion` disables all animation and smooth scrolling.
- Every interactive control is a real `<button>` or `<a>` with `aria-pressed`,
  `aria-current` and `aria-expanded` where appropriate.
- Cards use skeleton placeholders while loading instead of layout-jumping spinners.
- Focus-visible outlines, a skip link, and labelled form errors are included throughout.
- `accept="image/jpeg,image/png,image/webp"` plus a 5 MB client-side size check.

---

## Testing

```bash
python manage.py test api
```

86 tests covering:

- **Auth** — registration validation (mismatched passwords, short passwords, duplicate
  emails), login, logout token invalidation, and the current-user endpoint.
- **Roles** — group creation and permission sync, idempotency, role resolution for
  guests / ungrouped users / staff, promotion and demotion (including superuser
  revocation), rejection of unknown roles, and the capability helpers.
- **Moderation** — a cook cannot update or delete another cook's recipe; a moderator
  and an admin can; a moderator sees every draft and can publish one; guests still
  cannot see drafts; `can_edit` reflects the caller's role; moderators still cannot
  touch another user's favorites.
- **Role reporting** — `role`, `role_label` and `is_staff` are returned by both
  `auth/user/` and the login response.
- **Recipe reads** — published-only visibility for guests, draft visibility for authors
  only, detail payload contents, search (including by ingredient, and a guard against
  duplicate rows), every filter, ordering, pagination, favorite state, and related recipes.
- **Recipe writes** — guest rejection, nested child creation, the repeated-JSON multipart
  path, required children, server-side step renumbering, child replacement on update,
  children surviving a partial update, image upload, and owner-only update/delete.
- **Favorites** — idempotent creation, rejection of unknown and non-public recipes,
  per-user isolation, and 404 when deleting someone else's favorite.
- **JSON serializability** — detail and related endpoints are rendered, not just
  inspected, so a leaked model or queryset fails the test.
- **Pages** — every HTML shell renders for guests and authenticated users.

---

## Design decisions

**Why the frontend is a JSON client, not server-rendered pages.**
The brief was to demonstrate the frontend as its own discipline. Rendering shells from
Django and building the UI in JavaScript keeps a single rendering path and makes the
API the real contract.

**Why token authentication.**
Tokens work from `fetch` without CSRF token juggling, which suits a stateless JSON
client. Session auth remains enabled so the Django admin works normally.

**Why roles live in Django Groups rather than a `role` column.**
A role column would duplicate the permission system and drift from it. Attaching real
`Permission` objects to Groups means the role model is visible and editable in the
Django admin, and `user.has_perm("api.change_recipe")` stays the single source of truth
that both the permission classes and the admin site agree on.

**Why `published` is enforced in `get_queryset()`.**
Filtering visibility at the queryset level means unpublished recipes cannot leak through
the list, the detail endpoint or `related` — not just hidden in the UI.

**Why favorite state comes from the prefetch cache.**
`Recipe.objects` prefetches `favorited_by`, so `is_favorited` and `favorite_id` are read
from memory instead of issuing one query per row.

**Why the total-time filter is server-side.**
An earlier version filtered preparation and cooking time in JavaScript, which silently
dropped slow-cook dishes. `RecipeFilter` annotates `total_minutes` and filters in SQL.

**Why nested children are write-only.**
`RecipeWriteSerializer` accepts `ingredients` and `instructions` and handles creation,
replacement and renumbering, while read serializers expose them as ordinary nested data.
A partial update that omits them leaves existing rows untouched.

---

## Deployment

The production settings module targets PostgreSQL, enforces HTTPS and serves static
files through WhiteNoise.

```bash
pip install -r requirements.txt
export DJANGO_SETTINGS_MODULE=config.settings.prod

python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

Required environment variables:

| Variable | Notes |
| --- | --- |
| `SECRET_KEY` | Generate a real one. |
| `DEBUG` | `False`. |
| `ALLOWED_HOSTS` | Comma-separated, e.g. `example.com,www.example.com`. |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` | PostgreSQL connection. |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated, e.g. `https://example.com`. |
| `SECURE_SSL_REDIRECT` | Set to `0` only if TLS terminates upstream. |
| `SECURE_HSTS_SECONDS` | Defaults to one year. |

> Uploaded media lives on the local filesystem. For a multi-instance deployment,
> point `DEFAULT_FILE_STORAGE` at S3 or another shared backend.

---

## Future improvements

- Rating and review comments on recipes
- Follow other cooks and see a personalized feed
- Nutritional information per ingredient
- A shopping-list generator built from a recipe's ingredients
- Email verification and password reset
- Django REST Framework browsable API in development
- CI running `manage.py test` on every push

---

## License

Released under the MIT License.

## Author

Built as a portfolio project demonstrating full-stack development with Django and
vanilla JavaScript.
