# AI Coding Guidelines & Architectural Standards — Aduc Auto Platform (`agent.md`)

> **Goal**: This document defines the mandatory guidelines, conventions, and architectural constraints for any developer or AI Agent working on the **Aduc Auto** codebase. Adhering to these rules ensures seamless, consistent, and maintainable development ("vibe coding" with high precision).

---

## 🚨 MANDATORY CORE RULES (NON-NEGOTIABLE)

### 1. English Docstrings for All Functions & Classes
- **Rule**: Every single module, class, method, and function MUST be documented with clear, professional **English docstrings** following Google/Sphinx style.
- **Requirement**:
  - Describe the purpose of the function/class.
  - Document all parameters (`Args:`), return values (`Returns:`), and potential exceptions (`Raises:`).
  - Inline comments inside functions may be in English or concise Vietnamese if explaining complex business rules, but all formal docstrings MUST be in English.

```python
# ✅ CORRECT
async def get_vehicle_by_slug(session: AsyncSession, slug: str) -> VehicleModel:
    """Retrieve detailed vehicle information by its unique URL slug.

    Args:
        session (AsyncSession): Active asynchronous database session.
        slug (str): Unique vehicle URL slug identifier.

    Returns:
        VehicleModel: Database ORM entity containing vehicle details with eager-loaded variants and colors.

    Raises:
        NotFoundError: If no active vehicle is found matching the provided slug.
    """
    ...
```

---

### 2. STRICTLY NO HARDCODING (Zero Hardcode Principle)
- **Rule**: Never hardcode database URIs, API keys, secret tokens, timeouts, external URLs, page limits, magic numbers, or status strings directly inside business logic or routes.
- **Enforcement**:
  - All environment variables and global configurations must be defined in `src.app.config.Settings` (Pydantic Settings).
  - Module-specific domain constants (e.g., status codes, default values, state machine transition maps) must be placed in a dedicated `constants.py` or defined as Enums within the respective module.

```python
# ❌ WRONG (Hardcoded magic values)
if order.status == "pending":
    url = "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html?vnp_Amount=50000000"

# ✅ CORRECT
from src.app.config import settings
from src.app.modules.orders.constants import OrderStatus

if order.status == OrderStatus.PENDING:
    url = vnpay_service.build_payment_url(order=order, base_url=settings.VNPAY_URL)
```

---

### 3. Pragmatic Modular Monolith Boundaries
- **Rule**: The backend is organized into business modules under `src/app/modules/` (`users`, `catalog`, `leads`, `orders`, `payments`).
- **Communication Rules**:
  1. **Public Interface Only**: Module A must interact with Module B **ONLY** by calling public methods in `modules/B/service.py`.
  2. **No Cross-Module Model/Repository Import**: Module A is strictly forbidden from importing `modules/B/model.py` or `modules/B/repository.py`.
  3. **Single Transaction Context**: Cross-module service calls pass the same `AsyncSession` obtained from `get_db()` to maintain database atomicity.
  4. **Shared Concerns**: Cross-cutting utilities (JWT, DB Base, Audit Logging, Exception hierarchy, Response formatters) belong in `src/app/core/`.

```python
# ❌ WRONG (Direct cross-module model import)
from src.app.modules.catalog.model import VehicleVariantModel

# ✅ CORRECT (Inter-module service invocation)
from src.app.modules.catalog.service import CatalogService

variant = await CatalogService.get_variant(session, variant_id)
```

---

## 🏗️ Code Structure & Layering (3-Layer Pattern inside Modules)

Each business module under `src/app/modules/<module_name>/` must follow the 3-Layer Architecture:

```
src/app/modules/<module_name>/
├── model.py        # SQLAlchemy 2.0 ORM Entities (Database mapping)
├── repository.py   # Pure Data Access Layer (RAW SQLAlchemy queries only, no HTTP/business logic)
├── service.py      # Business Logic & Public Service Interface (Orchestrates queries, validations)
├── schema.py       # Pydantic v2 Request/Response Schemas (DTOs, Data validation)
└── api.py          # FastAPI Routers (Presentation Layer, Handles HTTP Status & Request Binding)
```

### Layer Responsibilities & Rules:
1. **`model.py`**: Inherits from `src.app.core.database.Base`. Contains table schemas, column definitions, and foreign keys.
2. **`repository.py`**: Performs database operations using `AsyncSession`. Only receives DB models or primitives. Never returns HTTP responses or raises `HTTPException`.
3. **`service.py`**: Implements business rules, state machine transitions, and cross-module calls. Raises `AppError` subclasses on business validation failures.
4. **`schema.py`**: Defines input/output schemas using Pydantic v2. Uses `ConfigDict(from_attributes=True)` for ORM compatibility.
5. **`api.py`**: Defines FastAPI routes. Uses `Depends(get_db)` and `Depends(check_permission)`. Converts output using standard `success()` / `error()` response helpers.

