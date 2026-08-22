from apps.accounts.admin.views.categories import (
    AdminCategoryDetailView,
    AdminCategoryListCreateView,
)
from apps.accounts.admin.views.overview import AdminOverviewView
from apps.accounts.admin.views.promotions import (
    AdminPromotionApproveView,
    AdminPromotionRejectView,
    AdminPromotionRequestListView,
    LegacyAdminPromotionApproveView,
    LegacyAdminPromotionRejectView,
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

__all__ = [
    'AdminCategoryDetailView',
    'AdminCategoryListCreateView',
    'AdminOverviewView',
    'AdminPromotionApproveView',
    'AdminPromotionRejectView',
    'AdminPromotionRequestListView',
    'AdminReportActionView',
    'AdminReportDetailView',
    'AdminReportDismissView',
    'AdminReportListView',
    'AdminRestaurantDetailView',
    'AdminRestaurantListView',
    'AdminUserDetailView',
    'AdminUserListView',
    'LegacyAdminPromotionApproveView',
    'LegacyAdminPromotionRejectView',
]
