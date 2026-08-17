"""Video Feed: Explore-style compose isolated for Feed (ready-video gate + unwatched ranking)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone as dt_timezone
from typing import Any

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from apps.analytics.models import ResourceAnalytics
from apps.analytics.services.event_service import EventService
from apps.feed.models import FeedImpression, FeedViewerState
from apps.feed.services.viewer import ViewerIdentity, resolve_viewer
from apps.mediahub.models import MediaProcessingStatus, MediaType
from apps.restaurants.models import Deal, DealStatus, MenuItem, MenuItemStatus
from apps.restaurants.services.deal_service import serialize_deal
from apps.restaurants.services.menu_item_service import serialize_menu_item
from apps.restaurants.services.restaurant_service import serialize_restaurant_public
from core.exceptions import AppAPIException
from core.utils import haversine_km


WATCH_MS = 3000
logger = logging.getLogger('apps.feed')
_EPOCH_TS = datetime.min.replace(tzinfo=dt_timezone.utc).timestamp()


def _slot_mark(slot: str) -> str:
    return 'P' if slot == 'promoted' else 'O'


def _candidate_title(cand: FeedCandidate) -> str:
    obj = cand.obj
    return getattr(obj, 'name', None) or getattr(obj, 'label', None) or ''


def _log_feed_sequence(
    *,
    geo: dict,
    viewer: ViewerIdentity,
    page: int,
    page_size: int,
    composed: list[dict],
    page_slice: list[dict],
    has_more: bool,
    next_page: int | None,
    loc_item_count: int,
    loc_deal_count: int,
    filtered_item_count: int,
    filtered_deal_count: int,
    ready_item_count: int,
    ready_deal_count: int,
    promoted: list,
    organic_items: list,
    organic_deals: list,
    all_promoted_watched: bool,
    all_organic_items_watched: bool,
    all_organic_deals_watched: bool,
    promo_rot: int,
    item_rot: int,
    deal_rot: int,
) -> None:
    marks = [_slot_mark(entry['slot']) for entry in page_slice]
    pattern = ''.join(marks) or '-'
    seen_keys: dict[tuple[str, int], int] = {}
    duplicate_ids: list[int] = []
    for entry in page_slice:
        cand = entry['candidate']
        key = (cand.type, cand.id)
        seen_keys[key] = seen_keys.get(key, 0) + 1
        if seen_keys[key] == 2:
            duplicate_ids.append(cand.id)
    recycle = all_promoted_watched or all_organic_items_watched or all_organic_deals_watched
    logger.info(
        'feed_sequence city=%s city_id=%s mode=%s count=%s pattern=%s '
        'page=%s limit=%s returned=%s has_more=%s next_page=%s '
        'loc_items=%s loc_deals=%s filtered_items=%s filtered_deals=%s '
        'ready_items=%s ready_deals=%s '
        'promo=%s org_items=%s org_deals=%s '
        'all_promo_watched=%s all_org_items_watched=%s all_org_deals_watched=%s '
        'promo_rot=%s item_rot=%s deal_rot=%s viewer=%s DUPLICATE_IDS=%s',
        geo.get('city'),
        geo.get('city_id'),
        'recycle' if recycle else 'fresh',
        len(composed),
        pattern,
        page,
        page_size,
        len(page_slice),
        has_more,
        next_page,
        loc_item_count,
        loc_deal_count,
        filtered_item_count,
        filtered_deal_count,
        ready_item_count,
        ready_deal_count,
        len(promoted),
        len(organic_items),
        len(organic_deals),
        all_promoted_watched,
        all_organic_items_watched,
        all_organic_deals_watched,
        promo_rot,
        item_rot,
        deal_rot,
        viewer.user_id or viewer.ip_hash,
        duplicate_ids,
    )
    for idx, entry in enumerate(page_slice):
        cand = entry['candidate']
        logger.info(
            '%02d %s  %s  %s',
            idx,
            _slot_mark(entry['slot']),
            cand.id,
            _candidate_title(cand),
        )


def _recency_ts(obj, *, promoted: bool = False) -> float:
    ts = None
    if promoted:
        ts = getattr(obj, 'promoted_starts_at', None)
    if ts is None:
        ts = getattr(obj, 'published_at', None)
    if ts is None:
        ts = getattr(obj, 'created_at', None)
    if ts is None:
        return _EPOCH_TS
    if timezone.is_naive(ts):
        ts = timezone.make_aware(ts, dt_timezone.utc)
    return ts.timestamp()


@dataclass
class FeedCandidate:
    type: str  # item | deal
    obj: Any
    distance_km: float | None
    score: float = 0.0
    serve_count: int = 0
    watched_ms: int | None = None
    last_served_at: datetime | None = None

    @property
    def id(self) -> int:
        return self.obj.pk

    @property
    def is_watched(self) -> bool:
        return self.watched_ms is not None and self.watched_ms >= WATCH_MS


def _parse_float(value, *, name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        raise AppAPIException(
            code='INVALID_COORDINATES',
            message=f'Invalid {name}.',
            status_code=400,
        )


def parse_geo_params(params) -> dict:
    from apps.geo.services.city_resolve import resolve_city_from_params

    lat_raw = params.get('lat')
    lng_raw = params.get('lng')
    distance_raw = params.get('distance_km')

    has_lat = lat_raw not in (None, '')
    has_lng = lng_raw not in (None, '')
    if has_lat ^ has_lng:
        raise AppAPIException(
            code='INVALID_COORDINATES',
            message='Both lat and lng are required together.',
            status_code=400,
        )

    lat = lng = None
    if has_lat and has_lng:
        lat = _parse_float(lat_raw, name='lat')
        lng = _parse_float(lng_raw, name='lng')
        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            raise AppAPIException(
                code='INVALID_COORDINATES',
                message='lat/lng out of range.',
                status_code=400,
            )

    distance_km = None
    if distance_raw not in (None, ''):
        if lat is None:
            raise AppAPIException(
                code='DISTANCE_REQUIRES_LOCATION',
                message='distance_km requires lat and lng.',
                status_code=400,
            )
        try:
            distance_km = int(float(distance_raw))
        except (TypeError, ValueError):
            raise AppAPIException(
                code='INVALID_DISTANCE_KM',
                message='Invalid distance_km.',
                status_code=400,
            )
        allowed = set(getattr(settings, 'EXPLORE_DISTANCE_FILTER_CHOICES', []))
        if distance_km not in allowed:
            raise AppAPIException(
                code='INVALID_DISTANCE_KM',
                message=f'distance_km must be one of {sorted(allowed)}.',
                status_code=400,
            )

    city = resolve_city_from_params(params)
    return {
        'lat': lat,
        'lng': lng,
        'distance_km': distance_km,
        'city_id': city.id if city is not None else None,
        'city': city.name if city is not None else None,
    }


def _parse_money(value, *, name: str) -> float:
    try:
        amount = float(value)
    except (TypeError, ValueError):
        raise AppAPIException(
            code='INVALID_PRICE',
            message=f'Invalid {name}.',
            status_code=400,
        )
    if amount < 0:
        raise AppAPIException(
            code='INVALID_PRICE',
            message=f'{name} must be >= 0.',
            status_code=400,
        )
    return amount


def _parse_category_ids(params) -> list[int]:
    raw_list = []
    if hasattr(params, 'getlist'):
        raw_list.extend(params.getlist('category_ids'))
        raw_list.extend(params.getlist('categoryIds'))
    for key in ('category_ids', 'categoryIds'):
        raw = params.get(key)
        if raw not in (None, '') and raw not in raw_list:
            raw_list.append(raw)

    ids: list[int] = []
    for raw in raw_list:
        parts = str(raw).split(',')
        for part in parts:
            part = part.strip()
            if not part:
                continue
            try:
                cid = int(part)
            except (TypeError, ValueError):
                raise AppAPIException(
                    code='INVALID_CATEGORY_IDS',
                    message='category_ids must be integers.',
                    status_code=400,
                )
            if cid < 1:
                raise AppAPIException(
                    code='INVALID_CATEGORY_IDS',
                    message='category_ids must be positive integers.',
                    status_code=400,
                )
            if cid not in ids:
                ids.append(cid)
    return ids


def parse_content_filters(params) -> dict:
    """Parse min_price / max_price / category_ids (snake_case; camelCase aliases accepted)."""
    min_raw = params.get('min_price', params.get('minPrice'))
    max_raw = params.get('max_price', params.get('maxPrice'))

    min_price = None
    max_price = None
    if min_raw not in (None, ''):
        min_price = _parse_money(min_raw, name='min_price')
    if max_raw not in (None, ''):
        max_price = _parse_money(max_raw, name='max_price')
    if min_price is not None and max_price is not None and min_price > max_price:
        raise AppAPIException(
            code='INVALID_PRICE_RANGE',
            message='min_price cannot be greater than max_price.',
            status_code=400,
        )

    return {
        'min_price': min_price,
        'max_price': max_price,
        'category_ids': _parse_category_ids(params),
    }


def _candidate_price(cand: FeedCandidate) -> float:
    if cand.type == 'item':
        return float(cand.obj.base_price)
    return float(cand.obj.deal_price)


def _candidate_category_ids(cand: FeedCandidate) -> set[int]:
    if cand.type == 'item':
        return set(cand.obj.categories.values_list('id', flat=True))
    ids: set[int] = set()
    for line in cand.obj.lines.all():
        if line.menu_item_id:
            ids.update(line.menu_item.categories.values_list('id', flat=True))
    return ids


def filter_by_category(
    cands: list[FeedCandidate],
    category_ids: list[int],
) -> list[FeedCandidate]:
    if not category_ids:
        return cands
    wanted = set(category_ids)
    return [c for c in cands if _candidate_category_ids(c) & wanted]


def filter_by_price(
    cands: list[FeedCandidate],
    *,
    min_price: float | None,
    max_price: float | None,
) -> list[FeedCandidate]:
    if min_price is None and max_price is None:
        return cands
    out: list[FeedCandidate] = []
    for c in cands:
        price = _candidate_price(c)
        if min_price is not None and price < min_price:
            continue
        if max_price is not None and price > max_price:
            continue
        out.append(c)
    return out


def _rotate(seq: list, offset: int) -> list:
    if not seq:
        return []
    o = offset % len(seq)
    return seq[o:] + seq[:o]



def _has_ready_feed_video(obj) -> bool:
    for m in obj.media.all():
        if (
            m.media_type == MediaType.VIDEO
            and m.is_feed_video
            and m.processing_status == MediaProcessingStatus.READY
        ):
            return True
    return False


def _restaurant_ok(restaurant) -> bool:
    return not restaurant.is_paused and not restaurant.is_permanently_closed


class FeedService:
    def get_feed(self, request, *, page: int, page_size: int) -> dict:
        if page < 1:
            raise AppAPIException(
                code='INVALID_PAGE',
                message='page must be >= 1.',
                status_code=400,
            )
        if page_size < 1 or page_size > 100:
            raise AppAPIException(
                code='INVALID_PAGE_SIZE',
                message='page_size must be between 1 and 100.',
                status_code=400,
            )

        geo = parse_geo_params(request.query_params)
        content = parse_content_filters(request.query_params)
        viewer = resolve_viewer(request)
        state = self._get_or_create_state(viewer)

        # 1) City filter (queryset)
        items_qs, deals_qs = self._eligible_querysets(city_id=geo['city_id'])
        use_distance = geo['lat'] is not None
        max_radius = None
        if use_distance:
            max_radius = (
                float(geo['distance_km'])
                if geo['distance_km'] is not None
                else float(settings.EXPLORE_DEFAULT_MAX_RADIUS_KM)
            )

        now = timezone.now()
        # 2) Location filter (distance)
        item_cands = self._build_candidates(
            'item',
            items_qs,
            geo=geo,
            max_radius=max_radius,
            now=now,
        )
        deal_cands = self._build_candidates(
            'deal',
            deals_qs,
            geo=geo,
            max_radius=max_radius,
            now=now,
        )
        loc_item_count = len(item_cands)
        loc_deal_count = len(deal_cands)
        # 3) Category filter
        item_cands = filter_by_category(item_cands, content['category_ids'])
        deal_cands = filter_by_category(deal_cands, content['category_ids'])
        # 4) Price filter
        item_cands = filter_by_price(
            item_cands,
            min_price=content['min_price'],
            max_price=content['max_price'],
        )
        deal_cands = filter_by_price(
            deal_cands,
            min_price=content['min_price'],
            max_price=content['max_price'],
        )
        filtered_item_count = len(item_cands)
        filtered_deal_count = len(deal_cands)
        # 5) Explore ranking / compose on filtered pools
        impressions = self._load_impressions(viewer, item_cands, deal_cands)
        scores = self._load_scores(item_cands, deal_cands)

        for c in item_cands + deal_cands:
            key = (c.type, c.id)
            imp = impressions.get(key)
            c.serve_count = imp.serve_count if imp else 0
            c.watched_ms = imp.watched_ms if imp else None
            c.last_served_at = imp.last_served_at if imp else None
            c.score = scores.get(key, 0.0)

        item_cands = [c for c in item_cands if _has_ready_feed_video(c.obj)]
        deal_cands = [c for c in deal_cands if _has_ready_feed_video(c.obj)]
        ready_item_count = len(item_cands)
        ready_deal_count = len(deal_cands)

        promoted = [
            c
            for c in item_cands + deal_cands
            if self._is_currently_promoted(c.obj, now)
        ]
        promoted_ids = {(c.type, c.id) for c in promoted}
        organic_items = [c for c in item_cands if (c.type, c.id) not in promoted_ids]
        organic_deals = [c for c in deal_cands if (c.type, c.id) not in promoted_ids]

        promoted = self._sort_promoted(promoted, use_distance=use_distance)
        organic_items = self._sort_organic(organic_items, use_distance=use_distance)
        organic_deals = self._sort_organic(organic_deals, use_distance=use_distance)

        # Unwatched stay on top. Rotate a pool only after every card in it is watched (>=3s).
        all_promoted_watched = bool(promoted) and all(c.is_watched for c in promoted)
        all_organic_items_watched = bool(organic_items) and all(
            c.is_watched for c in organic_items
        )
        all_organic_deals_watched = bool(organic_deals) and all(
            c.is_watched for c in organic_deals
        )
        if all_promoted_watched:
            promoted = _rotate(promoted, state.promoted_rotate_offset)
        if all_organic_items_watched:
            organic_items = _rotate(organic_items, state.organic_item_rotate_offset)
        if all_organic_deals_watched:
            organic_deals = _rotate(organic_deals, state.organic_deal_rotate_offset)

        composed = self._compose_all(
            promoted=promoted,
            organic_items=organic_items,
            organic_deals=organic_deals,
        )

        start = (page - 1) * page_size
        end = start + page_size
        page_slice = composed[start:end]
        has_more = end < len(composed)

        served_promoted = 0
        served_items = 0
        served_deals = 0
        results = []
        user = request.user if getattr(request.user, 'is_authenticated', False) else None
        event_svc = EventService()

        for entry in page_slice:
            cand = entry['candidate']
            self._record_impression(viewer, cand)
            event_svc.record(
                event_model=cand.type,
                resource_id=cand.id,
                event_type='impression',
                user=user,
                allow_impression=True,
            )
            if entry['slot'] == 'promoted':
                served_promoted += 1
            if cand.type == 'item':
                served_items += 1
            else:
                served_deals += 1

            payload = (
                serialize_menu_item(cand.obj)
                if cand.type == 'item'
                else serialize_deal(cand.obj)
            )
            row = {
                'slot': entry['slot'],
                'type': cand.type,
                'data': payload,
                'restaurant': serialize_restaurant_public(cand.obj.restaurant, request=request),
            }
            if use_distance and cand.distance_km is not None:
                row['distance_km'] = round(cand.distance_km, 1)
            else:
                row['distance_km'] = None
            results.append(row)

        promo_rot = state.promoted_rotate_offset
        item_rot = state.organic_item_rotate_offset
        deal_rot = state.organic_deal_rotate_offset
        if page == 1:
            if served_promoted and all_promoted_watched:
                state.promoted_rotate_offset += 1
            if all_organic_items_watched:
                state.organic_item_rotate_offset += 1
            if all_organic_deals_watched:
                state.organic_deal_rotate_offset += 1
            state.last_rotated_at = timezone.now()
            state.save(
                update_fields=[
                    'promoted_rotate_offset',
                    'organic_item_rotate_offset',
                    'organic_deal_rotate_offset',
                    'last_rotated_at',
                    'updated_at',
                ]
            )

        next_page = page + 1 if has_more else None
        _log_feed_sequence(
            geo=geo,
            viewer=viewer,
            page=page,
            page_size=page_size,
            composed=composed,
            page_slice=page_slice,
            has_more=has_more,
            next_page=next_page,
            loc_item_count=loc_item_count,
            loc_deal_count=loc_deal_count,
            filtered_item_count=filtered_item_count,
            filtered_deal_count=filtered_deal_count,
            ready_item_count=ready_item_count,
            ready_deal_count=ready_deal_count,
            promoted=promoted,
            organic_items=organic_items,
            organic_deals=organic_deals,
            all_promoted_watched=all_promoted_watched,
            all_organic_items_watched=all_organic_items_watched,
            all_organic_deals_watched=all_organic_deals_watched,
            promo_rot=promo_rot,
            item_rot=item_rot,
            deal_rot=deal_rot,
        )

        return {
            'results': results,
            'page': page,
            'page_size': page_size,
            'has_more': has_more,
            'next_page': next_page,
            'applied_radius_km': max_radius if use_distance else None,
            'city_id': geo['city_id'],
            'city': geo.get('city'),
            'min_price': content['min_price'],
            'max_price': content['max_price'],
            'category_ids': content['category_ids'] or None,
        }

    def _get_or_create_state(self, viewer: ViewerIdentity) -> FeedViewerState:
        if viewer.user_id:
            state, _ = FeedViewerState.objects.get_or_create(
                user_id=viewer.user_id,
                defaults={'ip_hash': None},
            )
            return state
        state, _ = FeedViewerState.objects.get_or_create(
            ip_hash=viewer.ip_hash,
            defaults={'user': None},
        )
        return state

    def _eligible_querysets(self, *, city_id):
        restaurant_filter = Q(
            restaurant__is_paused=False,
            restaurant__is_permanently_closed=False,
        )
        if city_id is not None:
            restaurant_filter &= Q(restaurant__city_id=city_id)

        items = (
            MenuItem.objects.filter(
                restaurant_filter,
                status=MenuItemStatus.PUBLISHED,
                is_available=True,
            )
            .select_related('restaurant')
            .prefetch_related('sizes', 'categories', 'media')
        )
        deals = (
            Deal.objects.filter(
                restaurant_filter,
                status=DealStatus.ACTIVE,
            )
            .select_related('restaurant')
            .prefetch_related('lines__menu_item__categories', 'media')
        )
        return items, deals

    def _build_candidates(
        self,
        type_name: str,
        qs,
        *,
        geo: dict,
        max_radius: float | None,
        now,
    ) -> list[FeedCandidate]:
        out: list[FeedCandidate] = []
        lat, lng = geo['lat'], geo['lng']
        for obj in qs:
            r = obj.restaurant
            if not _restaurant_ok(r):
                continue
            distance = None
            if lat is not None:
                if r.lat is None or r.lng is None:
                    continue
                distance = haversine_km(
                    lat,
                    lng,
                    float(r.lat),
                    float(r.lng),
                )
                if max_radius is not None and distance > max_radius:
                    continue
            out.append(
                FeedCandidate(
                    type=type_name,
                    obj=obj,
                    distance_km=distance,
                )
            )
        return out

    def _is_currently_promoted(self, obj, now) -> bool:
        if not getattr(obj, 'is_promoted', False):
            return False
        start = getattr(obj, 'promoted_starts_at', None)
        end = getattr(obj, 'promoted_ends_at', None)
        if start is None or end is None:
            return False
        return start <= now <= end

    def _load_impressions(self, viewer, item_cands, deal_cands):
        result = {}
        if viewer.user_id:
            qs = FeedImpression.objects.filter(user_id=viewer.user_id)
        else:
            qs = FeedImpression.objects.filter(ip_hash=viewer.ip_hash)
        item_ids = [c.id for c in item_cands]
        deal_ids = [c.id for c in deal_cands]
        if item_ids:
            for imp in qs.filter(menu_item_id__in=item_ids):
                result[('item', imp.menu_item_id)] = imp
        if deal_ids:
            for imp in qs.filter(deal_id__in=deal_ids):
                result[('deal', imp.deal_id)] = imp
        return result

    def _load_scores(self, item_cands, deal_cands):
        result = {}
        item_ids = [c.id for c in item_cands]
        deal_ids = [c.id for c in deal_cands]
        if item_ids:
            for row in ResourceAnalytics.objects.filter(
                user__isnull=True,
                menu_item_id__in=item_ids,
            ):
                result[('item', row.menu_item_id)] = row.engagement_score
        if deal_ids:
            for row in ResourceAnalytics.objects.filter(
                user__isnull=True,
                deal_id__in=deal_ids,
            ):
                result[('deal', row.deal_id)] = row.engagement_score
        return result

    def _sort_promoted(self, cands: list[FeedCandidate], *, use_distance: bool):
        """Unwatched promoted first (newest); watched by engagement_score."""
        if not cands:
            return []

        def key(c: FeedCandidate):
            recency = -_recency_ts(c.obj, promoted=True)
            if not c.is_watched:
                if use_distance:
                    dist = c.distance_km if c.distance_km is not None else 1e18
                    return (0, dist, recency, c.id)
                return (0, recency, c.id)
            if use_distance:
                dist = c.distance_km if c.distance_km is not None else 1e18
                return (1, -c.score, dist, recency, c.id)
            return (1, -c.score, recency, c.id)

        return sorted(cands, key=key)

    def _sort_organic(self, cands: list[FeedCandidate], *, use_distance: bool):
        """Unwatched newest-first; watched ≥3s sink; all-watched uses analytics."""
        if not cands:
            return []
        all_watched = all(c.is_watched for c in cands)

        def key(c: FeedCandidate):
            recency = -_recency_ts(c.obj)
            if all_watched:
                return (-c.score, recency, c.id)
            if not c.is_watched:
                if use_distance:
                    dist = c.distance_km if c.distance_km is not None else 1e18
                    return (0, dist, recency, c.id)
                return (0, recency, c.id)
            return (1, -c.score, recency, c.id)

        return sorted(cands, key=key)

    def _take_next_organic(
        self,
        *,
        prefer: str,
        item_q: list[FeedCandidate],
        deal_q: list[FeedCandidate],
        item_i: list[int],
        deal_i: list[int],
    ) -> FeedCandidate | None:
        """Prefer item or deal; cross-fill with the other when preferred pool is empty."""

        def take_item():
            if item_i[0] < len(item_q):
                c = item_q[item_i[0]]
                item_i[0] += 1
                return c
            return None

        def take_deal():
            if deal_i[0] < len(deal_q):
                c = deal_q[deal_i[0]]
                deal_i[0] += 1
                return c
            return None

        if prefer == 'item':
            return take_item() or take_deal()
        return take_deal() or take_item()

    def _compose_all(
        self,
        *,
        promoted: list[FeedCandidate],
        organic_items: list[FeedCandidate],
        organic_deals: list[FeedCandidate],
    ) -> list[dict]:
        """
        Repeating P-O-D-O while organic stock remains.
        Promoted cycles via modulo; organics are consumed once; cross-fill if one type empties.
        No infinite P loop after organics are gone. No promos → O-D-O-O style blocks.
        """
        results: list[dict] = []
        p_i = 0
        item_i = [0]
        deal_i = [0]

        def has_organic() -> bool:
            return item_i[0] < len(organic_items) or deal_i[0] < len(organic_deals)

        def append_organic(prefer: str) -> bool:
            c = self._take_next_organic(
                prefer=prefer,
                item_q=organic_items,
                deal_q=organic_deals,
                item_i=item_i,
                deal_i=deal_i,
            )
            if c is None:
                return False
            results.append({'slot': 'organic', 'candidate': c})
            return True

        if not promoted:
            # Organic-only: O, D, O, O (prefer) with cross-fill
            while has_organic():
                before = len(results)
                for prefer in ('item', 'deal', 'item', 'item'):
                    if not has_organic():
                        break
                    append_organic(prefer)
                if len(results) == before:
                    break
            return results

        # With promos: P, O, D, O … cycle P until organics exhausted
        while has_organic():
            results.append(
                {
                    'slot': 'promoted',
                    'candidate': promoted[p_i % len(promoted)],
                }
            )
            p_i += 1
            for prefer in ('item', 'deal', 'item'):
                if not has_organic():
                    break
                append_organic(prefer)

        # Promo-only pool (no organics): emit each unique promo once
        if not results and promoted:
            for c in promoted:
                results.append({'slot': 'promoted', 'candidate': c})

        return results

    def _record_impression(self, viewer: ViewerIdentity, cand: FeedCandidate):
        defaults = {'serve_count': 0}
        if viewer.user_id:
            lookup = {
                'user_id': viewer.user_id,
                'ip_hash': None,
            }
        else:
            lookup = {
                'user': None,
                'ip_hash': viewer.ip_hash,
            }
        if cand.type == 'item':
            lookup['menu_item_id'] = cand.id
            lookup['deal'] = None
        else:
            lookup['deal_id'] = cand.id
            lookup['menu_item'] = None

        imp, _ = FeedImpression.objects.get_or_create(**lookup, defaults=defaults)
        imp.serve_count = imp.serve_count + 1
        imp.save(update_fields=['serve_count', 'last_served_at'])
