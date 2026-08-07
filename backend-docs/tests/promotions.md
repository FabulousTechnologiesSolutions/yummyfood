# Tests: `promotions`

**Package:** `tests/promotions/`  
**Files:** `factories.py`, `test_console_promotions_api.py`, `test_admin_promotions_api.py`

---

## Console (owner)

### `GET /console/promotion-requests/`

| Case | Type | Expect |
|---|---|---|
| Lists own requests with status pills | + | 200 |
| Does not include other restaurants | + | filtered |
| No auth / non-owner | − | 401 / 403 |

### `POST /console/promotion-requests/`

| Case | Type | Expect |
|---|---|---|
| Create for deal with radius/duration | + | 201 `pending` |
| Create for menu_item | + | 201 |
| Missing target (no deal/item) | − | 400 |
| Both deal and item set | − | 400 |
| Invalid radius | − | 400 |
| Foreign deal/item | − | 403/404 |
| No auth | − | 401 |

### `GET /console/promotion-requests/{id}/`

| Case | Type | Expect |
|---|---|---|
| Own request detail | + | 200 |
| Foreign request | − | 403/404 |

---

## Admin

### `GET /admin-api/promotion-requests/?status=pending`

| Case | Type | Expect |
|---|---|---|
| Staff lists pending queue | + | 200 |
| Non-staff | − | 403 |
| No auth | − | 401 |

### `POST /admin-api/promotion-requests/{id}/approve/`

| Case | Type | Expect |
|---|---|---|
| Approve → `live`, video `is_promoted`, ends_at set | + | 200 |
| Approve already live | − | 409 |
| Non-staff | − | 403 |
| Unknown id | − | 404 |

### `POST /admin-api/promotion-requests/{id}/reject/`

| Case | Type | Expect |
|---|---|---|
| Reject with `admin_note` → `changes` | + | 200 |
| Reject without note (if required) | − | 400 |
| Non-staff | − | 403 |

---

## Side-effect / integration cases

| Case | Type | Expect |
|---|---|---|
| After approve, feed promoted bucket can include video | + | integration with feed |
| Expiry job → `ended`, clear is_promoted | + | task/unit test |
| Owner cannot call approve | − | 403 |

---

## Factories

- `PromotionRequestFactory` (pending)
- `LivePromotionFactory`
- `ChangesPromotionFactory`
- `AdminUserFactory` (reuse accounts)
