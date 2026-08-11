# Feed / Video API

TikTok-style feed for items and deals that have a **ready** feed video. State is **Feed-only** (`FeedViewerState`, `FeedImpression`); Explore tables are never written.

Shared analytics: both Explore and Feed use [`ResourceAnalytics`](../../analytics/models.py).

| Surface | When | Counter |
|---|---|---|
| Feed GET serve | each card on the page | `impression_count` (+ `FeedImpression.serve_count`) |
| Feed Seen `watched_ms >= 3000` | each qualifying Seen event | `detail_views` |

---

## Auth / identity

Both endpoints are **`AllowAny`**.

| Client | Viewer key |
|---|---|
| JWT present | `user_id` |
| Guest | `ip_hash` (SHA-256 of client IP + server salt; `X-Forwarded-For` first hop or `REMOTE_ADDR`) |

---

## `GET /api/feed/products/`

Public continuous feed. **No request body** — inputs are query params only.

### Behavior summary

- Eligibility: entity must have a video with `processing_status=ready` and `is_feed_video=true`
- Compose: repeating **`P → O → D → O`** (promo cycles via modulo; organic cross-fill; stop when organics empty)
- Ranking: **unwatched** (`FeedImpression.watched_ms` null or `< 3000`) on top; GET serve does **not** sink cards
- Watched band (`watched_ms >= 3000`): anonymous `ResourceAnalytics.engagement_score`
- On serve: upsert `FeedImpression.serve_count` + analytics `impression` (does **not** set `watched_ms`)

### Query params

| Param | Type | Required | Default | Notes |
|---|---|---|---|---|
| `lat` | float | no | — | Must be sent **with** `lng`. Range −90…90 |
| `lng` | float | no | — | Must be sent **with** `lat`. Range −180…180 |
| `distance_km` | int | no | — | Hard radius when lat/lng set. Allowed: **`1` \| `3` \| `5` \| `10` \| `25` \| `50`**. Requires lat/lng |
| `city_id` | int | no | — | Filter by active city PK |
| `city` | string | no | — | Filter by active city name (case-insensitive). If both sent, `city_id` wins |
| `category_ids` | int[] | no | all | Repeat or comma-separated: `category_ids=1&category_ids=3` or `category_ids=1,3,5` |
| `min_price` | number | no | — | Inclusive. Item → `base_price`; Deal → `deal_price` |
| `max_price` | number | no | — | Inclusive |
| `page` | int | no | `1` | Must be ≥ 1 |
| `page_size` | int | no | `20` | Must be 1…100 |

**CamelCase aliases** (accepted): `categoryIds`, `minPrice`, `maxPrice`.

### Example requests

```http
GET /api/feed/products/
GET /api/feed/products/?page=1&page_size=20
GET /api/feed/products/?lat=31.52&lng=74.35
GET /api/feed/products/?lat=31.52&lng=74.35&distance_km=5
GET /api/feed/products/?city_id=10
GET /api/feed/products/?lat=31.52&lng=74.35&city_id=10&distance_km=10
GET /api/feed/products/?category_ids=1,3,5&min_price=500&max_price=1000
GET /api/feed/products/?minPrice=500&maxPrice=1000&categoryIds=12
```

### Geo modes

| Mode | Params | Behavior |
|---|---|---|
| Hard radius | `lat` + `lng` + `distance_km` | Only restaurants within that km. `applied_radius_km` = filter |
| Default max | `lat` + `lng` only | Cap **50 km**. `applied_radius_km` = `50` |
| City only | `city_id` (no lat/lng) | City filter; row `distance_km` is `null` |
| City + coords | `city_id` + `lat`/`lng` [(+ `distance_km`)] | City first, then radius |
| Global | none of the above | Full eligible pool; no distances |

### Filter order (before ranking)

1. City (`city_id`)
2. Location (`lat` / `lng` / `distance_km`)
3. Ready feed-video gate
4. Category (`category_ids`)
5. Price (`min_price` / `max_price`)
6. Compose (`P → O → D → O`)

---

### Response envelope (`200`)