---

## 🐍 Python Coding Standards & Conventions

### 1. Naming Conventions
- **Files & Modules**: `snake_case.py` (e.g., `user_repository.py`)
- **Classes**: `PascalCase` (e.g., `OrderService`, `UserModel`, `PaymentGateway`)
- **Functions, Methods & Variables**: `snake_case` (e.g., `create_deposit_order`, `is_active`)
- **Constants & Enums**: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_PAGE_SIZE`, `MAX_LOGIN_ATTEMPTS`)
- **Private Helper Functions**: Preceded by an underscore `_snake_case` (e.g., `_verify_vnpay_signature`)

### 2. Type Hinting
- **Strict Typing**: All function parameters and return values **MUST** be explicitly type-hinted.
- Use Python standard collection types (`list`, `dict`, `set`, `tuple`) and `typing` constructs (`Optional`, `Union`, `AsyncGenerator`).

```python
# ✅ REQUIRED
async def find_users_by_role(
    session: AsyncSession,
    role_id: UUID,
    limit: int = 20,
    offset: int = 0,
) -> list[UserModel]:
    """Fetch a paginated list of users belonging to a specific role."""
    ...
```

### 3. Imports Formatting
Imports must be grouped in the following order (separated by a blank line):
1. Python standard library imports (`datetime`, `uuid`, `typing`).
2. Third-party library imports (`fastapi`, `sqlalchemy`, `pydantic`, `jose`).
3. Internal application imports using explicit paths from `src.app...` (`src.app.core...`, `src.app.modules...`).

---

## 🛠️ Error Handling & Standard Responses

### 1. Standard Error Handling
- Do not raise raw `HTTPException` or generic `Exception` inside domain logic.
- Use predefined `AppError` subclasses from `src.app.core.exceptions`:
  - `NotFoundError(detail)` -> HTTP 404
  - `ConflictError(detail)` -> HTTP 409
  - `ForbiddenError(detail)` -> HTTP 403
  - `UnauthorizedError(detail)` -> HTTP 401
  - `ValidationError(detail)` -> HTTP 422

### 2. Standardized API Response Output
All API router handlers in `api.py` must return responses via the core response helpers:

```python
from src.app.core.response import success, error

@router.get("/vehicles")
async def list_vehicles(session: AsyncSession = Depends(get_db)):
    vehicles, total = await CatalogService.list_vehicles(session)
    return success(
        data=vehicles,
        meta={"total": total}
    )
