# Tests: `engagement`

**Package:** `tests/engagement/`  
**Files:** `factories.py`, `test_saved_api.py`, `test_follow_api.py`, `test_like_api.py`, `test_report_api.py`

---

## Saved

### `GET /saved/?type=`

| Case | Type | Expect |
|---|---|---|
| `type=deals` lists saved deals sorted by soonest expiry | + | 200 |
| `type=places` / `items` / `videos` | + | 200 |
| Expired deals in expired group / flag | + | 200 |
| Invalid type | − | 400 |
| No auth | − | 401 |

### `POST /saved/`

| Case | Type | Expect |
|---|---|---|
| Save deal | + | 201 |
| Save restaurant / item / video | + | 201 |
| Idempotent re-save | + | 200/201 same unique |
| Guest no auth | − | 401 `AUTH_REQUIRED` + pending_action |
| Missing target ids | − | 400 |
| Unknown target | − | 404 |
| Mismatched target_type vs id | − | 400 |

### `DELETE /saved/{id}/`

| Case | Type | Expect |
|---|---|---|
| Unsave own | + | 204 |
| Unsave other user’s save | − | 403/404 |
| No auth | − | 401 |

---

## Follow

### `POST /follows/`

| Case | Type | Expect |
|---|---|---|
| Follow restaurant | + | 201 |
| Duplicate follow | + | 200 idempotent or 409 — pick one |
| Follow paused restaurant (optional allow) | +/− | document policy |
| No auth | − | 401 |
| Missing restaurant_id | − | 400 |
| Unknown restaurant | − | 404 |

### `DELETE /follows/{restaurant_id}/`

| Case | Type | Expect |
|---|---|---|
| Unfollow | + | 204 |
| Not following | − | 404 |
| No auth | − | 401 |

---

## Like

### `POST /videos/{id}/like/`

| Case | Type | Expect |
|---|---|---|
| Like as user | + | 200, like_count +1 |
| Unlike toggle | + | 200, count −1 |
| Guest with session_key | + | 200 |
| Unknown video | − | 404 |
| Removed video | − | 404 |

---

## Reports / not interested

### `POST /reports/`

| Case | Type | Expect |
|---|---|---|
| reason `not_interested` | + | 201 |
| reason `hide_restaurant` | + | 201 |
| reason `report_video` | + | 201 |
| Invalid reason | − | 400 |
| Missing video_id when required | − | 400 |

---

## Factories

- `SaveFactory`
- `FollowFactory`
- `LikeFactory`
- `ContentReportFactory`
