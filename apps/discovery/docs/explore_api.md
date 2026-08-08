# Explore / Discovery API

## `GET /api/explore/products/`

Public feed for the Explore tab (`AllowAny`). No request body — all inputs are **query params**.

- Optional JWT: if present, rotation uses `user_id`; otherwise guest rotation uses **`ip_hash`** of client IP (`X-Forwarded-For` first hop or `REMOTE_ADDR`).
- Serving a card writes `ExploreImpression` and an analytics `impression` event.

---

### Query params

| Param | Type | Required | Default | Notes |
|---|---|---|---|---|
| `lat` | float | no | — | Must be sent **with** `lng`. Range −90…90 |
| `lng` | float | no | — | Must be sent **with** `lat`. Range −180…180 |
| `distance_km` | int | no | — | Hard radius when lat/lng set. Allowed: **`1` \| `3` \| `5` \| `10` \| `25` \| `50`**. Requires lat/lng |
| `city_id` | int | no | — | Filter restaurants by `city_id` |
| `category_ids` | int[] | no | all | Repeat param or comma-separated: `category_ids=1&category_ids=3` or `category_ids=1,3,5` |
| `min_price` | number | no | — | Inclusive lower bound. Item → `base_price`; Deal → `deal_price` |
| `max_price` | number | no | — | Inclusive upper bound |
| `page` | int | no | `1` | Must be ≥ 1 |
| `page_size` | int | no | `20` | Must be 1…100 |

**CamelCase aliases** (accepted): `categoryIds`, `minPrice`, `maxPrice`.

There is **no POST payload** for this endpoint.

---

### Example requests

```http
GET /api/explore/products/
GET /api/explore/products/?page=1&page_size=20
GET /api/explore/products/?lat=31.52&lng=74.35
GET /api/explore/products/?lat=31.52&lng=74.35&distance_km=5
GET /api/explore/products/?city_id=10
GET /api/explore/products/?lat=31.52&lng=74.35&city_id=10&distance_km=10
GET /api/explore/products/?category_ids=1,3,5&min_price=500&max_price=1000
GET /api/explore/products/?minPrice=500&maxPrice=1000&categoryIds=12
```

---

### Filter order (before ranking)

1. **City** (`city_id`)  
2. **Location** (`lat` / `lng` / `distance_km`)  
3. **Category** (`category_ids`) — Items by M2M categories; Deals if any deal-line menu item is in a selected category  
4. **Price** (`min_price` / `max_price`)  
5. **Explore compose** (Promoted + Organic)

---

### Geo modes

| Mode | Params | Behavior |
|---|---|---|
| Hard radius | `lat` + `lng` + `distance_km` | Only restaurants within that km. No auto-expand. Cards include `distance_km` |
| Default max | `lat` + `lng` only | Cap **50 km**. Candidates ordered nearest-first, then compose. `applied_radius_km` = `50` |
| City only | `city_id` (no lat/lng) | City filter; `distance_km` on rows is `null`; `applied_radius_km` is `null` |
| City + coords | `city_id` + `lat`/`lng` [(+ `distance_km`)] | City first, then radius inside that city |
| Global | none of the above | Full eligible pool; no distances |

---

### Feed composition

Repeating block **`P, O, D, O`** while organic stock remains:

| Slot | Meaning |
|---|---|
| `P` | Promoted item or deal |
| `O` | Organic menu **item** (cross-fill with deal if items empty) |
| `D` | Organic **deal** (cross-fill with item if deals empty) |

- When unique promos are exhausted, **cycle** from the first promoted again (`P1, P2, P1, P2, …`) until organics run out — do **not** drop into promo-less blocks while organic remains.
- Each served card (including a **repeated** promo) records `ExploreImpression` + analytics `impression`.
- Stop cycling promoted once **both** organic item and deal pools are empty (no infinite P-only loop).
- **No promoted** → organic-only blocks preferring **`O, D, O, O`** with the same cross-fill.
- Never leave empty slots while eligible organic (or unique promo-only) stock remains.

**Viewer history:**

1. **Unseen first (promoted + organic):** never-served cards stay on **top**. Unseen ranking does **not** use global analytics (distance / id only).
2. **Seen use global engagement:** already-served cards are ordered by anonymous `ResourceAnalytics.engagement_score` (higher first). Among organic seen in a mixed feed, score then `last_served_at`.
3. **Promoted rotate:** only after **all** currently eligible promos have been seen — score-sort first, then rotate for equal exposure.
4. **Organic example** with 50 items and `page_size=20` on each `page=1`: first open serves 20; next open leads with remaining unread; then all-seen mode.
5. **All-seen organic:** sort by **highest global engagement_score**, then viewer `ExploreImpression.serve_count`.

