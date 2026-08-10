from rest_framework import serializers

from apps.accounts.models import SignupIntent


class RegisterSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)
    password = serializers.CharField(min_length=8, write_only=True)
    signup_intent = serializers.ChoiceField(choices=SignupIntent.choices)
    restaurant_name = serializers.CharField(required=False, allow_blank=True, default='')
    session_key = serializers.CharField(required=False, allow_blank=True, default='')


class LoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)
    password = serializers.CharField(write_only=True)
    session_key = serializers.CharField(required=False, allow_blank=True, default='')


class RefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class PasswordForgotSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)


class PasswordResetSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)
    otp = serializers.CharField(max_length=10)
    new_password = serializers.CharField(min_length=8, write_only=True)
    confirm_password = serializers.CharField(min_length=8, write_only=True)


class MeUpdateSerializer(serializers.Serializer):
    display_name = serializers.CharField(required=False, allow_blank=True, max_length=120)
    # avatar handled as file in view if present


class GuestMigrateSerializer(serializers.Serializer):
    session_key = serializers.CharField(max_length=64)


class AddRestaurantSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)


class RestaurantBrandingSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=['cover', 'logo'])
    image = serializers.ImageField()


class RestaurantProfileUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120, required=False)
    short_description = serializers.CharField(required=False, allow_blank=True)
    cuisines = serializers.ListField(
        child=serializers.CharField(max_length=64),
        required=False,
        max_length=3,
    )
    price_range = serializers.ChoiceField(
        choices=['$', '$$', '$$$', '$$$$'],
        required=False,
        allow_blank=True,
    )
    primary_phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    whatsapp_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    use_different_whatsapp = serializers.BooleanField(required=False)
    secondary_phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    street_address = serializers.CharField(max_length=255, required=False, allow_blank=True)
    area = serializers.CharField(max_length=120, required=False, allow_blank=True)
    city_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    lat = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False, allow_null=True,
    )
    lng = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False, allow_null=True,
    )
    is_paused = serializers.BooleanField(required=False)
    promo_default_radius_km = serializers.IntegerField(
        required=False, min_value=1, max_value=50,
    )
    promo_default_duration_days = serializers.IntegerField(
        required=False, min_value=1, max_value=90,
    )
    notify_on_promo_approval = serializers.BooleanField(required=False)
    auto_request_promo_on_deal = serializers.BooleanField(required=False)


class SwitchRestaurantSerializer(serializers.Serializer):
    restaurant_name = serializers.CharField(required=False, allow_blank=True, default='')


class CustomerPreferenceSerializer(serializers.Serializer):
    cuisines = serializers.ListField(child=serializers.CharField(), required=False)
    price_ranges = serializers.ListField(child=serializers.CharField(), required=False)
    max_distance_km = serializers.IntegerField(required=False, min_value=1, max_value=25)
    city_id = serializers.IntegerField(required=False, allow_null=True)
    language = serializers.ChoiceField(choices=['en', 'ur'], required=False)
    theme = serializers.ChoiceField(choices=['system', 'light', 'dark'], required=False)


class RestaurantPreferenceSerializer(serializers.Serializer):
    language = serializers.ChoiceField(choices=['en', 'ur'], required=False)
    theme = serializers.ChoiceField(choices=['system', 'light', 'dark'], required=False)


class CustomerNotificationSerializer(serializers.Serializer):
    enable_push_notification = serializers.BooleanField(required=False)
    expiry_reminders = serializers.BooleanField(required=False)
    new_deals_from_saved = serializers.BooleanField(required=False)
    nearby_flash_deals = serializers.BooleanField(required=False)
    new_videos_from_followed = serializers.BooleanField(required=False)
    weekly_digest = serializers.BooleanField(required=False)
    security_alerts = serializers.BooleanField(required=False)


class RestaurantNotificationSerializer(serializers.Serializer):
    enable_push_notification = serializers.BooleanField(required=False)
    promo_status_alerts = serializers.BooleanField(required=False)
    new_follower_alerts = serializers.BooleanField(required=False)
    weekly_performance_digest = serializers.BooleanField(required=False)
