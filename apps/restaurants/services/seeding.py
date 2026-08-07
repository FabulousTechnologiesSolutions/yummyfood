"""Global default menu category seeds."""

DEFAULT_CATEGORY_SEEDS = [
    ('fastfood', 'Fast Food'),
    ('pakistani', 'Pakistani'),
    ('continental', 'Continental'),
    ('chinese', 'Chinese'),
    ('bbq', 'BBQ'),
    ('pizza', 'Pizza'),
    ('burgers', 'Burgers'),
    ('wraps', 'Wraps'),
    ('pasta', 'Pasta'),
    ('rice', 'Rice'),
    ('salads', 'Salads'),
    ('soups', 'Soups'),
    ('beverages', 'Beverages'),
    ('desserts', 'Desserts'),
    ('kids', 'Kids'),
    ('deals', 'Deals'),
    ('addons', 'Add-ons'),
]


def seed_default_categories() -> list:
    from apps.restaurants.models import MenuCategory

    created = []
    for position, (slug, name) in enumerate(DEFAULT_CATEGORY_SEEDS):
        obj, was_created = MenuCategory.objects.get_or_create(
            slug=slug,
            defaults={
                'name': name,
                'position': position,
                'is_visible': True,
            },
        )
        if was_created:
            created.append(obj)
    return created
