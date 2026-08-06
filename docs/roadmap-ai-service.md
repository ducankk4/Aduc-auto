# Kế hoạch tổng quan triển khai AI Service

## 1. Mục tiêu và phạm vi

Xây dựng `ai-service` độc lập, giao tiếp với backend FastAPI qua HTTP và phục vụ các use case:

1. Tư vấn, tìm kiếm và so sánh xe.
2. Thu thập lead và đăng ký lái thử.
3. Tra cứu trạng thái đơn đặt cọc.
4. Hỗ trợ tạo đơn đặt cọc.
5. Hỗ trợ admin cập nhật trạng thái đơn và quản lý catalog.

AI service chỉ điều phối hội thoại và gọi API. Toàn bộ quy tắc nghiệp vụ như giá bán, tính hợp lệ của cấu hình xe, trạng thái đơn, RBAC và xử lý thanh toán vẫn thuộc backend.

## 2. Kiến trúc mục tiêu

Sử dụng Deep Agents làm lớp orchestration trên LangGraph, theo mô hình supervisor và các subagent chuyên biệt.

```text
Client / Chat UI
       |
Presentation layer
  HTTP API, streaming, conversation endpoint
       |
Application layer
  Chat use cases, session coordination, confirmation workflow
       |
Agent orchestration layer
  Supervisor Deep Agent
    |-- Vehicle Advisor Agent
    |-- Lead Agent
    |-- Order Agent
    |-- Admin Agent
       |
Tool / Integration layer
  Catalog tools | Lead tools | Order tools | Admin tools
       |
Infrastructure layer
  Backend HTTP client | RAG | checkpoint | conversation store | model provider
       |
Existing FastAPI backend
```

### Trách nhiệm các thành phần

- **Supervisor**: hiểu ý định, lập kế hoạch ngắn, chọn subagent và tổng hợp câu trả lời; không trực tiếp chứa logic nghiệp vụ.
- **Vehicle Advisor Agent**: tìm xe, giải thích cấu hình và so sánh các lựa chọn bằng catalog API kết hợp RAG.
- **Lead Agent**: thu thập đủ thông tin, xác nhận lại và gửi lead/đăng ký lái thử.
- **Order Agent**: tra cứu đơn, xây dựng bản nháp đơn đặt cọc và gửi yêu cầu tạo đơn sau xác nhận.
- **Admin Agent**: hỗ trợ tra cứu và chuẩn bị thay đổi trạng thái đơn/catalog; mọi thao tác ghi đều cần xác nhận.
- **Tools**: adapter mỏng, typed input/output, mỗi tool ánh xạ tới một backend API; không tính giá hoặc tự kiểm tra quy tắc nghiệp vụ.
- **Human-in-the-loop**: application layer lưu `pending_action`; chỉ tiếp tục tool ghi dữ liệu khi người dùng xác nhận đúng action và payload hiện tại.

## 3. Cấu trúc layer đề xuất

AI service áp dụng **Layered Architecture** với bốn layer chính. `agents` và `tools` là thành phần điều phối use case nên thuộc Application layer, không đứng ngang hàng với các layer. Domain của AI service được giữ mỏng vì nghiệp vụ xe, lead, đơn hàng và catalog đã thuộc backend.

```text
ai-service/
└── src/ai_service/
    ├── presentation/
    │   ├── api/                 # FastAPI routes, dependencies, streaming
    │   └── schemas/             # Request/response DTO
    │
    ├── application/
    │   ├── use_cases/           # Chat, confirm, reject, resume conversation
    │   ├── orchestration/
    │   │   ├── supervisor/      # Deep Agent điều phối chính
    │   │   └── subagents/       # Vehicle, Lead, Order, Admin agents
    │   ├── tools/               # Tool definitions gọi các application ports
    │   ├── ports/               # Interface tới backend, RAG, storage và LLM
    │   └── dto/                 # Dữ liệu trao đổi trong application layer
    │
    ├── domain/
    │   ├── conversation.py      # Conversation và vòng đời hội thoại
    │   ├── pending_action.py    # Action chờ người dùng xác nhận
    │   ├── agent_task.py        # Nhiệm vụ được supervisor giao
    │   └── enums.py             # ConfirmationStatus và trạng thái liên quan
    │
    ├── infrastructure/
    │   ├── backend/             # Async HTTP adapter cho FastAPI backend
    │   ├── rag/                 # Ingestion, embedding, retrieval adapter
    │   ├── persistence/         # Conversation, checkpoint, pending-action storage
    │   └── llm/                 # LangChain model provider và model factory
    │
    ├── bootstrap/               # Khởi tạo dependency và assemble agent graph
    └── config.py
```

