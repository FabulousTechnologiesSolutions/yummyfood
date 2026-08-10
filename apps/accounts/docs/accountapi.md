# Accounts API Reference

**Base URL:** `http://localhost:6060`  
**Content-Type:** `application/json` (unless noted)  
**Auth header (JWT):** `Authorization: Bearer <access_token>`

Mounted paths:

| Prefix | Source |
|---|---|cover
| `/api/auth/` | [`urls.py`](../urls.py) |
| `/api/me/` | [`me_urls.py`](../me_urls.py) |

---

## Shared shapes

### Auth / Me user payload

Returned by register, login, `GET/PATCH /api/auth/me/`, and several profile endpoints.

```json
{
  "id": 1,
  "phone_number": "+923008452119",
  "display_name": "Ahmad Sarwar",
  "active_mode": "customer",
  "profiles": {
    "customer": true,
    "restaurant": false,
    "platform_admin": false
  },
  "restaurant": null
}
```

With restaurant profile:

```json
{
  "id": 2,
  "phone_number": "+923001112233",
  "display_name": null,
  "active_mode": "restaurant",
  "profiles": {
    "customer": false,
    "restaurant": true,
    "platform_admin": false
  },
  "restaurant": {
    "id": 1,
    "name": "Burger House",
    "setup_completeness_pct": 17
  }
}
```

| Field | Type | Notes |
|---|---|---|
| `id` | int | User PK |
| `phone_number` | string | E.164 |
| `display_name` | string \| null | Empty string stored as `null` in response |
| `active_mode` | `"customer"` \| `"restaurant"` | Current UX mode; also in JWT claim |
| `profiles.customer` | bool | Has `CustomerProfile` |
| `profiles.restaurant` | bool | Owns a `Restaurant` |
| `profiles.platform_admin` | bool | `user.is_staff` |
| `restaurant` | object \| null | Present only when restaurant profile exists |

`avatar` is **not** included in this payload. It can be uploaded via `PATCH /api/auth/me/` (multipart) but is write-only for API responses.

### Tokens block

Added on register, login, add restaurant, and mode switches:

```json
{
  "tokens": {
    "access": "<jwt>",
    "refresh": "<jwt>"
  }
}
```

Access JWT claims include SimpleJWT defaults plus custom: `phone_number`, `active_mode` (and `user_id` from SimpleJWT).

### Error envelope

