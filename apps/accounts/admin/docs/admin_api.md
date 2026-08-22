# Admin platform APIs

REST APIs for the platform admin dashboard. Mounted at `/api/admin/`.

**Login** is the shared auth endpoint `POST /api/auth/login/` (not under `/api/admin/`). After login, send `Authorization: Bearer <access>` on every `/api/admin/` call.

**Auth on `/api/admin/`:** JWT + active account + **admin role** (`is_staff` or `is_superuser`). Permission stack: `IsAuthenticatedAndActive` + `IsAdminRole`.

The client should treat `profiles.platform_admin === true` as the dashboard gate. A valid JWT from a customer/restaurant account still gets `403 ADMIN_REQUIRED` on `/api/admin/`.

Non-admin authenticated users receive:

```json
{
  "error": {
    "code": "ADMIN_REQUIRED",
    "message": "Admin role required.",
    "details": {}
  }
}
```

Unauthenticated → `401`.

**Pagination** (all list endpoints): page-number. Default `page_size` is **10**, max **100**.

| Param | Default | Notes |
|---|---|---|
| `page` | `1` | 1-based |
| `page_size` | `10` | 1–100 |

**List envelope:**

```json
{
  "count": 23,
  "next": "http://localhost:6060/api/admin/users/?page=2",
  "previous": null,
  "results": []
}
```

`next` / `previous` are absolute URLs or `null`. Invalid `page` → `404`.

**Error envelope** (all endpoints):

```json
{
  "error": {
    "code": "REPORT_NOT_FOUND",
    "message": "Report not found.",
    "details": {}
  }
}
```

---

## 1. Login

There is no separate `/api/admin/login/`. Platform admins use the same phone + password login as other accounts.

### `POST /api/auth/login/`

**Auth:** public (`AllowAny`).

**Body:**

| Field | Required | Notes |
|---|---|---|
| `phone_number` | yes | E.164 (`+923008452119`) or PK local (`03008452119` / `3008452119`) |
| `password` | yes | |
| `session_key` | no | Guest session merge; omit for the admin dashboard |

```json
{
  "phone_number": "+923001110000",
  "password": "secret123"
}
```

**Success `200`:**

```json
{
  "id": 1,
  "phone_number": "+923001110000",
  "display_name": "Platform Admin",
  "active_mode": "customer",
  "profiles": {
    "customer": false,
    "restaurant": false,
    "platform_admin": true
  },
  "restaurant": null,
  "tokens": {
    "access": "<jwt>",
    "refresh": "<jwt>"
  }
}
```

Use `tokens.access` as `Authorization: Bearer <access>` on `/api/admin/` routes. `profiles.platform_admin` is `true` when `user.is_staff` is set.

Login itself does **not** reject non-admins (any active account can log in). If `platform_admin` is `false`, do not open the admin dashboard — `/api/admin/` will return `403 ADMIN_REQUIRED`.

| HTTP | Code | When |
|---|---|---|
| 400 | `INVALID` | Missing/invalid fields (serializer) |
| 400 | `INVALID_PHONE` | Unparseable phone |
| 401 | `INVALID_CREDENTIALS` | Wrong phone or password |
| 401 | `ACCOUNT_DELETED` | Soft-deleted or inactive account (message is still “Invalid credentials.”) |
| 404 | `SESSION_NOT_FOUND` | `session_key` sent but unknown |

### `POST /api/auth/refresh/`

**Auth:** public. Rotates tokens; old refresh is blacklisted when possible.

```json
{
  "refresh": "<refresh_jwt>"
}
```

**Success `200`:**

```json
{
  "access": "<new_access_jwt>",
  "refresh": "<new_refresh_jwt>"
}
```

| HTTP | Code | When |
|---|---|---|
| 401 | `INVALID_TOKEN` | Invalid or expired refresh |

### `POST /api/auth/logout/`

**Auth:** JWT (`IsAuthenticatedAndActive`). Blacklists the refresh token.

