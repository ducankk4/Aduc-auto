# ai_service — Tổng quan kiến trúc & lộ trình triển khai theo phase

## 0. Nguyên tắc chung

Toàn bộ codebase tuân theo **layered architecture**, map trực tiếp vào cấu trúc thư mục hiện có của `ai-service/`. Mọi agent/subagent đặt code đúng theo bảng này, không tự bịa thư mục mới cho layer đã có chỗ:

| Layer | Vai trò | Thư mục | Không được phép |
|---|---|---|---|
| **Domain** | Entity thuần (Car, TestDriveBooking, ComparisonResult...), business rule cốt lõi | `core/domain/` | Import framework (LangChain, FastAPI, SQLAlchemy...) |
| **Application** | Use case, orchestration logic, agent/graph definition, tool interface (Protocol) | `services/` (use case, orchestration logic), `agent/` (supervisor/subagent graph definition), `core/interface/` (Protocol — contract cho Infrastructure implement) | Biết chi tiết implementation của DB/API cụ thể |
| **Infrastructure** | Implementation thật: DB repository, vector store, external API client, LLM provider | `infrastructure/llm/`, `infrastructure/vector_store/`, `repository/` (sẽ thêm `infrastructure/db/` ở Phase 0 nếu cần tách riêng kết nối DB) | Chứa business rule |
| **Interface** | Entry point: agent tool wrapper, API router, CLI | `api/` | Chứa logic nghiệp vụ, chỉ gọi xuống application |

> **Lưu ý tên dễ nhầm:** `core/interface/` **không phải** layer "Interface" (entry point) ở hàng cuối bảng trên — đây là nơi định nghĩa Protocol/abstract contract (giống khái niệm "port" trong hexagonal architecture) mà `infrastructure/` và `repository/` implement. Layer "Interface" (entry point thật sự, expose ra ngoài) nằm ở `api/`. Sở dĩ đặt tên trùng vì `core/interface/` dùng nghĩa "interface" theo kiểu Python (Protocol/abstract class), khác với "Interface" trong layered architecture.

**Dependency rule** (map theo thư mục thật, một chiều, không ngoại lệ):

```
api/ ──────────────────────► services/, agent/ ──────────► core/domain/
                                      ▲
                                      │ implement Protocol định nghĩa ở core/interface/
                        infrastructure/, repository/
```

`core/domain/` không phụ thuộc vào bất kỳ thư mục nào khác trong `ai-service/`.

Mỗi phase dưới đây là một lát cắt dọc qua đủ 4 layer/thư mục, không phải "làm xong hết layer A rồi mới sang layer B".

---

## Phase 0 — Shared kernel (nền tảng, làm trước mọi agent)

**Mục tiêu:** dựng phần hạ tầng dùng chung để các phase sau cắm vào, tránh mỗi subagent tự bịa một kiểu.

**Thành phần chính:**
- `core/`: config loader, logging, exception hierarchy chung
- `core/checkpointer`: Postgres/SQLite saver cho LangGraph — **bắt buộc phải xong trước Phase 2** vì HITL cần persist state khi `interrupt()`
- `domain/`: entity dùng chung (Car, Customer, User...) — không phụ thuộc agent nào
- `infrastructure/db`: kết nối DB, base repository pattern
- `infrastructure/llm`: LLM client factory (model config tập trung một chỗ)
- `application/state.py`: schema state chung cho toàn bộ graph (nếu các subagent cần trao đổi dữ liệu qua supervisor)

**Ra khỏi phase khi:** có thể khởi tạo 1 graph rỗng, chạy checkpoint/resume thử nghiệm thành công, có ít nhất 1 repository thật kết nối DB.

---

## Phase 1 — Supervisor + RAG tool

**Mục tiêu:** dựng bộ khung điều phối trung tâm, có khả năng trả lời câu hỏi thông tin chung bằng RAG mà chưa cần subagent nào khác tồn tại.

**Phạm vi:** RAG giới hạn chỉ supervisor được gọi (đã chốt) — các subagent sau này không tự ý truy cập RAG.

| Layer | Nội dung |
|---|---|
| Domain | Không có entity riêng, dùng chung Phase 0 |
| Application | Supervisor graph (routing logic), RAG use case (query → retrieve → answer), Protocol cho retriever |
| Infrastructure | Vector store client thật, embedding pipeline |
| Interface | Tool wrapper `rag_search` đăng ký cho supervisor, entry point gọi graph từ ngoài |

**Ra khỏi phase khi:** supervisor có thể (a) trả lời câu hỏi general bằng RAG, (b) route được tới một subagent giả lập (stub) — chưa cần subagent thật, chỉ cần cơ chế `task tool` / delegation hoạt động.

---

