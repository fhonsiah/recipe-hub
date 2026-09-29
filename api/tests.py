"""API tests for the RecipeHub project.

Covers authentication, ownership rules, publication visibility, filtering,
search, pagination and the favorites endpoints.
"""
import io
import json

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from api.models import Category, Favorite, Ingredient, Instruction, Recipe
from api.roles import (
    ROLE_ADMIN,
    ROLE_COOK,
    ROLE_GUEST,
    ROLE_MODERATOR,
    assign_role,
    can_edit_recipe,
    ensure_groups,
    get_role,
)

User = get_user_model()


def png_upload(name="dish.png", size=(8, 8)):
    """A genuinely valid PNG produced by Pillow, so validation is exercised."""
    buffer = io.BytesIO()
    Image.new("RGB", size, (200, 120, 60)).save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


def make_recipe(author, **overrides):
    payload = {
        "title": "Test Pancakes",
        "description": "Fluffy butterscotch pancakes for testing.",
        "category": None,
        "cuisine": "American",
        "preparation_time": 10,
        "cooking_time": 15,
        "servings": 4,
        "difficulty": "easy",
        "published": True,
    }
    payload.update(overrides)
    recipe = Recipe.objects.create(author=author, **payload)
    Ingredient.objects.create(recipe=recipe, name="Flour", quantity=200, unit="g")
    Instruction.objects.create(recipe=recipe, step_number=1, description="Mix everything.")
    return recipe


def recipe_payload(**overrides):
    payload = {
        "title": "Garlic Butter Shrimp",
        "description": "Fast, garlicky and impossible to get wrong.",
        "cuisine": "Spanish",
        "preparation_time": 10,
        "cooking_time": 10,
        "servings": 2,
        "difficulty": "easy",
        "published": True,
        "ingredients": [
            {"name": "Shrimp", "quantity": "400", "unit": "g", "optional": False},
            {"name": "Garlic", "quantity": "6", "unit": "cloves", "optional": True},
        ],
        "instructions": [
            {"step_number": 1, "description": "Marinate the shrimp."},
            {"step_number": 2, "description": "Sear until pink."},
        ],
    }
    payload.update(overrides)
    return payload


class BaseAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.author = User.objects.create_user("mara", "mara@example.com", "recipehub123")
        self.other = User.objects.create_user("tomas", "tomas@example.com", "recipehub123")
        self.moderator = User.objects.create_user("editor", "editor@example.com", "recipehub123")
        self.admin = User.objects.create_user("chief", "chief@example.com", "recipehub123")
        self.category = Category.objects.create(name="Dinner", description="Evening meals")
        assign_role(self.author, ROLE_COOK)
        assign_role(self.other, ROLE_COOK)
        assign_role(self.moderator, ROLE_MODERATOR)
        assign_role(self.admin, ROLE_ADMIN)

    def auth(self, user):
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token.key)
        return token


