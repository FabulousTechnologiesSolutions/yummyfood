from django.urls import path

from apps.feed.views import FeedProductsView, FeedSeenBatchView

urlpatterns = [
    path(
        'feed/products/',
        FeedProductsView.as_view(),
        name='feed-products',
    ),
    path(
        'feed/seen/batch/',
        FeedSeenBatchView.as_view(),
        name='feed-seen-batch',
    ),
]
