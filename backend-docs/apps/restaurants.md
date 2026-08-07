# App: `restaurants`

**Package:** `apps.restaurants`  
**Depends on:** `accounts`, `geo`  
**Purpose:** Restaurant entity, ownership, claim flow, console settings, dashboard checklist, pause listing.

---

## Responsibility

- Create / update restaurant profile (R-17–R-21 fields)
- Multi-profile: user may own **at most one** restaurant (`owner` OneToOne)
- Creating/claiming a second restaurant for the same user → **409** `RESTAURANT_PROFILE_EXISTS`
- Claim unclaimed listing (OTP to listed phone)
- Setup checklist for dashboard
- Free-tier product quota counters (enforced with menu app)
- Public restaurant profile payload for customer app

---

## File layout

```
apps/restaurants/
├── __init__.py
├── admin.py
├── apps.py
├── models.py
├── serializers.py
├── urls.py
├── views.py
├── services.py          # checklist, claim OTP, quota helpers
└── signals.py           # seed default menu categories on create
```

---

## Models

### `Restaurant`

| Field | Type | Notes |
|---|---|---|
| `owner` | **OneToOneField(User)** | `related_name="restaurant"`; unique — max one restaurant per user |
| `name` | CharField(120) | required |
| `slug` | SlugField | unique |
| `short_description` | TextField | |
| `cuisines` | ArrayField | **max 3** |
| `price_range` | `$`–`$$$$` | |
| `logo` / `cover` | ImageField | 1:1 / 16:9 |
| `primary_phone` | CharField | checklist |
| `whatsapp_number` | CharField | blank |
| `use_different_whatsapp` | bool | |
| `secondary_phone` | CharField | |
| `street_address` | CharField | |
| `area` | CharField | |
| `city` | FK City | |
| `lat` / `lng` | Decimal(9,6) | pin ≠ geocoded address |
| `rating_avg` / `rating_count` | | display Phase 1 |
| `rating_histogram` | JSON | |
| `is_paused` | bool | |
| `is_permanently_closed` | bool | |
| `claim_status` | `owned` \| `unclaimed` \| `pending_claim` | |
| `promo_default_radius_km` | 1\|3\|5\|10 | default 5 |
| `promo_default_duration_days` | 1\|3\|7\|14 | default 3 |
| `notify_on_promo_approval` | bool | True |
| `auto_request_promo_on_deal` | bool | False |
| `products_created_this_month` | int | |
| `products_quota_month` | DateField | month key |
| `created_at` / `updated_at` | | |

### `RestaurantClaim` (optional table)

| Field | Type |
|---|---|
| `restaurant` | FK |
| `user` | FK |
| `otp_hash` | CharField |
| `expires_at` | DateTime |
| `status` | `pending` \| `verified` \| `expired` |

---

## API endpoints

### Public / customer

| Method | Path | Auth |
|---|---|---|
| GET | `/api/v1/restaurants/{id}/` | Public |
| GET | `/api/v1/restaurants/{id}/menu/` | Public (or proxy menu app) |
| GET | `/api/v1/restaurants/{id}/videos/` | Public |
| GET | `/api/v1/restaurants/{id}/photos/` | Public (derived) |
| GET | `/api/v1/restaurants/{id}/deals/` | Public |

### Ownership / claim

| Method | Path | Auth |
|---|---|---|
| POST | `/api/v1/me/restaurants/` | JWT |
| POST | `/api/v1/restaurants/{id}/claim/` | JWT |
| POST | `/api/v1/restaurants/{id}/claim/verify/` | JWT |

### Console

| Method | Path | Auth |
|---|---|---|
| GET | `/api/v1/console/dashboard/` | Owner |
| GET/PATCH | `/api/v1/console/restaurant/` | Owner |
| PATCH | `/api/v1/console/restaurant/media/` | Owner |
| PATCH | `/api/v1/console/restaurant/contact/` | Owner |
| PATCH | `/api/v1/console/restaurant/address/` | Owner |
| PATCH | `/api/v1/console/restaurant/promotion-defaults/` | Owner |
| POST | `/api/v1/console/restaurant/pause/` | Owner |

Console uses `request.user.restaurant` (single). No `X-Active-Restaurant-Id` header.

---

## Setup checklist (dashboard)

| Key | Complete when |
|---|---|
| `restaurant_created` | always |
| `profile` | short_description + ≤3 cuisines + price_range |
| `logo_cover` | logo and cover set |
| `contact` | primary_phone set |
| `address` | street + city + lat/lng |
| `menu` | ≥ 1 published menu item |

Return `completed_count / total` + deep-link keys.

---

## Business rules

1. Paused / permanently closed → hidden from Feed, Explore, Search.
2. Map pin (`lat`/`lng`) is editable separately from typed address.
3. Cuisines max 3.
4. Missing logo → client monogram; missing cover → placeholder.
5. Claim: OTP sent to **listed** `primary_phone`, not claimant’s phone.
6. Creating restaurant seeds default menu categories (signal → menu app).
7. Product quota fields live here; **enforcement** on menu item create.

---

## Validation

- `name` required on create
- Address patch: `street_address`, `city` required when completing checklist
- Contact: `primary_phone` required for “contact” checklist item
- Pause: toggle `is_paused`

---

## Public profile response (sketch)

```json
{
  "id": "r_1",
  "name": "Burger House",
  "logo_url": "...",
  "cover_url": "...",
  "rating_avg": 4.7,
  "rating_count": 312,
  "cuisines": ["Burgers", "American"],
  "price_range": "$$",
  "distance_km": 2.3,
  "primary_phone": "+92...",
  "whatsapp_number": "+92...",
  "lat": 31.52,
  "lng": 74.35,
  "active_deal_count": 2,
  "tabs": { "deals": true, "menu": true, "videos": true, "photos": true }
}
```

Hide empty tabs (`deals`/`menu`/`videos`/`photos`) when counts are 0.

---

## Tests checklist

- [ ] Create restaurant under user → has_restaurant_profile
- [ ] Second create for same user → 409
- [ ] Checklist completeness calculation
- [ ] Pause hides from public list endpoints
- [ ] Claim OTP verify transfers ownership only if claimant has no restaurant yet
