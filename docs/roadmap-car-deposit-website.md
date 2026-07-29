# Roadmap xây dựng Website đặt cọc xe (kiểu VinFast) — Production-grade

> Bối cảnh: anh là AI dev, muốn làm 1 dự án full-stack thật (không phải demo học tập) để bao quát thêm role dev. Stack: **React (Next.js) + FastAPI**, kiến trúc **Modular 3-Layer** (module hoá theo nghiệp vụ, mỗi module giữ 3-layer API → Service → Repository → Model bên trong), tích hợp **AI Agent chatbot** ở giai đoạn cuối như 1 client của các module có sẵn.

Sau khi xem trang tham khảo, mô hình thực tế gồm 3 mảng tách biệt:
1. **Landing/Marketing site** — giới thiệu xe, thông số, màu sắc, so sánh chi phí, form thu lead.
2. **Order/Shop system** — luồng đặt cọc thật: chọn phiên bản/màu → tạo đơn → thanh toán → theo dõi trạng thái.
3. **Admin/CMS** — quản lý xe, đơn hàng, khách hàng, nội dung, cấu trúc tổ chức (Enterprise-ready).

Một dự án thật luôn đi theo thứ tự: **Discovery → Design → Backend → Frontend → Tích hợp thanh toán → DevOps → Security → Test → Launch → (sau đó) AI**. Đừng nhảy cóc vào code ngay.

---

## Giai đoạn 0 — Discovery & Business Requirement

Trước khi code, viết ra (dạng markdown trong repo, thư mục `docs/`):

- **Đối tượng dùng**: khách hàng cuối (public), nhân viên sale/admin, (sau này) AI agent.
- **Use case chính**:
  - Khách xem danh sách xe → xem chi tiết → chọn phiên bản/màu/option → đặt cọc → thanh toán → nhận email xác nhận → theo dõi trạng thái đơn.
  - Khách đăng ký lái thử / để lại thông tin tư vấn (lead capture).
  - Admin quản lý catalog xe, xem/duyệt đơn cọc, xem danh sách lead, quản lý cơ cấu tổ chức (showroom/phòng ban) và phân quyền nhân viên.
- **Phạm vi MVP**: 1-2 mẫu xe, mỗi xe vài phiên bản/màu, 1 cổng thanh toán, 1 showroom.
- **Non-functional requirements**: SEO tốt (landing công khai) → Next.js SSR/SSG; chịu tải khi có traffic quảng cáo; bảo mật vì thu thập PII + thanh toán; audit trail đầy đủ cho mọi thao tác admin.

Output: 1 file `docs/prd.md`.

---

## Giai đoạn 1 — System Design & Architecture

### 1.1 Kiến trúc tổng thể — Modular 3-Layer

Chia theo **chiều dọc** (module nghiệp vụ), mỗi module giữ nguyên **3-layer bên trong** (API → Service → Repository → Model). Đây là "Modular Monolith" — 1 codebase, 1 database, nhưng ranh giới module rõ ràng để dễ tách thành service riêng sau này nếu cần.