### Trách nhiệm từng layer

- **Presentation**: nhận request, stream response và chuyển dữ liệu sang Application; không điều phối agent hoặc gọi backend trực tiếp.
- **Application**: triển khai luồng hội thoại, supervisor/subagent, tool calling và human-in-the-loop. Layer này điều phối nghiệp vụ nhưng không chứa quy tắc nghiệp vụ của hệ thống bán xe.
- **Domain**: chỉ mô hình hóa state và quy tắc vòng đời riêng của AI service: `Conversation`, `PendingAction`, `AgentTask`, `ConfirmationStatus`. Không sao chép entity `Vehicle`, `Lead`, `Order` hoặc `Payment` từ backend.
- **Infrastructure**: hiện thực các port bằng Deep Agents/LangGraph, HTTP client, vector store, checkpoint store và model provider.

### Quy tắc phụ thuộc

```text
Presentation -> Application -> Domain
Infrastructure -> Application ports / Domain
Bootstrap -> khởi tạo và kết nối các implementation
```

- Presentation chỉ gọi Application use case.
- Application có thể dùng Domain và các interface trong `application/ports`; không import implementation từ Infrastructure.
- Infrastructure hiện thực Application ports; không chứa use case hoặc quy tắc điều phối hội thoại.
- Domain không phụ thuộc FastAPI, Deep Agents, LangGraph, HTTP client, database hoặc vector store.
- Tool chỉ chuyển đổi input/output và gọi port tương ứng; không tính giá, validate trạng thái đơn hoặc tự thực hiện nghiệp vụ backend.
## 4. Lộ trình theo phase và use case

### Phase 0 — Nền tảng AI service

- Khởi tạo service, configuration, model factory và FastAPI chat/stream endpoint.
- Xây HTTP client dùng chung và typed contract cho backend.
- Thiết lập conversation, LangGraph checkpoint và `pending_action`.
- Tạo supervisor Deep Agent và cơ chế đăng ký subagent/tool.

**Đầu ra:** hội thoại nhiều lượt hoạt động, giữ được session và supervisor gọi được một tool đọc mẫu.

### Phase 1 — Tư vấn và so sánh xe

- Xây Catalog HTTP tools: danh sách, chi tiết, phiên bản, màu và option.
- Xây pipeline RAG cho nội dung tư vấn dài như mô tả, thông số và FAQ; dữ liệu giá/cấu hình hiện hành luôn lấy từ backend API.
- Triển khai Vehicle Advisor Agent cho tìm kiếm, tư vấn và so sánh có cấu trúc.

**Đầu ra:** người dùng có thể mô tả nhu cầu, nhận gợi ý xe và so sánh các cấu hình dựa trên dữ liệu hiện hành.

### Phase 2 — Lead và đăng ký lái thử

- Triển khai Lead Agent thu thập dần thông tin còn thiếu qua hội thoại.
- Sinh bản tóm tắt payload để người dùng kiểm tra.
- Sau xác nhận, gọi API tạo lead hoặc đăng ký lái thử và trả mã kết quả.

**Đầu ra:** hoàn thành trọn luồng tư vấn đến tạo lead/lịch lái thử với một điểm xác nhận trước khi ghi.

### Phase 3 — Tra cứu đơn đặt cọc

