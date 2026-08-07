# Tests: `geo`

**Package:** `tests/geo/`  
**Files:** `factories.py`, `test_cities_api.py`

Base: `/api/cities/`, `/api/bootstrap/`

---

## `GET /cities/`

| Case | Type | Expect |
|---|---|---|
| List active cities with restaurant_count | + | 200, only `is_active=true` |
| Inactive city excluded | + | 200, not in results |
| Empty DB | + | 200, `[]` |

---

## `GET /cities/search/?q=`

| Case | Type | Expect |
|---|---|---|
| `q=Lah` matches Lahore | + | 200 |
| Exact name match | + | 200 |
| No matches | + | 200 empty + optional suggestions |
| Missing `q` | − | 400 **or** return popular (document choice; prefer popular = +) |

---

## `GET /cities/{id}/`

| Case | Type | Expect |
|---|---|---|
| Valid id returns center lat/lng | + | 200 |
| Unknown id | − | 404 |
| Inactive city | − | 404 (public) |

---

## `POST /cities/waitlist/`

| Case | Type | Expect |
|---|---|---|
| city_name + optional phone | + | 201 |
| Authenticated attaches user | + | 201, user FK set |
| Missing city_name | − | 400 |
| city_name too short (&lt;2) | − | 400 |

---

## `GET /bootstrap/`

| Case | Type | Expect |
|---|---|---|
| Returns feature flags / min versions / free_tier limit | + | 200 |
| Works without auth | + | 200 |

---

## Factories

- `CityFactory` (active Lahore-like)
- `InactiveCityFactory`
- `CityWaitlistFactory`