```
backend/
├── app/
│   ├── main.py                  # Entry point, register router của từng module
│   │
│   ├── core/                    # Nền tảng dùng chung, KHÔNG chứa business logic riêng của module nào
│   │   ├── config.py            # pydantic-settings
│   │   ├── database.py           # SQLAlchemy Base chung — mọi model của mọi module import từ đây
│   │   ├── security.py            # JWT, password hashing
│   │   ├── middlewares.py          # CORS, rate limit, logging
│   │   ├── exceptions.py            # exception handlers, response format {success, data, error}
│   │   └── audit.py                  # audit_service dùng chung — module nào cũng gọi được
│   │
│   ├── modules/                 # ★ Chia theo domain nghiệp vụ, mỗi module là 1 "mini 3-layer"
│   │   ├── users/                # Auth, Roles, Permissions, Departments, Profile — module nền tảng
│   │   │   ├── api.py, service.py, repository.py, model.py, schema.py
│   │   │
│   │   ├── catalog/               # Xe, phiên bản, màu sắc, gallery — module nền tảng
│   │   │   ├── api.py, service.py, repository.py, model.py, schema.py
│   │   │
│   │   ├── leads/                   # Form tư vấn, đăng ký lái thử — phụ thuộc catalog
│   │   │   ├── api.py, service.py, repository.py, model.py, schema.py
│   │   │
│   │   ├── orders/                    # Đặt cọc, state machine trạng thái đơn — phụ thuộc catalog + users
│   │   │   ├── api.py, service.py, repository.py, model.py, schema.py
│   │   │
│   │   ├── payments/                     # VNPay/MoMo + webhook — phụ thuộc orders
│   │   │   ├── api.py, service.py, repository.py, model.py, schema.py
│   │   │
│   │   └── ai_agent/                        # ★ CLIENT của các module trên, KHÔNG phải domain ngang hàng
│   │       ├── conversation/                 # session hội thoại, lịch sử chat
│   │       ├── rag/                           # embedding, retrieval, vector index (OpenSearch/bge-m3)
│   │       ├── tools/                          # wrapper gọi catalog.service, orders.service, leads.service...
│   │       └── agent.py                          # orchestration (LangGraph/ReAct loop)
│   │
│   ├── workers/                 # Background jobs (Celery/APScheduler) — gửi email/SMS, đồng bộ, retry webhook
│   └── tests/
│       ├── unit/                 # test Service layer từng module (mock Repository)
│       └── integration/           # test Repository + API (DB test container)
│
├── frontend/          # Next.js
├── infra/             # docker-compose, nginx, ci-cd
└── docs/
```

### 1.2 Quy tắc bắt buộc — sơ đồ phụ thuộc giữa module

Đây là phần quan trọng nhất để tránh "big ball of mud" — viết ra thành văn bản trước khi code, dán vào `docs/module-dependency.md`:

```
users, catalog     →  module nền tảng, KHÔNG phụ thuộc module nghiệp vụ nào khác
leads               →  phụ thuộc catalog (biết khách quan tâm xe nào)
orders                →  phụ thuộc catalog + users
payments                →  phụ thuộc orders (không được ngược lại)
ai_agent                   →  phụ thuộc TẤT CẢ (đóng vai trò client) — nhưng KHÔNG module nào
                              được phép import ngược lại ai_agent
```

**2 quy tắc code cứng phải tuân theo:**
1. Module A muốn dùng chức năng của module B → chỉ được gọi qua `B/service.py` (public interface), **tuyệt đối không** import thẳng `B/repository.py` hay `B/model.py`. Đây là ranh giới thật sự giữ module độc lập, không chỉ nằm trên giấy.
2. Cross-cutting concern (audit log, notification chung) đặt ở `core/`, không đặt trong 1 module cụ thể rồi bắt module khác import — tránh biến 1 module thành nút thắt cổ chai bị mọi module khác phụ thuộc.

### 1.3 Bên trong mỗi module vẫn là 3-Layer (giữ nguyên tinh thần template mẫu)

```
API layer (api.py)        →  nhận request, validate Pydantic schema, gọi Service, format response
Service layer (service.py) →  business logic, permission check, state machine, gọi audit qua core/audit.py
Repository layer (repository.py) → CRUD, query — không chứa business logic
Model layer (model.py)     →  SQLAlchemy model, import Base từ core/database.py
```

**Điểm mấu chốt cho AI Agent (giai đoạn 9):** `service.py` của mỗi module phải nhận tham số thuần Python (không nhận FastAPI `Request`/trả `Response`), để cả `api.py` (HTTP) lẫn `ai_agent/tools/` (tool-calling) đều gọi được cùng 1 hàm mà không viết lại logic.

### 1.4 Thiết kế Database (ERD) — vẽ trước khi code

