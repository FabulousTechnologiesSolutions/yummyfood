from django.urls import path

from apps.restaurants.views import (
    CategoryDetailView,
    CategoryListCreateView,
    CategoryReorderView,
    DealDetailView,
    DealListCreateView,
    DealPreviewView,
    MenuItemAvailabilityView,
    MenuItemDetailView,
    MenuItemDuplicateView,
    MenuItemHideView,
    MenuItemListCreateView,
    MenuItemMoveView,
)

urlpatterns = [
    path('categories/', CategoryListCreateView.as_view(), name='restaurant-categories'),
    path(
        'categories/reorder/',
        CategoryReorderView.as_view(),
        name='restaurant-categories-reorder',
    ),
    path(
        'categories/<int:category_id>/',
        CategoryDetailView.as_view(),
        name='restaurant-category-detail',
    ),
    path('menu-items/', MenuItemListCreateView.as_view(), name='restaurant-menu-items'),
    path(
        'menu-items/<int:item_id>/',
        MenuItemDetailView.as_view(),
        name='restaurant-menu-item-detail',
    ),
    path(
        'menu-items/<int:item_id>/duplicate/',
        MenuItemDuplicateView.as_view(),
        name='restaurant-menu-item-duplicate',
    ),
    path(
        'menu-items/<int:item_id>/move/',
        MenuItemMoveView.as_view(),
        name='restaurant-menu-item-move',
    ),
    path(
        'menu-items/<int:item_id>/hide/',
        MenuItemHideView.as_view(),
        name='restaurant-menu-item-hide',
    ),
    path(
        'menu-items/<int:item_id>/availability/',
        MenuItemAvailabilityView.as_view(),
        name='restaurant-menu-item-availability',
    ),
    path('deals/', DealListCreateView.as_view(), name='restaurant-deals'),
    path(
        'deals/<int:deal_id>/',
        DealDetailView.as_view(),
        name='restaurant-deal-detail',
    ),
    path(
        'deals/<int:deal_id>/preview/',
        DealPreviewView.as_view(),
        name='restaurant-deal-preview',
    ),
]
