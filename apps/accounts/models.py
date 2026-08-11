from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.accounts.managers import UserManager


class SignupIntent(models.TextChoices):
    CUSTOMER = 'customer', 'Customer'
    RESTAURANT = 'restaurant', 'Restaurant'


class AppMode(models.TextChoices):
    CUSTOMER = 'customer', 'Customer'
    RESTAURANT = 'restaurant', 'Restaurant'


class ThemeChoice(models.TextChoices):
    SYSTEM = 'system', 'System'
    LIGHT = 'light', 'Light'
    DARK = 'dark', 'Dark'


class LanguageChoice(models.TextChoices):
    EN = 'en', 'English'
    UR = 'ur', 'Urdu'


class User(AbstractBaseUser, PermissionsMixin):
    phone_number = models.CharField(max_length=20, unique=True)
    display_name = models.CharField(max_length=120, blank=True, default='')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    signup_intent = models.CharField(
        max_length=20,
        choices=SignupIntent.choices,
        blank=True,
        default='',
    )
    active_mode = models.CharField(
        max_length=20,
        choices=AppMode.choices,
        default=AppMode.CUSTOMER,
    )
    last_active_mode = models.CharField(
        max_length=20,
        choices=AppMode.choices,
        default=AppMode.CUSTOMER,
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    terms_accepted_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        ordering = ['-date_joined']

    def __str__(self):
        return self.phone_number

    @property
    def has_customer_profile(self) -> bool:
        return CustomerProfile.objects.filter(user_id=self.pk).exists() if self.pk else False

    @property
    def has_restaurant_profile(self) -> bool:
        from apps.restaurants.models import Restaurant

        return Restaurant.objects.filter(owner_id=self.pk).exists() if self.pk else False

    @property
    def is_restaurant_owner(self) -> bool:
        from apps.restaurants.models import Restaurant

        try:
            restaurant = self.restaurant
        except Restaurant.DoesNotExist:
            return False
        return not restaurant.is_permanently_closed


class CustomerProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='customer_profile',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'CustomerProfile<{self.user_id}>'


class CustomerPreference(models.Model):
    customer_profile = models.OneToOneField(
        CustomerProfile,
        on_delete=models.CASCADE,
        related_name='preference',
    )
    cuisines = models.JSONField(default=list, blank=True)
    price_ranges = models.JSONField(default=list, blank=True)
    max_distance_km = models.PositiveSmallIntegerField(default=5)
    city = models.ForeignKey(
        'geo.City',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customer_preferences',
    )
    language = models.CharField(
        max_length=5,
        choices=LanguageChoice.choices,
        default=LanguageChoice.EN,
    )
    theme = models.CharField(
        max_length=10,
        choices=ThemeChoice.choices,
        default=ThemeChoice.SYSTEM,
    )

    def __str__(self):
        return f'CustomerPreference<{self.customer_profile_id}>'


class CustomerNotificationSetting(models.Model):
    customer_profile = models.OneToOneField(
        CustomerProfile,
        on_delete=models.CASCADE,
        related_name='notification_setting',
    )
    enable_push_notification = models.BooleanField(default=True)
    expiry_reminders = models.BooleanField(default=True)
    new_deals_from_saved = models.BooleanField(default=True)
    nearby_flash_deals = models.BooleanField(default=False)
    new_videos_from_followed = models.BooleanField(default=True)
    weekly_digest = models.BooleanField(default=False)
    security_alerts = models.BooleanField(default=True)

    def __str__(self):
        return f'CustomerNotificationSetting<{self.customer_profile_id}>'


class RestaurantPreference(models.Model):
    restaurant = models.OneToOneField(
        'restaurants.Restaurant',
        on_delete=models.CASCADE,
        related_name='preference',
    )
    language = models.CharField(
        max_length=5,
        choices=LanguageChoice.choices,
        default=LanguageChoice.EN,
    )
    theme = models.CharField(
        max_length=10,
        choices=ThemeChoice.choices,
        default=ThemeChoice.SYSTEM,
    )

    def __str__(self):
        return f'RestaurantPreference<{self.restaurant_id}>'


class RestaurantNotificationSetting(models.Model):
    restaurant = models.OneToOneField(
        'restaurants.Restaurant',
        on_delete=models.CASCADE,
        related_name='notification_setting',
    )
    enable_push_notification = models.BooleanField(default=True)
    promo_status_alerts = models.BooleanField(default=True)
    new_follower_alerts = models.BooleanField(default=True)
    weekly_performance_digest = models.BooleanField(default=False)

    def __str__(self):
        return f'RestaurantNotificationSetting<{self.restaurant_id}>'


class GuestSession(models.Model):
    session_key = models.CharField(max_length=64, unique=True)
    watch_history = models.JSONField(default=list, blank=True)
    search_history = models.JSONField(default=list, blank=True)
    pending_save = models.JSONField(null=True, blank=True)
    device_info = models.JSONField(default=dict, blank=True)
    merged_into_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='merged_guest_sessions',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.session_key


class PasswordResetOTP(models.Model):
    phone_number = models.CharField(max_length=20, db_index=True)
    otp_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'OTP<{self.phone_number}>'
