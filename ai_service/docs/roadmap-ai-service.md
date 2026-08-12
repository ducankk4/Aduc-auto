# Kế hoạch & Scope — AI Service (Layered Architecture + Deep Agents)

> Tài liệu này được viết sau khi đọc trực tiếp source backend (`backend/src/app/**`), không suy đoán từ roadmap. Mọi tool trong mục 5 đều ánh xạ tới một endpoint **có thật** trong code hiện tại. Mục 9 liệt kê các khoảng trống backend chặn một phần scope — cần quyết định trước khi vào Phase 2 trở đi.

---

## 1. Mục tiêu

Xây `ai-service` chạy độc lập, giao tiếp với backend FastAPI **chỉ qua HTTP**, đóng vai trò **conversational client** của các module nghiệp vụ đã có (`users`, `catalog`, `leads`, `orders`, `payments`).

### Nguyên tắc bất biến (không được vi phạm ở bất kỳ phase nào)

| # | Nguyên tắc | Hệ quả kiểm tra được |
|---|---|---|
| 1 | AI service **không** kết nối DB nghiệp vụ | `ai_service` không có `asyncpg`/`sqlalchemy` trỏ tới `aduc_auto_db` |
| 2 | Không có business logic nghiệp vụ xe trong ai-service | Không tính giá, không tính tiền cọc, không tự validate transition trạng thái đơn |
| 3 | RBAC do backend quyết định, AI **không** tự phân quyền | ai-service không có bảng role/permission riêng; chỉ forward token |
| 4 | Mọi thao tác ghi phải qua bước xác nhận của người dùng | Tool ghi luôn tạo `PendingAction`, không bao giờ gọi thẳng |
| 5 | Dữ liệu động (giá, tồn kho, trạng thái đơn) luôn từ API, **không** từ RAG | RAG chỉ chứa nội dung tĩnh: mô tả, FAQ, chính sách |
| 6 | Subagent không gọi lẫn nhau; chỉ supervisor điều phối | |

---

## 2. Ranh giới trách nhiệm

| Việc | Thuộc về |
|---|---|
| Hiểu ý định, hỏi lại thông tin thiếu, tổng hợp câu trả lời | **ai-service** |
| Quản lý hội thoại, checkpoint, pending action | **ai-service** |
| Truy xuất nội dung tư vấn dài (RAG) | **ai-service** |
| Giá, tiền cọc, tính hợp lệ variant/color, state machine đơn | **backend** |
| Xác thực JWT, kiểm tra permission `resource:action` | **backend** |
| Thanh toán VNPay, webhook, audit log, gửi email | **backend** |

> ai-service **không** xử lý thanh toán. Tối đa nó gọi `POST /payments/{order_id}/init` để lấy `payment_url` rồi trả link cho người dùng bấm.

---

## 3. Kiến trúc — Layered Architecture

```text
ai_service/
└── src/ai_service/
    ├── presentation/
    │   ├── api/                  # FastAPI router: /chat, /chat/stream, /chat/confirm, /health
    │   ├── dependencies.py       # trích Bearer token, session_id từ request
    │   └── schemas/              # Request/Response DTO (Pydantic)
    │
    ├── application/
    │   ├── use_cases/            # send_message, confirm_action, reject_action, get_history
    │   ├── orchestration/
    │   │   ├── supervisor.py     # Deep Agent điều phối
    │   │   ├── subagents/        # catalog_advisor, lead_agent, order_agent, admin_agent
    │   │   └── prompts/          # system prompt tách file, versioned
    │   ├── tools/                # tool định nghĩa — adapter mỏng gọi ports
    │   ├── ports/                # Protocol: BackendPort, RetrieverPort, ConversationPort, LLMPort
    │   └── dto/
    │
    ├── domain/                   # CHỈ state riêng của AI, không copy entity backend
    │   ├── pending_action.py     # PendingAction + payload hash
    │   ├── actor.py              # AuthContext: token, is_authenticated, permissions
    │   └── enums.py              # ConfirmationStatus, AgentRole
    │
    ├── infrastructure/
    │   ├── backend/              # httpx.AsyncClient + typed client cho từng module backend
    │   ├── rag/                  # ingestion, embedding, vector store adapter
    │   ├── persistence/          # LangGraph checkpointer + conversation store
    │   └── llm/                  # model factory
    │
    ├── bootstrap/                # wiring DI, build agent graph 1 lần lúc startup
    └── config.py
```

