import uuid

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from apps.mediahub.models import ContentMedia, MediaEntityType, MediaType
from apps.mediahub.services.upload_service import UploadService
from apps.restaurants.models import MenuCategory, MenuItem, MenuItemSize


@pytest.mark.django_db
def test_presign_local(auth_client, restaurant_user):
    client = auth_client(restaurant_user)
    res = client.post(
        '/api/restaurant/uploads/presign/',
        {
            'filename': 'photo.jpg',
            'content_type': 'image/jpeg',
            'byte_size': 1024,
        },
        format='json',
    )
    assert res.status_code == 200
    assert 'key' in res.data
    assert res.data['key'].startswith(f'uploads/tmp/{restaurant_user.restaurant.id}/')
    assert 'upload_url' in res.data
    assert 'public_url' in res.data


@pytest.mark.django_db
def test_delete_upload_key(auth_client, restaurant_user):
    restaurant = restaurant_user.restaurant
    key = f'uploads/tmp/{restaurant.id}/{uuid.uuid4().hex}_x.jpg'
    default_storage.save(key, ContentFile(b'data'))
    client = auth_client(restaurant_user)
    res = client.delete('/api/restaurant/uploads/', {'key': key}, format='json')
    assert res.status_code == 200
    assert res.data['deleted'] is True


@pytest.mark.django_db
def test_cover_reassignment_on_media_delete(restaurant_user):
    restaurant = restaurant_user.restaurant
    category = MenuCategory.objects.first()
    item = MenuItem.objects.create(
        restaurant=restaurant,
        name='T',
        base_price='10.00',
    )
    if category:
        item.categories.add(category)
    MenuItemSize.objects.create(menu_item=item, label='R', price='10.00')

    key1 = f'restaurants/{restaurant.id}/items/{item.id}/media/{uuid.uuid4().hex}/a.jpg'
    key2 = f'restaurants/{restaurant.id}/items/{item.id}/media/{uuid.uuid4().hex}/b.jpg'
    default_storage.save(key1, ContentFile(b'a'))
    default_storage.save(key2, ContentFile(b'b'))

    m1 = ContentMedia.objects.create(
        restaurant=restaurant,
        entity_type=MediaEntityType.MENU_ITEM,
        menu_item=item,
        media_type=MediaType.IMAGE,
        is_cover=True,
        order_index=0,
    )
    m1.file.name = key1
    m1.save(update_fields=['file'])

    m2 = ContentMedia.objects.create(
        restaurant=restaurant,
        entity_type=MediaEntityType.MENU_ITEM,
        menu_item=item,
        media_type=MediaType.IMAGE,
        is_cover=False,
        order_index=1,
    )
    m2.file.name = key2
    m2.save(update_fields=['file'])

    UploadService().delete_media(restaurant=restaurant, media_id=m1.id)
    m2.refresh_from_db()
    assert m2.is_cover is True


@pytest.mark.django_db
def test_process_content_video_mocked(monkeypatch, restaurant_user):
    called = {}

    def fake_delay(media_id):
        called['id'] = media_id

    monkeypatch.setattr('apps.mediahub.tasks.process_content_video.delay', fake_delay)

    from apps.mediahub.services.media_attach_service import MediaAttachService
    from apps.restaurants.models import MenuCategory, MenuItem, MenuItemSize

    restaurant = restaurant_user.restaurant
    category = MenuCategory.objects.first()
    item = MenuItem.objects.create(
        restaurant=restaurant,
        name='Vid',
        base_price='1.00',
    )
    if category:
        item.categories.add(category)
    MenuItemSize.objects.create(menu_item=item, label='R', price='1.00')

    img = f'uploads/tmp/{restaurant.id}/{uuid.uuid4().hex}.jpg'
    vid = f'uploads/tmp/{restaurant.id}/{uuid.uuid4().hex}.mp4'
    default_storage.save(img, ContentFile(b'i'))
    default_storage.save(vid, ContentFile(b'v'))

    MediaAttachService().sync_for_menu_item(
        restaurant=restaurant,
        menu_item=item,
        media_list=[
            {'type': 'image', 'url': img, 'is_cover': True},
            {'type': 'video', 'url': vid},
        ],
    )
    assert 'id' in called