## Phase 2 — Data-ops subagent (view + sensitive tools, có HITL)

**Mục tiêu:** subagent thao tác dữ liệu backend, tách rõ 2 nhóm tool và có cổng phê duyệt cho nhóm sensitive.

| Layer | Nội dung |
|---|---|
| Domain | Entity nghiệp vụ: Car, TestDriveBooking, trạng thái booking |
| Application | Use case cho từng tool (view xe, xem màu, tạo đăng ký lái thử...); Protocol cho backend data source; **middleware phân loại tool theo metadata `requires_approval`** |
| Infrastructure | Repository/API client thật gọi vào backend hệ thống |
| Interface | Tool definitions (LangChain tools) — tool view và tool sensitive đăng ký qua cùng 1 cơ chế nhưng khác flag |

**Điểm bắt buộc của phase này:**
- Tool sensitive luôn đi qua middleware chặn → `interrupt()` → chờ xác nhận → `Command(resume=...)`.
- Test riêng: interrupt phát sinh trong subagent phải propagate lên được supervisor/UI (đây là rủi ro kỹ thuật lớn nhất đã nêu ở lần trước).
- Tool view chạy thẳng, không qua gate.

**Ra khỏi phase khi:** có tối thiểu 1 tool view và 1 tool sensitive chạy end-to-end, bao gồm luồng HITL thật (không phải mock).

---

## Phase 3 — Comparison subagent (LangGraph subgraph)

**Mục tiêu:** subagent tạo card so sánh trực quan, xử lý multi-step do độ phức tạp cao hơn ReAct đơn giản.

| Layer | Nội dung |
|---|---|
| Domain | ComparisonResult, ComparisonCriteria (entity mô tả cấu trúc card) |
| Application | Subgraph riêng: fetch spec nhiều xe → tính diff → build card payload; đây là nơi dùng `CompiledSubAgent` thay vì spec đơn giản |
| Infrastructure | Tái sử dụng repository từ Phase 2 (không viết lại) để lấy dữ liệu xe |
| Interface | Tool trả về payload card cho supervisor hiển thị |

**Lưu ý phụ thuộc:** subagent này không tự gọi RAG (theo quyết định đã chốt) và không tự gọi thẳng backend data mà nên đi qua repository/use case đã có ở Phase 2 để tránh trùng logic truy vấn dữ liệu xe.

**Ra khỏi phase khi:** subgraph chạy được so sánh ≥2 xe và trả về card đúng format, có test cho case dữ liệu thiếu/không khớp.

---

## Phase 4 — Admin agent (graph tách biệt hoàn toàn)

**Mục tiêu:** agent riêng cho admin, tạo dashboard báo cáo hành vi user — **không nằm trong supervisor tree** (đã chốt).

| Layer | Nội dung |
|---|---|
| Domain | UserBehaviorEvent, ReportPeriod... — entity riêng cho phân tích, không trộn với domain khách hàng |
| Application | Use case tổng hợp báo cáo; cân nhắc chạy dạng async/background job nếu tổng hợp dữ liệu nặng |
| Infrastructure | Có thể dùng chung DB layer với Phase 0 nhưng qua read-model/aggregation riêng, không đụng trực tiếp bảng nghiệp vụ khách hàng |
| Interface | Entry point riêng biệt (route/graph_id riêng), auth riêng cho admin |

**Ra khỏi phase khi:** graph admin chạy độc lập, xác thực riêng, không có đường nào từ supervisor khách hàng gọi được vào agent này.

---

## Phase 5 — Tích hợp & cross-cutting

Làm sau khi 4 phase trên đã có bản chạy được, không làm song song từ đầu để tránh phải sửa lại nhiều lần:

- Observability: log theo layer (đặc biệt log đầy đủ mọi lần trigger HITL — audit trail bắt buộc cho tool sensitive)
- Error handling thống nhất theo exception hierarchy ở Phase 0
- Test: mỗi layer test riêng (domain: unit test thuần; application: test với mock infrastructure; infrastructure: integration test thật)
- Đóng gói `code_style.md` áp cho toàn bộ 5 phase (docstring, typing, `__init__.py` export...)

---

## Bảng phụ thuộc giữa các phase

```
Phase 0 (kernel)
   │
   ▼
Phase 1 (supervisor + RAG) ──► Phase 2 (data-ops) ──► Phase 3 (comparison, tái dùng repo của Phase 2)
   │
   ▼
Phase 4 (admin) — độc lập, chỉ phụ thuộc Phase 0
```

Phase 2 nên xong trước Phase 3 vì Phase 3 tái sử dụng repository dữ liệu xe. Phase 4 có thể làm song song với Phase 1–3 vì không phụ thuộc supervisor.
