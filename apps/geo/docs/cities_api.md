# Cities API

**Base:** `/api/cities/`

Public city list for the location picker, plus staff CRUD.

## Model

| Field | Type |
|---|---|
| `id` | int PK |
| `name` | unique string |
| `is_active` | bool (default true) |
| `created_at` / `updated_at` | datetime |

## Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/cities/` | Public | Active cities, order by `id` |
| GET | `/api/cities/{id}/` | Public | Detail |
| POST | `/api/cities/` | Admin JWT (`IsAdminRole`) | Create |
| PATCH | `/api/cities/{id}/` | Admin JWT (`IsAdminRole`) | Update |
| DELETE | `/api/cities/{id}/` | Admin JWT (`IsAdminRole`) | Delete |
| GET | `/api/cities/picker/` | Public | Popular list + live restaurant counts |
| GET | `/api/cities/search/?q=` | Public | Name contains search |

### Picker response

```json
{
  "popular": [
    { "id": 1, "name": "Karachi", "restaurant_count": 12 },
    { "id": 2, "name": "Lahore", "restaurant_count": 8 }
  ]
}
```

`restaurant_count` counts restaurants that are not paused and not permanently closed.

### Seed

```bash
python manage.py seed_cities
```

Inserts (idempotent): Karachi, Lahore, Islamabad, Faisalabad, Multan.

## Explore / Feed geo params

| Param | Notes |
|---|---|
| `city_id` | Active city PK |
| `city` | Active city name (case-insensitive) |

If both are sent, `city_id` wins. Response meta echoes `city_id` and `city` (name).
Unknown / inactive → `404 CITY_NOT_FOUND`.
