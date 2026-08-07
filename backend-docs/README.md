# FoodApp Backend — App Documentation

Per-app implementation guides for Django / DRF / PostgreSQL.

**Master spec:** [`../BACKEND-SPEC.md`](../BACKEND-SPEC.md)

## Apps

| App | Path | Purpose |
|---|---|---|
| [accounts](apps/accounts.md) | `apps.accounts` | User, JWT auth, multi-profile, prefs, notifications |
| [geo](apps/geo.md) | `apps.geo` | Cities, waitlist |
| [restaurants](apps/restaurants.md) | `apps.restaurants` | Restaurant listing, claim, console settings |
| [menu](apps/menu.md) | `apps.menu` | Categories, items, sizes, add-ons |
| [deals](apps/deals.md) | `apps.deals` | Combo deals + line items |
| [promotions](apps/promotions.md) | `apps.promotions` | Boost requests + admin approve/reject |
| [mediahub](apps/mediahub.md) | `apps.mediahub` | Photos, videos, uploads |
| [feed](apps/feed.md) | `apps.feed` | **Feed tab** — For You / Nearby video ranking |
| [discovery](apps/discovery.md) | `apps.discovery` | Explore, Map, Search, Filters |
| [engagement](apps/engagement.md) | `apps.engagement` | Save, Follow, Like, Report |
| [analytics](apps/analytics.md) | `apps.analytics` | Events, rollups, console analytics, export |
| [core](apps/core.md) | `core` | Shared auth helpers, permissions, pagination, populate |

## Suggested build order

1. `core` + `accounts`  
2. `geo`  
3. `restaurants`  
4. `mediahub`  
5. `menu`  
6. `deals`  
7. `promotions`  
8. `feed`  
9. `discovery`  
10. `engagement`  
11. `analytics`  

## Tests

Positive/negative API cases per app: **[`tests/README.md`](tests/README.md)**  
Target pytest layout lives at repo root `tests/` (one folder per app).

## Implementation note

- DRF **`ModelViewSet` + routers** for model CRUD; `@action` for extras  
- Every app has a **`services/`** folder: one service file per module, one service class per file  
- Views stay thin and **only call service methods**  

See `BACKEND-SPEC.md` §3.6–3.7 and §18.3.
