# AI Service Read-Only Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver AI-0 and AI-1: stable backend read contracts plus a provider-independent, authenticated, streaming, read-only Deep Agent service.

**Architecture:** The AI service is an independent FastAPI application that calls the backend only through HTTP. A Deep Agent coordinator receives model instances from a provider factory, invokes typed read-only tools, persists conversation ownership and graph checkpoints in an AI-owned PostgreSQL schema, and streams a stable SSE protocol without exposing hidden reasoning or credentials.

**Tech Stack:** Python 3.11+, FastAPI, Deep Agents, LangChain, LangGraph, HTTPX, Pydantic Settings, PostgreSQL checkpointer, pytest, pytest-asyncio, respx.

## Global Constraints

- AI service must not import backend application modules or query backend tables.
- Backend remains authoritative for price, deposit, catalog availability, permissions, ownership, and order state.
- JWT is injected through runtime context and must never enter prompts, messages, checkpoints, or traces.
- MVP language is Vietnamese.
- This plan is read-only: it must not create leads, create orders, initiate payments, or update domain state.
- Model providers are selected through configuration and exposed to orchestration as LangChain `BaseChatModel` instances.
- Production uses PostgreSQL persistence; in-memory persistence is allowed only in unit tests.
- No host shell or unrestricted host filesystem tool is exposed to the agent.

---

## File Map

### Backend modifications

- `backend/src/app/modules/catalog/schema.py`: typed public catalog search filters and responses.
- `backend/src/app/modules/catalog/repository.py`: filtered, paginated active-vehicle query.
- `backend/src/app/modules/catalog/service.py`: public search interface.
- `backend/src/app/modules/catalog/api.py`: versioned public search endpoint.
- `backend/tests/unit/test_catalog_service.py`: service search behavior.
- `backend/tests/integration/test_catalog_api.py`: HTTP contract coverage.

### AI service creation and modifications

- `ai_service/pyproject.toml`: runtime and test dependencies plus pytest settings.
- `ai_service/main.py`: compatibility entry point importing the application factory.
- `ai_service/src/ai_service/config.py`: validated environment configuration.
- `ai_service/src/ai_service/main.py`: FastAPI application factory and lifecycle.
- `ai_service/src/ai_service/providers/base.py`: capability contract.
- `ai_service/src/ai_service/providers/factory.py`: provider-neutral model construction.
- `ai_service/src/ai_service/clients/backend.py`: typed backend HTTP client.
- `ai_service/src/ai_service/clients/errors.py`: stable transport/domain error mapping.
- `ai_service/src/ai_service/tools/contracts.py`: Pydantic tool results.
- `ai_service/src/ai_service/tools/catalog.py`: catalog tools.
- `ai_service/src/ai_service/tools/orders.py`: authenticated order-read tools.
- `ai_service/src/ai_service/agents/state.py`: runtime context and state types.
- `ai_service/src/ai_service/agents/prompts.py`: coordinator system prompt.
- `ai_service/src/ai_service/agents/customer_assistant.py`: Deep Agent construction.
- `ai_service/src/ai_service/persistence/conversations.py`: conversation metadata and ownership.
- `ai_service/src/ai_service/persistence/checkpointer.py`: production checkpointer factory.
- `ai_service/src/ai_service/api/dependencies.py`: auth/runtime injection.
- `ai_service/src/ai_service/api/conversations.py`: conversation lifecycle API.
- `ai_service/src/ai_service/api/chat.py`: SSE chat API.
- `ai_service/src/ai_service/observability/redaction.py`: secret and PII redaction.
- `ai_service/tests/`: unit, contract, integration, and evaluation coverage.

## Task 1: Establish the AI Service Package and Configuration

**Files:**

- Modify: `ai_service/pyproject.toml`
- Replace: `ai_service/main.py`
- Create: `ai_service/src/ai_service/__init__.py`
- Create: `ai_service/src/ai_service/config.py`
- Create: `ai_service/tests/unit/test_config.py`

**Interfaces:**

- Produces: `Settings`, `get_settings()`, and importable package `ai_service`.
- Consumes: environment only; no backend or provider connections.

- [ ] **Step 1: Write failing configuration tests**

