# Tests: `menu`

**Package:** `tests/menu/`  
**Files:** `factories.py`, `test_public_menu_api.py`, `test_console_menu_api.py`

---

## Public

### `GET /restaurants/{id}/menu/`

| Case | Type | Expect |
|---|---|---|
| Returns visible categories + published items | + | 200 |
| Hidden category omitted | + | not in list |
| Unavailable items included but flagged | + | `is_available=false` |
| Paused restaurant | − | 404 |

### `GET /menu-items/{id}/`

| Case | Type | Expect |
|---|---|---|
| Detail with sizes + media | + | 200 |
| Draft/hidden item for public | − | 404 |
| Unknown id | − | 404 |

---

## Console categories

| Endpoint | + | − |
|---|---|---|
| `GET /console/categories/` | 200 list | no auth 401; non-owner 403 |
| `POST /console/categories/` | 201 name+icon | missing name 400; duplicate slug 400/409 |
| `PATCH /console/categories/{id}/` | 200 rename/visibility | other restaurant’s category 404/403 |
| `DELETE /console/categories/{id}/` | 204/200 | category with items policy; foreign 403 |
| `POST /console/categories/reorder/` | 200 positions updated | invalid ids 400; non-owner 403 |

---

## Console menu items

### `POST /console/menu-items/`

| Case | Type | Expect |
|---|---|---|
| Valid name, category, sizes, photo_ids, video_id | + | 201 published |
| With `request_promotion` → pending promo | + | 201 + PromotionRequest pending |
| Offer price &lt; price per size | + | 201 |
| Missing name | − | 400 |
| No photos / no video | − | 400 |
| offer_price ≥ price | − | 400 |
| 6th product in month (quota 5) | − | 403 `PRODUCT_QUOTA_EXCEEDED` |
| No auth | − | 401 |
| Non-owner | − | 403 |

### `GET/PATCH /console/menu-items/{id}/`

| Case | Type | Expect |
|---|---|---|
| GET own item | + | 200 |
| PATCH name / sizes | + | 200 |
| PATCH other owner’s item | − | 403/404 |
| Invalid size payload | − | 400 |

### Actions

| Endpoint | + | − |
|---|---|---|
| `POST .../duplicate/` | 201 new item | foreign 403; quota exceeded 403 |
| `POST .../move/` | 200 new category | category other restaurant 400; foreign 403 |
| `POST .../hide/` | 200 status hidden | foreign 403 |
| `DELETE .../` | 204 when safe | in active promo without force → 409; foreign 403 |
| `PATCH .../availability/` | 200 toggle | foreign 403 |

---

## Add-ons

| Endpoint | + | − |
|---|---|---|
| `GET/POST /console/addons/` | list / create | missing name/price 400; non-owner 403 |
| `PATCH/DELETE /console/addons/{id}/` | update / delete | foreign 403/404 |

---

## Factories

- `MenuCategoryFactory`
- `MenuItemFactory` (+ sizes, ready photo/video)
- `MenuItemSizeFactory`
- `AddOnFactory`
- `QuotaExhaustedRestaurantFactory` (5 products this month)
