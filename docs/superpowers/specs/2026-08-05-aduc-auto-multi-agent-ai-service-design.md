# Aduc Auto Multi-Agent AI Service Design

**Status:** Approved for specification review  
**Date:** 2026-08-05  
**Scope:** Independent AI assistant service for vehicle advice, authenticated lead and deposit-order workflows, order support, RAG, and human approval

## 1. Objective

Build an independently deployable AI service for the Aduc Auto website. The service uses a LangChain Deep Agents coordinator with specialized subagents for vehicle advice, sales lead assistance, deposit-order creation, and customer-owned order support.

The AI service is a client of the existing backend. It must not become a second implementation of catalog, pricing, lead, order, payment, authorization, or ownership rules. All business facts and mutations remain authoritative in the backend.

## 2. Product Scope

### 2.1 Anonymous users

Anonymous users may:

- Ask general questions about vehicles and policies.
- Search and compare vehicles, variants, and colors.
- Receive recommendations based on budget and usage needs.
- Retrieve long-form knowledge through RAG.

Anonymous users may not create leads, create orders, view orders, or access any other protected operation.

### 2.2 Authenticated users

Authenticated users receive all anonymous capabilities and may additionally:

- Prepare and submit a consultation or test-drive lead after explicit approval.
- View their own orders and order-status history.
- Prepare and create a pending deposit order after explicit approval.
- Receive a checkout URL and continue payment in the website checkout interface.

### 2.3 Explicit exclusions

The AI service does not:

- Initialize, process, confirm, refund, or otherwise operate payments.
- Receive passwords or payment-card credentials.
- Update order or lead status.
- Perform catalog or administrative mutations.
- Read another customer's order.
- Treat RAG content as authoritative for dynamic business facts.
- Execute a write action based only on conversational confirmation.

## 3. Architectural Style

The service follows **Layered Clean Architecture for a Deep Agents runtime**.

- Layered Architecture makes the service straightforward to navigate and aligns with the team's existing Python practices.
- Clean Architecture keeps application behavior dependent on domain contracts rather than concrete model, database, vector-store, or backend-client providers.
- Deep Agents handles conversational reasoning and delegation.
- Deterministic LangGraph command workflows control every business side effect and human-in-the-loop pause/resume transition.

Provider technology is deliberately excluded from the core design. Relational databases, vector databases, model providers, embedding providers, and SDKs are selected later through adapters and configuration. PostgreSQL and Qdrant are likely infrastructure choices but are not architectural dependencies.

## 4. System Boundary

```text
Next.js Chat UI
   |  HTTPS, SSE, approval and resume requests
   v
Independent AI Service
|-- API and authentication boundary
|-- Customer Assistant coordinator
|-- Specialized Deep Agent subagents
|-- Deterministic command workflows
|-- Knowledge RAG
|-- Conversation, checkpoint and draft persistence
`-- Backend gateway
   |  Versioned internal HTTP, user JWT and idempotency keys
   v
Aduc Auto Backend
|-- users
|-- catalog
|-- leads
|-- orders
`-- payments
```

Mandatory boundary rules:

1. The AI service communicates with the backend only through versioned HTTP contracts.
2. The AI service does not import backend modules or access backend business tables.
3. No backend module imports or depends on the AI service.
4. Tools are thin adapters and do not contain pricing, compatibility, ownership, authorization, order-state, or payment rules.
5. The backend revalidates JWTs, permissions, ownership, normalized inputs, price, deposit, vehicle compatibility, and business state during every protected operation.
6. The user's JWT exists only in runtime context. It must not enter prompts, messages, graph state, checkpoints, tool schemas, or traces.
7. The AI service uses its own persistence boundary and credentials even if infrastructure is hosted on a shared server.

## 5. Multi-Agent Topology

```text
Customer Assistant
|-- Vehicle Advisor
|   |-- Catalog read tools
|   `-- Knowledge RAG
|-- Sales Concierge
|   `-- Prepare lead -> approval -> execute lead
|-- Order Concierge
|   `-- Prepare order -> approval -> execute order
`-- Order Support
    `-- Customer-owned order read tools
