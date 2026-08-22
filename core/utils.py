"""Shared helpers: phone E.164, geo distance, etc."""
import math
import re

from core.exceptions import AppAPIException


_PK_LOCAL = re.compile(r'^0?3\d{9}$')
_E164_PK = re.compile(r'^\+923\d{9}$')
_E164_GENERIC = re.compile(r'^\+[1-9]\d{7,14}$')


def normalize_phone(phone: str) -> str:
    """Normalize Pakistan mobiles to local 03XXXXXXXXX form."""
    if not phone or not isinstance(phone, str):
        raise AppAPIException(
            code='INVALID_PHONE',
            message='Invalid phone number.',
            status_code=400,
        )
    raw = re.sub(r'[\s\-()]', '', phone.strip())
    if raw.startswith('00'):
        raw = '+' + raw[2:]
    # +923XXXXXXXXX → 03XXXXXXXXX
    if _E164_PK.match(raw):
        return '0' + raw[3:]  # drop +92, keep 3XXXXXXXXX → 03XXXXXXXXX
    # 03XXXXXXXXX or 3XXXXXXXXX → 03XXXXXXXXX
    if _PK_LOCAL.match(raw):
        digits = raw[1:] if raw.startswith('0') else raw
        return f'0{digits}'
    raise AppAPIException(
        code='INVALID_PHONE',
        message='Invalid phone number. Use 03XXXXXXXXX (e.g. 03177370119).',
        status_code=400,
    )


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in kilometers between two WGS84 points."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
