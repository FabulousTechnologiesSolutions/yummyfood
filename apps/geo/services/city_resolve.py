"""Resolve city query params for Explore / Feed."""

from apps.geo.models import City
from core.exceptions import AppAPIException


def resolve_city_from_params(params) -> City | None:
    """
    Accept `city_id` and/or `city` (name, case-insensitive).

    - Neither present → None
    - Both present → city_id wins (name ignored for resolution)
    - Invalid / inactive / missing → CITY_NOT_FOUND 404
    """
    city_id_raw = params.get('city_id')
    city_name_raw = params.get('city')

    has_id = city_id_raw not in (None, '')
    has_name = city_name_raw not in (None, '')

    if not has_id and not has_name:
        return None

    if has_id:
        try:
            city_id = int(city_id_raw)
        except (TypeError, ValueError):
            raise AppAPIException(
                code='CITY_NOT_FOUND',
                message='Invalid city_id.',
                status_code=404,
            )
        if city_id < 1:
            raise AppAPIException(
                code='CITY_NOT_FOUND',
                message='Invalid city_id.',
                status_code=404,
            )
        city = City.objects.filter(id=city_id, is_active=True).first()
        if city is None:
            raise AppAPIException(
                code='CITY_NOT_FOUND',
                message='City not found.',
                status_code=404,
            )
        return city

    name = str(city_name_raw).strip()
    if not name:
        raise AppAPIException(
            code='CITY_NOT_FOUND',
            message='Invalid city name.',
            status_code=404,
        )
    city = City.objects.filter(name__iexact=name, is_active=True).first()
    if city is None:
        raise AppAPIException(
            code='CITY_NOT_FOUND',
            message='City not found.',
            status_code=404,
        )
    return city