```json
{
  "results": [],
  "page": 1,
  "page_size": 20,
  "has_more": true,
  "next_page": 2,
  "applied_radius_km": 50.0,
  "city_id": 10,
  "city": "Lahore",
  "min_price": 500.0,
  "max_price": 1000.0,
  "category_ids": [1, 3, 5]
}
```

| Field | Type | Notes |
|---|---|---|
| `results` | array | Ordered feed cards for this page |
| `page` | int | Current page |
| `page_size` | int | Page size used |
| `has_more` | bool | More results after this page |
| `next_page` | int \| null | `page + 1` if `has_more`, else `null` |
| `applied_radius_km` | number \| null | Hard `distance_km`, or `50` when lat/lng-only; `null` if no coords |
| `city_id` | int \| null | Echo of filter |
| `min_price` | number \| null | Echo of filter |
| `max_price` | number \| null | Echo of filter |
| `category_ids` | int[] \| null | Echo; `null` if none passed |

### Result row shape

Every `results[]` element:

```json
{
  "slot": "promoted",
  "type": "item",
  "distance_km": 2.3,
  "data": {},
  "restaurant": {}
}
```

| Field | Values |
|---|---|
| `slot` | `promoted` \| `organic` |
| `type` | `item` \| `deal` |
| `distance_km` | number (1 decimal) when lat/lng used, else `null` |
| `data` | Full menu-item **or** deal object (includes `media[]`) |
| `restaurant` | Public restaurant object (`serialize_restaurant_public`) |

---

### Type A — promoted / organic **item** row

```json
{
  "slot": "promoted",
  "type": "item",
  "distance_km": 2.3,
  "data": {
    "id": 9,
    "restaurant_id": 1,
    "category_ids": [12, 7],
    "categories": [
      {
        "id": 12,
        "slug": "burgers",
        "name": "Burgers",
        "icon": "",
        "position": 6,
        "is_visible": true
      }
    ],
    "name": "Chicken Burger",
    "description": "Juicy grilled chicken",
    "subcategory": "",
    "item_type": "Chicken",
    "quantity_label": "1 pc",
    "sku": "FA-001",
    "is_available": true,
    "is_popular": false,
    "is_new": false,
    "is_promoted": true,
    "promoted_starts_at": "2026-08-07T00:00:00+00:00",
    "promoted_ends_at": "2026-08-10T23:59:59+00:00",
    "spicy_level": 1,
    "prep_time_min": 15,
    "calories": null,
    "emoji": "",
    "base_price": "999.00",
    "status": "published",
    "published_at": "2026-08-05T08:00:00+00:00",
    "sizes": [
      {
        "id": 3,
        "label": "Regular",
        "price": "1250.00",
        "offer_price": "999.00",
        "position": 0
      }
    ],
    "media": [
      {
        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "type": "image",
        "url": "/media/restaurants/1/items/9/media/.../cover.jpg",
        "is_cover": true,
        "order_index": 0,
        "processing_status": "",
        "duration": null,
        "thumbnail_url": "",
        "hls_master_url": "",
        "resolutions": []
      },
      {
        "id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        "type": "video",
        "url": "/media/restaurants/1/items/9/media/.../clip.mp4",
        "is_cover": false,
        "order_index": 1,
        "processing_status": "ready",
        "duration": 24.5,
        "thumbnail_url": "/media/restaurants/1/items/9/video/.../thumbnail.jpg",
        "hls_master_url": "/media/restaurants/1/items/9/video/.../hls/master.m3u8",
        "resolutions": [
          {
            "quality": "720p",
            "height": 720,
            "width": 1280,
            "bandwidth": 2928000,
            "hlsKey": "restaurants/1/items/9/video/.../hls/720p/index.m3u8",
            "hlsUrl": "/media/restaurants/1/items/9/video/.../hls/720p/index.m3u8"
          }
        ]
      }
    ],
    "created_at": "2026-08-05T08:00:00+00:00",
    "updated_at": "2026-08-05T08:00:00+00:00"
  },
  "restaurant": {
    "id": 1,
    "name": "Fab Burgers",
    "slug": "fab-burgers",
    "short_description": "Best burgers in town",
    "cuisines": ["Fast Food", "Burgers"],
    "price_range": 2,
    "logo": "/media/restaurants/1/logo.png",
    "cover": "/media/restaurants/1/cover.jpg",
    "primary_phone": "+923001234567",
    "whatsapp_number": "+923001234567",
    "street_address": "12 Main Blvd",
    "area": "Gulberg",
    "city_id": 10,
    "lat": "31.520400",
    "lng": "74.358700",
    "rating_avg": "4.50",
    "rating_count": 120,
    "is_paused": false
  }
}
```

