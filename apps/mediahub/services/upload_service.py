"""Presign / upload / delete orchestration."""

from django.conf import settings

from apps.mediahub.models import ContentMedia, MediaType
from apps.mediahub.services import r2
from core.exceptions import AppAPIException


class UploadService:
    def presign(self, *, restaurant, filename: str, content_type: str, byte_size: int, kind: str = ''):
        max_bytes = int(getattr(settings, 'MAX_UPLOAD_BYTES', 100 * 1024 * 1024))
        if byte_size <= 0 or byte_size > max_bytes:
            raise AppAPIException(
                code='INVALID_UPLOAD_SIZE',
                message=f'byte_size must be between 1 and {max_bytes}.',
                status_code=400,
            )
        expires_in = int(getattr(settings, 'PRESIGNED_UPLOAD_EXPIRES', 3600))
        key = r2.tmp_upload_key(restaurant.id, filename)
        upload_url = r2.generate_presigned_put_url(key, content_type, expires_in=expires_in)
        return {
            'key': key,
            'upload_url': upload_url,
            'public_url': r2.get_public_url(key),
            'expires_in': expires_in,
            'content_type': content_type,
            'kind': kind or '',
        }

    def delete_by_key(self, *, restaurant, key: str):
        if not key:
            raise AppAPIException(code='KEY_REQUIRED', message='key is required.', status_code=400)
        # Only allow delete under this restaurant tmp or owned prefixes
        allowed_prefixes = (
            f'uploads/tmp/{restaurant.id}/',
            f'restaurants/{restaurant.id}/',
        )
        if not any(key.startswith(p) for p in allowed_prefixes):
            raise AppAPIException(
                code='KEY_FORBIDDEN',
                message='You cannot delete this object key.',
                status_code=403,
            )
        r2.delete_object(key)
        return {'deleted': True, 'key': key}

    def delete_media(self, *, restaurant, media_id) -> dict:
        try:
            media = ContentMedia.objects.get(id=media_id, restaurant=restaurant)
        except ContentMedia.DoesNotExist:
            raise AppAPIException(
                code='MEDIA_NOT_FOUND',
                message='Media not found.',
                status_code=404,
            )
        was_cover = media.is_cover and media.media_type == MediaType.IMAGE
        menu_item_id = media.menu_item_id
        deal_id = media.deal_id

        if media.file:
            r2.delete_object(media.file.name)
        if media.thumbnail_key:
            r2.delete_object(media.thumbnail_key)
        if media.hls_master_key:
            # delete HLS tree under .../hls/
            prefix = media.hls_master_key.rsplit('/', 1)[0] + '/'
            r2.delete_prefix(prefix)

        media.delete()

        if was_cover:
            self.reassign_cover(menu_item_id=menu_item_id, deal_id=deal_id)

        return {'deleted': True, 'id': str(media_id)}

    def reassign_cover(self, *, menu_item_id=None, deal_id=None):
        qs = ContentMedia.objects.filter(media_type=MediaType.IMAGE)
        if menu_item_id:
            qs = qs.filter(menu_item_id=menu_item_id)
        elif deal_id:
            qs = qs.filter(deal_id=deal_id)
        else:
            return
        if qs.filter(is_cover=True).exists():
            return
        newest = qs.order_by('-created_at').first()
        if newest:
            newest.is_cover = True
            newest.save(update_fields=['is_cover'])