### Quy tắc phụ thuộc

```text
presentation  →  application  →  domain
infrastructure →  application.ports + domain     (implement, không bị import ngược)
bootstrap     →  nối implementation vào ports
```

- `domain/` không import FastAPI, LangChain, LangGraph, httpx.
- `application/` chỉ biết `ports`, không import `infrastructure`.
- Tool **chỉ** chuyển đổi input/output và gọi port. Nếu thấy mình đang cộng giá hay so sánh trạng thái trong `tools/` → logic đó thuộc backend.

---

## 4. Thiết kế Multi-agent (Deep Agent)

### 4.1 Supervisor

Nhiệm vụ: phân loại ý định → lập kế hoạch ngắn (todo list) → giao việc cho subagent → tổng hợp câu trả lời cuối. **Không** giữ tool nghiệp vụ nào ngoài `write_todos` và delegation tool.

Đặc tính Deep Agent áp dụng:
- **Planning tool** (`write_todos`): cần cho các yêu cầu ghép nhiều bước ("tư vấn xe rồi đặt cọc luôn").
- **Subagent delegation**: mỗi subagent có context window riêng → prompt và tool set gọn, không bị nhiễu.
- **Detailed system prompt**: quy tắc xác nhận, quy tắc không bịa giá, quy tắc RBAC.
- **Virtual filesystem**: *không cần* ở MVP. Chỉ bật khi có tác vụ so sánh nhiều xe cần nháp trung gian (Phase 6).

### 4.2 Bảng subagent

| Subagent | Phạm vi | Tool | Auth cần | Ghi dữ liệu |
|---|---|---|---|---|
| `catalog_advisor` | Tìm/tư vấn/so sánh xe, giải thích cấu hình, FAQ, chính sách | `list_vehicles`, `get_vehicle_detail`, `rag_search` | Không | Không |
| `lead_agent` | Thu thập thông tin tư vấn / đăng ký lái thử | `get_vehicle_detail`, `submit_lead` | Không | Có |
| `order_agent` | Tra cứu đơn, dựng nháp đơn cọc, chuyển sang thanh toán | `get_vehicle_detail`, `create_order`, `get_order_by_code`, `list_my_orders`, `init_payment` | Có (xem 9.4) | Có |
| `admin_agent` | Tra cứu & cập nhật đơn/lead/catalog bằng ngôn ngữ tự nhiên | `admin_list_orders`, `admin_update_order_status`, `admin_list_leads`, `admin_update_lead_status`, `admin_catalog_*` | Có + permission | Có |

**Quy tắc bật `admin_agent`:** supervisor chỉ được thấy `admin_agent` trong roster khi `AuthContext.role == "admin"` hoặc token có ít nhất một permission `orders:*` / `leads:*` / `catalog:*`. Đây là **defense in depth** — backend vẫn là nơi chặn thật; việc ẩn subagent chỉ để agent không lãng phí lượt gọi và không hứa hẹn việc nó không làm được.

> Chưa tách `knowledge_agent` riêng ở MVP. Nội dung FAQ/chính sách gộp vào `catalog_advisor` qua cùng một retriever. Chỉ tách khi corpus policy đủ lớn và cần prompt trích dẫn khác biệt (Phase 6).

---

## 5. Tool catalog — ánh xạ 1:1 với endpoint backend hiện có

Prefix backend: `/api/v1`.

### Read-only (không cần xác nhận)