```json
{
  "refresh": "<refresh_jwt>"
}
```

**Success `204`** (empty body).

| HTTP | Code | When |
|---|---|---|
| 400 | `INVALID_TOKEN` | Invalid or expired refresh |
| 401 | — | Missing/invalid JWT |

---

## 2. Overview

### `GET /api/admin/overview/`

Dashboard cards: pending promotion requests, open reports, and the oldest waiting queue (promotions + reports).

**Query params:** none.

**Success `200`:**

```json
{
  "pending_promotion_requests": 3,
  "open_reports": 2,
  "oldest_waiting": [
    {
      "id": 12,
      "type": "promotion",
      "title": "Chicken Burger",
      "restaurant_name": "Burger House",
      "waiting_minutes": 45
    },
    {
      "id": 4,
      "type": "report",
      "title": "Family Deal",
      "restaurant_name": "Burger House",
      "waiting_minutes": 20
    }
  ]
}
```

`oldest_waiting` is the oldest pending promotions and open reports, merged and sorted by `created_at`, capped at 10. `type` is `"promotion"` or `"report"`.

| HTTP | Code | When |
|---|---|---|
| 401 | — | Missing/invalid JWT |
| 403 | `ADMIN_REQUIRED` | Not staff/superuser |

---

## 3. Reports

Customer-submitted item/deal reports (`engagement.ContentReport`). Default list is **open**.

### `GET /api/admin/reports/`

**Query params:**

| Param | Required | Values |
|---|---|---|
| `status` | no | `open` (default), `actioned`, `dismissed` |
| `target_type` | no | `item`, `deal`, `restaurant` |
| `restaurant_id` | no | All reports for that restaurant (any scope) |
| `page` | no | default `1` |
| `page_size` | no | default `10`, max `100` |

**Success `200`:**

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 4,
      "target_type": "item",
      "menu_item_id": 45,
      "deal_id": null,
      "restaurant_id": 1,
      "restaurant_name": "Burger House",
      "reason": "photo_mismatch",
      "description": "Looks different",
      "status": "open",
      "created_by": 9,
      "created_by_phone": "+923001112233",
      "created_at": "2026-08-17T12:00:00+00:00",
      "title": "Chicken Burger",
      "report_count": 2,
      "age_minutes": 90,
      "reviewed_by": null,
      "reviewed_at": null,
      "admin_note": ""
    }
  ]
}
```

`target_type` is the scope: `item` / `deal` (one listing) or `restaurant` (the whole restaurant). `restaurant_id` is always set. For restaurant-scope rows, `menu_item_id` and `deal_id` are `null` and `title` is the restaurant name.

`report_count` is how many reports exist for the **same target** (same item, same deal, or restaurant-scope reports for the same restaurant).

Use `?target_type=restaurant` for restaurant-level tickets only. Use `?restaurant_id=` to see every report about that place (item + deal + restaurant).

### `GET /api/admin/reports/{id}/`

**Success `200`:** same object as a list row.

### `POST /api/admin/reports/{id}/action/`

Mark **actioned**. Optional note.

**Body (all optional):**

```json
{ "admin_note": "Took down the photo" }
```

**Success `200`:** report object with `status: "actioned"`, `reviewed_by`, `reviewed_at`.

### `POST /api/admin/reports/{id}/dismiss/`

Mark **dismissed**. Same optional body as action.

**Success `200`:** report object with `status: "dismissed"`.

| HTTP | Code | When |
|---|---|---|
| 400 | `INVALID_REPORT_STATUS` | `?status=` not open/actioned/dismissed |
| 400 | `INVALID_TARGET_TYPE` | `?target_type=` not item/deal/restaurant |
| 400 | `INVALID_RESTAURANT_ID` | `?restaurant_id=` is not an integer |
| 404 | `REPORT_NOT_FOUND` | Unknown id |
| 403 | `ADMIN_REQUIRED` | Not admin |

---

## 4. Promotion requests

Same `PromotionService` as owner requests. Going **live** writes the promo window onto the linked menu item or deal:

- `PromotionRequest.status = live`, `goes_live_at`, `ends_at`
- `MenuItem` or `Deal`: `is_promoted=true`, `promoted_starts_at`, `promoted_ends_at`
- Creates `FeaturedCampaign`

Those promo fields are already on every public/open item and deal payload (`serialize_menu_item` / `serialize_deal`).

### `GET /api/admin/promotion-requests/`

**Query params:**

| Param | Required | Values |
|---|---|---|
| `status` | no | `pending`, `live`, `changes`, `ended` (omit for all) |
| `page` | no | default `1` |
| `page_size` | no | default `10`, max `100` |

**Success `200`:**

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 12,
      "restaurant_id": 1,
      "restaurant_name": "Burger House",
      "event_model": "item",
      "resource_id": 45,
      "menu_item_id": 45,
      "deal_id": null,
      "title": "Chicken Burger",
      "status": "pending",
      "requested_start": "2026-08-17T12:00:00+00:00",
      "requested_end": "2026-08-20T23:59:59+00:00",
      "goes_live_at": null,
      "ends_at": null,
      "admin_note": "",
      "reviewed_at": null,
      "created_at": "2026-08-16T09:00:00+00:00",
      "updated_at": "2026-08-16T09:00:00+00:00"
    }
  ]
}
```

