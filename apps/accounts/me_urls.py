from django.urls import path

from apps.accounts import views

urlpatterns = [
    path('me/preferences/', views.PreferencesView.as_view(), name='me-preferences'),
    path('me/notifications/', views.NotificationsView.as_view(), name='me-notifications'),
    path('me/profiles/', views.ProfilesView.as_view(), name='me-profiles'),
    path('me/customer-profile/', views.AddCustomerProfileView.as_view(), name='me-customer-profile'),
    path('me/restaurants/', views.AddRestaurantView.as_view(), name='me-restaurants'),
    path('me/console-access/', views.ConsoleAccessView.as_view(), name='me-console-access'),
    path('me/switch-to-customer/', views.SwitchToCustomerView.as_view(), name='me-switch-customer'),
    path('me/switch-to-restaurant/', views.SwitchToRestaurantView.as_view(), name='me-switch-restaurant'),
]
