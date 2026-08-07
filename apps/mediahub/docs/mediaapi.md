# Mediahub restaurant upload API

Upload/presign helpers live in `apps/mediahub`. Menu item / deal create attaches media via URLs after upload — see also [`apps/restaurants/docs/menu_deals_api.md`](../../restaurants/docs/menu_deals_api.md).

**Auth (all endpoints below):** `Authorization: Bearer <access_jwt>` — requires restaurant ownership **and** `active_mode=restaurant` (`IsRestaurantOwner` + `IsRestaurantMode`). Dual-profile users in customer mode receive `403 RESTAURANT_MODE_REQUIRED`.

**Base prefix:** `/api/restaurant/`

**Error envelope:**

```json
{
  "error": {
    "code": "INVALID_UPLOAD_SIZE",
    "message": "byte_size must be between 1 and 104857600.",
    "details": {}
  }
}
```

---

## Shared shapes

### ContentMedia object (returned on menu item / deal responses)

Images (before/without HLS processing):

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "type": "image",
  "url": "/media/restaurants/1/items/9/media/a1b2…/cover.jpg",
  "is_cover": true,
  "order_index": 0,
  "processing_status": "",
  "duration": null,
  "thumbnail_url": "",
  "hls_master_url": "",
  "resolutions": []
}
```

Video after Celery HLS processing succeeds:

```json
{
  "id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
  "type": "video",
  "url": "/media/restaurants/1/items/9/media/bbbb…/clip.mp4",
  "is_cover": false,
  "order_index": 2,
  "processing_status": "ready",
  "duration": 24.5,
  "thumbnail_url": "/media/restaurants/1/items/9/video/bbbb…/thumbnail.jpg",
  "hls_master_url": "/media/restaurants/1/items/9/video/bbbb…/hls/master.m3u8",
  "resolutions": [
    {
      "quality": "720p",
      "height": 720,
      "width": 1280,
      "bandwidth": 2928000,
      "hlsKey": "restaurants/1/items/9/video/bbbb…/hls/720p/index.m3u8",
      "hlsUrl": "/media/restaurants/1/items/9/video/bbbb…/hls/720p/index.m3u8"
    }
  ]
}
```

| Field | Type | Notes |
|---|---|---|
| `id` | UUID string | `ContentMedia` primary key |
| `type` | string | `image` \| `video` |
| `url` | string | Public/original file URL |
| `is_cover` | bool | Images only; at most one cover per entity |
| `order_index` | int | Display order |
| `processing_status` | string | `""` \| `pending` \| `processing` \| `ready` \| `failed` |
| `duration` | float \| null | Seconds; set when video processing finishes |
| `thumbnail_url` | string | Video poster |
| `hls_master_url` | string | HLS master playlist |
| `resolutions` | array | Per-quality HLS entries |

### Media input (on menu item / deal create & update)

Sent as `media: [...]` on restaurant menu/deal APIs — **not** a standalone mediahub endpoint. Client uploads files first (presign → PUT), then passes URLs/keys.

**New uploads:**

```json
[
  {
    "type": "image",
    "url": "https://pub-xxx.r2.dev/uploads/tmp/1/abc_cover.jpg",
    "is_cover": true
  },
  {
    "type": "image",
    "url": "uploads/tmp/1/def_side.jpg"
  },
  {
    "type": "video",
    "url": "uploads/tmp/1/walk.mp4"
  }
]
```

`url` may be a full public URL or a bare storage key (`uploads/tmp/{restaurant_id}/…`).

**Keep existing rows on update** (omit an id → that media is deleted):

```json
[
  {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "type": "image",
    "is_cover": true
  },
  {
    "id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    "type": "video"
  },
  {
    "type": "image",
    "url": "uploads/tmp/1/new.jpg"
  }
]
```

| Field | Required | Notes |
|---|---|---|
| `type` | yes | `image` \| `video` |
| `url` | for new rows | ignored when `id` is present |
| `id` | update keep | existing `ContentMedia` UUID |
| `is_cover` | no | images only; at most one |

**Attach rules:** ≥1 image, exactly 1 video. If no cover is flagged, the first image becomes cover. Max video duration **60s** (enforced when processing completes).

### Resolution object (inside video `resolutions`)

```json
{
  "quality": "480p",
  "height": 480,
  "width": 854,
  "bandwidth": 1528000,
  "hlsKey": "restaurants/1/items/9/video/{media_id}/hls/480p/index.m3u8",
  "hlsUrl": "/media/restaurants/1/items/9/video/{media_id}/hls/480p/index.m3u8"
}
```

---

## Upload flow (client)

```
1. POST /api/restaurant/uploads/presign/     → key, upload_url, public_url
2. PUT  upload_url  (binary file)            → store object
3. POST /api/restaurant/menu-items|deals/    → media[].url = public_url or key
4. (optional) DELETE orphan keys / media rows
```

Storage layout after attach:

- Original: `restaurants/{restaurant_id}/{items\|deals}/{entity_id}/media/{media_id}/…`
- HLS + thumb: `restaurants/{restaurant_id}/{items\|deals}/{entity_id}/video/{media_id}/…`

---

## `POST /api/restaurant/uploads/presign/`

Request a temporary object key and upload URL. Does **not** upload bytes.

### Request

```json
{
  "filename": "burger.jpg",
  "content_type": "image/jpeg",
  "byte_size": 245678,
  "kind": "image"
}
```

| Field | Required | Type | Notes |
|---|---|---|---|
| `filename` | yes | string | max 255; used in generated key |
| `content_type` | yes | string | e.g. `image/jpeg`, `video/mp4` |
| `byte_size` | yes | int | ≥ 1; ≤ `MAX_UPLOAD_BYTES` (default 100 MiB) |
| `kind` | no | string | hint only (`image`, `video`, …); echoed back |

### Response `200`

**R2 / production** (`USE_LOCAL_MEDIA` false):

```json
{
  "key": "uploads/tmp/1/a1b2c3d4e5f6_burger.jpg",
  "upload_url": "https://….r2.cloudflarestorage.com/…?X-Amz-Algorithm=…",
  "public_url": "https://pub-xxx.r2.dev/uploads/tmp/1/a1b2c3d4e5f6_burger.jpg",
  "expires_in": 3600,
  "content_type": "image/jpeg",
  "kind": "image"
}
```

**Local / testing** (`USE_LOCAL_MEDIA=true`):

```json
{
  "key": "uploads/tmp/1/a1b2c3d4e5f6_burger.jpg",
  "upload_url": "/api/restaurant/uploads/local/?key=uploads/tmp/1/a1b2c3d4e5f6_burger.jpg",
  "public_url": "/media/uploads/tmp/1/a1b2c3d4e5f6_burger.jpg",
  "expires_in": 3600,
  "content_type": "image/jpeg",
  "kind": "image"
}
```

| Field | Notes |
|---|---|
| `key` | Object key under `uploads/tmp/{restaurant_id}/` |
| `upload_url` | Where the client `PUT`s the file |
| `public_url` | URL (or path) to pass later in `media[].url` |
| `expires_in` | Seconds until R2 presign expires (local still returns the value) |

### Client upload after presign

**R2:** HTTP `PUT` to `upload_url` with body = file bytes and header `Content-Type` matching presign.

**Local:** `PUT` or `POST` to `upload_url` (see [Local upload](#put--post-apirestaurantuploadslocal) below).

### Errors

| Code | Status | When |
|---|---|---|
| `INVALID_UPLOAD_SIZE` | 400 | `byte_size` out of range |
| `RESTAURANT_MODE_REQUIRED` | 403 | `active_mode` ≠ restaurant |
| `RESTAURANT_REQUIRED` | 403 | no restaurant profile |
| (DRF validation) | 400 | missing/invalid fields |

---

## `PUT` / `POST /api/restaurant/uploads/local/`

Dev/test upload target when `USE_LOCAL_MEDIA=true`. Not used in production R2 mode.

### Query / body

| Param | Required | Notes |
|---|---|---|
| `key` | yes | Query `?key=` or form field; must start with `uploads/tmp/{restaurant_id}/` |

### Request body

One of:

1. Multipart: field `file` or `upload` with the binary
2. Raw body: entire `request.body` written as the object

Example multipart:

```http
PUT /api/restaurant/uploads/local/?key=uploads/tmp/1/a1b2_burger.jpg
Authorization: Bearer <token>
Content-Type: multipart/form-data; boundary=----bound