Bảng cốt lõi, nhóm theo module để thấy rõ ranh giới:
- **users**: `users`, `roles`, `permissions`, `role_permissions`, `departments`
- **catalog**: `vehicles`, `vehicle_variants`, `vehicle_colors`, `vehicle_options`
- **leads**: `leads`
- **orders**: `orders`, `order_status_history`, `promotions`
- **payments**: `payments`
- **cross-cutting (core)**: `audit_logs`, `menus`

Dùng PostgreSQL. Vẽ ERD bằng dbdiagram.io hoặc draw.io trước, lưu vào `docs/erd.png`.

### 1.5 Thiết kế API contract trước (API-first)

```
GET  /api/v1/catalog/vehicles
GET  /api/v1/catalog/vehicles/{slug}
POST /api/v1/leads                     # form tư vấn
POST /api/v1/orders                     # tạo đơn đặt cọc
POST /api/v1/payments/{order_id}/init    # khởi tạo thanh toán
POST /api/v1/payments/webhook              # gateway callback
GET  /api/v1/admin/orders                   # admin, cần permission cụ thể
GET  /api/v1/admin/users/departments          # quản lý cơ cấu tổ chức
GET  /api/v1/admin/users/roles                 # quản lý role/permission
GET  /api/v1/admin/audit-logs                   # tra cứu nhật ký (core)
GET  /api/v1/admin/menus                          # menu động theo role (core)
```

### 1.6 RBAC chi tiết (fine-grained, nằm trong module `users`)

Permission dạng `resource:action`:
```
orders:read, orders:update_status, orders:cancel
catalog:create, catalog:update, catalog:delete
users:manage, roles:manage, audit_logs:read
```
`users/service.py` expose `check_permission(user, "orders:update_status")`, dùng làm FastAPI dependency (`core/security.py` hoặc `users/dependency.py`) cho từng endpoint admin ở bất kỳ module nào.

---

## Giai đoạn 2 — Backend Development (Modular 3-Layer)

Thứ tự build theo đúng sơ đồ phụ thuộc ở mục 1.2 — build module nền tảng trước, module phụ thuộc sau:

1. **`core/`**: `pydantic-settings`, `database.py` (Base chung + SQLAlchemy async engine), Alembic init, `exceptions.py`, response format chuẩn.
2. **`modules/users/`**: Model → Repository → Service → API đủ 4 tầng. Auth JWT (access 4h + refresh 7d), password hashing, login throttling (5 lần/phút), RBAC (`roles`, `permissions`), `departments`. Đây là module đầu tiên vì mọi module khác đều cần auth.
3. **`core/audit.py`**: viết `audit_service` dùng chung ngay sau khi có `users` (cần biết ai đang thao tác) — để các module sau gọi được luôn, không phải quay lại thêm sau.
4. **`modules/catalog/`**: Model → Repository → Service → API — module nền tảng thứ 2, tương đối đơn giản, dùng để làm quen pattern module hoá trước khi vào phần khó.
5. **`modules/leads/`**: phụ thuộc `catalog` (gọi qua `catalog.service`, không import `catalog.repository`). Gửi email qua `workers/`.
6. **`modules/orders/`**: phụ thuộc `catalog` + `users`. State machine trạng thái đơn nằm trong `orders/service.py` (Enum + hàm validate transition rõ ràng, gọi `core/audit.py` sau mỗi lần đổi trạng thái).
7. **`modules/payments/`**: phụ thuộc `orders` (gọi `orders.service.confirm_payment(...)`, không tự sửa DB của `orders`). Tích hợp VNPay/MoMo sandbox, xử lý webhook idempotent.
8. **Admin API** ở từng module (`GET /admin/...`): dùng `Depends(check_permission("..."))`.
9. **`workers/`**: background task (gửi email xác nhận đơn, retry webhook thất bại) dùng Celery hoặc APScheduler.
10. **Testing**: unit test `service.py` từng module (mock `repository.py`) — viết ngay sau khi hoàn thành module đó, không dồn về cuối. Integration test cho `repository.py` + `api.py` dùng DB test container.

