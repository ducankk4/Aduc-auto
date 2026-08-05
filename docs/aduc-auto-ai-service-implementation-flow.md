# Aduc Auto AI Service - Flow xây dựng từ đầu

## 1. Mục đích

Tài liệu này mô tả thứ tự xây dựng AI service độc lập cho Aduc Auto từ lúc chưa có mã nguồn đến khi có Customer Assistant, bốn subagent, RAG, approval workflow và durable resume.

Đây là **flow triển khai kiến trúc**, không phải danh sách thư mục cần tạo máy móc. Mỗi bước phải trả lời được:

- Xây thành phần này để giải quyết vấn đề gì?
- Logic nào thuộc AI service, logic nào bắt buộc thuộc backend?
- Input, output và error contract là gì?
- Thành phần phụ thuộc abstraction nào?
- Dùng công nghệ/thư viện gì và làm sao không để chúng rò vào domain?
- Kết quả nào chứng minh bước hiện tại đã hoàn thành?

Nguồn yêu cầu là `docs/superpowers/specs/2026-08-05-aduc-auto-multi-agent-ai-service-design.md`.

## 2. Tư duy xây dựng

Thiết kế **domain-first**, bàn giao theo **vertical slice**:

```text
Ranh giới nghiệp vụ
-> Domain
-> DTO/contract
-> Interface/port
-> Application service
-> Agent hoặc deterministic workflow
-> Infrastructure adapter
-> API
-> Composition root
-> Capability chạy hoàn chỉnh
```

Domain-first giữ đúng ranh giới và dependency. Vertical slice tránh xây abstraction, repository hoặc workflow khi chưa có capability sử dụng.

Ba nguyên tắc xuyên suốt:

1. **Backend là nguồn sự thật nghiệp vụ.** Giá, tiền cọc, catalog, compatibility, ownership, authorization và trạng thái đơn không được triển khai lại trong AI service.
2. **LLM chỉ reasoning và diễn đạt.** Side effect phải đi qua deterministic workflow, server-backed draft, explicit approval và idempotent command.
3. **Core không phụ thuộc provider.** FastAPI, LangGraph, model SDK, database SDK và vector-store SDK chỉ xuất hiện ở delivery hoặc infrastructure layer.

## 3. Bước 0 - Chốt ranh giới hệ thống

### Mục đích

Ngăn AI service trở thành backend thứ hai hoặc agent có quyền quá rộng.

```text
Next.js Chat UI
   -> HTTPS, SSE, approval/resume
Independent AI Service
   -> versioned internal HTTP + customer JWT + correlation headers
Aduc Auto Backend
```

AI service quản lý hội thoại, capability, điều phối agent, RAG, approval/resume và persistence riêng. Backend quản lý authentication, authorization, ownership, catalog, giá, tiền cọc, compatibility, lead/order mutation, trạng thái đơn, checkout eligibility và payment.

Quy tắc bắt buộc:

- Không import module hoặc đọc bảng nghiệp vụ backend.
- JWT chỉ tồn tại trong runtime context, không vào prompt, message, graph state, checkpoint, tool schema hoặc trace.
- Không nhận password/card data và không thực hiện payment.
- Anonymous user chỉ dùng capability đọc công khai.
- Biết `order_code` không đồng nghĩa có quyền đọc order.
- RAG không được ghi đè dữ liệu động từ backend.

**Đầu ra:** capability matrix anonymous/authenticated/admin và danh sách contract backend cần cung cấp.

## 4. Bước 1 - Thiết kế domain

### Mục đích

Mô hình hóa khái niệm ổn định mà không gắn với FastAPI, LangGraph, Pydantic, SQLAlchemy hoặc provider.

Domain nền tảng:

```text
Conversation
Message
UserContext / UserCapability
AgentResult
ToolResult
Source
PublicEvent
```

Khi có side effect, bổ sung:

```text
ApprovalDraft
ApprovalDecision
ApprovalStatus
ExecutionStatus
ActionType
```

