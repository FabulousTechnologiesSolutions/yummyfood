# App: `engagement`

**Package:** `apps.engagement`  
**Depends on:** `accounts`, `restaurants`, `menu`, `deals`, `mediahub`  
**Purpose:** Save, Follow, Like, Report / Not interested; soft-auth gated actions.

---

## Responsibility

- Saved lists: Deals · Places · Items · Videos
- Follow restaurants (feed signal)
- Like videos
- Report / not-interested reasons for ranking
- Contact deep-link helper can live here or analytics — prefer `POST /contact/` in analytics or engagement; document both if split

---

## File layout

```
apps/engagement/
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

### `Save`

| Field | Type |
|---|---|
| `user` | FK |
| `target_type` | `deal` \| `restaurant` \| `menu_item` \| `video` |
| `deal` / `restaurant` / `menu_item` / `video` | FK nullable |
| `created_at` | DateTime |
| UniqueTogether | user + concrete target |

Saved deals sort by soonest deal/promo `ends_at`. Expired → `Expired` group in query.

### `Follow`

| Field | Type |
|---|---|
| `user` | FK |
| `restaurant` | FK |
| `created_at` | |
| UniqueTogether | (`user`, `restaurant`) |

### `Like`

| Field | Type |
|---|---|
| `user` | FK nullable |
| `session_key` | CharField nullable |
| `video` | FK |
| Unique on (user|session) + video |

### `ContentReport`

| Field | Type |
|---|---|
| `user` / `session_key` | |
| `video` | FK |
| `reason` | see enums |
| `created_at` | |

### `NotInterested`

| Field | Type |
|---|---|
| `user` / `session_key` | |
| `video` | FK nullable |
| `restaurant` | FK nullable |
| `cuisine` | CharField nullable |
| `reason` | CharField |
| `created_at` | |

### Report reasons

```text
not_interested   → Not interested in this
hide_restaurant  → Hide {Restaurant}
less_cuisine     → Less {Cuisine}
report_video     → Report this video
```

---

## API endpoints

| Method | Path | Auth |
|---|---|---|
| GET | `/api/saved/?type=deals\|places\|items\|videos` | JWT |
| POST | `/api/saved/` | JWT |
| DELETE | `/api/saved/{id}/` | JWT |
| POST | `/api/follows/` | JWT |
| DELETE | `/api/follows/{restaurant_id}/` | JWT |
| POST | `/api/videos/{id}/like/` | Optional |
| POST | `/api/reports/` | Optional |

### Save body

```json
POST /api/saved/
{
  "target_type": "deal",
  "deal_id": "deal_1"
}
```

Guest → `401 AUTH_REQUIRED` with `pending_action` echo for client soft gate.

---

## Business rules

1. Save / Follow require authenticated customer profile (always present on User).
2. After login, complete pending save automatically (accounts guest migrate).
3. Following does **not** grant console access.
4. Own-restaurant follow/save: allow or no-op; never elevate permissions.
5. Emit analytics events on save/follow/like/report (analytics app).
6. Expiry reminders for saved deals use notification settings + Celery.

---

## Tests checklist

- [ ] Save deal / unsave unique constraint
- [ ] Saved deals sorted by expiry
- [ ] Guest save returns 401 + pending_action
- [ ] Follow / unfollow
- [ ] Not interested feeds negative signal store
