# Tests: `mediahub`

**Package:** `tests/mediahub/`  
**Files:** `factories.py`, `test_uploads_api.py`, `test_public_media_api.py`

---

## Uploads (owner)

### `POST /console/uploads/init/`

| Case | Type | Expect |
|---|---|---|
| Init photo upload | + | 201, upload_url + upload_id |
| Init video upload | + | 201 |
| Unsupported content_type | − | 400 |
| byte_size over limit | − | 400 |
| No auth / non-owner | − | 401 / 403 |

### `POST /console/uploads/{id}/complete/`

| Case | Type | Expect |
|---|---|---|
| Complete valid photo → ready Photo id | + | 200 |
| Complete valid video ≤60s → Video processing/ready | + | 200 |
| Video duration &gt; 60s | − | 400 |
| Complete unknown upload | − | 404 |
| Complete other owner’s upload | − | 403 |
| Complete already cancelled | − | 409 |

### `DELETE /console/uploads/{id}/`

| Case | Type | Expect |
|---|---|---|
| Cancel pending upload | + | 204 |
| Foreign upload | − | 403 |
| Unknown id | − | 404 |

---

## Public media

### `GET /restaurants/{id}/photos/`

| Case | Type | Expect |
|---|---|---|
| Derived from item/deal photos | + | 200 |
| Paused restaurant | − | 404 |

### `GET /restaurants/{id}/videos/`

| Case | Type | Expect |
|---|---|---|
| Only `ready` videos | + | 200 |
| Processing videos excluded | + | not listed |
| Paused restaurant | − | 404 |

### `GET /videos/{id}/`

| Case | Type | Expect |
|---|---|---|
| Ready video detail | + | 200 |
| Removed / failed | − | 404 |
| Unknown | − | 404 |

---

## Factories

- `UploadSessionFactory`
- `PhotoFactory` (ready)
- `VideoFactory` (ready, duration 30)
- `ProcessingVideoFactory`
- `LongVideoFactory` (for reject path via mock duration)
