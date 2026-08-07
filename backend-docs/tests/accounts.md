# Tests: `accounts`

**Package:** `tests/accounts/`  
**Files:**  
`factories.py`, `test_auth_api.py`, `test_mode_switch_api.py`, `test_profile_api.py`, `test_preferences_api.py`, `test_password_api.py`

**Base:** `/api/auth/`, `/api/me/`  
**Style:** ViewSet / `@action` where applicable; auth endpoints may be `APIView`.

**Active mode:** stored on `User` (`active_mode` / `last_active_mode`) **and** in JWT claims. Backend trusts the token for current mode.

---

## Registration — `POST /auth/register/`

Body: `phone_number`, `password`, `role` / `signup_intent` (`customer` | `restaurant`), optional `restaurant_name`, optional `session_key`.

After success: user is **logged in** — response includes tokens (same shape as login).

| Case | Type | Expect |
|---|---|---|
| Customer: phone + password ≥8 + role=customer | + | 201, tokens, `profiles.customer=true`, `profiles.restaurant=false`, `active_mode=customer`, JWT claim `active_mode=customer` |
| Restaurant: phone + password + role=restaurant + `restaurant_name` | + | 201, tokens, `profiles.restaurant=true`, `restaurant` object, `active_mode=restaurant`, JWT claim set |
| Register with `session_key` migrates guest data | + | 201, pending save/history merged |
| Restaurant without `restaurant_name` | − | 400 |
| Customer with `restaurant_name` ignored or rejected | +/− | 201 ignore **or** 400 — document one policy |
| Missing phone / password / role | − | 400 |
| Password &lt; 8 chars | − | 400 |
| Duplicate phone | − | 400 / 409 |
| Invalid phone format | − | 400 |

---

## Login — `POST /auth/login/`

| Case | Type | Expect |
|---|---|---|
| Valid credentials | + | 200, access + refresh |
| Response includes **last active mode** restored as `active_mode` | + | e.g. previously restaurant → `active_mode=restaurant` |
| JWT access token contains `active_mode` claim matching response | + | decode token and assert |
| Customer-only user who last used customer | + | `active_mode=customer` |
| User with both profiles; last mode restaurant | + | opens restaurant mode |
| Login merges guest `session_key` | + | 200, guest data attached |
| Wrong password | − | 400/401 generic message |
| Unknown phone | − | 400/401 (same message) |
| Soft-deleted user | − | 401 |
| Missing fields | − | 400 |

---

## Logout — `POST /auth/logout/`

| Case | Type | Expect |
|---|---|---|
| Authenticated logout | + | 200/204, refresh blacklisted |
| **Before** invalidating token, persist `last_active_mode` from current token/user | + | DB `last_active_mode` == mode at logout |
| Next login restores that mode | + | login `active_mode` matches what was saved on logout |
| Logout while in customer mode → next login customer | + | |
| Logout while in restaurant mode → next login restaurant | + | |
| No auth | − | 401 |
| Missing refresh token (if required) | − | 400 |

---

## Token refresh — `POST /auth/refresh/`

| Case | Type | Expect |
|---|---|---|
| Valid refresh | + | 200, new access; **`active_mode` claim preserved** from user record |
| After mode switch, refresh issues token with **new** `active_mode` | + | claim matches DB |
| Invalid / expired refresh | − | 401 |
| Blacklisted refresh after logout | − | 401 |

---

## Profile switching (two separate `@action` methods)

Suggested routes (adjust to match ViewSet):

- `POST /api/me/switch-to-customer/` (or `@action` `switch_to_customer`)
- `POST /api/me/switch-to-restaurant/` (or `@action` `switch_to_restaurant`)

Optional: `GET /api/me/active-mode/` — current mode from token/user.

### Get current active mode

| Case | Type | Expect |
|---|---|---|
| GET me / active-mode while customer | + | `active_mode=customer` |
| GET me / active-mode while restaurant | + | `active_mode=restaurant` |
| No auth | − | 401 |

### `switch_to_customer` — get-or-create

| Case | Type | Expect |
|---|---|---|
| User already has CustomerProfile | + | 200, activate existing; `active_mode=customer`; new/rotated access token with claim |
| Restaurant-only user, **no** CustomerProfile yet | + | 200, **CustomerProfile** created, `active_mode=customer`, token updated |
| Already in customer mode (idempotent) | + | 200, still customer |
| Persist `last_active_mode=customer` on user | + | DB updated |
| No auth | − | 401 |

### `switch_to_restaurant` — get-or-create

| Case | Type | Expect |
|---|---|---|
| User already has Restaurant profile | + | 200, activate existing; `active_mode=restaurant`; token claim updated |
| Customer-only user, **no** Restaurant yet + body includes `restaurant_name` | + | 200/201, Restaurant **created**, mode=restaurant, token updated |
| Customer-only, no Restaurant, **missing** `restaurant_name` when required | − | 400 (prompt/complete name) **or** 200 with incomplete restaurant + checklist flag — assert chosen policy |
| Switching does **not** fail only because profile was missing | + | get-or-create succeeds when name provided |
| User already has one restaurant; switch again | + | reuses same restaurant (never creates a second) |
| Attempt to attach second restaurant via switch | − | must not create second; still one `user.restaurant` |
| Persist `last_active_mode=restaurant` | + | DB updated |
| No auth | − | 401 |

