# Tests: `deals`

**Package:** `tests/deals/`  
**Files:** `factories.py`, `test_public_deals_api.py`, `test_console_deals_api.py`

---

## Public

### `GET /deals/{id}/`

| Case | Type | Expect |
|---|---|---|
| Active deal → promo sheet payload + prefill_message | + | 200 |
| Expired deal → `promo_state=expired` + similar | + | 200 |
| Scheduled deal → `promo_state=scheduled` | + | 200 |
| Deleted / hidden deal | − | 404 (+ optional restaurant_id hint) |
| Deal of paused restaurant | − | 404 |

### `GET /deals/{id}/similar/`

| Case | Type | Expect |
|---|---|---|
| Returns other active deals nearby/same cuisine | + | 200 |
| Unknown id | − | 404 |

### `GET /restaurants/{id}/deals/`

| Case | Type | Expect |
|---|---|---|
| Lists active deals | + | 200 |
| Paused restaurant | − | 404 |

---

## Console

### `GET /console/deals/?segment=`

| Case | Type | Expect |
|---|---|---|
| `segment=active` | + | 200 |
| `segment=pending` (promo pending) | + | 200 |
| `segment=ended` | + | 200 |
| Invalid segment | − | 400 |
| Non-owner / no auth | − | 403 / 401 |

### `POST /console/deals/`

| Case | Type | Expect |
|---|---|---|
| Valid lines + deal_price &lt; items_total + media | + | 201, savings computed |
| `request_promotion` creates pending promo | + | 201 |
| auto_request_promo_on_deal without toggle | + | PromotionRequest created |
| deal_price ≥ items_total | − | 400 |
| No lines | − | 400 |
| Missing video/photos | − | 400 |
| ends_at ≤ starts_at | − | 400 |
| No auth / non-owner | − | 401 / 403 |

### `GET/PATCH/DELETE /console/deals/{id}/`

| Case | Type | Expect |
|---|---|---|
| GET/PATCH own deal | + | 200 |
| DELETE own ended/draft | + | 204 |
| Foreign deal | − | 403/404 |
| PATCH invalid price | − | 400 |

### `GET /console/deals/{id}/preview/`

| Case | Type | Expect |
|---|---|---|
| Matches customer serializer shape | + | 200 |
| Foreign deal | − | 403/404 |

---

## Factories

- `DealFactory` (+ lines, ready media)
- `PendingPromoDealFactory`
- `ExpiredDealFactory`
- `DealLineFactory`