```python
def test_settings_require_backend_and_database_urls(monkeypatch):
    monkeypatch.setenv("AI_BACKEND_BASE_URL", "http://backend:8000")
    monkeypatch.setenv("AI_DATABASE_URL", "postgresql://ai:secret@postgres/ai_service")
    settings = Settings(_env_file=None)
    assert str(settings.backend_base_url) == "http://backend:8000/"
    assert settings.model_provider == "openai"


def test_settings_reject_backend_url_with_public_path(monkeypatch):
    monkeypatch.setenv("AI_BACKEND_BASE_URL", "http://backend:8000/api/v1")
    monkeypatch.setenv("AI_DATABASE_URL", "postgresql://ai:secret@postgres/ai_service")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
```

- [ ] **Step 2: Run the focused test and confirm it fails because `Settings` does not exist**

Run: `cd ai_service && .\.venv\Scripts\python.exe -m pytest tests/unit/test_config.py -v`

Expected: FAIL with an import error for `ai_service.config` or `Settings`.

- [ ] **Step 3: Add dependencies and package settings**

Add Deep Agents, HTTPX, Pydantic Settings, PostgreSQL checkpoint support, provider integrations, SSE support, pytest, pytest-asyncio, and respx to `ai_service/pyproject.toml`. Configure Hatch to package `src/ai_service` and configure pytest with `asyncio_mode = "auto"`.

Do not manually edit `uv.lock`; run `uv sync` from `ai_service` only after receiving permission to resolve/install dependencies in that environment.

- [ ] **Step 4: Implement typed settings**

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AI_", env_file=".env", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    backend_base_url: AnyHttpUrl
    database_url: PostgresDsn
    model_provider: Literal["openai", "anthropic", "openai_compatible"] = "openai"
    model_name: str
    model_temperature: float = Field(default=0.1, ge=0, le=2)
    model_timeout_seconds: float = Field(default=45, gt=0)
    model_max_retries: int = Field(default=2, ge=0, le=5)
    backend_timeout_seconds: float = Field(default=10, gt=0)

    @field_validator("backend_base_url")
    @classmethod
    def require_origin_only(cls, value: AnyHttpUrl) -> AnyHttpUrl:
        if value.path not in ("", "/"):
            raise ValueError("AI_BACKEND_BASE_URL must not include an API path")
        return value
```

Use `@lru_cache` for `get_settings()`. Replace the root demo with `from ai_service.main import app`; remove all import-time graph execution, `print`, and `input` calls.

- [ ] **Step 5: Verify package configuration**

Run: `cd ai_service && .\.venv\Scripts\python.exe -m pytest tests/unit/test_config.py -v`

Expected: PASS.

- [ ] **Step 6: Commit checkpoint**

Suggested commit: `feat(ai): establish service package and typed configuration`

## Task 2: Add the Backend Catalog Search Contract

**Files:**

- Modify: `backend/src/app/modules/catalog/schema.py`
- Modify: `backend/src/app/modules/catalog/repository.py`
- Modify: `backend/src/app/modules/catalog/service.py`
- Modify: `backend/src/app/modules/catalog/api.py`
- Modify: `backend/tests/unit/test_catalog_service.py`
- Modify: `backend/tests/integration/test_catalog_api.py`

**Interfaces:**

- Produces: `CatalogService.search_vehicles(session, query, category, min_price, max_price, page, limit)` and `GET /api/v1/catalog/vehicles/search`.
- Response: existing `{success, data, meta}` envelope with `VehicleResponseSchema` items.

- [ ] **Step 1: Write failing service and API tests**

```python
@pytest.mark.asyncio
async def test_search_vehicles_delegates_filters():
    with patch.object(CatalogRepository, "search_vehicles", new_callable=AsyncMock) as repo:
        repo.return_value = ([], 0)
        await CatalogService.search_vehicles(
            session=AsyncMock(), query="SUV", category="electric",
            min_price=Decimal("500000000"), max_price=Decimal("1500000000"),
            page=1, limit=20,
        )
        repo.assert_awaited_once()


