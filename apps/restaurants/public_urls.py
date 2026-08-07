from django.urls import path

from apps.restaurants.views import (
    PublicDealDetailView,
    PublicMenuItemDetailView,
    PublicRestaurantDetailView,
)

urlpatterns = [
    path(
        'restaurants/<int:restaurant_id>/',
        PublicRestaurantDetailView.as_view(),
        name='public-restaurant-detail',
    ),
    path(
        'menu-items/<int:item_id>/',
        PublicMenuItemDetailView.as_view(),
        name='public-menu-item',
    ),
    path('deals/<int:deal_id>/', PublicDealDetailView.as_view(), name='public-deal'),
]
