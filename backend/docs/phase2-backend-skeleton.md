# Giai đoạn 2 — Backend Development: Flow Logic & Project Skeleton

> **Stack**: Python (uv), FastAPI (async), SQLAlchemy 2.0 async + asyncpg, Alembic, Pydantic v2  
> **Database**: PostgreSQL  
> **Nguyên tắc**: Layered Architecture — Request đi qua `api → service → repository → model/db`, không bao giờ để router gọi thẳng DB.

---

## 1. Thứ Tự Build (8 bước — không nhảy cóc)

```
Bước 1: Project Setup & Core Infrastructure    (core/ + main.py + pyproject.toml)
   ↓
Bước 2: Database Models & Migrations           (models/ + alembic/)
   ↓
Bước 3: Pydantic Schemas (DTOs)                (schemas/)
   ↓
Bước 4: Auth Module                            (JWT, bcrypt, RBAC)
   ↓
Bước 5: Vehicle Catalog Module                 (CRUD xe, variant, màu)
   ↓
Bước 6: Order/Deposit Module                   (State Machine: pending→paid→confirmed)
   ↓
Bước 7: Payment Module                         (VNPay Sandbox + Webhook Idempotent)
   ↓
Bước 8: Lead/Admin APIs                        (form tư vấn, dashboard admin)
```

---

## 2. Cấu Trúc Thư Mục Đầy Đủ (Project Skeleton)

```
backend/
├── pyproject.toml                  # Khai báo dependencies (uv)
├── .env.example                    # Template biến môi trường (KHÔNG commit .env thật)
├── alembic.ini                     # Config alembic
├── alembic/
│   ├── env.py                      # Async alembic runner (import Base, async engine)
│   └── versions/                   # Auto-generated migration files
│
├── app/
│   ├── main.py                     # FastAPI App factory, gắn routers, middleware, lifespan
│   │
│   ├── core/
│   │   ├── config.py               # AppSettings (pydantic-settings, đọc từ .env)
│   │   ├── database.py             # Async SQLAlchemy engine + SessionLocal + get_db()
│   │   ├── security.py             # JWT encode/decode, hash_password, verify_password
│   │   ├── dependencies.py         # Reusable FastAPI Depends (get_current_user, require_admin)
│   │   └── exceptions.py           # Custom HTTPException classes (NotFound, Forbidden, …)
│   │
│   ├── models/                     # SQLAlchemy ORM Models — ánh xạ trực tiếp tới bảng DB
│   │   ├── base.py                 # DeclarativeBase, TimestampMixin (created_at, updated_at)
│   │   ├── user.py                 # User model (id, email, password_hash, full_name, phone, role)
│   │   ├── vehicle.py              # Vehicle + VehicleVariant + VehicleColor models
│   │   ├── order.py                # Order model + OrderStatus enum
│   │   ├── payment.py              # Payment model + PaymentStatus enum
│   │   └── lead.py                 # Lead model + LeadStatus enum
│   │
│   ├── schemas/                    # Pydantic v2 DTOs — validate Input, shape Output
│   │   ├── auth.py                 # RegisterRequest, LoginRequest, TokenResponse, UserOut
│   │   ├── vehicle.py              # VehicleOut, VehicleDetailOut, VariantOut, ColorOut
│   │   ├── order.py                # CreateOrderRequest, OrderOut, OrderStatusUpdate
│   │   ├── payment.py              # InitPaymentResponse, WebhookPayload (VNPay/MoMo)
│   │   └── lead.py                 # CreateLeadRequest, LeadOut
│   │
│   ├── repositories/               # Data Access Layer — CRUD thuần, không business logic
│   │   ├── base.py                 # BaseRepository[Model] generic (get, get_many, create, update, delete)
│   │   ├── user_repo.py            # get_by_email, create_user
│   │   ├── vehicle_repo.py         # get_active_vehicles, get_by_slug, get_with_variants_colors
│   │   ├── order_repo.py           # create_order, get_by_order_code, update_status
│   │   ├── payment_repo.py         # create_payment, get_by_transaction_code (idempotency check)
│   │   └── lead_repo.py            # create_lead, list_leads_for_admin
│   │
│   ├── services/                   # Business Logic Layer
│   │   ├── auth_service.py         # register(), login() → trả TokenResponse
│   │   ├── vehicle_service.py      # list_vehicles(), get_vehicle_detail()
│   │   ├── order_service.py        # create_order(), STATE MACHINE transition logic
│   │   ├── payment_service.py      # init_payment_url(), handle_webhook() với idempotency
│   │   └── lead_service.py         # submit_lead(), list_leads()
│   │
│   └── api/
│       └── v1/
│           ├── router.py           # Tổng hợp toàn bộ sub-routers của v1
│           ├── auth.py             # POST /auth/register, /auth/login, /auth/refresh, GET /auth/me
│           ├── vehicles.py         # GET /vehicles, GET /vehicles/{slug}
│           ├── orders.py           # POST /orders, GET /orders/{code}, POST /orders/{code}/payment
│           ├── webhooks.py         # POST /webhooks/payment/{gateway}
│           ├── leads.py            # POST /leads
│           └── admin/
│               ├── router.py       # Admin sub-router, prefix=/admin, require_admin Depends
│               ├── vehicles.py     # CRUD xe cho admin
│               ├── orders.py       # Duyệt/hủy đơn
│               └── leads.py        # Xem danh sách lead
│
└── tests/
    ├── conftest.py                  # Async test DB, test client, fixtures (create_test_user, …)
    ├── test_auth.py
    ├── test_vehicles.py
    ├── test_orders.py
    └── test_payment_webhook.py      # Test idempotency quan trọng nhất
```

