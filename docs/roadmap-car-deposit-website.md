# Roadmap xây dựng Website đặt cọc xe (kiểu VinFast) — Production-grade

> Bối cảnh: anh là AI dev, muốn làm 1 dự án full-stack thật (không phải demo học tập) để bao quát thêm role dev. Stack: **React (Next.js) + FastAPI**, tích hợp **AI Agent chatbot** ở giai đoạn cuối.

Sau khi xem trang tham khảo, mô hình thực tế gồm 3 mảng tách biệt:
1. **Landing/Marketing site** — giới thiệu xe, thông số, màu sắc, so sánh chi phí, form thu lead (giống trang anh gửi).
2. **Order/Shop system** — luồng đặt cọc thật: chọn phiên bản/màu → tạo đơn → thanh toán → theo dõi trạng thái.
3. **Admin/CMS** — quản lý xe, đơn hàng, khách hàng, nội dung.

Một dự án thật luôn đi theo thứ tự: **Discovery → Design → Backend → Frontend → Tích hợp thanh toán → DevOps → Security → Test → Launch → (sau đó) AI**. Đừng nhảy cóc vào code ngay.

---

## Giai đoạn 0 — Discovery & Business Requirement (1 team thật luôn làm bước này trước)

Trước khi code, viết ra (dạng markdown trong repo, thư mục `docs/`):

- **Đối tượng dùng**: khách hàng cuối (public), nhân viên sale/admin, (sau này) AI agent.
- **Use case chính** (viết dạng user story):
  - Khách xem danh sách xe → xem chi tiết → chọn phiên bản/màu/option → đặt cọc → thanh toán → nhận email xác nhận → theo dõi trạng thái đơn.
  - Khách đăng ký lái thử / để lại thông tin tư vấn (lead capture).
  - Admin quản lý catalog xe, xem/duyệt đơn cọc, xem danh sách lead.
- **Phạm vi MVP** (đừng làm full như VinFast ngay): 1-2 mẫu xe, mỗi xe vài phiên bản/màu, 1 cổng thanh toán, không cần multi-dealer/showroom.
- **Non-functional requirements**: cần SEO tốt (landing công khai) → chọn Next.js SSR/SSG chứ không phải React CRA SPA thuần; cần chịu tải khi có traffic quảng cáo; bảo mật vì thu thập PII + thanh toán.

Output của giai đoạn này: 1 file `docs/prd.md` (Product Requirements Document) — đây là thứ một dev thật sẽ có trước khi viết dòng code đầu tiên.

---

## Giai đoạn 1 — System Design & Architecture

### 1.1 Kiến trúc tổng thể
Bắt đầu **monolith có cấu trúc rõ ràng** (không cần microservice ngay, anh đã có kinh nghiệm layered `core/services/pipelines` từ `ai_service` — áp dụng tương tự):

```
car-booking-platform/
├── backend/          # FastAPI monolith
│   ├── core/         # config, db session, security, exceptions
│   ├── models/       # SQLAlchemy models
│   ├── schemas/      # Pydantic schemas
│   ├── repositories/ # DB access layer
│   ├── services/      # business logic
│   ├── api/v1/        # routers
│   └── tests/
├── frontend/          # Next.js
├── infra/             # docker-compose, nginx, ci-cd
└── docs/
```

### 1.2 Thiết kế Database (ERD) — vẽ trước khi code
Bảng cốt lõi:
- `users` (customer + admin, role-based)
- `vehicles`, `vehicle_variants` (phiên bản), `vehicle_colors`, `vehicle_options`
- `orders` (đơn đặt cọc): trạng thái `pending → paid → confirmed → cancelled`
- `payments` (liên kết order, lưu transaction id, gateway, trạng thái webhook)
- `leads` (form tư vấn/đăng ký lái thử)
- `promotions` (mã ưu đãi, giống banner "Ưu đãi tới 31/12" trên trang mẫu)

Dùng PostgreSQL. Vẽ ERD bằng dbdiagram.io hoặc draw.io trước, lưu vào `docs/erd.png`.

### 1.3 Thiết kế API contract trước (API-first)
Viết OpenAPI spec / hoặc phác thảo endpoint trước khi code service:
```
GET  /api/v1/vehicles
GET  /api/v1/vehicles/{slug}
POST /api/v1/orders               # tạo đơn đặt cọc
POST /api/v1/orders/{id}/payment  # khởi tạo thanh toán
POST /api/v1/webhooks/payment     # gateway callback
POST /api/v1/leads                # form tư vấn
GET  /api/v1/admin/orders         # admin, cần auth + role
```
FastAPI tự sinh Swagger UI (`/docs`) — tận dụng cái này để frontend dev song song mà không cần đợi backend hoàn thiện 100%.

