# App: `feed`

**Package:** `apps.feed`  
**Depends on:** `mediahub`, `restaurants`, `deals`, `promotions`, `engagement`, `accounts` (prefs / guest session), `geo`, `analytics` (events)  
**Purpose:** Customer **Feed** tab only — vertical video discovery (`For You` / `Nearby`), ranking, and promo bars on video cards.

---

## Responsibility

- Paginated vertical video feed (TikTok-style)
- Modes: **For You** (personalized) and **Nearby** (geo)
- New-user content mix + personalization ramp
- Attach promo bar payload per video card
- Stable cursor pagination (no full reshuffle on refresh)
- Exclude paused / permanently closed restaurants
- Console “own Feed” can reuse the same read serializers; uploads stay in `mediahub` / `menu` / `deals`

**Out of scope for this app:** Explore, Map, Search, Filters → `apps.discovery`

---

## File layout

```
apps/feed/
├── __init__.py
├── apps.py
├── models.py              # optional: FeedImpression, WatchSession
├── serializers.py         # FeedCardSerializer, PromoBarSerializer
├── services/
│   ├── __init__.py
│   ├── ranking.py         # scores, buckets, signal weights
│   ├── for_you.py         # personalized playlist builder
│   ├── nearby.py          # geo filter + radius widen ladder
│   └── cursor.py          # encode/decode cursor
├── urls.py
├── views.py
└── tests/
```

---

## Optional models

Most feed state can be ephemeral (built from Video + engagement). Optional persistence:

### `WatchSession` (optional)

| Field | Type |
|---|---|
| `user` / `session_key` | |
| `video` | FK mediahub.Video |
| `watch_seconds` | Float |
| `completed` | bool |
| `created_at` | |

Useful for personalization ramp and analytics if not only writing to `analytics.EngagementEvent`.

### `FeedImpression` (optional)

| Field | Type |
|---|---|
| `user` / `session_key` | |
| `video` | FK |
| `position` | int |
| `mode` | `for_you` \| `nearby` |
| `created_at` | |

Helps avoid repeating the same videos too aggressively.

---

## API endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/feed/` | Optional | Main feed page |
| GET | `/api/feed/nearby/` | Optional | Alias or force `mode=nearby` |
| POST | `/api/feed/not-interested/` | Optional | Proxy to engagement or thin wrapper |

Primary:

```http
GET /api/feed/?mode=for_you|nearby&cursor=&lat=&lng=&city_id=
Authorization: Bearer <optional>
X-Session-Key: <guest session>
```

---

## Query parameters

| Param | Required | Values / notes |
|---|---|---|
| `mode` | no | `for_you` (default) \| `nearby` |
| `cursor` | no | opaque; omit for first page |
| `lat` / `lng` | for nearby | client GPS |
| `city_id` | fallback | use city center when GPS denied |
| `limit` | no | default 10, max 20 |

---

## Response shape

```json
{
  "next_cursor": "eyJ...",
  "mode": "for_you",
  "widened_to_km": null,
  "results": [
    {
      "video_id": "v1",
      "video_url": "https://...",
      "poster_url": "https://...",
      "duration_seconds": 28,
      "caption": "New Loaded Burger — 20% OFF This Weekend! #burger",
      "hashtags": ["burger"],
      "like_count": 1200,
      "comment_count": 48,
      "is_liked": false,
      "is_saved": false,
      "is_following_restaurant": false,
      "restaurant": {
        "id": "r_1",
        "name": "Burger House",
        "logo_url": "https://...",
        "is_promoted": true
      },
      "menu_item_id": "mi_1",
      "deal_id": "deal_1",
      "promo_bar": {
        "deal_id": "deal_1",
        "title": "Weekend Pizza Deal",
        "old_price": "1500.00",
        "new_price": "999.00",
        "discount_percent": 33,
        "ends_in_seconds": 187200,
        "state": "active"
      }
    }
  ]
}
```

### `promo_bar.state`

`active` · `expiring_soon` (&lt;48h) · `expiring_critical` (&lt;2h) · `expired` · `scheduled` · `null` (no promo)

If multiple live promos on one video: show best-value bar + optional `more_count`.

---

## Ranking & personalization

### New-user mix (cold start)

| Share | Bucket |
|---|---|
| 40% | Featured / Promoted (`PromotionRequest.status=live`) |
| 30% | Trending (view velocity) |
| 20% | New videos |
| 10% | Exploration / diversity |

### Personalization ramp

| Videos watched | Strength |
|---|---|
| 1–2 | 10–20% |
| 3–5 | 30–40% |
| 5–10 | 50–60% |
| 15+ | 70–80% |

Blend explicit prefs (`UserPreference.cuisines`, price, distance) with behaviour; behaviour wins over time.

### Signal weights (high → low)

1. promo click  
2. menu view  
3. restaurant profile visit  
4. save  
5. share  
6. completion (~95% watch)  
7. watch duration  
8. like  

**Minimum watch** before a positive signal counts: **3 seconds**.

### Negative signals

- `not_interested` / hide restaurant / less cuisine (`engagement` app)
- Rapid skip (&lt; 2s) = weak negative
- Repeated skips of one cuisine = strong negative

### Refresh contract

- Pull-to-refresh **prepends** new items
- Preserve already-seen tail — **do not** fully reshuffle
- Cursor must remain stable under concurrent inserts

---

## Nearby mode

1. Filter videos by restaurant distance from `lat/lng` (or city center)
2. Default radius: **5 km** (`AppConfig.feed_nearby_default_km`)
3. If empty, auto-widen: `1 → 3 → 5 → 10 → 25` km
4. Response field `widened_to_km` + client shows banner
5. If still empty → national trending fallback (never blank feed)

Omit `distance_km` on cards when location unknown (never `"-- km"`).

---

## Eligibility rules

Include video only if:

- `Video.status == ready`
- Restaurant not `is_paused` and not `is_permanently_closed`
- Attached to menu item and/or deal and/or restaurant (actionable video)
- For promoted bucket: linked `PromotionRequest.status == live` and within radius/window when applicable

---

## Client events (handled by `analytics`, fired from Feed UI)

Feed should document expected client calls:

| Event | When |
|---|---|
| `video_view` | ≥ 3s watch |
| `video_complete` | ~95% |
| `video_skip` | &lt; 2s |
| `like` / `share` / `promo_click` | user action |
| `not_interested` | long-press sheet |

Use `POST /api/events/` (`apps.analytics`).

---

## Business rules

1. Feed is always the launch tab; no auth wall.
2. Opening Promo Sheet must not require pausing video (client); feed API just supplies `promo_bar`.
3. Guest personalization via `session_key` + `GuestSession`.
4. Restaurant console Feed tab = same card shape + FAB to add product (write path elsewhere).
5. Prefer PostGIS `dwithin` for nearby; else Haversine in `core.utils`.

---

## URL wiring

`conf/urls.py`:

```python
path("api/", include("apps.feed.urls")),
```

`INSTALLED_APPS`: `"apps.feed"`

---

## Tests checklist

- [ ] For You returns cursor + cards with restaurant
- [ ] Nearby respects radius and widen ladder
- [ ] Paused restaurants excluded
- [ ] Promoted bucket ~40% for cold session
- [ ] Refresh prepends without reshuffling seen IDs
- [ ] Guest session personalization without JWT
- [ ] Promo bar states for expiring / expired deals
- [ ] Empty city falls back to national trending (non-empty)
