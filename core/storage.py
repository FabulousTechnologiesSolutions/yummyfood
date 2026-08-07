from urllib.parse import urlparse

from storages.backends.s3boto3 import S3Boto3Storage


def normalize_r2_public_domain(public_url: str) -> str | None:
    """Return hostname (no scheme) from an R2 public URL."""
    if not public_url:
        return None
    parsed = urlparse(public_url if '://' in public_url else f'https://{public_url}')
    return parsed.netloc or None


class CloudflareR2Storage(S3Boto3Storage):
    """Thin S3-compatible storage stub for Cloudflare R2."""

    addressing_style = 'path'
