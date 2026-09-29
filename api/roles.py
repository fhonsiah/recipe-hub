"""Role-based access control for RecipeHub.

Roles are stored as Django auth ``Group`` records with real ``Permission``
objects attached, rather than being hard-coded in view logic. That keeps the
role model auditable and editable from the Django admin, and means adding a
capability is a data change, not a code change.

    guest      -> unauthenticated, read published content only
    cook       -> registered user, manages their own recipes and favorites
    moderator  -> cook, plus edits and deletes anyone's recipe and curates
                  categories
    admin      -> moderator, plus full Django admin access
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

ROLE_GUEST = "guest"
ROLE_COOK = "cook"
ROLE_MODERATOR = "moderator"
ROLE_ADMIN = "admin"

#: Roles that can actually be assigned to a user account.
ASSIGNABLE_ROLES = (ROLE_COOK, ROLE_MODERATOR, ROLE_ADMIN)

ROLE_LABELS = {
    ROLE_GUEST: "Guest",
    ROLE_COOK: "Cook",
    ROLE_MODERATOR: "Moderator",
    ROLE_ADMIN: "Admin",
}

ROLE_DESCRIPTIONS = {
    ROLE_COOK: "Publishes recipes and manages their own favorites.",
    ROLE_MODERATOR: "Edits and removes any recipe, and curates categories.",
    ROLE_ADMIN: "Full access, including the Django admin site.",
}

GROUP_COOKS = "Cooks"
GROUP_MODERATORS = "Moderators"
GROUP_ADMINISTRATORS = "Administrators"

ROLE_GROUPS = {
    ROLE_COOK: GROUP_COOKS,
    ROLE_MODERATOR: GROUP_MODERATORS,
    ROLE_ADMIN: GROUP_ADMINISTRATORS,
}

GROUP_ROLES = {group: role for role, group in ROLE_GROUPS.items()}

# Roles are evaluated in descending privilege, so a user in several groups
# resolves to their most capable role.
ROLE_PRECEDENCE = (ROLE_ADMIN, ROLE_MODERATOR, ROLE_COOK)


def _perms(app_label, model, actions):
    """Build ``app_label.codename`` strings for the given actions."""
    return ["%s.%s_%s" % (app_label, action, model) for action in actions]


_COOK_PERMISSIONS = _perms("api", "recipe", ["add", "view"]) + _perms("api", "category", ["view"])

_MODERATOR_PERMISSIONS = _COOK_PERMISSIONS + _perms(
    "api", "recipe", ["change", "delete"]
) + _perms("api", "category", ["add", "change", "delete"])

_ADMIN_PERMISSIONS = _MODERATOR_PERMISSIONS + _perms("api", "favorite", ["view"])

ROLE_PERMISSIONS = {
    ROLE_COOK: _COOK_PERMISSIONS,
    ROLE_MODERATOR: _MODERATOR_PERMISSIONS,
    ROLE_ADMIN: _ADMIN_PERMISSIONS,
}


def get_role(user):
    """Resolve a user's effective role.

    Superusers and staff are always treated as admins so that the Django
    admin site keeps working regardless of group membership.
    """
    if not user or not user.is_authenticated:
        return ROLE_GUEST
    if user.is_superuser or user.is_staff:
        return ROLE_ADMIN

    group_names = set(user.groups.values_list("name", flat=True))
    for role in ROLE_PRECEDENCE:
        if ROLE_GROUPS[role] in group_names:
            return role
    # A registered user without a group still gets the default cook role.
    return ROLE_COOK


def is_moderator_or_above(user):
    return get_role(user) in (ROLE_MODERATOR, ROLE_ADMIN)


def can_edit_recipe(user, recipe):
    """Whether `user` may modify `recipe`.

    Authors may always edit their own work; moderators and admins may edit
    anyone's.
    """
    if not user or not user.is_authenticated or recipe is None:
        return False
    if recipe.author_id == user.pk:
        return True
    return user.has_perm("api.change_recipe")


def can_delete_recipe(user, recipe):
    if not user or not user.is_authenticated or recipe is None:
        return False
    if recipe.author_id == user.pk:
        return True
    return user.has_perm("api.delete_recipe")


def ensure_groups():
    """Create the role groups and sync their permissions. Idempotent."""
    groups = {}
    for role, group_name in ROLE_GROUPS.items():
        group, _ = Group.objects.get_or_create(name=group_name)
        groups[role] = group

    # Resolve codenames against the real Permission rows so the mapping stays
    # correct even if a model is renamed.
    wanted = {}
    for role, codenames in ROLE_PERMISSIONS.items():
        wanted[groups[role]] = set(
            Permission.objects.filter(
                codename__in=[c.split(".", 1)[1] for c in codenames]
            ).values_list("codename", flat=True)
        )

    for group, codenames in wanted.items():
        group.permissions.set(
            Permission.objects.filter(
                codename__in=codenames, content_type__app_label="api"
            )
        )
    return groups


def assign_role(user, role):
    """Put `user` in exactly the group for `role` and return it."""
    if role not in ASSIGNABLE_ROLES:
        raise ValueError(
            "Unknown role %r. Choose one of: %s" % (role, ", ".join(ASSIGNABLE_ROLES))
        )
    groups = ensure_groups()
    user.groups.set([groups[role]])

    # Staff and superuser flags follow the role, so demoting an account really
    # does revoke its access to the Django admin.
    is_admin = role == ROLE_ADMIN
    user.is_staff = is_admin
    user.is_superuser = is_admin
    user.save()
    return get_role(user)


def clear_roles(user):
    user.groups.clear()
    user.is_staff = False
    user.is_superuser = False
    user.save()
    return get_role(user)
