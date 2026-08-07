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
