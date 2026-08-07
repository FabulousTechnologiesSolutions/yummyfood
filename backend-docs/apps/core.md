# Package: `core`

**Path:** `core/` (not under `apps/`, not a domain app)  
**Purpose:** Shared infrastructure — permissions, pagination, errors, auth helpers, factories, seed command.

---

## Responsibility

- Cross-app DRF permissions
- Cursor / page pagination classes
- Standard API error envelope
- Phone / distance / currency helpers
- Optional JWT helpers
- `manage.py populate` seed data
- factory_boy factories for tests

---

## File layout

```
core/
├── __init__.py
├── auth.py
├── exceptions.py
├── factories.py
├── middleware.py
├── pagination.py
├── permissions.py
├── utils.py
└── management/
    ├── __init__.py
    └── commands/
        ├── __init__.py
        └── populate.py
```

Do **not** put domain models here.

---

## API style — `ModelViewSet` + services

**Layering**

```text
ViewSet / APIView  →  services/<module>_service.py (Service class)  →  models / integrations
```

- Every domain app has a **`services/`** folder
- One **service file per module**, one **service class** per file
- All business logic lives in service methods; views only call them

Default for model CRUD: DRF **`ModelViewSet`** + router. Extra endpoints → `@action` → service method.

### Suggested ViewSet → Service map

| App | ViewSet | Service class | Extra `@action` → service methods |
|---|---|---|---|
| `geo` | `CityViewSet` | `CityService` | `search` |
| `restaurants` | `RestaurantViewSet` | `RestaurantService` / `ClaimService` | `claim`, `claim_verify`, `pause` |
| `restaurants` | `ConsoleRestaurantViewSet` | `ConsoleSettingsService` | `media`, `contact`, `address`, `promotion_defaults` |
| `menu` | `MenuCategoryViewSet` | `CategoryService` | `reorder` |
| `menu` | `MenuItemViewSet` | `MenuItemService` | `duplicate`, `move`, `hide`, `availability` |
| `menu` | `AddOnViewSet` | `AddOnService` | |
| `deals` | `DealViewSet` | `DealService` | `preview`, `similar` |
| `promotions` | `PromotionRequestViewSet` | `PromotionService` | |
| `promotions` | `AdminPromotionViewSet` | `PromotionService` | `approve`, `reject` |
| `mediahub` | `UploadSessionViewSet` | `UploadService` | `complete` |
| `engagement` | `SaveViewSet` | `SaveService` | |
| `engagement` | `FollowViewSet` | `FollowService` | |
| `accounts` | auth / profile views | `AuthService`, `ProfileService`, `PasswordService`, `PreferenceService` | `switch_to_customer`, `switch_to_restaurant` |
| `feed` | feed views | `FeedService`, `RankingService`, `NearbyService` | |
| `discovery` | explore/search views | `ExploreService`, `SearchService`, `FilterService` | |
| `analytics` | events/analytics views | `EventService`, `ContactService`, `AnalyticsService`, `ExportService` | |

Full pattern: `BACKEND-SPEC.md` §3.6–3.7.

---

## `permissions.py`

```text
IsAuthenticated
HasCustomerProfile         # user.customer_profile exists
IsRestaurantOwner          # hasattr(request.user, "restaurant")
IsRestaurantObjectOwner    # object.restaurant.owner_id == request.user.id
IsPlatformAdmin            # is_staff
AllowAny / IsAuthenticated
```

**Never** check `user.role == "restaurant"`. Use OneToOne profile ownership.

Resolve console restaurant:

1. `request.user.restaurant` only
2. If missing → 403

---

## `pagination.py`

- `CursorPagination` for Feed (stable)
- `PageNumberPagination` or cursor for Explore / Search / Saved (page size 20)
- Max page size cap (e.g. 50)

---

## `exceptions.py`

Standard envelope:

```json
{
  "error": {
    "code": "PRODUCT_QUOTA_EXCEEDED",
    "message": "You've added 5 products this month",
    "details": { "limit": 5, "used": 5, "resets_on": "2026-09-01" }
  }
}
```

Register custom exception handler in DRF settings (`base.py`).

Common codes:

| Code | HTTP |
|---|---|
| `VALIDATION_ERROR` | 400 |
| `AUTH_REQUIRED` | 401 |
| `PERMISSION_DENIED` | 403 |
| `PRODUCT_QUOTA_EXCEEDED` | 403 |
| `RESTAURANT_PROFILE_EXISTS` | 409 |
| `CUSTOMER_PROFILE_EXISTS` | 409 |
| `NOT_FOUND` | 404 |
| `CONFLICT` | 409 |
| `THROTTLED` | 429 |

---

## `utils.py`

| Helper | Purpose |
|---|---|
| `normalize_phone(raw) → E.164` | PK numbers |
| `haversine_km(lat1, lng1, lat2, lng2)` | Distance |
| `format_pkr(decimal)` | `Rs. 1,500` display (prefer client; useful in exports) |
| `widen_radius(km)` | `1→3→5→10→25` ladder |
| `parse_hashtags(caption)` | `#burger` → list |

---

## `auth.py`

- Optional phone auth backend
- Helpers to issue/blacklist SimpleJWT tokens
- Guest session key validation

---

## `middleware.py`

Optional:

- Request ID header
- Soft-deleted user rejection
- Active restaurant context attachment

---

## `factories.py`

factory_boy factories for:

- User, City, Restaurant, MenuCategory, MenuItem, Deal, Video, PromotionRequest, EngagementEvent

Used by tests and `populate`.

---

## `management/commands/populate.py`

```bash
python manage.py populate
python manage.py populate --flush
```

Seed per master spec:

- Cities (Lahore, Karachi, …)
- ≥ 12 restaurants (paused, no menu, no videos, far, long name, …)
- Menu aligned with prototype `menu-data.js`
- Deals: active / pending promo / ending soon / expired
- Videos 8–60s
- Analytics approximating 25,400 / 4,200 / 2,850 / 1,400 / 1,180 / 642 / 318
- One restaurant at **5/5** product quota
- Platform admin user

---

## Settings hooks (`conf/settings/base.py`)

```python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardPagination",
    "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
}

AUTH_USER_MODEL = "accounts.User"
```

---

## Tests checklist

- [ ] IsRestaurantObjectOwner allows owner, denies other
- [ ] User without restaurant gets 403 on console
- [ ] Second restaurant create returns 409
- [ ] Error envelope shape
- [ ] populate creates expected fixture counts
- [ ] Phone normalize for local PK formats
