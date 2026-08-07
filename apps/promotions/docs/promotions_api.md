# Promotions API

## Owner (`restaurant` mode)

| Method | Path |
|---|---|
| GET/POST | `/api/restaurant/promotion-requests/` |
| GET | `/api/restaurant/promotion-requests/<id>/` |

### Create body

```json
{
  "event_model": "item",
  "resource_id": 12,
  "requested_start": "2026-08-07T00:00:00+05:00",
  "requested_end": "2026-08-10T00:00:00+05:00"
}
```

## Admin (staff)

| Method | Path |
|---|---|
| GET | `/api/admin-api/promotion-requests/?status=pending` |
| POST | `/api/admin-api/promotion-requests/<id>/approve/` |
| POST | `/api/admin-api/promotion-requests/<id>/reject/` |

Approve sets `is_promoted` + dates on MenuItem/Deal and creates `FeaturedCampaign`.

Reject body: `{ "admin_note": "..." }` → status `changes`.

## Expiry

Celery task `apps.promotions.tasks.expire_promotions` daily at 00:00 Asia/Karachi clears expired `is_promoted` flags and marks live requests `ended`.
