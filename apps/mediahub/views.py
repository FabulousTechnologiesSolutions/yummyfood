from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAuthenticatedAndActive
from apps.mediahub.serializers import DeleteKeySerializer, PresignSerializer
from apps.mediahub.services import UploadService
from core.exceptions import AppAPIException
from core.permissions import IsRestaurantMode, IsRestaurantOwner


class RestaurantOwnerMixin:
    permission_classes = [IsAuthenticatedAndActive, IsRestaurantOwner, IsRestaurantMode]

    def get_restaurant(self, request):
        restaurant = getattr(request.user, 'restaurant', None)
        if restaurant is None:
            raise AppAPIException(
                code='RESTAURANT_REQUIRED',
                message='Restaurant profile required.',
                status_code=403,
            )
        return restaurant


class PresignUploadView(RestaurantOwnerMixin, APIView):
    @extend_schema(request=PresignSerializer)
    def post(self, request):
        serializer = PresignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        result = UploadService().presign(
            restaurant=self.get_restaurant(request),
            filename=data['filename'],
            content_type=data['content_type'],
            byte_size=data['byte_size'],
            kind=data.get('kind') or '',
        )
        return Response(result, status=status.HTTP_200_OK)


class DeleteUploadView(RestaurantOwnerMixin, APIView):
    @extend_schema(request=DeleteKeySerializer)
    def delete(self, request):
        serializer = DeleteKeySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = UploadService().delete_by_key(
            restaurant=self.get_restaurant(request),
            key=serializer.validated_data['key'],
        )
        return Response(result, status=status.HTTP_200_OK)


class DeleteMediaView(RestaurantOwnerMixin, APIView):
    def delete(self, request, media_id):
        result = UploadService().delete_media(
            restaurant=self.get_restaurant(request),
            media_id=media_id,
        )
        return Response(result, status=status.HTTP_200_OK)


class LocalUploadView(RestaurantOwnerMixin, APIView):
    """Dev/test upload target when USE_LOCAL_MEDIA=true."""

    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticatedAndActive, IsRestaurantOwner, IsRestaurantMode]

    def put(self, request):
        key = request.query_params.get('key') or request.data.get('key')
        if not key:
            raise AppAPIException(code='KEY_REQUIRED', message='key is required.', status_code=400)
        restaurant = self.get_restaurant(request)
        if not key.startswith(f'uploads/tmp/{restaurant.id}/'):
            raise AppAPIException(code='KEY_FORBIDDEN', message='Invalid upload key.', status_code=403)
        upload = request.FILES.get('file') or request.FILES.get('upload')
        if upload is None and request.body:
            default_storage.save(key, ContentFile(request.body))
        elif upload is not None:
            default_storage.save(key, ContentFile(upload.read()))
        else:
            raise AppAPIException(code='FILE_REQUIRED', message='file is required.', status_code=400)
        from apps.mediahub.services import r2

        return Response({'key': key, 'public_url': r2.get_public_url(key)}, status=status.HTTP_200_OK)

    def post(self, request):
        return self.put(request)
