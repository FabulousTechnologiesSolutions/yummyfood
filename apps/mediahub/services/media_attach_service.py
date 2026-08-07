"""Attach / sync ContentMedia rows for menu items and deals."""

from django.conf import settings
from django.db import transaction

from apps.mediahub.models import (
    ContentMedia,
    MediaEntityType,
    MediaProcessingStatus,
    MediaType,
)
from apps.mediahub.services import r2
from core.exceptions import AppAPIException

MAX_VIDEO_SECONDS = 60


def _validate_media_payload(media_list: list) -> None:
    if not media_list:
        raise AppAPIException(
            code='MEDIA_REQUIRED',
            message='At least one image and one video are required.',
            status_code=400,
        )
    images = [m for m in media_list if m.get('type') == MediaType.IMAGE]
    videos = [m for m in media_list if m.get('type') == MediaType.VIDEO]
    if len(images) < 1:
        raise AppAPIException(
            code='MEDIA_REQUIRED',
            message='At least one image is required.',
            status_code=400,
        )
    if len(videos) != 1:
        raise AppAPIException(
            code='VIDEO_REQUIRED',
            message='Exactly one video is required.',
            status_code=400,
        )
    covers = [m for m in images if m.get('is_cover')]
    if len(covers) > 1:
        raise AppAPIException(
            code='INVALID_COVER',
            message='Only one cover image is allowed.',
            status_code=400,
        )


def serialize_media(media: ContentMedia) -> dict:
    return {
        'id': str(media.id),
        'type': media.media_type,
        'url': media.public_url or (r2.get_public_url(media.file.name) if media.file else ''),
        'is_cover': media.is_cover,
        'order_index': media.order_index,
        'processing_status': media.processing_status,
        'duration': media.duration,
        'thumbnail_url': media.thumbnail_url,
        'hls_master_url': media.hls_master_url,
        'resolutions': media.resolutions,
    }


class MediaAttachService:
    def validate_payload(self, media_list: list) -> None:
        _validate_media_payload(media_list)

    @transaction.atomic
    def sync_for_menu_item(self, *, restaurant, menu_item, media_list: list, enqueue_videos: bool = True):
        return self._sync(
            restaurant=restaurant,
            entity_type=MediaEntityType.MENU_ITEM,
            menu_item=menu_item,
            deal=None,
            entity_kind='items',
            entity_id=menu_item.id,
            media_list=media_list,
            enqueue_videos=enqueue_videos,
        )

    @transaction.atomic
    def sync_for_deal(self, *, restaurant, deal, media_list: list, enqueue_videos: bool = True):
        return self._sync(
            restaurant=restaurant,
            entity_type=MediaEntityType.DEAL,
            menu_item=None,
            deal=deal,
            entity_kind='deals',
            entity_id=deal.id,
            media_list=media_list,
            enqueue_videos=enqueue_videos,
        )

    def _sync(
        self,
        *,
        restaurant,
        entity_type,
        menu_item,
        deal,
        entity_kind,
        entity_id,
        media_list,
        enqueue_videos,
    ):
        _validate_media_payload(media_list)

        existing_qs = ContentMedia.objects.filter(restaurant=restaurant)
        if menu_item is not None:
            existing_qs = existing_qs.filter(menu_item=menu_item)
        else:
            existing_qs = existing_qs.filter(deal=deal)
        existing_by_id = {str(m.id): m for m in existing_qs}

        keep_ids = set()
        created = []
        order = 0
        has_cover = any(
            m.get('type') == MediaType.IMAGE and m.get('is_cover') for m in media_list
        )

        for idx, entry in enumerate(media_list):
            media_type = entry['type']
            media_id = entry.get('id')
            is_cover = bool(entry.get('is_cover')) if media_type == MediaType.IMAGE else False
            if media_type == MediaType.IMAGE and not has_cover and idx == 0:
                is_cover = True

            if media_id and str(media_id) in existing_by_id:
                media = existing_by_id[str(media_id)]
                media.order_index = order
                media.is_cover = is_cover
                media.save(update_fields=['order_index', 'is_cover'])
                keep_ids.add(str(media.id))
                order += 1
                continue

            url = entry.get('url') or ''
            try:
                source_key = r2.parse_storage_key_from_url(url)
            except ValueError:
                raise AppAPIException(
                    code='INVALID_MEDIA_URL',
                    message='media.url is invalid.',
                    status_code=400,
                )

            media = ContentMedia(
                restaurant=restaurant,
                entity_type=entity_type,
                menu_item=menu_item,
                deal=deal,
                media_type=media_type,
                order_index=order,
                is_cover=is_cover,
                is_feed_video=(media_type == MediaType.VIDEO),
                processing_status=(
                    MediaProcessingStatus.PENDING
                    if media_type == MediaType.VIDEO
                    else MediaProcessingStatus.EMPTY
                ),
            )
            media.save()

            filename = source_key.rsplit('/', 1)[-1]
            dest_key = r2.final_media_key(
                restaurant.id, entity_kind, entity_id, media.id, filename
            )
            # Prefer rename/copy within storage when possible
            self._place_file(media, source_key, dest_key)
            keep_ids.add(str(media.id))
            created.append(media)
            order += 1

        # Delete omitted
        for mid, media in existing_by_id.items():
            if mid not in keep_ids:
                was_cover = media.is_cover and media.media_type == MediaType.IMAGE
                if media.file:
                    r2.delete_object(media.file.name)
                if media.thumbnail_key:
                    r2.delete_object(media.thumbnail_key)
                if media.hls_master_key:
                    prefix = media.hls_master_key.rsplit('/', 1)[0] + '/'
                    r2.delete_prefix(prefix)
                media.delete()
                if was_cover:
                    from apps.mediahub.services.upload_service import UploadService

                    UploadService().reassign_cover(
                        menu_item_id=menu_item.id if menu_item else None,
                        deal_id=deal.id if deal else None,
                    )

        if enqueue_videos:
            for media in ContentMedia.objects.filter(
                restaurant=restaurant,
                media_type=MediaType.VIDEO,
                is_feed_video=True,
                processing_status=MediaProcessingStatus.PENDING,
                **({'menu_item': menu_item} if menu_item else {'deal': deal}),
            ):
                from apps.mediahub.tasks import process_content_video

                process_content_video.delay(str(media.id))

        return list(
            ContentMedia.objects.filter(
                restaurant=restaurant,
                **({'menu_item': menu_item} if menu_item else {'deal': deal}),
            )
        )

    def _place_file(self, media: ContentMedia, source_key: str, dest_key: str):
        from django.core.files.base import ContentFile
        from django.core.files.storage import default_storage

        if source_key == dest_key:
            media.file.name = dest_key
            media.save(update_fields=['file'])
            return

        if default_storage.exists(source_key):
            with default_storage.open(source_key, 'rb') as src:
                default_storage.save(dest_key, ContentFile(src.read()))
            # Keep tmp for safety in concurrent uploads; optional cleanup
            if source_key.startswith('uploads/tmp/'):
                try:
                    default_storage.delete(source_key)
                except Exception:
                    pass
        else:
            # Assume client uploaded to dest already, or key is logical
            dest_key = source_key

        media.file.name = dest_key
        media.save(update_fields=['file'])
