# App: `accounts`

**Package:** `apps.accounts`  
**Depends on:** `core`; OneToOne to `restaurants.Restaurant`  
**Purpose:** Authentication, multi-profile (Customer 0..1 + Restaurant 0..1), prefs, notifications, guest merge.

---

## Multi-profile rules (authoritative)

```text
User
├── Customer Profile (0..1)
└── Restaurant Profile (0..1)   ← never more than one restaurant
```

| Example | Valid |
|---|---|
| Customer only | ✅ |
| Restaurant only | ✅ |
| Customer + Restaurant | ✅ |
| Two restaurants | ❌ |

---

## File layout

```
apps/accounts/
├── models.py
├── serializers.py
├── urls.py
├── views.py              # thin — call services only
├── permissions.py
├── signals.py
├── managers.py
└── services/
    ├── __init__.py
    ├── auth_service.py         # AuthService — register, login, logout, tokens
    ├── profile_service.py      # ProfileService — switch mode, get-or-create profiles
    ├── password_service.py     # PasswordService — OTP forgot/reset
    └── preference_service.py   # PreferenceService — prefs + notifications
```

**Rule:** put all business logic in the service class methods; ViewSets/APIViews only call them.

---

## Models

### `User`

Phone login. **No exclusive role field. No `last_active_restaurant`.**

| Field | Notes |
|---|---|
| `phone_number` | unique E.164 |
| `password` | min 8 |
| `display_name`, `avatar` | |
| `signup_intent` | audit only |
| `is_staff` | platform admin |

```python
@property
def has_customer_profile(self) -> bool: ...
@property
def has_restaurant_profile(self) -> bool: ...  # hasattr(self, "restaurant")
```

### `CustomerProfile`

`OneToOneField(User, related_name="customer_profile")` — **at most one**.

### `UserPreference` / `NotificationSetting`

Prefer OneToOne → `CustomerProfile`.

### `GuestSession`

Unchanged (session merge on auth).

---

## API endpoints

Base: `/api/auth/`, `/api/me/`

| Method | Path | Notes |
|---|---|---|
| POST | `/auth/register/` | Creates Customer **or** Restaurant profile per `signup_intent` |
| POST | `/auth/login/` | |
| POST | `/auth/refresh/` / `/auth/logout/` | |
| POST | `/auth/password/forgot/` / `reset/` | |
| GET/PATCH | `/auth/me/` | Includes `profiles` + single `restaurant` or `null` |
| POST | `/auth/guest/migrate/` | |
| DELETE | `/auth/me/` | soft-delete |
| GET/PATCH | `/me/preferences/` | requires CustomerProfile |
| GET/PATCH | `/me/notifications/` | requires CustomerProfile |
| GET | `/me/profiles/` | `{ customer, restaurant }` |
| POST | `/me/customer-profile/` | Add customer if missing; 409 if exists |
| POST | `/me/restaurants/` | Add restaurant if missing; **409 if exists** |
| GET | `/me/console-access/` | `{ can_switch, restaurant }` |

---

## `/auth/me/` shape

```json
{
  "id": "u_01",
  "phone_number": "+923008452119",
  "display_name": "Ahmad Sarwar",
  "profiles": {
    "customer": true,
    "restaurant": true,
    "platform_admin": false
  },
  "restaurant": {
    "id": "r_1",
    "name": "Burger House",
    "setup_completeness_pct": 60
  }
}
```

Customer-only → `"restaurant": null`. Restaurant-only → `"profiles.customer": false`.

---

## Business rules

1. One phone = one User.
2. At most one `CustomerProfile` and one `Restaurant` per user.
3. Same JWT for both modes; client switches UI.
4. Second `POST /me/restaurants/` → `409 RESTAURANT_PROFILE_EXISTS`.
5. Guest migrate + pending save require / create CustomerProfile as needed.

---

## Tests checklist

- [ ] Register customer → customer true, restaurant null  
- [ ] Register restaurant → restaurant object, customer false (unless product creates both)  
- [ ] Customer adds restaurant → success once; second → 409  
- [ ] Restaurant-only adds customer profile → success once  
- [ ] Claim fails if user already has restaurant  