> Kinh nghiệm async Python/streaming của anh áp dụng tốt ở `workers/` và xử lý webhook trong `payments/service.py`.

---

## Giai đoạn 3 — Frontend Development (Next.js/React)

Vì đây là trang public cần SEO tốt → **bắt buộc dùng Next.js**.

1. Setup: Next.js (App Router) + TypeScript + TailwindCSS + shadcn/ui.
2. Design system cơ bản trước khi build trang.
3. Trang chính: landing (SSG), chi tiết xe + chọn cấu hình (client component), đặt cọc/checkout, tài khoản khách hàng, form tư vấn, trang admin (route riêng `/admin`, sidebar menu động load từ `GET /api/v1/admin/menus` theo permission).
4. React Query cho data fetching — mỗi module backend có thể map tương ứng 1 nhóm hook/API client ở frontend (`lib/api/catalog.ts`, `lib/api/orders.ts`...) để giữ cùng tư duy module hoá cả 2 phía.
5. `next/image`, lazy load, Lighthouse audit trước launch.

---

## Giai đoạn 4 — Payment & Third-party Integration

- Sandbox VNPay/MoMo.
- Luồng: FE → BE (`orders/service.create_order()`) → BE gọi `payments/service.create_payment_url()` → redirect khách → gateway callback vào `payments/api.py` → `payments/service.confirm_payment()` verify chữ ký → gọi `orders/service.update_status()` (qua public interface, không sửa thẳng DB `orders`) → `core/audit.py` ghi log → `workers/` gửi email.
- Bắt buộc: verify chữ ký webhook, idempotency, log đầy đủ transaction.

---

## Giai đoạn 5 — DevOps & Infrastructure

1. Containerize: Dockerfile backend + frontend, `docker-compose.yml` (Postgres, Redis, backend, frontend, nginx).
2. CI/CD: GitHub Actions — lint + test khi push, build & deploy khi merge `main`. Có thể tách CI theo module (chỉ chạy test của module thay đổi) để pipeline nhanh hơn khi dự án lớn dần.
3. Tách môi trường `dev/staging/production`, secret qua GitHub Secrets.
4. Hosting: VPS VN hoặc DigitalOcean/AWS Lightsail.
5. Nginx reverse proxy + SSL.
6. Monitoring: Sentry + UptimeRobot.
7. Backup DB định kỳ lên S3/MinIO.
8. Redis: cache (catalog — ít đổi, đọc nhiều) + rate limiting + Celery broker (nếu dùng).

---

## Giai đoạn 6 — Security & Compliance

- HTTPS toàn site, CORS chặt theo domain.
- Rate limiting ở `core/middlewares.py`, cấu hình riêng cho endpoint nhạy cảm (login, tạo order/lead).
- Login throttling: 5 lần/phút, khoá tạm sau khi vượt ngưỡng.
- Password policy: tối thiểu 8 ký tự, có chữ và số.
- JWT: access 4h, refresh 7d, refresh token lưu Redis/DB để revoke được khi logout.
- File Security: validate type/size ảnh xe khi admin upload, quét malware cơ bản, lưu MinIO (S3-compatible).
- Input validation ở `schema.py` (Pydantic) của từng module, validate nghiệp vụ thêm ở `service.py`.
- Trang chính sách bảo mật + consent, tuân Nghị định 13/2023 VN.
- Không lưu thông tin thẻ thanh toán trực tiếp.

---

## Giai đoạn 7 — Testing & QA

- Unit test `service.py` từng module (mock `repository.py`) — nhanh, viết song song lúc code module đó.
- Integration test `repository.py` + `api.py` (DB test container).
- Test riêng ranh giới module: đảm bảo module A thật sự chỉ gọi qua `B/service.py`, không có import lén `B/repository.py` (có thể check bằng lint rule/script đơn giản).
- Frontend: component test + E2E Playwright cho luồng đặt cọc.
- Load test nhẹ bằng Locust nếu dự tính có traffic quảng cáo.
- UAT trước khi launch.

