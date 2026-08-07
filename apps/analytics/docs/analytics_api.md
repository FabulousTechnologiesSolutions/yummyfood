# Analytics API

## `POST /api/analytics/event/`

Public (`AllowAny`). Optional JWT for per-user rows.

### Body

```json
{
  "event_model": "item",
  "resource_id": 123,
  "event_type": "detail_view"
}
```

| Field | Values |
|---|---|
| `event_model` | `item` \| `deal` |
| `event_type` | `detail_view` \| `call` \| `whatsapp` \| `share` \| `save` \| `follow` \| `direction` |

`impression` is **server-only** (Explore serve) → `400 IMPRESSION_SERVER_ONLY`.

### Effects

- Upserts anonymous `ResourceAnalytics` (ranking score)
- If authenticated, also per-user row
- If active `FeaturedCampaign` window, bumps campaign counters
- Recalculates `engagement_score` from `EXPLORE_ENGAGEMENT_WEIGHTS`

### Response

```json
{ "ok": true, "engagement_score": 12.4 }
```