Khi có RAG, bổ sung:

```text
KnowledgeDocument
KnowledgeChunk
KnowledgeSourceMetadata
RetrievalResult
```

Cách xây:

- Dùng Python `dataclass`, `Enum` và immutable value object.
- Entity có identity/lifecycle; value object không có identity.
- Invariant đặt trong domain, không đặt trong route hoặc prompt.
- Tách public data khỏi secret/runtime data ngay từ type.
- Dùng UTC và định nghĩa rõ expiry.

Invariant chính của `ApprovalDraft`:

```text
có owner
-> payload sau prepare là immutable
-> có expiry
-> chỉ pending draft được approve/reject
-> executed/rejected/expired draft không được execute
-> thay payload phải sinh draft mới
```

Cần chú ý:

- Domain không chứa HTTP request/response, Pydantic `BaseModel`, database session hoặc SDK object.
- `UserContext` không chứa JWT.
- Không lưu raw backend payload hoặc retrieval result lớn trong graph state.
- Không tạo generic base/repository nếu chưa có nhu cầu thực.

**Đầu ra:** type đủ biểu diễn flow hội thoại read-only mà chưa cần LLM hoặc database thật.

## 5. Bước 2 - Thiết kế DTO và contract

### 5.1 Public API DTO

Dùng Pydantic v2 để định nghĩa:

```text
CreateConversationRequest / Response
StreamChatRequest
ResumeConversationRequest
ConversationResponse
ApprovalCardResponse
PublicErrorResponse
SSE event payloads
```

Public API:

```text
POST   /api/v1/conversations
GET    /api/v1/conversations/{conversation_id}
DELETE /api/v1/conversations/{conversation_id}
POST   /api/v1/chat/streams
POST   /api/v1/conversations/{conversation_id}/resume
POST   /api/v1/knowledge/documents
GET    /health/live
GET    /health/ready
```

Resume chỉ nhận `draft_id` và `decision`; frontend không gửi lại business payload để AI service tin tưởng.

### 5.2 Backend DTO

```text
CurrentUser
VehicleSearch / VehicleDetail / VehicleComparison
PrepareLead / ExecuteLead
PrepareOrder / ExecuteOrder
OwnedOrder / OrderHistory
CheckoutEligibility
BackendError
```

Backend contract:

```text
GET  /api/v1/auth/me
GET  /api/v1/catalog/vehicles/search
GET  /api/v1/catalog/vehicles/{slug}
POST /api/v1/leads/prepare
POST /api/v1/leads
POST /api/v1/orders/prepare
POST /api/v1/orders
GET  /api/v1/orders/me
GET  /api/v1/orders/{order_code}
GET  /api/v1/orders/{order_code}/checkout-eligibility
```

### 5.3 Internal result contract

Agent/tool dùng envelope ổn định, không truyền dictionary tùy ý:

```json
{
  ok: true,
  data: {},
  error: null,
  retryable: false,
  source: backend
}
```

`AgentResult` biểu diễn answer data, `missing_fields`, sources, suggested actions, delegation metadata và public error.

### 5.4 SSE contract

```text
conversation.started
message.delta
agent.delegated
tool.started
tool.completed
approval.required
approval.resolved
checkout.available
message.completed
error
```

SSE không stream hidden reasoning, prompt, raw graph state, credential hoặc tool arguments chứa PII.

Error taxonomy: `authentication_required`, `permission_denied`, `not_found`, `validation_error`, `business_conflict`, `rate_limited`, `dependency_unavailable`, `contract_error`.

**Đầu ra:** mỗi boundary có schema riêng, mapping rõ sang domain và OpenAPI contract ổn định.

## 6. Bước 3 - Định nghĩa interface/port

Port nền tảng:

```text
ChatModel
BackendGateway
ConversationRepository
CheckpointStore
EventPublisher
```

Port bổ sung theo capability:

```text
DraftRepository
KnowledgeIngestor
DocumentExtractor
Chunker
EmbeddingProvider
KnowledgeRepository
Retriever
Reranker
MemoryRepository
```

