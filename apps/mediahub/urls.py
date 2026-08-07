from django.urls import path

from apps.mediahub.views import (
    DeleteMediaView,
    DeleteUploadView,
    LocalUploadView,
    PresignUploadView,
)

urlpatterns = [
    path('uploads/presign/', PresignUploadView.as_view(), name='restaurant-upload-presign'),
    path('uploads/', DeleteUploadView.as_view(), name='restaurant-upload-delete'),
    path('uploads/local/', LocalUploadView.as_view(), name='restaurant-upload-local'),
    path('media/<uuid:media_id>/', DeleteMediaView.as_view(), name='restaurant-media-delete'),
]
