"""Object- and view-level permission classes for RecipeHub.

Class-level gates decide *whether a request is allowed at all*; object-level
gates decide *which instances* the caller may touch. RecipeHub's ownership
rule is expressed through the role helpers in :mod:`api.roles` so that a
moderator can curate content without a bespoke code path per view.
"""
from rest_framework import permissions

from .roles import can_delete_recipe, can_edit_recipe, get_role


class IsAuthorOrModeratorOrReadOnly(permissions.BasePermission):
    """Safe methods are public; unsafe methods need authorship or moderation.

    A cook may only modify their own recipes. A moderator or admin may modify
    anyone's, which is what makes review and cleanup possible without
    impersonating the author.
    """

    message = "You can only edit or delete your own recipes."

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method == "DELETE":
            return can_delete_recipe(request.user, obj)
        return can_edit_recipe(request.user, obj)


class CanCreateRecipe(permissions.BasePermission):
    """Any signed-in user may publish; guests may not."""

    message = "You need an account to publish a recipe."

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated)


class CanManageCategories(permissions.BasePermission):
    """Categories are curated by moderators and admins only."""

    message = "Only moderators and admins can manage categories."

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in ("POST", "PUT", "PATCH"):
            return request.user.has_perm("api.add_category") or request.user.has_perm(
                "api.change_category"
            )
        return request.user.has_perm("api.delete_category")


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Generic owner check for models that use `user` rather than `author`."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        owner = getattr(obj, "user", None) or getattr(obj, "author", None)
        return owner is not None and owner == request.user
