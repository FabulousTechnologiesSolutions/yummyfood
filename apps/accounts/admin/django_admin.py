from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.accounts.models import (
    CustomerNotificationSetting,
    CustomerPreference,
    CustomerProfile,
    GuestSession,
    PasswordResetOTP,
    RestaurantNotificationSetting,
    RestaurantPreference,
    User,
)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ('phone_number',)
    list_display = (
        'phone_number',
        'display_name',
        'active_mode',
        'is_staff',
        'is_active',
        'date_joined',
    )
    search_fields = ('phone_number', 'display_name')
    fieldsets = (
        (None, {'fields': ('phone_number', 'password')}),
        (
            'Profile',
            {
                'fields': (
                    'display_name',
                    'avatar',
                    'signup_intent',
                    'active_mode',
                    'last_active_mode',
                    'terms_accepted_at',
                    'deleted_at',
                )
            },
        ),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': ('phone_number', 'password1', 'password2', 'is_staff', 'is_superuser'),
            },
        ),
    )
    filter_horizontal = ('groups', 'user_permissions')


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'created_at')


admin.site.register(CustomerPreference)
admin.site.register(CustomerNotificationSetting)
admin.site.register(RestaurantPreference)
admin.site.register(RestaurantNotificationSetting)
admin.site.register(GuestSession)
admin.site.register(PasswordResetOTP)
