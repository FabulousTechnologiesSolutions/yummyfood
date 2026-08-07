# App: `mediahub`

**Package:** `apps.mediahub`  
**Depends on:** `restaurants`  
**Purpose:** Photos, videos, upload sessions; attach to menu items / deals / restaurant branding.

---

## Responsibility

- Presigned / direct upload flow
- Validate image types and video duration ≤ 60s
- Transcode + poster generation (async)
- Derived restaurant photo gallery (read-only)
- Logo / cover can live on Restaurant model or here — prefer Restaurant fields for branding; item/deal media here

---

## File layout

```
apps/mediahub/
├── __init__.py
├── admin.py
├── apps.py
├── models.py
├── serializers.py
├── urls.py
├── views.py
├── services.py          # presign, validate, attach
└── tasks.py             # ffmpeg / transcode / poster
```

---

## Models

### `UploadSession`

| Field | Type |
|---|---|
| `id` | UUID |
| `restaurant` | FK |
| `uploaded_by` | FK User |
| `kind` | `photo` \| `video` |
| `status` | `pending` \| `uploading` \| `processing` \| `ready` \| `failed` \| `cancelled` |
| `storage_key` | CharField |
| `content_type` | CharField |
| `byte_size` | BigInteger |
| `error_message` | TextField |
| `created_at` / `completed_at` | |

### `Photo`

| Field | Type |
|---|---|
| `restaurant` | FK nullable |
| `menu_item` | FK nullable |
| `deal` | FK nullable |
| `file` | ImageField / URL |
| `aspect` | `1:1` \| `4:3` \| `16:9` \| `free` |
| `is_cover` | bool |
| `position` | int |
| `upload_status` | `uploading` \| `ready` \| `failed` |

### `Video`

| Field | Type | Notes |
|---|---|---|
| `restaurant` | FK | |
| `menu_item` | FK / OneToOne nullable | |
| `deal` | FK nullable | |
| `file` / `hls_url` | | |
| `poster` | ImageField | |
| `duration_seconds` | int | **max 60** |
| `caption` | TextField | |
| `hashtags` | ArrayField | parsed |
| `view_count` / `like_count` | int | |
| `is_promoted` | bool | set by promotions |
| `status` | `processing` \| `ready` \| `failed` \| `removed` | |

**Rule:** Published product/deal needs exactly one ready video.

---

## API endpoints

| Method | Path | Auth |
|---|---|---|
| POST | `/api/console/uploads/init/` | Owner |
| POST | `/api/console/uploads/{id}/complete/` | Owner |
| DELETE | `/api/console/uploads/{id}/` | Owner |
| GET | `/api/restaurants/{id}/photos/` | Public (derived) |
| GET | `/api/restaurants/{id}/videos/` | Public |
| GET | `/api/videos/{id}/` | Public / Optional |

### Init example

```json
POST /console/uploads/init/
{
  "kind": "video",
  "filename": "burger.mp4",
  "content_type": "video/mp4",
  "byte_size": 12000000
}
```

```json
{
  "upload_id": "...",
  "upload_url": "https://s3.../presigned",
  "fields": {}
}
```

### Complete

```json
POST /console/uploads/{id}/complete/
{}
```

Validates mime, size, duration; enqueues processing; returns `photo` or `video` id when ready (or `processing`).

---

## Asset rules

| Asset | Aspect | Limits |
|---|---|---|
| Item/deal photos | 1:1 preferred | ≥1 to publish; max ~10 MB |
| Item/deal video | vertical preferred | Exactly 1; ≤ 60s; ~100 MB |
| Logo | 1:1 | on Restaurant |
| Cover | 16:9 | on Restaurant |

Allowed: `image/jpeg`, `image/png`, `image/webp`, `video/mp4`, `video/quicktime`.

Storage paths:

```
media/restaurants/{id}/items/{item_id}/
media/restaurants/{id}/deals/{deal_id}/
media/restaurants/{id}/videos/{video_id}/
```

---

## Business rules

1. Gallery = union of item + deal photos for restaurant (no separate library upload in Phase 1).
2. Offline clients may queue; support cancel + retry.
3. Failed processing → `status=failed`, Retry via new complete or re-init.
4. Feed only serves `status=ready` videos.
5. Removing video used by published item should block or force hide item.

---

## Tests checklist

- [ ] Init returns upload URL
- [ ] Complete rejects video &gt; 60s
- [ ] Processing task sets ready + poster
- [ ] Cancel deletes incomplete object
- [ ] Public gallery derived correctly
