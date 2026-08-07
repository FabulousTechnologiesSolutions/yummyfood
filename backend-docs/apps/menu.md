# App: `menu`

**Package:** `apps.menu`  
**Depends on:** `restaurants`, `mediahub` (photos/video required to publish)  
**Purpose:** Menu categories, products, per-size pricing, add-ons, console builder CRUD.

---

## Responsibility

- Category CRUD + reorder + visibility
- Menu item CRUD with sizes / offer prices
- Publish immediately (content); promotion is separate app
- Free-tier: max 5 new products / month (counter on Restaurant)
- Customer read-only menu + item detail

---

## File layout

```
apps/menu/
├── __init__.py
├── admin.py
├── apps.py
├── models.py
├── serializers.py
├── urls.py
├── views.py
└── services.py          # SKU gen, quota check, duplicate/move
```

---

## Models

### `MenuCategory`

| Field | Type |
|---|---|
| `restaurant` | FK |
| `slug` | CharField |
| `name` | CharField |
| `icon` | CharField |
| `position` | PositiveInteger |
| `is_visible` | bool |
| UniqueTogether | (`restaurant`, `slug`) |

**Default seeds:**  
`fastfood`, `pakistani`, `continental`, `chinese`, `bbq`, `pizza`, `burgers`, `wraps`, `pasta`, `rice`, `salads`, `soups`, `beverages`, `desserts`, `kids`, `deals`, `addons`

### `MenuItem`

| Field | Type | Notes |
|---|---|---|
| `restaurant` | FK | |
| `category` | FK MenuCategory | primary |
| `cross_categories` | M2M | `also` |
| `name` | CharField | * |
| `description` | TextField | |
| `subcategory` | CharField | optional |
| `item_type` | Chicken/Beef/… | |
| `quantity_label` | CharField | |
| `sku` | CharField | auto e.g. `FA-001` |
| `is_available` | bool | |
| `is_popular` | bool | |
| `is_new` | bool | optional |
| `spicy_level` | 0–3 | |
| `prep_time_min` | int | |
| `calories` | int | legacy |
| `emoji` | CharField | |
| `base_price` | Decimal | denorm min size |
| `status` | `draft` \| `published` \| `hidden` | |
| `published_at` | DateTime | |

### `MenuItemSize`

| Field | Type |
|---|---|
| `menu_item` | FK |
| `label` | CharField |
| `price` | Decimal * |
| `offer_price` | Decimal nullable (&lt; price) |
| `position` | int |

### `AddOn`

| Field | Type |
|---|---|
| `restaurant` | FK |
| `name` | CharField |
| `price` | Decimal |
| `item_type` | CharField |
| `applies_to_categories` | M2M |
| `applies_to_all` | bool |
| `is_available` | bool |

---

## API endpoints

### Customer

| Method | Path |
|---|---|
| GET | `/api/restaurants/{id}/menu/` |
| GET | `/api/menu-items/{id}/` |

### Console — categories

| Method | Path |
|---|---|
| GET/POST | `/api/console/categories/` |
| PATCH/DELETE | `/api/console/categories/{id}/` |
| POST | `/api/console/categories/reorder/` |

### Console — items

| Method | Path |
|---|---|
| GET/POST | `/api/console/menu-items/` |
| GET/PATCH | `/api/console/menu-items/{id}/` |
| POST | `/api/console/menu-items/{id}/duplicate/` |
| POST | `/api/console/menu-items/{id}/move/` |
| POST | `/api/console/menu-items/{id}/hide/` |
| DELETE | `/api/console/menu-items/{id}/` |
| PATCH | `/api/console/menu-items/{id}/availability/` |

### Console — add-ons

| Method | Path |
|---|---|
| GET/POST | `/api/console/addons/` |
| PATCH/DELETE | `/api/console/addons/{id}/` |

---

## Create item example

```json
POST /api/console/menu-items/
{
  "name": "Zinger Burger",
  "description": "Crispy fried chicken...",
  "category_id": "...",
  "item_type": "Chicken",
  "sizes": [
    { "label": "Regular", "price": "690.00", "offer_price": null },
    { "label": "Large", "price": "890.00", "offer_price": "749.00" }
  ],
  "photo_ids": ["ph_1"],
  "video_id": "vid_1",
  "is_available": true,
  "is_popular": true,
  "request_promotion": true,
  "promotion": {
    "title": "Zinger Combo Deal",
    "starts_at": "2026-08-01T00:00:00+05:00",
    "ends_at": "2026-08-03T23:59:59+05:00"
  }
}
```

**On success**

- Item `status=published` immediately
- If `request_promotion` → create `promotions.PromotionRequest` (`pending`)
- Increment restaurant `products_created_this_month`

---

## Validation

- `name`, `category_id` required
- ≥ 1 ready photo; exactly 1 ready video ≤ 60s
- Each size: `price` required; `offer_price < price` if set
- Quota: if ≥ limit → `403 PRODUCT_QUOTA_EXCEEDED`
- Delete: warn if in active deal / live promo / linked video; require `force=true` or block

---

## Business rules

1. **Publish ≠ promote** — item live now; boost after admin approval.
2. Promoted items pinned in console/customer “🔥 Promoted” section when promo `live`.
3. Out of stock: `is_available=false` — dim on customer menu.
4. Cross-list via `cross_categories` (`also` in prototype data).
5. Gallery photos for restaurant are derived from item/deal photos (mediahub).

---

## Tests checklist

- [ ] Create with sizes + media publishes
- [ ] Quota blocks 6th product in month
- [ ] Offer price validation
- [ ] Reorder categories
- [ ] Duplicate / move / hide
- [ ] Promotion request created when toggled
