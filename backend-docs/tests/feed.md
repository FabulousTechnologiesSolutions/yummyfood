# Tests: `feed`

**Package:** `tests/feed/`  
**Files:** `factories.py`, `test_feed_api.py`

Base: `/api/feed/`

---

## `GET /feed/?mode=for_you`

| Case | Type | Expect |
|---|---|---|
| Returns cards with video + restaurant | + | 200, non-empty when fixtures exist |
| Guest (no auth) works | + | 200 |
| Authenticated includes is_liked / is_saved / is_following | + | 200 flags correct |
| Promo bar present for live promo video | + | `promo_bar` object |
| Cursor pagination next page | + | `next_cursor`, no duplicate ids vs page1 |
| Refresh/cursor stability (prepend contract) | + | unit/service test |
| Cold user mix includes promoted videos | + | ≥1 promoted when available |
| Paused restaurant videos excluded | + | not in results |
| Processing videos excluded | + | not in results |
| Invalid mode | − | 400 |
| Corrupt cursor | − | 400 |

---

## `GET /feed/?mode=nearby` / `GET /feed/nearby/`

| Case | Type | Expect |
|---|---|---|
| With lat/lng within 5 km returns local | + | 200 |
| Empty at 5 km → widen + `widened_to_km` | + | 200 |
| city_id fallback without GPS | + | 200 |
| No lat/lng and no city_id | − | 400 **or** national fallback (+) — prefer fallback |
| Totally empty universe → trending national | + | 200 non-empty if national fixtures exist |

---

## `POST /feed/not-interested/` (if exposed)

| Case | Type | Expect |
|---|---|---|
| Valid video_id reduces future ranking | + | 200/204 |
| Missing video_id | − | 400 |
| Unknown video | − | 404 |

---

## Ranking service unit tests (optional file `test_ranking.py`)

| Case | Type | Expect |
|---|---|---|
| Weights order promo_click &gt; like | + | score order |
| Watch &lt; 3s ignored | + | no positive signal |
| Negative not_interested applied | + | lower score |

---

## Factories

- Reuse `VideoFactory`, `RestaurantFactory`, `LivePromotionFactory`
- `NearbyRestaurantFactory` (set lat/lng near test point)
- `FarRestaurantFactory`
- `PausedRestaurantFactory`
