# Customer report and rating APIs

New customer APIs from this pass (not saved / explore / feed).

**Auth:** JWT + customer profile + `active_mode=customer`  
(`IsAuthenticatedAndActive` + `HasCustomerProfile` + `IsCustomerMode`).

| Failure | HTTP | Code |
|---|---|---|
| Missing/invalid JWT | 401 | — |
| No customer profile | 403 | — |
| `active_mode` is not `customer` | 403 | `CUSTOMER_MODE_REQUIRED` |

**Error envelope:**

```json
{
  "error": {
    "code": "REPORT_EXISTS",
    "message": "You have already reported this item.",
    "details": {}
  }
}
```

---

## 1. Report a menu item

### `POST /api/reports/items/{item_id}/`

Report a **published, available** menu item at a visible restaurant.

**Body:**

| Field | Required | Notes |
|---|---|---|
| `reason` | yes | See reasons below |
| `description` | no | Free text |

**Reasons:** `misleading_price`, `photo_mismatch`, `unavailable`, `other`.

```json
{
  "reason": "misleading_price",
  "description": "Listed at 200 but billed 450"
}
```

Stores `created_by` (the customer) and `created_at` (server timestamp). One report per user + item.

**Success `201`:**

```json
{
  "id": 4,
  "target_type": "item",
  "menu_item_id": 45,
  "deal_id": null,
  "restaurant_id": 1,
  "restaurant_name": "Burger House",
  "reason": "misleading_price",
  "description": "Listed at 200 but billed 450",
  "status": "open",
  "created_by": 9,
  "created_at": "2026-08-17T12:00:00+00:00",
  "title": "Chicken Burger"
}
```

| HTTP | Code | When |
|---|---|---|
| 400 | (validation) | Missing/invalid `reason` |
| 400 | `INVALID_REPORT_REASON` | Reason not in the allowed set |
| 404 | `MENU_ITEM_NOT_FOUND` | Unknown, unpublished, unavailable, or restaurant paused/closed |
| 409 | `REPORT_EXISTS` | This user already reported this item |

---

## 2. Report a deal

### `POST /api/reports/deals/{deal_id}/`

Report an **active** deal (within `starts_at`–`ends_at`) at a visible restaurant.

**Body:** same as item report (`reason`, optional `description`).

```json
{
  "reason": "unavailable",
  "description": "Deal is never honoured"
}
```

Stores `created_by` and `created_at`. One report per user + deal.

**Success `201`:**

```json
{
  "id": 5,
  "target_type": "deal",
  "menu_item_id": null,
  "deal_id": 12,
  "restaurant_id": 1,
  "restaurant_name": "Burger House",
  "reason": "unavailable",
  "description": "Deal is never honoured",
  "status": "open",
  "created_by": 9,
  "created_at": "2026-08-17T12:05:00+00:00",
  "title": "Family Bundle"
}
```

| HTTP | Code | When |
|---|---|---|
| 400 | (validation) | Missing/invalid `reason` |
| 404 | `DEAL_NOT_FOUND` | Unknown, inactive, outside window, or restaurant paused/closed |
| 409 | `REPORT_EXISTS` | This user already reported this deal |

---

## 3. Report a restaurant

### `POST /api/reports/restaurants/{restaurant_id}/`

Report the **entire restaurant** (all of its listings). This is one ticket with `target_type=restaurant`; it does **not** fan out into per-item/per-deal rows.

The same user may also report a specific item or deal at that restaurant — those are separate scopes.

**Body:** same as item report (`reason`, optional `description`).

```json
{
  "reason": "other",
  "description": "The whole menu is misleading"
}
```

Stores `created_by` and `created_at`. One restaurant-scope report per user + restaurant.

**Success `201`:**

```json
{
  "id": 8,
  "target_type": "restaurant",
  "menu_item_id": null,
  "deal_id": null,
  "restaurant_id": 1,
  "restaurant_name": "Burger House",
  "reason": "other",
  "description": "The whole menu is misleading",
  "status": "open",
  "created_by": 9,
  "created_at": "2026-08-17T12:10:00+00:00",
  "title": "Burger House"
}
```

Identify scope from `target_type`:

| `target_type` | `menu_item_id` | `deal_id` | Meaning |
|---|---|---|---|
| `item` | set | `null` | One menu item |
| `deal` | `null` | set | One deal |
| `restaurant` | `null` | `null` | Whole restaurant |

`restaurant_id` is set on every report.

| HTTP | Code | When |
|---|---|---|
| 400 | (validation) | Missing/invalid `reason` |
| 404 | `RESTAURANT_NOT_FOUND` | Unknown, paused, or permanently closed |
| 409 | `REPORT_EXISTS` | This user already filed a restaurant-scope report |

---

## 4. Ratings (item, deal, or restaurant)

Same body for every scope. A second POST on the **same scope** updates stars/description (`200`) instead of creating another row. Item, deal, and restaurant ratings are independent — a customer can rate an item and the restaurant it belongs to.

Restaurant `rating_avg` / `rating_count` / `rating_histogram` are recomputed from **restaurant-scope** ratings only.

**Body:**

| Field | Required | Notes |
|---|---|---|
| `stars` | yes | Integer 1–5 |
| `description` | no | Free text |

```json
{
  "stars": 4,
  "description": "Great food"
}
```

Stores `rated_at` on first create (`auto_now_add`). Later updates keep the original `rated_at` and refresh `updated_at`.

Identify scope from `target_type`:

| `target_type` | `menu_item_id` | `deal_id` | Endpoint |
|---|---|---|---|
| `item` | set | `null` | `POST` / `GET` `/api/menu-items/{item_id}/rating/` |
| `deal` | `null` | set | `POST` / `GET` `/api/deals/{deal_id}/rating/` |
| `restaurant` | `null` | `null` | `POST` / `GET` `/api/restaurants/{restaurant_id}/rating/` |

`restaurant_id` is set on every rating.

**Success `201` (created) / `200` (updated / GET):**

```json
{
  "id": 7,
  "target_type": "restaurant",
  "restaurant_id": 1,
  "menu_item_id": null,
  "deal_id": null,
  "stars": 4,
  "description": "Great food",
  "rated_at": "2026-08-17T13:00:00+00:00",
  "updated_at": "2026-08-17T13:00:00+00:00",
  "created_by": 9
}
```

Item example: `target_type` is `item`, `menu_item_id` is set. Deal example: `target_type` is `deal`, `deal_id` is set.

| HTTP | Code | When |
|---|---|---|
| 400 | `INVALID_STARS` | `stars` not in 1–5 |
| 404 | `RESTAURANT_NOT_FOUND` | Unknown, paused, or permanently closed (restaurant endpoint) |
| 404 | `MENU_ITEM_NOT_FOUND` | Unknown / unpublished / unavailable item |
| 404 | `DEAL_NOT_FOUND` | Unknown / inactive / out-of-window deal |
| 404 | `RATING_NOT_FOUND` | GET when this user has not rated that scope |
