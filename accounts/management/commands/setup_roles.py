from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError

from accounts.roles import ROLE_PERMISSIONS


class Command(BaseCommand):
    help = "Create or update Vendilume's company roles."

    def handle(self, *args, **options):
        for role_name, permission_keys in ROLE_PERMISSIONS.items():
            permissions = []

            for app_label, codename in permission_keys:
                try:
                    permission = Permission.objects.get(
                        content_type__app_label=app_label,
                        codename=codename,
                    )
                except Permission.DoesNotExist as error:
                    raise CommandError(
                        "Required permission does not exist: "
                        f"{app_label}.{codename}"
                    ) from error

                permissions.append(permission)

            group, _ = Group.objects.get_or_create(
                name=role_name,
            )
            group.permissions.set(permissions)

            self.stdout.write(
                self.style.SUCCESS(
                    f'Configured role "{role_name}" '
                    f"with {len(permissions)} permissions."
                )
            )
