# Rayalseema — Backend Flow

Django 5.2 + Django REST Framework backend for the Rayalseema food-delivery
platform. This doc explains how the backend is put together, how a request
flows through it, and what every API endpoint does. For a machine-readable,
importable version of every endpoint see `postman/Rayalseema.postman_collection.json`
at the project root (generated straight from this backend's OpenAPI schema).

## Stack

| Layer | Choice |
|---|---|
| Framework | Django 5.2.16 + Django REST Framework 3.17 |
| Auth | `djangorestframework-simplejwt` (JWT access + refresh, custom claims) |
| Database | PostgreSQL in production, falls back to local SQLite if `DATABASE_URL` is unset |
| Realtime | Django Channels 4 (ASGI, ws://…/ws/…) over Daphne, backed by Redis |
| Background jobs | Celery + Redis (broker) |
| Payments | Razorpay SDK, with a `PAYMENT_STUB_MODE` that auto-succeeds without hitting Razorpay |
| OTP delivery | Twilio (SMS) / SMTP (email), with an `OTP_STUB_MODE` that just logs the code instead of sending it |
| API docs | `drf-spectacular` — OpenAPI schema at `/api/schema/`, Swagger UI at `/api/docs/`, Redoc at `/api/redoc/` |
| Brute-force protection | `django-axes` (5 failed logins → 1 hour cooldown, keyed by username+IP) |
| Media storage | Local filesystem in dev, S3 via `django-storages` when `USE_S3=True` |

Every app under `backend/` is a normal Django app: `accounts`, `otp`,
`addresses`, `restaurants`, `foods`, `coupons`, `orders`, `payments`,
`tracking`, `reviews`, `notifications`, `analytics`, `delivery`, `adminpanel`,
plus `core` (shared permissions/pagination/response helpers/audit log) and
`config` (the Django project itself: settings, root urls, ASGI routing).

## Request flow

```
Client (React app)
   │  Authorization: Bearer <access-token>
   ▼
DRF View / ViewSet
   │  permission_classes (IsAuthenticated + role check, or AllowAny)
   ▼
Serializer (validates + shapes data)
   │
   ▼
Service layer / model methods (business rules: order totals, OTP checks,
   coupon math, delivery-assignment transitions, etc.)
   │
   ▼
core.responses.success_response / error_response
   → { "success": true, "message": "...", "data": {...} }
   → { "success": false, "message": "...", "errors": {...} }
```

List endpoints are paginated by `core.pagination.StandardResultsPagination`
(page size 20, `?page_size=` to override, capped at 100) and wrap the array in
`data` plus a `meta` block: `{count, page, pages, page_size, next, previous}`.

## Auth flow

All three signup flows (customer, restaurant owner, delivery partner) share
the same shape: **register → email OTP → verify → JWT issued**. Restaurant
and delivery signups have an *extra* gate on top: an admin must approve the
account before it can actually do anything role-specific.

```
Customer:
  POST /accounts/register/            → creates User(role=customer, is_verified=False), emails OTP
  POST /accounts/verify-registration/ → checks OTP, is_verified=True, returns access+refresh+user
  (can log in and order immediately — no admin approval needed)

Restaurant owner:
  POST /restaurants/register/         → creates User(role=restaurant) + Restaurant(is_approved=False), emails OTP
  POST /restaurants/verify-registration/ → verifies email, returns tokens — but restaurant is
                                           still is_approved=False, so it's invisible to customers
  POST /admin/restaurants/{id}/approve/  → admin flips is_approved=True (only then it's public)

Delivery partner:
  POST /delivery/register/            → creates User(role=delivery) + DeliveryPartner(is_approved=False)
  POST /delivery/verify-registration/ → verifies email, returns tokens — but can't go online or
                                         accept deliveries until approved
  POST /admin/delivery-partners/{id}/approve/ → admin approves
```

Login: `POST /accounts/token/` with `{email, password}` → `{access, refresh, user}`.
The JWT embeds `role` and `email` as custom claims. Access tokens last 30
minutes; refresh tokens last 7 days and rotate + get blacklisted on use
(`POST /accounts/token/refresh/`).

Role checks are a plain field comparison, not Django's `is_staff`/`is_superuser`:
`core/permissions.py` defines `IsCustomer`, `IsRestaurantOwner`,
`IsDeliveryPartner`, `IsAdminRole`, each checking `request.user.role == "..."`.
Every admin-only endpoint requires `IsAuthenticated + IsAdminRole`. There's no
public "become an admin" endpoint — admin accounts are created with
`python manage.py createsuperuser` (sets `role=admin`) or via the seed command.

`OTP_STUB_MODE=True` (the default in `.env.example`) skips real Twilio/SMTP
calls and just logs the 6-digit code to the console — useful for local dev
and for scripting through the Postman collection without a real inbox.
`PAYMENT_STUB_MODE=True` does the same for Razorpay: `POST /payments/verify/`
auto-succeeds regardless of the signature you send.

## Order lifecycle

```
placed → accepted → preparing → out_for_delivery → delivered
     ↘ cancelled (from "placed" only, via restaurant reject)
```

- Customer creates an order: `POST /orders/` with an address + a list of
  `{food_id, variant_id?, quantity}` — all items must belong to the *same*
  restaurant. Prices are snapshotted onto `OrderItem` at creation time so
  later menu price changes don't retroactively change past orders.
- Restaurant moves it forward: `POST /orders/restaurant/{id}/accept/`,
  `.../reject/` (placed → cancelled), `.../advance/` (accepted → preparing →
  out_for_delivery).
- Once `out_for_delivery`, it shows up in `GET /delivery/available-orders/`
  for any approved, online delivery partner nearby. One of them calls
  `POST /delivery/available-orders/{order_id}/accept/`, which creates a
  `DeliveryAssignment` (assigned → picked_up → delivered). Marking an
  assignment `delivered` also flips the parent `Order.status` to `delivered`.
- Reviews are 1:1 with orders (`Review.order` is a `OneToOneField`) — a
  customer can only review an order once, via `POST /reviews/`.

## Payments

`POST /payments/create/` with `{order_id}` opens a Razorpay order and stores
a `Payment` row (`status=created`). `POST /payments/verify/` with the
Razorpay payment id + signature marks it `success` and flips
`Order.payment_status` to `paid` (or just auto-succeeds in stub mode). Admins
can refund via `POST /admin/payments/{id}/refund/`, which creates a `Refund`
row and sets `Order.payment_status=refunded`.

## Realtime (WebSocket, not REST)

Channels/ASGI consumers exist for order status pushes, live delivery
location, and notifications (`orders/`, `tracking/`, `notifications/`
`consumers.py` + `routing.py`, wired up in `config/routing.py`). The frontend
connects with `ws://<host>/ws/<path>?token=<access_token>` — see
`core/ws_auth.py` for how the JWT is validated on the socket handshake. These
aren't part of the Postman collection since Postman doesn't drive WebSocket
flows the same way; `python manage.py runserver` won't serve them — use
`daphne config.asgi:application` (see `Procfile`/deployment notes) for the
ASGI server.

## All API endpoints

Base path for everything below: `/api/v1`. Full detail (request/response
schemas) is in `/api/docs/` (Swagger) once the server is running, and in the
Postman collection. `AllowAny` = no token needed; everything else needs
`Authorization: Bearer <access>`.

### accounts — `/accounts/`
| Method | Path | Auth | What it does |
|---|---|---|---|
| POST | `register/` | AllowAny | Customer signup, sends OTP |
| POST | `verify-registration/` | AllowAny | Confirms OTP, returns tokens |
| POST | `forgot-password/` | AllowAny | Sends password-reset OTP (always 200, no email enumeration) |
| POST | `reset-password/` | AllowAny | Confirms OTP + sets new password |
| POST | `google/` | AllowAny | Google Sign-In → login/create as customer |
| GET/PATCH | `profile/` | Auth | View/edit own profile (PATCH accepts multipart for avatar) |
| POST | `token/` | AllowAny | Login → access + refresh + user |
| POST | `token/refresh/` | AllowAny | Rotate refresh token → new access |

### otp — `/otp/`
| Method | Path | Auth | What it does |
|---|---|---|---|
| POST | `send/` | AllowAny | Send a standalone OTP (identifier, channel, purpose) |
| POST | `verify/` | AllowAny | Verify a standalone OTP |

### addresses — `/addresses/`
| Method | Path | Auth | What it does |
|---|---|---|---|
| GET/POST | `` | Auth | List / create your own saved addresses |
| GET/PUT/PATCH/DELETE | `{id}/` | Auth | Manage one address (own only) |
| POST | `{id}/set-default/` | Auth | Mark as your default delivery address |

### restaurants — `/restaurants/`
| Method | Path | Auth | What it does |
|---|---|---|---|
| GET | `categories/` | AllowAny | Cuisine category list (Biryani, Chinese, …) |
| GET | `favorites/` | Auth | Your favorited restaurants |
| POST | `register/` | AllowAny | Restaurant owner signup |
| POST | `verify-registration/` | AllowAny | Confirm OTP → tokens + restaurant (unapproved) |
| GET/PATCH | `me/` | Owner | View/edit your own restaurant |
| PUT | `me/opening-hours/` | Owner | Bulk-set weekly opening hours |
| GET | `` | AllowAny | Public restaurant list — filters: `category`, `min_rating`, `lat`/`lng`/`radius_km`, `ordering`, `search` |
| GET | `{slug}/` | AllowAny | Restaurant detail |
| POST/DELETE | `{slug}/favorite/` | Auth | Favorite / unfavorite |

### foods — `/foods/`
| Method | Path | Auth | What it does |
|---|---|---|---|
| GET | `categories/?restaurant=<slug>` | AllowAny | Menu categories for a restaurant |
| GET | `wishlist/` | Auth | Your wishlisted food items |
| CRUD | `my-categories/`, `my-categories/{id}/` | Owner | Manage your own menu categories |
| CRUD | `my-variants/`, `my-variants/{id}/` | Owner | Manage your own food variants (Half/Full etc.) |
| GET | `` | AllowAny | Food list — filters: `restaurant`, `category`, `is_vegetarian`, `mine=true` (own items), `search` |
| POST | `` | Owner | Create a food item |
| GET | `{id}/` | AllowAny | Food detail |
| PUT/PATCH/DELETE | `{id}/` | Owner | Edit/remove your own food item |
| POST/DELETE | `{id}/wishlist/` | Auth | Wishlist / unwishlist |
| POST | `{id}/toggle-availability/` | Owner | 86 an item without deleting it |

### coupons — `/coupons/`
| Method | Path | Auth | What it does |
|---|---|---|---|
| POST | `validate/` | Auth | `{code, subtotal}` → discount preview before checkout |

(Coupon CRUD is admin-only — see `adminpanel` below.)

### orders — `/orders/`
| Method | Path | Auth | What it does |
|---|---|---|---|
| GET/POST | `` | Auth | List your orders / place a new one |
| GET | `{id}/` | Auth | Order detail |
| GET | `restaurant/` | Owner | Orders placed at your restaurant |
| GET | `restaurant/{id}/` | Owner | One order's detail |
| POST | `restaurant/{id}/accept/` | Owner | placed → accepted |
| POST | `restaurant/{id}/reject/` | Owner | placed → cancelled |
| POST | `restaurant/{id}/advance/` | Owner | accepted → preparing → out_for_delivery |

### payments — `/payments/`
| Method | Path | Auth | What it does |
|---|---|---|---|
| POST | `create/` | Auth | `{order_id}` → opens a Razorpay order |
| POST | `verify/` | Auth | Confirms payment signature → marks order paid |

### tracking — `/tracking/`
| Method | Path | Auth | What it does |
|---|---|---|---|
| POST | `location/` | Auth (assigned delivery partner or staff) | Push a GPS ping for a live order |

### reviews — `/reviews/`
| Method | Path | Auth | What it does |
|---|---|---|---|
| GET | `?restaurant=<slug>` | AllowAny | Reviews for a restaurant |
| POST | `` | Auth | Leave a review for a delivered order (one per order) |
| POST | `{id}/respond/` | Owner | Restaurant owner replies to a review |

### notifications — `/notifications/`
| Method | Path | Auth | What it does |
|---|---|---|---|
| GET | `` | Auth | Your notifications |
| POST | `{id}/read/` | Auth | Mark one as read |
| POST | `read-all/` | Auth | Mark all as read |
| GET | `unread-count/` | Auth | Badge count |

### analytics — `/analytics/`
| Method | Path | Auth | What it does |
|---|---|---|---|
| GET | `restaurant/dashboard/` | Owner | Today/this-week/this-month stats for your restaurant |
| GET | `restaurant/sales/?start=&end=` | Owner | Sales report, optional `export=csv` |
| GET | `platform/dashboard/` | Admin | Platform-wide stats |
| GET | `platform/daily-summary/?start=&end=` | Admin | Daily breakdown, optional `export=csv` |

### delivery — `/delivery/`
| Method | Path | Auth | What it does |
|---|---|---|---|
| POST | `register/` | AllowAny | Delivery partner signup |
| POST | `verify-registration/` | AllowAny | Confirm OTP → tokens + partner (unapproved) |
| GET/PATCH | `me/` | Partner | View/edit your own delivery profile |
| POST | `me/toggle-online/` | Partner (must be approved) | Go online/offline |
| GET | `available-orders/?lat=&lng=` | Partner (approved) | Orders ready for pickup, unassigned |
| POST | `available-orders/{order_id}/accept/` | Partner (approved) | Claim a delivery |
| GET | `earnings/summary/` | Partner | Today/week/all-time earnings |
| GET | `my-deliveries/`, `my-deliveries/{id}/` | Partner | Your assignment history |
| POST | `my-deliveries/{id}/picked-up/` | Partner | assigned → picked_up |
| POST | `my-deliveries/{id}/delivered/` | Partner | picked_up → delivered (also completes the Order) |

### adminpanel — `/admin/` (everything here needs `IsAdminRole`)
| Method | Path | What it does |
|---|---|---|
| GET/PATCH | `settings/` | Platform-wide settings (commission %, delivery radius, support contact) |
| GET | `users/`, `users/{id}/` | Customer accounts |
| POST | `users/{id}/suspend/`, `.../reactivate/` | Ban / unban a customer |
| GET | `restaurants/`, `restaurants/{id}/` | All restaurants, filter by `is_approved` |
| POST | `restaurants/{id}/approve/`, `.../suspend/`, `.../reactivate/` | Approval + moderation |
| GET | `delivery-partners/`, `.../{id}/` | All delivery partners, filter by `is_approved` |
| POST | `delivery-partners/{id}/approve/`, `.../suspend/`, `.../reactivate/` | Approval + moderation |
| GET | `orders/`, `orders/{id}/` | Platform-wide order oversight, filter by `status`, `restaurant` |
| GET | `payments/`, `payments/{id}/` | All payment records |
| POST | `payments/{id}/refund/` | Issue a refund |
| CRUD | `coupons/`, `coupons/{id}/` | Full coupon management |
| GET | `coupons/{id}/usage/` | Who's used a coupon |
| GET | `audit-log/` | Read-only history of admin actions (`core.services.log_action`) |

### search (root-level, not under `/admin` or any app prefix)
| Method | Path | Auth | What it does |
|---|---|---|---|
| GET | `/api/v1/search/?q=` | AllowAny | Combined restaurant + food search, top 10 each |

**Endpoint count: 92 distinct URL patterns, ~130+ operations once every
supported HTTP method per pattern is counted** (see the Postman collection
for the literal, generated-from-schema list — it will never drift from the
real routes because it's regenerated from `manage.py spectacular`, not typed
by hand).

## Data model quick reference

All primary keys are UUIDs (`models.UUIDField(default=uuid.uuid4)`), not
auto-increment integers — keep that in mind if you're writing raw SQL or
constructing test fixtures by hand.

```
User (role: customer|restaurant|delivery|admin)
 ├─ Restaurant (owner=User, is_approved, is_active)
 │   ├─ RestaurantCategory (M2M, e.g. "Biryani")
 │   ├─ OpeningHours (per weekday)
 │   ├─ FoodCategory
 │   │   └─ Food (base_price, is_vegetarian, is_available)
 │   │        └─ FoodVariant (Half/Full, its own price)
 │   └─ Review (1:1 with Order) → restaurant_response
 ├─ DeliveryPartner (1:1, is_approved, is_online)
 │   └─ DeliveryAssignment (1:1 with Order) — assigned→picked_up→delivered
 ├─ Address (multiple, one is_default)
 ├─ Order (restaurant=PROTECT, coupon=SET_NULL)
 │   ├─ OrderItem (food/variant snapshot: name + price at time of order)
 │   ├─ Payment (Razorpay order/payment id, status)
 │   │   └─ Refund
 │   └─ LocationUpdate (GPS pings for live tracking)
 ├─ Notification (order_status | promo | system)
 └─ FavoriteRestaurant / FoodWishlist (bookmarks)

Coupon (code, discount_type: percentage|flat, valid_from/until)
 └─ CouponUsage (per user, per order)

OTP (identifier, channel: email|sms, purpose: register|login|password_reset|phone_verify)
AuditLog (actor, action, target_type/id, metadata) — every admin moderation action
PlatformSettings (singleton) / PlatformDailySummary (per-day rollup)
```

## Local setup

See `../SETUP.md` at the project root for the one-command setup, or
manually:

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows; source venv/bin/activate on macOS/Linux
pip install -r requirements.txt
copy .env.example .env       # cp on macOS/Linux — defaults use SQLite + stub OTP/payments, no external services required
python manage.py migrate
python manage.py seed_demo_data   # see below
python manage.py runserver
```

## Seeding demo data

```bash
python manage.py seed_demo_data
```

Creates (idempotent — safe to re-run):
- `user1@yopmail.com` — customer, with saved addresses
- `restaurant1@yopmail.com` — approved restaurant owner, with menu categories, food items, variants, opening hours
- `delivery1@yopmail.com` — approved, online delivery partner
- `admin1@yopmail.com` — admin (`is_staff`/`is_superuser`)

All four passwords: `Password@123`. It also creates a few extra restaurants,
a coupon, sample orders across different statuses (including a delivered one
with a review and completed delivery assignment), and notifications, so
every screen in the frontend has real data to show instead of empty states.
See `python manage.py seed_demo_data --help` for flags (e.g. `--flush` to
wipe seeded data first).
