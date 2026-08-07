"""Helpers to seed preference / notification rows."""
from apps.accounts.models import (
    CustomerNotificationSetting,
    CustomerPreference,
    CustomerProfile,
    RestaurantNotificationSetting,
    RestaurantPreference,
)


def seed_customer_side(profile: CustomerProfile) -> None:
    CustomerPreference.objects.get_or_create(customer_profile=profile)
    CustomerNotificationSetting.objects.get_or_create(customer_profile=profile)


def seed_restaurant_side(restaurant) -> None:
    RestaurantPreference.objects.get_or_create(restaurant=restaurant)
    RestaurantNotificationSetting.objects.get_or_create(restaurant=restaurant)
    from apps.restaurants.services.seeding import seed_default_categories

    seed_default_categories()
