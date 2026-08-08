"""Feed viewer identity — copied from discovery (isolated module)."""

import hashlib
from dataclasses import dataclass

from django.conf import settings


@dataclass(frozen=True)
class ViewerIdentity:
    user_id: int | None = None
    ip_hash: str | None = None

    @property
    def is_authenticated(self) -> bool:
        return self.user_id is not None


def _client_ip(request) -> str:
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR') or '0.0.0.0'


def hash_ip(ip: str) -> str:
    salt = getattr(settings, 'VIEWER_IP_HASH_SALT', settings.SECRET_KEY)
    raw = f'{salt}:{ip}'.encode()
    return hashlib.sha256(raw).hexdigest()


def resolve_viewer(request) -> ViewerIdentity:
    user = getattr(request, 'user', None)
    if user is not None and getattr(user, 'is_authenticated', False):
        return ViewerIdentity(user_id=user.pk)
    return ViewerIdentity(ip_hash=hash_ip(_client_ip(request)))
