"""
URL configuration for FoodApp.
"""
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path(
        'api/docs/',
        SpectacularSwaggerView.as_view(url_name='schema'),
        name='swagger-ui',
    ),
    path(
        'api/redoc/',
        SpectacularRedocView.as_view(url_name='schema'),
        name='redoc',
    ),
    path('api/auth/', include('apps.accounts.urls')),
    path('api/', include('apps.accounts.me_urls')),
    path('api/', include('apps.geo.urls')),
    path('api/restaurant/', include('apps.restaurants.urls')),
    path('api/restaurant/', include('apps.mediahub.urls')),
    path('api/public/', include('apps.restaurants.public_urls')),
    path('api/', include('apps.menu.urls')),
    path('api/', include('apps.deals.urls')),
    path('api/', include('apps.promotions.urls')),
    path('api/', include('apps.feed.urls')),
    path('api/', include('apps.discovery.urls')),
    path('api/', include('apps.engagement.urls')),
    path('api/', include('apps.analytics.urls')),
]
