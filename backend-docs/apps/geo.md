# App: `geo`

**Package:** `apps.geo`  
**Depends on:** none (leaf)  
**Purpose:** Cities for location fallback, Explore scoping, and unsupported-city waitlist.

---

## Responsibility

- List / search active cities
- City centers for Nearby when GPS denied
- Waitlist capture (e.g. Sialkot)
- Cached `restaurant_count` per city

---

## File layout

```
apps/geo/
├── __init__.py
├── admin.py
├── apps.py
├── models.py
├── serializers.py
├── urls.py
└── views.py
```

---

## Models

### `City`

| Field | Type | Notes |
|---|---|---|
| `name` | CharField | unique with country |
| `slug` | SlugField | |
| `region` / `province` | CharField | |
| `country_code` | CharField | default `PK` |
| `center_lat` / `center_lng` | Decimal(9,6) | |
| `is_active` | bool | |
| `restaurant_count` | PositiveInteger | cached |
| `sort_order` | int | |

**Seed:** Lahore, Karachi, Islamabad, Faisalabad, Multan.

### `CityWaitlist`

| Field | Type |
|---|---|
| `city_name` | CharField | free text |
| `phone_number` | CharField | optional |
| `user` | FK accounts.User | nullable |
| `created_at` | DateTime | |

---

## API endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/cities/` | Public | Active cities + counts |
| GET | `/api/cities/search/?q=` | Public | Typeahead |
| GET | `/api/cities/{id}/` | Public | Detail + center |
| POST | `/api/cities/waitlist/` | Optional JWT | Join waitlist |
| GET | `/api/bootstrap/` | Optional | Can live here or `core`: app config flags |

---

## Response example

```json
GET /api/cities/
{
  "results": [
    {
      "id": "c_lhr",
      "name": "Lahore",
      "slug": "lahore",
      "region": "Punjab",
      "center_lat": "31.5204",
      "center_lng": "74.3587",
      "restaurant_count": 128,
      "is_active": true
    }
  ]
}
```

---

## Validation

- Waitlist: `city_name` required, min 2 chars
- Search: empty `q` → popular / recent cities (client can also send recent IDs)

---

## Business rules

1. Inactive cities omitted from public list.
2. When GPS denied, discovery uses `city.center_lat/lng`.
3. Never return `"-- km"` — omit distance if no lat/lng.
4. Update `restaurant_count` via signal/task when restaurants change city or pause state.

---

## Admin

- CRUD cities
- View waitlist entries

---

## Tests checklist

- [ ] List only active cities
- [ ] Search fuzzy by name
- [ ] Waitlist create
- [ ] restaurant_count updates after restaurant create/pause
