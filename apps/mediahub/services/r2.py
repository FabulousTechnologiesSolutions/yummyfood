"""R2 / storage helpers for uploads and HLS video pipeline."""

import logging
import os
import uuid
from pathlib import Path
from urllib.parse import urlparse

import boto3
from botocore.config import Config
from django.conf import settings
from django.core.files.storage import default_storage

logger = logging.getLogger(__name__)


def use_local_media() -> bool:
    backend = settings.STORAGES.get('default', {}).get('BACKEND', '')
    return (
        os.getenv('USE_LOCAL_MEDIA', '').lower() in ('true', '1', 'yes')
        or 'FileSystemStorage' in backend
    )


def _get_r2_client():
    if not all([
        settings.CLOUDFLARE_ACCOUNT_ID,
        settings.CLOUDFLARE_R2_ACCESS_KEY_ID,
        settings.CLOUDFLARE_R2_SECRET_ACCESS_KEY,
        settings.CLOUDFLARE_R2_BUCKET_NAME,
    ]):
        raise RuntimeError(
            'Cloudflare R2 storage is not configured. Set CLOUDFLARE_ACCOUNT_ID, '
            'CLOUDFLARE_R2_ACCESS_KEY_ID, CLOUDFLARE_R2_SECRET_ACCESS_KEY, and '
            'CLOUDFLARE_R2_BUCKET_NAME.',
        )
    return boto3.client(
        's3',
        region_name='auto',
        endpoint_url=settings.CLOUDFLARE_R2_ENDPOINT_URL,
        aws_access_key_id=settings.CLOUDFLARE_R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.CLOUDFLARE_R2_SECRET_ACCESS_KEY,
        config=Config(signature_version='s3v4'),
    )


def get_public_url(key: str) -> str:
    if use_local_media():
        media_url = (settings.MEDIA_URL or '/media/').rstrip('/')
        return f'{media_url}/{key.lstrip("/")}'
    base = (settings.CLOUDFLARE_R2_PUBLIC_URL or '').rstrip('/')
    if not base:
        try:
            return default_storage.url(key)
        except Exception:
            return key
    return f'{base}/{key}'


def upload_file_stream(key, body, content_type):
    if use_local_media():
        from django.core.files.base import ContentFile

        data = body.read() if hasattr(body, 'read') else body
        default_storage.save(key, ContentFile(data))
        return
    client = _get_r2_client()
    client.put_object(
        Bucket=settings.CLOUDFLARE_R2_BUCKET_NAME,
        Key=key,
        Body=body,
        ContentType=content_type,
    )


def upload_local_file(key, local_path, content_type):
    with open(local_path, 'rb') as f:
        upload_file_stream(key, f, content_type)


def upload_directory(local_dir, r2_prefix, content_type_fn):
    local_path = Path(local_dir)
    upload_tasks = []

    for entry in local_path.iterdir():
        r2_key = f'{r2_prefix}/{entry.name}'
        if entry.is_dir():
            upload_directory(str(entry), r2_key, content_type_fn)
        else:
            upload_tasks.append((r2_key, str(entry), content_type_fn(entry.name)))

    for r2_key, path, ctype in upload_tasks:
        upload_local_file(r2_key, path, ctype)


def get_content_type(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    mapping = {
        '.m3u8': 'application/vnd.apple.mpegurl',
        '.ts': 'video/mp2t',
        '.m4s': 'video/iso.segment',
        '.mp4': 'video/mp4',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.webp': 'image/webp',
    }
    return mapping.get(ext, 'application/octet-stream')


def delete_object(key: str) -> None:
    if not key:
        return
    if use_local_media():
        if default_storage.exists(key):
            default_storage.delete(key)
        return
    try:
        client = _get_r2_client()
        client.delete_object(Bucket=settings.CLOUDFLARE_R2_BUCKET_NAME, Key=key)
    except Exception:
        logger.exception('Failed to delete R2 object %s', key)


def delete_prefix(prefix: str) -> None:
    """Best-effort delete of objects under a prefix (HLS leftovers)."""
    if not prefix:
        return
    if use_local_media():
        # Local: walk MEDIA_ROOT under prefix if possible
        root = Path(settings.MEDIA_ROOT) / prefix
        if root.is_dir():
            for path in root.rglob('*'):
                if path.is_file():
                    rel = str(path.relative_to(settings.MEDIA_ROOT))
                    delete_object(rel)
            return
        # Try deleting known keys via storage
        return
    try:
        client = _get_r2_client()
        bucket = settings.CLOUDFLARE_R2_BUCKET_NAME
        paginator = client.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get('Contents', []):
                client.delete_object(Bucket=bucket, Key=obj['Key'])
    except Exception:
        logger.exception('Failed to delete R2 prefix %s', prefix)


def generate_presigned_put_url(key: str, content_type: str, expires_in: int = 3600) -> str:
    if use_local_media():
        # Client uploads via local endpoint using this key.
        return f'/api/restaurant/uploads/local/?key={key}'
    client = _get_r2_client()
    return client.generate_presigned_url(
        'put_object',
        Params={
            'Bucket': settings.CLOUDFLARE_R2_BUCKET_NAME,
            'Key': key,
            'ContentType': content_type,
        },
        ExpiresIn=expires_in,
    )


def parse_storage_key_from_url(url: str) -> str:
    """Extract object key from a public URL or path."""
    if not url:
        raise ValueError('empty url')
    raw = url.strip()
    # Already a key
    if '://' not in raw and not raw.startswith('/'):
        return raw.lstrip('/')

    parsed = urlparse(raw)
    path = parsed.path.lstrip('/')

    media_prefix = (settings.MEDIA_URL or '/media/').strip('/')
    if media_prefix and path.startswith(media_prefix + '/'):
        return path[len(media_prefix) + 1 :]
    if path.startswith('media/'):
        return path[len('media/') :]

    public = (settings.CLOUDFLARE_R2_PUBLIC_URL or '').rstrip('/')
    if public:
        public_host = urlparse(public if '://' in public else f'https://{public}').netloc
        if parsed.netloc and parsed.netloc == public_host:
            return path

    # Fallback: last useful path segment chain after known roots
    for marker in ('uploads/', 'restaurants/', 'mediahub/'):
        idx = path.find(marker)
        if idx >= 0:
            return path[idx:]
    return path


def tmp_upload_key(restaurant_id, filename: str) -> str:
    safe_name = Path(filename).name.replace(' ', '_')
    return f'uploads/tmp/{restaurant_id}/{uuid.uuid4().hex}_{safe_name}'


def final_media_key(restaurant_id, entity_kind: str, entity_id, media_id, filename: str) -> str:
    safe_name = Path(filename).name.replace(' ', '_')
    return (
        f'restaurants/{restaurant_id}/{entity_kind}/{entity_id}/'
        f'media/{media_id}/{safe_name}'
    )


def video_storage_prefix(restaurant_id, entity_kind: str, entity_id, media_id) -> str:
    return f'restaurants/{restaurant_id}/{entity_kind}/{entity_id}/video/{media_id}'