```

Subagents do not call one another directly. All delegation returns through the Customer Assistant. Each subagent receives the minimum tool allowlist required for its responsibility.

### 5.1 Customer Assistant

The Customer Assistant is the only conversational coordinator exposed to the user. It identifies intent, checks authentication capability, delegates work, preserves conversational continuity, combines structured subagent results, and blocks operations outside the user's permission scope.

It does not directly create leads or orders and does not call payment operations.

### 5.2 Vehicle Advisor

The Vehicle Advisor serves both anonymous and authenticated users. It:

- Searches vehicles from expressed requirements.
- Compares vehicles and variants.
- Explains specifications in user-friendly language.
- Recommends vehicles, variants, and colors.
- Uses RAG for FAQs, policies, extended descriptions, and support material.
- Verifies dynamic facts through backend catalog tools before presenting them as current.

Expected read capabilities:

```text
search_vehicles
get_vehicle_detail
compare_vehicles
compare_vehicle_variants
search_knowledge
```

### 5.3 Sales Concierge

The Sales Concierge is available only to authenticated users. It collects vehicle interest, customer contact details, and showroom preference. It prepares a normalized lead draft, requests an approval card, and executes lead creation only after a valid approval resume.

The existing backend lead schema supports consultation capture. Distinguishing consultation from test-drive scheduling requires later backend fields such as `lead_type`, `preferred_date`, and `preferred_time`.

### 5.4 Order Concierge

The Order Concierge is available only to authenticated users. It collects the selected variant, color, and required customer information. It asks the backend to validate compatibility and calculate authoritative price and deposit values. It then creates an immutable draft and requests approval.

After approval, it executes an idempotent order command and returns the authoritative order code plus a frontend checkout handoff. It never initializes payment.

### 5.5 Order Support

The Order Support subagent is available only to authenticated users. It lists the user's orders, retrieves an owned order, explains status history, and provides the appropriate next step. It may return checkout availability only when the backend reports that the order remains eligible.

Knowing an order code is not sufficient authorization. Backend ownership checks are mandatory.

## 6. Hybrid Orchestration Model

Read-only conversational work remains flexible:

```text
User message
-> Customer Assistant
-> Specialized subagent
-> Read tools and/or RAG
-> Structured subagent result
-> Customer-facing response
```

All writes use a deterministic command workflow:

```text
Collect required fields
-> Prepare against backend
-> Persist immutable owned draft
-> Emit approval.required
-> Interrupt
-> Receive approve or reject
-> Reload draft from server
-> Verify owner, expiry and execution state
-> Revalidate dynamic facts
-> Execute with idempotency key
-> Return authoritative result
```

The model is never offered a direct, unconfirmed `create_lead` or `create_order` tool. Reasoning and delegation may be probabilistic; state mutation is deterministic.

## 7. Human-in-the-Loop Approval

Write actions require a structured approval card in the frontend. A user message such as "đồng ý" may be interpreted conversationally but can never execute a command.

An approval card contains:

- Opaque `draft_id`.
- Action type.
- Normalized vehicle and configuration summary.
- Backend-calculated monetary values when applicable.
- Masked customer information.
- Relevant policy link.
- Expiration time.
- Explicit approve and reject controls.

The frontend resumes the workflow with only the draft identifier and decision. It must not echo the business payload as trusted input. The AI service reloads the server-side draft and verifies ownership, expiry, action type, approval status, and execution status.

Draft data is immutable. If a price, deposit, variant, color, or customer field changes, the previous approval becomes invalid and a new draft and approval card are required.

Because an interrupted LangGraph node may restart when resumed, the interrupt node must not perform a side effect. Lead or order creation occurs in a separate post-approval node. Every execution uses a stable idempotency key so retries and duplicate resume requests cannot create duplicate entities.

## 8. Main User Flows

### 8.1 Vehicle advice

```text
Question
-> classify intent
-> Vehicle Advisor
-> catalog lookup plus knowledge retrieval
-> verify dynamic facts
-> recommendation with sources
```

When required criteria are missing, the advisor returns structured missing fields and the coordinator asks a focused follow-up question rather than guessing.

### 8.2 Lead creation

```text
Authenticated user
-> Sales Concierge
-> collect vehicle, contact and showroom data
-> backend prepare/validate
-> persist lead draft
-> approval card and interrupt
-> approve or reject
-> idempotent execute_lead
```

Rejecting closes the draft without creating a backend lead.

### 8.3 Deposit-order creation

```text
Authenticated user
-> Order Concierge
-> collect variant, color and customer data
-> backend validates compatibility and calculates deposit
-> persist order draft
-> approval card and interrupt
-> approve or reject
-> backend revalidation
-> idempotent execute_order
-> order code plus checkout handoff
```

Payment remains a browser/backend workflow after handoff.

### 8.4 Order support

```text
Authenticated user
-> Order Support
-> backend ownership check
-> retrieve order and status history
-> explain current state and next action
```

### 8.5 Durable resume

Each conversation maps to an opaque workflow thread and durable checkpoint. When the page or service restarts, the AI service verifies conversation ownership, loads the pending interrupt, and returns the same approval card. The user can then approve or reject without repeating the conversation.

## 9. State and Persistence Model

The design separates four persistence concerns:

| Store | Responsibility |
|---|---|
| Conversation store | Ownership, metadata, lifecycle and message references |
| Checkpoint store | Graph position, compact state, interrupts and resume data |
| Draft store | Immutable command payload, ownership, expiry, approval and execution state |
| Long-term memory store | Explicitly consented, deletable customer preferences |

Graph state may contain messages, user capability context, current intent, current agent, collected non-secret fields, pending action references, and compact tool results. Large retrieval results and raw backend payloads must not accumulate indefinitely in graph state.

Long-term memory may include budget, vehicle preferences, usage needs, and preferred showroom when the user has consented. It excludes passwords, JWTs, payment data, identity-card numbers, current prices, and order statuses.

## 10. RAG and Data Authority

Structured backend tools are the only source of truth for current prices, deposits, catalog availability, variant/color compatibility, order ownership, and order status.

RAG covers vehicle descriptions, extended specifications, FAQs, deposit and cancellation policies, payment guidance, and admin-uploaded support documents.

```text
Knowledge source
-> parse
-> normalize
-> chunk
-> embed
-> index
-> retrieve
-> optional rerank
-> context with source metadata
```

Required provider-neutral contracts:

```text
KnowledgeIngestor
EmbeddingProvider
KnowledgeRepository
Retriever
Reranker
```

Knowledge metadata includes document identity, type, title, source URL, section, version, effective and expiry dates, audience, and language. Retrieved content is untrusted data and cannot override system policy or authorize a tool call.

When RAG conflicts with current backend data, the backend result always wins.

## 11. Backend Contracts

The AI service should consume versioned contracts equivalent to:

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

Prepare endpoints do not create business entities. They validate and normalize input and return authoritative preview data for the approval card. Execute endpoints revalidate all dynamic facts and require an `Idempotency-Key`.

AI requests include correlation headers:

```text
Authorization: Bearer <customer JWT>
Idempotency-Key: <stable command key>
X-Request-ID: <request identifier>
X-AI-Conversation-ID: <conversation identifier>
```

Tool results use a stable provider-neutral envelope:

```json
{
  "ok": true,
  "data": {},
  "error": null,
  "retryable": false,
  "source": "backend"
}
```

Error categories include `authentication_required`, `permission_denied`, `not_found`, `validation_error`, `business_conflict`, `rate_limited`, `dependency_unavailable`, and `contract_error`.

## 12. Public AI API and Streaming

The service exposes contracts equivalent to:

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

Knowledge administration requires an authenticated administrative contract and is not exposed to ordinary users.

The SSE protocol supports:

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

Events expose only public message content, coarse tool status, normalized approval payloads, request identifiers, conversation identifiers, sources, and final actions. They do not expose prompts, hidden reasoning, raw graph state, credentials, or tool arguments containing PII.

## 13. Source Layout

```text
ai_service/
|-- pyproject.toml
|-- README.md
|-- .env.example
`-- src/ai_service/
    |-- main.py
    |-- config.py
    |-- api/
    |   |-- chat.py
    |   |-- conversations.py
    |   |-- approvals.py
    |   |-- knowledge.py
    |   |-- dependencies.py
    |   `-- schemas.py
    |-- domain/
    |   |-- conversation.py
    |   |-- approval.py
    |   |-- draft.py
    |   |-- knowledge.py
    |   |-- events.py
    |   `-- enums.py
    |-- interfaces/
    |   |-- model.py
    |   |-- backend.py
    |   |-- retrieval.py
    |   |-- persistence.py
    |   `-- services.py
    |-- services/
    |   |-- chat_service.py
    |   |-- conversation_service.py
    |   |-- approval_service.py
    |   `-- knowledge_service.py
    |-- agents/
    |   |-- coordinator.py
    |   |-- state.py
    |   |-- middleware.py
    |   |-- prompts.py
    |   `-- subagents/
    |       |-- vehicle_advisor.py
    |       |-- sales_concierge.py
    |       |-- order_concierge.py
    |       `-- order_support.py
    |-- workflows/
    |   |-- lead_workflow.py
    |   |-- order_workflow.py
    |   `-- approval_workflow.py
    |-- tools/
    |   |-- catalog.py
    |   |-- leads.py
    |   |-- orders.py
    |   |-- knowledge.py
    |   |-- contracts.py
    |   `-- policies.py
    |-- rag/
    |   |-- ingestion.py
    |   |-- chunking.py
    |   |-- retrieval.py
    |   `-- synchronization.py
    |-- repositories/
    |   |-- conversations.py
    |   |-- drafts.py
    |   |-- memory.py
    |   `-- knowledge.py
    |-- stores/
    |   |-- checkpoint_store.py
    |   |-- relational_store.py
    |   `-- vector_store.py
    |-- providers/
    |   |-- chat_model.py
    |   |-- embeddings.py
    |   `-- factories.py
    |-- clients/
    |   |-- backend_client.py
    |   |-- auth_client.py
    |   `-- errors.py
    `-- core/
        |-- exceptions.py
        |-- runtime_context.py
        |-- security.py
        |-- idempotency.py
        |-- logging.py
        `-- redaction.py