All API / domain errors use:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message.",
    "details": {}
  }
}
```

DRF validation failures (serializer) also wrap into this envelope; field errors usually appear under `error.details`.

**Important:** `error.code` is always uppercase in live responses (e.g. `NOT_AUTHENTICATED`, `INVALID`). Serializer failures use code **`INVALID`** with field messages in `details`.

### Phone numbers

Accepted input:

- E.164: `+923008452119`
- PK local: `03008452119` or `3008452119` → normalized to `+923008452119`

---

## Error code catalogue

| Code | HTTP | Message | Where |
|---|---|---|---|
| `INVALID_PHONE` | 400 | `Invalid phone number.` | Empty / non-string phone |
| `INVALID_PHONE` | 400 | `Invalid phone number. Use E.164 (e.g. +923008452119).` | Bad format |
| `INVALID_PASSWORD` | 400 | `Password must be at least 8 characters.` | Register / password reset (service). HTTP often surfaces as `INVALID` from serializer `min_length` first |
| `INVALID_SIGNUP_INTENT` | 400 | `signup_intent must be customer or restaurant.` | Register (service). HTTP often surfaces as `INVALID` from serializer `ChoiceField` first |
| `RESTAURANT_NAME_REQUIRED` | 400 | `restaurant_name is required for restaurant signup.` | Register restaurant |
| `RESTAURANT_NAME_REQUIRED` | 400 | `name is required.` | `POST /me/restaurants/` |
| `PHONE_EXISTS` | 409 | `An account with this phone number already exists.` | Register |
| `INVALID_CREDENTIALS` | 401 | `Invalid credentials.` | Login wrong phone/password |
| `ACCOUNT_DELETED` | 401 | `Invalid credentials.` | Soft-deleted / inactive **login** only |
| `INVALID_TOKEN` | 401 | `Invalid or expired refresh token.` | Refresh |
| `INVALID_TOKEN` | 400 | `Invalid or expired refresh token.` | Logout with bad refresh |
| `OTP_COOLDOWN` | 429 | `Please wait before requesting another OTP.` | Password forgot (<60s) |
| `OTP_INVALID` | 400 | `Invalid OTP.` | Reset: missing / wrong / max attempts / no user |
| `OTP_EXPIRED` | 400 | `OTP has expired.` | Reset |
| `PASSWORD_MISMATCH` | 400 | `Passwords do not match.` | Reset |
| `SESSION_REQUIRED` | 400 | `session_key is required.` | Guest migrate (empty) — rare on HTTP; empty body usually fails serializer as `INVALID` |
| `SESSION_NOT_FOUND` | 404 | `Guest session not found.` | Guest migrate; also register/login when `session_key` is present but unknown |
| `CUSTOMER_PROFILE_EXISTS` | 409 | `Customer profile already exists.` | Add customer profile |
| `RESTAURANT_PROFILE_EXISTS` | 409 | `You already have a restaurant profile.` | Add / create second restaurant |
| `CUSTOMER_PROFILE_REQUIRED` | 403 | `Customer profile required.` | Prefs/notifications in customer mode without profile |
| `RESTAURANT_PROFILE_REQUIRED` | 403 | `Restaurant profile required.` | Prefs/notifications in restaurant mode without restaurant |
| `INVALID_PRICE_RANGE` | 400 | `Invalid price_ranges value.` | Customer prefs patch |
| `INVALID_DISTANCE` | 400 | `max_distance_km must be between 1 and 25.` | Customer prefs (service). HTTP often surfaces as `INVALID` from serializer `min_value`/`max_value` first |
| `NOT_AUTHENTICATED` | 401 | Authentication credentials were not provided. / … | Missing/invalid JWT; also soft-deleted users on protected routes (`is_active=false`) |
| `INVALID` | 400 | Varies | Serializer validation (`signup_intent`, password length, field types, etc.); details in `error.details` |

---

# Auth endpoints (`/api/auth/`)

---

## 1. Register

`POST /api/auth/register/`  
**Auth:** Public

### Request — customer

```json
{
  "phone_number": "+923008452119",
  "password": "secret123",
  "signup_intent": "customer",
  "session_key": "guest-abc-123"
}
```

| Field | Required | Notes |
|---|---|---|
| `phone_number` | yes | max 20 |
| `password` | yes | min 8 (serializer + service) |
| `signup_intent` | yes | `customer` \| `restaurant` |
| `restaurant_name` | no* | **Required** when `signup_intent=restaurant` |
| `session_key` | no | Merges guest session if present |

### Request — restaurant

```json
{
  "phone_number": "+923001112233",
  "password": "secret123",
  "signup_intent": "restaurant",
  "restaurant_name": "Burger House"
}
```

### Success — `201 Created`

Customer:

```json
{
  "id": 1,
  "phone_number": "+923008452119",
  "display_name": null,
  "active_mode": "customer",
  "profiles": {
    "customer": true,
    "restaurant": false,
    "platform_admin": false
  },
  "restaurant": null,
  "tokens": {
    "access": "...",
    "refresh": "..."
  }
}
```

Restaurant-only (`profiles.customer=false`):

```json
{
  "id": 2,
  "phone_number": "+923001112233",
  "display_name": null,
  "active_mode": "restaurant",
  "profiles": {
    "customer": false,
    "restaurant": true,
    "platform_admin": false
  },
  "restaurant": {
    "id": 1,
    "name": "Burger House",
    "setup_completeness_pct": 17
  },
  "tokens": {
    "access": "...",
    "refresh": "..."
  }
}
```

### Errors

| HTTP | Code | Message |
|---|---|---|
| 400 | `INVALID_PHONE` | Invalid phone… |
| 400 | `INVALID_PASSWORD` | Password must be at least 8 characters. (service) |
| 400 | `INVALID_SIGNUP_INTENT` | signup_intent must be customer or restaurant. (service) |
| 400 | `RESTAURANT_NAME_REQUIRED` | restaurant_name is required for restaurant signup. |
| 400 | `INVALID` | Serializer validation (e.g. missing fields, password &lt; 8, bad `signup_intent`) |
| 404 | `SESSION_NOT_FOUND` | Guest session not found. (when `session_key` is sent but unknown) |
| 409 | `PHONE_EXISTS` | An account with this phone number already exists. |

---

## 2. Login

`POST /api/auth/login/`  
**Auth:** Public

### Request

```json
{
  "phone_number": "+923008452119",
  "password": "secret123",
  "session_key": "guest-abc-123"
}
```

| Field | Required |
|---|---|
| `phone_number` | yes |
| `password` | yes |
| `session_key` | no |

### Success — `200 OK`

Same shape as register (user + `tokens`).  
`active_mode` restored from `last_active_mode` (adjusted if that profile is missing).

### Errors

| HTTP | Code | Message |
|---|---|---|
| 400 | `INVALID_PHONE` | … |
| 400 | `INVALID` | Missing / invalid fields |
| 401 | `INVALID_CREDENTIALS` | Invalid credentials. |
| 401 | `ACCOUNT_DELETED` | Invalid credentials. (soft-deleted / inactive account) |
| 404 | `SESSION_NOT_FOUND` | Guest session not found. (when `session_key` is sent but unknown) |

---

## 3. Refresh token

`POST /api/auth/refresh/`  
**Auth:** Public

### Request

```json
{
  "refresh": "<refresh_jwt>"
}
```

### Success — `200 OK`

```json
{
  "access": "<new_access_jwt>",
  "refresh": "<new_refresh_jwt>"
}
```

Old refresh is blacklisted when possible. New access claim `active_mode` comes from DB.

### Errors

| HTTP | Code | Message |
|---|---|---|
| 400 | `INVALID` | `refresh` required |
| 401 | `INVALID_TOKEN` | Invalid or expired refresh token. |

---

## 4. Logout

`POST /api/auth/logout/`  
**Auth:** JWT required

### Request

```json
{
  "refresh": "<refresh_jwt>"
}
```

### Success — `204 No Content`

Empty body. Persists `last_active_mode = active_mode`, blacklists refresh.

### Errors

| HTTP | Code | Message |
|---|---|---|
| 401 | `NOT_AUTHENTICATED` | Missing/invalid access token |
| 400 | `INVALID` | `refresh` required |
| 400 | `INVALID_TOKEN` | Invalid or expired refresh token. |

---

## 5. Password forgot (send OTP)

`POST /api/auth/password/forgot/`  
**Auth:** Public

### Request

```json
{
  "phone_number": "+923008452119"
}
```

### Success — `200 OK` (always, even if phone unknown)

```json
{
  "message": "If an account exists for this phone, an OTP has been sent."
}
```

OTP is sent via console SMS stub (provider TBD). TTL default **10 minutes**. Resend cooldown **60 seconds**.

### Errors

| HTTP | Code | Message |
|---|---|---|
| 400 | `INVALID_PHONE` | … |
| 400 | `INVALID` | Missing phone |
| 429 | `OTP_COOLDOWN` | Please wait before requesting another OTP. |

---

## 6. Password reset (verify OTP)

`POST /api/auth/password/reset/`  
**Auth:** Public

### Request

```json
{
  "phone_number": "+923008452119",
  "otp": "123456",
  "new_password": "newsecret1",
  "confirm_password": "newsecret1"
}
```

| Field | Required | Notes |
|---|---|---|
| `phone_number` | yes | |
| `otp` | yes | max 10 |
| `new_password` | yes | min 8 |
| `confirm_password` | yes | must match `new_password` |

### Success — `200 OK`

```json
{
  "message": "Password updated successfully."
}
```

### Errors

| HTTP | Code | Message |
|---|---|---|
| 400 | `PASSWORD_MISMATCH` | Passwords do not match. |
| 400 | `INVALID_PASSWORD` | Password must be at least 8 characters. |
| 400 | `OTP_INVALID` | Invalid OTP. |
| 400 | `OTP_EXPIRED` | OTP has expired. |
| 400 | `INVALID_PHONE` | … |
| 400 | `INVALID` | Field errors |

---

## 7. Me — get / update / soft-delete

`GET /api/auth/me/`  
`PATCH /api/auth/me/`  
`DELETE /api/auth/me/`  
**Auth:** JWT required (`IsAuthenticatedAndActive`)

### GET — Success `200 OK`

User payload **without** `tokens` (see Shared shapes). Avatar is never returned.

### PATCH — Request

JSON (`Content-Type: application/json`):

```json
{
  "display_name": "Ahmad Sarwar"
}
```

Multipart (`Content-Type: multipart/form-data`):

| Field | Required | Notes |
|---|---|---|
| `display_name` | no | max 120 |
| `avatar` | no | Image file; stored on the user model but **not** echoed in the response |

### PATCH — Success `200 OK`

Updated user payload (no tokens). Same shape as GET — no `avatar` URL/field.

### DELETE — Success `204 No Content`

Soft-delete: sets `deleted_at`, `is_active=false`.

After soft-delete:

| Situation | Result |
|---|---|
| Login with same credentials | `401` `ACCOUNT_DELETED` (message: `Invalid credentials.`) |
| Reuse of existing JWT on protected routes | `401` `NOT_AUTHENTICATED` (permission requires active, non-deleted user) |

### Errors

| HTTP | Code | Message |
|---|---|---|
| 401 | `NOT_AUTHENTICATED` | Missing/invalid JWT, or soft-deleted / inactive user |
| 400 | `INVALID` | `display_name` max 120, etc. |

---

## 8. Guest migrate

`POST /api/auth/guest/migrate/`  
**Auth:** JWT required

### Request

```json
{
  "session_key": "guest-abc-123"
}
```

### Success — `200 OK`

First merge:

```json
{
  "merged": true,
  "idempotent": false
}
```

Already merged:

```json
{
  "merged": true,
  "idempotent": true
}
```

If guest has `pending_save` and user lacks customer profile, a customer profile (+ prefs/notifications) is created.

### Errors

| HTTP | Code | Message |
|---|---|---|
| 401 | `NOT_AUTHENTICATED` | … |
| 400 | `INVALID` | Missing / blank `session_key` (serializer) |
| 400 | `SESSION_REQUIRED` | session_key is required. (service; rare on HTTP) |
| 404 | `SESSION_NOT_FOUND` | Guest session not found. |

---

# Me endpoints (`/api/me/`)

All require JWT (`IsAuthenticatedAndActive`). Soft-deleted or inactive users get `401` `NOT_AUTHENTICATED`.

**Mode-aware:** preferences / notifications read-write the customer or restaurant side based on `user.active_mode`.

---

## 9. Preferences

`GET /api/me/preferences/`  
`PATCH /api/me/preferences/`

### GET — customer mode — `200`

```json
{
  "side": "customer",
  "cuisines": ["BBQ", "Pizza"],
  "price_ranges": ["$", "$$"],
  "max_distance_km": 5,
  "city_id": null,
  "language": "en",
  "theme": "system"
}
```

### GET — restaurant mode — `200`

```json
{
  "side": "restaurant",
  "language": "en",
  "theme": "system"
}
```

### PATCH — customer request

```json
{
  "cuisines": ["Burgers", "Pakistani"],
  "price_ranges": ["$$", "$$$"],
  "max_distance_km": 10,
  "city_id": null,
  "language": "ur",
  "theme": "dark"
}
```

| Field | Allowed |
|---|---|
| `cuisines` | list of strings |
| `price_ranges` | `$` `$$` `$$$` `$$$$` |
| `max_distance_km` | 1–25 |
| `city_id` | int \| null |
| `language` | `en` \| `ur` |
| `theme` | `system` \| `light` \| `dark` |

Out-of-range `max_distance_km` normally fails the serializer as `400` `INVALID` (`min_value`/`max_value`) before the service `INVALID_DISTANCE` code is reached.

### PATCH — restaurant request

```json
{
  "language": "ur",
  "theme": "light"
}
```

### PATCH — Success `200`

Same shape as GET for that side.

### Errors

| HTTP | Code | Message |
|---|---|---|
| 401 | `NOT_AUTHENTICATED` | … |
| 403 | `CUSTOMER_PROFILE_REQUIRED` | Customer profile required. |
| 403 | `RESTAURANT_PROFILE_REQUIRED` | Restaurant profile required. |
| 400 | `INVALID_PRICE_RANGE` | Invalid price_ranges value. |
| 400 | `INVALID_DISTANCE` | max_distance_km must be between 1 and 25. (service; rare on HTTP) |
| 400 | `INVALID` | Invalid `language` / `theme` / types / out-of-range distance |

---

## 10. Notifications

`GET /api/me/notifications/`  
`PATCH /api/me/notifications/`

### GET — customer — `200`

```json
{
  "side": "customer",
  "enable_push_notification": true,
  "expiry_reminders": true,
  "new_deals_from_saved": true,
  "nearby_flash_deals": false,
  "new_videos_from_followed": true,
  "weekly_digest": false,
  "security_alerts": true
}
```

Defaults match the customer Notifications UI. **`security_alerts` is always `true`** (cannot be turned off).  
`enable_push_notification` defaults to `true` and can be toggled.

### GET — restaurant — `200`

```json
{
  "side": "restaurant",
  "enable_push_notification": true,
  "promo_status_alerts": true,
  "new_follower_alerts": true,
  "weekly_performance_digest": false
}
```

### PATCH — customer request

```json
{
  "enable_push_notification": false,
  "expiry_reminders": true,
  "new_deals_from_saved": false,
  "nearby_flash_deals": true,
  "new_videos_from_followed": true,
  "weekly_digest": true,
  "security_alerts": false
}
```

Note: sending `security_alerts: false` is **ignored**; response still has `security_alerts: true`.

### PATCH — restaurant request

```json
{
  "enable_push_notification": false,
  "promo_status_alerts": true,
  "new_follower_alerts": false,
  "weekly_performance_digest": true
}
```

### PATCH — Success `200`

Same shape as GET for that side. Example after a customer PATCH that tried to turn off security alerts:

```json
{
  "side": "customer",
  "enable_push_notification": false,
  "expiry_reminders": true,
  "new_deals_from_saved": false,
  "nearby_flash_deals": true,
  "new_videos_from_followed": true,
  "weekly_digest": true,
  "security_alerts": true
}
```

### Errors

| HTTP | Code | Message |
|---|---|---|
| 401 | `NOT_AUTHENTICATED` | … |
| 403 | `CUSTOMER_PROFILE_REQUIRED` | Customer profile required. |
| 403 | `RESTAURANT_PROFILE_REQUIRED` | Restaurant profile required. |
| 400 | `INVALID` | Invalid booleans |

---

## 11. List profiles

`GET /api/me/profiles/`  
**Auth:** JWT

`restaurant_id` is included **only** when `restaurant` is `true`.

### Success — `200`

Customer only:

```json
{
  "customer": true,
  "restaurant": false
}
```

Restaurant only:

```json
{
  "customer": false,
  "restaurant": true,
  "restaurant_id": 1
}
```

Dual profile:

```json
{
  "customer": true,
  "restaurant": true,
  "restaurant_id": 1
}
```

### Errors

| HTTP | Code |
|---|---|
| 401 | `NOT_AUTHENTICATED` |

---

## 12. Add customer profile

`POST /api/me/customer-profile/`  
**Auth:** JWT  
**Body:** none (empty `{}` OK)

Used by restaurant-only users to add a customer profile.

### Success — `201 Created`

User me payload (no tokens). Seeds customer preference + notification settings.

### Errors

| HTTP | Code | Message |
|---|---|---|
| 401 | `NOT_AUTHENTICATED` | … |
| 409 | `CUSTOMER_PROFILE_EXISTS` | Customer profile already exists. |

---

## 13. Add restaurant profile

`POST /api/me/restaurants/`  
**Auth:** JWT

### Request

```json
{
  "name": "Burger House"
}
```

### Success — `201 Created`

Me payload + new `tokens` (mode set to `restaurant`). Seeds restaurant preference + notification settings.

### Errors

| HTTP | Code | Message |
|---|---|---|
| 401 | `NOT_AUTHENTICATED` | … |
| 400 | `RESTAURANT_NAME_REQUIRED` | name is required. |
| 400 | `INVALID` | Missing `name` |
| 409 | `RESTAURANT_PROFILE_EXISTS` | You already have a restaurant profile. |

---

## 13a. Get / update owned restaurant profile

`GET /api/me/restaurant/`  
`PATCH /api/me/restaurant/`  
**Auth:** JWT  
**Content-Type (PATCH):** `application/json`

Returns/updates the authenticated user’s restaurant. Logo/cover uploads stay on `POST /api/me/restaurant/branding/`.

### GET — Success `200`

```json
{
  "id": 1,
  "name": "Burger House",
  "slug": "burger-house",
  "short_description": "Best burgers in town",
  "cuisines": ["Burgers", "American"],
  "price_range": "$$",
  "logo": "https://…/restaurants/logos/logo.png",
  "cover": "https://…/restaurants/covers/cover.png",
  "primary_phone": "+923001112233",
  "whatsapp_number": "+923001112233",
  "use_different_whatsapp": false,
  "secondary_phone": "",
  "street_address": "12 Mall Road",
  "area": "Gulberg",
  "city_id": 1,
  "lat": "31.520400",
  "lng": "74.358700",
  "is_paused": false,
  "is_permanently_closed": false,
  "promo_default_radius_km": 5,
  "promo_default_duration_days": 3,
  "notify_on_promo_approval": true,
  "auto_request_promo_on_deal": false,
  "rating_avg": "0.0",
  "rating_count": 0,
  "setup_completeness_pct": 50
}
```

### PATCH — Request (all fields optional)

```json
{
  "name": "Burger House",
  "short_description": "Best burgers in town",
  "cuisines": ["Burgers", "American"],
  "price_range": "$$",
  "primary_phone": "+923001112233",
  "whatsapp_number": "+923001112233",
  "use_different_whatsapp": false,
  "secondary_phone": "",
  "street_address": "12 Mall Road",
  "area": "Gulberg",
  "city_id": 1,
  "lat": 31.5204,
  "lng": 74.3587,
  "is_paused": false,
  "promo_default_radius_km": 5,
  "promo_default_duration_days": 3,
  "notify_on_promo_approval": true,
  "auto_request_promo_on_deal": false
}
```

| Field | Notes |
|---|---|
| `cuisines` | max 3 strings |
| `price_range` | `$` `$$` `$$$` `$$$$` or `""` |
| phones | E.164 (e.g. `+92300…`); blank clears |
| `lat` / `lng` | set together; both null clears |

### PATCH — Success `200`

Same shape as GET.

### Errors

| HTTP | Code | Message |
|---|---|---|
| 401 | `NOT_AUTHENTICATED` | … |
| 403 | `RESTAURANT_REQUIRED` | Restaurant profile required. |
| 400 | `RESTAURANT_NAME_REQUIRED` | name is required. |
| 400 | `INVALID_CUISINES` | At most 3 cuisines are allowed. |
| 400 | `INVALID_PRICE_RANGE` | Invalid price_range value. |
| 400 | `INVALID_PHONE` | … |
| 400 | `INVALID_COORDINATES` | Both lat and lng are required together. |

---

## 13b. Add or update restaurant cover / logo

`POST /api/me/restaurant/branding/`  
**Auth:** JWT  
**Content-Type:** `multipart/form-data`

Add or replace the owned restaurant’s `cover` or `logo` image. Replaces the previous file when one already exists.

### Request (multipart)

| Field | Required | Description |
|---|---|---|
| `type` | yes | `cover` or `logo` |
| `image` | yes | Image file |

```
type=cover
image=<file>
```

```
type=logo
image=<file>
```

### Success — `200 OK`

```json
{
  "type": "cover",
  "restaurant": {
    "id": 1,
    "name": "Burger House",
    "logo": null,
    "cover": "http://localhost:6060/media/restaurants/covers/abc.jpg",
    "setup_completeness_pct": 33
  }
}
```

`logo` / `cover` are absolute URLs (R2 public URL when configured, otherwise the request host + `/media/...`) or `null`.

### Errors

| HTTP | Code | Message |
|---|---|---|
| 401 | `NOT_AUTHENTICATED` | … |
| 403 | `RESTAURANT_REQUIRED` | Restaurant profile required. |
| 400 | `INVALID` | Missing/invalid `type` or `image` |

---

## 14. Console access

`GET /api/me/console-access/`  
**Auth:** JWT

### Success — customer-only `200`

```json
{
  "can_switch": false,
  "restaurant": null
}
```

### Success — restaurant owner `200`

```json
{
  "can_switch": true,
  "restaurant": {
    "id": 1,
    "name": "Burger House",
    "setup_completeness_pct": 17
  }
}
```

### Errors

| HTTP | Code |
|---|---|
| 401 | `NOT_AUTHENTICATED` |

---

## 15. Switch to customer

`POST /api/me/switch-to-customer/`  
**Auth:** JWT  
**Body:** none

Get-or-creates `CustomerProfile` (+ prefs/notifications), sets `active_mode=customer`, returns me + **new tokens**.

### Success — `200 OK`

```json
{
  "id": 2,
  "phone_number": "+923001112233",
  "display_name": null,
  "active_mode": "customer",
  "profiles": {
    "customer": true,
    "restaurant": true,
    "platform_admin": false
  },
  "restaurant": {
    "id": 1,
    "name": "Burger House",
    "setup_completeness_pct": 17
  },
  "tokens": {
    "access": "...",
    "refresh": "..."
  }
}
```

### Errors

| HTTP | Code |
|---|---|
| 401 | `NOT_AUTHENTICATED` |

---

## 16. Switch to restaurant

`POST /api/me/switch-to-restaurant/`  
**Auth:** JWT

### Request

Body may be empty `{}`. Optional name when creating for the first time:

```json
{
  "restaurant_name": "Burger House"
}
```

If the user has **no** restaurant yet and `restaurant_name` is omitted, a shell is **auto-created** using:
1. `restaurant_name` if provided  
2. else `user.display_name`  
3. else `"My Restaurant"`

### Success — `200 OK` (first create)

```json
{
  "id": 1,
  "phone_number": "+923008452119",
  "display_name": "Ahmad",
  "active_mode": "restaurant",
  "profiles": {
    "customer": true,
    "restaurant": true,
    "platform_admin": false
  },
  "restaurant": {
    "id": 1,
    "name": "Ahmad",
    "setup_completeness_pct": 17
  },
  "needs_profile_update": true,
  "tokens": {
    "access": "...",
    "refresh": "..."
  }
}
```

`needs_profile_update: true` is returned **only when the restaurant profile is created in this request**. Frontend should navigate to Restaurant Profile to complete details.

### Success — `200 OK` (already has restaurant)

Same shape with `"needs_profile_update": false`. Never creates a second restaurant.

### Errors

| HTTP | Code | Message |
|---|---|---|
| 401 | `NOT_AUTHENTICATED` | … |
| 409 | `RESTAURANT_PROFILE_EXISTS` | You already have a restaurant profile. *(race on create)* |

---

## Endpoint index

| Method | Path | Auth |
|---|---|---|
| POST | `/api/auth/register/` | Public |
| POST | `/api/auth/login/` | Public |
| POST | `/api/auth/refresh/` | Public |
| POST | `/api/auth/logout/` | JWT |
| POST | `/api/auth/password/forgot/` | Public |
| POST | `/api/auth/password/reset/` | Public |
| GET | `/api/auth/me/` | JWT |
| PATCH | `/api/auth/me/` | JWT |
| DELETE | `/api/auth/me/` | JWT |
| POST | `/api/auth/guest/migrate/` | JWT |
| GET/PATCH | `/api/me/preferences/` | JWT (mode-scoped) |
| GET/PATCH | `/api/me/notifications/` | JWT (mode-scoped) |
| GET | `/api/me/profiles/` | JWT |
| POST | `/api/me/customer-profile/` | JWT |
| POST | `/api/me/restaurants/` | JWT |
| GET/PATCH | `/api/me/restaurant/` | JWT |
| POST | `/api/me/restaurant/branding/` | JWT |
| GET | `/api/me/console-access/` | JWT |
| POST | `/api/me/switch-to-customer/` | JWT |
| POST | `/api/me/switch-to-restaurant/` | JWT |

Interactive OpenAPI: `/api/docs/`