| Tool | Endpoint | Ghi chú |
|---|---|---|
| `list_vehicles(page, limit)` | `GET /catalog/vehicles` | Public. **Chưa có filter** — xem 9.1 |
| `get_vehicle_detail(slug)` | `GET /catalog/vehicles/{slug}` | Trả kèm `variants[]` + `colors[]` |
| `get_order_by_code(order_code)` | `GET /orders/{order_code}` | **Bắt buộc Bearer token** — xem 9.4 |
| `list_my_orders(page, limit)` | `GET /orders/me` | Bắt buộc token |
| `admin_list_orders(status, page, limit)` | `GET /admin/orders` | Cần `orders:read` |
| `admin_list_leads(status, page, limit)` | `GET /leads` | Cần `leads:read` |
| `rag_search(query, top_k)` | — | Vector store nội bộ ai-service |

### Write (bắt buộc `PendingAction` + xác nhận)

| Tool | Endpoint | Permission backend |
|---|---|---|
| `submit_lead(...)` | `POST /leads` | Public (rate limit — xem 9.6) |
| `create_order(...)` | `POST /orders` | Optional auth (guest được) |
| `init_payment(order_id)` | `POST /payments/{order_id}/init` | Bắt buộc token |
| `admin_update_order_status(order_id, status, note)` | `PATCH /admin/orders/{id}/status` | `orders:update_status` |
| `admin_update_lead_status(lead_id, status)` | `PATCH /leads/{id}/status` | `leads:write` |
| `admin_create_vehicle` / `admin_update_vehicle` | `POST` / `PUT /catalog/vehicles` | `catalog:write` |
| `admin_add_variant` / `admin_add_color` | `POST /catalog/vehicles/{id}/variants|colors` | `catalog:write` |
| `admin_delete_variant` / `admin_delete_color` | `DELETE /catalog/variants|colors/{id}` | `catalog:write` |

### Enum phải khớp backend (không được tự chế)

```text
OrderStatus:  pending | paid | confirmed | cancelled | refunded
  Transition hợp lệ: pending→{paid,cancelled}; paid→{confirmed,refunded}; còn lại terminal
LeadStatus:   new | contacted | qualified | lost | converted
```

Tool `admin_update_order_status` chỉ **liệt kê** transition hợp lệ cho người dùng chọn (đọc từ hằng số đồng bộ hoá), còn **việc chặn transition sai vẫn để backend raise lỗi** — AI không tự quyết.

### Xử lý response

Backend trả format thống nhất:
```json
{ "success": true,  "data": ..., "meta": {"page":1,"limit":20,"total":50} }
{ "success": false, "error": {"code": "...", "message": "..."} }
```
`BackendPort` unwrap `data`/`error` một chỗ duy nhất; tool nhận DTO đã typed, và **trả nguyên `error.message` tiếng Việt của backend cho agent** thay vì tự diễn giải lại lỗi.

---

## 6. Auth & RBAC — mô hình token pass-through

Đây là quyết định kiến trúc quan trọng nhất về bảo mật.

```text
Frontend ──(Bearer JWT của user)──▶ ai-service ──(forward nguyên token)──▶ backend
```

- ai-service **không** giữ service account admin. Không có "AI user" quyền cao trong DB.
- ai-service **không** decode để phân quyền. Nó chỉ decode (không verify chữ ký) để đọc `role`/`permissions` phục vụ việc **ẩn/hiện subagent** — mọi quyết định cho phép thật do `check_permission()` của backend.
- Chat ẩn danh (không token) → chỉ `catalog_advisor` + `lead_agent`.
- Token hết hạn → backend trả 401 → ai-service trả thông điệp "phiên đăng nhập hết hạn, vui lòng đăng nhập lại", **không** tự refresh (refresh token không nên đi qua ai-service).

**Không lưu JWT vào conversation state / checkpoint.** Token chỉ sống trong request scope, truyền qua `context_schema` của agent runtime, không được ghi vào LangGraph checkpoint (checkpoint sẽ persist ra DB).

---

## 7. RAG

