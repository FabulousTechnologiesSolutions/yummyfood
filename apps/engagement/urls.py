from django.urls import path

from apps.engagement.views import (
    DealRatingView,
    ItemRatingView,
    ReportDealView,
    ReportItemView,
    ReportRestaurantView,
    RestaurantRatingView,
    SavedDetailView,
    SavedListCreateView,
)

urlpatterns = [
    path('saved/', SavedListCreateView.as_view(), name='saved-list-create'),
    path('saved/<int:saved_id>/', SavedDetailView.as_view(), name='saved-detail'),
    path('reports/items/<int:item_id>/', ReportItemView.as_view(), name='report-item'),
    path('reports/deals/<int:deal_id>/', ReportDealView.as_view(), name='report-deal'),
    path(
        'reports/restaurants/<int:restaurant_id>/',
        ReportRestaurantView.as_view(),
        name='report-restaurant',
    ),
    path(
        'restaurants/<int:restaurant_id>/rating/',
        RestaurantRatingView.as_view(),
        name='restaurant-rating',
    ),
    path(
        'menu-items/<int:item_id>/rating/',
        ItemRatingView.as_view(),
        name='item-rating',
    ),
    path(
        'deals/<int:deal_id>/rating/',
        DealRatingView.as_view(),
        name='deal-rating',
    ),
]