```

Dependency direction:

```text
api -> services
services -> interfaces + domain
agents/workflows -> interfaces + domain
tools -> interfaces + domain
repositories/stores/providers/clients -> implement interfaces
main.py -> constructs and connects concrete dependencies
```

No layer may instantiate a concrete infrastructure dependency except the composition root. Files remain split by responsibility inside each layer to avoid large generic service or repository modules.

## 14. Security and Privacy

- Anonymous sessions use an opaque signed credential and strict ownership checks.
- Authenticated conversation and draft operations verify the current user.
- Backend authorization remains mandatory for every protected tool.
- Phone and email values are masked in cards, logs, and traces.
- Identity-card values do not enter model context, checkpoints, traces, or long-term memory.
- Sensitive order fields should ultimately be collected through a protected frontend form rather than free-form chat.
- Tools use explicit per-agent allowlists.
- Host shell and unrestricted host filesystem capabilities are disabled.
- Retrieved documents are treated as untrusted content.
- Secrets and provider configuration are loaded only through centralized settings or a secret manager.

## 15. Error Behavior

- Missing fields: ask one focused follow-up question.
- Backend 401: request reauthentication and do not retry.
- Backend 403: report insufficient permission and do not route around it.
- Backend 404: report that no permitted resource was found.
- Backend 409: invalidate or re-prepare the affected draft.
- Backend 422: explain the normalized invalid fields.
- Backend 429: apply bounded backoff only where safe.
- Backend timeout, 502, or 503: retry reads within configured limits; retry commands only with the same idempotency key.
- Retrieval failure: continue with structured tools and disclose that supporting knowledge is unavailable.
- Checkpoint or draft-store failure: stop and execute no command.
- Tool contract violation: fail closed and emit a public contract error.
- Model fallback is permitted only before a side effect and never midway through a prepared command workflow.

## 16. Delivery Flow

### AI-0: Backend contract readiness

Normalize catalog search, authenticated identity, owned-order reads, lead/order prepare endpoints, idempotent command endpoints, checkout eligibility, correlation headers, and stable error codes.

### AI-1: Service foundation

Create the independent FastAPI service, configuration, composition root, backend gateway, provider-neutral interfaces, conversation ownership, durable checkpoints, runtime authentication context, and SSE protocol.

### AI-2: Vehicle Advisor and RAG

Create the Customer Assistant, Vehicle Advisor, catalog read tools, knowledge ingestion/retrieval, authority policy, source metadata, and citation output.

### AI-3: Order Support

Add customer-owned order tools, status-history explanation, and checkout-availability actions.

### AI-4: Sales Concierge

Add lead drafts and the durable prepare, approval, interrupt, resume, and idempotent execute workflow.

### AI-5: Order Concierge

Add order drafts, backend compatibility/deposit preview, durable approval, idempotent creation, and checkout handoff.

### AI-6: Memory and operational hardening

Add consented preference memory, conversation deletion, PII redaction, quotas, dependency health, prompt/document injection controls, and admin knowledge synchronization.

Testing and agent evaluation are intentionally outside the planning focus of this document. The interfaces, deterministic workflows, stable event protocol, and provider boundaries are designed so those activities can be added without restructuring the service.

## 17. Architectural Acceptance Criteria

The design is satisfied when:

- One Customer Assistant coordinates four specialized subagents.
- Subagents cannot call one another directly and receive only allowlisted tools.
- Anonymous users cannot invoke protected capabilities.
- No business write executes without an explicit server-backed approval card.
- Duplicate resume and retry requests cannot duplicate leads or orders.
- The AI service never initializes or processes payment.
- The backend remains authoritative for business rules and dynamic facts.
- RAG is used only for knowledge and explanatory content.
- The service imports no backend application code and reads no backend business tables.
- Concrete infrastructure and AI providers can change without altering agent policy or command workflows.
- An interrupted approval flow survives page reload and service restart.
- JWTs, secrets, payment data, and sensitive PII do not enter model-visible or persisted graph context.

