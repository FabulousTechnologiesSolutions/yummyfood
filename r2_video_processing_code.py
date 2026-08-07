"""
REFERENCE COPY ONLY — do not import from production.

Source mirror of `process_property_video` and everything it uses:
  - apps/properties/tasks.py (RESOLUTIONS + helpers + Celery task)
  - apps/properties/services/r2.py (R2 helpers used by the task)

Original production code is unchanged.
"""

import json
import logging
import os
import shutil
import subprocess
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from celery import shared_task
from django.conf import settings
from django.core.files.storage import default_storage

from apps.properties.choices import MediaStatus, MediaType
from apps.properties.models import PropertyMedia

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Settings used by this pipeline
# ---------------------------------------------------------------------------
# FFMPEG_PATH / FFPROBE_PATH
# CLOUDFLARE_ACCOUNT_ID
# CLOUDFLARE_R2_ACCESS_KEY_ID
# CLOUDFLARE_R2_SECRET_ACCESS_KEY
# CLOUDFLARE_R2_BUCKET_NAME
# CLOUDFLARE_R2_PUBLIC_URL
# CLOUDFLARE_R2_ENDPOINT_URL


# ---------------------------------------------------------------------------
# Storage keys written by process_property_video
# ---------------------------------------------------------------------------
# storage_prefix   = properties/{property_id}/video/{media_id}
# thumbnail_key    = {storage_prefix}/thumbnail.jpg
# hls_prefix       = {storage_prefix}/hls
# master_key       = {hls_prefix}/master.m3u8
# per-quality HLS  = {hls_prefix}/{quality}/index.m3u8
#                  + segment%03d.m4s, init.mp4 under the same folder
#
# resolutions[] item keys (saved on PropertyMedia.resolutions JSON):
#   quality, height, width, bandwidth, hlsKey, hlsUrl
#
# PropertyMedia fields updated on success:
#   processing_status, duration, thumbnail_key, thumbnail_url,
#   hls_master_key, hls_master_url, resolutions, processing_error
#
# Content types:
#   thumbnail.jpg  -> image/jpeg
#   *.m3u8         -> application/vnd.apple.mpegurl
#   *.m4s          -> video/iso.segment
#   *.mp4          -> video/mp4


# ===========================================================================
# From apps/properties/tasks.py
# ===========================================================================

RESOLUTIONS = [
    {'quality': '240p', 'height': 240, 'video_bitrate': '400k', 'audio_bitrate': '64k', 'bandwidth': 464000},
    {'quality': '360p', 'height': 360, 'video_bitrate': '800k', 'audio_bitrate': '96k', 'bandwidth': 896000},
    {'quality': '480p', 'height': 480, 'video_bitrate': '1400k', 'audio_bitrate': '128k', 'bandwidth': 1528000},
    {'quality': '720p', 'height': 720, 'video_bitrate': '2800k', 'audio_bitrate': '128k', 'bandwidth': 2928000},
    {'quality': '1080p', 'height': 1080, 'video_bitrate': '5000k', 'audio_bitrate': '192k', 'bandwidth': 5192000},
]


def _run_command(cmd, label='ffmpeg'):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f'{label} failed: {result.stderr or result.stdout}')
    return result


def probe_video(input_source):
    cmd = [
        settings.FFPROBE_PATH,
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_format',
        '-show_streams',
        input_source,
    ]
    result = _run_command(cmd, 'ffprobe')
    data = json.loads(result.stdout)
    video_stream = next(
        (s for s in data.get('streams', []) if s.get('codec_type') == 'video'),
        {},
    )
    return {
        'width': int(video_stream.get('width') or 1280),
        'height': int(video_stream.get('height') or 720),
        'duration': float(data.get('format', {}).get('duration') or 0),
    }


def generate_hls_for_resolution(input_source, output_dir, res):
    res_dir = os.path.join(output_dir, res['quality'])
    os.makedirs(res_dir, exist_ok=True)
    segment_pattern = os.path.join(res_dir, 'segment%03d.m4s')
    playlist_path = os.path.join(res_dir, 'index.m3u8')

    cmd = [
        settings.FFMPEG_PATH,
        '-y',
        '-i', input_source,
        '-vf', f"scale=-2:{res['height']}",
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-preset', 'veryfast',
        '-crf', '23',
        '-b:v', res['video_bitrate'],
        '-b:a', res['audio_bitrate'],
        '-hls_time', '4',
        '-hls_playlist_type', 'vod',
        '-hls_segment_type', 'fmp4',
        '-hls_fmp4_init_filename', 'init.mp4',
        '-hls_segment_filename', segment_pattern,
        '-hls_flags', 'independent_segments',
        '-f', 'hls',
        playlist_path,
    ]
    _run_command(cmd)


def generate_thumbnail(input_source, output_path):
    cmd = [
        settings.FFMPEG_PATH,
        '-y',
        '-ss', '00:00:02',
        '-i', input_source,
        '-vframes', '1',
        '-q:v', '2',
        '-vf', 'scale=-2:720',
        output_path,
    ]
    _run_command(cmd)