---

## Giai đoạn 8 — Launch

- Soft launch, theo dõi log/error sát sao vài ngày đầu.
- Rollback plan sẵn sàng.
- Checklist: SSL, backup DB đã test restore, thanh toán đã test hết case.

---

## Giai đoạn 9 — AI Agent Chatbot (module `ai_agent`, client của các module có sẵn)

- `ai_agent/tools/` chứa các wrapper mỏng, mỗi tool gọi thẳng 1 hàm ở `service.py` module tương ứng:
  - `get_vehicle_detail_tool` → gọi `catalog/service.get_vehicle_detail()`
  - `get_order_status_tool` → gọi `orders/service.get_status()`
  - `submit_lead_tool` → gọi `leads/service.create_lead()`
- **Không viết logic nghiệp vụ mới trong `ai_agent/`** — nếu thấy mình đang tính giá, check tồn kho, hay validate trạng thái đơn ngay trong `tools/`, đó là dấu hiệu đang phá vỡ ranh giới module, phải chuyển logic đó vào `service.py` của module tương ứng rồi gọi lại.
- `ai_agent/rag/`: đồng bộ embedding từ chính DB `catalog` (không phải tài liệu tĩnh) để luôn khớp giá/tồn kho thật — dùng lại kinh nghiệm OpenSearch/bge-m3 của anh ở `ai_service`.
- Permission: agent gọi `check_permission()` giống hệt luồng admin — không viết RBAC riêng cho AI.
- Vì `ai_agent` phụ thuộc mọi module khác (theo sơ đồ mục 1.2), nó nên là module **build sau cùng**, đúng như kế hoạch ban đầu.

---

## Gợi ý thứ tự triển khai thực tế theo tuần

| Tuần | Việc chính |
|---|---|
| 1 | PRD, ERD theo nhóm module, sơ đồ phụ thuộc module (`docs/module-dependency.md`), API contract |
| 2 | `core/` (config, database Base, exceptions) + `modules/users/` (Auth, RBAC, departments) |
| 3 | `core/audit.py` + `modules/catalog/` |
| 4 | `modules/leads/` + `modules/orders/` (state machine) |
| 5 | `modules/payments/` (VNPay sandbox) + `workers/` |
| 6-7 | Frontend: Next.js landing + chi tiết xe + luồng đặt cọc |
| 8 | Admin dashboard (menu động, department, audit log UI) |
| 9 | Docker hoá, CI/CD |
| 10 | Testing E2E (kèm test ranh giới module), security review |
| 11 | Deploy production, soft launch |
| 12+ | `modules/ai_agent/` — tool gọi vào các module có sẵn |

---

### Lưu ý quan trọng cho anh

- Đây là **Modular Monolith** — vẫn 1 database, 1 codebase, 1 lần deploy, không phải microservice. Lợi ích chính là ranh giới rõ ràng trong code, không phải tách hạ tầng.
- 2 quy tắc sống còn để kiến trúc này không sụp đổ sau vài tháng: **(1)** gọi module khác luôn qua `service.py`, không bao giờ import thẳng `repository.py`/`model.py` của module khác; **(2)** cross-cutting (audit, notification chung) nằm ở `core/`, không nhét vào 1 module cụ thể.
- Nếu sau này 1 module (thường là `orders` hoặc `payments`) tăng trưởng phức tạp tới mức cần tách domain entity riêng khỏi SQLAlchemy model — hoàn toàn có thể áp Clean Architecture **cho riêng module đó**, không cần đổi kiến trúc toàn bộ hệ thống. Đây là lợi thế lớn nhất của Modular Monolith: áp dụng độ phức tạp kiến trúc theo đúng nhu cầu thực tế của từng phần, không ép 1 khuôn cho tất cả.