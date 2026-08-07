from apps.accounts.models import (
    AppMode,
    CustomerNotificationSetting,
    CustomerPreference,
    RestaurantNotificationSetting,
    RestaurantPreference,
    User,
)
from core.exceptions import AppAPIException


ALLOWED_PRICE = {'$', '$$', '$$$', '$$$$'}


class PreferenceService:
    def _require_customer(self, user: User):
        if not user.has_customer_profile:
            raise AppAPIException(
                code='CUSTOMER_PROFILE_REQUIRED',
                message='Customer profile required.',
                status_code=403,
            )
        return user.customer_profile

    def _require_restaurant(self, user: User):
        if not user.has_restaurant_profile:
            raise AppAPIException(
                code='RESTAURANT_PROFILE_REQUIRED',
                message='Restaurant profile required.',
                status_code=403,
            )
        return user.restaurant

    def get_preferences(self, user: User) -> dict:
        if user.active_mode == AppMode.RESTAURANT:
            restaurant = self._require_restaurant(user)
            pref, _ = RestaurantPreference.objects.get_or_create(restaurant=restaurant)
            return {
                'side': 'restaurant',
                'language': pref.language,
                'theme': pref.theme,
            }
        profile = self._require_customer(user)
        pref, _ = CustomerPreference.objects.get_or_create(customer_profile=profile)
        return {
            'side': 'customer',
            'cuisines': pref.cuisines,
            'price_ranges': pref.price_ranges,
            'max_distance_km': pref.max_distance_km,
            'city_id': pref.city_id,
            'language': pref.language,
            'theme': pref.theme,
        }

    def update_preferences(self, user: User, data: dict) -> dict:
        if user.active_mode == AppMode.RESTAURANT:
            restaurant = self._require_restaurant(user)
            pref, _ = RestaurantPreference.objects.get_or_create(restaurant=restaurant)
            if 'language' in data and data['language'] is not None:
                pref.language = data['language']
            if 'theme' in data and data['theme'] is not None:
                pref.theme = data['theme']
            pref.save()
            return self.get_preferences(user)

        profile = self._require_customer(user)
        pref, _ = CustomerPreference.objects.get_or_create(customer_profile=profile)
        if 'cuisines' in data and data['cuisines'] is not None:
            pref.cuisines = data['cuisines']
        if 'price_ranges' in data and data['price_ranges'] is not None:
            prices = data['price_ranges']
            if any(p not in ALLOWED_PRICE for p in prices):
                raise AppAPIException(
                    code='INVALID_PRICE_RANGE',
                    message='Invalid price_ranges value.',
                    status_code=400,
                )
            pref.price_ranges = prices
        if 'max_distance_km' in data and data['max_distance_km'] is not None:
            dist = int(data['max_distance_km'])
            if dist < 1 or dist > 25:
                raise AppAPIException(
                    code='INVALID_DISTANCE',
                    message='max_distance_km must be between 1 and 25.',
                    status_code=400,
                )
            pref.max_distance_km = dist
        if 'city_id' in data:
            pref.city_id = data['city_id']
        if 'language' in data and data['language'] is not None:
            pref.language = data['language']
        if 'theme' in data and data['theme'] is not None:
            pref.theme = data['theme']
        pref.save()
        return self.get_preferences(user)

    def get_notifications(self, user: User) -> dict:
        if user.active_mode == AppMode.RESTAURANT:
            restaurant = self._require_restaurant(user)
            setting, _ = RestaurantNotificationSetting.objects.get_or_create(
                restaurant=restaurant
            )
            return {
                'side': 'restaurant',
                'enable_push_notification': setting.enable_push_notification,
                'promo_status_alerts': setting.promo_status_alerts,
                'new_follower_alerts': setting.new_follower_alerts,
                'weekly_performance_digest': setting.weekly_performance_digest,
            }
        profile = self._require_customer(user)
        setting, _ = CustomerNotificationSetting.objects.get_or_create(
            customer_profile=profile
        )
        return {
            'side': 'customer',
            'enable_push_notification': setting.enable_push_notification,
            'expiry_reminders': setting.expiry_reminders,
            'new_deals_from_saved': setting.new_deals_from_saved,
            'nearby_flash_deals': setting.nearby_flash_deals,
            'new_videos_from_followed': setting.new_videos_from_followed,
            'weekly_digest': setting.weekly_digest,
            'security_alerts': True,  # always on
        }

    def update_notifications(self, user: User, data: dict) -> dict:
        if user.active_mode == AppMode.RESTAURANT:
            restaurant = self._require_restaurant(user)
            setting, _ = RestaurantNotificationSetting.objects.get_or_create(
                restaurant=restaurant
            )
            for field in (
                'enable_push_notification',
                'promo_status_alerts',
                'new_follower_alerts',
                'weekly_performance_digest',
            ):
                if field in data and data[field] is not None:
                    setattr(setting, field, bool(data[field]))
            setting.save()
            return self.get_notifications(user)

        profile = self._require_customer(user)
        setting, _ = CustomerNotificationSetting.objects.get_or_create(
            customer_profile=profile
        )
        if 'security_alerts' in data and data['security_alerts'] is False:
            # Always on — ignore off or reject; ignore quietly keep True
            pass
        for field in (
            'enable_push_notification',
            'expiry_reminders',
            'new_deals_from_saved',
            'nearby_flash_deals',
            'new_videos_from_followed',
            'weekly_digest',
        ):
            if field in data and data[field] is not None:
                setattr(setting, field, bool(data[field]))
        setting.security_alerts = True
        setting.save()
        return self.get_notifications(user)