def build_master_playlist(applicable, source_width, source_height):
    lines = ['#EXTM3U', '#EXT-X-VERSION:3', '']
    for res in reversed(applicable):
        width = round((source_width / source_height) * res['height'])
        lines.append(
            f'#EXT-X-STREAM-INF:BANDWIDTH={res["bandwidth"]},'
            f'RESOLUTION={width}x{res["height"]},NAME="{res["quality"]}"'
        )
        lines.append(f'{res["quality"]}/index.m3u8')
        lines.append('')
    return '\n'.join(lines)


def _process_resolution(input_source, hls_dir, res, prefix):
    generate_hls_for_resolution(input_source, hls_dir, res)
    res_dir = os.path.join(hls_dir, res['quality'])
    upload_directory(res_dir, f'{prefix}/{res["quality"]}', get_content_type)
    shutil.rmtree(res_dir, ignore_errors=True)


def _download_original_to_temp(media):
    suffix = os.path.splitext(media.file.name)[1] or '.mp4'
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    with default_storage.open(media.file.name, 'rb') as src, open(path, 'wb') as dst:
        shutil.copyfileobj(src, dst)
    return path


@shared_task(
    bind=True,
    name='process_property_video',
    max_retries=3,
    default_retry_delay=5,
    retry_backoff=True,
    retry_backoff_max=60,
)
def process_property_video(self, media_id):
    tmp_dir = os.path.join(tempfile.gettempdir(), f'propvid-{uuid.uuid4()}')
    hls_dir = os.path.join(tmp_dir, 'hls')
    thumb_path = os.path.join(tmp_dir, 'thumb.jpg')
    original_path = None

    try:
        media = PropertyMedia.objects.get(id=media_id, type=MediaType.VIDEO)
        if not media.is_feed_video:
            return
        media.processing_status = MediaStatus.PROCESSING
        media.save(update_fields=['processing_status'])

        os.makedirs(hls_dir, exist_ok=True)
        original_path = _download_original_to_temp(media)

        meta = probe_video(original_path)
        source_width = meta['width']
        source_height = meta['height']
        duration = meta['duration']

        generate_thumbnail(original_path, thumb_path)
        storage_prefix = f'properties/{media.property_id}/video/{media.id}'
        thumbnail_key = f'{storage_prefix}/thumbnail.jpg'
        upload_local_file(thumbnail_key, thumb_path, 'image/jpeg')

        applicable = [r for r in RESOLUTIONS if r['height'] <= source_height]
        if not applicable:
            applicable = [RESOLUTIONS[0]]

        hls_prefix = f'{storage_prefix}/hls'

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(_process_resolution, original_path, hls_dir, res, hls_prefix)
                for res in applicable
            ]
            for future in as_completed(futures):
                future.result()

        master_content = build_master_playlist(applicable, source_width, source_height)
        master_path = os.path.join(hls_dir, 'master.m3u8')
        with open(master_path, 'w', encoding='utf-8') as f:
            f.write(master_content)

        master_key = f'{hls_prefix}/master.m3u8'
        upload_local_file(master_key, master_path, 'application/vnd.apple.mpegurl')

        resolutions = []
        for res in applicable:
            width = round((source_width / source_height) * res['height'])
            hls_key = f'{hls_prefix}/{res["quality"]}/index.m3u8'
            resolutions.append({
                'quality': res['quality'],
                'height': res['height'],
                'width': width,
                'bandwidth': res['bandwidth'],
                'hlsKey': hls_key,
                'hlsUrl': get_public_url(hls_key),
            })

        media.processing_status = MediaStatus.READY
        media.duration = duration
        media.thumbnail_key = thumbnail_key
        media.thumbnail_url = get_public_url(thumbnail_key)
        media.hls_master_key = master_key
        media.hls_master_url = get_public_url(master_key)
        media.resolutions = resolutions
        media.processing_error = ''
        media.save(update_fields=[
            'processing_status', 'duration', 'thumbnail_key', 'thumbnail_url',
            'hls_master_key', 'hls_master_url', 'resolutions', 'processing_error',
        ])
        from apps.notifications.services.notification_service import NotificationService
        NotificationService.notify_video_ready(media.property)
    except Exception as exc:
        logger.exception('Property video processing failed for %s', media_id)
        if self.request.retries >= self.max_retries:
            PropertyMedia.objects.filter(id=media_id).update(
                processing_status=MediaStatus.FAILED,
                processing_error=str(exc),
            )
            try:
                media = PropertyMedia.objects.select_related('property__dealer__user').get(id=media_id)
                from apps.notifications.services.notification_service import NotificationService
                NotificationService.notify_video_failed(media.property, str(exc))
            except PropertyMedia.DoesNotExist:
                pass
            raise
        raise self.retry(exc=exc) from exc
    finally:
        if original_path and os.path.exists(original_path):
            os.remove(original_path)
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ===========================================================================
# From apps/properties/services/r2.py (methods used by the task)
# ===========================================================================

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


def get_public_url(key):
    base = (settings.CLOUDFLARE_R2_PUBLIC_URL or '').rstrip('/')
    return f'{base}/{key}'


def upload_file_stream(key, body, content_type):
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
    }
    return mapping.get(ext, 'application/octet-stream')