`restaurant.id` always matches `data.restaurant_id`.

---

### Type B — organic **deal** row

```json
{
  "slot": "organic",
  "type": "deal",
  "distance_km": 1.1,
  "data": {
    "id": 4,
    "restaurant_id": 1,
    "label": "Lunch Deal",
    "description": "Burger + drink",
    "deal_price": "400.00",
    "items_total": "500.00",
    "savings_amount": "100.00",
    "savings_percent": "20.00",
    "starts_at": "2026-08-05T00:00:00+00:00",
    "ends_at": "2026-08-12T23:59:59+00:00",
    "days_of_week": [0, 1, 2, 3, 4],
    "terms": "Dine-in only",
    "status": "active",
    "is_promoted": false,
    "promoted_starts_at": null,
    "promoted_ends_at": null,
    "lines": [
      {
        "id": 1,
        "menu_item_id": 9,
        "menu_item_name": "Chicken Burger",
        "size_label": "Regular",
        "unit_price": "450.00",
        "quantity": 1,
        "position": 0
      }
    ],
    "media": [
      {
        "id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
        "type": "video",
        "url": "/media/restaurants/1/deals/4/media/.../clip.mp4",
        "is_cover": false,
        "order_index": 0,
        "processing_status": "ready",
        "duration": 18.0,
        "thumbnail_url": "/media/restaurants/1/deals/4/video/.../thumbnail.jpg",
        "hls_master_url": "/media/restaurants/1/deals/4/video/.../hls/master.m3u8",
        "resolutions": [
          {
            "quality": "720p",
            "height": 720,
            "width": 1280,
            "bandwidth": 2500000,
            "hlsKey": "restaurants/1/deals/4/video/.../hls/720p/index.m3u8",
            "hlsUrl": "/media/restaurants/1/deals/4/video/.../hls/720p/index.m3u8"
          }
        ]
      }
    ],
    "created_at": "2026-08-05T08:00:00+00:00",
    "updated_at": "2026-08-05T08:00:00+00:00"
  },
  "restaurant": {
    "id": 1,
    "name": "Fab Burgers",
    "slug": "fab-burgers",
    "short_description": "Best burgers in town",
    "cuisines": ["Fast Food"],
    "price_range": 2,
    "logo": "/media/restaurants/1/logo.png",
    "cover": "/media/restaurants/1/cover.jpg",
    "primary_phone": "+923001234567",
    "whatsapp_number": "+923001234567",
    "street_address": "12 Main Blvd",
    "area": "Gulberg",
    "city_id": 10,
    "lat": "31.520400",
    "lng": "74.358700",
    "rating_avg": "4.50",
    "rating_count": 120,
    "is_paused": false
  }
}
```

---

### Media object fields (`data.media[]`)

| Field | Type | Notes |
|---|---|---|
| `id` | UUID string | `ContentMedia` PK |
| `type` | string | `image` \| `video` |
| `url` | string | Original / public file URL |
| `is_cover` | bool | Images; at most one cover per entity |
| `order_index` | int | Display order |
| `processing_status` | string | `""` \| `pending` \| `processing` \| `ready` \| `failed` |
| `duration` | float \| null | Seconds (video) |
| `thumbnail_url` | string | Video poster |
| `hls_master_url` | string | HLS master playlist |
| `resolutions` | array | Per-quality HLS entries (`quality`, `height`, `width`, `bandwidth`, `hlsKey`, `hlsUrl`) |

Feed listing only includes entities that already have a **ready** feed video; images/covers still appear alongside that video in `media[]`.

---

### Full list response examples