Nguyên tắc:

- Interface diễn đạt use case, không phản chiếu SDK.
- Method có input/output type và error semantics rõ.
- Tách read query khỏi write command vì retry policy khác nhau.
- Chỉ thêm method khi service hiện tại cần.
- Service không tự tạo client, model hoặc repository.

```text
api -> services
services -> domain + interfaces
agents/workflows -> domain + interfaces
tools -> domain + interfaces
infrastructure -> implement interfaces
main.py -> assemble concrete dependencies
```

Dùng `typing.Protocol` hoặc abstract base class. **Đầu ra:** application service chạy được với fake/in-memory adapters.

## 7. Bước 4 - Xây application services

Service nền tảng là `ConversationService` và `ChatService`; bổ sung `ApprovalService`, `KnowledgeService` khi capability tương ứng xuất hiện.

`ConversationService` quản lý create/load/delete, ownership và lifecycle.

`ChatService`:

```text
message + runtime context
-> load conversation
-> kiểm tra capability
-> dựng compact agent context
-> gọi coordinator
-> publish public events
-> persist message/result
```

`ApprovalService`:

```text
draft_id + decision
-> kiểm tra conversation owner
-> load draft server-side
-> validate owner/expiry/status/action
-> resume đúng workflow thread
```

Route chỉ parse input, gọi service và map output. Service không trả SDK object/HTTP response. Draft/checkpoint failure phải fail closed.

**Đầu ra:** conversation/chat flow chạy bằng coordinator giả, event publisher giả và repository in-memory.

## 8. Bước 5 - Runtime context, authentication và state

Runtime context trong request scope:

```text
request_id
conversation_id
anonymous session identity hoặc user_id
capability set
customer JWT
correlation metadata
```

JWT chỉ được backend client đọc để tạo `Authorization` header.

Graph/conversation state chỉ giữ:

```text
conversation_id
capability không chứa credential
current intent/current agent
recent messages đã giới hạn
collected non-secret fields
pending draft reference
compact tool result
```

Không giữ JWT, secret, raw payload lớn, toàn bộ retrieval result, payment/identity-card data hoặc dynamic fact trong long-term memory.

Dùng FastAPI dependency injection; có thể dùng `contextvars` cho correlation nhưng không dùng global mutable state. Chỉ thêm LangGraph state/checkpointer khi cần interrupt/resume.

## 9. Bước 6 - Infrastructure adapters

### Backend client

```text
domain request
-> backend DTO
-> HTTP có Authorization/X-Request-ID/X-AI-Conversation-ID
-> validate response
-> map backend error
-> domain result
```

Command thêm stable `Idempotency-Key`. Khuyến nghị `httpx.AsyncClient`, timeout riêng, pooling và bounded retry. Chỉ retry read an toàn; command chỉ retry cùng idempotency key.

### Persistence

| Store | Trách nhiệm |
|---|---|
| Conversation | Ownership, metadata, lifecycle, message references |
| Checkpoint | Graph position, compact state, interrupt, resume |
| Draft | Immutable payload, ownership, expiry, approval, execution |
| Knowledge | Document, chunk, embedding, source metadata |
| Memory | Preference có consent và có thể xóa |

Không gộp thành generic repository. PostgreSQL/SQLAlchemy, Qdrant và durable LangGraph checkpointer là lựa chọn hợp lý nhưng chỉ là replaceable adapters.

### Providers

`ChatModel` và `EmbeddingProvider` bọc provider được cấu hình. Factory chọn provider bằng centralized settings; provider-specific type/exception không thoát khỏi adapter.

## 10. Bước 7 - FastAPI và SSE foundation

```text
centralized settings
-> composition root
-> FastAPI app/lifespan
-> health endpoints
-> conversation endpoints
-> chat streaming
-> SSE publisher
-> exception mapping
```

Streaming flow:

```text
client gửi message
-> resolve runtime context
-> verify conversation ownership
-> ChatService xử lý
-> phát ordered SSE events
-> persist
-> message.completed hoặc error
```

Công nghệ: FastAPI, Uvicorn, Pydantic Settings, ASGI `StreamingResponse`/SSE library và structured logging có redaction.

**Đầu ra:** service có health check, conversation API và stream response giả đúng protocol.

## 11. Bước 8 - Vertical Slice 1: Vehicle Advisor

### Mục đích

Hoàn thiện capability có giá trị đầu tiên, chỉ đọc và dùng được cho cả anonymous lẫn authenticated user.

```text
Catalog DTO
-> BackendGateway catalog methods
-> catalog read tools
-> Vehicle Advisor result contract
-> Vehicle Advisor
-> Customer Assistant tối thiểu
-> streamed response
```

Capabilities: `search_vehicles`, `get_vehicle_detail`, `compare_vehicles`, `compare_vehicle_variants`.

```text
user hỏi về xe
-> coordinator xác định intent
-> Vehicle Advisor chuẩn hóa tiêu chí
-> thiếu: trả missing_fields và hỏi một câu bổ sung
-> đủ: gọi catalog tools
-> backend trả dữ liệu hiện tại
-> structured recommendation
-> coordinator diễn đạt và stream
```

Dùng LangChain Deep Agents theo spec và Pydantic structured output. Chưa cần LangGraph approval. Tool là adapter mỏng, không tự tính giá/compatibility; model không tự điền field còn thiếu.

**Đầu ra:** tìm, xem, so sánh xe qua hội thoại, có persistence và streaming.

## 12. Bước 9 - Vertical Slice 2: Knowledge RAG

### Mục đích

Bổ sung nguồn kiến thức dài mà không biến RAG thành nguồn sự thật cho dữ liệu động.

Ingestion:

```text
admin upload
-> authorize
-> validate metadata
-> extract/normalize/chunk
-> embed/index
-> persist status/version
```

Metadata gồm document identity/type/title, source URL, section/version, effective/expiry date, audience và language.

Retrieval:

```text
normalize query
-> retrieve
-> optional rerank
-> audience/date filters
-> context budget
-> content + source metadata
```

Authority:

```text
giá/availability/compatibility -> backend
FAQ/policy/long description   -> RAG
mixed question                -> backend + RAG
conflict                      -> backend thắng
```

Dùng provider-neutral embedding, Qdrant/vector store qua interface và chỉ thêm reranker khi cần. Retrieved content là untrusted input; không lưu chunks lớn trong graph state; admin API không mở cho user thường.

**Đầu ra:** Vehicle Advisor trả lời câu hỏi hỗn hợp có source và luôn ưu tiên backend cho business fact hiện tại.

## 13. Bước 10 - Multi-agent routing

### Mục đích

Đưa mọi hội thoại qua một coordinator duy nhất và giới hạn quyền của từng subagent.