---

## 3. Flow Logic Chi Tiết Từng Luồng

### Luồng A — Authentication (Bước 4)

```
POST /auth/register
  → schemas.RegisterRequest (validate email, password strength)
  → auth_service.register()
      ├─ user_repo.get_by_email() → nếu tồn tại: raise 409 Conflict
      ├─ security.hash_password(plain) → password_hash
      └─ user_repo.create_user({email, password_hash, full_name, phone, role="customer"})
  → Trả về schemas.UserOut (không có password_hash!)

POST /auth/login
  → schemas.LoginRequest (email, password)
  → auth_service.login()
      ├─ user_repo.get_by_email() → nếu None: raise 401
      ├─ security.verify_password(plain, hash) → nếu False: raise 401
      ├─ security.create_access_token({sub: user.id, role: user.role})
      └─ security.create_refresh_token(...)
  → Trả về schemas.TokenResponse {access_token, refresh_token, token_type}

GET /auth/me  (Header: Authorization: Bearer <token>)
  → Depends(get_current_user)
      ├─ security.decode_token(token) → payload
      └─ user_repo.get(payload["sub"]) → User obj
  → Trả về schemas.UserOut
```

---

### Luồng B — Vehicle Catalog (Bước 5)

```
GET /vehicles?page=1&limit=12
  → vehicles router → vehicle_service.list_vehicles()
      └─ vehicle_repo.get_active_vehicles(skip, limit)
          SELECT id, name, slug, base_price FROM vehicles WHERE is_active=True
  → Trả về List[VehicleOut] (không có variants/colors → response nhẹ)

GET /vehicles/{slug}
  → vehicle_service.get_vehicle_detail(slug)
      └─ vehicle_repo.get_by_slug_with_relations(slug)
          SELECT vehicle + related variants + related colors (eager load / joined query)
          → nếu None: raise 404 NotFound
  → Trả về VehicleDetailOut {vehicle_info, variants: List[VariantOut], colors: List[ColorOut]}
```

---

### Luồng C — Order State Machine (Bước 6) — Quan trọng nhất

```
POST /orders  (Requires Auth: Bearer token)
  → JWT Depends → get_current_user → user
  → schemas.CreateOrderRequest {variant_id, color_id, customer_name, phone, email, id_card}
  → order_service.create_order(user_id, request)
      ├─ vehicle_repo.get_variant(variant_id) → validate tồn tại
      ├─ vehicle_repo.get_color(color_id) → validate thuộc cùng vehicle
      ├─ Tính deposit_amount = variant.vehicle.deposit_amount
      ├─ Sinh order_code = f"ORD-{date}-{uuid4().hex[:6].upper()}"
      └─ order_repo.create_order({...status="pending"...})
  → Trả về schemas.OrderOut

State Machine (transitions hợp lệ):
  pending  →  paid        (khi webhook payment thành công)
  pending  →  cancelled   (admin hủy hoặc timeout thanh toán)
  paid     →  confirmed   (admin xác nhận, xe sẵn sàng)
  paid     →  refunded    (admin duyệt hoàn tiền)

  KHÔNG cho phép: confirmed → paid, cancelled → paid, v.v.

VALID_TRANSITIONS = {
    "pending":   ["paid", "cancelled"],
    "paid":      ["confirmed", "refunded"],
    "confirmed": [],   # trạng thái cuối
    "cancelled": [],   # trạng thái cuối
    "refunded":  [],   # trạng thái cuối
}
if new_status not in VALID_TRANSITIONS[current_status]:
    raise InvalidTransitionError(409)
```

---

### Luồng D — Payment & Webhook Idempotency (Bước 7) — Dễ bug nhất