------bound
Content-Disposition: form-data; name="file"; filename="burger.jpg"
Content-Type: image/jpeg

<binary>
------bound--
```

### Response `200`

```json
{
  "key": "uploads/tmp/1/a1b2_burger.jpg",
  "public_url": "/media/uploads/tmp/1/a1b2_burger.jpg"
}
```

### Errors

| Code | Status | When |
|---|---|---|
| `KEY_REQUIRED` | 400 | missing `key` |
| `KEY_FORBIDDEN` | 403 | key not under this restaurant’s tmp prefix |
| `FILE_REQUIRED` | 400 | no multipart file and empty body |
| `RESTAURANT_MODE_REQUIRED` | 403 | wrong active mode |
| `RESTAURANT_REQUIRED` | 403 | no restaurant |

---

## `DELETE /api/restaurant/uploads/`

Delete a storage object by key (orphan / temp cleanup). Does **not** require a `ContentMedia` DB row.

### Request

```json
{
  "key": "uploads/tmp/1/a1b2c3d4e5f6_burger.jpg"
}
```

| Field | Required | Notes |
|---|---|---|
| `key` | yes | Must start with `uploads/tmp/{restaurant_id}/` **or** `restaurants/{restaurant_id}/` |

### Response `200`

```json
{
  "deleted": true,
  "key": "uploads/tmp/1/a1b2c3d4e5f6_burger.jpg"
}
```

### Errors

| Code | Status | When |
|---|---|---|
| `KEY_REQUIRED` | 400 | empty key |
| `KEY_FORBIDDEN` | 403 | key outside allowed prefixes |
| `RESTAURANT_MODE_REQUIRED` | 403 | wrong active mode |
| `RESTAURANT_REQUIRED` | 403 | no restaurant |

---

## `DELETE /api/restaurant/media/{media_id}/`

Delete a `ContentMedia` row and its storage objects (original file, thumbnail, HLS prefix).  
`media_id` is a UUID.

### Request

No body.

```http
DELETE /api/restaurant/media/a1b2c3d4-e5f6-7890-abcd-ef1234567890/
Authorization: Bearer <token>
```

### Response `200`

```json
{
  "deleted": true,
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

### Cover reassignment

If the deleted row was an image with `is_cover=true`, and other images remain on that menu item / deal, the **newest remaining image** is set as cover.

### Errors

| Code | Status | When |
|---|---|---|
| `MEDIA_NOT_FOUND` | 404 | no media for this id owned by the restaurant |
| `RESTAURANT_MODE_REQUIRED` | 403 | wrong active mode |
| `RESTAURANT_REQUIRED` | 403 | no restaurant |

---

## Video processing (background)

Triggered automatically when a menu item or deal is created/updated with a new video `ContentMedia` (`is_feed_video=true`).

Celery task: `process_content_video`

| Step | Result |
|---|---|
| Download original | from storage key |
| Probe | width, height, duration |
| Reject if `duration` > 60s | status → `failed` after retries |
| Thumbnail @ 2s | `…/video/{media_id}/thumbnail.jpg` |
| HLS ladder | 240p–1080p (source-capped), fMP4 segments |
| Master playlist | `…/video/{media_id}/hls/master.m3u8` |

Status flow: `pending` → `processing` → `ready` \| `failed` (up to 3 retries).

No push notification on ready/failed in this phase (logged only). Clients poll menu item / deal detail (or list) for updated `media[].processing_status`.

### Storage keys (video outputs)

```
restaurants/{restaurant_id}/{items|deals}/{entity_id}/video/{media_id}/thumbnail.jpg
restaurants/{restaurant_id}/{items|deals}/{entity_id}/video/{media_id}/hls/master.m3u8
restaurants/{restaurant_id}/{items|deals}/{entity_id}/video/{media_id}/hls/{quality}/index.m3u8
restaurants/{restaurant_id}/{items|deals}/{entity_id}/video/{media_id}/hls/{quality}/init.mp4
restaurants/{restaurant_id}/{items|deals}/{entity_id}/video/{media_id}/hls/{quality}/segment000.m4s
…
```

---

## Media attach errors (via menu / deal APIs)

When creating or updating menu items / deals with `media[]`, these codes may appear:

| Code | Status | When |
|---|---|---|
| `MEDIA_REQUIRED` | 400 | no media, or no images |
| `VIDEO_REQUIRED` | 400 | not exactly one video |
| `INVALID_COVER` | 400 | more than one `is_cover` |
| `INVALID_MEDIA_URL` | 400 | cannot parse `url` into a storage key |

Full menu/deal payloads: [`apps/restaurants/docs/menu_deals_api.md`](../../restaurants/docs/menu_deals_api.md).

---

## Endpoint summary

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/restaurant/uploads/presign/` | Get tmp key + upload URL |
| `PUT`/`POST` | `/api/restaurant/uploads/local/` | Local file upload (dev) |
| `DELETE` | `/api/restaurant/uploads/` | Delete object by key |
| `DELETE` | `/api/restaurant/media/{uuid}/` | Delete ContentMedia + files |
