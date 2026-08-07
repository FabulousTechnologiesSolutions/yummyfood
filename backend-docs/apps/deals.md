# App: `deals`

**Package:** `apps.deals`  
**Depends on:** `restaurants`, `menu`, `mediahub`, optionally `promotions`  
**Purpose:** Combo / deal offers bundling menu items at one deal price.

---

## Responsibility

- Create/edit deals with line items (item + size + unit price snapshot)
- Require photo(s) + exactly one video ≤ 60s
- Derive savings from items total vs deal price
- List segments: Active / Pending (promo) / Ended
- Customer promo-sheet payload for deals
- Optional auto promotion request when restaurant `auto_request_promo_on_deal`

---

## File layout

```
apps/deals/
├── __init__.py
├── admin.py
├── apps.py
├── models.py
├── serializers.py
├── urls.py
├── views.py
└── services.py          # totals, savings, preview, segment filters
```

---

## Models

### `Deal`

| Field | Type | Notes |
|---|---|---|
| `restaurant` | FK | |
| `label` | CharField | DEAL LABEL * |
| `description` | TextField | |
| `deal_price` | Decimal | * |
| `items_total` | Decimal | derived |
| `savings_amount` | Decimal | derived |
| `savings_percent` | Decimal | derived |
| `starts_at` / `ends_at` | DateTime | |
| `days_of_week` | ArrayField(int) | 0=Mon … 6=Sun |
| `terms` | TextField | |
| `status` | `draft` \| `active` \| `ended` \| `hidden` | |
| `view_count` | int | optional cache |
| `whatsapp_clicks` / `call_clicks` / `save_count` | int | optional |

**Rule:** `deal_price` &lt; `items_total`.

### `DealLine`

| Field | Type |
|---|---|
| `deal` | FK |
| `menu_item` | FK menu.MenuItem |
| `size_label` | CharField |
| `unit_price` | Decimal | snapshot |
| `quantity` | PositiveSmallInteger default 1 |
| `position` | int |

---

## API endpoints

### Customer

| Method | Path |
|---|---|
| GET | `/api/deals/{id}/` |
| GET | `/api/deals/{id}/similar/` |
| GET | `/api/restaurants/{id}/deals/` |

### Console

| Method | Path |
|---|---|
| GET | `/api/console/deals/?segment=active\|pending\|ended` |
| POST | `/api/console/deals/` |
| GET/PATCH/DELETE | `/api/console/deals/{id}/` |
| GET | `/api/console/deals/{id}/preview/` |

---

## Create example

```json
POST /api/console/deals/
{
  "label": "Zinger Combo Deal",
  "description": "Zinger + Fries + Drink",
  "lines": [
    { "menu_item_id": "mi_1", "size_label": "Regular", "unit_price": "690.00", "quantity": 1 },
    { "menu_item_id": "mi_2", "size_label": "Medium", "unit_price": "280.00", "quantity": 1 },
    { "menu_item_id": "mi_3", "size_label": "500ml", "unit_price": "280.00", "quantity": 1 }
  ],
  "deal_price": "999.00",
  "starts_at": "2026-08-01T00:00:00+05:00",
  "ends_at": "2026-08-31T23:59:59+05:00",
  "days_of_week": [4, 5, 6],
  "terms": "Dine-in and takeaway only. Cannot combine with other offers.",
  "photo_ids": ["ph_d1"],
  "video_id": "vid_d1",
  "request_promotion": true
}
```

Server computes: `items_total=1250`, `savings_amount=251`, `savings_percent=20`.

---

## Promo sheet response (`GET /deals/{id}/`)

Include:

- prices, countdown, `promo_state` (`active` / `expiring_soon` / `expired` / `scheduled`)
- terms list
- restaurant meta + contact
- `prefill_message` for WhatsApp
- `promotion_status` from promotions app
- `is_saved`

WhatsApp template:

```text
Hi! I saw your "{label}" deal on FoodApp — is it available today?
```

---

## Segments (console list)

| Segment | Meaning |
|---|---|
| `active` | Deal on menu / running window |
| `pending` | Deal live on menu but promotion request pending |
| `ended` | Past `ends_at` or status ended |

---

## Validation

- ≥ 1 line; media rules same as menu item
- `deal_price` &lt; sum(line unit_price × qty)
- `ends_at` &gt; `starts_at`
- Warn (non-blocking) if duration &gt; 90 days
- Warn if overlapping promo on same items

---

## Business rules

1. Deal publishes to menu **immediately**; boosted placement waits on promotion approval.
2. If `auto_request_promo_on_deal`, create PromotionRequest even without toggle.
3. Expired deep links return 200 with `promo_state=expired` + similar deals.
4. Days-of-week filter: deal redeemable only on selected weekdays (display + optional server flag).

---

## Tests checklist

- [ ] Savings math
- [ ] Reject deal_price ≥ items_total
- [ ] Segments filter correctly
- [ ] Preview matches customer serializer
- [ ] Auto-request promotion when setting enabled