class AuthTests(BaseAPITestCase):
    def test_register_creates_user_and_returns_201(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "newcook",
                "email": "newcook@example.com",
                "password": "strongpass123",
                "confirm_password": "strongpass123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="newcook").exists())
        self.assertTrue(Token.objects.filter(user__username="newcook").exists())

    def test_register_rejects_mismatched_passwords(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "newcook",
                "email": "newcook@example.com",
                "password": "strongpass123",
                "confirm_password": "different123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("confirm_password", response.data)

    def test_register_rejects_short_password(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "newcook",
                "email": "newcook@example.com",
                "password": "short",
                "confirm_password": "short",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_register_rejects_duplicate_email(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "another",
                "email": "MARA@example.com",
                "password": "strongpass123",
                "confirm_password": "strongpass123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_login_returns_token_and_user(self):
        response = self.client.post(
            reverse("login"), {"username": "mara", "password": "recipehub123"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)
        self.assertEqual(response.data["user"]["username"], "mara")

    def test_login_rejects_bad_credentials(self):
        response = self.client.post(
            reverse("login"), {"username": "mara", "password": "wrong"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout_invalidates_token(self):
        token = self.auth(self.author)
        response = self.client.post(reverse("logout"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Token.objects.filter(key=token.key).exists())

    def test_current_user_requires_authentication(self):
        self.assertEqual(self.client.get(reverse("current-user")).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_current_user_returns_profile(self):
        self.auth(self.author)
        response = self.client.get(reverse("current-user"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "mara")


class RecipeReadTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.public = make_recipe(self.author, category=self.category)
        self.draft = make_recipe(self.other, title="Secret Draft", published=False)

    def test_guests_only_see_published_recipes(self):
        response = self.client.get(reverse("recipe-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [r["title"] for r in response.data["results"]]
        self.assertIn(self.public.title, titles)
        self.assertNotIn(self.draft.title, titles)

    def test_authenticated_author_sees_own_draft(self):
        self.auth(self.other)
        titles = [r["title"] for r in self.client.get(reverse("recipe-list")).data["results"]]
        self.assertIn(self.draft.title, titles)

    def test_authenticated_non_author_cannot_see_draft(self):
        self.auth(self.author)
        titles = [r["title"] for r in self.client.get(reverse("recipe-list")).data["results"]]
        self.assertNotIn(self.draft.title, titles)

    def test_retrieve_detail_includes_children(self):
        response = self.client.get(reverse("recipe-detail", args=[self.public.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["ingredients"]), 1)
        self.assertEqual(len(response.data["instructions"]), 1)
        self.assertIn("related_recipes", response.data)
        self.assertEqual(
            response.data["preparation_time"] + response.data["cooking_time"], 25
        )

    def test_detail_endpoint_is_json_serializable(self):
        """Catches fields that leak model/queryset objects into the response."""
        make_recipe(self.author, title="Sibling", category=self.category)
        response = self.client.get(reverse("recipe-detail", args=[self.public.id]))
        json.dumps(response.data)  # raises if a QuerySet or model leaked through
        payload = json.loads(response.content)
        self.assertIsInstance(payload["related_recipes"], list)
        self.assertEqual(len(payload["related_recipes"]), 1)

    def test_draft_detail_is_hidden_from_guests(self):
        response = self.client.get(reverse("recipe-detail", args=[self.draft.id]))
        self.assertIn(response.status_code, [status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN])

    def test_search_by_title(self):
        make_recipe(self.author, title="Miso Salmon", cuisine="Japanese")
        response = self.client.get(reverse("recipe-list"), {"search": "Miso"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["title"], "Miso Salmon")

    def test_search_by_ingredient_does_not_duplicate_rows(self):
        make_recipe(self.author, title="Salmon Bowl", cuisine="Japanese")
        response = self.client.get(reverse("recipe-list"), {"search": "Flour"})
        ids = [r["id"] for r in response.data["results"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn(self.public.id, ids)

    def test_filter_by_difficulty(self):
        make_recipe(self.author, title="Hard One", difficulty="hard")
        response = self.client.get(reverse("recipe-list"), {"difficulty": "hard"})
        self.assertEqual(response.data["count"], 1)

    def test_filter_by_multiple_difficulties(self):
        make_recipe(self.author, title="Hard One", difficulty="hard")
        response = self.client.get(reverse("recipe-list"), {"difficulty": ["easy", "hard"]})
        self.assertEqual(response.data["count"], 2)

    def test_filter_by_category(self):
        response = self.client.get(reverse("recipe-list"), {"category": self.category.id})
        self.assertEqual(response.data["count"], 1)

    def test_filter_by_total_time(self):
        make_recipe(self.author, title="Slow Stew", preparation_time=60, cooking_time=90)
        response = self.client.get(reverse("recipe-list"), {"total_time": 30})
        titles = [r["title"] for r in response.data["results"]]
        self.assertIn(self.public.title, titles)
        self.assertNotIn("Slow Stew", titles)

    def test_ordering_by_title(self):
        make_recipe(self.author, title="Apple Pie")
        response = self.client.get(reverse("recipe-list"), {"ordering": "title"})
        titles = [r["title"] for r in response.data["results"]]
        self.assertEqual(titles, sorted(titles))

    def test_pagination(self):
        for index in range(14):
            make_recipe(self.author, title="Recipe %02d" % index)
        response = self.client.get(reverse("recipe-list"), {"page_size": 5})
        self.assertEqual(response.data["count"], 15)
        self.assertEqual(len(response.data["results"]), 5)
        self.assertIsNotNone(response.data["next"])

    def test_is_favorited_is_false_for_guests(self):
        Favorite.objects.create(user=self.author, recipe=self.public)
        response = self.client.get(reverse("recipe-detail", args=[self.public.id]))
        self.assertFalse(response.data["is_favorited"])
        self.assertIsNone(response.data["favorite_id"])

    def test_is_favorited_is_true_for_the_favoriting_user(self):
        favorite = Favorite.objects.create(user=self.author, recipe=self.public)
        self.auth(self.author)
        response = self.client.get(reverse("recipe-detail", args=[self.public.id]))
        self.assertTrue(response.data["is_favorited"])
        self.assertEqual(response.data["favorite_id"], favorite.id)

    def test_is_owner_flag(self):
        self.auth(self.other)
        response = self.client.get(reverse("recipe-detail", args=[self.public.id]))
        self.assertFalse(response.data["is_owner"])

    def test_related_recipes_excludes_self(self):
        sibling = make_recipe(self.author, title="Sibling", category=self.category)
        response = self.client.get(reverse("recipe-related", args=[self.public.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [r["id"] for r in response.data]
        self.assertIn(sibling.id, ids)
        self.assertNotIn(self.public.id, ids)

    def test_related_recipes_without_category_or_cuisine_is_empty(self):
        orphan = make_recipe(self.author, title="Orphan", category=None, cuisine="")
        response = self.client.get(reverse("recipe-related", args=[orphan.id]))
        self.assertEqual(response.data, [])

    def test_related_action_is_json_serializable(self):
        make_recipe(self.author, title="Sibling", category=self.category)
        response = self.client.get(reverse("recipe-related", args=[self.public.id]))
        json.dumps(response.data)
        self.assertIsInstance(json.loads(response.content), list)


class RecipeWriteTests(BaseAPITestCase):
    def test_guests_cannot_create(self):
        response = self.client.post(reverse("recipe-list"), recipe_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_with_nested_children(self):
        self.auth(self.author)
        response = self.client.post(reverse("recipe-list"), recipe_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=response.data["id"])
        self.assertEqual(recipe.author, self.author)
        self.assertEqual(recipe.ingredients.count(), 2)
        self.assertEqual(recipe.instructions.count(), 2)

    def test_create_accepts_children_as_repeated_json_strings(self):
        """Mirrors what the multipart frontend sends."""
        self.auth(self.author)
        payload = recipe_payload()
        payload.pop("ingredients")
        payload.pop("instructions")
        data = {"ingredients": [json.dumps(row) for row in recipe_payload()["ingredients"]]}
        data["instructions"] = [json.dumps(row) for row in recipe_payload()["instructions"]]
        data.update({k: v for k, v in payload.items() if k not in ("ingredients", "instructions")})

        response = self.client.post(reverse("recipe-list"), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Recipe.objects.get(id=response.data["id"]).ingredients.count(), 2)

    def test_create_requires_ingredients_and_instructions(self):
        self.auth(self.author)
        payload = recipe_payload()
        payload["ingredients"] = []
        payload["instructions"] = []
        response = self.client.post(reverse("recipe-list"), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("ingredients", response.data)
        self.assertIn("instructions", response.data)

    def test_step_numbers_are_normalised(self):
        self.auth(self.author)
        payload = recipe_payload()
        payload["instructions"] = [
            {"step_number": 9, "description": "Second in reality"},
            {"step_number": 3, "description": "First in reality"},
        ]
        response = self.client.post(reverse("recipe-list"), payload, format="json")
        recipe = Recipe.objects.get(id=response.data["id"])
        self.assertEqual(
            [i.step_number for i in recipe.instructions.all()], [1, 2]
        )

    def test_update_replaces_children(self):
        self.auth(self.author)
        recipe = make_recipe(self.author)
        payload = recipe_payload(
            ingredients=[{"name": "Butter", "quantity": "50", "unit": "g", "optional": False}],
            instructions=[{"step_number": 1, "description": "Only step."}],
        )
        response = self.client.patch(
            reverse("recipe-detail", args=[recipe.id]), payload, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.ingredients.count(), 1)
        self.assertEqual(recipe.instructions.count(), 1)
        self.assertEqual(recipe.ingredients.first().name, "Butter")

    def test_partial_update_keeps_existing_children(self):
        """A PATCH that omits ingredients must not wipe them."""
        self.auth(self.author)
        recipe = make_recipe(self.author)
        response = self.client.patch(
            reverse("recipe-detail", args=[recipe.id]), {"title": "Renamed Pancakes"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, "Renamed Pancakes")
        self.assertEqual(recipe.ingredients.count(), 1)
        self.assertEqual(recipe.instructions.count(), 1)

    def test_image_upload(self):
        self.auth(self.author)
        response = self.client.post(
            reverse("recipe-list"),
            {
                "title": "Photo Dish",
                "description": "With a photo.",
                "preparation_time": 5,
                "cooking_time": 5,
                "servings": 1,
                "difficulty": "easy",
                "image": png_upload(),
                "ingredients": json.dumps([{"name": "Salt", "quantity": "1", "unit": "pinch", "optional": False}]),
                "instructions": json.dumps([{"description": "Serve."}]),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        recipe = Recipe.objects.get(id=response.data["id"])
        self.assertTrue(recipe.image)
        self.assertIn("image", response.data)

    def test_owner_can_delete(self):
        self.auth(self.author)
        recipe = make_recipe(self.author)
        response = self.client.delete(reverse("recipe-detail", args=[recipe.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_delete_removes_children(self):
        self.auth(self.author)
        recipe = make_recipe(self.author)
        self.client.delete(reverse("recipe-detail", args=[recipe.id]))
        self.assertEqual(Ingredient.objects.filter(recipe=recipe).count(), 0)
        self.assertEqual(Instruction.objects.filter(recipe=recipe).count(), 0)

    def test_non_owner_cannot_update(self):
        self.auth(self.other)
        recipe = make_recipe(self.author)
        response = self.client.patch(
            reverse("recipe-detail", args=[recipe.id]), {"title": "Hijacked"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        recipe.refresh_from_db()
        self.assertNotEqual(recipe.title, "Hijacked")

    def test_non_owner_cannot_delete(self):
        self.auth(self.other)
        recipe = make_recipe(self.author)
        response = self.client.delete(reverse("recipe-detail", args=[recipe.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())

    def test_guests_cannot_delete(self):
        recipe = make_recipe(self.author)
        response = self.client.delete(reverse("recipe-detail", args=[recipe.id]))
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_my_recipes_requires_authentication(self):
        response = self.client.get(reverse("recipe-my-recipes"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_my_recipes_returns_only_own_recipes(self):
        make_recipe(self.author, title="Mine")
        make_recipe(self.other, title="Theirs")
        self.auth(self.author)
        response = self.client.get(reverse("recipe-my-recipes"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [r["title"] for r in response.data["results"]]
        self.assertEqual(titles, ["Mine"])


class CategoryTests(BaseAPITestCase):
    def test_list_includes_recipe_counts(self):
        make_recipe(self.author, category=self.category)
        response = self.client.get(reverse("category-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["recipe_count"], 1)

    def test_list_search(self):
        Category.objects.create(name="Dessert")
        response = self.client.get(reverse("category-list"), {"search": "Dess"})
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Dessert")

    def test_categories_are_read_only_for_guests(self):
        """Anonymous callers are rejected; writes are reserved for curators."""
        anonymous = self.client.post(
            reverse("category-list"), {"name": "Nope"}, format="json"
        )
        self.assertEqual(anonymous.status_code, status.HTTP_401_UNAUTHORIZED)
        self.auth(self.author)
        cook_write = self.client.post(
            reverse("category-list"), {"name": "Nope"}, format="json"
        )
        self.assertEqual(cook_write.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Category.objects.filter(name="Nope").exists())

    def test_moderator_can_create_a_category(self):
        self.auth(self.moderator)
        response = self.client.post(
            reverse("category-list"), {"name": "Soups", "description": "Warm bowls"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(Category.objects.filter(name="Soups").exists())

    def test_cook_cannot_delete_a_category(self):
        self.auth(self.author)
        response = self.client.delete(reverse("category-detail", args=[self.category.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_moderator_can_delete_a_category(self):
        self.auth(self.moderator)
        response = self.client.delete(reverse("category-detail", args=[self.category.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Category.objects.filter(id=self.category.id).exists())


class FavoriteTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.recipe = make_recipe(self.author)

    def test_list_requires_authentication(self):
        response = self.client.get(reverse("favorite-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_is_idempotent(self):
        self.auth(self.author)
        first = self.client.post(reverse("favorite-list"), {"recipe_id": self.recipe.id}, format="json")
        second = self.client.post(reverse("favorite-list"), {"recipe_id": self.recipe.id}, format="json")
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Favorite.objects.filter(user=self.author, recipe=self.recipe).count(), 1)

    def test_create_rejects_unknown_recipe(self):
        self.auth(self.author)
        response = self.client.post(reverse("favorite-list"), {"recipe_id": 99999}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_rejects_another_users_unpublished_recipe(self):
        draft = make_recipe(self.other, title="Hidden", published=False)
        self.auth(self.author)
        response = self.client.post(reverse("favorite-list"), {"recipe_id": draft.id}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_returns_only_own_favorites(self):
        self.auth(self.author)
        self.client.post(reverse("favorite-list"), {"recipe_id": self.recipe.id}, format="json")
        self.auth(self.other)
        self.client.post(reverse("favorite-list"), {"recipe_id": self.recipe.id}, format="json")
        self.auth(self.author)
        response = self.client.get(reverse("favorite-list"))
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["recipe"]["id"], self.recipe.id)

    def test_delete_removes_favorite(self):
        favorite = Favorite.objects.create(user=self.author, recipe=self.recipe)
        self.auth(self.author)
        response = self.client.delete(reverse("favorite-detail", args=[favorite.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Favorite.objects.filter(id=favorite.id).count(), 0)

    def test_cannot_delete_another_users_favorite(self):
        favorite = Favorite.objects.create(user=self.other, recipe=self.recipe)
        self.auth(self.author)
        response = self.client.delete(reverse("favorite-detail", args=[favorite.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class RoleTests(BaseAPITestCase):
    """The role model itself: group sync, resolution and capability helpers."""

    def test_ensure_groups_creates_groups_with_permissions(self):
        groups = ensure_groups()
        self.assertEqual(
            set(groups), {ROLE_COOK, ROLE_MODERATOR, ROLE_ADMIN}
        )
        for role in (ROLE_COOK, ROLE_MODERATOR, ROLE_ADMIN):
            self.assertGreater(groups[role].permissions.count(), 0)

    def test_ensure_groups_is_idempotent(self):
        first = ensure_groups()
        counts = {name: g.permissions.count() for name, g in first.items()}
        second = ensure_groups()
        self.assertEqual(
            counts, {name: g.permissions.count() for name, g in second.items()}
        )

    def test_guest_resolves_to_guest(self):
        from django.contrib.auth.models import AnonymousUser

        self.assertEqual(get_role(AnonymousUser()), ROLE_GUEST)
        self.assertEqual(get_role(None), ROLE_GUEST)

    def test_registered_user_without_a_group_is_a_cook(self):
        user = User.objects.create_user("nogroup", "nogroup@example.com", "x")
        self.assertEqual(get_role(user), ROLE_COOK)

    def test_assign_role_sets_group_and_matching_permissions(self):
        user = User.objects.create_user("newmod", "newmod@example.com", "x")
        assign_role(user, ROLE_MODERATOR)
        user.refresh_from_db()
        self.assertEqual(get_role(user), ROLE_MODERATOR)
        self.assertTrue(user.has_perm("api.change_recipe"))
        self.assertTrue(user.has_perm("api.delete_recipe"))
        self.assertFalse(user.is_superuser)

    def test_assign_role_replaces_previous_role(self):
        user = User.objects.create_user("swap", "swap@example.com", "x")
        assign_role(user, ROLE_MODERATOR)
        assign_role(user, ROLE_COOK)
        user.refresh_from_db()
        self.assertEqual(get_role(user), ROLE_COOK)
        self.assertEqual(user.groups.count(), 1)
        self.assertFalse(user.has_perm("api.change_recipe"))

    def test_assign_admin_sets_staff_and_superuser(self):
        user = User.objects.create_user("boss", "boss@example.com", "x")
        assign_role(user, ROLE_ADMIN)
        user.refresh_from_db()
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertEqual(get_role(user), ROLE_ADMIN)

    def test_demoting_an_admin_revokes_superuser(self):
        user = User.objects.create_user("exboss", "exboss@example.com", "x")
        assign_role(user, ROLE_ADMIN)
        assign_role(user, ROLE_COOK)
        user.refresh_from_db()
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_staff)

    def test_assign_role_rejects_unknown_role(self):
        user = User.objects.create_user("bad", "bad@example.com", "x")
        with self.assertRaises(ValueError):
            assign_role(user, "wizard")

    def test_staff_without_groups_is_still_admin(self):
        user = User.objects.create_user("staffer", "staffer@example.com", "x", is_staff=True)
        self.assertEqual(get_role(user), ROLE_ADMIN)

    def test_can_edit_recipe_helper(self):
        recipe = make_recipe(self.author)
        self.assertTrue(can_edit_recipe(self.author, recipe))
        self.assertFalse(can_edit_recipe(self.other, recipe))
        self.assertTrue(can_edit_recipe(self.moderator, recipe))
        self.assertTrue(can_edit_recipe(self.admin, recipe))

    def test_cook_does_not_get_moderation_permissions(self):
        cook = User.objects.create_user("plain", "plain@example.com", "x")
        assign_role(cook, ROLE_COOK)
        cook = User.objects.get(pk=cook.pk)  # refresh the perm cache
        self.assertFalse(cook.has_perm("api.change_recipe"))
        self.assertFalse(cook.has_perm("api.delete_recipe"))
        self.assertTrue(cook.has_perm("api.add_recipe"))


class ModerationTests(BaseAPITestCase):
    """Moderators and admins may act on anyone's recipes; cooks may not."""

    def setUp(self):
        super().setUp()
        self.recipe = make_recipe(self.author, title="Author's Recipe")

    def test_cook_cannot_update_another_cooks_recipe(self):
        self.auth(self.other)
        response = self.client.patch(
            reverse("recipe-detail", args=[self.recipe.id]),
            {"title": "Hijacked"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.recipe.refresh_from_db()
        self.assertEqual(self.recipe.title, "Author's Recipe")

    def test_cook_cannot_delete_another_cooks_recipe(self):
        self.auth(self.other)
        response = self.client.delete(reverse("recipe-detail", args=[self.recipe.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Recipe.objects.filter(id=self.recipe.id).exists())

    def test_moderator_can_update_another_users_recipe(self):
        self.auth(self.moderator)
        response = self.client.patch(
            reverse("recipe-detail", args=[self.recipe.id]),
            {"title": "Moderated Title"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.recipe.refresh_from_db()
        self.assertEqual(self.recipe.title, "Moderated Title")

    def test_moderator_can_delete_another_users_recipe(self):
        self.auth(self.moderator)
        response = self.client.delete(reverse("recipe-detail", args=[self.recipe.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=self.recipe.id).exists())

    def test_moderator_can_publish_a_draft(self):
        draft = make_recipe(self.other, title="Pending Draft", published=False)
        self.auth(self.moderator)
        response = self.client.patch(
            reverse("recipe-detail", args=[draft.id]), {"published": True}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        draft.refresh_from_db()
        self.assertTrue(draft.published)

    def test_moderator_sees_every_draft_in_the_listing(self):
        draft = make_recipe(self.other, title="Pending Draft", published=False)
        self.auth(self.moderator)
        ids = [r["id"] for r in self.client.get(reverse("recipe-list")).data["results"]]
        self.assertIn(draft.id, ids)
        self.assertIn(self.recipe.id, ids)

    def test_guest_still_cannot_see_drafts(self):
        draft = make_recipe(self.other, title="Pending Draft", published=False)
        ids = [r["id"] for r in self.client.get(reverse("recipe-list")).data["results"]]
        self.assertNotIn(draft.id, ids)

    def test_moderator_can_create_a_recipe(self):
        self.auth(self.moderator)
        response = self.client.post(reverse("recipe-list"), recipe_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(Recipe.objects.get(id=response.data["id"]).author, self.moderator)

    def test_admin_can_moderate(self):
        self.auth(self.admin)
        response = self.client.patch(
            reverse("recipe-detail", args=[self.recipe.id]),
            {"description": "Rewritten by an administrator."},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_can_edit_flag_reflects_role(self):
        self.auth(self.other)
        response = self.client.get(reverse("recipe-detail", args=[self.recipe.id]))
        self.assertFalse(response.data["is_owner"])
        self.assertFalse(response.data["can_edit"])

        self.auth(self.moderator)
        response = self.client.get(reverse("recipe-detail", args=[self.recipe.id]))
        self.assertFalse(response.data["is_owner"])
        self.assertTrue(response.data["can_edit"])

    def test_moderator_still_cannot_touch_another_users_favorites(self):
        favorite = Favorite.objects.create(user=self.author, recipe=self.recipe)
        self.auth(self.moderator)
        response = self.client.delete(reverse("favorite-detail", args=[favorite.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Favorite.objects.filter(id=favorite.id).exists())


class RoleReportingTests(BaseAPITestCase):
    """The API must tell the frontend which role the caller holds."""

    def test_current_user_includes_role(self):
        self.auth(self.moderator)
        data = self.client.get(reverse("current-user")).data
        self.assertEqual(data["role"], ROLE_MODERATOR)
        self.assertEqual(data["role_label"], "Moderator")

    def test_login_includes_role(self):
        response = self.client.post(
            reverse("login"), {"username": "chief", "password": "recipehub123"}, format="json"
        )
        self.assertEqual(response.data["user"]["role"], ROLE_ADMIN)
        self.assertTrue(response.data["user"]["is_staff"])

    def test_cook_role_is_reported(self):
        self.auth(self.author)
        data = self.client.get(reverse("current-user")).data
        self.assertEqual(data["role"], ROLE_COOK)


class PageRenderTests(TestCase):
    """The HTML shells must render for guests and logged-in users alike."""

    def test_public_pages_render(self):
        for name in ["core:home", "core:recipes", "core:login", "core:register"]:
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "RecipeHub")

    def test_detail_page_shell_renders(self):
        response = self.client.get(reverse("core:recipe-detail", args=[1]))
        self.assertEqual(response.status_code, 200)

    def test_edit_page_renders(self):
        response = self.client.get(reverse("core:edit-recipe", args=[1]))
        self.assertEqual(response.status_code, 200)
