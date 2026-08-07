"""Explore feed: geo filter + 1 promoted + soft organic (2 items + 1 deal)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone as dt_timezone
from typing import Any

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from apps.analytics.models import ResourceAnalytics
from apps.analytics.services.event_service import EventService
from apps.discovery.models import ExploreImpression, ExploreViewerState
from apps.discovery.services.viewer import ViewerIdentity, resolve_viewer
from apps.restaurants.models import Deal, DealStatus, MenuItem, MenuItemStatus
from apps.restaurants.services.deal_service import serialize_deal
from apps.restaurants.services.menu_item_service import serialize_menu_item
from core.exceptions import AppAPIException
from core.utils import haversine_km


@dataclass
class FeedCandidate:
    type: str  # item | deal
    obj: Any
    distance_km: float | None
    score: float = 0.0
    serve_count: int = 0
    last_served_at: datetime | None = None

    @property
    def id(self) -> int:
        return self.obj.pk


@dataclass
class ExploreContext:
    viewer: ViewerIdentity
    state: ExploreViewerState
    use_distance: bool
    applied_radius_km: float | None
    city_id: int | None
    impressions: dict[tuple[str, int], ExploreImpression] = field(default_factory=dict)


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
    lat_raw = params.get('lat')
    lng_raw = params.get('lng')
    distance_raw = params.get('distance_km')
    city_raw = params.get('city_id')

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

    city_id = None
    if city_raw not in (None, ''):
        try:
            city_id = int(city_raw)
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

    return {
        'lat': lat,
        'lng': lng,
        'distance_km': distance_km,
        'city_id': city_id,
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


def _restaurant_ok(restaurant) -> bool:
    return not restaurant.is_paused and not restaurant.is_permanently_closed


class ExploreFeedService:
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
        # 5) Explore ranking / compose on filtered pools
        impressions = self._load_impressions(viewer, item_cands, deal_cands)
        scores = self._load_scores(item_cands, deal_cands)

        for c in item_cands + deal_cands:
            key = (c.type, c.id)
            imp = impressions.get(key)
            c.serve_count = imp.serve_count if imp else 0
            c.last_served_at = imp.last_served_at if imp else None
            c.score = scores.get(key, 0.0)

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

        # Unread promoted stay on top. Rotate only after every promo has been seen,
        # so equal exposure applies in all-seen mode without burying unseen promos.
        all_promoted_seen = bool(promoted) and all(c.serve_count > 0 for c in promoted)
        if all_promoted_seen:
            promoted = _rotate(promoted, state.promoted_rotate_offset)

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
            }
            if use_distance and cand.distance_km is not None:
                row['distance_km'] = round(cand.distance_km, 1)
            else:
                row['distance_km'] = None
            results.append(row)

        if page == 1:
            # Advance promo rotate only when it was applied (all promoted already seen).
            if served_promoted and all_promoted_seen:
                state.promoted_rotate_offset += 1
            # Organic offsets kept for diagnostics / future use; order uses impressions.
            state.organic_item_rotate_offset += served_items
            state.organic_deal_rotate_offset += served_deals
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

        return {
            'results': results,
            'page': page,
            'page_size': page_size,
            'has_more': has_more,
            'next_page': page + 1 if has_more else None,
            'applied_radius_km': max_radius if use_distance else None,
            'city_id': geo['city_id'],
            'min_price': content['min_price'],
            'max_price': content['max_price'],
            'category_ids': content['category_ids'] or None,
        }

    def _get_or_create_state(self, viewer: ViewerIdentity) -> ExploreViewerState:
        if viewer.user_id:
            state, _ = ExploreViewerState.objects.get_or_create(
                user_id=viewer.user_id,
                defaults={'ip_hash': None},
            )
            return state
        state, _ = ExploreViewerState.objects.get_or_create(
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
            qs = ExploreImpression.objects.filter(user_id=viewer.user_id)
        else:
            qs = ExploreImpression.objects.filter(ip_hash=viewer.ip_hash)
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
        """
        Unread promoted first (no analytics). Seen promoted by global
        engagement_score, then distance/id. Caller may rotate when all seen.
        """
        if not cands:
            return []

        def key(c: FeedCandidate):
            if c.serve_count == 0:
                if use_distance:
                    dist = c.distance_km if c.distance_km is not None else 1e18
                    return (0, dist, c.id)
                return (0, c.id)
            if use_distance:
                dist = c.distance_km if c.distance_km is not None else 1e18
                return (1, -c.score, dist, c.id)
            return (1, -c.score, c.id)

        return sorted(cands, key=key)

    def _sort_organic(self, cands: list[FeedCandidate], *, use_distance: bool):
        """
        Unread always before seen; unread band has no analytics.
        Seen band uses global engagement_score.
        When every candidate has been served, order by score then serve_count.
        """
        if not cands:
            return []
        all_seen = all(c.serve_count > 0 for c in cands)
        epoch = datetime.min.replace(tzinfo=dt_timezone.utc)

        def key(c: FeedCandidate):
            if all_seen:
                return (
                    -c.score,
                    -c.serve_count,
                    c.id,
                )
            if c.serve_count == 0:
                dist = (
                    c.distance_km
                    if (use_distance and c.distance_km is not None)
                    else 0.0
                )
                return (0, dist if use_distance else 0.0, c.id)
            last = c.last_served_at or epoch
            return (1, -c.score, last, c.id)

        return sorted(cands, key=key)

    def _take_organic(
        self,
        n: int,
        item_q: list[FeedCandidate],
        deal_q: list[FeedCandidate],
        item_i: list[int],
        deal_i: list[int],
        prefer_items: int = 2,
        prefer_deals: int = 1,
    ) -> list[FeedCandidate]:
        picked: list[FeedCandidate] = []

        def take_item():
            while item_i[0] < len(item_q):
                c = item_q[item_i[0]]
                item_i[0] += 1
                return c
            return None

        def take_deal():
            while deal_i[0] < len(deal_q):
                c = deal_q[deal_i[0]]
                deal_i[0] += 1
                return c
            return None

        items_needed = min(prefer_items, n)
        deals_needed = min(prefer_deals, n - items_needed)

        for _ in range(items_needed):
            c = take_item()
            if c:
                picked.append(c)
        for _ in range(deals_needed):
            c = take_deal()
            if c:
                picked.append(c)

        while len(picked) < n:
            c = take_item() or take_deal()
            if not c:
                break
            picked.append(c)

        # Preserve queue order (already unread-first / impression-ranked).
        # Do not re-sort in a way that mixes seen ahead of unread.
        return picked

    def _compose_all(
        self,
        *,
        promoted: list[FeedCandidate],
        organic_items: list[FeedCandidate],
        organic_deals: list[FeedCandidate],
    ) -> list[dict]:
        results: list[dict] = []
        p_i = 0
        item_i = [0]
        deal_i = [0]

        while True:
            if p_i < len(promoted):
                results.append({'slot': 'promoted', 'candidate': promoted[p_i]})
                p_i += 1
                organics = self._take_organic(
                    3,
                    organic_items,
                    organic_deals,
                    item_i,
                    deal_i,
                    prefer_items=2,
                    prefer_deals=1,
                )
                for c in organics:
                    results.append({'slot': 'organic', 'candidate': c})
                if not organics and p_i >= len(promoted):
                    # only promoted left already appended; continue for more promoted
                    if p_i >= len(promoted):
                        break
                continue

            # organic-only blocks of 4
            organics = self._take_organic(
                4,
                organic_items,
                organic_deals,
                item_i,
                deal_i,
                prefer_items=2,
                prefer_deals=1,
            )
            if not organics:
                break
            for c in organics:
                results.append({'slot': 'organic', 'candidate': c})

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

        imp, _ = ExploreImpression.objects.get_or_create(**lookup, defaults=defaults)
        imp.serve_count = imp.serve_count + 1
        imp.save(update_fields=['serve_count', 'last_served_at'])