#### 1) Global (no geo)

**Request:** `GET /api/feed/products/?page=1&page_size=4`

```json
{
  "results": [
    {
      "slot": "promoted",
      "type": "item",
      "distance_km": null,
      "data": { "id": 9, "name": "Chicken Burger", "is_promoted": true, "media": [] },
      "restaurant": { "id": 1, "name": "Fab Burgers" }
    },
    {
      "slot": "organic",
      "type": "item",
      "distance_km": null,
      "data": { "id": 11, "name": "Fries", "media": [] },
      "restaurant": { "id": 1, "name": "Fab Burgers" }
    },
    {
      "slot": "organic",
      "type": "deal",
      "distance_km": null,
      "data": { "id": 4, "label": "Lunch Deal", "media": [] },
      "restaurant": { "id": 1, "name": "Fab Burgers" }
    },
    {
      "slot": "organic",
      "type": "item",
      "distance_km": null,
      "data": { "id": 12, "name": "Shake", "media": [] },
      "restaurant": { "id": 1, "name": "Fab Burgers" }
    }
  ],
  "page": 1,
  "page_size": 4,
  "has_more": true,
  "next_page": 2,
  "applied_radius_km": null,
  "city_id": null,
  "min_price": null,
  "max_price": null,
  "category_ids": null
}
```

*(Truncated `data` / `restaurant` for brevity; production returns full objects as above.)*

#### 2) Lat/lng only (default 50 km)

**Request:** `GET /api/feed/products/?lat=31.52&lng=74.35&page_size=4`

```json
{
  "results": [
    {
      "slot": "promoted",
      "type": "item",
      "distance_km": 2.3,
      "data": { "id": 9, "is_promoted": true },
      "restaurant": { "id": 1, "name": "Fab Burgers" }
    },
    {
      "slot": "organic",
      "type": "item",
      "distance_km": 1.5,
      "data": { "id": 11 },
      "restaurant": { "id": 1, "name": "Fab Burgers" }
    },
    {
      "slot": "organic",
      "type": "deal",
      "distance_km": 1.1,
      "data": { "id": 4 },
      "restaurant": { "id": 1, "name": "Fab Burgers" }
    },
    {
      "slot": "organic",
      "type": "item",
      "distance_km": 3.2,
      "data": { "id": 12 },
      "restaurant": { "id": 1, "name": "Fab Burgers" }
    }
  ],
  "page": 1,
  "page_size": 4,
  "has_more": false,
  "next_page": null,
  "applied_radius_km": 50.0,
  "city_id": null,
  "min_price": null,
  "max_price": null,
  "category_ids": null
}
```

#### 3) Hard radius + filters

**Request:**  
`GET /api/feed/products/?lat=31.52&lng=74.35&distance_km=5&city_id=10&category_ids=12&min_price=500&max_price=1000`

```json
{
  "results": [
    {
      "slot": "promoted",
      "type": "item",
      "distance_km": 2.3,
      "data": {
        "id": 9,
        "category_ids": [12],
        "base_price": "999.00",
        "is_promoted": true
      },
      "restaurant": { "id": 1, "city_id": 10 }
    }
  ],
  "page": 1,
  "page_size": 20,
  "has_more": false,
  "next_page": null,
  "applied_radius_km": 5.0,
  "city_id": 10,
  "min_price": 500.0,
  "max_price": 1000.0,
  "category_ids": [12]
}
```

#### 4) Empty page / past end

```json
{
  "results": [],
  "page": 4,
  "page_size": 20,
  "has_more": false,
  "next_page": null,
  "applied_radius_km": null,
  "city_id": null,
  "min_price": null,
  "max_price": null,
  "category_ids": null
}
```

---

### List error responses

FoodApp error envelope:

```json
{
  "error": {
    "code": "INVALID_COORDINATES",
    "message": "Both lat and lng are required together.",
    "details": {}
  }
}
```

