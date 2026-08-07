# FoodApp — Backend Development Specification

**Stack:** Django · Django REST Framework (DRF) · PostgreSQL · JWT  
**Version:** 1.0 · **Date:** 2026-08-03  
**Source of truth:** HTML prototype (`prototype/`) over `UI-PLAN.md` where they diverge  
**Phase:** 1 — discovery & promotion only (**no cart, checkout, payments, delivery, or orders**)

This document is complete enough for a backend developer to implement the API and database without re-analyzing the frontend.

---

## Table of contents

1. [Project overview & application flow](#1-project-overview--application-flow)
2. [Scope boundaries](#2-scope-boundaries)
3. [Recommended Django project structure](#3-recommended-django-project-structure)  
   - §3.6 **ModelViewSet + services** · §3.7 service map
4. [Multi-profile system & permissions](#4-multi-profile-system--permissions)
5. [Database models & relationships](#5-database-models--relationships)
6. [Enums & constants](#6-enums--constants)
7. [Authentication & authorization (JWT)](#7-authentication--authorization-jwt)
8. [REST API catalogue](#8-rest-api-catalogue)
9. [Request/response examples & validation](#9-requestresponse-examples--validation)
10. [Business logic & workflows](#10-business-logic--workflows)
11. [File upload & media handling](#11-file-upload--media-handling)
12. [Pagination, filtering, searching & sorting](#12-pagination-filtering-searching--sorting)
13. [Analytics & event tracking](#13-analytics--event-tracking)
14. [Notifications](#14-notifications)
15. [Third-party integrations](#15-third-party-integrations)
16. [Feed ranking & personalization](#16-feed-ranking--personalization)
17. [Error handling & edge cases](#17-error-handling--edge-cases)
18. [Environment, security & best practices](#18-environment-security--best-practices)
19. [Seed data & fixtures](#19-seed-data--fixtures)
20. [Out of scope / deferred](#20-out-of-scope--deferred)

---

## 1. Project overview & application flow

### 1.1 Product one-liner

**Discover food through video → find the restaurant → see the promotion → Call / WhatsApp / visit.**

The transaction never happens in the app. The north-star metric is a **contact event**: `call_click`, `whatsapp_click`, or `directions_click`.

### 1.2 Two surfaces

| Surface | Who | Entry |
|---|---|---|
| **Customer App** | Every registered user (and guests) | 4 tabs: Feed · Explore · Saved · Profile |
| **Restaurant Console** | Same user, when they own a restaurant | Profile → **Switch to Restaurant** (never a 5th customer tab) |

**One account, multiple profiles.** A restaurant owner is still a full customer of other restaurants. Switching modes is UX only — not a different login.

Console bottom nav (prototype): **Dashboard · Menu · Feed · Deals · Analytics**

### 1.3 Customer golden path

```
WATCH VIDEO → SEE DEAL / PROMO → OPEN RESTAURANT → VIEW MENU
  → SAVE DEAL → CALL / WHATSAPP / DIRECTIONS → VISIT
```

Max depth to contact: **3 taps from Feed**.

### 1.4 First-run (guest)

1. Splash (prefetch feed)
2. Location primer → Allow GPS | Choose city | Skip (national feed)
3. City picker (if city path)
4. Feed — **no signup wall**, no cuisine questionnaire

### 1.5 Restaurant journey

```
SIGN UP (name + phone + password)
  → DASHBOARD CHECKLIST (profile, logo/cover, contact, address, menu)
  → ADD PRODUCTS (photo + video required)
  → BUILD DEALS
  → REQUEST PROMOTION (admin approval)
  → CUSTOMERS DISCOVER → ANALYTICS
```

### 1.6 Conceptual split (critical)

| Concept | Meaning |
|---|---|
| **Menu item / Deal on menu** | Customer-visible content; publishes **immediately** |
| **Promotion / Promoted** | Admin-approved **boosted placement** in Feed & Explore |

Item/deal can exist on the menu while its promotion request is still `pending`.

---

## 2. Scope boundaries

### In Phase 1

- Video feed discovery (For You / Nearby)
- Explore products + map + search + filters
- Restaurant profile, read-only menu, item detail
- Deals / combos with media
- Save: deals, places (restaurants), items, videos
- Follow restaurant
- Call / WhatsApp / Directions + analytics
- Restaurant console: menu CRUD, deals, promotion requests, analytics
- Auth: phone + password; **multi-profile** (customer + optional restaurant owner on one account)
- Platform admin: approve/reject promotion requests
- Guest browsing; soft gate on Save / Follow / Console

### Explicitly NOT in Phase 1

- Cart, checkout, payments, orders, delivery
- Packages / billing / boost paid campaigns (Free/Silver/Gold/Premium UI deferred)
- Team members management
- Opening hours CRUD (prototype dropped collection; compute open/closed only if added later)
- In-app review writing (ratings displayed; source TBD)
- Google / Apple Sign-In (plan only; prototype uses phone + password)

---

## 3. Recommended Django project structure

Follow this layout (same pattern as your reference: `conf` + `apps` + `core`). Replace sample apps (`books` / `reviews`) with FoodApp domain apps.

```
foodapp/
├── conf/
│   ├── settings/
│   │   ├── __init__.py          # loads env → development|production|testing
│   │   ├── base.py              # shared: INSTALLED_APPS, DRF, JWT, AUTH_USER_MODEL
│   │   ├── development.py
│   │   ├── production.py
│   │   └── testing.py
│   ├── __init__.py
│   ├── asgi.py
│   ├── urls.py                  # include apps.*.urls under /api/
│   ├── wsgi.py
│   └── celery.py                # optional: digests, expiry, analytics rollups
├── apps/
│   ├── __init__.py
│   ├── accounts/
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── views.py                 # thin: ModelViewSet / APIView → call services
│   │   ├── permissions.py
│   │   ├── signals.py
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── auth_service.py      # AuthService
│   │       ├── profile_service.py   # ProfileService (switch mode, get-or-create)
│   │       ├── password_service.py  # PasswordService (OTP reset)
│   │       └── preference_service.py
│   ├── geo/
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── city_service.py
│   │       └── waitlist_service.py
│   ├── restaurants/
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   ├── signals.py
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── restaurant_service.py
│   │       ├── claim_service.py
│   │       └── console_settings_service.py
│   ├── menu/
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── category_service.py
│   │       ├── menu_item_service.py
│   │       └── addon_service.py
│   ├── deals/
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   └── services/
│   │       ├── __init__.py
│   │       └── deal_service.py
│   ├── promotions/
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   └── services/
│   │       ├── __init__.py
│   │       └── promotion_service.py
│   ├── mediahub/
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── upload_service.py
│   │       ├── photo_service.py
│   │       └── video_service.py
│   ├── feed/
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── feed_service.py
│   │       ├── ranking_service.py
│   │       └── nearby_service.py
│   ├── discovery/
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── explore_service.py
│   │       ├── search_service.py
│   │       └── filter_service.py
│   ├── engagement/
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── save_service.py
│   │       ├── follow_service.py
│   │       ├── like_service.py
│   │       └── report_service.py
│   └── analytics/
│       ├── __init__.py
│       ├── admin.py
│       ├── apps.py
│       ├── models.py
│       ├── serializers.py
│       ├── urls.py
│       ├── views.py
│       ├── tasks.py
│       └── services/
│           ├── __init__.py
│           ├── event_service.py
│           ├── contact_service.py
│           ├── analytics_service.py
│           └── export_service.py
├── core/                        # shared cross-app utilities (not a domain app)
│   ├── __init__.py
│   ├── auth.py                  # JWT helpers, optional custom auth backend
│   ├── exceptions.py            # API error envelope
│   ├── factories.py             # factory_boy fixtures (tests / populate)
│   ├── middleware.py
│   ├── pagination.py            # cursor + page pagination
│   ├── permissions.py           # IsRestaurantOwner, IsRestaurantObjectOwner
│   ├── utils.py                 # phone E.164, distance, currency
│   └── management/
│       ├── __init__.py
│       └── commands/
│           ├── __init__.py
│           └── populate.py      # seed cities, restaurants, menu, analytics
├── media/                       # local uploads (dev only; gitignored)
├── tests/                       # pytest suite — one package per app (see §3.5)
│   ├── __init__.py
│   ├── conftest.py              # api_client, auth helpers, shared fixtures
│   ├── accounts/
│   ├── geo/
│   ├── restaurants/
│   ├── menu/
│   ├── deals/
│   ├── promotions/
│   ├── mediahub/
│   ├── feed/
│   ├── discovery/
│   ├── engagement/
│   └── analytics/
├── docker-compose.yml           # web, db (PostGIS), redis, worker
├── Dockerfile
├── requirements.txt
├── pytest.ini                   # or pyproject.toml [tool.pytest]
├── .env
├── .env.example
├── .gitignore
├── manage.py
└── README.md
```

### 3.1 Settings wiring

`conf/settings/__init__.py` selects module from `DJANGO_ENV` / `ENVIRONMENT`:

| Value | Module |
|---|---|
| `development` (default) | `conf.settings.development` |
| `production` | `conf.settings.production` |
| `testing` | `conf.settings.testing` |

`manage.py` / `wsgi.py` / `asgi.py`:

```python
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "conf.settings")
```

`INSTALLED_APPS` (domain apps as):

```python
"apps.accounts",
"apps.geo",
"apps.restaurants",
"apps.menu",
"apps.deals",
"apps.promotions",
"apps.mediahub",
"apps.feed",
"apps.discovery",
"apps.engagement",
"apps.analytics",
```

`AUTH_USER_MODEL = "accounts.User"` (label from `apps.accounts`).

### 3.2 URL layout

`conf/urls.py`:

```python
urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/", include("apps.geo.urls")),
    path("api/", include("apps.restaurants.urls")),
    path("api/", include("apps.menu.urls")),
    path("api/", include("apps.deals.urls")),
    path("api/", include("apps.promotions.urls")),
    path("api/", include("apps.mediahub.urls")),
    path("api/", include("apps.feed.urls")),
    path("api/", include("apps.discovery.urls")),
    path("api/", include("apps.engagement.urls")),
    path("api/", include("apps.analytics.urls")),
]
```
### 3.3 Packages to use

| Concern | Package |
|---|---|
| API | `djangorestframework` |
| JWT | `djangorestframework-simplejwt` |
| Filtering | `django-filter` |
| CORS | `django-cors-headers` |
| Env | `python-dotenv` or `django-environ` |
| Media (prod) | `django-storages` + S3/R2-compatible |
| Images | Pillow; optional `django-imagekit` |
| Geo | `django.contrib.gis` + PostGIS **or** Haversine |
| Phone | `phonenumber_field` (or normalize E.164 yourself) |
| Admin | Django Admin for platform ops |
| Async | Celery + Redis (notifications, rollups, digests) |
| Tests / seed | `factory_boy`, `pytest-django` |

### 3.4 Docker (suggested services)

`docker-compose.yml`: `web` (Django), `db` (PostgreSQL / PostGIS), `redis`, `worker` (Celery). Mount `.env`; never commit secrets.

### 3.5 Tests layout (pytest)

Mirror each domain app under a top-level `tests/` package (same pattern as your reference project). **Every API** gets positive and negative cases.

```
tests/
├── __init__.py
├── conftest.py
├── accounts/
│   ├── __init__.py
│   ├── factories.py
│   ├── test_auth_api.py
│   ├── test_profile_api.py
│   ├── test_preferences_api.py
│   └── test_password_api.py
├── geo/
│   ├── __init__.py
│   ├── factories.py
│   └── test_cities_api.py
├── restaurants/
│   ├── __init__.py
│   ├── factories.py
│   ├── test_public_api.py
│   ├── test_console_api.py
│   └── test_claim_api.py
├── menu/
│   ├── __init__.py
│   ├── factories.py
│   ├── test_public_menu_api.py
│   └── test_console_menu_api.py
├── deals/
│   ├── __init__.py
│   ├── factories.py
│   ├── test_public_deals_api.py
│   └── test_console_deals_api.py
├── promotions/
│   ├── __init__.py
│   ├── factories.py
│   ├── test_console_promotions_api.py
│   └── test_admin_promotions_api.py
├── mediahub/
│   ├── __init__.py
│   ├── factories.py
│   └── test_uploads_api.py
├── feed/
│   ├── __init__.py
│   ├── factories.py
│   └── test_feed_api.py
├── discovery/
│   ├── __init__.py
│   ├── factories.py
│   ├── test_explore_api.py
│   └── test_search_api.py
├── engagement/
│   ├── __init__.py
│   ├── factories.py
│   ├── test_saved_api.py
│   ├── test_follow_api.py
│   └── test_report_api.py
└── analytics/
    ├── __init__.py
    ├── factories.py
    ├── test_events_api.py
    └── test_console_analytics_api.py
```

**Conventions**

| Rule | Detail |
|---|---|
| Runner | `pytest` + `pytest-django` |
| Settings | `DJANGO_SETTINGS_MODULE=conf.settings` with `ENVIRONMENT=testing` |
| Client | `APIClient` fixture in `conftest.py` |
| Auth | helpers: `auth_client(user)`, `owner_client(restaurant)` |
| Factories | `factory_boy` per app (`factories.py`) |
| Naming | `test_<area>_api.py`; methods `test_<action>_success` / `test_<action>_<failure_reason>` |
| Coverage | Every endpoint: ≥1 positive + ≥1 negative (auth, validation, permission, 404) |

Full case lists: [`backend-docs/tests/`](backend-docs/tests/README.md).

### 3.6 API implementation standard — `ModelViewSet` + services

**Default pattern:** DRF `ModelViewSet` / `APIView` (thin) → **service class method** → models / external APIs.

Views must **not** contain business logic. They validate input (serializers), call a service, and return the response.

#### Services folder (every app)

```
apps/<app>/services/
├── __init__.py
├── <module>_service.py    # one file per module
└── ...
```

| Rule | Detail |
|---|---|
| One file per module | e.g. `auth_service.py`, `menu_item_service.py`, `deal_service.py` |
| One service class per file | e.g. `class AuthService:`, `class MenuItemService:` |
| Methods = use cases | `register`, `login`, `switch_to_customer`, `duplicate`, `approve`, … |
| ViewSets only call services | `MenuItemService().duplicate(item=..., user=...)` |
| Reusable | Same service callable from ViewSet, management command, Celery task, tests |

**Example service:**

```python
# apps/menu/services/menu_item_service.py
class MenuItemService:
    def create(self, *, restaurant, validated_data, photo_ids, video_id, request_promotion=False):
        # quota check, create item, sizes, attach media, optional promo request
        ...

    def duplicate(self, *, menu_item, user):
        ...

    def hide(self, *, menu_item, user):
        ...

    def set_availability(self, *, menu_item, is_available, user):
        ...
```

**Example ViewSet (thin):**

```python
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.menu.services.menu_item_service import MenuItemService

class MenuItemViewSet(viewsets.ModelViewSet):
    serializer_class = MenuItemSerializer
    permission_classes = [...]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = MenuItemService()

    def get_queryset(self):
        return self.service.get_queryset_for_user(self.request.user)

    def perform_create(self, serializer):
        self.service.create(
            restaurant=self.request.user.restaurant,
            validated_data=serializer.validated_data,
            photo_ids=self.request.data.get("photo_ids", []),
            video_id=self.request.data.get("video_id"),
            request_promotion=self.request.data.get("request_promotion", False),
        )

    @action(detail=True, methods=["post"])
    def duplicate(self, request, pk=None):
        item = self.service.duplicate(menu_item=self.get_object(), user=request.user)
        return Response(MenuItemSerializer(item).data)
```

Built-in ViewSet actions still apply (`list`, `create`, `retrieve`, `update`, `partial_update`, `destroy`); each delegates to the service.

**Router wiring** (per app `urls.py`):

```python
from rest_framework.routers import DefaultRouter
from .views import MenuItemViewSet, MenuCategoryViewSet

router = DefaultRouter()
router.register("console/menu-items", MenuItemViewSet, basename="console-menu-items")
router.register("console/categories", MenuCategoryViewSet, basename="console-categories")

urlpatterns = router.urls
```

**When not to use `ModelViewSet`**

| Endpoint type | Prefer |
|---|---|
| Auth login / register / refresh / logout | `APIView` → `AuthService` |
| Feed playlist / search ranking | `APIView` / non-model `ViewSet` → `FeedService` / `SearchService` |
| Analytics aggregates / export | `APIView` → `AnalyticsService` |
| Contact deep-link | `APIView` → `ContactService` |
| Password reset | `APIView` → `PasswordService` |

**Read vs write serializers:** `get_serializer_class()` by `self.action`.  
**Permissions:** on the ViewSet; services may raise domain errors (`PermissionDenied`, custom exceptions).  
**Querysets:** prefer `Service.get_queryset_for_user(...)` used from `get_queryset()`.

### 3.7 Suggested service map (by app)

| App | Service files (classes) |
|---|---|
| `accounts` | `AuthService`, `ProfileService`, `PasswordService`, `PreferenceService` |
| `geo` | `CityService`, `WaitlistService` |
| `restaurants` | `RestaurantService`, `ClaimService`, `ConsoleSettingsService` |
| `menu` | `CategoryService`, `MenuItemService`, `AddOnService` |
| `deals` | `DealService` |
| `promotions` | `PromotionService` |
| `mediahub` | `UploadService`, `PhotoService`, `VideoService` |
| `feed` | `FeedService`, `RankingService`, `NearbyService` |
| `discovery` | `ExploreService`, `SearchService`, `FilterService` |
| `engagement` | `SaveService`, `FollowService`, `LikeService`, `ReportService` |
| `analytics` | `EventService`, `ContactService`, `AnalyticsService`, `ExportService` |

See also §18.3 and [`backend-docs/apps/core.md`](backend-docs/apps/core.md).
---

## 4. Multi-profile system & permissions

### 4.1 Core rule — multi-profile (max one of each)

**One User = one phone login.** A user may have Customer and/or Restaurant profiles, with hard caps:

```text
User
├── Customer Profile   (0..1)
└── Restaurant Profile (0..1)   ← at most ONE restaurant; never multiple
```

| Rule | Allowed |
|---|---|
| Customer only | ✅ |
| Restaurant only | ✅ |
| Customer + Restaurant | ✅ |
| Two or more restaurants on one user | ❌ **Not allowed** |

| Profile | Cardinality | Capabilities |
|---|---|---|
| **Guest** | (no account) | Browse feed, explore, search, menus, profiles; Call / WhatsApp / Directions |
| **Customer profile** | 0..1 | Save, follow, customer prefs, customer notifications, Saved tab |
| **Restaurant profile** | 0..1 | Console for **that one** restaurant (menu, deals, analytics, promotion requests) |
| **Platform admin** | flag on User | Approve/reject promotions; moderate reports; cities; quota overrides |

```
┌─────────────────────────────────────────────┐
│  User (phone + password)                    │
│  ├── CustomerProfile   (0..1)               │
│  ├── Restaurant        (0..1, OneToOne)     │
│  └── is_staff admin    (optional)           │
└─────────────────────────────────────────────┘
         │                      │
         ▼                      ▼
   Customer App mode      Restaurant Console mode
```

**Examples:** User A = Customer only ✅ · User B = Restaurant only ✅ · User C = both ✅ · User D = Restaurant 1 + Restaurant 2 ❌

Signup UI “Customer | Restaurant” controls which profile is created on day one:

| Signup path | Result |
|---|---|
| Customer | Create `CustomerProfile` only. Later may add **one** Restaurant via create/claim |
| Restaurant | Create `Restaurant` shell (restaurant profile). May add `CustomerProfile` later if missing |
| User already has a Restaurant | Further create/claim → **409** `RESTAURANT_PROFILE_EXISTS` |

**Switch to Restaurant** (C-16): client mode switch when the user has a restaurant profile. Same JWT. No multi-restaurant context header.

### 4.2 Permission rules

- Guests: public reads + `POST /events/` (with `session_key`)
- Save / Follow: authenticated user **with** a `CustomerProfile` (or auto-create customer profile on first save — product choice; default: require customer profile)
- Console APIs: authenticated user with OneToOne `user.restaurant`
- Restaurant writes: `request.user.restaurant_id == object.restaurant_id` (via `owner` OneToOne)
- **Never** allow a second restaurant for the same user
- Platform admin: `IsAdminUser`
- Paused / permanently closed restaurants: hidden from **customer discovery**; owner still uses console
- Own-restaurant follow/save: allow or no-op; never grant console rights via follow

### 4.3 Soft auth gate triggers (client)

Save · Follow · Enter console · Create/claim restaurant (**only if user has no restaurant yet**)

On auth success: complete **pending intent** and **migrate guest session**.

---

## 5. Database models & relationships

### 5.1 ER overview

```
User 0..1──1 CustomerProfile          ← Customer profile (optional)
User 0..1──1 Restaurant (owner)       ← Restaurant profile; OneToOne ONLY (never 2+)
CustomerProfile 1──1 UserPreference
CustomerProfile 1──1 NotificationSetting
User *──* Save ──> Deal | Restaurant | MenuItem | Video   ← requires CustomerProfile
User *──* Follow ──> Restaurant       ← requires CustomerProfile; not ownership
User *──* Like ──> Video
User *──* Report / NotInterested

City 1──* Restaurant
Restaurant 1──* MenuCategory 1──* MenuItem
MenuItem *──* MenuCategory (M2M cross-list via `also`)
MenuItem 1──* MenuItemSize
MenuItem 1──* MenuItemPhoto
MenuItem 0..1 Video (required to publish)
MenuItem 0..* PromotionRequest
MenuItem *──* AddOn (via category applicability)

Restaurant 1──* Deal
Deal *──* DealLine (MenuItem + size_label + unit_price)
Deal 1──* DealPhoto
Deal 0..1 Video (required to publish)
Deal 0..* PromotionRequest

Restaurant 1──* Video (also linked via item/deal)
Restaurant 1──* ContactEvent / EngagementEvent
Restaurant 1──* AnalyticsDaily

PromotionRequest ── reviewed_by (User admin, nullable)
```

### 5.2 `accounts.User`

Extend `AbstractBaseUser` or `AbstractUser`. **Phone is the login identity** (no email required in prototype).

**Do not store an exclusive `role`.** Profiles are separate OneToOne rows; admin is `is_staff`.

| Field | Type | Constraints |
|---|---|---|
| `id` | UUID / BigAuto | PK |
| `phone_number` | CharField(20) | unique, E.164 preferred e.g. `+923008452119` |
| `password` | hashed | min length 8 |
| `display_name` | CharField(120) | customer-facing name (e.g. Ahmad Sarwar) |
| `avatar` | ImageField | optional; else monogram initials |
| `is_active` | bool | default True |
| `is_staff` | bool | platform admin |
| `is_superuser` | bool | optional |
| `signup_intent` | CharField | audit only: `customer` \| `restaurant` |
| `date_joined` | DateTime | |
| `last_login` | DateTime | |
| `deleted_at` | DateTime | nullable; 30-day soft delete window |

**USERNAME_FIELD** = `phone_number`  
**Removed:** `last_active_restaurant` (only one restaurant possible).

**Derived helpers:**

```python
@property
def has_customer_profile(self) -> bool:
    return hasattr(self, "customer_profile") and self.customer_profile is not None

@property
def has_restaurant_profile(self) -> bool:
    return hasattr(self, "restaurant") and self.restaurant is not None

@property
def is_restaurant_owner(self) -> bool:
    return self.has_restaurant_profile and not self.restaurant.is_permanently_closed
```

### 5.2b `accounts.CustomerProfile`

OneToOne → User (`related_name="customer_profile"`). **At most one per user.**

| Field | Type | Notes |
|---|---|---|
| `user` | OneToOneField(User) | unique |
| `created_at` | DateTime | |

Presence of this row = user has a Customer profile. Prefs/notifications hang off this model (preferred) or User.

### 5.3 `accounts.UserPreference`

OneToOne → **CustomerProfile** (preferred) or User

| Field | Type | Notes |
|---|---|---|
| `cuisines` | ArrayField / M2M | Burgers, BBQ, Pakistani, Pizza, Chinese, Desserts, Cafés, Drinks |
| `price_ranges` | ArrayField | `$` `$$` `$$$` `$$$$` (multi) |
| `max_distance_km` | PositiveSmallInteger | 1–25, default 5 |
| `city` | FK City | nullable |
| `language` | CharField | `en` \| `ur`, default `en` |
| `theme` | CharField | `system` \| `light` \| `dark` |

### 5.4 `accounts.NotificationSetting`

OneToOne → **CustomerProfile** (preferred) or User

| Field | Type | Default |
|---|---|---|
| `expiry_reminders` | bool | True (24h before saved deal ends) |
| `new_deals_from_saved` | bool | True |
| `nearby_flash_deals` | bool | False (under 2 km, ending within 6 h) |
| `new_videos_from_followed` | bool | True |
| `weekly_digest` | bool | False (Sundays 6 PM) |
| `security_alerts` | bool | True (**always on**; ignore client off) |

### 5.5 `accounts.GuestSession` (optional but recommended)

| Field | Type |
|---|---|
| `session_key` | CharField unique |
| `watch_history` | JSON |
| `search_history` | JSON |
| `pending_save` | JSON nullable |
| `device_info` | JSON |
| `merged_into_user` | FK User nullable |
| `created_at` / `updated_at` | |

On register/login: merge into user (union, no overwrite of existing saves).

### 5.6 `geo.City`

| Field | Type |
|---|---|
| `name` | CharField unique-per-country |
| `slug` | SlugField |
| `region` / `province` | CharField |
| `country_code` | CharField default `PK` |
| `center_lat` / `center_lng` | Decimal |
| `is_active` | bool |
| `restaurant_count` | cached PositiveInteger |
| `sort_order` | int |

Seed examples: Lahore, Karachi, Islamabad, Faisalabad, Multan.

### 5.7 `geo.CityWaitlist`

| Field | Type |
|---|---|
| `city_name` | CharField (free text e.g. Sialkot) |
| `phone_number` | CharField optional |
| `user` | FK nullable |
| `created_at` | |

### 5.8 `restaurants.Restaurant`

| Field | Type | Notes |
|---|---|---|
| `owner` | **OneToOneField(User)** | `related_name="restaurant"`; **unique** — at most one restaurant per user |
| `name` | CharField(120) | required at signup |
| `slug` | SlugField | unique |
| `short_description` | TextField | blank |
| `cuisines` | ArrayField / M2M | **max 3** |
| `price_range` | CharField | `$` \| `$$` \| `$$$` \| `$$$$` |
| `logo` | ImageField | 1:1 preferred; blank → monogram |
| `cover` | ImageField | 16:9 preferred |
| `primary_phone` | CharField | required for listing completeness |
| `whatsapp_number` | CharField | blank; may equal primary |
| `use_different_whatsapp` | bool | default False |
| `secondary_phone` | CharField | blank |
| `street_address` | CharField | |
| `area` | CharField | e.g. Gulberg III |
| `city` | FK City | |
| `lat` / `lng` | Decimal(9,6) | **map pin; independent of typed address** |
| `rating_avg` | Decimal(2,1) | display only Phase 1 |
| `rating_count` | PositiveInteger | |
| `rating_histogram` | JSON | `{1:4,2:4,3:12,4:44,5:248}` |
| `is_paused` | bool | “Pause listing” |
| `is_permanently_closed` | bool | |
| `claim_status` | CharField | `owned` \| `unclaimed` \| `pending_claim` |
| `setup_checklist` | JSON | see §10.2 |
| `promo_default_radius_km` | PositiveSmallInteger | 1\|3\|5\|10 default 5 |
| `promo_default_duration_days` | PositiveSmallInteger | 1\|3\|7\|14 default 3 |
| `notify_on_promo_approval` | bool | True |
| `auto_request_promo_on_deal` | bool | False |
| `products_created_this_month` | PositiveInteger | free-tier counter |
| `products_quota_month` | DateField | month key for reset |
| `created_at` / `updated_at` | |

**Computed (not stored, or cached):** `distance_km`, `is_open_now` (if hours added later), `active_deal_count`, `profile_completeness_pct`.

### 5.9 `menu.MenuCategory`

| Field | Type |
|---|---|
| `restaurant` | FK Restaurant |
| `slug` | CharField | e.g. `fastfood`, `pakistani` |
| `name` | CharField |
| `icon` | CharField | emoji or icon key |
| `position` | PositiveInteger | drag order |
| `is_visible` | bool | “visible to customers” |
| UniqueTogether | (`restaurant`, `slug`) |

**System category seeds** (per restaurant on create, or global templates):

`fastfood`, `pakistani`, `continental`, `chinese`, `bbq`, `pizza`, `burgers`, `wraps`, `pasta`, `rice`, `salads`, `soups`, `beverages`, `desserts`, `kids`, `deals`, `addons`

### 5.10 `menu.MenuItem`

| Field | Type | Notes |
|---|---|---|
| `restaurant` | FK | |
| `category` | FK MenuCategory | primary |
| `cross_categories` | M2M MenuCategory | `also` |
| `name` | CharField | PRODUCT NAME * |
| `description` | TextField | |
| `subcategory` | CharField | optional e.g. Soft Drinks, Shakes |
| `item_type` | CharField | Chicken/Beef/Mutton/Fish/Veg/Vegetarian/Egg/Mixed |
| `quantity_label` | CharField | serving hint |
| `sku` | CharField | e.g. `FA-001`; auto-generate |
| `is_available` | bool | In stock / Out of stock |
| `is_popular` | bool | Popular badge |
| `is_new` | bool | carried in data; optional render |
| `spicy_level` | 0–3 | optional |
| `prep_time_min` | PositiveSmallInteger | optional |
| `calories` | PositiveInteger | legacy; not rendered |
| `emoji` | CharField | prototype subject glyph |
| `base_price` | Decimal | if single size; else min of sizes |
| `status` | CharField | `draft` \| `published` \| `hidden` |
| `published_at` | DateTime | |
| `created_at` / `updated_at` | |

### 5.11 `menu.MenuItemSize`

| Field | Type |
|---|---|
| `menu_item` | FK |
| `label` | CharField | Regular, Large, Half, Full, … |
| `price` | Decimal(10,2) | PKR * required |
| `offer_price` | Decimal(10,2) | nullable; must be &lt; price if set |
| `position` | PositiveSmallInteger | |

### 5.12 `menu.AddOn`

| Field | Type |
|---|---|
| `restaurant` | FK |
| `name` | CharField |
| `price` | Decimal |
| `item_type` | CharField | Vegetarian / Chicken / Beef / … |
| `applies_to_categories` | M2M | or `applies_to_all` bool |
| `is_available` | bool | |

### 5.13 `deals.Deal`

| Field | Type | Notes |
|---|---|---|
| `restaurant` | FK | |
| `label` | CharField | DEAL LABEL * |
| `description` | TextField | |
| `deal_price` | Decimal | DEAL PRICE * |
| `items_total` | Decimal | derived sum of line unit prices |
| `savings_amount` | Decimal | derived |
| `savings_percent` | Decimal | derived |
| `starts_at` | DateTime | RUNS |
| `ends_at` | DateTime | |
| `days_of_week` | ArrayField(int) | 0=Mon … 6=Sun (UI: M T W T F S S) |
| `terms` | TextField | bullet-friendly text |
| `status` | CharField | `draft` \| `active` \| `ended` \| `hidden` |
| `view_count` / denorm contact counts | optional caches | |
| `created_at` / `updated_at` | |

**Rule:** `deal_price` &lt; `items_total`.

### 5.14 `deals.DealLine`

| Field | Type |
|---|---|
| `deal` | FK |
| `menu_item` | FK |
| `size_label` | CharField |
| `unit_price` | Decimal | snapshot at build time |
| `quantity` | PositiveSmallInteger default 1 |
| `position` | int | |

### 5.15 `promotions.PromotionRequest`

Boosted placement request for a **menu item** or **deal**.

| Field | Type | Notes |
|---|---|---|
| `restaurant` | FK | |
| `content_type` | GenericFK or explicit | `menu_item` \| `deal` |
| `menu_item` | FK nullable | |
| `deal` | FK nullable | |
| `title` | CharField | PROMOTION TITLE / deal label |
| `status` | CharField | `pending` \| `live` \| `changes` \| `ended` |
| `reach_radius_km` | PositiveSmallInteger | 1\|3\|5\|10 |
| `duration_days` | PositiveSmallInteger | 1\|3\|7\|14 |
| `requested_start` / `requested_end` | DateTime | from RUN DATES |
| `admin_note` | TextField | e.g. “needs a clearer video” |
| `reviewed_by` | FK User nullable | |
| `reviewed_at` | DateTime nullable | |
| `goes_live_at` / `ends_at` | DateTime | set on approval |
| `created_at` | | |

**Important:** Publishing the item/deal does **not** auto-set `live`. Only admin approval does (unless you add auto-approve later; prototype is admin-reviewed, free in beta).

### 5.16 `mediahub.Video`

| Field | Type | Notes |
|---|---|---|
| `restaurant` | FK | |
| `menu_item` | OneToOne/FK nullable | exactly one attachment target |
| `deal` | FK nullable | |
| `file` / `hls_url` | FileField / URL | |
| `poster` | ImageField | cover frame |
| `duration_seconds` | PositiveInteger | **max 60** |
| `caption` | TextField | + hashtags parsed |
| `view_count` | PositiveInteger | |
| `like_count` | PositiveInteger | |
| `is_promoted` | bool | true when linked promo is `live` |
| `status` | CharField | `processing` \| `ready` \| `failed` \| `removed` |
| `created_at` | | |

**Rule:** Every published product and deal needs **exactly one** video (≤ 60s).

### 5.17 `mediahub.Photo`

| Field | Type |
|---|---|
| `restaurant` | FK nullable |
| `menu_item` | FK nullable |
| `deal` | FK nullable |
| `file` | ImageField |
| `aspect` | CharField | `1:1` \| `4:3` \| `16:9` \| `free` |
| `is_cover` | bool | for galleries |
| `position` | int | |
| `upload_status` | CharField | `uploading` \| `ready` \| `failed` |

Restaurant **photo gallery** is **derived** from menu item / deal photos (read-only N-03), not a separate upload library in Phase 1.

### 5.18 `engagement.Save`

| Field | Type |
|---|---|
| `user` | FK |
| `target_type` | `deal` \| `restaurant` \| `menu_item` \| `video` |
| `deal` / `restaurant` / `menu_item` / `video` | FK nullable |
| `created_at` | |
| UniqueTogether | (`user`, target) |

Saved deals sorted by **soonest expiry**. Expired deals move to collapsed `Expired` group (query filter).

### 5.19 `engagement.Follow`

| Field | Type |
|---|---|
| `user` | FK |
| `restaurant` | FK |
| `created_at` | |
| UniqueTogether | (`user`, `restaurant`) |

### 5.20 `engagement.Like`

| Field | Type |
|---|---|
| `user` | FK nullable (guest via session) |
| `session_key` | CharField nullable |
| `video` | FK |
| Unique constraint on user/session + video |

### 5.21 `engagement.ContentReport`

| Field | Type |
|---|---|
| `user` / `session_key` | |
| `video` | FK |
| `reason` | CharField | see enums |
| `created_at` | |

### 5.22 `engagement.NotInterested`

| Field | Type |
|---|---|
| `user` / `session_key` | |
| `video` | FK nullable |
| `restaurant` | FK nullable |
| `cuisine` | CharField nullable |
| `reason` | CharField | |
| `created_at` | |

### 5.23 `analytics.EngagementEvent`

Immutable event log (high volume — consider partitioning / Timescale later).

| Field | Type |
|---|---|
| `event_type` | CharField | see §13 |
| `user` | FK nullable |
| `session_key` | CharField |
| `restaurant` | FK nullable |
| `video` / `deal` / `menu_item` | FK nullable |
| `source` | CharField | `feed` \| `explore` \| `search` \| `promoted` \| `direct` \| `profile` |
| `watch_seconds` | Float nullable |
| `metadata` | JSON |
| `lat` / `lng` | nullable |
| `created_at` | indexed |

### 5.24 `analytics.AnalyticsDaily`

Rollup per restaurant per day (Celery hourly/daily).

| Field | Type |
|---|---|
| `restaurant` | FK |
| `date` | Date |
| `video_views` | int |
| `restaurant_views` | int |
| `menu_views` | int |
| `deal_views` | int |
| `whatsapp_clicks` | int |
| `call_clicks` | int |
| `directions_clicks` | int |
| `saves` | int |
| `shares` | int |
| `follows` | int |
| `unique_visitors` | int |
| `new_visitors` | int |
| `returning_visitors` | int |
| UniqueTogether | (`restaurant`, `date`) |

### 5.25 `common.AppConfig` (singleton / key-value)

| Key | Example |
|---|---|
| `free_tier_products_per_month` | `5` |
| `min_app_version_ios` / `android` | |
| `feed_nearby_default_km` | `5` |
| `promo_expiring_warn_hours` | `48` |
| `promo_expiring_danger_hours` | `2` |

---

## 6. Enums & constants

```python
class SignupIntent(models.TextChoices):
    """UI choice at register only — NOT an authorization role."""
    CUSTOMER = "customer", "Customer"
    RESTAURANT = "restaurant", "Restaurant"

class AppMode(models.TextChoices):
    """Client UX mode; optional hint, not enforced as exclusive role."""
    CUSTOMER = "customer", "Customer"
    CONSOLE = "console", "Restaurant Console"

class PriceRange(models.TextChoices):
    BUDGET = "$", "$"
    MODERATE = "$$", "$$"
    UPSALE = "$$$", "$$$"
    FINE = "$$$$", "$$$$"

class ItemType(models.TextChoices):
    CHICKEN = "Chicken"
    BEEF = "Beef"
    MUTTON = "Mutton"
    FISH = "Fish"
    VEG = "Veg"
    VEGETARIAN = "Vegetarian"
    EGG = "Egg"
    MIXED = "Mixed"

class PromotionStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    LIVE = "live", "Live"          # UI also shows "Promoted" / "appr"
    CHANGES = "changes", "Changes" # rejected / needs revision
    ENDED = "ended", "Ended"

class DealListSegment(models.TextChoices):
    ACTIVE = "active"
    PENDING = "pending"  # promotion pending
    ENDED = "ended"

class ReportReason(models.TextChoices):
    NOT_INTERESTED = "not_interested", "Not interested in this"
    HIDE_RESTAURANT = "hide_restaurant", "Hide restaurant"
    LESS_CUISINE = "less_cuisine", "Less of this cuisine"
    REPORT_VIDEO = "report_video", "Report this video"

class ContactEventType(models.TextChoices):
    CALL = "call_click"
    WHATSAPP = "whatsapp_click"
    DIRECTIONS = "directions_click"
```

**Currency:** PKR, display as `Rs. 1,500` (thousands separators). Store as `Decimal`.

**WhatsApp prefills template:**

```text
Hi! I saw your "{deal_or_promo_title}" deal on FoodApp — is it available today?
```

Client builds `https://wa.me/{digits}?text={urlencoded}`; API returns `whatsapp_number` and suggested `prefill_message`.

---

## 7. Authentication & authorization (JWT)

### 7.1 Library

`djangorestframework-simplejwt`

- Access token TTL: 30–60 minutes  
- Refresh token TTL: 7–30 days  
- Rotate refresh tokens; blacklist on logout  

### 7.2 Auth endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/register/` | Public | Create account (± restaurant shell). Always gets customer profile |
| POST | `/api/auth/login/` | Public | Phone + password → JWT pair |
| POST | `/api/auth/refresh/` | Public | Refresh access token |
| POST | `/api/auth/logout/` | JWT | Blacklist refresh |
| POST | `/api/auth/password/forgot/` | Public | Start reset (SMS/OTP or link) — **UI label exists; implement backend** |
| POST | `/api/auth/password/reset/` | Public | Confirm reset with token/OTP |
| GET | `/api/auth/me/` | JWT | User + `profiles.customer` / `profiles.restaurant` + single `restaurant` object or null |
| PATCH | `/api/auth/me/` | JWT | Update display name, avatar |
| POST | `/api/auth/guest/migrate/` | JWT | Merge `session_key` guest data |
| DELETE | `/api/auth/me/` | JWT | Soft-delete; 30-day purge |
| POST | `/api/me/customer-profile/` | JWT | Add Customer profile if missing (restaurant-only → both) |
| POST | `/api/me/restaurants/` | JWT | Add Restaurant profile if missing; **409 if already has one** |
| GET | `/api/me/profiles/` | JWT | Available modes for Switch UI |

### 7.3 Registration validation

**Shared (both signup paths)**

- `phone_number`: required, unique, valid PK mobile
- `password`: min 8 characters
- Accept Terms & Privacy (client; log `terms_accepted_at`)

**Signup as Customer** (`signup_intent=customer`)

- Create `CustomerProfile` (+ prefs / notification settings)
- Do **not** create Restaurant
- Response: `profiles.customer = true`, `profiles.restaurant = false`

**Signup as Restaurant** (`signup_intent=restaurant`)

- `restaurant_name`: required
- Create `Restaurant` shell (`owner` OneToOne); checklist incomplete
- Do **not** require CustomerProfile (Restaurant-only ✅); optionally also create CustomerProfile if product wants both from day one
- Response: `profiles.customer = <bool>`, `profiles.restaurant = true`, `restaurant: { id, name, ... }`

### 7.4 Add the other profile later

| Method | Path | Description |
|---|---|---|
| POST | `/api/me/customer-profile/` | Restaurant-only user adds Customer profile |
| POST | `/api/me/restaurants/` | Customer-only user adds **one** Restaurant; **409** if already owns one |
| POST | `/api/restaurants/{id}/claim/` | Start claim; OTP to listed `primary_phone`; fail if user already has restaurant |
| POST | `/api/restaurants/{id}/claim/verify/` | Verify OTP; set `owner = request.user` (OneToOne) |

After restaurant create/claim, Profile shows **Switch to Restaurant**.

### 7.5 DRF permission classes

```text
IsAuthenticated
HasCustomerProfile         # user.customer_profile exists
IsRestaurantOwner          # hasattr(user, "restaurant")
IsRestaurantObjectOwner    # object.restaurant.owner_id == user.id
IsPlatformAdmin
AllowAny
IsAuthenticatedOrReadOnly
```

**Never** check `user.role == "restaurant"`. Use profile existence / OneToOne ownership.

---

## 8. REST API catalogue

Base URL: `/api/`  
Format: JSON  
Auth header: `Authorization: Bearer <access>`

### 8.1 Geo & bootstrap

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | `/cities/` | Public | List cities + restaurant_count |
| GET | `/cities/search/?q=` | Public | City typeahead |
| POST | `/cities/waitlist/` | Optional | Waitlist for unsupported city |
| GET | `/bootstrap/` | Optional | App config, min versions, feature flags |

### 8.2 Customer — Feed (`apps.feed`)

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | `/feed/?mode=for_you\|nearby&cursor=` | Optional | Paginated video feed |

See [`backend-docs/apps/feed.md`](backend-docs/apps/feed.md) for ranking, promo bar, and refresh rules.

### 8.2b Customer — Explore / Search (`apps.discovery`)

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | `/explore/products/` | Optional | Product cards (prototype Explore) |
| GET | `/explore/map/` | Optional | Pins + compact cards |
| GET | `/search/?q=&tab=food\|restaurants\|deals` | Optional | Unified search |
| GET | `/search/trending/` | Optional | Trending queries (EN + Urdu) |
| GET | `/filters/meta/` | Public | Allowed filter values |

### 8.3 Customer — Restaurants & menu

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | `/restaurants/{id}/` | Public | Profile |
| GET | `/restaurants/{id}/menu/` | Public | Categories + items |
| GET | `/restaurants/{id}/videos/` | Public | Video grid |
| GET | `/restaurants/{id}/photos/` | Public | Derived gallery |
| GET | `/restaurants/{id}/deals/` | Public | Active deals |
| GET | `/menu-items/{id}/` | Public | Item detail + sizes + linked deal |
| GET | `/deals/{id}/` | Public | Promo sheet payload |
| GET | `/deals/{id}/similar/` | Public | After expiry |

### 8.4 Customer — Engagement

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | `/saved/?type=deals\|places\|items\|videos` | JWT | Saved lists |
| POST | `/saved/` | JWT | Save target |
| DELETE | `/saved/{id}/` | JWT | Unsave |
| POST | `/follows/` | JWT | Follow restaurant |
| DELETE | `/follows/{restaurant_id}/` | JWT | Unfollow |
| POST | `/videos/{id}/like/` | Optional | Like / unlike |
| POST | `/reports/` | Optional | Report / not interested |
| POST | `/events/` | Optional | Batch analytics events |
| POST | `/contact/` | Optional | Log contact + return deep-link payloads |

### 8.5 Customer — Profile & multi-profile switch

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET/PATCH | `/me/preferences/` | JWT | Cuisine, price, distance (customer profile) |
| GET/PATCH | `/me/notifications/` | JWT | Notification toggles |
| GET | `/me/profiles/` | JWT | `{ customer: bool, restaurant: bool, restaurant_id?: ... }` |
| POST | `/me/customer-profile/` | JWT | Create Customer profile if missing |
| POST | `/me/restaurants/` | JWT | Create Restaurant profile if missing; **409 if exists** |
| GET | `/me/console-access/` | JWT | `{ can_switch: bool, restaurant: {...}|null }` |

### 8.6 Restaurant console

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | `/console/dashboard/` | Owner | Checklist + this-month stats |
| GET/PATCH | `/console/restaurant/` | Owner | Profile fields (R-17) |
| PATCH | `/console/restaurant/media/` | Owner | Logo / cover (R-18) |
| PATCH | `/console/restaurant/contact/` | Owner | Phones (R-19) |
| PATCH | `/console/restaurant/address/` | Owner | Address + lat/lng (R-20) |
| PATCH | `/console/restaurant/promotion-defaults/` | Owner | R-21 defaults |
| POST | `/console/restaurant/pause/` | Owner | Toggle `is_paused` |

**Categories**

| Method | Endpoint | Purpose |
|---|---|---|
| GET/POST | `/console/categories/` | List / create (N-01) |
| PATCH/DELETE | `/console/categories/{id}/` | Update / soft-hide |
| POST | `/console/categories/reorder/` | `[{id, position}]` |

**Menu items**

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/console/menu-items/` | Builder list + promoted section |
| POST | `/console/menu-items/` | Create (R-08) — enforces free-tier quota |
| GET/PATCH | `/console/menu-items/{id}/` | Detail / update |
| POST | `/console/menu-items/{id}/duplicate/` | Duplicate |
| POST | `/console/menu-items/{id}/move/` | Change category |
| POST | `/console/menu-items/{id}/hide/` | Hide from menu |
| DELETE | `/console/menu-items/{id}/` | Delete (warn if in active promo/video) |
| PATCH | `/console/menu-items/{id}/availability/` | Toggle stock |

**Add-ons**

| Method | Endpoint | Purpose |
|---|---|---|
| GET/POST | `/console/addons/` | N-02 |
| PATCH/DELETE | `/console/addons/{id}/` | |

**Deals**

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/console/deals/?segment=active\|pending\|ended` | R-11 |
| POST | `/console/deals/` | R-12 |
| GET/PATCH/DELETE | `/console/deals/{id}/` | |
| GET | `/console/deals/{id}/preview/` | Customer-accurate preview |

**Promotion requests**

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/console/promotion-requests/` | R-21 list |
| POST | `/console/promotion-requests/` | From item/deal toggle |
| GET | `/console/promotion-requests/{id}/` | |

**Analytics**

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/console/analytics/overview/?range=` | R-14 |
| GET | `/console/analytics/funnel/?range=` | R-14b |
| GET | `/console/analytics/content/?range=` | R-14c |
| GET | `/console/analytics/export/?format=pdf\|csv&range=` | Export |

**Media uploads**

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/console/uploads/init/` | Create upload session |
| POST | `/console/uploads/{id}/chunk/` or PUT to signed URL | Upload bytes |
| POST | `/console/uploads/{id}/complete/` | Finalize + process |
| DELETE | `/console/uploads/{id}/` | Cancel |

### 8.7 Platform admin

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/admin-api/promotion-requests/?status=pending` | Queue |
| POST | `/admin-api/promotion-requests/{id}/approve/` | → `live` |
| POST | `/admin-api/promotion-requests/{id}/reject/` | → `changes` + note |
| POST | `/admin-api/restaurants/{id}/quota/override/` | Lift product cap |
| GET | `/admin-api/reports/` | Moderation queue |

(Also use Django Admin UI for ops.)

---

## 9. Request/response examples & validation

### 9.1 Register — customer only

`POST /api/auth/register/`

```json
{
  "signup_intent": "customer",
  "phone_number": "+923008452119",
  "password": "secret123",
  "session_key": "guest-abc-123"
}
```

**201 Response**

```json
{
  "user": {
    "id": "u_01",
    "phone_number": "+923008452119",
    "display_name": null,
    "profiles": {
      "customer": true,
      "restaurant": false,
      "platform_admin": false
    },
    "restaurant": null
  },
  "tokens": { "access": "<jwt>", "refresh": "<jwt>" }
}
```

Later: `POST /me/restaurants/` or claim → `profiles.restaurant = true` (still one account). Second create → **409**.

### 9.2 Register — restaurant only

```json
{
  "signup_intent": "restaurant",
  "restaurant_name": "Burger House",
  "phone_number": "+923001112233",
  "password": "secret123"
}
```

**201 Response**

```json
{
  "user": {
    "id": "u_02",
    "phone_number": "+923001112233",
    "display_name": null,
    "profiles": {
      "customer": false,
      "restaurant": true,
      "platform_admin": false
    },
    "restaurant": {
      "id": "r_1",
      "name": "Burger House",
      "setup_completeness_pct": 20
    }
  },
  "tokens": { "access": "<jwt>", "refresh": "<jwt>" }
}
```

Restaurant-only users use Console; to Save/Follow as a customer they call `POST /me/customer-profile/` first (or product may auto-create both at restaurant signup — confirm with PM).

### 9.2b Add the missing profile

`POST /api/me/restaurants/` (customer-only user):

```json
{ "name": "Burger House" }
```

| Result | Status |
|---|---|
| First restaurant created | 201, `profiles.restaurant: true` |
| User already has a restaurant | **409** `RESTAURANT_PROFILE_EXISTS` |

`POST /api/me/customer-profile/` (restaurant-only user) → 201, `profiles.customer: true` · already has customer → 409 `CUSTOMER_PROFILE_EXISTS`.

### 9.3 Login

```json
{
  "phone_number": "+923008452119",
  "password": "secret123",
  "session_key": "guest-abc-123"
}
```

**400:** invalid credentials (generic message).  
**200:** same shape as `/auth/me/` (`profiles` + single `restaurant` or `null`); merge guest if `session_key`.

### 9.4 Create menu item

`POST /api/console/menu-items/`

```json
{
  "name": "Zinger Burger",
  "description": "Crispy fried chicken fillet, lettuce, mayo, sesame bun",
  "category_id": "cat_fastfood",
  "subcategory": null,
  "item_type": "Chicken",
  "sizes": [
    { "label": "Regular", "price": "690.00", "offer_price": null },
    { "label": "Large", "price": "890.00", "offer_price": "749.00" }
  ],
  "photo_ids": ["ph_1", "ph_2"],
  "video_id": "vid_1",
  "is_available": true,
  "is_popular": true,
  "request_promotion": true,
  "promotion": {
    "title": "Zinger Combo Deal",
    "starts_at": "2026-08-01T00:00:00+05:00",
    "ends_at": "2026-08-03T23:59:59+05:00"
  }
}
```

**Validation**

- `name`, `category_id` required
- ≥ 1 photo; exactly 1 video; video duration ≤ 60s
- Each size: `price` required; if `offer_price`, then `offer_price < price`
- If `request_promotion`, `promotion.title` + date range required; end &gt; start
- Free tier: reject with `403` / code `PRODUCT_QUOTA_EXCEEDED` when `products_created_this_month >= 5` (configurable)

**Behavior**

- Item publishes **immediately** (`status=published`)
- Promotion request created as `pending` (“Awaiting approval”)
- Response includes publish matrix: Feed video `Immediately`; Promoted rail `After approval`

### 9.5 Create deal

`POST /api/console/deals/`

```json
{
  "label": "Zinger Combo Deal",
  "description": "Zinger Burger + French Fries + Soft Drink",
  "lines": [
    { "menu_item_id": "mi_1", "size_label": "Regular", "unit_price": "690.00", "quantity": 1 },
    { "menu_item_id": "mi_fries", "size_label": "Medium", "unit_price": "280.00", "quantity": 1 },
    { "menu_item_id": "mi_drink", "size_label": "500ml", "unit_price": "280.00", "quantity": 1 }
  ],
  "deal_price": "999.00",
  "starts_at": "2026-08-01T00:00:00+05:00",
  "ends_at": "2026-08-31T23:59:59+05:00",
  "days_of_week": [4, 5, 6],
  "terms": "Dine-in and takeaway only. Cannot be combined with other offers. Mention this deal when ordering.",
  "photo_ids": ["ph_d1", "ph_d2"],
  "video_id": "vid_d1",
  "request_promotion": true
}
```

**Validation**

- ≥ 1 line item; `deal_price` &lt; sum(`unit_price * quantity`)
- Server computes `items_total`, `savings_amount`, `savings_percent` (e.g. Rs. 251 · 20%)
- Media rules same as product
- Warn (not block) if duration &gt; 90 days
- Warn if overlapping promo on same items
- If restaurant `auto_request_promo_on_deal`, create promotion request even without toggle

### 9.6 Promo sheet payload (customer)

`GET /api/deals/{id}/`

```json
{
  "id": "deal_1",
  "label": "WEEKEND PIZZA DEAL",
  "hero_image_url": "...",
  "hero_video_url": null,
  "original_price": "1500.00",
  "promo_price": "999.00",
  "discount_percent": 33,
  "starts_at": "...",
  "ends_at": "...",
  "countdown_seconds": 187200,
  "promo_state": "active",
  "terms": [
    "Dine-in and takeaway only",
    "Cannot combine with other offers",
    "Mention this promo when ordering"
  ],
  "restaurant": {
    "id": "r_1",
    "name": "Burger House",
    "rating_avg": 4.7,
    "distance_km": 2.3,
    "is_open": true,
    "primary_phone": "+92...",
    "whatsapp_number": "+92...",
    "lat": 31.52,
    "lng": 74.35
  },
  "is_saved": false,
  "prefill_message": "Hi! I saw your \"Weekend Pizza Deal\" deal on FoodApp — is it available today?",
  "promotion_status": "live"
}
```

**`promo_state` values for UI:** `active` · `expiring_soon` (&lt;48h) · `expiring_critical` (&lt;2h) · `expired` · `scheduled` · `fully_claimed` (future)

### 9.7 Explore filters

`GET /api/explore/products/?distance_km=3&price=$$&price=$$$&min_rating=4.5&open_now=true&has_deals=true&lat=&lng=&city_id=`

| Param | Type | Rules |
|---|---|---|
| `distance_km` | 1\|3\|5\|10 | single; requires lat/lng |
| `price` | multi `$`…`$$$$` | |
| `min_rating` | 3.5\|4.0\|4.5 | single |
| `open_now` | bool | |
| `has_deals` | bool | “Deals available” |
| `q` | string | optional text |
| `page` / `cursor` | | |

Response includes `count` for CTA **Show {n} results** and active filter echo.

### 9.8 Contact action

`POST /api/contact/`

```json
{
  "action": "whatsapp_click",
  "restaurant_id": "r_1",
  "deal_id": "deal_1",
  "source": "promo_sheet",
  "session_key": "..."
}
```

**200**

```json
{
  "tel_uri": "tel:+92300...",
  "whatsapp_uri": "https://wa.me/92300...?text=Hi%21%20I%20saw...",
  "maps_uri": "https://maps.google.com/?q=31.52,74.35",
  "address_text": "12 Main Blvd, Gulberg III, Lahore"
}
```

Always persist analytics event.

### 9.9 Feed page

`GET /api/feed/?mode=for_you&cursor=eyJ...`

```json
{
  "next_cursor": "...",
  "results": [
    {
      "video_id": "v1",
      "video_url": "...",
      "poster_url": "...",
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
        "logo_url": "...",
        "is_promoted": true
      },
      "promo_bar": {
        "deal_id": "deal_1",
        "title": "Weekend Pizza Deal",
        "old_price": "1500.00",
        "new_price": "999.00",
        "ends_in_seconds": 187200,
        "state": "active"
      }
    }
  ]
}
```

**Refresh contract:** prepend new items; do **not** fully reshuffle the already-seen tail.

### 9.10 Analytics overview

`GET /api/console/analytics/overview/?range=this_month`

Ranges: `last_7_days` \| `this_month` \| `last_month` \| `custom` (`start`, `end`)

```json
{
  "customers_reached": 1600,
  "breakdown": {
    "whatsapp": 1180,
    "calls": 642,
    "directions": 318
  },
  "contacts_per_video_view": "1 per 16",
  "delta_vs_previous_pct": 22,
  "metrics": {
    "video_views": { "value": 25400, "delta_pct": 12 },
    "whatsapp_clicks": { "value": 1180, "delta_pct": 21 },
    "call_clicks": { "value": 642, "delta_pct": 9 },
    "directions": { "value": 318, "delta_pct": 14 },
    "restaurant_views": { "value": 4200, "delta_pct": 8 },
    "menu_views": { "value": 2850, "delta_pct": 15 },
    "deal_views": { "value": 1400, "delta_pct": 31 },
    "saves": { "value": 320, "delta_pct": 19 },
    "shares": { "value": 148, "delta_pct": 27 },
    "follows": { "value": 96, "delta_pct": -4 }
  },
  "daily_restaurant_views": [{"date": "2026-08-01", "count": 106}, "..."],
  "contact_mix_pct": {"whatsapp": 55, "call": 30, "directions": 15},
  "last_refreshed_at": "2026-08-03T09:15:00+05:00"
}
```

**Headline formula:** `customers_reached = whatsapp + calls + directions` (unique contacts optional later; prototype sums clicks).

Funnel stages: Video → Restaurant → Menu → Deal → Contacts.  
Sources share: Feed 62%, Explore 21%, Search 9%, Promoted 6%, Direct 2%.

---

## 10. Business logic & workflows

### 10.0 Multi-profile (Customer 0..1 + Restaurant 0..1)

```
User
├── CustomerProfile (0..1)
└── Restaurant      (0..1)   ← hard max one

Customer-only
  └─ May add Restaurant once → POST /me/restaurants/ or claim
        └─ Second restaurant attempt → 409 RESTAURANT_PROFILE_EXISTS

Restaurant-only
  └─ May add CustomerProfile once → POST /me/customer-profile/
        └─ Console for their single restaurant
        └─ Switch to Customer mode after CustomerProfile exists

Both
  └─ Same JWT; client switches Customer App ↔ Console
```

Rules:

1. **One phone = one User.**
2. **At most one Restaurant** per user (`owner` OneToOne).
3. **At most one CustomerProfile** per user.
4. Console auth = `user.restaurant` exists, not a role enum.
5. Mode switch does not re-authenticate.

### 10.1 Publish vs promote

```
Publish MenuItem / Deal
  ├─ Content visible on menu / profile / explore immediately
  ├─ Video eligible for organic Feed immediately
  └─ If request_promotion:
        Create PromotionRequest(status=pending)
          └─ Admin approve → status=live → boosted Feed/Explore placement
          └─ Admin reject → status=changes + admin_note
```

### 10.2 Setup checklist (Dashboard)

Compute booleans:

| Key | Complete when |
|---|---|
| `restaurant_created` | always true after signup |
| `profile` | short_description + cuisines (≤3) + price_range |
| `logo_cover` | logo and cover present |
| `contact` | primary_phone set |
| `address` | street + city + lat/lng |
| `menu` | ≥ 1 published menu item |

Return `completed_count / total` and deep-link keys for each incomplete row.

### 10.3 Free-tier product quota

- Default: **5 new products per calendar month**
- Counter resets on month boundary (`products_quota_month`)
- At limit: block create; error copy matches E-13; suggest **Message support** (no paywall in Phase 1)
- Admin can override

### 10.4 Delete / hide menu item

- If item is in an **active** deal or **live** promotion or linked video: return warning payload; require `force=true` or block with clear message (prototype: “In 1 promo”)
- Soft-delete preferred; hard-delete only if safe

### 10.5 Pause listing

`is_paused=true` → exclude from Feed, Explore, Search, Map (same as permanently closed for customers). Owner console remains available; banner “Listing paused”.

### 10.6 Open / closed

Prototype does **not** collect opening hours. Options:

1. Phase 1: omit `open_now` filter server-side **or** treat all as unknown/open
2. Add `OpeningHours` model later (per-day open/close, overnight, holiday) and compute `is_open_now` in restaurant TZ (`Asia/Karachi`)

If hours exist: closed cards stay visible unless `open_now=true`; WhatsApp stays primary; Call label may include “Opens 5:00 PM”.

### 10.7 Radius ladder (empty nearby)

If zero results within requested radius, auto-widen `1 → 3 → 5 → 10 → 25` km and return `widened_to_km` + banner message.

### 10.8 Guest → registered migration

Union:

- Pending save intent → execute Save
- Watch history / searches → attach to user
- Likes / not-interested → attach where possible  
Do not delete existing user saves.

### 10.9 Promo expiry jobs (Celery)

- Transition `live` → `ended` when `ends_at` passed
- Push expiry reminders 24h before for users with saved deal + setting on
- Nearby flash: deals ending within 6h and user within 2 km

---

## 11. File upload & media handling

### 11.1 Asset rules

| Asset | Aspect | Constraints |
|---|---|---|
| Menu / deal photos | 1:1 preferred | ≥ 1 required to publish |
| Menu / deal video | vertical preferred | Exactly 1; **≤ 60 seconds**; required to publish |
| Logo | 1:1 | Optional |
| Cover | 16:9 | Optional |
| Crop modes | 1:1 / 4:3 / 16:9 / Free | Client crop before upload |

### 11.2 Recommended flow

1. `POST /console/uploads/init/` → `{ upload_id, upload_url, fields }` (S3 presigned)
2. Client uploads directly to object storage
3. `POST /console/uploads/{id}/complete/` → validate mime, size, duration (ffprobe)
4. Transcode video to HLS / MP4 ladder; generate poster
5. Attach `photo_ids` / `video_id` when creating item/deal

### 11.3 Limits (suggested)

| Type | Max size |
|---|---|
| Image | 10 MB |
| Video | 100 MB (≤ 60s) |

Allowed: `image/jpeg`, `image/png`, `image/webp`, `video/mp4`, `video/quicktime`.

### 11.4 Offline / failure

- Support resumable uploads
- Status `failed` → Retry
- Cancel deletes incomplete objects
- Gallery endpoint is read-only derived media

### 11.5 Storage layout

```
media/restaurants/{restaurant_id}/logo/
media/restaurants/{restaurant_id}/cover/
media/restaurants/{restaurant_id}/items/{item_id}/
media/restaurants/{restaurant_id}/deals/{deal_id}/
media/restaurants/{restaurant_id}/videos/{video_id}/
```

Serve via CDN in production. Never commit media to git.

---

## 12. Pagination, filtering, searching & sorting

### 12.1 Pagination

- Feed: **cursor** pagination (stable under inserts)
- Explore / Search / Saved / Console lists: cursor or page-number; default page size **20**
- If Explore/Search &gt; 500 matches: paginate; optional hint “Add a filter to narrow down”

### 12.2 Filtering (Explore)

See §9.7. Quick chips: Promotions, Open Now, Nearby, 4.5+.

### 12.3 Search

- Tabs: `food` (menu items) · `restaurants` · `deals`
- Index: name, description, cuisine, area, city, caption/hashtags
- Support English + Urdu / Roman-Urdu (`biryani` / `بریانی`)
- Fuzzy / did-you-mean on zero results
- Empty query → recent (user) + trending

### 12.4 Sorting

| Surface | Default sort |
|---|---|
| Explore (with location) | distance ascending |
| Saved deals | soonest `ends_at` |
| Saved others | `created_at` desc |
| Console deals Active | `ends_at` asc / recently updated |
| Menu builder | category `position`, item `position` |
| Feed | ranked score (§16), not pure chrono |

### 12.5 Geo

Prefer **PostGIS** (`geography` point) + `dwithin`. Fallback: Haversine annotated queryset.

Always accept `lat`, `lng`, `city_id`. If no location: hide distance fields (never `"-- km"`).

---

## 13. Analytics & event tracking

### 13.1 Event types

| `event_type` | Fired when |
|---|---|
| `video_view` | ≥ 3s watch (min signal) |
| `video_complete` | ≥ ~95% watched |
| `video_skip` | &lt; 2s |
| `like` | double-tap / like |
| `share` | share sheet action |
| `promo_click` | Promo Bar / sheet open |
| `restaurant_view` | profile open |
| `menu_view` | menu open |
| `deal_view` | promo sheet / deal card |
| `menu_item_view` | item detail |
| `save` / `unsave` | |
| `follow` / `unfollow` | |
| `whatsapp_click` | |
| `call_click` | |
| `directions_click` | |
| `search` | query submitted |
| `not_interested` | |

### 13.2 Batch ingest

`POST /api/events/`

```json
{
  "session_key": "...",
  "events": [
    {
      "event_type": "video_view",
      "video_id": "v1",
      "restaurant_id": "r1",
      "watch_seconds": 12.4,
      "source": "feed",
      "client_ts": "2026-08-03T17:01:00+05:00"
    }
  ]
}
```

Idempotency: optional `client_event_id` unique per session.

### 13.3 Rollups

- Hourly job updates `AnalyticsDaily` and denormalized counters
- UI copy: “Figures update hourly”
- Export PDF/CSV from same aggregates

### 13.4 Ranking weights (for personalization)

Highest → lowest: **promo click · menu view · restaurant profile · save · share · completion · watch duration · like**

Negatives: not interested, hide restaurant, less cuisine, rapid skip.

---

## 14. Notifications

### 14.1 Channels

- Push (FCM / APNs)
- WhatsApp Business API (optional for owner approval alerts)
- In-app (future)

### 14.2 Triggers

| Trigger | Audience | Respects setting |
|---|---|---|
| Saved deal expires in 24h | Customer | `expiry_reminders` |
| New deal from saved restaurant | Customer | `new_deals_from_saved` |
| Nearby flash deal | Customer | `nearby_flash_deals` |
| New video from followed | Customer | `new_videos_from_followed` |
| Weekly digest Sundays 6 PM Asia/Karachi | Customer | `weekly_digest` |
| Security / sign-in | Customer | always |
| Promotion approved / changes requested | Owner | `notify_on_promo_approval` |

Never send promotional pushes for restaurants the user hasn't interacted with (product rule).

---

## 15. Third-party integrations

| Integration | Purpose | Backend responsibility |
|---|---|---|
| **WhatsApp** | `wa.me` deep links; optional Business API for owner notify | Return normalized digits + prefill text |
| **Phone** | `tel:` | Return E.164 |
| **Maps** | Directions | Return lat/lng + formatted address |
| **Object storage / CDN** | Media | Presigned uploads, public read URLs |
| **FCM / APNs** | Push | Device token registry |
| **SMS gateway** | Password reset OTP; claim OTP | Provider abstraction |
| **Video processing** | Transcode / poster | Worker (ffmpeg) or cloud media service |
| **PDF/CSV** | Analytics export | ReportLab / WeasyPrint / csv module |

**Not in Phase 1 backend:** JazzCash / Easypaisa / card payments, package billing, paid boost ledger.

Share targets (Facebook, Instagram, Status, Copy link) are **client-side**; backend only provides canonical deep links:

```
https://foodapp.app/r/{restaurant_id}
https://foodapp.app/d/{deal_id}
https://foodapp.app/v/{video_id}
```

---

## 16. Feed ranking & personalization

> Implemented in **`apps.feed`** (not `discovery`). Full detail: `backend-docs/apps/feed.md`.

### 16.1 New-user mix (cold start)

| Share | Bucket |
|---|---|
| 40% | Featured / Promoted (`promotion_status=live`) |
| 30% | Trending (views velocity) |
| 20% | New videos |
| 10% | Exploration / diversity |

### 16.2 Personalization ramp

| Videos watched | Strength |
|---|---|
| 1–2 | 10–20% |
| 3–5 | 30–40% |
| 5–10 | 50–60% |
| 15+ | 70–80% |

Blend explicit preferences (C-18) with observed behaviour; behaviour wins over time.

### 16.3 Modes

- **For You:** personalized + promoted mix
- **Nearby:** geo-filtered (default 5 km, widen ladder); requires location or city center

### 16.4 Attachments

Every feed video must resolve to restaurant and preferably deal/item destination (actionable video rule).

---

## 17. Error handling & edge cases

Use consistent error envelope:

```json
{
  "error": {
    "code": "PRODUCT_QUOTA_EXCEEDED",
    "message": "You've added 5 products this month",
    "details": { "limit": 5, "used": 5, "resets_on": "2026-09-01" }
  }
}
```

| Case | API behavior |
|---|---|
| Expired deal deep link | 200 with `promo_state=expired` + `similar_deals` |
| Deleted deal | 404 with `restaurant_id` fallback hint |
| Paused restaurant | 404 on public detail **or** 410 with message; excluded from lists |
| Location denied | Accept `city_id` only; omit `distance_km` fields |
| Zero search results | 200 empty + `suggestions` + `did_you_mean` |
| Concurrent menu edits | last-write-wins; return `updated_at` for client refresh |
| Promo price ≥ original | 400 validation |
| Video &gt; 60s | 400 on upload complete |
| Guest save | 401 `AUTH_REQUIRED` with `pending_action` echo |

HTTP mapping: 400 validation · 401 auth · 403 permission/quota · 404 missing · 409 conflict · 429 rate limit.

---

## 18. Environment, security & best practices

### 18.1 Settings checklist

- `AUTH_USER_MODEL = "accounts.User"`
- PostgreSQL + (recommended) PostGIS
- `SIMPLE_JWT` lifetimes + rotation
- `CORS_ALLOWED_ORIGINS` for mobile / web
- `MEDIA` via S3 in prod; local in dev
- Time zone: `Asia/Karachi`
- Language: English + Urdu strings for notifications
- Throttle: anon/user rates on auth, events, search

### 18.2 Security

- Hash passwords (Django default)
- Rate-limit login and OTP
- Never log raw passwords / OTP
- Signed URLs for uploads; scan mime sniffing
- Object-level permissions on all console writes
- Soft-delete users; purge PII after 30 days
- Admin actions audited (`reviewed_by`, timestamps)

### 18.3 DRF best practices — ModelViewSet + services

- **Every app has `services/`** — one service file per module, one service class per file
- Views / ViewSets stay **thin**: serialize → call service method → respond
- **Default to `ModelViewSet`** for model-backed resources; custom endpoints via `@action` that call services
- Built-ins: `list`, `create`, `retrieve`, `update`, `partial_update`, `destroy` → each delegates to a service where logic is non-trivial
- Split **read/write serializers** via `get_serializer_class()` by `self.action`
- Scope console data via service queryset helpers (`request.user.restaurant` OneToOne)
- `select_related` / `prefetch_related` inside service query methods
- Auth, feed, analytics aggregates: `APIView` + dedicated service (`AuthService`, `FeedService`, …)
- Mount API under `/api/` (no `/v1` prefix)
- OpenAPI via `drf-spectacular`
- Idempotent event ingest via `EventService`
- Celery tasks call the **same** service methods (no duplicated logic)

### 18.4 Testing priorities

1. Auth register/login/JWT refresh  
2. Menu item publish + promotion pending  
3. Admin approve → appears in promoted feed bucket  
4. Deal price &lt; items total  
5. Free-tier quota  
6. Save requires auth; migrate guest session  
7. Contact events increment analytics  
8. Paused restaurant excluded from explore  
9. Geo distance filter + widen ladder  
10. Cursor feed stability on refresh  

---

## 19. Seed data & fixtures

Match prototype / plan for QA:

- Cities: Lahore, Karachi, Islamabad, Faisalabad, Multan (+ empty Sialkot waitlist path)
- ≥ 12 restaurants including: closed/paused, no menu, no videos, no deals, missing logo, far away, long name
- Menu catalog aligned with `prototype/menu-data.js` categories & item schema
- Deals: active, pending promotion, ended, expiring &lt; 48h, scheduled
- Videos: 8–60s; some promoted
- Analytics fixtures approximating: video views 25,400 · restaurant 4,200 · menu 2,850 · deals 1,400 · WhatsApp 1,180 · calls 642 · directions 318 · saves 320
- 1 restaurant at **5/5** product quota for E-13 testing
- Platform admin user for promotion queue

---

## 20. Out of scope / deferred

Do **not** build in Phase 1 unless product re-opens scope:

| Deferred | Notes |
|---|---|
| Orders / cart / payments | Phase 2+ |
| Packages Free/Silver/Gold/Premium | Plan only; prototype has no billing |
| Paid Promote / boost campaigns | R-13 budget slider deferred |
| Team members | Settings note: no Team |
| Opening hours CRUD | Dropped in console v1 |
| Google / Apple OAuth | Plan only |
| In-app reviews write API | Ratings display-only; source TBD |
| Promo redemption QR/codes | Open product question |
| Comments on videos | UI shows count; full comments optional |

When monetization returns, add: `Package`, `Subscription`, `BoostCampaign`, `CreditLedger`, payment webhooks — without breaking Phase 1 content models.

---

## Appendix A — Screen → API map

| Screen | Primary APIs |
|---|---|
| C-03 City Picker | `GET /cities/`, `GET /cities/search/` |
| C-04 Feed | `GET /feed/` (`apps.feed`), `POST /events/` |
| C-05 Promo Sheet | `GET /deals/{id}/`, `POST /saved/`, `POST /contact/` |
| C-06/C-07 Explore/Map | `GET /explore/products/`, `GET /explore/map/` (`apps.discovery`) |
| C-08 Search | `GET /search/`, `GET /search/trending/` |
| C-09 Filters | query params on explore |
| C-10 Profile | `GET /restaurants/{id}/` |
| C-11 Menu | `GET /restaurants/{id}/menu/` |
| C-12 Item | `GET /menu-items/{id}/` |
| C-13 Videos | `GET /restaurants/{id}/videos/` |
| C-15 Saved | `GET /saved/?type=` |
| C-16–19 Profile/Prefs/Notifs | `/auth/me/`, `/me/preferences/`, `/me/notifications/` |
| C-17 Auth | `/auth/register/`, `/auth/login/` |
| R-06 Dashboard | `/console/dashboard/` |
| R-07–08 Menu | `/console/categories/`, `/console/menu-items/` |
| R-11–12 Deals | `/console/deals/` |
| R-14 Analytics | `/console/analytics/*` |
| R-16–21 Settings | `/console/restaurant*` |
| R-21 / Admin | `/console/promotion-requests/`, `/admin-api/promotion-requests/` |

---

## Appendix B — Prototype vs UI-PLAN (backend truth)

| Topic | Implement as (prototype) |
|---|---|
| Auth | Phone + password (+ forgot-password backend) |
| Profiles | **Multi-profile:** Customer (0..1) + Restaurant (0..1); **never** multiple restaurants |
| Explore | **Products** with restaurant meta, not restaurant-only cards |
| Saved tabs | Deals · Places · Items · Videos |
| Console nav | Dashboard · Menu · Feed · Deals · Analytics |
| Promotion | Admin approval; free in beta |
| Media | Bound to product/deal; gallery derived |
| Monetization | Product monthly cap + support; no packages API |
| Hours | Not required for MVP listing |

---

## Appendix C — Suggested model implementation order

1. `accounts` (User, JWT)  
2. `geo.City`  
3. `restaurants.Restaurant`  
4. `menu` (Category, Item, Size, AddOn)  
5. `mediahub` (Photo, Video, uploads)  
6. `deals`  
7. `promotions`  
8. `feed` (For You / Nearby ranking)  
9. `discovery` (explore/search/filters)  
10. `engagement`  
11. `analytics`  
12. Admin promotion review  
13. Notifications workers  

---

*End of specification. Implement against this document and the `prototype/` screens; escalate only open product questions listed in UI-PLAN Appendix A (redemption proof, ratings source, payments) if they block Phase 1 delivery.*