### Token claim after switch

| Case | Type | Expect |
|---|---|---|
| After switch, old access token rejected **or** still valid until expiry but new token returned | + | document policy; prefer return new access with updated `active_mode` |
| Backend reads mode from token claims (not client header) | + | protected endpoint behaves by claim |
| Client sending wrong mode header ignored | + | token wins |

---

## Password reset

### Step 1 — `POST /auth/password/forgot/` (send OTP)

| Case | Type | Expect |
|---|---|---|
| Existing phone → OTP sent | + | 200 (generic message OK) |
| Unknown phone → no leak | + | 200 same generic (prefer) |
| Invalid phone | − | 400 |
| Resend within cooldown | − | 429 or 400 with wait |

### Step 2 — `POST /auth/password/reset/` (verify OTP + set password)

Body: `phone_number`, `otp`, `new_password`, `confirm_password`.

| Case | Type | Expect |
|---|---|---|
| Valid OTP + matching new/confirm passwords ≥8 | + | 200, can login with new password |
| `new_password` ≠ `confirm_password` | − | 400 |
| Wrong OTP | − | 400 |
| Expired OTP | − | 400 |
| OTP used twice | − | 400 |
| Weak password | − | 400 |
| Missing fields | − | 400 |

---

## Profile management (mode-scoped)

### Customer mode — update customer profile only

| Case | Type | Expect |
|---|---|---|
| `active_mode=customer`: PATCH personal profile (display_name, avatar) | + | 200 |
| `active_mode=customer`: PATCH restaurant profile fields | − | 403 (wrong mode) |
| No auth | − | 401 |

### Restaurant mode — personal + restaurant profile

| Case | Type | Expect |
|---|---|---|
| `active_mode=restaurant`: PATCH personal profile | + | 200 |
| `active_mode=restaurant`: PATCH restaurant profile (name, description, etc.) | + | 200 |
| `active_mode=customer` cannot update restaurant | − | 403 |
| Token without restaurant profile but mode=restaurant | − | 403 / force switch create first |
| No auth | − | 401 |

### `GET /auth/me/`

| Case | Type | Expect |
|---|---|---|
| Returns `active_mode`, `profiles`, `restaurant` (or null) | + | 200 |
| Reflects mode from token | + | matches JWT claim |
| No token | − | 401 |

---

## Preferences — `GET/PATCH /me/preferences/`

Configure/update all app preferences (cuisines, price ranges, max distance, language, theme, etc.).

| Case | Type | Expect |
|---|---|---|
| GET preferences (customer profile exists) | + | 200 |
| PATCH all preference fields | + | 200, persisted |
| PATCH partial preferences | + | 200 |
| max_distance_km out of 1–25 | − | 400 |
| Invalid cuisine / price_range value | − | 400 |
| Restaurant-only user without CustomerProfile | − | 403 **or** auto-create customer on first prefs access — assert policy |
| No auth | − | 401 |

### Notifications — `GET/PATCH /me/notifications/` (if part of prefs surface)

| Case | Type | Expect |
|---|---|---|
| GET notification settings | + | 200 |
| PATCH toggles | + | 200 |
| `security_alerts=false` | − | 400 or ignored (always on) |
| No auth | − | 401 |

---

## Soft-delete (optional retention)

| Case | Type | Expect |
|---|---|---|
| `DELETE /auth/me/` soft-delete | + | 204, cannot login |
| No auth | − | 401 |

---

## Guest migrate — `POST /auth/guest/migrate/`

| Case | Type | Expect |
|---|---|---|
| Valid `session_key` | + | 200 merged |
| Already merged | + | 200 idempotent |
| No auth | − | 401 |
| Missing / unknown session | − | 400 / 404 |

---

## End-to-end mode persistence scenarios

| Case | Type | Expect |
|---|---|---|
| Register customer → use app → switch to restaurant (get-or-create) → logout → login | + | login returns `active_mode=restaurant` |
| Register restaurant → switch to customer (get-or-create) → logout → login | + | login returns `active_mode=customer` |
| Never create a second restaurant across switches | + | still OneToOne `user.restaurant` |

---

## Factories (`factories.py`)

- `UserFactory` — with `CustomerProfile`, `active_mode=customer`, `last_active_mode=customer`
- `RestaurantOnlyUserFactory` — restaurant profile, no customer, `active_mode=restaurant`
- `BothProfilesUserFactory` — both profiles; configurable `active_mode`
- `AdminUserFactory`
- `GuestSessionFactory`
- `CustomerProfileFactory` / `RestaurantFactory` (or import from restaurants)
- `UserPreferenceFactory` / `NotificationSettingFactory`
- Helper: `access_token_for(user, active_mode=...)` asserting JWT claims
