# App: `analytics`

**Package:** `apps.analytics`  
**Depends on:** `restaurants`, `accounts`, related content FKs  
**Purpose:** Event ingest, daily rollups, restaurant console analytics (R-14), PDF/CSV export, contact logging.

---

## Responsibility

- Batch ingest engagement / contact events (guest + auth)
- Hourly/daily rollups into `AnalyticsDaily`
- Overview / funnel / content / audience APIs
- North-star: contact events (WhatsApp, Call, Directions)
- Export reports

---

## File layout

```
apps/analytics/
├── __init__.py
├── admin.py
├── apps.py
├── models.py
├── serializers.py
├── urls.py
├── views.py
├── services.py          # aggregate queries
└── tasks.py             # rollups, export generation
```

---

## Models

### `EngagementEvent`

| Field | Type |
|---|---|
| `event_type` | CharField |
| `user` | FK nullable |
| `session_key` | CharField |
| `restaurant` | FK nullable |
| `video` / `deal` / `menu_item` | FK nullable |
| `source` | `feed` \| `explore` \| `search` \| `promoted` \| `direct` \| `profile` \| `promo_sheet` |
| `watch_seconds` | Float nullable |
| `metadata` | JSON |
| `client_event_id` | CharField nullable | idempotency |
| `lat` / `lng` | nullable |
| `created_at` | indexed |

### Event types

```text
video_view, video_complete, video_skip, like, share,
promo_click, restaurant_view, menu_view, deal_view, menu_item_view,
save, unsave, follow, unfollow,
whatsapp_click, call_click, directions_click,
search, not_interested
```

### `AnalyticsDaily`

| Field | Type |
|---|---|
| `restaurant` | FK |
| `date` | Date |
| `video_views` | int |
| `restaurant_views` | int |
| `menu_views` | int |
| `deal_views` | int |
| `whatsapp_clicks` | int |
| `call_clicks` | int |
| `directions_clicks` | int |
| `saves` / `shares` / `follows` | int |
| `unique_visitors` / `new_visitors` / `returning_visitors` | int |
| UniqueTogether | (`restaurant`, `date`) |

---

## API endpoints

| Method | Path | Auth |
|---|---|---|
| POST | `/api/events/` | Optional |
| POST | `/api/contact/` | Optional |
| GET | `/api/console/analytics/overview/?range=` | Owner |
| GET | `/api/console/analytics/funnel/?range=` | Owner |
| GET | `/api/console/analytics/content/?range=` | Owner |
| GET | `/api/console/analytics/export/?format=pdf\|csv&range=` | Owner |

### Ranges

`last_7_days` \| `this_month` \| `last_month` \| `custom` (`start`, `end`)

### Batch events

```json
POST /api/events/
{
  "session_key": "...",
  "events": [
    {
      "event_type": "video_view",
      "video_id": "v1",
      "restaurant_id": "r1",
      "watch_seconds": 12.4,
      "source": "feed",
      "client_event_id": "uuid-1",
      "client_ts": "2026-08-03T17:01:00+05:00"
    }
  ]
}
```

### Contact

```json
POST /api/contact/
{
  "action": "whatsapp_click",
  "restaurant_id": "r_1",
  "deal_id": "deal_1",
  "source": "promo_sheet",
  "session_key": "..."
}
```

Returns `tel_uri`, `whatsapp_uri`, `maps_uri`, `address_text` and logs event.

---

## Overview metrics (R-14)

**Headline:** `customers_reached = whatsapp + calls + directions`

Also return:

- MoM / vs previous period deltas
- Daily restaurant views series
- Contact mix % (prototype ~55 / 30 / 15)
- Tile metrics: video views, contacts, restaurant/menu/deal views, saves, shares, follows
- `last_refreshed_at` (“Figures update hourly”)

### Funnel

```text
Video views → Restaurant views → Menu views → Deal views → Contacts
```

Sources share example: Feed 62%, Explore 21%, Search 9%, Promoted 6%, Direct 2%.

### Content

- Top videos by views
- Top promotions (views / saves / calls / directions)
- Most-viewed menu items
- Ratings histogram (from restaurant fields)
- Audience: new/returning %, median distance, saved_you count

---

## Dashboard “This month” (R-06)

Subset of overview: video views, WhatsApp, calls, directions + MoM deltas.

---

## Business rules

1. Min 3s watch before `video_view` counts as ranking signal (client should filter; server may re-validate).
2. Idempotent ingest via `client_event_id` + session/user.
3. Rollups hourly via Celery.
4. Empty analytics → friendly empty state (no fake zeros required if no rows).
5. Export uses same aggregates as overview.

---

## Tests checklist

- [ ] Batch ingest + idempotency
- [ ] Contact logs whatsapp_click and returns wa.me URL
- [ ] Overview customers_reached formula
- [ ] Funnel stage counts
- [ ] Owner cannot read another restaurant’s analytics
- [ ] Export CSV returns file
