# Tests — Overview

Pytest suite layout and per-app **positive / negative** API cases for FoodApp.

**Master spec:** [`../BACKEND-SPEC.md`](../BACKEND-SPEC.md) §3.5  
**App docs:** [`../apps/`](../README.md)

---

## Target folder (in the Django repo)

```
tests/
├── __init__.py
├── conftest.py
├── accounts/
├── geo/
├── restaurants/
├── menu/
├── deals/
├── promotions/
├── mediahub/
├── feed/
├── discovery/
├── engagement/
└── analytics/
```

Each app folder: `__init__.py`, `factories.py`, `test_*_api.py`.

---

## Case catalogues (this folder)

| App | Doc |
|---|---|
| accounts | [accounts.md](accounts.md) |
| geo | [geo.md](geo.md) |
| restaurants | [restaurants.md](restaurants.md) |
| menu | [menu.md](menu.md) |
| deals | [deals.md](deals.md) |
| promotions | [promotions.md](promotions.md) |
| mediahub | [mediahub.md](mediahub.md) |
| feed | [feed.md](feed.md) |
| discovery | [discovery.md](discovery.md) |
| engagement | [engagement.md](engagement.md) |
| analytics | [analytics.md](analytics.md) |

---

## Conventions

### Positive vs negative

| Type | Meaning | Typical status |
|---|---|---|
| **Positive** | Happy path — valid auth, valid body, expected resource | 200 / 201 / 204 |
| **Negative** | Auth missing/wrong, validation fail, forbidden, not found, quota, conflict | 400 / 401 / 403 / 404 / 409 / 429 |

### Naming

```python
def test_register_customer_success(api_client): ...
def test_register_duplicate_phone_fails(api_client): ...
def test_console_menu_create_unauthorized(api_client): ...
def test_console_menu_create_quota_exceeded(owner_client): ...
```

### Shared `conftest.py` fixtures

```python
# suggested
api_client          # unauthenticated APIClient
user_factory / restaurant_factory
auth_headers(user)  # Bearer access
customer_client     # JWT customer (no restaurant)
owner_client        # JWT + owned restaurant
admin_client        # is_staff
session_key         # guest session
```

### Error assert helper

Always assert envelope:

```json
{ "error": { "code": "...", "message": "...", "details": {} } }
```

### Run

```bash
pytest tests/ -q
pytest tests/accounts/ -q
pytest tests/feed/test_feed_api.py -k success
```

---

## Minimum coverage rule

For **every** endpoint listed in app docs:

1. At least **one positive** test  
2. At least **one negative** test (prefer: unauthenticated if protected, plus validation or 404)  
3. Owner-only routes: also **other user’s token → 403**