```

---

## 🗄️ Database & Migration Guidelines

1. **SQLAlchemy 2.0 Async Style**: Always use `select()`, `update()`, `delete()` with `await session.execute()` and `.scalars()`. Avoid legacy 1.x `session.query()` syntax.
2. **Alembic Migrations**: Any modification to `model.py` files MUST be followed by generating an Alembic migration script (`uv run alembic revision --autogenerate -m "description"`).
3. **Foreign Keys & Indexes**: Always add index on columns used frequently in `WHERE` clauses (e.g., `slug`, `order_code`, `email`, `phone`, `status`).

---

## 🧪 Testing Standards

- **Unit Tests (`tests/unit/`)**: Test business services in isolation. Mock external dependencies (e.g., payment gateways, email senders).
- **Integration Tests (`tests/integration/`)**: Test end-to-end API endpoints against a test PostgreSQL instance. Verify status codes and exact response structure.
- **Idempotency & State Machine Tests**: Write explicit tests verifying payment webhook idempotency (duplicate call safety) and invalid order state transitions.

---

## 💡 Summary Checklist for Developers & AI Agents

Before submitting or generating any code:
- [ ] Are all classes, methods, and functions documented with clear **English docstrings**?
- [ ] Are there **ZERO hardcoded** strings, keys, URLs, or magic numbers?
- [ ] Are imports from other modules restricted **ONLY** to their `service.py`?
- [ ] Is `AsyncSession` passed across inter-module service calls for atomic transactions?
- [ ] Are function signatures 100% type-hinted?
- [ ] Are error cases throwing appropriate `AppError` exceptions?
- [ ] Does the code adhere to the `src.app...` package import format?

## Logging Conventions

### Core rule
- Use `loguru` exclusively. Never use `print()` or standard `logging.getLogger()` for application code.
- Import pattern: `from loguru import logger` — no logger instantiation needed per module.
- Central config lives in `app/core/logging_config.py`, called once via `setup_logging()` in the `lifespan` context of `main.py`. Never call `logger.add()` or `logger.remove()` outside that file.

### Where logging belongs (by layer)
- **Router (API layer)**: NO business logging here. Routers only orchestrate. Request/response logging is handled automatically by `LoggingMiddleware` — do not add manual logs in route handlers.
- **Service layer**: this is where business-event logging belongs. Every meaningful business outcome (success or failure) must be logged here — e.g. login success/failure, resource created, business rule violated.
- **Repository/DB layer**: log only technical failures (query errors, timeouts, constraint violations). Do not log routine successful queries.
- **Exception handlers** (`app/core/exception_handler.py`): every handler for unexpected/unhandled exceptions MUST use `logger.exception(...)` to capture the full traceback. Handlers for expected business exceptions (`AppException` subclasses) should log at `WARNING`, not `ERROR`.

### Log level rules
| Level | Use for |
|---|---|
| `DEBUG` | Local dev tracing only (payloads, intermediate values). Never enabled in production. |
| `INFO` | Normal business events that succeeded (user logged in, role created, request completed). |
| `WARNING` | Expected failure / abnormal-but-handled case (invalid credentials, resource not found, validation rejected). |
| `ERROR` | Unexpected failure that broke a request (DB error, external API failure). |
| `CRITICAL` | System-level failure that may take down the service (DB pool exhausted, startup failure). |

Rule of thumb before choosing a level: *"If this fires 1000x/day in production, do I want an alert?"* Yes → `ERROR`/`CRITICAL`. No → `INFO`/`WARNING`.

### Environment-based behavior (must be implemented in `logging_config.py`)
- Controlled by `settings.ENV` (`development` | `production`), read via Pydantic Settings — never hardcode.
- **Development**: colorized human-readable format, minimum level `DEBUG`, `diagnose=True` (shows local variable values on exceptions).
- **Production**:
  - `serialize=True` (JSON output) for stdout, so log aggregators (ELK/CloudWatch/Datadog) can parse it.
  - Minimum level `INFO` — never `DEBUG` in production.
  - `diagnose=False` — MUST be false in production; showing local variables in tracebacks is a security leak.
  - File sink for `ERROR`+ with `rotation="00:00"`, `retention="30 days"`, `compression="zip"`.
- Standard-library loggers (`uvicorn`, `uvicorn.access`, `sqlalchemy.engine`) must be intercepted and routed through Loguru via `InterceptHandler` — never leave them on default stdlib formatting.

### Request tracing
- Every incoming request gets a `request_id` (UUID4), generated in `LoggingMiddleware`.
- Wrap request handling in `logger.contextualize(request_id=request_id)` so every log line emitted during that request — including logs from the service layer — automatically carries the same `request_id`, without passing it manually through function signatures.
- Response must echo the ID back via `X-Request-ID` header.
- Middleware logs one line per request on completion: method, path, status_code, duration_ms. Do not duplicate this logging elsewhere.

### Security / data hygiene — non-negotiable
- NEVER log: passwords, raw tokens (access/refresh), full card numbers, or other PII in plaintext.
- When logging identifiers, prefer non-sensitive fields (`user_id`, `username`) over sensitive ones (`email`, `phone`) unless explicitly required for the log's purpose.
- Never let `diagnose=True` reach production — it can leak sensitive local variables in tracebacks.
- Exception handlers must log full details internally but must NEVER return tracebacks or internal error messages in the HTTP response body — response stays generic (`"Internal server error"`).

### Format requirements
- Use Loguru's `{}`-style lazy formatting (`logger.info("User {} logged in", user_id)`), not f-strings, so string formatting is skipped when the log level is filtered out.
- Every log call tied to a specific entity should include its ID (`user_id`, `role_id`, etc.) as structured context, not just embedded in a free-text sentence — prefer `logger.bind(user_id=user_id).info(...)` or contextualize where reused across multiple lines.

### Anti-patterns agent must avoid
- Do not add `try/except` blocks purely to log-and-re-raise without adding value — let business exceptions propagate to the global exception handler.
- Do not log the same event at multiple layers (e.g., both service and router logging "user logged in").
- Do not use `print()` for debugging in committed code.
- Do not log inside tight loops at `INFO`+ level (use `DEBUG` or aggregate the result and log once).