- Triển khai Order Agent và tool tra cứu trạng thái/lịch sử đơn.
- Bổ sung bước xác minh thông tin cần thiết qua contract backend trước khi trả dữ liệu đơn.
- Chuẩn hóa câu trả lời theo trạng thái và bước tiếp theo của đơn.

**Đầu ra:** khách hàng tra cứu được trạng thái và tiến trình đơn ngay trong hội thoại.

### Phase 4 — Hỗ trợ tạo đơn đặt cọc

- Order Agent thu thập xe, phiên bản, màu, option và thông tin khách hàng.
- Backend API kiểm tra cấu hình và trả lại preview chính thức gồm giá/cọc.
- Lưu preview thành `pending_action`; chỉ gọi API tạo đơn sau khi người dùng xác nhận.
- Trả kết quả tạo đơn và hướng dẫn chuyển sang luồng thanh toán hiện có; AI không trực tiếp xử lý thanh toán.

**Đầu ra:** hoàn thành luồng cấu hình xe đến tạo đơn, có xác nhận trên payload và giá do backend cung cấp.

### Phase 5 — Tác vụ admin

- Triển khai Admin Agent với các tool đọc đơn/catalog trước.
- Bổ sung thay đổi trạng thái đơn và CRUD catalog theo API backend hiện có.
- Mọi tool ghi tạo `pending_action`, hiển thị thay đổi trước/sau và chỉ thực thi sau xác nhận.

**Đầu ra:** admin có thể tra cứu và thực hiện các cập nhật được hỗ trợ bằng ngôn ngữ tự nhiên, vẫn tuân theo nghiệp vụ backend.

### Phase 6 — Hoàn thiện trải nghiệm đa agent

- Hoàn thiện routing giữa các subagent và xử lý yêu cầu gồm nhiều use case liên tiếp.
- Bổ sung streaming trạng thái như đang tra cứu, chờ bổ sung thông tin và chờ xác nhận.
- Hoàn thiện cơ chế resume sau xác nhận hoặc từ chối và tóm tắt hội thoại dài.
- Chuẩn hóa cách bổ sung một subagent/tool mới mà không sửa lõi supervisor.

**Đầu ra:** trải nghiệm hội thoại thống nhất xuyên suốt tư vấn -> lead/đặt cọc -> tra cứu đơn -> nghiệp vụ admin.
  
## 5. Thứ tự ưu tiên triển khai

```text
Nền tảng
  -> Tư vấn xe
  -> Lead/lái thử
  -> Tra cứu đơn
  -> Tạo đơn đặt cọc
  -> Admin
  -> Hoàn thiện phối hợp đa agent
```

Thứ tự này đi từ read-only đến write workflow, đồng thời mỗi phase tạo ra một vertical slice có thể sử dụng độc lập. Không triển khai một subagent chung cho mọi nghiệp vụ ngay từ đầu; mỗi subagent chỉ được thêm khi tool contract và use case tương ứng đã rõ ràng.

## 6. Các quyết định cần giữ cố định

- AI service chỉ gọi backend qua HTTP, không truy cập trực tiếp database nghiệp vụ.
- Dữ liệu động như giá, cấu hình và trạng thái đơn lấy từ API; RAG chỉ hỗ trợ truy xuất nội dung tư vấn.
- Mọi thao tác nhạy cảm phải tạo preview/pending action và chờ xác nhận.
- Payload được xác nhận phải bất biến; nếu nội dung thay đổi thì yêu cầu xác nhận lại.
- Subagent không gọi lẫn nhau trực tiếp; supervisor chịu trách nhiệm giao việc và tổng hợp.
- Conversation/checkpoint của AI tách khỏi dữ liệu nghiệp vụ của backend.

## 7. Gợi ý bổ sung (chưa có trong roadmap hiện tại)

### Phase 7 — Observability & Hardening

- OpenTelemetry tracing cho conversation flow và tool calls
- Prometheus metrics: token usage, latency p50/p95/p99, error rate, retry rate
- Structured logging với session_id và agent_task correlation
- Health check endpoint và readiness probe
- Chaos testing cho backend failure scenarios (timeout, 5xx, circuit breaker)

### Non-Functional Requirements

