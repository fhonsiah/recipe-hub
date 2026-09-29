from django.contrib import admin

from .models import Category, Favorite, Ingredient, Instruction, Recipe


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "recipe_count", "created_at"]
    search_fields = ["name"]
    readonly_fields = ["created_at"]

    @admin.display(description="Recipes")
    def recipe_count(self, obj):
        return obj.recipes.count()


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ["name", "recipe", "quantity", "unit", "optional"]
    list_select_related = ["recipe"]


@admin.register(Instruction)
class InstructionAdmin(admin.ModelAdmin):
    list_display = ["step_number", "recipe"]
    list_select_related = ["recipe"]


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ["user", "recipe", "created_at"]
    list_select_related = ["user", "recipe"]


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ["title", "author", "category", "difficulty", "published", "created_at"]
    list_filter = ["published", "difficulty", "category", "created_at"]
    search_fields = ["title", "description"]
    autocomplete_fields = ["author", "category"]
