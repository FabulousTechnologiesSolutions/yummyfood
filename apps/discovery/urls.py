from django.urls import path

from apps.discovery.views import ExploreProductsView

urlpatterns = [
    path(
        'explore/products/',
        ExploreProductsView.as_view(),
        name='explore-products',
    ),
]
