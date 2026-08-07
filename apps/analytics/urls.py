from django.urls import path

from apps.analytics.views import AnalyticsEventView

urlpatterns = [
    path('analytics/event/', AnalyticsEventView.as_view(), name='analytics-event'),
]
