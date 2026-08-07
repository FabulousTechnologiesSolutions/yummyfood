from django.urls import path

from apps.accounts import views

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='auth-register'),
    path('login/', views.LoginView.as_view(), name='auth-login'),
    path('refresh/', views.RefreshView.as_view(), name='auth-refresh'),
    path('logout/', views.LogoutView.as_view(), name='auth-logout'),
    path('password/forgot/', views.PasswordForgotView.as_view(), name='auth-password-forgot'),
    path('password/reset/', views.PasswordResetView.as_view(), name='auth-password-reset'),
    path('me/', views.MeView.as_view(), name='auth-me'),
    path('guest/migrate/', views.GuestMigrateView.as_view(), name='auth-guest-migrate'),
]