| Code | Status | When |
|---|---|---|
| `INVALID_COORDINATES` | 400 | Only one of lat/lng; non-numeric; out of range |
| `DISTANCE_REQUIRES_LOCATION` | 400 | `distance_km` without lat/lng |
| `INVALID_DISTANCE_KM` | 400 | Not in `{1,3,5,10,25,50}` |
| `CITY_NOT_FOUND` | 404 | Invalid / non-positive `city_id` |
| `INVALID_PRICE` | 400 | Non-numeric or negative price bound |
| `INVALID_PRICE_RANGE` | 400 | `min_price` > `max_price` |
| `INVALID_CATEGORY_IDS` | 400 | Non-integer / non-positive category id |
| `INVALID_PAGE` | 400 | `page` &lt; 1 or non-integer |
| `INVALID_PAGE_SIZE` | 400 | `page_size` outside 1…100 or non-integer |

---

## `POST /api/feed/seen/batch/`

Batch watch / Seen events. **Only** this endpoint — there is no single `POST /api/feed/seen/`.

- Accepts **1–10** items per request
- Dedupes by `(event_model, resource_id)` keeping the **highest** `watched_ms`
- Partial success: invalid resources return `recorded: false` + `error`; valid ones still record
- Upgrades `FeedImpression.watched_ms` / `duration_ms` / `outcome` only (never downgrade)
- `watched_ms >= 3000` → `EventService` `detail_view` → `ResourceAnalytics.detail_views` (+1 each time, including rewatch)
- Below 3s: no `detail_views`; ranking still treats as **unwatched**

### Outcome classification

| Condition | `outcome` |
|---|---|
| `duration_ms` set and watch percent ≥ 95% | `complete` |
| percent ≥ 50% **or** `watched_ms >= 3000` | `watch` |
| otherwise | `skip` |

Upgrade order: `skip` → `watch` → `complete` (never reverse).

### Request body schema

