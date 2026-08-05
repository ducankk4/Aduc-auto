 > Contract-first → security-first → read-only vertical slice → deterministic write workflows → hardening.

  Điểm quan trọng nhất: đây không đơn thuần là chatbot RAG. Nó là một AI orchestration service đứng trước backend nghiệp
  vụ, trong đó:

  - AI được phép suy luận và tư vấn.
  - Backend quyết định business facts.
  - LangGraph kiểm soát deterministic workflow.
  - Mọi side effect phải qua draft, approval và idempotent execution.
  - JWT chỉ tồn tại trong runtime context, tuyệt đối không đi vào model context.

  ———

  # 1. Nguyên tắc phát triển xuyên suốt

  Trước khi chia phase, team cần thống nhất sáu nguyên tắc bất biến.

  ## 1.1 Backend là nguồn sự thật

  Các dữ liệu sau chỉ được lấy từ backend:

  - Giá hiện tại.
  - Tiền cọc.
  - Tình trạng xe.
  - Variant/color compatibility.
  - Quyền sở hữu order.
  - Trạng thái order.
  - Điều kiện checkout.
  - Lead/order validation.

  RAG chỉ dùng cho:

  - Chính sách.
  - FAQ.
  - Hướng dẫn.
  - Nội dung giới thiệu dài.
  - Giải thích sản phẩm.

  Nếu backend và RAG xung đột, backend luôn thắng.

  ## 1.2 Read linh hoạt, write deterministic

  Read:
  User → Coordinator → Subagent → Tool/RAG → Answer

  Write:
  Collect → Prepare → Draft → Approval → Interrupt
  → Resume → Verify → Revalidate → Execute

  Model không bao giờ có tool kiểu create_order hoặc create_lead trực tiếp.

  ## 1.3 Contract-first

  Không triển khai agent trước khi xác định:

  - Tool input/output.
  - Backend endpoint.
  - Error mapping.
  - SSE event schema.
  - Draft state transition.
  - Idempotency behavior.

  ## 1.4 Security là thiết kế, không phải phase cuối

  Ngay từ foundation phải bảo đảm:

  - JWT không vào prompt, message, graph state hay checkpoint.
  - Log và trace được redaction.
  - Anonymous/authenticated capability tách rõ.
  - Ownership được kiểm tra cả ở AI service và backend.
  - Mỗi subagent chỉ nhận tool allowlist tối thiểu.

  ## 1.5 Phát triển theo vertical slice

  Không nên xây hết repository rồi mới xây service, sau đó mới làm agent. Mỗi capability nên đi xuyên các tầng:

  Domain
  → Interface
  → Fake adapter
  → Service/use case
  → Tool
  → Agent/workflow
  → API/SSE
  → Tests/evaluation

  Như vậy cuối mỗi phase đều có một luồng chạy hoàn chỉnh.

  ## 1.6 Composition root là nơi duy nhất chọn provider

  Chỉ main.py hoặc module bootstrap/container được phép khởi tạo:

  - Model provider.
  - Embedding provider.
  - Backend client.
  - Relational store.
  - Vector store.
  - Checkpoint store.
  - Concrete repository.

  Agent, workflow và service chỉ phụ thuộc interface.

  ———

  # 2. Phase 0 — Chốt product behavior và threat model

  Phase này tạo nền tảng trước khi viết code.

  ## Công việc

  ### Lập capability matrix

   Capability              Anonymous    Authenticated    Admin
  ━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━  ━━━━━━━━━━━━━━━  ━━━━━━━
   Vehicle advice                 Có               Có       Có
  ──────────────────────  ───────────  ───────────────  ───────
   Catalog search                 Có               Có       Có
  ──────────────────────  ───────────  ───────────────  ───────
   Knowledge RAG                  Có               Có       Có
  ──────────────────────  ───────────  ───────────────  ───────
   Create lead                 Không               Có       Có
  ──────────────────────  ───────────  ───────────────  ───────
   View owned orders           Không               Có       Có
  ──────────────────────  ───────────  ───────────────  ───────
   Create deposit order        Không               Có       Có
  ──────────────────────  ───────────  ───────────────  ───────
   Knowledge ingestion         Không            Không       Có

  ### Xác định data classification

  Phân loại dữ liệu:

  - Public: catalog description, policy.
  - Customer data: tên, email, phone.
  - Sensitive: JWT, identity-card data.
  - Financial: price/deposit preview.
  - Forbidden in AI context: JWT, password, card data, secrets.

  ### Lập threat model

  Ít nhất phải xét:

  - Prompt injection từ người dùng.
  - Prompt injection trong tài liệu RAG.
  - Tool privilege escalation.
  - Anonymous gọi protected tool.
  - Truy cập order người khác.
  - Fake approval payload.
  - Duplicate resume.
  - LangGraph node chạy lại sau interrupt.
  - JWT bị ghi log hoặc checkpoint.
  - Model tạo business facts không có backend xác nhận.

  ## Đầu ra

  - Capability matrix.
  - Data-classification policy.
  - Threat model.
  - Danh sách invariants.
  - Danh sách operation bị cấm.
  - Quy tắc backend authority và RAG authority.

  ## Điều kiện hoàn thành

  Mọi thành viên trả lời thống nhất được:

  - AI được quyền làm gì?
  - AI không được quyền làm gì?
  - Dữ liệu nào được đưa vào model?
  - Operation nào bắt buộc approval?
  - Nguồn nào authoritative cho từng loại dữ liệu?

  ———

  # 3. Phase 1 — Backend contract readiness

  Đây là dependency bắt buộc. Không nên phát triển write workflow bằng mock quá lâu nếu backend contract chưa được chốt.

  ## 3.1 Chốt versioned HTTP contracts

  Các endpoint tối thiểu:

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

  ## 3.2 Chốt prepare/execute semantics

  Prepare endpoint:

  - Không tạo entity.
  - Validate và normalize input.
  - Tính authoritative values.
  - Trả preview để tạo approval card.

  Execute endpoint:

  - Revalidate toàn bộ dynamic facts.
  - Bắt buộc Idempotency-Key.
  - Cùng idempotency key phải trả lại cùng kết quả hoặc cùng command status.
  - Không được tạo duplicate lead/order.

  ## 3.3 Chuẩn hóa response envelope

  {
    "ok": true,
    "data": {},
    "error": null,
    "retryable": false,
    "source": "backend"
  }

  Error category:

  authentication_required
  permission_denied
  not_found
  validation_error
  business_conflict
  rate_limited
  dependency_unavailable
  contract_error

  ## 3.4 Chốt correlation headers

  Authorization
  Idempotency-Key
  X-Request-ID
  X-AI-Conversation-ID

  ## Test cần có

  - OpenAPI/schema contract tests.
  - Authentication tests.
  - Ownership tests.
  - Prepare không tạo entity.
  - Execute có idempotency.
  - Duplicate execute không tạo duplicate.
  - Price/deposit được revalidate khi execute.
  - Order của user khác trả 403 hoặc permitted 404.

  ## Điều kiện hoàn thành

  AI service có thể chạy một bộ contract test tự động chống lại backend staging mà không phụ thuộc backend source code.

  ———

  # 4. Phase 2 — Khởi tạo service foundation

  Mục tiêu là tạo một service chạy độc lập, chưa cần agent thông minh.

  ## 4.1 Tạo project skeleton

  src/ai_service/
  ├── api/
  ├── domain/
  ├── interfaces/
  ├── services/
  ├── agents/
  ├── workflows/
  ├── tools/
  ├── rag/
  ├── repositories/
  ├── stores/
  ├── providers/
  ├── clients/
  └── core/

  Thiết lập:

  - FastAPI application.
  - Centralized settings.
  - Structured logging.
  - Request ID.
  - Health endpoints.
  - Dependency lifecycle.
  - Composition root.
  - Test framework.
  - Type checking, linting và formatting.

  ## 4.2 Xây domain trước

  Các domain model đầu tiên:

  - Conversation.
  - Message.
  - WorkflowThread.
  - Approval.
  - Draft.
  - KnowledgeDocument.
  - PublicEvent.
  - ToolResult.
  - UserCapability.

  Đặc biệt cần state machine rõ ràng cho draft:

  PREPARED
     ├── APPROVED → EXECUTING → EXECUTED
     ├── REJECTED
     ├── EXPIRED
     └── INVALIDATED

  Không cho phép transition tùy ý.

  ## 4.3 Định nghĩa interface

  Tối thiểu:

  BackendGateway
  ModelProvider
  EmbeddingProvider

  ConversationRepository
  CheckpointRepository
  DraftRepository
  MemoryRepository
  KnowledgeRepository

  Retriever
  Reranker

  ChatService
  ConversationService
  ApprovalService
  KnowledgeService

  Interface không được phụ thuộc:

  - FastAPI request object.
  - Provider SDK model.
  - Database SDK object.
  - LangChain-specific response nếu có thể tránh.

  ## 4.4 Runtime authentication context

  JWT chỉ nằm trong request-scoped runtime context:

  HTTP Authorization header
  → authentication middleware/dependency
  → runtime context
  → backend client header

  Nó không được copy sang:

  - Graph state.
  - Message.
  - Draft.
  - Checkpoint.
  - Tool arguments.
  - Trace metadata.

  Nên dùng ContextVar hoặc explicit runtime dependency có lifetime theo request.

  ## 4.5 Conversation ownership

  Cần hỗ trợ:

  - Anonymous conversation bằng signed opaque credential.
  - Authenticated conversation gắn với user ID nội bộ.
  - Lấy conversation.
  - Xóa conversation.
  - Resume conversation.
  - Ownership check trước mọi operation.

  ## 4.6 SSE protocol

  Xây event model trước khi làm agent:

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

  Mọi event phải có:

  - Event ID.
  - Request ID.
  - Conversation ID.
  - Event type.
  - Timestamp.
  - Public payload.

  Không đưa vào event:

  - Prompt.
  - Hidden reasoning.
  - Tool arguments thô.
  - JWT.
  - Unmasked PII.
  - Raw graph state.

  ## 4.7 Durable checkpoint

  Tạo một graph nhỏ để chứng minh:

  1. Bắt đầu conversation.
  2. Stream event.
  3. Interrupt.
  4. Restart service.
  5. Resume đúng thread.
  6. Tiếp tục workflow.

  ## Test cần có

  - Config validation.
  - Dependency wiring.
  - Conversation ownership.
  - Anonymous signed credential.
  - JWT leakage tests.
  - SSE serialization.
  - Checkpoint resume sau restart.
  - Readiness khi dependency down.
  - Log redaction.

  ## Điều kiện hoàn thành

  Một conversation có thể được tạo, stream, persist, reload và resume sau restart mà không làm lộ JWT hay dữ liệu nhạy
  cảm.

  ———

  # 5. Phase 3 — Backend gateway và tool framework

  Trước khi xây agent, cần làm lớp giao tiếp backend ổn định.

  ## 5.1 Backend client

  Backend client chịu trách nhiệm kỹ thuật:

  - HTTP connection pooling.
  - Timeout.
  - Correlation headers.
  - JWT forwarding từ runtime context.
  - Retry policy.
  - Response parsing.
  - Error normalization.

  Không chứa business rule.

  ## 5.2 Backend gateway

  Gateway chuyển HTTP contract thành operation trung lập:

  search_vehicles(...)
  get_vehicle_detail(...)
  prepare_lead(...)
  execute_lead(...)
  prepare_order(...)
  execute_order(...)
  list_owned_orders(...)
  get_owned_order(...)

  Service và tool không nên biết URL cụ thể.

  ## 5.3 Tool contracts

  Tool phải:

  - Có input schema chặt.
  - Có output envelope ổn định.
  - Không trả raw backend payload.
  - Không nhận JWT làm argument.
  - Không chứa business rule.
  - Không log PII thô.
  - Fail closed khi backend response sai contract.

  ## 5.4 Capability enforcement

  Mỗi tool có metadata:

  required_auth
  allowed_agents
  read_or_write
  approval_requirement
  timeout_policy
  retry_policy

  Enforcement phải bằng code/middleware, không chỉ ghi trong prompt.

  ## Retry policy

  - GET/read: bounded retry với backoff.
  - 401/403/404/422: không retry.
  - 429: retry có giới hạn nếu an toàn.
  - Command: chỉ retry với cùng idempotency key.
  - Contract error: không retry mù.

  ## Điều kiện hoàn thành

  Toàn bộ backend capability có thể được gọi qua fake và real adapter với cùng interface, cùng error category và cùng
  tool envelope.

  ———

  # 6. Phase 4 — Vehicle Advisor vertical slice

  Đây là feature đầu tiên vì read-only, rủi ro thấp hơn write workflow.

  ## 6.1 Xây catalog read tools

  search_vehicles
  get_vehicle_detail
  compare_vehicles
  compare_vehicle_variants

  Mỗi result phải đánh dấu:

  source = backend
  authoritative_at = timestamp

  ## 6.2 Xây RAG ingestion pipeline

  Upload
  → validate
  → parse
  → normalize
  → chunk
  → embed
  → index
  → record metadata/version

  Metadata tối thiểu:

  - Document ID.
  - Type.
  - Title.
  - Source URL.
  - Section.
  - Version.
  - Effective date.
  - Expiry date.
  - Audience.
  - Language.

  ## 6.3 Xây retrieval pipeline

  Query normalization
  → retrieve
  → metadata filtering
  → optional rerank
  → context assembly
  → citation mapping

  Retrieval result phải giữ source identity để frontend hiển thị citation.

  ## 6.4 Authority policy

  Trước khi generate answer:

  - Dynamic fact → backend tool.
  - Explanatory knowledge → RAG.
  - Dynamic fact có trong RAG nhưng chưa được backend xác nhận → không trình bày như fact hiện tại.
  - RAG unavailable → vẫn trả backend facts và thông báo thiếu supporting knowledge.

  ## 6.5 Vehicle Advisor

  Agent được allowlist:

  search_vehicles
  get_vehicle_detail
  compare_vehicles
  compare_vehicle_variants
  search_knowledge

  Agent trả structured result:

  - Recommendation.
  - Compared vehicles.
  - Missing fields.
  - Backend facts.
  - Knowledge explanation.
  - Sources.
  - Suggested next action.

  Nếu thiếu budget hoặc usage criteria, agent phải trả missing fields để coordinator hỏi một câu tập trung.

  ## 6.6 Customer Assistant phiên bản đầu

  Coordinator chỉ cần:

  - Nhận diện vehicle-advice intent.
  - Kiểm tra capability.
  - Delegate sang Vehicle Advisor.
  - Nhận structured result.
  - Tạo câu trả lời cuối.
  - Không tự gọi write tools.

  ## Evaluation cần có

  Tạo golden dataset gồm:

  - Tìm xe theo ngân sách.
  - So sánh hai mẫu xe.
  - So sánh variant.
  - Hỏi màu tương thích.
  - Hỏi chính sách.
  - Câu hỏi kết hợp catalog và policy.
  - Prompt injection nằm trong RAG document.
  - RAG cũ xung đột với backend hiện tại.
  - Câu hỏi thiếu thông tin.
  - Không tìm thấy xe.

  Chỉ số:

  - Tool selection accuracy.
  - Retrieval relevance.
  - Citation correctness.
  - Dynamic-fact grounding.
  - Missing-field behavior.
  - Hallucination rate.
  - Latency và token usage.

  ## Điều kiện hoàn thành

  Vehicle Advisor không tạo giá, availability hoặc compatibility từ model/RAG; mọi dynamic fact đều truy nguyên được về
  backend.

  ———

  # 7. Phase 5 — Order Support vertical slice

  Feature này có authentication và ownership nhưng vẫn read-only.

  ## Công việc

  Xây tools:

  list_owned_orders
  get_owned_order
  get_checkout_eligibility

  Xây OrderSupport:

  - Liệt kê order của current user.
  - Giải thích trạng thái.
  - Trình bày status history.
  - Đưa next action.
  - Chỉ phát checkout.available nếu backend xác nhận eligibility.

  Coordinator phải chặn anonymous trước khi delegate hoặc tool middleware phải trả authentication_required. Tốt nhất
  thực hiện cả hai lớp.

  ## Test quan trọng

  - Anonymous bị chặn.
  - User xem được order của mình.
  - Biết order code của người khác vẫn không xem được.
  - Backend 403/404 không bị agent tìm cách route vòng.
  - Checkout event chỉ xuất hiện khi backend trả eligible.
  - JWT không vào graph state hoặc trace.
  - Order status không được ghi vào long-term memory.

  ## Điều kiện hoàn thành

  Không có đường gọi nào cho phép model, tool hoặc client tự xác nhận ownership; kết quả luôn đến từ backend.

  ———

  # 8. Phase 6 — Approval engine dùng chung

  Trước Sales Concierge và Order Concierge, nên xây approval engine chung một lần.

  ## 8.1 Draft repository

  Draft phải:

  - Server-owned.
  - Immutable business payload.
  - Gắn owner.
  - Có action type.
  - Có expiration.
  - Có stable idempotency key.
  - Có execution state.
  - Chỉ lưu reference trong graph state.

  Graph state không giữ toàn bộ draft payload.

  ## 8.2 Approval card

  Public approval projection chứa:

  - Opaque draft_id.
  - Action type.
  - Summary đã normalize.
  - Monetary preview nếu có.
  - Masked PII.
  - Policy link.
  - Expiration.
  - Approve/reject controls.

  Không trả payload thực thi đầy đủ cho frontend.

  ## 8.3 Resume contract

  Frontend chỉ gửi:

  {
    "draft_id": "opaque-id",
    "decision": "approve"
  }

  Server phải reload draft rồi kiểm tra:

  1. Conversation ownership.
  2. User ownership.
  3. Action type.
  4. Expiration.
  5. Current approval state.
  6. Execution state.
  7. Pending graph interrupt có khớp không.

  ## 8.4 Workflow shape

  prepare
  → persist draft
  → approval interrupt
  → resume validation
  → approved/rejected branch
  → revalidate
  → execute
  → persist result

  Interrupt node tuyệt đối không tạo side effect.

  ## 8.5 Concurrency và idempotency

  Cần xử lý:

  - Double click approve.
  - Hai browser tab resume cùng lúc.
  - Client retry do timeout.
  - Service restart sau backend execute nhưng trước khi lưu result.
  - LangGraph node restart.
  - Backend trả cùng kết quả cho cùng key.

  Draft store cần atomic state transition hoặc optimistic locking.

  ## Test quan trọng

  - Fake conversational “đồng ý” không thực thi.
  - Frontend sửa approval payload không ảnh hưởng server draft.
  - Draft hết hạn không execute.
  - Draft thuộc user khác không resume được.
  - Reject không tạo business entity.
  - Duplicate resume tạo đúng một entity.
  - Restart trước/sau interrupt vẫn resume được.
  - Store/checkpoint unavailable thì fail closed.
  - Thay đổi dữ liệu tạo draft mới và invalidate approval cũ.

  ## Điều kiện hoàn thành

  Một fake command chạy qua toàn bộ prepare → approval → resume → execute và chứng minh không thể duplicate side effect.

  ———

  # 9. Phase 7 — Sales Concierge

  Sau khi approval engine ổn định mới làm lead workflow thật.

  ## Luồng phát triển

  ### Domain

  - LeadDraft.
  - LeadPreview.
  - LeadExecutionResult.
  - Required fields.
  - Lead draft state.

  ### Interface

  prepare_lead
  execute_lead

  ### Sales Concierge

  Agent chỉ thu thập:

  - Vehicle interest.
  - Contact information.
  - Showroom preference.
  - Lead type nếu backend đã hỗ trợ.
  - Preferred date/time nếu contract đã hỗ trợ.

  Agent không được tự normalize theo business rule phức tạp; backend prepare chịu trách nhiệm authoritative
  normalization.

  ### Deterministic workflow

  Collect required fields
  → backend prepare_lead
  → persist immutable LeadDraft
  → approval.required
  → interrupt
  → approve/reject
  → revalidate draft
  → execute_lead với stable key
  → approval.resolved
  → message.completed

  ## Test/evaluation

  - Thiếu một field thì hỏi đúng một câu.
  - Anonymous không tạo được draft.
  - Mask phone/email trong card và log.
  - Backend validation error được diễn giải đúng.
  - Draft hết hạn.
  - Reject.
  - Duplicate approval.
  - Backend timeout sau execute.
  - 409 làm invalid draft hoặc yêu cầu prepare lại.

  ## Điều kiện hoàn thành

  Lead chỉ được tạo từ post-approval execution node và backend ghi nhận tối đa một lead cho một idempotency key.

  ———

  # 10. Phase 8 — Order Concierge

  Đây là phase rủi ro cao nhất vì liên quan tiền và checkout handoff.

  ## Domain

  - OrderDraft.
  - OrderPreview.
  - AuthoritativePrice.
  - DepositPreview.
  - VehicleConfiguration.
  - CheckoutHandoff.

  Không dùng model-generated number cho price hoặc deposit.

  ## Workflow

  Collect variant/color/customer data
  → backend prepare_order
  → validate compatibility
  → receive authoritative price/deposit
  → persist immutable OrderDraft
  → approval.required
  → interrupt
  → resume
  → reload and verify
  → backend revalidation
  → execute_order với idempotency key
  → receive order code
  → checkout eligibility/handoff

  ## Quy tắc bắt buộc

  - AI không gọi payment initialization.
  - AI không nhận card data.
  - Checkout URL phải do backend/frontend contract tạo.
  - Thay variant, color, price, deposit hoặc customer data phải tạo draft mới.
  - Backend execute phải revalidate tất cả dynamic facts.
  - 409 phải invalidate/re-prepare, không được cố execute lại draft cũ.
  - Model fallback không được xảy ra giữa prepare và execute.

  ## Test quan trọng

  - Variant/color incompatible.
  - Giá thay đổi sau approval.
  - Deposit thay đổi sau approval.
  - Double resume.
  - Execute timeout nhưng backend đã tạo order.
  - Ownership mismatch.
  - Expired approval.
  - Modified frontend payload.
  - Checkout ineligible.
  - Chứng minh không có payment tool trong allowlist.

  ## Điều kiện hoàn thành

  Có thể chạy fault-injection test tại mọi điểm của workflow mà không tạo duplicate order và không bắt đầu payment.

  ———

  # 11. Phase 9 — Hoàn thiện multi-agent topology

  Coordinator nên được mở rộng dần theo feature, không xây toàn bộ từ đầu.

  Topology cuối:

  Customer Assistant
  ├── Vehicle Advisor
  ├── Sales Concierge
  ├── Order Concierge
  └── Order Support

  ## Coordinator contract

  Coordinator nhận:

  - Current intent.
  - Capability context.
  - Conversation summary.
  - Pending action reference.
  - Structured subagent result.

  Coordinator trả:

  - Selected agent.
  - Required capability.
  - User-facing response.
  - Missing information.
  - Proposed next action.

  ## Quy tắc delegation

  - Subagent không gọi nhau.
  - Mọi delegation quay về coordinator.
  - Mỗi turn chỉ có owner rõ ràng.
  - Pending deterministic workflow không được coordinator thay thế tùy ý.
  - Protected subagent không được nhận authenticated capability chỉ vì user tự khai mình đã đăng nhập.
  - Tool allowlist enforce trong runtime.

  ## Routing evaluation

  Dataset phải kiểm tra:

  - Vehicle advice.
  - Lead intent.
  - Order creation.
  - Order lookup.
  - Mixed intent.
  - Ambiguous intent.
  - Anonymous protected request.
  - Attempt route-around after 403.
  - Prompt yêu cầu gọi unauthorized tool.
  - User đổi chủ đề khi đang có pending approval.

  ## Điều kiện hoàn thành

  Coordinator route đúng intent và không thể mở rộng quyền của subagent thông qua prompt hoặc conversational
  instruction.

  ———

  # 12. Phase 10 — Long-term memory có consent

  Memory nên triển khai sau khi core flow ổn định.

  ## Chỉ lưu khi có consent

  Có thể lưu:

  - Budget preference.
  - Loại xe yêu thích.
  - Nhu cầu sử dụng.
  - Showroom ưu tiên.

  Không lưu:

  - JWT.
  - Password.
  - Card/payment data.
  - Identity-card number.
  - Current price.
  - Current order status.
  - Approval payload.
  - Raw backend responses.

  ## Chức năng cần có

  - Consent record.
  - Read memory.
  - Update memory.
  - List memory.
  - Delete memory.
  - Conversation deletion không nhất thiết đồng nghĩa memory deletion, nhưng UI và policy phải giải thích rõ.
  - User có thể thu hồi consent.

  ## Điều kiện hoàn thành

  Memory có provenance, consent, retention policy và khả năng xóa; không có dynamic business fact hoặc secret.

  ———

  # 13. Phase 11 — Knowledge administration và synchronization

  ## Admin API

  POST /api/v1/knowledge/documents

  Phải yêu cầu admin authentication riêng, không dùng capability của customer assistant.

  ## Pipeline

  - File validation.
  - Malware/type/size checks nếu cần.
  - Parser theo định dạng.
  - Versioning.
  - Effective/expiry date.
  - Language và audience.
  - Chunking.
  - Embedding.
  - Atomic activation.
  - Old-version retirement.
  - Reindex/re-embed.
  - Delete/tombstone.

  ## Prompt-injection controls

  Retrieved document là untrusted input:

  - Không cho document thay đổi system policy.
  - Không cho document cấp permission.
  - Không cho nội dung retrieval tạo tool call trực tiếp.
  - Context phải được phân tách và gắn source metadata.
  - Lọc instruction-like content khi thích hợp.

  ## Điều kiện hoàn thành

  Admin có thể upload, version, activate, expire và reindex tài liệu mà không làm gián đoạn retrieval đang hoạt động.

  ———

  # 14. Phase 12 — Operational hardening

  ## Observability

  Theo dõi:

  - Request latency.
  - Model latency.
  - Backend-tool latency.
  - Retrieval latency.
  - Token usage.
  - Tool failure rate.
  - Agent routing accuracy.
  - Approval conversion.
  - Duplicate resume attempts.
  - Idempotency conflicts.
  - Dependency health.
  - SSE disconnect rate.

  ## Logging và tracing

  Cho phép:

  - Request ID.
  - Conversation ID.
  - Agent name.
  - Tool name.
  - Coarse result status.
  - Duration.
  - Error category.

  Không cho phép:

  - JWT.
  - Prompt chứa PII thô.
  - Full tool arguments.
  - Raw draft.
  - Identity-card data.
  - Model hidden reasoning.

  ## Resilience

  - Timeout riêng cho từng dependency.
  - Circuit breaker nếu cần.
  - Bounded retry.
  - Graceful shutdown.
  - SSE cancellation.
  - Connection pooling.
  - Checkpoint and draft availability guard.
  - Backpressure và concurrency limits.
  - Rate limit theo anonymous credential/user.

  ## Health endpoints

  /health/live chỉ kiểm tra process.

  /health/ready kiểm tra các dependency bắt buộc:

  - Database.
  - Checkpoint store.
  - Draft store.
  - Backend connectivity.
  - Model provider.
  - Vector store nếu RAG là capability bắt buộc.

  Readiness không được báo tên provider đã bỏ hoặc dependency không được khởi tạo.

  ## Điều kiện hoàn thành

  Service có thể degrade read-only capability hợp lý, nhưng fail closed đối với write workflow khi draft/checkpoint/
  backend không an toàn.

  ———

  # 15. Chiến lược test tổng thể

  Mặc dù spec nói testing nằm ngoài trọng tâm planning, dự án này không thể để testing đến cuối.

  ## Test pyramid

  ### Unit tests

  - Domain state transition.
  - Approval validation.
  - Idempotency generation.
  - Capability policy.
  - Redaction.
  - Error mapping.
  - Tool input/output.
  - Agent routing functions.
  - Context construction.

  ### Contract tests

  - Backend HTTP schema.
  - Model provider adapter.
  - Embedding adapter.
  - Vector-store adapter.
  - Checkpoint adapter.
  - Repository implementation.

  ### Integration tests

  - Conversation lifecycle.
  - SSE sequence.
  - RAG ingestion/retrieval.
  - Durable interrupt/resume.
  - Draft atomic transition.
  - Backend prepare/execute.
  - Ownership enforcement.

  ### End-to-end tests

  - Anonymous vehicle advice.
  - Authenticated order support.
  - Lead approval.
  - Order approval.
  - Service restart trong approval.
  - Duplicate resume.
  - Backend price change.
  - RAG failure.
  - Dependency timeout.

  ### Agent evaluation

  - Intent routing.
  - Tool selection.
  - Missing-field detection.
  - Source-grounded answers.
  - Dynamic-fact accuracy.
  - Prompt injection resistance.
  - Protected-capability refusal.
  - PII leakage.
  - Stable behavior qua nhiều model/provider.

  ### Security tests

  - JWT leak scanning.
  - Cross-user conversation access.
  - Cross-user draft resume.
  - Cross-user order access.
  - Approval payload tampering.
  - Tool allowlist bypass.
  - Prompt/document injection.
  - Sensitive log scanning.

  ———

  # 16. Workflow phát triển cho từng ticket

  Mỗi ticket nên đi theo chu trình này:

  1. Viết acceptance criteria và security invariants
  2. Xác định source of truth
  3. Thêm/sửa domain model
  4. Thêm/sửa interface contract
  5. Viết unit/contract test thất bại
  6. Implement service/use case
  7. Implement fake adapter
  8. Implement real adapter
  9. Expose qua tool hoặc workflow
  10. Wiring tại composition root
  11. Expose API/SSE nếu cần
  12. Chạy integration và agent evaluation
  13. Kiểm tra log/trace/PII
  14. Review dependency direction
  15. Merge khi quality gate đạt

  Một feature chưa hoàn thành nếu chỉ “agent trả lời được”. Nó chỉ hoàn thành khi:

  - Permission đúng.
  - Source of truth đúng.
  - Error behavior đúng.
  - Retry/idempotency đúng.
  - Event protocol đúng.
  - Không leak dữ liệu.
  - Có automated verification.

  ———

  # 17. Thứ tự delivery đề xuất

  M0  Product invariants + threat model
  M1  Backend contracts
  M2  Service foundation
  M3  Backend gateway + tool runtime
  M4  Vehicle Advisor + RAG
  M5  Order Support
  M6  Shared approval engine
  M7  Sales Concierge
  M8  Order Concierge
  M9  Complete coordinator routing
  M10 Consent memory
  M11 Knowledge administration
  M12 Operational/security hardening
  M13 Production readiness

  Một điều chỉnh quan trọng so với delivery flow trong spec là em tách approval engine dùng chung thành milestone độc
  lập trước Sales và Order Concierge. Nếu không, team rất dễ viết hai workflow approval gần giống nhau nhưng khác hành
  vi ở expiry, ownership, resume và idempotency.

  # 18. Production readiness gate

  Chỉ nên production khi tất cả điều sau đều đạt:

  - Backend contract tests pass.
  - Anonymous không gọi được protected capability.
  - Cross-user ownership tests pass.
  - JWT/PII leakage scan pass.
  - RAG không được dùng làm nguồn giá/trạng thái.
  - Approval card luôn backed bởi server-side immutable draft.
  - Conversational confirmation không tạo side effect.
  - Duplicate resume không tạo duplicate entity.
  - Interrupt survive restart.
  - Checkpoint/draft failure fail closed.
  - Order workflow không có payment tool.
  - SSE schema ổn định và versioned.
  - Model/provider có thể thay qua adapter.
  - Load test đạt target.
  - Alerting và rollback procedure sẵn sàng.

  Tóm lại, đường phát triển phù hợp nhất là:

  Secure foundation
  → authoritative backend tools
  → read-only intelligence
  → authenticated reads
  → reusable approval engine
  → lead write workflow
  → order write workflow
  → memory/admin capabilities
  → production hardening

  Cách đi này giải quyết phần ít rủi ro trước, chứng minh boundary và persistence sớm, rồi mới mở side effect. Nó đặc
  biệt tránh được lỗi nguy hiểm nhất của hệ multi-agent: để model điều khiển trực tiếp business mutation chỉ vì cuộc hội
  thoại có vẻ đã “đồng ý”.