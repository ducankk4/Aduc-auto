# AI Service Hybrid Deep Agent Design

**Status:** Approved design
**Date:** 2026-08-04
**Scope:** AI customer assistant for vehicle advice, lead capture, order lookup, and deposit-order creation

## 1. Objective

Build an independently deployable AI service around LangChain Deep Agents. The service acts as a client of the existing backend and supports the complete customer journey from vehicle advice through lead capture and creation of a pending deposit order.

The AI service must never become a second source of business truth. Prices, deposits, catalog availability, permissions, order ownership, and state transitions remain authoritative in the backend.

## 2. Product Scope

The initial product supports:

- Anonymous vehicle discovery, comparison, FAQ assistance, and lead creation.
- Authenticated vehicle discovery, lead creation, order lookup, and pending-order creation.
- Explicit user confirmation before every operation that writes business data.
- A checkout handoff after order creation. The AI service does not initiate or process payment.
- Vietnamese-only conversations for the MVP.

The MVP excludes payment operations, order-status updates, admin catalog actions, autonomous writes, model fine-tuning, and unrestricted host filesystem or shell access.

## 3. Chosen Architecture

Use a hybrid Deep Agent architecture:

- A `customer_assistant` coordinator handles ordinary conversation and direct tool use.
- Read-only domain tools serve catalog, knowledge, and customer-owned order queries.
- Command workflows use prepare, approve, and execute stages.
- A `vehicle_advisor` subagent handles complex comparison and recommendation work.
- An `order_support` subagent may be introduced when evaluation shows that dedicated context improves order-support quality.
- Subagents use per-invocation state by default and do not keep independent cross-conversation memory.

Subagents are added only when evaluation data demonstrates a need. Simple domain calls remain direct tools.

```text
Next.js Chat UI
      | HTTPS / SSE
      v
AI Service (FastAPI)
|-- API and authentication boundary
|-- Deep Agent runtime
|-- Tool gateway
|-- Knowledge retrieval
|-- Durable persistence
`-- Observability and redaction
      | Internal HTTP
      v
Backend API
|-- users/auth/RBAC
|-- catalog
|-- leads
|-- orders
`-- payments
      |
      v
Backend PostgreSQL
```

Deep Agents provides the coordinator harness, context management, memory, skills, subagents, and human-in-the-loop integration. LangGraph persistence provides durable checkpoints and resumable interrupts.

References:

- https://docs.langchain.com/oss/python/deepagents/overview
- https://github.com/langchain-ai/deepagents
- https://docs.langchain.com/oss/python/langgraph/persistence
- https://docs.langchain.com/oss/python/langgraph/interrupts
- https://docs.langchain.com/oss/python/langgraph/use-subgraphs

## 4. Service Boundaries

The following constraints are mandatory:

1. The AI service communicates with the backend through versioned internal HTTP APIs.
2. It does not import backend Python modules or access backend database tables.
3. Tools are thin adapters and contain no pricing, ownership, permission, order-state, or payment business rules.
4. The backend revalidates JWTs, permissions, ownership, input, price, deposit amount, variant/color compatibility, and state transitions.
5. A customer JWT is forwarded to the backend for authenticated operations.
6. Anonymous sessions may read public data and create confirmed leads, but order lookup and order creation require authentication.
7. The AI service never receives passwords and never issues application JWTs.
8. No backend module depends on the AI service.

## 5. Internal Module Layout

```text
ai_service/
|-- src/ai_service/
|   |-- main.py
|   |-- config.py
|   |-- api/
|   |   |-- chat.py
|   |   |-- conversations.py
|   |   |-- approvals.py
|   |   `-- dependencies.py
|   |-- agents/
|   |   |-- customer_assistant.py
|   |   |-- prompts.py
|   |   |-- state.py
|   |   |-- middleware.py
|   |   `-- subagents/
|   |       |-- vehicle_advisor.py
|   |       `-- order_support.py
|   |-- tools/
|   |   |-- catalog.py
|   |   |-- leads.py
|   |   |-- orders.py
|   |   |-- knowledge.py
|   |   |-- contracts.py
|   |   `-- policies.py
|   |-- providers/
|   |   |-- base.py
|   |   |-- factory.py
|   |   |-- openai.py
|   |   |-- anthropic.py
|   |   `-- openai_compatible.py
|   |-- clients/
|   |   |-- backend.py
|   |   |-- auth.py
|   |   `-- errors.py
|   |-- rag/
|   |   |-- retriever.py
|   |   |-- ingestion.py
|   |   |-- embeddings.py
|   |   `-- repositories.py
|   |-- persistence/
|   |   |-- checkpointer.py
|   |   |-- conversations.py
|   |   `-- drafts.py
|   `-- observability/
|       |-- tracing.py
|       |-- metrics.py
|       `-- redaction.py
`-- tests/
    |-- unit/
    |-- contract/
    |-- integration/
    `-- evaluation/
```

`agents` owns orchestration, `tools` owns model-facing contracts and command policies, `clients` owns backend HTTP behavior, `providers` owns model construction, `rag` owns knowledge retrieval, and `persistence` owns durable application state.

