# Tests: `analytics`

**Package:** `tests/analytics/`  
**Files:** `factories.py`, `test_events_api.py`, `test_contact_api.py`, `test_console_analytics_api.py`

---

## Events

### `POST /events/`

| Case | Type | Expect |
|---|---|---|
| Batch video_view with session_key | + | 202/200 |
| Authenticated user events | + | 200, user FK set |
| Idempotent `client_event_id` | + | no duplicate rows |
| Empty events list | − | 400 |
| Invalid event_type | − | 400 |
| Missing session_key when anonymous | − | 400 |

---

## Contact

### `POST /contact/`

| Case | Type | Expect |
|---|---|---|
| `whatsapp_click` returns wa.me + logs event | + | 200 |
| `call_click` returns tel_uri | + | 200 |
| `directions_click` returns maps_uri | + | 200 |
| Prefill includes deal title | + | message contains label |
| Missing restaurant_id | − | 400 |
| Unknown restaurant | − | 404 |
| Invalid action | − | 400 |

---

## Console analytics

Ranges: `last_7_days` | `this_month` | `last_month` | `custom`

### `GET /console/analytics/overview/`

| Case | Type | Expect |
|---|---|---|
| Owner gets customers_reached = wa+call+directions | + | 200 |
| Deltas present | + | 200 |
| `range=custom` with start/end | + | 200 |
| Invalid range | − | 400 |
| custom missing dates | − | 400 |
| Non-owner / other restaurant header | − | 403 |
| No auth | − | 401 |
| No data yet | + | 200 empty-friendly zeros or nulls |

### `GET /console/analytics/funnel/`

| Case | Type | Expect |
|---|---|---|
| Stages video→…→contacts | + | 200 |
| Non-owner | − | 403 |

### `GET /console/analytics/content/`

| Case | Type | Expect |
|---|---|---|
| Top videos / promos / items | + | 200 |
| Non-owner | − | 403 |

### `GET /console/analytics/export/`

| Case | Type | Expect |
|---|---|---|
| `format=csv` file response | + | 200, content-type csv |
| `format=pdf` | + | 200 |
| Invalid format | − | 400 |
| Non-owner | − | 403 |

---

## Rollup task

| Case | Type | Expect |
|---|---|---|
| Events roll into AnalyticsDaily | + | row counts match |
| Idempotent re-run same day | + | no double count |

---

## Factories

- `EngagementEventFactory`
- `AnalyticsDailyFactory`
- Seed month of events for overview fixtures (25_400 style optional)