def test_catalog_search_contract(client):
    response = client.get("/api/v1/catalog/vehicles/search?q=SUV&limit=10")
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["meta"]["limit"] == 10
```

- [ ] **Step 2: Run the tests and confirm the missing interface**

Run: `cd backend && .\.venv\Scripts\python.exe -m pytest tests/unit/test_catalog_service.py tests/integration/test_catalog_api.py -v`

Expected: FAIL because `search_vehicles` and the search route do not exist.

- [ ] **Step 3: Implement repository filtering**

Add a SQLAlchemy 2.0 query over active vehicles. Apply case-insensitive query matching to `name`, `category`, and `description`; exact category filtering; and inclusive base-price bounds. Apply identical predicates to count and data queries. Preserve eager loading of variants and colors and deterministic ordering by `created_at DESC, id ASC`.

```python
@staticmethod
async def search_vehicles(
    session: AsyncSession,
    query: str | None,
    category: str | None,
    min_price: Decimal | None,
    max_price: Decimal | None,
    page: int,
    limit: int,
) -> tuple[list[VehicleModel], int]:
    predicates = [VehicleModel.is_active.is_(True)]
    if query:
        pattern = f"%{query.strip()}%"
        predicates.append(or_(
            VehicleModel.name.ilike(pattern),
            VehicleModel.category.ilike(pattern),
            VehicleModel.description.ilike(pattern),
        ))
    # Add category and price predicates, then count and paginated select.