## 6. Model Provider Abstraction

Agent and business-facing code depend on LangChain's `BaseChatModel`, not a vendor SDK. A provider factory creates the configured adapter and validates this capability profile at startup:

```python
class ModelCapabilities:
    tool_calling: bool
    structured_output: bool
    streaming: bool
    parallel_tool_calls: bool
    vision: bool
```

Supported adapter families are OpenAI, Anthropic, and OpenAI-compatible/self-hosted endpoints. Provider, model, timeout, retry count, and temperature are environment configuration.

Rules:

- Production pins provider and model identifiers.
- Prompt and tool schemas avoid vendor-specific syntax.
- Provider changes require the complete evaluation suite.
- Automatic fallback is allowed only before a side effect and never halfway through an active command workflow.
- Startup fails when the selected model lacks required tool-calling, structured-output, or streaming capabilities.

## 7. Tool Contracts

Read tools execute without confirmation:

```text
search_vehicles(query, filters)
get_vehicle_detail(vehicle_slug)
compare_vehicle_variants(vehicle_slug, variant_ids)
get_my_orders()
get_my_order(order_code)
search_knowledge(query)
```

Command tools use two explicit stages:

```text
prepare_lead(vehicle_id, customer_info, showroom_pref)
execute_lead(draft_id, idempotency_key)
prepare_order(variant_id, color_id, customer_info)
execute_order(draft_id, idempotency_key)
```

The model is never offered a direct unconfirmed `create_lead` or `create_order` tool. Tools return a stable envelope:

```json
{
  "ok": false,
  "error": {
    "category": "business_conflict",
    "code": "INVALID_ORDER_STATE",
    "message": "The order is not in an allowed state."
  },
  "retryable": false
}
```

Raw stack traces, backend bodies, tokens, and secrets are never added to model context.

## 8. Human-in-the-Loop Command Flow

Every write follows this state transition:

```text
collect fields
  -> prepare against backend
  -> persist owned draft
  -> emit structured approval payload
  -> interrupt
  -> receive approve or reject
  -> reload and validate draft
  -> execute with idempotency key
  -> return authoritative result
```

The approval payload contains `action`, `draft_id`, normalized vehicle selection, backend-calculated deposit, masked customer details, and `expires_at`.

Resume requests contain only the approval decision. The server reloads the draft and verifies conversation ownership, user ownership, expiry, action type, and prior execution status. It does not trust a payload echoed by the browser.

Because an interrupted LangGraph node restarts from its beginning on resume, side effects occur in a separate post-approval node. All backend command endpoints require an `Idempotency-Key`. Repeated resumes or network retries return the original result rather than create a duplicate lead or order.

## 9. Backend HTTP Contracts

The AI service consumes versioned backend contracts equivalent to:

```text
GET  /api/v1/catalog/vehicles/search
GET  /api/v1/catalog/vehicles/{slug}
GET  /api/v1/orders/me
GET  /api/v1/orders/{order_code}
POST /api/v1/leads/validate
POST /api/v1/leads
POST /api/v1/orders/validate
POST /api/v1/orders
```

Command requests require `Idempotency-Key`. Requests include `X-Request-ID` and `X-AI-Conversation-ID`. Authenticated requests forward `Authorization: Bearer <customer JWT>`.

After a pending order is created, the AI response contains the authoritative order code and a frontend checkout URL. The AI service does not call payment initialization or payment webhooks.

## 10. RAG and Authoritative Data

Structured backend tools are the only source of truth for price, deposit, availability, variants, colors, ownership, and order status.

RAG covers descriptive and long-form content such as vehicle descriptions, extended specifications, FAQs, deposit/cancellation policies, payment guidance, and support material. Retrieved content is untrusted context, not executable instruction.

The initial retriever uses PostgreSQL with pgvector because the MVP has a small catalog and document set. A `Retriever` interface allows later migration to OpenSearch and bge-m3 without changing agent code.

Embedding synchronization may lag. Any material fact included in an answer is verified with a structured backend tool when a real-time field exists.

## 11. Persistence and Memory

Use three distinct data classes:

| Store | Purpose | Retention |
|---|---|---|
| Checkpoints | Graph state, interrupts, tool progress | Short to medium term |
| Conversations | Ownership and conversation metadata | Account retention policy |
| Long-term memory | Consented preferences such as budget and vehicle needs | Consent-based and deletable |

Production uses a PostgreSQL-backed LangGraph checkpointer. The AI service may share a PostgreSQL server with other services but uses its own database or schema and credentials.

Graph state contains messages, user context, conversation ID, intent, collected fields, pending action, compact tool results, and approval state. Large tool responses and retrieved documents are offloaded through bounded virtual storage/context middleware instead of being copied indefinitely into message history.

Long-term memory excludes passwords, JWTs, payment data, and identity-card numbers. Users can delete conversations and consented memory.

## 12. Public API and Streaming

The service exposes:

```text
POST   /api/v1/chat/streams
POST   /api/v1/conversations
GET    /api/v1/conversations/{id}
POST   /api/v1/conversations/{id}/resume
DELETE /api/v1/conversations/{id}
GET    /health/live
GET    /health/ready
```

Chat uses server-sent events with a stable event protocol:

```text
message.delta
tool.started
tool.completed
approval.required
message.completed
error
```

The service never streams chain-of-thought or hidden reasoning. The client receives answer text, coarse tool status, normalized approval payloads, and final results.

## 13. Security and Privacy

- JWTs live only in injected request/runtime context and never enter prompts, messages, checkpoints, model traces, or LangSmith payloads.
- Every read, resume, or delete operation verifies that conversation ownership matches the authenticated user or anonymous-session credential.
- Phone, email, identity-card values, and free-form PII are redacted before logging and tracing.
- Identity-card values are not stored in long-term memory.
- Backend authorization and validation are mandatory even if the AI service already checked them.
- Tools use an explicit allowlist. Deep Agent filesystem access is virtual and conversation-scoped; host shell and host filesystem access are disabled.
- Retrieved text is treated as data to resist prompt injection.
- Anonymous session, user, and IP quotas protect public endpoints.
- Provider keys, backend URLs, signing secrets, and tracing credentials use environment configuration or a secret manager.

## 14. Error Handling

Errors are normalized into these behaviors:

- Missing user input: ask for required fields.
- Backend 401: request reauthentication; do not retry.
- Backend 403: report insufficient permission; do not route around the denial.
- Backend 404, 409, or 422: present the normalized business error.
- Timeout, 502, or 503: bounded retries for reads; commands retry only with the same idempotency key.
- Model failure: fallback only before side effects.
- Retrieval failure: continue with structured tools and disclose that supporting documents are unavailable.
- Checkpoint failure: stop and execute no command.
- Tool schema violation: fail closed and record a contract error.

## 15. Observability

Each chat turn correlates:

```text
request_id
conversation_id
thread_id
user_id_hash
agent_run_id
tool_call_id
backend_request_id
model provider and model
token usage
latency
result or error category
```

Dashboards track tool success, approval and rejection rates, blocked duplicates, first-token and total latency, token cost, retrieval hit rate, and ungrounded-answer rate. Traces apply PII and secret redaction before export.

## 16. Verification Strategy

### Unit tests

Cover provider capability validation, tool mapping, hidden JWT injection, confirmation policy, redaction, error classification, draft ownership, and draft expiry.

### Backend contract tests

Verify catalog, lead, and order schemas; JWT and correlation headers; idempotency behavior; and stable mapping of 401, 403, 404, 409, and 422 responses.

### Graph integration tests

Cover anonymous advice and lead creation, authenticated order creation, durable pause/restart/resume, rejection without writes, duplicate resume safety, cross-user isolation, and backend failures before and after an interrupt.

### Agent evaluations

Maintain a versioned Vietnamese dataset for budget-based advice, variant comparison, missing fields, lead/order workflows, prompt injection, unauthorized order access, stale RAG data, and incorrect tool selection.

Initial release gates are:

```text
Tool selection accuracy        >= 95%
Required-field completion      >= 95%
Unauthorized action blocked    = 100%
Write without confirmation     = 0%
Duplicate order or lead        = 0%
Grounded factual answers       >= 95%
Conversation task success      >= 90%
```

The complete evaluation suite runs before any prompt, model, or provider promotion.

## 17. Delivery Roadmap

### AI-0: Contract readiness

Add or normalize backend search and validation endpoints, stable error codes, mandatory idempotency for command endpoints, and backend/AI contract tests.

### AI-1: Read-only assistant

Build FastAPI service boundaries, provider abstraction, coordinator, catalog and knowledge tools, SSE, PostgreSQL checkpointing, conversation ownership, and read-only evaluations.

### AI-2: Lead workflow

Add lead preparation, durable approval interrupt, idempotent execution, draft expiration, ownership checks, and restart/reject/duplicate tests.

### AI-3: Order workflow

Add customer-owned order reads, order preparation and execution, JWT forwarding, checkout handoff, and cross-user security tests.

### AI-4: Hybrid specialization

Add `vehicle_advisor` first and `order_support` only when evaluation demonstrates a measurable improvement. Use per-invocation subagent state and bounded context offloading.

### AI-5: Production hardening

Add Redis-backed quotas/cache where measurement justifies it, tracing dashboards, SSE load tests, model/version promotion controls, outage runbooks, retention controls, and consented memory deletion.

## 18. Architectural Acceptance Criteria

The design is satisfied when:

- AI business operations occur only through backend HTTP contracts.
- No write occurs without durable explicit confirmation.
- Duplicate resume and retry cannot duplicate leads or orders.
- Backend remains authoritative for all domain facts and permissions.
- Provider replacement requires configuration and evaluation, not changes to agent or tool business code.
- A service restart can resume an interrupted workflow.
- Cross-user conversation and order access are blocked.
- Tokens and sensitive PII do not appear in model context or exported traces.
- Payment remains outside AI execution scope.
- Release evaluation gates pass for the selected provider/model combination.
