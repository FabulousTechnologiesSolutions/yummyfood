"""Celery HLS video processing for ContentMedia."""

import json
import logging
import os
import shutil
import subprocess
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

from celery import shared_task
from django.conf import settings
from django.core.files.storage import default_storage

from apps.mediahub.models import ContentMedia, MediaProcessingStatus, MediaType
from apps.mediahub.services.r2 import (
    get_content_type,
    get_public_url,
    upload_directory,
    upload_local_file,
    video_storage_prefix,
)

logger = logging.getLogger(__name__)

RESOLUTIONS = [
    {'quality': '240p', 'height': 240, 'video_bitrate': '400k', 'audio_bitrate': '64k', 'bandwidth': 464000},
    {'quality': '360p', 'height': 360, 'video_bitrate': '800k', 'audio_bitrate': '96k', 'bandwidth': 896000},
    {'quality': '480p', 'height': 480, 'video_bitrate': '1400k', 'audio_bitrate': '128k', 'bandwidth': 1528000},
    {'quality': '720p', 'height': 720, 'video_bitrate': '2800k', 'audio_bitrate': '128k', 'bandwidth': 2928000},
    {'quality': '1080p', 'height': 1080, 'video_bitrate': '5000k', 'audio_bitrate': '192k', 'bandwidth': 5192000},
]

MAX_VIDEO_SECONDS = 60


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


def _entity_kind(media: ContentMedia) -> str:
    if media.menu_item_id:
        return 'items'
    return 'deals'


def _entity_id(media: ContentMedia):
    return media.menu_item_id or media.deal_id


@shared_task(
    bind=True,
    name='process_content_video',
    max_retries=3,
    default_retry_delay=5,
    retry_backoff=True,
    retry_backoff_max=60,
)
def process_content_video(self, media_id):
    tmp_dir = os.path.join(tempfile.gettempdir(), f'contentvid-{uuid.uuid4()}')
    hls_dir = os.path.join(tmp_dir, 'hls')
    thumb_path = os.path.join(tmp_dir, 'thumb.jpg')
    original_path = None

    try:
        media = ContentMedia.objects.get(id=media_id, media_type=MediaType.VIDEO)
        if not media.is_feed_video:
            return
        media.processing_status = MediaProcessingStatus.PROCESSING
        media.save(update_fields=['processing_status'])

        os.makedirs(hls_dir, exist_ok=True)
        original_path = _download_original_to_temp(media)

        meta = probe_video(original_path)
        source_width = meta['width']
        source_height = meta['height']
        duration = meta['duration']

        if duration > MAX_VIDEO_SECONDS:
            raise RuntimeError(f'Video duration {duration:.1f}s exceeds {MAX_VIDEO_SECONDS}s limit.')

        generate_thumbnail(original_path, thumb_path)
        storage_prefix = video_storage_prefix(
            media.restaurant_id,
            _entity_kind(media),
            _entity_id(media),
            media.id,
        )
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

        media.processing_status = MediaProcessingStatus.READY
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
        logger.info('Content video ready: %s', media_id)
    except Exception as exc:
        logger.exception('Content video processing failed for %s', media_id)
        if self.request.retries >= self.max_retries:
            ContentMedia.objects.filter(id=media_id).update(
                processing_status=MediaProcessingStatus.FAILED,
                processing_error=str(exc),
            )
            logger.error('Content video permanently failed: %s — %s', media_id, exc)
            raise
        raise self.retry(exc=exc) from exc
    finally:
        if original_path and os.path.exists(original_path):
            os.remove(original_path)
        shutil.rmtree(tmp_dir, ignore_errors=True)
