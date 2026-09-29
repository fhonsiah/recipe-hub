"""Assign, inspect or clear a RecipeHub role for a user.

    python manage.py assign_role mara cook
    python manage.py assign_role editor moderator
    python manage.py assign_role chief admin
    python manage.py assign_role mara --clear
    python manage.py assign_role --list
    python manage.py sync_roles
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from api.roles import (
    ASSIGNABLE_ROLES,
    ROLE_DESCRIPTIONS,
    ROLE_LABELS,
    assign_role,
    clear_roles,
    ensure_groups,
    get_role,
)


class Command(BaseCommand):
    help = "Manage RecipeHub roles (cook, moderator, admin)."

    def add_arguments(self, parser):
        parser.add_argument("username", nargs="?", help="The account to change.")
        parser.add_argument(
            "role",
            nargs="?",
            choices=list(ASSIGNABLE_ROLES),
            help="The role to assign.",
        )
        parser.add_argument(
            "--clear", action="store_true", help="Remove the user from all role groups."
        )
        parser.add_argument(
            "--list", action="store_true", help="List every account and its effective role."
        )
        parser.add_argument(
            "--sync", action="store_true", help="Create or resync the role groups and permissions."
        )

    def handle(self, *args, **options):
        User = get_user_model()

        if options["sync"]:
            groups = ensure_groups()
            for role, group in groups.items():
                self.stdout.write(
                    self.style.SUCCESS(
                        "%-11s %-15s %d permission(s)" % (
                            role, group.name, group.permissions.count()
                        )
                    )
                )
            return

        if options["list"]:
            self.stdout.write(self.style.MIGRATE_HEADING("Roles"))
            for role in ASSIGNABLE_ROLES:
                self.stdout.write(
                    "  %-11s %-11s %s" % (role, ROLE_LABELS[role], ROLE_DESCRIPTIONS[role])
                )
            self.stdout.write("")
            self.stdout.write(self.style.MIGRATE_HEADING("Accounts"))
            if not User.objects.exists():
                self.stdout.write("  (no users yet)")
                return
            for user in User.objects.order_by("id"):
                self.stdout.write(
                    "  %-14s %-11s staff=%-5s super=%-5s groups=%s"
                    % (
                        user.username,
                        get_role(user),
                        user.is_staff,
                        user.is_superuser,
                        ", ".join(user.groups.values_list("name", flat=True)) or "-",
                    )
                )
            return

        username = options["username"]
        if not username:
            raise CommandError("Provide a username, or use --list / --sync.")

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError("No such user: %s" % username)

        if options["clear"]:
            role = clear_roles(user)
            self.stdout.write(
                self.style.WARNING("%s now has no role group (effective role: %s)." % (username, role))
            )
            return

        role = options["role"]
        if not role:
            raise CommandError(
                "Provide a role (%s), or use --clear." % ", ".join(ASSIGNABLE_ROLES)
            )

        assigned = assign_role(user, role)
        self.stdout.write(
            self.style.SUCCESS(
                "%s is now a %s (staff=%s, superuser=%s)."
                % (username, ROLE_LABELS[assigned], user.is_staff, user.is_superuser)
            )
        )