Serving a card writes `ExploreImpression` and an analytics `impression`.

---

## Response envelope (`200`)

```json
{
  "results": [ /* result rows — see below */ ],
  "page": 1,
  "page_size": 20,
  "has_more": true,
  "next_page": 2,
  "applied_radius_km": 50,
  "city_id": 10,
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
| `city_id` | int \| null | Echo of filter (or `null`) |
| `min_price` | number \| null | Echo of filter (or `null`) |
| `max_price` | number \| null | Echo of filter (or `null`) |
| `category_ids` | int[] \| null | Echo of filter; `null` if none passed |

---

## Result row shapes

Each element of `results` is:

```json
{
  "slot": "promoted",
  "type": "item",
  "distance_km": 2.3,
  "data": { }
}
```

| Field | Values |
|---|---|
| `slot` | `promoted` \| `organic` |
| `type` | `item` \| `deal` |
| `distance_km` | number (1 decimal) when lat/lng used, else `null` |
| `data` | Full menu-item object **or** deal object (see below) |

### Type A — `type: "item"` (menu item `data`)

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
        "duration": null
      }
    ],
    "created_at": "2026-08-05T08:00:00+00:00",
    "updated_at": "2026-08-05T08:00:00+00:00"
  }
}
```

### Type B — `type: "deal"` (deal `data`)

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
    "media": [],
    "created_at": "2026-08-05T08:00:00+00:00",
    "updated_at": "2026-08-05T08:00:00+00:00"
  }
}
```

---

## Full response examples by mode

### 1) Global (no geo / filters)

**Request:** `GET /api/explore/products/?page=1&page_size=4`

```json
{
  "results": [
    {
      "slot": "organic",
      "type": "item",
      "distance_km": null,
      "data": { "id": 9, "name": "Chicken Burger", "base_price": "399.00" }
    },
    {
      "slot": "organic",
      "type": "deal",
      "distance_km": null,
      "data": { "id": 4, "label": "Lunch Deal", "deal_price": "400.00" }
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

*(Truncated `data` for brevity; production returns full item/deal objects as above.)*

### 2) Lat/lng only (default 50 km)

**Request:** `GET /api/explore/products/?lat=31.52&lng=74.35&page_size=4`

```json
{
  "results": [
    {
      "slot": "promoted",
      "type": "item",
      "distance_km": 2.3,
      "data": { "id": 9, "is_promoted": true, "base_price": "999.00" }
    },
    {
      "slot": "organic",
      "type": "deal",
      "distance_km": 1.1,
      "data": { "id": 4, "deal_price": "400.00" }
    },
    {
      "slot": "organic",
      "type": "item",
      "distance_km": 1.5,
      "data": { "id": 11, "base_price": "850.00" }
    },
    {
      "slot": "organic",
      "type": "item",
      "distance_km": 3.2,
      "data": { "id": 12, "base_price": "650.00" }
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

### 3) Hard radius + filters

**Request:**  
`GET /api/explore/products/?lat=31.52&lng=74.35&distance_km=5&city_id=10&category_ids=12&min_price=500&max_price=1000`

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
      }
    },
    {
      "slot": "organic",
      "type": "item",
      "distance_km": 1.5,
      "data": {
        "id": 11,
        "category_ids": [12],
        "base_price": "750.00"
      }
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

### 4) City only

**Request:** `GET /api/explore/products/?city_id=10`

```json
{
  "results": [],
  "page": 1,
  "page_size": 20,
  "has_more": false,
  "next_page": null,
  "applied_radius_km": null,
  "city_id": 10,
  "min_price": null,
  "max_price": null,
  "category_ids": null
}
```

*(Empty `results` when nothing matches; same envelope.)*

### 5) Last page

```json
{
  "results": [
    {
      "slot": "organic",
      "type": "item",
      "distance_km": null,
      "data": { "id": 20 }
    }
  ],
  "page": 3,
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

## Error responses

Same FoodApp error envelope:

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

## Related APIs

- Track engagement after user actions: `POST /api/analytics/event/` — see [`apps/analytics/docs/analytics_api.md`](../../analytics/docs/analytics_api.md)
- Promote an item/deal: `POST /api/restaurant/promotion-requests/` — see [`apps/restaurants/docs/menu_deals_api.md`](../../restaurants/docs/menu_deals_api.md) (Promotion requests)