### `POST /api/admin/promotion-requests/{request_id}/approve/`

Go **live**. **`starts_at` (or `goes_live_at`) and `ends_at` are required.** `ends_at` must be after the start.

**Body (required):**

```json
{
  "starts_at": "2026-08-17T12:00:00+05:00",
  "ends_at": "2026-08-20T23:59:59+05:00"
}
```

Alias: `"goes_live_at"` instead of `"starts_at"`.

**Success `200`:** promotion object with `status: "live"`, `goes_live_at`, `ends_at`.

### `POST /api/admin/promotion-requests/{request_id}/reject/`

Reject → `status: "changes"`. Does **not** clear promo flags on the item/deal (not live yet). **`admin_note` is required** (non-empty).

**Body (required):**

```json
{
  "admin_note": "Needs a clearer video and better price"
}
```

**Success `200`:** promotion object with `status: "changes"` and `admin_note`.

| HTTP | Code | When |
|---|---|---|
| 400 | (validation) | Missing `starts_at`/`ends_at` on approve, or missing `admin_note` on reject |
| 400 | `INVALID_PROMO_WINDOW` | `ends_at` ≤ start |
| 400 | `ALREADY_LIVE` | Approve/reject a live request |
| 400 | `ALREADY_ENDED` | Approve an ended request |
| 400 | `ALREADY_REJECTED` | Reject already in `changes` |
| 404 | `PROMOTION_REQUEST_NOT_FOUND` | Unknown id |

---

## 5. Restaurants

### `GET /api/admin/restaurants/`

**Query params:**

| Param | Required | Values |
|---|---|---|
| `status` | no | `live`, `paused`, `claim`, `incomplete` |
| `q` | no | Search name, area, city |
| `page` | no | default `1` |
| `page_size` | no | default `10`, max `100` |

**Derived `status`:** `paused` if `is_paused`; else `claim` if `claim_status` is `unclaimed` or `pending_claim`; else `incomplete` if setup completeness &lt; 100%; else `live`.