| Hạng mục | Quyết định |
|---|---|
| Corpus | Mô tả xe dạng dài, FAQ, chính sách đặt cọc/hủy/hoàn tiền, so sánh chi phí sử dụng, hướng dẫn lái thử |
| **Không** đưa vào corpus | Giá, `price_extra` màu, tiền cọc, tồn kho, trạng thái đơn — luôn gọi API |
| Nguồn | 2 nguồn: (a) `description` của vehicle sync từ `GET /catalog/vehicles/{slug}`, (b) file markdown chính sách/FAQ do team soạn trong `ai_service/knowledge/` |
| Embedding | Nhiều provider chat model không có embeddings API (kể cả provider đang dùng cho chat model, xem `infrastructure/llm/factory.py`) → dùng bge-m3 self-host (đúng kinh nghiệm sẵn có) hoặc dịch vụ embedding riêng, kiểm tra riêng lúc chọn |
| Vector store | pgvector (DB riêng của ai-service) cho MVP; Qdrant/OpenSearch nếu cần scale |
| Đồng bộ | Job định kỳ + trigger thủ công; mỗi chunk gắn `vehicle_slug`, `source`, `synced_at` |
| Chống lệch dữ liệu | Chunk mô tả xe **không chứa số giá**. Nếu mô tả gốc có giá, strip khi ingest. Prompt bắt buộc: "khi nói tới giá/cọc, phải gọi tool, không dùng nội dung truy xuất" |

---

## 8. Human-in-the-loop (HITL)

Cơ chế:

1. Agent quyết định gọi tool ghi → runtime `interrupt()` trước khi thực thi (dùng `HumanInTheLoopMiddleware` của LangChain 1.x, đã có sẵn trong `langchain/agents/middleware/human_in_the_loop.py`).
2. Application layer lưu `PendingAction{ id, session_id, tool_name, payload, payload_hash, created_at, expires_at }`.
3. Trả về client bản tóm tắt dễ đọc (không phải JSON thô) + `pending_action_id`.
4. Client gọi `POST /chat/confirm` với `pending_action_id` → resume graph → tool chạy.

Ràng buộc:
- **Payload bất biến**: nếu hội thoại thay đổi payload sau khi hiển thị, `payload_hash` đổi → yêu cầu xác nhận lại.
- **TTL** (đề xuất 15 phút) — hết hạn phải xác nhận lại, tránh tạo đơn theo giá cũ.
- **Idempotency**: mỗi `PendingAction` chỉ thực thi 1 lần; đánh dấu `consumed` trước khi gọi backend. Xem thêm 9.5.

---

## 9. Khoảng trống ở backend — cần quyết định

Đây là các điểm phát hiện khi đọc code, chặn hoặc làm xấu một phần scope. Phân loại: 🔴 chặn tính năng · 🟡 làm giảm chất lượng · 🟢 nên có.

### 9.1 🟡 Catalog không có search/filter
`GET /catalog/vehicles` chỉ nhận `page`, `limit`. `catalog_advisor` không thể lọc theo ngân sách/phân khúc/từ khoá — buộc phải kéo toàn bộ danh sách rồi lọc trong prompt. Chấp nhận được với MVP 1–2 mẫu xe, **không** scale.
→ Đề xuất backend thêm `?q=&category=&min_price=&max_price=&is_active=`.

### 9.2 🔴 Không resolve được `variant_id` / `color_id` → tên xe
`OrderResponseSchema` chỉ trả `variant_id`, `color_id` (UUID). Không có endpoint public nào tra variant/color theo ID (`CatalogService.get_variant` tồn tại nhưng **không expose qua API**). Hệ quả: khi tra cứu đơn, AI không thể hiển thị "VF8 bản Plus màu Xanh" mà chỉ có UUID.
→ Đề xuất: (a) enrich `OrderResponseSchema` thêm `vehicle_name`, `variant_name`, `color_name` — **giải pháp tốt nhất**, hoặc (b) thêm `GET /catalog/variants/{id}`, `GET /catalog/colors/{id}`.