```text
Customer Assistant
|-- Vehicle Advisor
|-- Order Support
|-- Sales Concierge
`-- Order Concierge
```

```text
message + state + capability
-> xác định intent
-> capability gate
-> chọn subagent
-> emit agent.delegated
-> nhận structured result
-> hỏi missing field hoặc tạo response
-> cập nhật compact state
```

Subagent không gọi nhau, mọi kết quả về coordinator, mỗi subagent có tool allowlist tối thiểu. Coordinator không có direct write tool. Prompt không thay thế authorization bằng code/backend.

**Đầu ra:** routing có structured delegation, capability gate và public events rõ ràng.

## 14. Bước 11 - Vertical Slice 3: Order Support

```text
authenticated user hỏi về order
-> capability gate
-> Order Support
-> backend revalidate JWT + ownership
-> list/detail/status history
-> giải thích trạng thái và bước tiếp theo
```

Checkout:

```text
get_checkout_eligibility
-> backend quyết định
-> emit checkout.available nếu hợp lệ
-> frontend tiếp tục browser/backend checkout
```

401/403 không route vòng; 404 không làm lộ resource; AI service không khởi tạo hoặc xử lý payment.

**Đầu ra:** authenticated user xem order của mình, hiểu status history và nhận checkout handoff khi backend cho phép.

## 15. Bước 12 - Approval workflow dùng chung

### Mục đích

Tạo cơ chế deterministic, durable và idempotent cho mọi business mutation.

Thành phần:

```text
ApprovalDraft domain
DraftRepository
ApprovalService
approval DTO/events
LangGraph checkpoint adapter
shared workflow nodes
resume API
```

State:

```text
COLLECTING -> PREPARED -> AWAITING_APPROVAL
-> APPROVED/REJECTED/EXPIRED
-> EXECUTING -> EXECUTED/FAILED
```

Workflow:

```text
collect
-> backend prepare
-> persist immutable owned draft + stable idempotency key
-> approval.required
-> interrupt
-> receive draft_id + decision
-> reload draft server-side
-> verify owner/expiry/action/status
-> reject: close, no side effect
-> approve: backend revalidate
-> execute ở node riêng với cùng idempotency key
-> persist result
-> approval.resolved
```

Dùng LangGraph vì cần checkpoint/interrupt/resume sống qua restart. Tin nhắn “đồng ý” không execute command. Interrupt node không có side effect. Duplicate resume dùng cùng draft/key. Payload thay đổi phải invalid draft và approval lại.

**Đầu ra:** workflow giả survive restart, approve/reject và execute đúng một lần.

## 16. Bước 13 - Vertical Slice 4: Sales Concierge

```text
authenticated user cần tư vấn/lái thử
-> collect vehicle/contact/showroom
-> missing_fields nếu thiếu
-> backend prepare/normalize
-> immutable lead draft
-> approval + interrupt
-> reject: đóng draft
-> approve: reload/verify/execute cùng idempotency key
-> authoritative lead result
```

Agent thu thập dữ liệu; workflow kiểm soát transition; backend validate/tạo lead; frontend hiển thị masked card. Phone/email phải mask. Chỉ mô tả test-drive scheduling khi backend đã có contract ngày/giờ.

**Đầu ra:** lead flow chạy đủ prepare -> approval -> resume -> idempotent execute; reject không tạo lead.

## 17. Bước 14 - Vertical Slice 5: Order Concierge

```text
authenticated user muốn đặt cọc
-> collect variant/color/customer fields
-> backend prepare
-> validate compatibility + current price + deposit
-> immutable order draft
-> approval + interrupt
-> approve: reload + backend revalidate
-> execute cùng idempotency key
-> order_code
-> checkout eligibility
-> checkout.available
```

Khi backend trả 409 do giá/config/state thay đổi: invalid draft cũ, prepare lại, tạo preview/draft mới và approval lại.

Model không tính giá/tiền cọc/compatibility. Không nhận card data. Sensitive identity fields nên dùng protected frontend form. Không model fallback giữa prepared command workflow.

**Đầu ra:** order được tạo đúng một lần sau approval; kết quả có order code và checkout handoff do backend cho phép.

## 18. Bước 15 - Durable resume, memory và vận hành

Durable resume:

```text
page/service restart
-> verify conversation ownership
-> load checkpoint + pending draft
-> dựng lại approval card
-> approve/reject
-> resume đúng thread
```

Conversation/thread/draft ID phải opaque.

Long-term memory chỉ lưu preference có consent như budget, vehicle, usage, showroom; không lưu credential, identity/payment data, current price hoặc order status. Memory phải xem/xóa được.

Security:

- Per-agent tool allowlist và capability gate bằng code.
- Redact PII trước log/trace/event.
- Retrieved document là untrusted content.
- Centralized secrets/config.
- Rate limit, quota, input/context limits.
- Disable host shell và unrestricted filesystem.

Error policy:

```text
401 -> reauthenticate, không retry
403 -> không đủ quyền, không route vòng
404 -> không có resource được phép truy cập
409 -> invalidate/re-prepare draft
422 -> normalized field errors
429 -> bounded backoff khi an toàn
timeout/502/503 -> bounded retry cho read
command retry -> cùng idempotency key
RAG failure -> tiếp tục structured tools và disclose
contract violation -> fail closed
```

Observability gồm structured logs theo correlation ID, metrics cho latency/model/tool/approval/resume/idempotency và traces đã redact. `/health/live` báo process; `/health/ready` kiểm tra dependency cần thiết.

## 19. Composition root và source layout

`main.py` là nơi duy nhất lắp concrete dependency:

```text
settings
-> HTTP/database/vector/model clients
-> adapters
-> repositories/stores
-> services
-> tools + allowlists
-> subagents/coordinator/workflows
-> API dependencies
-> resource lifecycle
```

Layout mục tiêu:

```text
ai_service/
|-- pyproject.toml
|-- README.md
|-- .env.example
`-- src/ai_service/
    |-- main.py
    |-- config.py
    |-- api/
    |-- domain/
    |-- interfaces/
    |-- services/
    |-- agents/subagents/
    |-- workflows/
    |-- tools/
    |-- rag/
    |-- repositories/
    |-- stores/
    |-- providers/
    |-- clients/
    `-- core/
