# Tests: `restaurants` (Restaurant Module)

**Package:** `tests/restaurants/`  
**Files:**  
`factories.py`, `test_restaurant_api.py`, `test_menu_api.py`, `test_deal_api.py`, `test_promotion_api.py`

**Services:** `RestaurantService`, `ClaimService`, `ConsoleSettingsService` (+ menu/deal/promotion services called from console flows)  
**Style:** `ModelViewSet` → service methods

**Scope of this module**

1. Restaurant profile (limited fields)  
2. Menu categories + menu items + sizes + media  
3. Deals  
4. Promotion requests (restaurant / item / deal)

---

## Restaurant model — fields under test

Only these fields are required on `Restaurant`:

| Field | Notes |
|---|---|
| `name` | required |
| `description` | |
| `logo` | image |
| `cover_image` | image |
| `primary_phone` | |
| `whatsapp_number` | |
| `city` | FK |
| `latitude` | separate field |
| `longitude` | separate field |

`owner` OneToOne → User (at most one restaurant per user).

---

## Restaurant APIs

### Create — `POST /api/me/restaurants/` (or register-as-restaurant / switch get-or-create)

| Case | Type | Expect |
|---|---|---|
| Create with `name` (+ optional other fields) | + | 201, `owner` set, single restaurant |
| Create with all basic fields (phones, city, lat/lng, logo, cover) | + | 201, all persisted |
| Missing `name` | − | 400 |
| User already has a restaurant | − | **409** `RESTAURANT_PROFILE_EXISTS` |
| Invalid lat/lng | − | 400 |
| Invalid city id | − | 400 |
| No auth | − | 401 |

### Public retrieve — `GET /api/restaurants/{id}/`

| Case | Type | Expect |
|---|---|---|
| Active restaurant returns name, description, logo, cover, phones, city, lat, lng | + | 200 |
| Unknown id | − | 404 |
| Paused / hidden from discovery (if pause exists) | − | 404/410 |

### Console get/update — `GET/PATCH /api/console/restaurant/`

| Case | Type | Expect |
|---|---|---|
| Owner GET own restaurant | + | 200 |
| Owner PATCH description, phones, city, lat, lng | + | 200 |
| Owner PATCH logo / cover | + | 200 |
| Non-owner / no restaurant profile | − | 403 |
| No auth | − | 401 |
| PATCH empty name | − | 400 |

### Claim (if still in scope)

| Case | Type | Expect |
|---|---|---|
| Claim unclaimed listing + verify OTP | + | 200, ownership OneToOne |
| Claimant already has restaurant | − | 409 |
| Wrong OTP | − | 400 |
| No auth | − | 401 |

---

## Menu categories

### Defaults (command / seeder)

Seeder / `populate` must create:

Fast Food, Pakistani, Continental, Chinese, BBQ, Pizza, Burger, Wraps, Pasta, Rice, Salad, Beverages, Desserts, Cakes, Deals, Add-ons

| Case | Type | Expect |
|---|---|---|
| After seed, all default category names exist | + | count/names match list |
| Seeder idempotent (run twice) | + | no duplicates |
| New restaurant can list/use default categories | + | 200 |

### Admin creates extra categories

| Case | Type | Expect |
|---|---|---|
| Admin POST new category | + | 201 |
| Non-admin creates global category | − | 403 |
| Duplicate default/admin name (if unique) | − | 400/409 |
| Missing name | − | 400 |

### Console list categories — `GET /api/console/categories/`

| Case | Type | Expect |
|---|---|---|
| Owner lists categories available for items | + | 200 includes defaults |
| No auth | − | 401 |
| Non-owner | − | 403 |

---

## Menu items

### Fields under test

Category, Subcategory, Name, Description, Item Type, Quantity, Base Price, Is Popular, Is New, Status (`draft` | `published` | `hidden`)  
Media: **one video**, **multiple images**  
Sizes: optional related `MenuItemSize` rows

### Create — `POST /api/console/menu-items/`

| Case | Type | Expect |
|---|---|---|
| Create with category, name, base_price, status=draft | + | 201 |
| Create published with one video + multiple images | + | 201 |
| Create with sizes (label, price, offer_price, position) | + | 201, sizes ordered by position |
| Is Popular / Is New flags | + | 201, flags true |
| Missing name or category | − | 400 |
| Missing base_price when no sizes | − | 400 |
| Offer price ≥ price on a size | − | 400 |
| Two videos attached | − | 400 (max one video) |
| Zero images when policy requires ≥1 for publish | − | 400 |
| Publish without required media | − | 400 |
| Invalid status | − | 400 |
| No restaurant profile / non-owner | − | 403 |
| No auth | − | 401 |
| Quota exceeded (if free-tier still applies) | − | 403 `PRODUCT_QUOTA_EXCEEDED` |

### List / retrieve

| Case | Type | Expect |
|---|---|---|
| Console list own items | + | 200 |
| Public menu shows only `published` (not draft/hidden) | + | 200 |
| Retrieve item with sizes sorted by `position` | + | Small→Medium→Large order |
| Foreign item | − | 403/404 |
| Unknown id | − | 404 |

### Update / status

| Case | Type | Expect |
|---|---|---|
| PATCH name, description, flags | + | 200 |
| Change status draft → published | + | 200 |
| Change status → hidden | + | 200; hidden from public menu |
| PATCH sizes reorder via position | + | 200 |
| Non-owner PATCH | − | 403 |

### Delete / hide

