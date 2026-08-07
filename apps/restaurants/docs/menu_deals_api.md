# Restaurant menu & deals API

All menu/deal models and routes live in `apps/restaurants` (restaurant profile setup).  
Promotion requests (promote item/deal for Explore) live in `apps/promotions` and are documented in the **Promotion requests** section below.  
Media upload/presign/delete APIs live in `apps/mediahub` and are documented in the **Mediahub APIs** section below (also mirrored in [`apps/mediahub/docs/mediaapi.md`](../../mediahub/docs/mediaapi.md)).

**Auth (restaurant):** `Authorization: Bearer <access_jwt>` — requires restaurant ownership **and** `active_mode=restaurant` (`IsRestaurantOwner` + `IsRestaurantMode`). Dual-profile users in customer mode receive `403 RESTAURANT_MODE_REQUIRED`.  
**Auth (public):** none (`AllowAny`) under `/api/public/…`.

**Error envelope:**

```json
{
  "error": {
    "code": "PRODUCT_QUOTA_EXCEEDED",
    "message": "Free plan allows 5 products per month.",
    "details": { "limit": 5, "used": 5 }
  }
}
```

---

## Shared shapes

### Category object

```json
{
  "id": 12,
  "slug": "burgers",
  "name": "Burgers",
  "icon": "",
  "position": 6,
  "is_visible": true
}
```

### Size object (response)

```json
{
  "id": 3,
  "label": "Regular",
  "price": "450.00",
  "offer_price": "399.00",
  "position": 0
}
```

`offer_price` may be `null`.

### Size input (request)

```json
{
  "label": "Regular",
  "price": "450.00",
  "offer_price": "399.00",
  "position": 0
}
```

| Field | Required on create | Notes |
|---|---|---|
| `label` | yes | max 40 |
| `price` | yes | decimal string/number |
| `offer_price` | no | must be **&lt;** `price` if set |
| `position` | no | default by array index |

### Media object (response)

```json
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
}
```

Video example (after processing):

```json
{
  "id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
  "type": "video",
  "url": "/media/restaurants/1/items/9/media/.../clip.mp4",
  "is_cover": false,
  "order_index": 2,
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
```

`processing_status`: `""` | `pending` | `processing` | `ready` | `failed`.

### Media input (request)

**New upload** (after client uploaded via presign):

```json
{
  "type": "image",
  "url": "https://pub-xxx.r2.dev/uploads/tmp/1/abc_cover.jpg",
  "is_cover": true
}
```

URL may also be a bare storage key: `"uploads/tmp/1/abc_cover.jpg"`.