```json
{
  "items": [
    {
      "event_model": "item",
      "resource_id": 9,
      "watched_ms": 4500,
      "duration_ms": 12000
    }
  ]
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `items` | array | yes | Length **1…10** |
| `items[].event_model` | string | yes | `item` \| `deal` |
| `items[].resource_id` | int | yes | ≥ 1 |
| `items[].watched_ms` | int | yes | ≥ 0 (milliseconds watched) |
| `items[].duration_ms` | int \| null | no | ≥ 1 when sent; used for percent / `complete` |

### Request payload examples

#### Minimal — item skip (&lt; 3s, no duration)

```json
{
  "items": [
    { "event_model": "item", "resource_id": 9, "watched_ms": 800 }
  ]
}
```

#### Item watch (≥ 3s)

```json
{
  "items": [
    { "event_model": "item", "resource_id": 9, "watched_ms": 3500 }
  ]
}
```

#### Item complete (percent ≥ 95)

```json
{
  "items": [
    {
      "event_model": "item",
      "resource_id": 9,
      "watched_ms": 11400,
      "duration_ms": 12000
    }
  ]
}
```

#### Deal skip

```json
{
  "items": [
    { "event_model": "deal", "resource_id": 4, "watched_ms": 500 }
  ]
}
```

#### Mixed batch (item + deal)

```json
{
  "items": [
    { "event_model": "item", "resource_id": 9, "watched_ms": 4500, "duration_ms": 12000 },
    { "event_model": "deal", "resource_id": 3, "watched_ms": 800 }
  ]
}
```

#### Duplicate resource (server keeps highest `watched_ms`)

```json
{
  "items": [
    { "event_model": "item", "resource_id": 9, "watched_ms": 500 },
    { "event_model": "item", "resource_id": 9, "watched_ms": 4000 }
  ]
}
```

→ One result for resource `9` with `watched_ms=4000` (outcome `watch`, `view_counted=true`).

#### Max size (10 events)

```json
{
  "items": [
    { "event_model": "item", "resource_id": 1, "watched_ms": 100 },
    { "event_model": "item", "resource_id": 2, "watched_ms": 100 },
    { "event_model": "item", "resource_id": 3, "watched_ms": 100 },
    { "event_model": "item", "resource_id": 4, "watched_ms": 100 },
    { "event_model": "item", "resource_id": 5, "watched_ms": 100 },
    { "event_model": "deal", "resource_id": 1, "watched_ms": 100 },
    { "event_model": "deal", "resource_id": 2, "watched_ms": 100 },
    { "event_model": "deal", "resource_id": 3, "watched_ms": 100 },
    { "event_model": "deal", "resource_id": 4, "watched_ms": 100 },
    { "event_model": "deal", "resource_id": 5, "watched_ms": 100 }
  ]
}
```

---

### Success response envelope (`200`)

```json
{
  "recorded_count": 2,
  "results": [
    {
      "event_model": "item",
      "resource_id": 9,
      "recorded": true,
      "outcome": "watch",
      "view_counted": true,
      "created": false
    },
    {
      "event_model": "deal",
      "resource_id": 3,
      "recorded": true,
      "outcome": "skip",
      "view_counted": false,
      "created": true
    }
  ]
}
```

| Field | Type | Notes |
|---|---|---|
| `recorded_count` | int | Number of items with `recorded: true` |
| `results` | array | One row per **deduped** input (order follows first occurrence) |
| `results[].event_model` | string | `item` \| `deal` |
| `results[].resource_id` | int | Resource id |
| `results[].recorded` | bool | `true` if Saved successfully |
| `results[].outcome` | string | Present when recorded: `skip` \| `watch` \| `complete` |
| `results[].view_counted` | bool | `true` if this event bumped `detail_views` (`watched_ms >= 3000`) |
| `results[].created` | bool | `true` if a new `FeedImpression` row was created |
| `results[].error` | string | Present when `recorded: false` |

### Partial success (`200`)

Valid + missing resource in one batch:

**Request:**

```json
{
  "items": [
    { "event_model": "item", "resource_id": 9, "watched_ms": 1000 },
    { "event_model": "item", "resource_id": 999999, "watched_ms": 1000 }
  ]
}
```

**Response:**

```json
{
  "recorded_count": 1,
  "results": [
    {
      "event_model": "item",
      "resource_id": 9,
      "recorded": true,
      "outcome": "skip",
      "view_counted": false,
      "created": true
    },
    {
      "event_model": "item",
      "resource_id": 999999,
      "recorded": false,
      "error": "Menu item not found."
    }
  ]
}
```

### Outcome upgrade example

1. First Seen `watched_ms=500` → `outcome=skip`, `view_counted=false`
2. Later `watched_ms=5000`, `duration_ms=10000` → `outcome=watch`, `view_counted=true`
3. Later `watched_ms=9500`, `duration_ms=10000` → `outcome=complete`
4. Later `watched_ms=100` → still `outcome=complete`, `watched_ms` stays `9500` (no downgrade)

---

### Seen batch validation / error responses (`400`)

Request-level failures (body rejected before processing):

#### Empty `items`

**Request:** `{ "items": [] }`

```json
{
  "error": {
    "code": "INVALID",
    "message": "Request failed.",
    "details": {
      "items": ["items must contain between 1 and 10 events."]
    }
  }
}
```

*(Exact `code` / wrapping follows the project’s DRF validation envelope.)*

#### More than 10 items

**Request:** 11 events in `items` → `400` with validation that batch size must be 1…10.

#### Missing `watched_ms`

**Request:**

```json
{
  "items": [
    { "event_model": "item", "resource_id": 9 }
  ]
}
```

→ `400` validation error on `items[].watched_ms`.

#### Invalid `event_model`

**Request:**

```json
{
  "items": [
    { "event_model": "badge", "resource_id": 1, "watched_ms": 100 }
  ]
}
```

→ `400` validation (`event_model` must be `item` or `deal`).

---

## Related APIs

- Explore list (separate state): `GET /api/explore/products/` — [`apps/discovery/docs/explore_api.md`](../../discovery/docs/explore_api.md)
- Manual engagement events: `POST /api/analytics/event/` — [`apps/analytics/docs/analytics_api.md`](../../analytics/docs/analytics_api.md)
- Media object details / upload: [`apps/mediahub/docs/mediaapi.md`](../../mediahub/docs/mediaapi.md)
- Menu / deals serializers: [`apps/restaurants/docs/menu_deals_api.md`](../../restaurants/docs/menu_deals_api.md)
