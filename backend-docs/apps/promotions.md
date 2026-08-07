# App: `promotions`

**Package:** `apps.promotions`  
**Depends on:** `restaurants`, `menu` and/or `deals`, `accounts` (admin reviewer)  
**Purpose:** Boosted placement requests; admin approve → `live`, reject → `changes`.

---

## Responsibility

- Create promotion requests from item/deal toggles
- Store reach radius / duration defaults (also on Restaurant)
- Admin queue: approve / reject with note
- Drive `is_promoted` on related videos / discovery ranking
- Free in beta — no payment

**Critical:** Publishing menu content ≠ promotion live.

---

## File layout

```
apps/promotions/
├── __init__.py
├── admin.py
├── apps.py
├── models.py
├── serializers.py
├── urls.py
├── views.py
└── services.py          # approve/reject side effects, expiry job helpers
```

---

## Models

### `PromotionRequest`

| Field | Type | Notes |
|---|---|---|
| `restaurant` | FK | |
| `target_type` | `menu_item` \| `deal` | |
| `menu_item` | FK nullable | |
| `deal` | FK nullable | |
| `title` | CharField | |
| `status` | `pending` \| `live` \| `changes` \| `ended` | |
| `reach_radius_km` | 1\|3\|5\|10 | |
| `duration_days` | 1\|3\|7\|14 | |
| `requested_start` / `requested_end` | DateTime | |
| `admin_note` | TextField | e.g. needs clearer video |
| `reviewed_by` | FK User | nullable |
| `reviewed_at` | DateTime | |
| `goes_live_at` / `ends_at` | DateTime | set on approve |
| `created_at` | DateTime | |

Exactly one of `menu_item` / `deal` must be set.

---

## Status mapping (UI pills)

| Status | UI |
|---|---|
| `pending` | Pending / Awaiting approval |
| `live` | Live / Promoted |
| `changes` | Changes (rejected / needs revision) |
| `ended` | Ended |

---

## API endpoints

### Owner console

| Method | Path |
|---|---|
| GET | `/api/console/promotion-requests/` |
| POST | `/api/console/promotion-requests/` |
| GET | `/api/console/promotion-requests/{id}/` |

Defaults also via restaurants:  
`PATCH /api/console/restaurant/promotion-defaults/`

### Platform admin

| Method | Path |
|---|---|
| GET | `/api/admin-api/promotion-requests/?status=pending` |
| POST | `/api/admin-api/promotion-requests/{id}/approve/` |
| POST | `/api/admin-api/promotion-requests/{id}/reject/` |

```json
POST .../reject/
{ "admin_note": "needs a clearer video" }
```

```json
POST .../approve/
{
  "goes_live_at": null,
  "duration_days": 3,
  "reach_radius_km": 5
}
```

If omitted, use request defaults / restaurant defaults.

---

## Create from menu/deal

```json
POST /api/console/promotion-requests/
{
  "target_type": "deal",
  "deal_id": "deal_1",
  "title": "Zinger Combo Deal",
  "reach_radius_km": 5,
  "duration_days": 3,
  "requested_start": "...",
  "requested_end": "..."
}
```

---

## Side effects on approve

1. `status = live`
2. Set `goes_live_at`, `ends_at` (now + duration or requested window)
3. Mark linked video `is_promoted = true`
4. Notify owner if `notify_on_promo_approval` (push + WhatsApp)
5. Discovery feed includes in “featured/promoted” bucket

## Side effects on reject

1. `status = changes`
2. Save `admin_note`
3. Notify owner
4. Owner may re-submit (new request or reset to pending — choose one policy; recommend new request or `resubmit` endpoint)

## Expiry job

Celery: when `ends_at` passed → `status = ended`, clear `is_promoted` on video.

---

## Business rules

1. Nothing charged in beta.
2. Multiple active promos on one video: discovery picks best-value + “+N more”.
3. Discount &gt; 90%: warn on create (non-blocking).
4. Permissions: owner for own requests; `IsAdminUser` for approve/reject.

---

## Tests checklist

- [ ] Create pending from deal toggle
- [ ] Approve → live + video promoted
- [ ] Reject → changes + note
- [ ] Expiry → ended
- [ ] Non-owner cannot list others’ requests
- [ ] Non-admin cannot approve