```

- [ ] **Step 4: Implement service validation and the route**

Reject `min_price > max_price` with the existing application validation error. Define `/vehicles/search` before `/vehicles/{slug}` so FastAPI does not bind `search` as a slug.

```python
@catalog_router.get("/vehicles/search")
async def search_vehicles(
    session: DBSession,
    q: str | None = Query(None, min_length=1, max_length=100),
    category: str | None = Query(None, max_length=50),
    min_price: Decimal | None = Query(None, ge=0),
    max_price: Decimal | None = Query(None, ge=0),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    vehicles, total = await CatalogService.search_vehicles(
        session, q, category, min_price, max_price, page, limit
    )
    data = [VehicleResponseSchema.model_validate(v).model_dump(mode="json") for v in vehicles]
    return success(data=data, meta={"page": page, "limit": limit, "total": total})
```

- [ ] **Step 5: Verify backend contract and regression suite**

Run: `cd backend && .\.venv\Scripts\python.exe -m pytest tests -q`

Expected: all tests PASS, including query, empty result, invalid price range, and route-order coverage.

- [ ] **Step 6: Commit checkpoint**

Suggested commit: `feat(catalog): add public vehicle search contract`

## Task 3: Implement the Provider-Neutral Model Factory

**Files:**

- Create: `ai_service/src/ai_service/providers/__init__.py`
- Create: `ai_service/src/ai_service/providers/base.py`
- Create: `ai_service/src/ai_service/providers/factory.py`
- Create: `ai_service/tests/unit/providers/test_factory.py`

**Interfaces:**

- Produces: `ModelCapabilities`, `ModelBundle`, and `create_model(settings) -> ModelBundle`.
- Consumers: agent construction in Task 7.

- [ ] **Step 1: Write failing provider tests**

```python
def test_create_model_uses_configured_provider(monkeypatch, settings):
    fake = object()
    init_model = Mock(return_value=fake)
    monkeypatch.setattr("ai_service.providers.factory.init_chat_model", init_model)
    bundle = create_model(settings)
    assert bundle.model is fake
    assert bundle.capabilities.tool_calling is True
    init_model.assert_called_once()


def test_unsupported_provider_fails_closed(settings):
    object.__setattr__(settings, "model_provider", "unknown")
    with pytest.raises(UnsupportedModelProviderError):
        create_model(settings)
```

- [ ] **Step 2: Run and confirm factory imports fail**

Run: `cd ai_service && .\.venv\Scripts\python.exe -m pytest tests/unit/providers/test_factory.py -v`

Expected: FAIL because provider contracts do not exist.

- [ ] **Step 3: Implement capability and bundle types**

```python
@dataclass(frozen=True)
class ModelCapabilities:
    tool_calling: bool
    structured_output: bool
    streaming: bool
    parallel_tool_calls: bool
    vision: bool = False


@dataclass(frozen=True)
class ModelBundle:
    model: BaseChatModel
    provider: str
    model_name: str
    capabilities: ModelCapabilities
```

- [ ] **Step 4: Implement one factory path per configured family**

Use `langchain.chat_models.init_chat_model` and an explicit allowlisted configuration map. Pass timeout, retry, temperature, and provider-specific base URL/API key through adapter configuration. Do not import provider SDKs from agent code.

Fail application startup unless `tool_calling`, `structured_output`, and `streaming` are enabled for the configured profile.

- [ ] **Step 5: Verify provider selection tests**

Run: `cd ai_service && .\.venv\Scripts\python.exe -m pytest tests/unit/providers/test_factory.py -v`

Expected: PASS for OpenAI, Anthropic, and OpenAI-compatible configuration; PASS for fail-closed unsupported provider behavior.

- [ ] **Step 6: Commit checkpoint**

Suggested commit: `feat(ai): add provider-neutral model factory`

## Task 4: Build the Typed Backend HTTP Client

**Files:**

- Create: `ai_service/src/ai_service/clients/__init__.py`
- Create: `ai_service/src/ai_service/clients/errors.py`
- Create: `ai_service/src/ai_service/clients/backend.py`
- Create: `ai_service/tests/contract/test_backend_client.py`

**Interfaces:**

- Produces: `BackendClient.search_vehicles`, `get_vehicle_detail`, `list_my_orders`, and `get_my_order`.
- Accepts: request-scoped JWT and correlation IDs as arguments; client stores no user token.

- [ ] **Step 1: Write failing HTTP contract tests with respx**

```python
@pytest.mark.asyncio
async def test_get_my_order_forwards_auth_and_correlation_headers(client, respx_mock):
    route = respx_mock.get("http://backend:8000/api/v1/orders/ORD-1").mock(
        return_value=httpx.Response(200, json={"success": True, "data": {"order_code": "ORD-1"}})
    )
    result = await client.get_my_order("ORD-1", "jwt-value", "req-1", "conv-1")
    request = route.calls[0].request
    assert request.headers["Authorization"] == "Bearer jwt-value"
    assert request.headers["X-Request-ID"] == "req-1"
    assert request.headers["X-AI-Conversation-ID"] == "conv-1"
    assert result["order_code"] == "ORD-1"


@pytest.mark.asyncio
async def test_backend_403_is_not_retryable(client, respx_mock):
    respx_mock.get(url__regex=r".*/orders/ORD-2").mock(
        return_value=httpx.Response(403, json={"success": False, "error": {"code": "FORBIDDEN", "message": "denied"}})
    )
    with pytest.raises(BackendForbiddenError) as exc:
        await client.get_my_order("ORD-2", "jwt", "req", "conv")
    assert exc.value.retryable is False
```

- [ ] **Step 2: Run and confirm missing client failure**

Run: `cd ai_service && .\.venv\Scripts\python.exe -m pytest tests/contract/test_backend_client.py -v`

Expected: FAIL because `BackendClient` does not exist.

- [ ] **Step 3: Implement stable errors and response parsing**

Define typed errors for unauthorized, forbidden, not found, business conflict, validation, rate limit, unavailable, timeout, and contract violation. Parse only the backend response envelope and fail closed when `success`, `data`, or `error` has an unexpected shape.

Retries are restricted to GET requests on connection errors, timeout, 502, and 503. Use bounded exponential backoff within the configured total timeout. Never log authorization headers.

- [ ] **Step 4: Implement request-scoped headers**

```python
def _headers(jwt: str | None, request_id: str, conversation_id: str) -> dict[str, str]:
    headers = {
        "X-Request-ID": request_id,
        "X-AI-Conversation-ID": conversation_id,
        "Accept": "application/json",
    }
    if jwt:
        headers["Authorization"] = f"Bearer {jwt}"
    return headers
```

Construct URLs from the validated backend origin and constant `/api/v1` paths. URL-encode slugs and order codes.

- [ ] **Step 5: Verify all client contracts**

Run: `cd ai_service && .\.venv\Scripts\python.exe -m pytest tests/contract/test_backend_client.py -v`

Expected: PASS for success envelopes, all mapped status codes, malformed responses, timeouts, and header forwarding.

- [ ] **Step 6: Commit checkpoint**

Suggested commit: `feat(ai): add typed backend API client`

## Task 5: Create Read-Only Agent Tools with Hidden Runtime Credentials

**Files:**

- Create: `ai_service/src/ai_service/agents/state.py`
- Create: `ai_service/src/ai_service/tools/__init__.py`
- Create: `ai_service/src/ai_service/tools/contracts.py`
- Create: `ai_service/src/ai_service/tools/catalog.py`
- Create: `ai_service/src/ai_service/tools/orders.py`
- Create: `ai_service/tests/unit/tools/test_catalog_tools.py`
- Create: `ai_service/tests/unit/tools/test_order_tools.py`

**Interfaces:**

- Produces: `AgentRuntimeContext`, `build_catalog_tools(client)`, and `build_order_tools(client)`.
- Tool schemas expose business inputs only; JWT and correlation values come from runtime context.

- [ ] **Step 1: Write failing tests proving credentials are hidden**

```python
def test_order_tool_schema_does_not_expose_jwt(order_tools):
    schema = order_tools[0].args_schema.model_json_schema()
    serialized = json.dumps(schema).lower()
    assert "jwt" not in serialized
    assert "authorization" not in serialized


@pytest.mark.asyncio
async def test_get_my_order_injects_runtime_context(fake_client, runtime):
    tool = build_order_tools(fake_client)[1]
    await tool.ainvoke({"order_code": "ORD-1"}, context=runtime)
    fake_client.get_my_order.assert_awaited_once_with(
        "ORD-1", runtime.jwt, runtime.request_id, runtime.conversation_id
    )
```

- [ ] **Step 2: Run and confirm missing tools**

Run: `cd ai_service && .\.venv\Scripts\python.exe -m pytest tests/unit/tools -v`

Expected: FAIL because runtime context and tools do not exist.

- [ ] **Step 3: Implement immutable runtime context**

```python
@dataclass(frozen=True)
class AgentRuntimeContext:
    conversation_id: str
    request_id: str
    user_id: UUID | None
    jwt: str | None = field(repr=False)
    anonymous_session_id: str | None = field(default=None, repr=False)
```

Do not place this object inside graph state. Inject it through the runtime context supported by LangChain/Deep Agents.

- [ ] **Step 4: Implement Pydantic tool outputs and tools**

Catalog tools accept query/filter or slug inputs. Order tools require `runtime.user_id` and `runtime.jwt`; otherwise return a normalized `authentication_required` error without calling the backend.

Tool descriptions explicitly state when to call the tool and that returned prices/status values are authoritative. Return compact structured results rather than raw HTTP bodies.

- [ ] **Step 5: Verify tool behavior and schema secrecy**

Run: `cd ai_service && .\.venv\Scripts\python.exe -m pytest tests/unit/tools -v`

Expected: PASS; tool JSON schemas contain no credential field and anonymous order access does not call the backend.

- [ ] **Step 6: Commit checkpoint**

Suggested commit: `feat(ai): expose safe read-only backend tools`

## Task 6: Add Durable Conversation Ownership and Checkpointing

**Files:**

- Create: `ai_service/src/ai_service/persistence/__init__.py`
- Create: `ai_service/src/ai_service/persistence/checkpointer.py`
- Create: `ai_service/src/ai_service/persistence/conversations.py`
- Create: `ai_service/tests/unit/persistence/test_conversations.py`
- Create: `ai_service/tests/integration/test_checkpoint_resume.py`

**Interfaces:**

- Produces: `ConversationStore.create/get/delete/assert_owner` and `checkpointer_lifespan(database_url)`.
- Conversation identity is separate from LangGraph `thread_id` and checked before every graph call.

- [ ] **Step 1: Write failing ownership tests**

```python
@pytest.mark.asyncio
async def test_user_cannot_open_another_users_conversation(store):
    conversation = await store.create(user_id=UUID(int=1), anonymous_session_id=None)
    with pytest.raises(ConversationForbiddenError):
        await store.assert_owner(conversation.id, user_id=UUID(int=2), anonymous_session_id=None)


@pytest.mark.asyncio
async def test_anonymous_session_must_match(store):
    conversation = await store.create(user_id=None, anonymous_session_id="anon-a")
    with pytest.raises(ConversationForbiddenError):
        await store.assert_owner(conversation.id, user_id=None, anonymous_session_id="anon-b")
```

- [ ] **Step 2: Run and confirm missing persistence interfaces**

Run: `cd ai_service && .\.venv\Scripts\python.exe -m pytest tests/unit/persistence/test_conversations.py -v`

Expected: FAIL because persistence interfaces do not exist.

- [ ] **Step 3: Implement conversation metadata storage**

Store `id`, opaque `thread_id`, `user_id`, hashed anonymous-session identifier, `created_at`, `updated_at`, and `deleted_at`. Use parameterized SQL through an async PostgreSQL driver or SQLAlchemy; do not reuse backend ORM models.

Return 404 for absent/deleted conversations and 403 for ownership mismatch. Do not reveal whether a forbidden conversation exists through the public API; map both to a public not-found response while retaining the internal category in redacted logs.

- [ ] **Step 4: Implement PostgreSQL checkpointer lifecycle**

Create the checkpointer once during FastAPI lifespan, run its required setup explicitly during deployment/startup migration, and close its connection pool on shutdown. Unit tests use an injected in-memory saver; production settings reject an in-memory saver.

- [ ] **Step 5: Add a process-restart integration test**

Compile a minimal graph with the PostgreSQL checkpointer, invoke a thread, dispose the graph/checkpointer, recreate both, and assert the same `thread_id` state can be loaded. Mark the test `integration` and skip with a clear reason when `AI_TEST_DATABASE_URL` is absent.

- [ ] **Step 6: Verify persistence tests**

Run: `cd ai_service && .\.venv\Scripts\python.exe -m pytest tests/unit/persistence -v`

Run with test DB: `cd ai_service && .\.venv\Scripts\python.exe -m pytest tests/integration/test_checkpoint_resume.py -v`

Expected: unit suite PASS; integration PASS when PostgreSQL is configured, otherwise one explicit skip.

- [ ] **Step 7: Commit checkpoint**

Suggested commit: `feat(ai): persist conversations and graph checkpoints`

## Task 7: Construct the Read-Only Hybrid Deep Agent

**Files:**

- Create: `ai_service/src/ai_service/agents/prompts.py`
- Create: `ai_service/src/ai_service/agents/customer_assistant.py`
- Create: `ai_service/src/ai_service/agents/subagents/__init__.py`
- Create: `ai_service/src/ai_service/agents/subagents/vehicle_advisor.py`
- Create: `ai_service/tests/unit/agents/test_customer_assistant.py`
- Create: `ai_service/tests/evaluation/cases/read_only_vi.jsonl`

**Interfaces:**

- Produces: `create_customer_assistant(model_bundle, tools, checkpointer)`.
- Agent supports catalog and authenticated order reads only.

- [ ] **Step 1: Write failing construction and policy tests**

```python
def test_agent_receives_only_allowlisted_read_tools(fake_model, checkpointer):
    agent = create_customer_assistant(fake_model, read_tools(), checkpointer)
    names = configured_tool_names(agent)
    assert set(names) == {
        "search_vehicles", "get_vehicle_detail", "compare_vehicle_variants",
        "get_my_orders", "get_my_order",
    }
    assert not any(name.startswith(("create_", "update_", "delete_", "execute_")) for name in names)


def test_system_prompt_forbids_claiming_unverified_price():
    assert "backend tool" in CUSTOMER_ASSISTANT_PROMPT.lower()
    assert "không được tự suy đoán giá" in CUSTOMER_ASSISTANT_PROMPT.lower()
```

- [ ] **Step 2: Run and confirm missing agent factory**

Run: `cd ai_service && .\.venv\Scripts\python.exe -m pytest tests/unit/agents/test_customer_assistant.py -v`

Expected: FAIL because agent construction does not exist.

- [ ] **Step 3: Implement the coordinator prompt and state policy**

The Vietnamese prompt must require tool verification for catalog price, variants, colors, and order status; ask concise follow-up questions when needed; refuse cross-user access; clearly distinguish knowledge context from instructions; and state that write/payment abilities are unavailable in this release.

Never request or reveal passwords, full payment credentials, or JWTs. Do not expose chain-of-thought.

- [ ] **Step 4: Construct the Deep Agent**

```python
def create_customer_assistant(
    model_bundle: ModelBundle,
    tools: Sequence[BaseTool],
    checkpointer: BaseCheckpointSaver,
) -> CompiledStateGraph:
    validate_required_capabilities(model_bundle.capabilities)
    return create_deep_agent(
        model=model_bundle.model,
        tools=list(tools),
        system_prompt=CUSTOMER_ASSISTANT_PROMPT,
        checkpointer=checkpointer,
        subagents=[vehicle_advisor_definition(model_bundle.model)],
    )
```

The vehicle advisor is read-only, receives a narrow tool subset, returns a structured recommendation summary, and uses per-invocation state. If library integration makes the subagent materially increase the first milestone, keep the definition behind a feature flag defaulting to disabled while preserving the coordinator interface.

- [ ] **Step 5: Create the first evaluation fixtures**

Add at least 20 JSONL cases across vehicle discovery, budget constraints, comparisons, missing information, stale-price challenge, prompt injection, anonymous order query, authenticated order query, and requests for unavailable write/payment actions. Each case includes expected tool names, forbidden tool names, and required answer facts.

- [ ] **Step 6: Verify agent policy tests**

Run: `cd ai_service && .\.venv\Scripts\python.exe -m pytest tests/unit/agents -v`

Expected: PASS without live model calls by using a fake chat model.

- [ ] **Step 7: Commit checkpoint**

Suggested commit: `feat(ai): construct read-only hybrid deep agent`

## Task 8: Expose Authenticated Conversation and SSE APIs

**Files:**

- Create: `ai_service/src/ai_service/api/__init__.py`
- Create: `ai_service/src/ai_service/api/dependencies.py`
- Create: `ai_service/src/ai_service/api/conversations.py`
- Create: `ai_service/src/ai_service/api/chat.py`
- Create: `ai_service/src/ai_service/main.py`
- Create: `ai_service/tests/integration/test_conversation_api.py`
- Create: `ai_service/tests/integration/test_chat_stream.py`

**Interfaces:**

- Produces: conversation CRUD and `POST /api/v1/chat/streams` SSE.
- SSE events: `message.delta`, `tool.started`, `tool.completed`, `message.completed`, and `error`.

- [ ] **Step 1: Write failing API ownership and stream tests**

```python
def test_user_cannot_read_another_users_conversation(client, user_a_token, user_b_token):
    created = client.post("/api/v1/conversations", headers=auth(user_a_token)).json()
    response = client.get(
        f"/api/v1/conversations/{created['data']['id']}",
        headers=auth(user_b_token),
    )
    assert response.status_code == 404


def test_chat_stream_uses_stable_sse_events(client, user_a_token, conversation_id):
    with client.stream(
        "POST", "/api/v1/chat/streams",
        headers=auth(user_a_token),
        json={"conversation_id": conversation_id, "message": "Tư vấn xe SUV"},
    ) as response:
        body = "".join(response.iter_text())
    assert "event: message.delta" in body
    assert "event: message.completed" in body
    assert "chain_of_thought" not in body
```

- [ ] **Step 2: Run and confirm routes are missing**

Run: `cd ai_service && .\.venv\Scripts\python.exe -m pytest tests/integration/test_conversation_api.py tests/integration/test_chat_stream.py -v`

Expected: FAIL with route/import errors.

- [ ] **Step 3: Implement authentication context**

Parse bearer JWT only to obtain an untrusted identity hint for conversation routing, or call a backend `/auth/me` contract to validate it before use. The backend remains authoritative. Anonymous callers receive a signed, HTTP-only anonymous-session credential. Never serialize the raw bearer token into a Pydantic response or graph input.

- [ ] **Step 4: Implement conversation routes**

Create, get, and delete conversations through `ConversationStore`. All routes call `assert_owner` before reading graph state. Return the repository's standard success/error envelope without checkpoint internals.

- [ ] **Step 5: Implement stable SSE translation**

Translate LangGraph stream events through an explicit allowlist. Emit JSON data containing public message text, tool display name, coarse status, request ID, and conversation ID. Drop internal node state, prompts, raw tool arguments containing PII, token usage detail not intended for clients, and hidden reasoning.

On client disconnect, cancel the active read-only run cleanly. Since this plan has no writes, reconnect starts a new turn using the same persisted thread.

- [ ] **Step 6: Build FastAPI lifespan and health checks**

Lifespan creates the backend HTTP client, provider bundle, checkpointer, conversation store, and compiled agent once. `/health/live` checks only the process. `/health/ready` checks initialization state and bounded connectivity to required persistence; it must not call the LLM provider on every probe.

- [ ] **Step 7: Verify API integration tests**

Run: `cd ai_service && .\.venv\Scripts\python.exe -m pytest tests/integration/test_conversation_api.py tests/integration/test_chat_stream.py -v`

Expected: PASS for authenticated ownership, anonymous ownership, stable SSE, disconnect handling, and redacted errors.

- [ ] **Step 8: Commit checkpoint**

Suggested commit: `feat(ai): expose conversation and streaming chat APIs`

## Task 9: Add Redaction, Metrics, and Full Verification

**Files:**

- Create: `ai_service/src/ai_service/observability/__init__.py`
- Create: `ai_service/src/ai_service/observability/redaction.py`
- Create: `ai_service/src/ai_service/observability/metrics.py`
- Create: `ai_service/tests/unit/observability/test_redaction.py`
- Modify: `ai_service/README.md`

**Interfaces:**

- Produces: `redact_event(payload)`, stable metric names, local setup and operational documentation.

- [ ] **Step 1: Write failing redaction tests**

```python
def test_redaction_removes_nested_credentials_and_masks_pii():
    event = {
        "authorization": "Bearer secret",
        "customer": {"phone": "0912345678", "email": "alice@example.com", "id_card": "001234567890"},
    }
    clean = redact_event(event)
    assert "secret" not in json.dumps(clean)
    assert clean["customer"]["phone"] == "09******78"
    assert clean["customer"]["email"] == "a***@example.com"
    assert clean["customer"]["id_card"] == "[REDACTED]"
```

- [ ] **Step 2: Run and confirm redactor is missing**

Run: `cd ai_service && .\.venv\Scripts\python.exe -m pytest tests/unit/observability/test_redaction.py -v`

Expected: FAIL because `redact_event` does not exist.

- [ ] **Step 3: Implement recursive redaction and metric boundaries**

Redact bearer tokens, cookies, API keys, secrets, passwords, identity-card values, phone numbers, and email local parts recursively before logging or trace export. Define counters/histograms for chat turns, tool results, backend errors, first-token latency, total latency, and model token usage. Labels must not include raw user ID, conversation ID, prompt text, phone, email, or order code.

- [ ] **Step 4: Document local operation**

Document environment variables, separate `ai_service/.venv` use, dependency installation requiring explicit approval, backend/test database prerequisites, test commands, SSE examples, provider switching, and the read-only limitation. Remove notebook-style instructions from the service README.

- [ ] **Step 5: Run complete verification**

Run backend suite:

`cd backend && .\.venv\Scripts\python.exe -m pytest tests -q`

Run AI unit and contract suites:

`cd ai_service && .\.venv\Scripts\python.exe -m pytest tests/unit tests/contract -q`

Run AI integration suite with configured test services:

`cd ai_service && .\.venv\Scripts\python.exe -m pytest tests/integration -q`

Run import-boundary scan:

`rg -n "from (backend|app)\.|import (backend|app)" ai_service/src`

Expected: all configured tests PASS; boundary scan returns zero matches; PostgreSQL-only tests report explicit skips only when the test database was intentionally not configured.

- [ ] **Step 6: Run the read-only evaluation gate**

Execute the evaluation runner against the selected configured provider. Record provider, exact model identifier, prompt version, dataset commit, tool-selection accuracy, grounded-answer accuracy, and task success. Do not promote AI-1 unless tool selection and grounded factual answers each reach at least 95%, unauthorized actions are blocked at 100%, and no write tool is present.

- [ ] **Step 7: Commit checkpoint**

Suggested commit: `test(ai): verify read-only agent foundation`

## Completion Gate

AI-0 and AI-1 are complete only when:

- Backend catalog search contract is tested and stable.
- AI service imports no backend code and accesses no backend database table.
- Provider selection is configuration-only and capability validation fails closed.
- JWTs are absent from tool schemas, graph state, checkpoints, logs, and traces.
- Anonymous and authenticated conversation ownership tests pass.
- Catalog and customer-owned order read tools work through HTTP contracts.
- PostgreSQL checkpoint state survives recreation of the service runtime.
- SSE emits only the documented public event types.
- Full backend and AI test suites pass in the configured environment.
- Read-only evaluation thresholds are recorded and satisfied.
- No lead, order, payment, update, or delete tool is exposed to the model.
