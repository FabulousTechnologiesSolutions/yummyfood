# Tests: `discovery`

**Package:** `tests/discovery/`  
**Files:** `factories.py`, `test_explore_api.py`, `test_search_api.py`

---

## Explore

### `GET /explore/products/`

| Case | Type | Expect |
|---|---|---|
| Default list of products | + | 200 |
| Filter `has_deals=true` | + | only deal products |
| Filter `min_rating=4.5` | + | filtered |
| Filter `price=$$` multi | + | filtered |
| Filter `distance_km=3` with lat/lng | + | filtered |
| Combined filters | + | 200 + count |
| Zero results | + | 200 empty + optional widen |
| Paused restaurants excluded | + | not listed |
| Invalid distance_km | − | 400 |
| Invalid min_rating | − | 400 |

### `GET /explore/map/`

| Case | Type | Expect |
|---|---|---|
| Pins with lat/lng + promo flag | + | 200 |
| Bounding box / city scope | + | 200 |
| Missing location + no city | − | 400 or city-required message |

### `GET /filters/meta/`

| Case | Type | Expect |
|---|---|---|
| Returns allowed distance, price, rating values | + | 200 |
| Public no auth | + | 200 |

---

## Search

### `GET /search/?q=&tab=`

| Case | Type | Expect |
|---|---|---|
| `tab=food` finds menu item by name | + | 200 |
| `tab=restaurants` finds by name | + | 200 |
| `tab=deals` finds deal label | + | 200 |
| Urdu query `بریانی` | + | 200 match |
| Roman `biryani` | + | 200 |
| Empty q → trending | + | 200 |
| Typo → did_you_mean | + | 200 |
| Invalid tab | − | 400 |
| Paused restaurant not in results | + | excluded |

### `GET /search/trending/`

| Case | Type | Expect |
|---|---|---|
| Returns EN + Urdu chips | + | 200 |
| No auth | + | 200 |

---

## Factories

- Product/restaurant fixtures with varied price_range, rating, deals
- `SearchableBiryaniItemFactory` (EN + Urdu fields if indexed)
