from django.urls import path

from apps.accounts.admin.views.categories import (
    AdminCategoryDetailView,
    AdminCategoryListCreateView,
)
from apps.accounts.admin.views.overview import AdminOverviewView
from apps.accounts.admin.views.promotions import (
    AdminPromotionApproveView,
    AdminPromotionRejectView,
    AdminPromotionRequestListView,
)
from apps.accounts.admin.views.reports import (
    AdminReportActionView,
    AdminReportDetailView,
    AdminReportDismissView,
    AdminReportListView,
)
from apps.accounts.admin.views.restaurants import (
    AdminRestaurantDetailView,
    AdminRestaurantListView,
)
from apps.accounts.admin.views.users import AdminUserDetailView, AdminUserListView

urlpatterns = [
    path('overview/', AdminOverviewView.as_view(), name='admin-overview'),
    path('reports/', AdminReportListView.as_view(), name='admin-reports'),
    path('reports/<int:report_id>/', AdminReportDetailView.as_view(), name='admin-report-detail'),
    path(
        'reports/<int:report_id>/action/',
        AdminReportActionView.as_view(),
        name='admin-report-action',
    ),
    path(
        'reports/<int:report_id>/dismiss/',
        AdminReportDismissView.as_view(),
        name='admin-report-dismiss',
    ),
    path(
        'promotion-requests/',
        AdminPromotionRequestListView.as_view(),
        name='platform-admin-promotion-requests',
    ),
    path(
        'promotion-requests/<int:request_id>/approve/',
        AdminPromotionApproveView.as_view(),
        name='platform-admin-promotion-approve',
    ),
    path(
        'promotion-requests/<int:request_id>/reject/',
        AdminPromotionRejectView.as_view(),
        name='platform-admin-promotion-reject',
    ),
    path('restaurants/', AdminRestaurantListView.as_view(), name='admin-restaurants'),
    path(
        'restaurants/<int:restaurant_id>/',
        AdminRestaurantDetailView.as_view(),
        name='admin-restaurant-detail',
    ),
    path('users/', AdminUserListView.as_view(), name='admin-users'),
    path('users/<int:user_id>/', AdminUserDetailView.as_view(), name='admin-user-detail'),
    path('categories/', AdminCategoryListCreateView.as_view(), name='admin-categories'),
    path(
        'categories/<int:category_id>/',
        AdminCategoryDetailView.as_view(),
        name='admin-category-detail',
    ),
]