| Case | Type | Expect |
|---|---|---|
| Soft-hide or destroy own item | + | 200/204 |
| Delete item in active deal without force | − | 409 (if protected) |
| Non-owner | − | 403 |

### Size example assert

| Label | Price | Offer Price | Position |
|---|---:|---:|---:|
| Small | 1200 | 1050 | 1 |
| Medium | 1800 | 1650 | 2 |
| Large | 2500 | 2250 | 3 |

| Case | Type | Expect |
|---|---|---|
| Create pizza with three sizes as above | + | 201; GET returns same order by position |
| Missing label or price on size | − | 400 |

---

## Deals

### Fields under test

Title, Description, Deal Price, Multiple Menu Items, Total Items, Saving Amount, Saving Percentage, Start Time, End Time, Days of Week (Sun–Sat), Status (`draft` | `active` | `expired` | `hidden`), Deal image(s)

### Create — `POST /api/console/deals/`

| Case | Type | Expect |
|---|---|---|
| Create deal with title, deal_price, ≥1 menu items, start/end, days, image | + | 201 |
| Server computes total_items, saving_amount, saving_percentage | + | savings = items total − deal_price |
| Days = Sat + Sun only | + | 201, `days_of_week` persisted |
| Days = every day | + | 201 |
| `deal_price` ≥ items total | − | 400 |
| No menu items | − | 400 |
| Missing title / deal_price | − | 400 |
| `end_time` ≤ `start_time` | − | 400 |
| Invalid day value | − | 400 |
| Missing image when required | − | 400 |
| No auth / non-owner | − | 401 / 403 |

### Status transitions

| Case | Type | Expect |
|---|---|---|
| draft → active | + | 200 |
| Past end_time → expired (job or on read) | + | status `expired` |
| active → hidden | + | 200; hidden from public |
| Invalid status | − | 400 |

### Public / list

| Case | Type | Expect |
|---|---|---|
| Public lists active deals for restaurant | + | 200 |
| Draft/hidden not public | + | excluded |
| Console segments / filters by status | + | 200 |
| GET deal detail with items + savings | + | 200 |
| Foreign deal mutate | − | 403/404 |

---

## Promotions

Restaurants can promote: **Restaurant** | **Menu Item** | **Deal**.

### Create request — `POST /api/console/promotion-requests/`

Fields: promotion type, selected menu item (if item), selected deal (if deal), duration (days), start date, end date. Cost derived from duration days.

| Case | Type | Expect |
|---|---|---|
| Promote entire restaurant + duration days | + | 201, status `pending`, cost calculated |
| Promote menu item (type=item + menu_item_id) | + | 201 pending |
| Promote deal (type=deal + deal_id) | + | 201 pending |
| Start/end dates consistent with duration | + | 201 |
| Type=item without menu_item_id | − | 400 |
| Type=deal without deal_id | − | 400 |
| Type=restaurant with item/deal ids set | − | 400 (or ignored — assert policy) |
| Missing duration / invalid dates | − | 400 |
| end ≤ start | − | 400 |
| Foreign item/deal | − | 403/404 |
| No auth / non-owner | − | 401 / 403 |

### Status workflow

Statuses: `pending` → `approved` | `rejected` → `live` (when start date reached after approval)

| Case | Type | Expect |
|---|---|---|
| Admin approve pending → `approved` (+ reviewed_by, review_date) | + | 200 |
| After approve, when start≤now≤end → `live` | + | 200 / job sets live |
| Admin reject → `rejected` + reviewed_by/date | + | 200 |
| Non-admin approve/reject | − | 403 |
| Approve already rejected/live | − | 409 |
| Owner lists own requests | + | 200 |
| Owner cannot approve | − | 403 |

### Admin fields

| Case | Type | Expect |
|---|---|---|
| Approve sets `reviewed_by` = admin user | + | FK set |
| Approve sets `review_date` | + | timestamp set |
| Reject sets reviewed_by + review_date | + | set |

---

## Permissions matrix (module-wide)

| Actor | Restaurant update | Menu/Deal write | Create promotion | Approve promotion |
|---|---|---|---|---|
| Guest | − | − | − | − |
| Customer (no restaurant) | − | − | − | − |
| Restaurant owner | + own only | + own only | + | − |
| Admin | per policy | per policy | − | + |

---

## Factories (`factories.py`)

- `RestaurantFactory` — only the basic fields above + `owner` OneToOne  
- `CityFactory`  
- `MenuCategoryFactory` / ensure defaults via seeder fixture  
- `MenuItemFactory` — status, popular/new, category, base_price  
- `MenuItemSizeFactory` — label, price, offer_price, position  
- `MenuItemImageFactory` / `MenuItemVideoFactory` (one video max)  
- `DealFactory` — days_of_week, status, deal_price, image  
- `DealLineFactory` — menu items on deal  
- `PromotionRequestFactory` — type restaurant|item|deal, pending  
- `ApprovedPromotionFactory` / `LivePromotionFactory`  
- `AdminUserFactory`

---

## Suggested test file split

| File | Focus |
|---|---|
| `test_restaurant_api.py` | create/get/patch restaurant fields, claim, 409 second restaurant |
| `test_menu_api.py` | categories seed, item CRUD, media rules, sizes/position, statuses |
| `test_deal_api.py` | deal CRUD, savings math, days_of_week, statuses |
| `test_promotion_api.py` | types, cost/duration, pending→approved/rejected→live, admin review fields |
