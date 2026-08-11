# Saved Items / Deals API

**Base:** `/api/saved/`  
**Auth:** JWT + customer profile + `active_mode=customer` on every method.

Customers can save and unsave published menu items and active deals. List/detail return full item/deal payloads.

---

## Permissions

| Requirement | Failure |
|---|---|
| Authenticated + active | `401` |
| Has `CustomerProfile` | `403` |
| `active_mode=customer` | `403 CUSTOMER_MODE_REQUIRED` |

---

## Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/saved/` | Save item or deal (idempotent) |
| GET | `/api/saved/?type=items\|deals` | List (omit `type` for all) |
| GET | `/api/saved/{id}/` | Detail |
| DELETE | `/api/saved/{id}/` | Unsave → `204` |

### POST body

```json
{ "target_type": "item", "menu_item_id": 45 }
```

```json
{ "target_type": "deal", "deal_id": 12 }
```

- First save → `201`
- Already saved → `200` (no second analytics bump)

### Analytics

On **new** save: `ResourceAnalytics` for `(user, menu_item|deal)` `get_or_create`, `save_count += 1`, recalc `engagement_score`.

On unsave: same row `save_count = max(0, save_count - 1)`.

Anonymous aggregate rows are **not** updated.

### Response object (list row / detail / POST)

```json
{
  "id": 9,
  "target_type": "deal",
  "created_at": "2026-08-10T08:00:00+00:00",
  "menu_item": null,
  "deal": { },
  "restaurant": {
    "id": 1,
    "name": "Burger House",
    "slug": "burger-house",
    "logo": null,
    "city_id": 2,
    "city": "Lahore"
  }
}
```

List wrapper:

```json
{ "count": 1, "results": [ /* objects */ ] }
```

### Errors

| Code | HTTP |
|---|---|
| `INVALID_TARGET_TYPE` | 400 |
| `MENU_ITEM_NOT_FOUND` | 404 |
| `DEAL_NOT_FOUND` | 404 |
| `SAVED_NOT_FOUND` | 404 |
| `CUSTOMER_MODE_REQUIRED` | 403 |
