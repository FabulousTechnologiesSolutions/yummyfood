from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.geo.views import CityViewSet

router = DefaultRouter()
router.register('cities', CityViewSet, basename='cities')

urlpatterns = [
    path('', include(router.urls)),
]