**Keep existing on update** (omit deletes the rest):

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "type": "image",
  "is_cover": true
}
```

| Field | Required | Notes |
|---|---|---|
| `type` | yes | `image` \| `video` |
| `url` | for new rows | ignored when `id` is present |
| `id` | update keep | UUID of existing `ContentMedia` |
| `is_cover` | no | images only; at most one cover |

**Rules:** ≥1 image, exactly 1 video. If no cover flagged, first image becomes cover.

### Menu item object

```json
{
  "id": 9,
  "restaurant_id": 1,
  "category_ids": [12, 7],
  "categories": [
    {"id": 12, "slug": "burgers", "name": "Burgers", "icon": "", "position": 6, "is_visible": true},
    {"id": 7, "slug": "fastfood", "name": "Fast Food", "icon": "", "position": 0, "is_visible": true}
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
  "is_promoted": false,
  "promoted_starts_at": null,
  "promoted_ends_at": null,
  "spicy_level": 1,
  "prep_time_min": 15,
  "calories": null,
  "emoji": "",
  "base_price": "399.00",
  "status": "published",
  "published_at": "2026-08-05T08:00:00+00:00",
  "sizes": [
    {
      "id": 3,
      "label": "Regular",
      "price": "450.00",
      "offer_price": "399.00",
      "position": 0
    }
  ],
  "media": [],
  "created_at": "2026-08-05T08:00:00+00:00",
  "updated_at": "2026-08-05T08:00:00+00:00"
}
```

`item_type` choices: `Chicken`, `Beef`, `Mutton`, `Fish`, `Veg`, `Vegetarian`, `Egg`, `Mixed`, or `""`.  
`status` choices: `draft`, `published`, `hidden`.  
`spicy_level`: `0`–`3` or `null`.  
`is_promoted` / `promoted_starts_at` / `promoted_ends_at`: set only via **Promotion requests** (admin approve); owners cannot PATCH these directly.

### Deal line object (response)

```json
{
  "id": 1,
  "menu_item_id": 9,
  "menu_item_name": "Chicken Burger",
  "size_label": "Regular",
  "unit_price": "450.00",
  "quantity": 1,
  "position": 0
}
```

### Deal line input (request)

```json
{
  "menu_item_id": 9,
  "size_label": "Regular",
  "unit_price": "450.00",
  "quantity": 1,
  "position": 0
}
```

### Deal object

```json
{
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
  "lines": [],
  "media": [],
  "created_at": "2026-08-05T08:00:00+00:00",
  "updated_at": "2026-08-05T08:00:00+00:00"
}
```

`days_of_week`: `0`=Mon … `6`=Sun.  
`status`: `draft`, `active`, `ended`, `hidden`.  
`deal_price` must be **&lt;** `items_total` (server-computed from lines).  
`is_promoted` / promo window fields: set via **Promotion requests** only.

---

## Categories

Categories are **global** (not per restaurant). Default seeds (`fastfood` … `addons`) are created once and shared. Any restaurant owner can create additional categories.

### `GET /api/restaurant/categories/`

List categories for the authenticated restaurant.

**Response `200`:**

```json
[
  {
    "id": 1,
    "slug": "fastfood",
    "name": "Fast Food",
    "icon": "",
    "position": 0,
    "is_visible": true
  }
]
```

---

### `POST /api/restaurant/categories/`

**Request:**

```json
{
  "slug": "specials",
  "name": "Specials",
  "icon": "⭐",
  "position": 20,
  "is_visible": true
}
```

| Field | Required | Default |
|---|---|---|
| `slug` | yes | — |
| `name` | yes | — |
| `icon` | no | `""` |
| `position` | no | `0` |
| `is_visible` | no | `true` |

**Response `201`:** category object.

**Errors:** `CATEGORY_SLUG_EXISTS` (409).

---

### `PATCH /api/restaurant/categories/{id}/`

Partial update. All fields optional.

**Request:**

```json
{
  "name": "Burgers & Wraps",
  "is_visible": false,
  "position": 3,
  "icon": "",
  "slug": "burgers"
}
```

**Response `200`:** category object.

**Errors:** `CATEGORY_NOT_FOUND` (404), `CATEGORY_SLUG_EXISTS` (409).

---

### `DELETE /api/restaurant/categories/{id}/`

**Response `204`:** empty body.

**Errors:** `CATEGORY_NOT_FOUND` (404), `CATEGORY_IN_USE` (400) if items still reference it.

---

### `POST /api/restaurant/categories/reorder/`

**Request:**

```json
{
  "ordered_ids": [3, 1, 2, 5]
}
```

**Response `200`:** full category list in new order (same shape as list).

**Errors:** `CATEGORY_NOT_FOUND` (404).

---

## Menu items

### `GET /api/restaurant/menu-items/`

**Response `200`:** array of menu item objects (with `sizes` + `media`).

---

### `POST /api/restaurant/menu-items/`

Creates and **publishes** immediately. Counts toward free-tier monthly quota (default 5).

**Request (full):**

```json
{
  "category_ids": [12, 7],
  "name": "Chicken Burger",
  "description": "Juicy grilled chicken",
  "subcategory": "",
  "item_type": "Chicken",
  "quantity_label": "1 pc",
  "sku": "",
  "is_available": true,
  "is_popular": false,
  "is_new": true,
  "spicy_level": 1,
  "prep_time_min": 15,
  "calories": 520,
  "emoji": "",
  "sizes": [
    { "label": "Regular", "price": "450.00", "offer_price": "399.00", "position": 0 },
    { "label": "Large", "price": "550.00", "position": 1 }
  ],
  "media": [
    { "type": "image", "url": "uploads/tmp/1/cover.jpg", "is_cover": true },
    { "type": "image", "url": "uploads/tmp/1/side.jpg" },
    { "type": "video", "url": "uploads/tmp/1/walk.mp4" }
  ]
}
```

**Minimal request:**

```json
{
  "category_ids": [12],
  "name": "Chicken Burger",
  "sizes": [{ "label": "Regular", "price": "450.00" }],
  "media": [
    { "type": "image", "url": "uploads/tmp/1/a.jpg", "is_cover": true },
    { "type": "video", "url": "uploads/tmp/1/b.mp4" }
  ]
}
```

| Field | Required | Notes |
|---|---|---|
| `category_ids` | yes | ≥1 global category ids |
| `name` | yes | |
| `sizes` | yes | ≥1 |
| `media` | yes | ≥1 image + exactly 1 video |
| `sku` | no | auto `FA-00N` if blank |
| others | no | see shared shapes |

**Response `201`:** menu item object.

**Errors:**

| Code | Status |
|---|---|
| `PRODUCT_QUOTA_EXCEEDED` | 403 |
| `CATEGORY_NOT_FOUND` | 404 |
| `SIZES_REQUIRED` | 400 |
| `INVALID_OFFER_PRICE` | 400 |
| `MEDIA_REQUIRED` | 400 |
| `VIDEO_REQUIRED` | 400 |
| `INVALID_COVER` | 400 |
| `INVALID_MEDIA_URL` | 400 |
| `INVALID_SPICY_LEVEL` | 400 |

---

### `GET /api/restaurant/menu-items/{id}/`

**Response `200`:** menu item object.

**Errors:** `MENU_ITEM_NOT_FOUND` (404).

---

### `PATCH /api/restaurant/menu-items/{id}/`

Partial update. Omit `sizes` / `media` to leave them unchanged. If `media` is sent, it is a full sync (keep by `id`, add new, delete omitted).

**Request (example):**

```json
{
  "name": "Chicken Burger Deluxe",
  "is_popular": true,
  "status": "published",
  "sizes": [
    { "label": "Regular", "price": "480.00", "offer_price": null }
  ],
  "media": [
    { "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890", "type": "image", "is_cover": true },
    { "id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", "type": "video" },
    { "type": "image", "url": "uploads/tmp/1/new.jpg" }
  ]
}
```

**Response `200`:** menu item object.

**Errors:** same as create where applicable + `MENU_ITEM_NOT_FOUND` (404).

---

### `DELETE /api/restaurant/menu-items/{id}/`

Deletes item and its media (storage + DB).

**Response `204`:** empty body.

**Errors:** `MENU_ITEM_NOT_FOUND` (404).

---

### `POST /api/restaurant/menu-items/{id}/duplicate/`

No body. Creates a copy (`name` + ` (copy)`), new SKU, counts toward quota, re-attaches media from source file keys.

**Response `201`:** menu item object.

**Errors:** `MENU_ITEM_NOT_FOUND` (404), `PRODUCT_QUOTA_EXCEEDED` (403), media/size errors as on create.

---

### `POST /api/restaurant/menu-items/{id}/move/`

**Request:**

```json
{
  "category_id": 8
}

Sets the item's `categories` M2M to this single category.
```

**Response `200`:** menu item object (updated `category`).

**Errors:** `MENU_ITEM_NOT_FOUND` (404), `CATEGORY_NOT_FOUND` (404).

---

### `POST /api/restaurant/menu-items/{id}/hide/`

No body. Sets `status` to `hidden`.

**Response `200`:** menu item object.

**Errors:** `MENU_ITEM_NOT_FOUND` (404).

---

### `PATCH /api/restaurant/menu-items/{id}/availability/`

**Request:**

```json
{
  "is_available": false
}
```

**Response `200`:** menu item object.

**Errors:** `MENU_ITEM_NOT_FOUND` (404).

---

## Deals

### `GET /api/restaurant/deals/?segment=active|pending|ended`

| `segment` | Meaning |
|---|---|
| `active` (default) | `status=active` and now within `[starts_at, ends_at]` |
| `pending` | stub — always `[]` (use promotion-requests for promo status) |
| `ended` | `status=ended` or `ends_at` &lt; now |

**Response `200`:** array of deal objects.

**Errors:** `INVALID_SEGMENT` (400).

---

### `POST /api/restaurant/deals/`

**Request (full):**

```json
{
  "label": "Lunch Deal",
  "description": "Burger + drink special",
  "deal_price": "400.00",
  "starts_at": "2026-08-05T00:00:00Z",
  "ends_at": "2026-08-12T23:59:59Z",
  "days_of_week": [0, 1, 2, 3, 4],
  "terms": "Valid for dine-in only",
  "status": "active",
  "lines": [
    {
      "menu_item_id": 9,
      "size_label": "Regular",
      "unit_price": "450.00",
      "quantity": 1,
      "position": 0
    },
    {
      "menu_item_id": 10,
      "size_label": "Regular",
      "unit_price": "50.00",
      "quantity": 1,
      "position": 1
    }
  ],
  "media": [
    { "type": "image", "url": "uploads/tmp/1/deal_cover.jpg", "is_cover": true },
    { "type": "video", "url": "uploads/tmp/1/deal.mp4" }
  ]
}
```

**Minimal request:**

```json
{
  "label": "Lunch Deal",
  "deal_price": "400.00",
  "starts_at": "2026-08-05T00:00:00Z",
  "ends_at": "2026-08-12T23:59:59Z",
  "lines": [
    {
      "menu_item_id": 9,
      "size_label": "Regular",
      "unit_price": "500.00",
      "quantity": 1
    }
  ],
  "media": [
    { "type": "image", "url": "uploads/tmp/1/a.jpg", "is_cover": true },
    { "type": "video", "url": "uploads/tmp/1/b.mp4" }
  ]
}
```

| Field | Required | Notes |
|---|---|---|
| `label` | yes | |
| `deal_price` | yes | must be &lt; sum of line totals |
| `starts_at` / `ends_at` | yes | `ends_at` &gt; `starts_at` |
| `lines` | yes | ≥1; items must belong to restaurant |
| `media` | yes | same rules as menu items |
| `status` | no | default `active` |

Server sets `items_total`, `savings_amount`, `savings_percent`.

**Response `201`:** deal object.

**Errors:**

| Code | Status |
|---|---|
| `LINES_REQUIRED` | 400 |
| `INVALID_DEAL_PRICE` | 400 |
| `INVALID_SCHEDULE` | 400 |
| `MENU_ITEM_NOT_FOUND` | 404 |
| `MEDIA_REQUIRED` / `VIDEO_REQUIRED` / … | 400 |

---

### `GET /api/restaurant/deals/{id}/`

**Response `200`:** deal object.

**Errors:** `DEAL_NOT_FOUND` (404).

---

### `PATCH /api/restaurant/deals/{id}/`

Partial update. Sending `lines` replaces all lines. Sending `media` full-syncs media.

**Request (example):**

```json
{
  "label": "Extended Lunch Deal",
  "deal_price": "380.00",
  "ends_at": "2026-08-20T23:59:59Z",
  "status": "active",
  "lines": [
    {
      "menu_item_id": 9,
      "size_label": "Large",
      "unit_price": "550.00",
      "quantity": 1
    }
  ]
}
```

**Response `200`:** deal object.

**Errors:** same as create where applicable + `DEAL_NOT_FOUND` (404).

---

### `DELETE /api/restaurant/deals/{id}/`

**Response `204`:** empty body.

**Errors:** `DEAL_NOT_FOUND` (404).

---

### `GET /api/restaurant/deals/{id}/preview/`

Same as deal detail plus `"preview": true`.

**Response `200`:**

```json
{
  "id": 4,
  "restaurant_id": 1,
  "label": "Lunch Deal",
  "description": "",
  "deal_price": "400.00",
  "items_total": "500.00",
  "savings_amount": "100.00",
  "savings_percent": "20.00",
  "starts_at": "2026-08-05T00:00:00+00:00",
  "ends_at": "2026-08-12T23:59:59+00:00",
  "days_of_week": [0, 1, 2, 3, 4],
  "terms": "",
  "status": "active",
  "lines": [],
  "media": [],
  "created_at": "2026-08-05T08:00:00+00:00",
  "updated_at": "2026-08-05T08:00:00+00:00",
  "preview": true
}
```

**Errors:** `DEAL_NOT_FOUND` (404).

---

## Promotion requests

Request Explore promotion for a **menu item** or **deal**. Implemented in `apps/promotions` (same restaurant JWT auth as menu/deals).

**Flow:** owner submits request → admin approves → resource gets `is_promoted=true` + window → Explore promoted pool. Rejected requests become `changes`. Midnight Celery job clears expired promos.

Also documented in [`apps/promotions/docs/promotions_api.md`](../../promotions/docs/promotions_api.md).

### Promotion request object

```json
{
  "id": 3,
  "restaurant_id": 1,
  "event_model": "item",
  "resource_id": 9,
  "menu_item_id": 9,
  "deal_id": null,
  "status": "pending",
  "requested_start": "2026-08-07T00:00:00+05:00",
  "requested_end": "2026-08-10T23:59:59+05:00",
  "goes_live_at": null,
  "ends_at": null,
  "admin_note": "",
  "reviewed_at": null,
  "created_at": "2026-08-07T08:00:00+00:00",
  "updated_at": "2026-08-07T08:00:00+00:00"
}
```

| Field | Notes |
|---|---|
| `event_model` | `item` \| `deal` |
| `resource_id` | Menu item or deal PK matching `event_model` |
| `status` | `pending` \| `live` \| `changes` \| `ended` |
| `requested_start` / `requested_end` | Owner-requested promo window (`end` must be after `start`) |
| `goes_live_at` / `ends_at` | Set on admin approve (defaults to requested window) |
| `admin_note` | Filled on reject |

---

### `GET /api/restaurant/promotion-requests/`

List promotion requests for the authenticated restaurant (newest first).

**Auth:** restaurant owner + `active_mode=restaurant`.

**Response `200`:** array of promotion request objects.

---

### `POST /api/restaurant/promotion-requests/`

Submit a promotion request for an owned menu item or deal.

**Auth:** restaurant owner + `active_mode=restaurant`.

**Request (promote a menu item):**

```json
{
  "event_model": "item",
  "resource_id": 9,
  "requested_start": "2026-08-07T00:00:00+05:00",
  "requested_end": "2026-08-10T23:59:59+05:00"
}
```

**Request (promote a deal):**

```json
{
  "event_model": "deal",
  "resource_id": 4,
  "requested_start": "2026-08-07T00:00:00+05:00",
  "requested_end": "2026-08-14T23:59:59+05:00"
}
```

| Field | Required | Notes |
|---|---|---|
| `event_model` | yes | `item` or `deal` |
| `resource_id` | yes | Must belong to this restaurant |
| `requested_start` | yes | ISO datetime |
| `requested_end` | yes | Must be **after** `requested_start` |

**Response `201`:** promotion request object (`status`: `pending`).

**Errors:**

| Code | Status | When |
|---|---|---|
| `INVALID_EVENT_MODEL` | 400 | `event_model` not `item`/`deal` |
| `INVALID_PROMO_WINDOW` | 400 | end ≤ start |
| `MENU_ITEM_NOT_FOUND` | 404 | item missing or not owned |
| `DEAL_NOT_FOUND` | 404 | deal missing or not owned |
| `RESTAURANT_MODE_REQUIRED` | 403 | user not in restaurant mode |
| `RESTAURANT_REQUIRED` | 403 | no restaurant profile |

---

### `GET /api/restaurant/promotion-requests/{id}/`

**Auth:** restaurant owner + `active_mode=restaurant`.

**Response `200`:** promotion request object.

**Errors:** `PROMOTION_REQUEST_NOT_FOUND` (404).

---

### Admin: list / approve / reject

Staff (`IsAdminUser`) endpoints for the review queue.

#### `GET /api/admin-api/promotion-requests/?status=pending`

Optional `status` filter (`pending` \| `live` \| `changes` \| `ended`).

**Response `200`:** array of promotion request objects.

#### `POST /api/admin-api/promotion-requests/{id}/approve/`

**Request (optional overrides):**

```json
{
  "goes_live_at": "2026-08-07T00:00:00+05:00",
  "ends_at": "2026-08-10T23:59:59+05:00"
}
```

If omitted, uses `requested_start` / `requested_end`.

**Side effects:**

1. Request `status` → `live`
2. Target MenuItem or Deal: `is_promoted=true`, `promoted_starts_at`, `promoted_ends_at` set
3. Creates a `FeaturedCampaign` for that window (ROI counters)

**Response `200`:** updated promotion request object.

**Errors:** `PROMOTION_REQUEST_NOT_FOUND` (404), `ALREADY_LIVE` (400), `ALREADY_ENDED` (400), `INVALID_PROMO_WINDOW` (400).

#### `POST /api/admin-api/promotion-requests/{id}/reject/`

**Request:**

```json
{
  "admin_note": "Needs a clearer video"
}
```

`admin_note` optional. Sets `status` → `changes`. Does **not** change the item/deal promo flags.

**Response `200`:** updated promotion request object.

**Errors:** `PROMOTION_REQUEST_NOT_FOUND` (404), `ALREADY_REJECTED` (400), `ALREADY_LIVE` (400).

---

### Expiry

Celery task `apps.promotions.tasks.expire_promotions` runs daily at **00:00 Asia/Karachi**:

- Clears `is_promoted` (+ start/end) when `promoted_ends_at <= now`
- Marks linked live promotion requests as `ended`

---

## Public reads

No auth required. Menu items must be `published`; deals must be `active` and within schedule.

### `GET /api/public/restaurants/{restaurant_id}/`

Combined restaurant profile: essentials + visible categories + published menu items + active deals.

**Response `200`:**

```json
{
  "restaurant": {
    "id": 1,
    "name": "My Restaurant",
    "slug": "my-restaurant",
    "short_description": "",
    "cuisines": [],
    "price_range": "",
    "logo": null,
    "cover": null,
    "primary_phone": "+923001234567",
    "whatsapp_number": "",
    "street_address": "",
    "area": "",
    "city_id": null,
    "lat": null,
    "lng": null,
    "rating_avg": "0.0",
    "rating_count": 0,
    "is_paused": false
  },
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
  "menu_items": [
    {
      "id": 9,
      "restaurant_id": 1,
      "category_ids": [12],
      "name": "Chicken Burger",
      "status": "published",
      "sizes": [],
      "media": []
    }
  ],
  "deals": [
    {
      "id": 4,
      "restaurant_id": 1,
      "label": "Lunch Deal",
      "deal_price": "400.00",
      "status": "active",
      "lines": [],
      "media": []
    }
  ]
}
```

`logo` / `cover` are public media URLs or `null`. `lat` / `lng` are decimal strings or `null`.

**Errors:** `RESTAURANT_NOT_FOUND` (404).

---

### `GET /api/public/menu-items/{id}/`

**Response `200`:** menu item object (published only).

**Errors:** `MENU_ITEM_NOT_FOUND` (404).

---

### `GET /api/public/deals/{id}/`

**Response `200`:** deal object (`status=active` only).

**Errors:** `DEAL_NOT_FOUND` (404).

---

## Mediahub APIs

Same auth as restaurant console: `IsAuthenticatedAndActive` + `IsRestaurantOwner` + `IsRestaurantMode`.  
Base prefix: `/api/restaurant/`.  
Shared media object / `media[]` input shapes are defined under [Shared shapes](#shared-shapes) above.

### Upload flow (client)

```
1. POST /api/restaurant/uploads/presign/     → key, upload_url, public_url
2. PUT  upload_url  (binary file)            → store object
3. POST /api/restaurant/menu-items|deals/    → media[].url = public_url or key
4. (optional) DELETE orphan keys / media rows
```

Storage layout after attach:

- Original: `restaurants/{restaurant_id}/{items|deals}/{entity_id}/media/{media_id}/…`
- HLS + thumb: `restaurants/{restaurant_id}/{items|deals}/{entity_id}/video/{media_id}/…`

---

### `POST /api/restaurant/uploads/presign/`

Request a temporary object key and upload URL. Does **not** upload bytes.

**Request:**

```json
{
  "filename": "burger.jpg",
  "content_type": "image/jpeg",
  "byte_size": 245678,
  "kind": "image"
}
```

| Field | Required | Type | Notes |
|---|---|---|---|
| `filename` | yes | string | max 255; used in generated key |
| `content_type` | yes | string | e.g. `image/jpeg`, `video/mp4` |
| `byte_size` | yes | int | ≥ 1; ≤ `MAX_UPLOAD_BYTES` (default 100 MiB) |
| `kind` | no | string | hint only (`image`, `video`, …); echoed back |

**Response `200` (R2 / production):**

```json
{
  "key": "uploads/tmp/1/a1b2c3d4e5f6_burger.jpg",
  "upload_url": "https://….r2.cloudflarestorage.com/…?X-Amz-Algorithm=…",
  "public_url": "https://pub-xxx.r2.dev/uploads/tmp/1/a1b2c3d4e5f6_burger.jpg",
  "expires_in": 3600,
  "content_type": "image/jpeg",
  "kind": "image"
}
```

**Response `200` (local / `USE_LOCAL_MEDIA=true`):**

```json
{
  "key": "uploads/tmp/1/a1b2c3d4e5f6_burger.jpg",
  "upload_url": "/api/restaurant/uploads/local/?key=uploads/tmp/1/a1b2c3d4e5f6_burger.jpg",
  "public_url": "/media/uploads/tmp/1/a1b2c3d4e5f6_burger.jpg",
  "expires_in": 3600,
  "content_type": "image/jpeg",
  "kind": "image"
}
```

| Field | Notes |
|---|---|
| `key` | Object key under `uploads/tmp/{restaurant_id}/` |
| `upload_url` | Where the client `PUT`s the file |
| `public_url` | URL/path to pass later in `media[].url` |
| `expires_in` | Seconds until R2 presign expires |

**Client upload after presign**

- **R2:** HTTP `PUT` to `upload_url` with file bytes and matching `Content-Type`
- **Local:** `PUT`/`POST` to the local upload path (next section)

**Errors:** `INVALID_UPLOAD_SIZE` (400), `RESTAURANT_MODE_REQUIRED` (403), `RESTAURANT_REQUIRED` (403).

---

### `PUT` / `POST /api/restaurant/uploads/local/`

Dev/test upload target when `USE_LOCAL_MEDIA=true`. Not used in production R2 mode.

| Param | Required | Notes |
|---|---|---|
| `key` | yes | Query `?key=` or form field; must start with `uploads/tmp/{restaurant_id}/` |

**Request body** — one of:

1. Multipart field `file` or `upload`
2. Raw body written as the object

```http
PUT /api/restaurant/uploads/local/?key=uploads/tmp/1/a1b2_burger.jpg
Authorization: Bearer <token>
Content-Type: multipart/form-data; boundary=----bound

------bound
Content-Disposition: form-data; name="file"; filename="burger.jpg"
Content-Type: image/jpeg

<binary>
------bound--
```

**Response `200`:**

```json
{
  "key": "uploads/tmp/1/a1b2_burger.jpg",
  "public_url": "/media/uploads/tmp/1/a1b2_burger.jpg"
}
```

**Errors:** `KEY_REQUIRED` (400), `KEY_FORBIDDEN` (403), `FILE_REQUIRED` (400), `RESTAURANT_MODE_REQUIRED` (403), `RESTAURANT_REQUIRED` (403).

---

### `DELETE /api/restaurant/uploads/`

Delete a storage object by key (orphan / temp cleanup). No `ContentMedia` row required.

**Request:**

```json
{
  "key": "uploads/tmp/1/a1b2c3d4e5f6_burger.jpg"
}
```

| Field | Required | Notes |
|---|---|---|
| `key` | yes | Must start with `uploads/tmp/{restaurant_id}/` **or** `restaurants/{restaurant_id}/` |

**Response `200`:**

```json
{
  "deleted": true,
  "key": "uploads/tmp/1/a1b2c3d4e5f6_burger.jpg"
}
```

**Errors:** `KEY_REQUIRED` (400), `KEY_FORBIDDEN` (403), `RESTAURANT_MODE_REQUIRED` (403), `RESTAURANT_REQUIRED` (403).

---

### `DELETE /api/restaurant/media/{media_id}/`

Delete a `ContentMedia` row and its storage objects (original file, thumbnail, HLS prefix).  
`media_id` is a UUID. No body.

```http
DELETE /api/restaurant/media/a1b2c3d4-e5f6-7890-abcd-ef1234567890/
Authorization: Bearer <token>
```

**Response `200`:**

```json
{
  "deleted": true,
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**Cover reassignment:** If the deleted row was a cover image and other images remain on that menu item / deal, the newest remaining image becomes cover.

**Errors:** `MEDIA_NOT_FOUND` (404), `RESTAURANT_MODE_REQUIRED` (403), `RESTAURANT_REQUIRED` (403).

---

### Video processing (background)

Triggered when a menu item or deal is created/updated with a new video `ContentMedia`.

Celery task: `process_content_video`

| Step | Result |
|---|---|
| Download original | from storage key |
| Probe | width, height, duration |
| Reject if `duration` > 60s | status → `failed` after retries |
| Thumbnail @ 2s | `…/video/{media_id}/thumbnail.jpg` |
| HLS ladder | 240p–1080p (source-capped), fMP4 segments |
| Master playlist | `…/video/{media_id}/hls/master.m3u8` |

Status flow: `pending` → `processing` → `ready` \| `failed` (up to 3 retries).

No push notification on ready/failed in this phase. Clients poll menu item / deal responses for `media[].processing_status`.

**Storage keys (video outputs):**

```
restaurants/{restaurant_id}/{items|deals}/{entity_id}/video/{media_id}/thumbnail.jpg
restaurants/{restaurant_id}/{items|deals}/{entity_id}/video/{media_id}/hls/master.m3u8
restaurants/{restaurant_id}/{items|deals}/{entity_id}/video/{media_id}/hls/{quality}/index.m3u8
restaurants/{restaurant_id}/{items|deals}/{entity_id}/video/{media_id}/hls/{quality}/init.mp4
restaurants/{restaurant_id}/{items|deals}/{entity_id}/video/{media_id}/hls/{quality}/segment000.m4s
…
```

---

### Media attach errors (on menu / deal create & update)

| Code | Status | When |
|---|---|---|
| `MEDIA_REQUIRED` | 400 | no media, or no images |
| `VIDEO_REQUIRED` | 400 | not exactly one video |
| `INVALID_COVER` | 400 | more than one `is_cover` |
| `INVALID_MEDIA_URL` | 400 | cannot parse `url` into a storage key |

---

### Mediahub endpoint summary

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/restaurant/uploads/presign/` | Get tmp key + upload URL |
| `PUT`/`POST` | `/api/restaurant/uploads/local/` | Local file upload (dev) |
| `DELETE` | `/api/restaurant/uploads/` | Delete object by key |
| `DELETE` | `/api/restaurant/media/{uuid}/` | Delete ContentMedia + files |