---

## Giai đoạn 2 — Backend Development (FastAPI)

Thứ tự build thực tế (không phải viết hết 1 lúc):

1. **Project skeleton**: config qua `pydantic-settings`, DB session (SQLAlchemy async + `asyncpg`), Alembic cho migration (rất quan trọng — dự án thật luôn version hoá schema DB).
2. **Auth module**: JWT (access + refresh token), password hashing (`bcrypt`/`argon2`), RBAC đơn giản (`customer`, `admin`).
3. **Vehicle catalog module**: CRUD xe/phiên bản/màu — đây là phần đơn giản để làm quen pattern layered của anh.
4. **Order/Deposit module**: đây là phần lõi nghiệp vụ — state machine cho trạng thái đơn, validate tồn kho/số lượng cọc tối đa nếu cần.
5. **Payment module**: tích hợp cổng thanh toán VN (VNPay/MoMo/ZaloPay có sandbox miễn phí) — service riêng, xử lý webhook idempotent (rất hay bị lỗi nếu không cẩn thận, cổng có thể gọi webhook nhiều lần).
6. **Lead/CRM-lite module**: lưu form tư vấn, gửi email thông báo (SMTP hoặc SES).
7. **Admin API**: endpoint riêng cho dashboard quản trị, có phân quyền.
8. **Testing**: pytest + `httpx.AsyncClient` cho integration test, đặc biệt test kỹ luồng payment (mock gateway).

> Vì anh vốn mạnh async Python — đây là điểm anh sẽ áp dụng tốt kinh nghiệm streaming/async generator đã làm với Groq vào việc xử lý webhook, background task (dùng `BackgroundTasks` của FastAPI hoặc Celery nếu cần retry đáng tin cậy).

---

## Giai đoạn 3 — Frontend Development (Next.js/React)

Vì đây là trang public cần SEO tốt (giống trang VinFast index bởi Google) → **bắt buộc dùng Next.js**, không dùng React SPA thuần (Vite/CRA sẽ yếu SEO cho landing page xe).

1. **Setup**: Next.js (App Router) + TypeScript + TailwindCSS + component library (shadcn/ui).
2. **Design system cơ bản**: màu sắc, typography, button, card — dựa theo 1 bộ token đơn giản trước khi build trang.
3. **Trang chính** (đi theo đúng thứ tự trang VinFast mẫu):
   - Trang chủ / landing xe (hero, thông số, màu sắc — dùng SSG vì ít đổi).
   - Trang chi tiết xe + chọn cấu hình (color picker, variant selector) — client component vì có tương tác.
   - Trang đặt cọc/checkout (form + tích hợp payment redirect).
   - Trang tài khoản khách hàng (theo dõi đơn).
   - Form tư vấn/lead capture (giống form "NHẬN TƯ VẤN" trên trang mẫu).
   - Trang admin (có thể tách app riêng `admin.yourdomain.com` hoặc route riêng `/admin`).
4. **State/data fetching**: React Query (TanStack Query) để gọi API, không tự quản state thủ công.
5. **Tối ưu**: `next/image` cho ảnh xe, lazy load, Lighthouse audit trước khi launch.

---

## Giai đoạn 4 — Payment & Third-party Integration

- Đăng ký sandbox VNPay/MoMo (miễn phí, có docs tiếng Việt rõ ràng — hợp vì đây là dự án target VN).
- Luồng chuẩn: FE gọi BE tạo order → BE gọi gateway tạo payment URL → redirect khách sang gateway → gateway callback (webhook) về BE → BE verify checksum/signature → update trạng thái order → FE poll hoặc dùng websocket để cập nhật trạng thái.
- **Bắt buộc**: verify chữ ký webhook, xử lý idempotency (tránh cộng dồn nếu gateway gọi lại), log đầy đủ transaction.

---

## Giai đoạn 5 — DevOps & Infrastructure

Đây là phần khiến dự án "giống thật" nhất vì đa số demo học tập bỏ qua:

