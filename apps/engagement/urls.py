from django.urls import path

from apps.engagement.views import SavedDetailView, SavedListCreateView

urlpatterns = [
    path('saved/', SavedListCreateView.as_view(), name='saved-list-create'),
    path('saved/<int:saved_id>/', SavedDetailView.as_view(), name='saved-detail'),
]