**Success `200`:**

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Burger House",
      "area": "Gulberg",
      "city": "Lahore",
      "city_id": 2,
      "logo": "https://example.com/media/restaurants/logos/logo.png",
      "products_count": 12,
      "promotions_count": 1,
      "pending_promotions_count": 2,
      "status": "live",
      "claim_status": "owned",
      "is_paused": false,
      "setup_completeness_pct": 100,
      "rating_avg": "4.5",
      "rating_count": 8,
      "owner_id": 3
    }
  ]
}
```

`products_count` is published menu items. `promotions_count` is live promotion requests; `pending_promotions_count` is pending.

### `GET /api/admin/restaurants/{id}/`

**Success `200`:** same object as a list row.

| HTTP | Code | When |
|---|---|---|
| 400 | `INVALID_RESTAURANT_STATUS` | Bad `?status=` |
| 404 | `RESTAURANT_NOT_FOUND` | Unknown id |

---

## 6. Users

Soft-deleted users (`deleted_at` set) are excluded.

### `GET /api/admin/users/`

**Query params:**

| Param | Required | Values |
|---|---|---|
| `role` | no | `customer`, `owner`, `staff` |
| `q` | no | Search phone or display name |
| `page` | no | default `1` |
| `page_size` | no | default `10`, max `100` |

**Derived `role`:** `staff` if `is_staff` or `is_superuser`; else `owner` if the user owns a restaurant; else `customer`.

`last_active_at` is `last_login`, falling back to `date_joined`.

**Success `200`:**

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 9,
      "display_name": "Ahmad",
      "phone_number": "+923001112233",
      "role": "customer",
      "last_active_at": "2026-08-17T10:00:00+00:00",
      "is_staff": false,
      "is_superuser": false,
      "active_mode": "customer",
      "date_joined": "2026-07-01T08:00:00+00:00"
    }
  ]
}
```

### `GET /api/admin/users/{id}/`

**Success `200`:** same object as a list row.

| HTTP | Code | When |
|---|---|---|
| 400 | `INVALID_USER_ROLE` | Bad `?role=` |
| 404 | `USER_NOT_FOUND` | Unknown or soft-deleted id |

---

## 7. Categories

Official global categories via `CategoryService`. Owner routes at `/api/restaurant/categories/` are unchanged.

List includes `used_by` = distinct restaurants that have menu items in that category.

### `GET /api/admin/categories/`

**Query params:** `page`, `page_size` (see pagination above).

**Success `200`:**

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 12,
      "slug": "burgers",
      "name": "Burgers",
      "icon": "",
      "position": 6,
      "is_visible": true,
      "used_by": 2
    }
  ]
}
```

### `POST /api/admin/categories/`

**Body:**

| Field | Required | Notes |
|---|---|---|
| `name` | yes | max 120 |
| `slug` | no | Generated from `name` if omitted |
| `icon` | no | |
| `position` | no | default 0 |
| `is_visible` | no | default true |

```json
{ "name": "Wraps", "icon": "🌯", "position": 8, "is_visible": true }
```

**Success `201`:** category object including `used_by` (0 for a new category).

### `PATCH /api/admin/categories/{id}/`

Partial update. Same fields as create (all optional).

**Success `200`:** updated category object.

### `DELETE /api/admin/categories/{id}/`

**Success `204`** if unused. If any menu items still use it → `400 CATEGORY_IN_USE`.

| HTTP | Code | When |
|---|---|---|
| 404 | `CATEGORY_NOT_FOUND` | Unknown id |
| 409 | `CATEGORY_SLUG_EXISTS` | Duplicate slug on create/update |
| 400 | `CATEGORY_IN_USE` | Delete while menu items remain |

---

## 8. Backward-compatible aliases

Existing dashboard clients on `/api/admin-api/` keep working. Same handlers as above except **approve** still allows an empty body (falls back to the request’s `requested_start` / `requested_end`).

| Method | Path | Notes |
|---|---|---|
| GET | `/api/admin-api/promotion-requests/` | Same as `/api/admin/promotion-requests/` |
| POST | `/api/admin-api/promotion-requests/{request_id}/approve/` | Window optional |
| POST | `/api/admin-api/promotion-requests/{request_id}/reject/` | `admin_note` optional on this alias |

Prefer `/api/admin/` for new clients (required window + required reject note).