1. **Containerize**: Dockerfile cho backend + frontend, `docker-compose.yml` cho local dev (Postgres, Redis, backend, frontend, nginx).
2. **CI/CD**: GitHub Actions — chạy lint + test khi push, build & deploy khi merge vào `main`.
3. **Môi trường**: tách `dev / staging / production`, quản lý secret bằng `.env` + GitHub Secrets (không commit secret).
4. **Hosting**: VPS (Vietnam: Viettel Cloud, VNG Cloud; hoặc quốc tế: DigitalOcean/AWS Lightsail cho chi phí thấp khi mới launch) + domain + SSL (Let's Encrypt hoặc Cloudflare).
5. **Reverse proxy**: Nginx trước backend + frontend, cấu hình cache cho static asset.
6. **Monitoring cơ bản**: Sentry (error tracking) + uptime monitor (UptimeRobot) — không cần Prometheus/Grafana phức tạp ngay từ đầu.
7. **Backup DB**: cron job backup Postgres định kỳ lên S3/MinIO (anh đã có kinh nghiệm MinIO — dùng lại).

---

## Giai đoạn 6 — Security & Compliance

- HTTPS bắt buộc toàn site, CORS cấu hình chặt (chỉ domain của mình).
- Rate limiting cho API (đặc biệt endpoint tạo order/lead để tránh spam).
- Input validation nghiêm ngặt qua Pydantic (anh vốn quen), sanitize output tránh XSS ở frontend.
- Vì thu thập dữ liệu cá nhân (giống form "đồng ý cho xử lý dữ liệu cá nhân" trên trang mẫu) → cần có trang chính sách bảo mật + cơ chế consent, tuân Nghị định 13/2023 về bảo vệ dữ liệu cá nhân VN.
- Không lưu thông tin thẻ thanh toán trực tiếp — luôn qua gateway (PCI compliance nằm ở phía gateway).

---

## Giai đoạn 7 — Testing & QA

- Backend: unit test (service layer) + integration test (API, DB test container).
- Frontend: component test cơ bản, E2E test luồng chính bằng Playwright (đặc biệt luồng đặt cọc — đây là luồng tiền nên phải test kỹ nhất).
- Load test nhẹ bằng Locust nếu dự tính có traffic từ quảng cáo.
- UAT: tự chạy thử toàn bộ luồng như 1 khách hàng thật trước khi launch.

---

## Giai đoạn 8 — Launch

- Soft launch (giới hạn traffic, theo dõi log/error sát sao vài ngày đầu).
- Rollback plan: giữ version trước sẵn sàng deploy lại nếu lỗi nghiêm trọng.
- Checklist trước launch: SSL, backup DB đã chạy thử restore, thanh toán đã test hết case thành công/thất bại/timeout.

---

## Giai đoạn 9 — AI Agent Chatbot (sau khi backend/frontend ổn định)

Đây là phần anh mạnh nhất, tích hợp sau khi có nền tảng:

- **Kiến trúc**: 1 service riêng (tách khỏi core backend, giống pattern `ai_service` anh đang làm) expose qua gRPC/REST, gọi vào backend chính qua API nội bộ.
- **Khả năng agent nên có**:
  - Tư vấn xe dựa trên catalog thật (RAG trên dữ liệu xe/FAQ, không hallucinate thông số).
  - Tool-calling: kiểm tra tồn kho, tạo lead, thậm chí hỗ trợ tạo đơn đặt cọc qua hội thoại.
  - Đặt lịch lái thử qua chat.
- **Nguồn dữ liệu cho RAG**: đồng bộ từ chính DB catalog xe (không phải tài liệu tĩnh) để luôn cập nhật giá/tồn kho.
- Đây chính là lúc dùng lại kinh nghiệm OpenSearch/embedding/agent MCP mà anh đã làm ở `ai_service`.

---

## Gợi ý thứ tự triển khai thực tế theo tuần (MVP trước, mở rộng sau)

| Tuần | Việc chính |
|---|---|
| 1 | Viết PRD, vẽ ERD, thiết kế API contract |
| 2-3 | Backend: auth + catalog module + migration |
| 4 | Backend: order module + payment sandbox |
| 5-6 | Frontend: setup Next.js, trang landing + chi tiết xe |
| 7 | Frontend: luồng đặt cọc + checkout |
| 8 | Docker hoá, CI/CD cơ bản, deploy staging |
| 9 | Testing E2E luồng thanh toán, security review |
| 10 | Deploy production, soft launch |
| 11+ | AI Agent chatbot tích hợp |

---

### Lưu ý quan trọng cho anh (từ góc nhìn AI dev chuyển sang full dev)
- Đừng cố làm giống 100% VinFast (multi-dealer, đa ngôn ngữ, ADAS comparison tool...) — quá rộng cho 1 người. Làm MVP thật gọn nhưng **đúng chuẩn production** (có auth thật, có payment thật, có CI/CD thật) sẽ có giá trị học tập cao hơn nhiều so với làm rộng nhưng hời hợt.
- Phần khó nhất với dev mới thường không phải là code mà là **thiết kế state machine cho đơn hàng** và **xử lý webhook thanh toán đúng cách** — nên dành thời gian đọc kỹ docs gateway trước khi code.