```

Không tạo đủ mọi file từ đầu; mỗi slice chỉ thêm file/adapter thực sự cần.

## 20. Thứ tự delivery

### AI-0 - Backend contract readiness

Identity, catalog, owned-order reads, prepare lead/order, idempotent execute, checkout eligibility, stable errors và correlation headers.

### AI-1 - Service foundation

```text
domain -> DTO -> interfaces -> services -> runtime context
-> backend adapter -> persistence -> FastAPI + SSE
```

### AI-2 - Vehicle Advisor và RAG

```text
catalog tools -> Customer Assistant tối thiểu -> Vehicle Advisor
-> ingestion/retrieval -> authority policy + sources
```

### AI-3 - Multi-agent và Order Support

```text
capability routing -> coordinator -> owned-order tools
-> Order Support -> checkout action
```

### AI-4 - Approval và Sales Concierge

```text
draft/store -> shared workflow -> durable resume
-> Sales Concierge -> lead prepare/execute
```

### AI-5 - Order Concierge

```text
order prepare -> preview -> approval
-> idempotent execute -> checkout handoff
```

### AI-6 - Operational hardening

```text
consented memory -> deletion -> PII redaction -> quotas
-> health -> injection controls -> knowledge synchronization
```

## 21. Checklist hoàn thành

- Một Customer Assistant điều phối đúng bốn subagent.
- Subagent không gọi nhau và chỉ có allowlisted tools.
- Anonymous user không gọi được protected capability.
- Backend là nguồn sự thật cho business rule/dynamic fact.
- Không write action nào thiếu server-backed approval.
- Duplicate resume/retry không tạo duplicate lead/order.
- Interrupt node không chứa side effect.
- Approval sống qua page reload/service restart.
- RAG chỉ phục vụ knowledge, có source metadata.
- AI service không xử lý payment, đọc bảng hoặc import backend code.
- Provider có thể thay mà không sửa agent policy/workflow.
- JWT, secret, payment data và sensitive PII không vào model-visible/persisted graph context.

## 22. Flow tổng quát

```text
System boundary
-> Domain
-> DTO/contracts
-> Interfaces/ports
-> Application services
-> Runtime context/state
-> Infrastructure adapters
-> FastAPI/SSE foundation
-> Vehicle Advisor
-> RAG
-> Multi-agent coordinator
-> Order Support
-> Shared approval workflow
-> Sales Concierge
-> Order Concierge
-> Durable resume, memory, hardening
-> Composition root hoàn chỉnh
```

Tư duy quan trọng nhất: **thiết kế từ domain và contract, triển khai theo capability, chỉ đưa LLM vào nơi cần reasoning, và giữ mọi side effect trong deterministic workflow dựa trên backend authority**.
