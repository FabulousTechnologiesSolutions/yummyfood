"""Feed seen/batch — watch outcomes and detail_views for watched_ms >= 3000."""

from __future__ import annotations

from django.db import transaction

from apps.analytics.services.event_service import EventService
from apps.feed.models import FeedImpression, FeedWatchOutcome
from apps.feed.services.feed_service import WATCH_MS
from apps.feed.services.viewer import ViewerIdentity
from apps.restaurants.models import Deal, DealStatus, MenuItem, MenuItemStatus
from core.exceptions import AppAPIException

MAX_SEEN_BATCH_ITEMS = 10

OUTCOME_RANK = {
    '': 0,
    FeedWatchOutcome.SKIP: 1,
    FeedWatchOutcome.WATCH: 2,
    FeedWatchOutcome.COMPLETE: 3,
}


def classify_outcome(*, watched_ms: int, duration_ms: int | None) -> str:
    percent = 0.0
    if duration_ms and duration_ms > 0:
        percent = (watched_ms / duration_ms) * 100.0
    if percent >= 95:
        return FeedWatchOutcome.COMPLETE
    if percent >= 50 or watched_ms >= WATCH_MS:
        return FeedWatchOutcome.WATCH
    return FeedWatchOutcome.SKIP


def _public_item(resource_id: int) -> MenuItem:
    try:
        item = MenuItem.objects.select_related('restaurant').get(pk=resource_id)
    except MenuItem.DoesNotExist:
        raise AppAPIException(
            code='MENU_ITEM_NOT_FOUND',
            message='Menu item not found.',
            status_code=404,
        )
    r = item.restaurant
    if (
        item.status != MenuItemStatus.PUBLISHED
        or not item.is_available
        or r.is_paused
        or r.is_permanently_closed
    ):
        raise AppAPIException(
            code='MENU_ITEM_NOT_FOUND',
            message='Menu item not found.',
            status_code=404,
        )
    return item


def _public_deal(resource_id: int) -> Deal:
    try:
        deal = Deal.objects.select_related('restaurant').get(pk=resource_id)
    except Deal.DoesNotExist:
        raise AppAPIException(
            code='DEAL_NOT_FOUND',
            message='Deal not found.',
            status_code=404,
        )
    r = deal.restaurant
    if deal.status != DealStatus.ACTIVE or r.is_paused or r.is_permanently_closed:
        raise AppAPIException(
            code='DEAL_NOT_FOUND',
            message='Deal not found.',
            status_code=404,
        )
    return deal


def _get_or_create_impression(viewer: ViewerIdentity, *, event_model: str, resource_id: int):
    lookup: dict = {}
    if viewer.user_id:
        lookup['user_id'] = viewer.user_id
        lookup['ip_hash'] = None
    else:
        lookup['user'] = None
        lookup['ip_hash'] = viewer.ip_hash
    if event_model == 'item':
        lookup['menu_item_id'] = resource_id
        lookup['deal'] = None
    else:
        lookup['deal_id'] = resource_id
        lookup['menu_item'] = None
    imp, created = FeedImpression.objects.get_or_create(
        **lookup,
        defaults={'serve_count': 0},
    )
    return imp, created


@transaction.atomic
def record_seen(
    *,
    viewer: ViewerIdentity,
    event_model: str,
    resource_id: int,
    watched_ms: int,
    duration_ms: int | None,
    user=None,
) -> dict:
    if event_model == 'item':
        _public_item(resource_id)
    elif event_model == 'deal':
        _public_deal(resource_id)
    else:
        raise AppAPIException(
            code='INVALID_EVENT_MODEL',
            message='event_model must be item or deal.',
            status_code=400,
        )

    outcome = classify_outcome(watched_ms=watched_ms, duration_ms=duration_ms)
    imp, created = _get_or_create_impression(
        viewer, event_model=event_model, resource_id=resource_id
    )

    # Upgrade-only watched_ms / outcome / duration
    updates = []
    if imp.watched_ms is None or watched_ms > imp.watched_ms:
        imp.watched_ms = watched_ms
        updates.append('watched_ms')
    if duration_ms is not None and (imp.duration_ms is None or duration_ms > (imp.duration_ms or 0)):
        imp.duration_ms = duration_ms
        updates.append('duration_ms')
    if OUTCOME_RANK.get(outcome, 0) > OUTCOME_RANK.get(imp.outcome or '', 0):
        imp.outcome = outcome
        updates.append('outcome')
    if updates:
        imp.save(update_fields=updates + ['last_served_at'])

    view_counted = False
    if watched_ms >= WATCH_MS:
        EventService().record(
            event_model=event_model,
            resource_id=resource_id,
            event_type='detail_view',
            user=user,
        )
        view_counted = True

    return {
        'event_model': event_model,
        'resource_id': resource_id,
        'recorded': True,
        'outcome': imp.outcome or outcome,
        'view_counted': view_counted,
        'created': created,
    }


def record_seen_batch(*, viewer: ViewerIdentity, items: list[dict], user=None) -> dict:
    if not items:
        raise AppAPIException(
            code='INVALID_SEEN_BATCH',
            message='items must contain between 1 and 10 events.',
            status_code=400,
        )
    if len(items) > MAX_SEEN_BATCH_ITEMS:
        raise AppAPIException(
            code='INVALID_SEEN_BATCH',
            message=f'items must contain at most {MAX_SEEN_BATCH_ITEMS} events.',
            status_code=400,
        )

    # Dedupe by (event_model, resource_id) keeping highest watched_ms
    best: dict[tuple[str, int], dict] = {}
    for raw in items:
        key = (raw['event_model'], int(raw['resource_id']))
        prev = best.get(key)
        if prev is None or int(raw['watched_ms']) > int(prev['watched_ms']):
            best[key] = raw

    results = []
    recorded_count = 0
    for raw in best.values():
        try:
            row = record_seen(
                viewer=viewer,
                event_model=raw['event_model'],
                resource_id=int(raw['resource_id']),
                watched_ms=int(raw['watched_ms']),
                duration_ms=(
                    int(raw['duration_ms'])
                    if raw.get('duration_ms') not in (None, '')
                    else None
                ),
                user=user,
            )
            recorded_count += 1
            results.append(row)
        except AppAPIException as exc:
            results.append(
                {
                    'event_model': raw.get('event_model'),
                    'resource_id': raw.get('resource_id'),
                    'recorded': False,
                    'error': str(exc.detail),
                }
            )
        except Exception as exc:  # noqa: BLE001
            results.append(
                {
                    'event_model': raw.get('event_model'),
                    'resource_id': raw.get('resource_id'),
                    'recorded': False,
                    'error': str(exc),
                }
            )

    return {'recorded_count': recorded_count, 'results': results}
