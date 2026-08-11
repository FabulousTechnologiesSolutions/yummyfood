from django.core.management.base import BaseCommand

from apps.geo.models import City

SEED_CITIES = (
    'Karachi',
    'Lahore',
    'Islamabad',
    'Faisalabad',
    'Multan',
)


class Command(BaseCommand):
    help = 'Seed popular Pakistani cities (idempotent by name).'

    def handle(self, *args, **options):
        created_count = 0
        for name in SEED_CITIES:
            _, created = City.objects.update_or_create(
                name=name,
                defaults={'is_active': True},
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Created city: {name}'))
            else:
                self.stdout.write(f'Exists: {name}')
        self.stdout.write(
            self.style.SUCCESS(
                f'Done. {created_count} created, {len(SEED_CITIES) - created_count} already present.'
            )
        )