### 9.3 🔴 Không có endpoint preview/quote đơn hàng
`deposit_amount` đang **hard-code `Decimal("50000000.00")`** trong `OrderService.create()` ([orders/service.py:67](backend/src/app/modules/orders/service.py#L67)). Không có API nào trả tiền cọc trước khi tạo đơn. AI không thể hiển thị con số cọc chính thức ở bước xác nhận — nếu tự hard-code lại 50tr thì đã vi phạm nguyên tắc #2.
→ Đề xuất `POST /orders/preview` nhận `variant_id`, `color_id`, trả `{vehicle_name, variant_name, color_name, variant_price, color_price_extra, deposit_amount}`. Đây là **điều kiện tiên quyết của Phase 4**.

### 9.4 🔴 Guest tạo được đơn nhưng không tra cứu được đơn
`POST /orders` cho phép guest (`credentials` optional), nhưng `GET /orders/{order_code}` bắt buộc `get_current_user` → 401. Khách vãng lai đặt cọc qua chatbot rồi không tra cứu được chính đơn của mình.
→ Đề xuất: `GET /orders/lookup?order_code=...&phone=...` (xác minh 2 yếu tố, rate-limited), hoặc chấp nhận scope: **tra cứu đơn chỉ dành cho user đã đăng nhập** (quyết định sản phẩm, cần chốt trước Phase 3).

### 9.5 🟢 `POST /orders` không có idempotency key
Agent retry (timeout mạng, người dùng bấm xác nhận 2 lần) có thể tạo 2 đơn trùng. Hiện `order_code` sinh ngẫu nhiên nên backend không tự chặn được.
→ Ngắn hạn: ai-service tự khoá bằng `PendingAction.consumed`. Dài hạn: backend nhận header `Idempotency-Key`.

### 9.6 🔴 Rate limit lead theo IP sẽ bóp nghẹt chatbot
`_enforce_rate_limit` trong [leads/api.py](backend/src/app/modules/leads/api.py) giới hạn **10 request/phút/IP**, lưu in-memory theo `request.client.host`. ai-service là **một IP duy nhất** → toàn bộ lead do AI gửi dùng chung 1 bucket 10/phút cho mọi khách hàng. Vượt ngưỡng → tất cả khách đều bị chặn.
→ Bắt buộc xử lý: backend đọc `X-Forwarded-For` / header `X-Client-IP` do ai-service truyền lên, hoặc allowlist theo service token. **Đây là blocker của Phase 2.**

### 9.7 🟡 `vehicle_options` tồn tại trong DB nhưng không có API
`OptionModel` có bảng `vehicle_options`, nhưng: không có endpoint, không nằm trong `VehicleResponseSchema`, và `OrderCreateSchema` không có trường option.
→ Kết luận: **loại "chọn option" khỏi scope AI** cho tới khi backend hỗ trợ. Không hứa với người dùng tính năng này.

### 9.8 🟡 Lead không có trường lịch lái thử
`LeadCreateSchema` chỉ có `vehicle_id`, `customer_name`, `phone`, `email`, `showroom_pref` (string tự do). Không có ngày/giờ mong muốn. Danh sách showroom nằm ở `GET /admin/users/departments` — **cần `users:manage`**, nên luồng công khai không liệt kê được showroom.
→ Scope AI: "đăng ký lái thử" = tạo lead + ghi nguyện vọng showroom dạng text. **Không** hứa đặt lịch theo giờ.

### 9.9 🟢 Guest order nuốt lỗi token
[orders/api.py](backend/src/app/modules/orders/api.py): `except Exception: pass` — token hết hạn/sai sẽ âm thầm thành đơn guest thay vì báo lỗi. Với chatbot, user đang đăng nhập có thể tạo ra đơn không gắn `user_id` → sau đó `GET /orders/me` không thấy đơn.
→ Đề xuất phân biệt "không có token" (guest, OK) với "có token nhưng không hợp lệ" (401).

### 9.10 🟢 CORS `allow_origins=["*"]` kèm `allow_credentials=True`
Cấu hình này trình duyệt sẽ từ chối, và sắp tới thêm origin của ai-service. Nên siết theo domain trước khi lên staging.

---

## 10. API contract của ai-service

```text
POST /api/v1/chat                  # đồng bộ, trả full message
POST /api/v1/chat/stream           # SSE: token + trạng thái (đang tra cứu / chờ xác nhận)
POST /api/v1/chat/confirm          # { session_id, pending_action_id }
POST /api/v1/chat/reject           # { session_id, pending_action_id, reason? }
GET  /api/v1/chat/{session_id}     # lịch sử hội thoại
GET  /health
```

Request `/chat`:
```json
{ "session_id": "uuid|null", "message": "string" }
```
Header: `Authorization: Bearer <JWT của user>` (optional), `X-Client-IP` (forward cho rate limit backend — xem 9.6).

Response:
```json
{
  "success": true,
  "data": {
    "session_id": "...",
    "reply": "...",
    "pending_action": { "id": "...", "summary": "...", "expires_at": "..." } 
  }
}
```
Giữ đúng format `{success, data, error}` của backend để frontend dùng chung một lớp xử lý.

---

## 11. Lộ trình theo phase

Đi từ read-only → write, mỗi phase là một vertical slice dùng được ngay.

| Phase | Nội dung | Đầu ra | Phụ thuộc backend |
|---|---|---|---|
| **0 — Nền tảng** | Layer skeleton, config, model factory, `BackendPort` + httpx client, conversation store + LangGraph checkpointer, supervisor rỗng gọi được 1 tool đọc, `/chat` + `/chat/stream` | Hội thoại nhiều lượt giữ được session | — |
| **1 — Tư vấn xe** | `catalog_advisor`, catalog tools, pipeline RAG (ingest mô tả + FAQ), so sánh có cấu trúc | Khách mô tả nhu cầu → được gợi ý & so sánh theo dữ liệu hiện hành | 9.1 (nên có) |
| **2 — Lead / lái thử** | `lead_agent`, thu thập dần thông tin thiếu, HITL đầy đủ (`PendingAction` + confirm) | Trọn luồng tư vấn → tạo lead | **9.6 (blocker)**, 9.8 |
| **3 — Tra cứu đơn** | `order_agent` (read), chuẩn hoá câu trả lời theo `OrderStatus` + bước tiếp theo | Khách tra cứu trạng thái đơn trong hội thoại | **9.4 (blocker)**, **9.2 (blocker)** |
| **4 — Tạo đơn cọc** | `create_order` + preview giá/cọc từ backend, bàn giao `payment_url` | Cấu hình xe → tạo đơn → link thanh toán | **9.3 (blocker)**, 9.5 |
| **5 — Admin** | `admin_agent`: đọc trước, rồi update status + catalog CRUD; hiển thị diff trước/sau | Admin thao tác bằng ngôn ngữ tự nhiên, vẫn qua RBAC backend | — |
| **6 — Hoàn thiện** | Routing đa ý định trong 1 lượt, streaming trạng thái, summarization hội thoại dài, thêm subagent/tool mà không sửa lõi supervisor, (tuỳ chọn) virtual filesystem + `knowledge_agent` | Trải nghiệm thống nhất | — |

---

## 12. Dependency & cấu hình

### Thiếu so với `pyproject.toml` hiện tại

Hiện có: `fastapi`, `langchain>=1.3.14`, `langgraph>=1.2.10`, `pydantic-settings`, `uvicorn`.

Cần bổ sung:

| Package | Vai trò |
|---|---|
| Chat model provider package | Không pre-lock ở đây — chọn/đổi theo provider dùng thực tế lúc code (infra `llm/factory.py` là nơi duy nhất biết provider cụ thể, xem `code-style.md` mục 6). Hiện đang dùng `langchain-groq`. |
| `httpx` | Backend HTTP client |
| `langgraph-checkpoint-postgres` (hoặc `-sqlite` cho dev) | Persist checkpoint — bản base `langgraph-checkpoint` đã có, chỉ là in-memory |
| Thư viện embedding + vector store | RAG (bge-m3 / pgvector client) |
| `deepagents` *(tuỳ chọn)* | **Chưa cài.** LangChain 1.3.14 đã có sẵn `create_agent` + middleware `todo`, `human_in_the_loop`, `summarization`, `context_editing`, và subagent transformer — **đủ để dựng kiến trúc deepagent mà không cần package riêng**. Chỉ thêm `deepagents` nếu muốn preset dựng sẵn. |

### Model & provider — quyết định ở tầng infrastructure, không pre-plan ở roadmap

Provider/model cho từng agent (supervisor + subagent) là quyết định triển khai, tự chốt lúc code từng phần chứ không khoá sẵn ở đây — tránh tài liệu lệch code mỗi khi đổi provider. Nơi duy nhất biết provider cụ thể là `infrastructure/llm/factory.py`; `Settings.model_supervisor` (và các field model khác nếu tách theo subagent) luôn đọc từ `.env`, không hard-code trong code Python.

Cân nhắc chung khi chọn model cho từng vai trò (không gắn với 1 provider cụ thể): agent có ghi dữ liệu (`order_agent`, `admin_agent`) nên ưu tiên model mạnh nhất đang có; agent read-only nặng đọc (`catalog_advisor`) có thể dùng model rẻ/nhanh hơn nếu đã đo và chấp nhận đánh đổi chất lượng. Prompt caching cho system prompt của supervisor vẫn đáng bật nếu provider hỗ trợ (giảm chi phí đáng kể ở chatbot nhiều lượt).

> Lưu ý: embedding cho RAG không nhất thiết cùng provider với chat model — nhiều provider LLM không có embeddings API, cần kiểm tra riêng khi chọn (vd bge-m3 self-host là một lựa chọn không phụ thuộc provider chat).

### Config cần có (`.env` hiện đang trống)

```text
APP_ENV, APP_DEBUG
BACKEND_BASE_URL=http://localhost:8000/api/v1
BACKEND_TIMEOUT_SECONDS=15
GROQ_API_KEY
MODEL_SUPERVISOR / MODEL_SUBAGENT
AI_DATABASE_URL          # DB riêng của ai-service (conversation + checkpoint + vector)
EMBEDDING_ENDPOINT
PENDING_ACTION_TTL_SECONDS=900
```

---

## 13. Rủi ro & cách kiểm soát

| Rủi ro | Kiểm soát |
|---|---|
| AI bịa giá / tiền cọc | Nguyên tắc #5 + strip số giá khỏi corpus RAG + system prompt bắt buộc gọi tool; thêm eval case chuyên kiểm tra |
| Tạo đơn trùng | `PendingAction.consumed` + đề xuất `Idempotency-Key` (9.5) |
| Rate limit lead chặn toàn bộ chatbot | **Phải xử lý 9.6 trước Phase 2** |
| Prompt injection từ input người dùng để leo quyền | RBAC ở backend, AI không có service account; token pass-through |
| Rò rỉ JWT qua checkpoint | Token chỉ ở request scope, cấm ghi vào state/checkpoint (mục 6) |
| Hội thoại dài vượt context | `summarization` middleware + `context_editing` (đều có sẵn trong LangChain 1.3.14) |
| Backend đổi contract làm AI hỏng ngầm | Typed DTO ở `infrastructure/backend/` + contract test chạy với backend thật trong CI |

---

## 14. Việc cần chốt trước khi code

1. **9.6** — cơ chế rate limit lead cho traffic từ ai-service (blocker Phase 2).
2. **9.4** — khách vãng lai có được tra cứu đơn qua chat không? (blocker Phase 3)
3. **9.2 + 9.3** — backend có bổ sung enrich order response và endpoint preview không? (blocker Phase 3–4)
4. Xác nhận **loại option xe khỏi scope** (9.7) và **lái thử không đặt lịch theo giờ** (9.8).
5. Chốt vector store cho RAG: pgvector chung DB ai-service, hay Qdrant/OpenSearch riêng.
