from django.urls import path

from .views import PageView

app_name = "core"

urlpatterns = [
    path("", PageView.as_view(template_name="core/home.html"), name="home"),
    path("recipes/", PageView.as_view(template_name="core/recipes.html"), name="recipes"),
    path("recipes/add/", PageView.as_view(template_name="core/recipe_form.html"), name="add-recipe"),
    path("recipes/<int:pk>/", PageView.as_view(template_name="core/recipe_detail.html"), name="recipe-detail"),
    path("recipes/<int:pk>/edit/", PageView.as_view(template_name="core/recipe_form.html"), name="edit-recipe"),
    path("login/", PageView.as_view(template_name="core/login.html"), name="login"),
    path("register/", PageView.as_view(template_name="core/register.html"), name="register"),
    path("dashboard/", PageView.as_view(template_name="core/dashboard.html"), name="dashboard"),
    path("favorites/", PageView.as_view(template_name="core/favorites.html"), name="favorites"),
]
