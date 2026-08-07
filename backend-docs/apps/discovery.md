# App: `discovery`

**Package:** `apps.discovery`  
**Depends on:** `restaurants`, `menu`, `deals`, `mediahub`, `promotions`, `engagement`, `accounts` (prefs), `geo`  
**Purpose:** Explore tab, Map, Search, and Filters — **not** the Feed tab (see `apps.feed`).

---

## Responsibility

- Explore product cards + map pins
- Unified search (food / restaurants / deals)
- Filter meta + apply filters
- **No Deals tab** — promos still appear inline on Explore cards / search results

**Out of scope:** vertical video Feed → [`feed.md`](feed.md)

---

## File layout

```
apps/discovery/
├── __init__.py
├── apps.py
├── serializers.py
├── services/
│   ├── explore.py
│   ├── search.py
│   └── filters.py
├── urls.py
└── views.py
```

Optional model: `TrendingQuery` / `SearchLog` for server-side trending.

---

## API endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/explore/products/` | Optional | Product list |
| GET | `/api/explore/map/` | Optional | Pins + cards |
| GET | `/api/search/?q=&tab=food\|restaurants\|deals` | Optional | Search |
| GET | `/api/search/trending/` | Optional | EN + Urdu trends |
| GET | `/api/filters/meta/` | Public | Allowed filter values |

Feed lives at `GET /api/feed/` in **`apps.feed`**.

---

## Explore filters

| Param | Rules |
|---|---|
| `distance_km` | 1\|3\|5\|10 (needs lat/lng) |
| `price` | multi `$`–`$$$$` |
| `min_rating` | 3.5\|4.0\|4.5 |
| `open_now` | bool (hours deferred — see master spec) |
| `has_deals` | bool |
| `q` | optional text |
| `city_id` | fallback |

Quick chips: Promotions, Open Now, Nearby, 4.5+.

Response includes `count` for “Show {n} results”.

**Prototype Explore = products**, not restaurant-only cards.

If zero results within radius, widen `1 → 3 → 5 → 10 → 25` km and return `widened_to_km` (same ladder as feed nearby).

---

## Search

- Tabs: `food` (menu items), `restaurants`, `deals`
- Index names, descriptions, cuisines, area, captions/hashtags
- English + Urdu / Roman-Urdu (`biryani` / `بریانی`)
- Empty query → trending
- Zero results → `did_you_mean` + suggestions
- Paginate if &gt; 500 matches

---

## Map

- Pins: restaurant location; flame style if active promo
- Payload: compact product/restaurant card for carousel

---

## Business rules

1. Omit `distance_km` when no location (never `"-- km"`).
2. Exclude paused / permanently closed restaurants.
3. Prefer PostGIS `dwithin`; else Haversine (`core.utils`).
4. Shared filter helpers may be imported by `apps.feed` for Nearby if useful — keep feed ranking in `apps.feed`.

---

## Tests checklist

- [ ] Filters combine correctly
- [ ] Search Urdu + English
- [ ] Paused restaurants excluded
- [ ] Map pins include promo flag
- [ ] Explore radius widen ladder