```
POST /orders/{order_code}/payment
  → validate order.status == "pending"
  → payment_service.init_payment_url(order)
      ├─ Tạo payment record {order_id, amount, status="pending", gateway="vnpay"}
      ├─ Gọi VNPay Sandbox API → lấy payment_url
      └─ Trả về {payment_url, order_code}
  → FE redirect khách hàng đến payment_url

─── Khách thanh toán xong trên VNPay ───

POST /webhooks/payment/vnpay  (VNPay gọi vào — có thể gọi nhiều lần!)
  → KHÔNG yêu cầu JWT (public, nhưng phải verify signature)
  → payment_service.handle_webhook(gateway="vnpay", raw_payload)

  Idempotency Logic:
  1. Verify HMAC signature của payload
     → nếu sai: trả về 200 OK nhưng bỏ qua (đừng trả 400!)
  2. Lấy transaction_code từ payload
  3. payment_repo.get_by_transaction_code(txn_code)
     → nếu đã tồn tại và status == "success":
       EARLY RETURN 200 OK ngay (idempotent! dừng xử lý)
  4. Cập nhật payment: status="success", paid_at=now()
     Lưu raw_webhook_payload vào DB để audit
  5. order_service.update_status(order_id, "paid")
  6. Gửi email xác nhận (BackgroundTask — không block response)
  → Luôn trả HTTP 200 (gateway chờ 200 để dừng retry)
```

---

## 4. Module Dependencies (Build Order)

```
core/config.py          ← không phụ thuộc gì
     ↓
core/database.py        ← depends: config
core/security.py        ← depends: config
     ↓
models/*                ← depends: database (Base, TimestampMixin)
     ↓
alembic/                ← depends: models (để autogenerate)
repositories/*          ← depends: models + database
     ↓
core/dependencies.py    ← depends: security + repositories
services/*              ← depends: repositories + security + dependencies
     ↓
api/v1/*                ← depends: services + schemas + dependencies
     ↓
app/main.py             ← tổng hợp routers, lifespan, middleware
```

**Nguyên tắc cứng**: Tầng thấp KHÔNG được import từ tầng cao.  
- `models` không biết `services` tồn tại.  
- `repositories` không gọi thẳng `db.execute()` tự ý — nhận `session` qua tham số.  
- `services` không import từ `api`.

---

## 5. Dependencies cần cài (pyproject.toml)

```toml
[project]
dependencies = [
    # Web Framework
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",

    # Database (async)
    "sqlalchemy>=2.0",
    "asyncpg>=0.30",
    "alembic>=1.14",

    # Validation & Config
    "pydantic[email]>=2.9",
    "pydantic-settings>=2.6",

    # Auth
    "python-jose[cryptography]>=3.3",
    "passlib[bcrypt]>=1.7",

    # HTTP Client (gọi VNPay Sandbox)
    "httpx>=0.28",

    # Email
    "fastapi-mail>=1.4",

    # Multipart (upload ảnh xe)
    "python-multipart>=0.0.18",
]

[tool.uv.dev-dependencies]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.24",
    "anyio>=4",
    "httpx>=0.28",
]
```

---

## 6. Biến Môi Trường (.env.example)

```env
# App
APP_ENV=development
SECRET_KEY=your-super-secret-key-min-32-chars
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/car_deposit_db

# VNPay Sandbox
VNPAY_TMN_CODE=your_tmn_code
VNPAY_HASH_SECRET=your_hash_secret
VNPAY_URL=https://sandbox.vnpayment.vn/paymentv2/vpcpay.html
VNPAY_RETURN_URL=http://localhost:3000/orders/result

# Email (SMTP)
MAIL_USERNAME=your@gmail.com
MAIL_PASSWORD=your_app_password
MAIL_FROM=no-reply@your-app.com
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_STARTTLS=true
```

---

## 7. Checklist Hoàn Thành Giai Đoạn 2

- [ ] **B1** `pyproject.toml` khai báo đầy đủ deps, chạy `uv sync` thành công
- [ ] **B1** `.env.example` và `core/config.py` với `AppSettings`
- [ ] **B1** `core/database.py` — async engine + `get_db()` dependency
- [ ] **B2** Tất cả SQLAlchemy models khai báo xong
- [ ] **B2** `alembic init` + `alembic revision --autogenerate` chạy được
- [ ] **B2** `alembic upgrade head` tạo đủ bảng trong PostgreSQL local
- [ ] **B3** Schemas (DTOs) cho auth, vehicle, order, payment, lead
- [ ] **B4** Auth endpoints hoạt động, JWT decode đúng
- [ ] **B5** `GET /vehicles` và `GET /vehicles/{slug}` trả dữ liệu đúng
- [ ] **B6** Tạo đơn cọc được, state machine từ chối transition sai
- [ ] **B7** Webhook handler xử lý idempotent (gọi 2 lần chỉ update 1 lần)
- [ ] **B8** Admin endpoints có RBAC (role != "admin" → 403)
- [ ] FastAPI `GET /docs` hiển thị đầy đủ Swagger UI