- Response time target: < 3s cho first token, < 8s cho full response
- Concurrency: support tối thiểu 100 concurrent sessions
- Data retention: conversation lưu 90 ngày, sau đó archive/compress
- RAG refresh: catalog data sync tối thiểu mỗi 1 giờ
- Availability target: 99.5% uptime

### Error Handling & Resilience

- Tool call failure: retry với backoff, fallback text response
- Backend API timeout: circuit breaker + graceful degradation
- LLM hallucination: tool validation layer, reject invalid tool calls
- Routing failure: fallback về default agent với clarification prompt
- Checkpoint recovery: resume conversation từ last checkpoint sau restart

### Security & Compliance

- PII redaction trong conversation logs
- Rate limiting per user/session
- Admin tool access control (verify RBAC từ backend trước khi allow)
- Input sanitization và output filtering
- Audit log cho tất cả admin write operations

### Session & Infrastructure

- Persistence layer choice: Redis cho checkpoint (real-time), PostgreSQL cho long-term storage
- Session cleanup: auto-expire inactive sessions sau 24h
- Model fallback: khi primary LLM unavailable, switch to smaller model với degraded experience
- RAG data sync: background job để sync catalog + FAQ vào vector store

## 8. Tối ưu hiệu năng và mở rộng quy mô (scale-out)

### Phase 8 — Performance Optimization & Scale-out

#### 8.1 Cache & Prefetch
- Response caching: cache các câu trả lời phổ biến (FAQ, so sánh xe tiêu biểu) với TTL
- Catalog prefetch: preload các xe hot, cấu hình phổ biến vào local cache
- RAG result caching: cache embedding kết quả truy vấn thường gặp
- CDN cho static assets: hình ảnh xe, brochure, video review

#### 8.2 Model Optimization
- Prompt compression & pruning để giảm token count
- Context window management: truncate old messages intelligently, summarization
- Speculative decoding / faster inference nếu model support
- Quantization: INT8/INT4 cho local deployment, giảm memory footprint
- Batch processing cho admin bulk operations

#### 8.3 Multi-instance & Scaling
- Horizontal scaling: run multiple ai-service instances behind load balancer
- Stateful sessions: share checkpoint qua Redis cluster
- Queue-based processing: dùng message queue (RabbitMQ/Kafka) cho heavy operations
- WebSocket support: real-time bidirectional communication thay vì chỉ streaming HTTP

#### 8.4 Advanced RAG
- Hybrid search: kết hợp vector similarity + keyword/bm25
- Query rewriting: rewrite user query trước khi embedding để improve recall
- Multi-document chunking: link thông tin giữa catalog, spec sheet, FAQ
- Embedding evaluation: đánh giá RAG quality với retrieval accuracy, MRR, NDCG
- Feedback loop: ghi nhận user thumbs-up/down để retrain/query improve

#### 8.5 A/B Testing & Experimentation
- Experiment framework: test different prompts, models, routing strategies
- Metrics dashboard: conversion rate (từ tư vấn -> lead), task success rate
- Shadow mode: chạy model mới song song để so sánh trước khi switch
- User satisfaction tracking: NPS score sau mỗi conversation

#### 8.6 Localization & Multi-language
- Multi-language support: tiếng Việt ưu tiên, tiếng Anh fallback
- Language detection auto trong conversation
- Cultural adaptation: response tone phù hợp với market
- Translation pipeline cho catalog content

#### 8.7 Mobile & Channel Integration
- Mobile SDK: embed ai-service trong mobile app (iOS/Android)
- Zalo/Facebook Messenger integration
- WhatsApp Business API cho follow-up notifications
- Push notification: thông báo khi đơn đặt cọc thay đổi trạng thái

### Deliverables Phase 8
- P95 latency giảm < 2s cho first token sau optimization
- Support 500+ concurrent sessions với stable performance
- RAG retrieval accuracy > 85% (evaluated by human)
- A/B test framework operational với ít nhất 2 experiments running
- Mobile SDK hoặc channel integration cho ít nhất 1 platform mới
