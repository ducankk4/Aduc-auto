# AI Coding Guidelines & Architectural Standards — Aduc Auto Platform (`agent.md`)

> **Goal**: This document defines the mandatory guidelines, conventions, and architectural constraints for any developer or AI Agent working on the **Aduc Auto** codebase. Adhering to these rules ensures seamless, consistent, and maintainable development.

---

## MANDATORY CORE RULES (NON-NEGOTIABLE)

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

## Code Structure & Layering (3-Layer Pattern inside Modules)

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

## Code Quality & Clean Code

### 1. Naming Conventions

| Target | Convention | Example |
| :--- | :--- | :--- |
| Files & modules | `snake_case` | `user_repository.py` |
| Classes | `PascalCase` | `OrderService`, `UserModel` |
| Functions, methods, variables | `snake_case` | `create_deposit_order`, `is_active` |
| Constants & Enums | `UPPER_SNAKE_CASE` | `DEFAULT_PAGE_SIZE`, `MAX_LOGIN_ATTEMPTS` |
| Private helpers | `_snake_case` | `_verify_vnpay_signature` |

### 2. Type Hinting

All function parameters and return values must be explicitly type-hinted. No implicit `Any`.

```python
async def find_users_by_role(
    session: AsyncSession,
    role_id: UUID,
    limit: int = 20,
    offset: int = 0,
) -> list[UserModel]:
    """Fetch a paginated list of users belonging to a specific role."""
    ...
```

### 3. Import Order

Group imports in the following order, separated by a blank line:

1. Standard library (`datetime`, `uuid`, `typing`)
2. Third-party (`fastapi`, `sqlalchemy`, `pydantic`, `loguru`)
3. Internal application (`app.config`, `app.core.*`, `app.modules.*`)

### 4. Function & Method Design

- **Single Responsibility**: Each function does exactly one thing. If a function needs a comment to describe what it does, split it.
- **Short functions**: Aim for under 30 lines per function body. Extract named helpers for complex logic.
- **No dead code**: Remove unused imports, variables, and commented-out blocks before committing.
- **No flag arguments**: Avoid boolean parameters that switch behavior (e.g., `def process(order, send_email=True)`). Split into two separate functions.
- **Early returns**: Prefer guard clauses over deeply nested `if/else` trees.

```python
# Avoid
async def get_order(order_id, raise_if_missing=True):
    order = await repo.find(order_id)
    if raise_if_missing:
        if not order:
            raise NotFoundError()
    return order

# Prefer
async def get_order(order_id: UUID) -> OrderModel:
    order = await repo.find(order_id)
    if not order:
        raise NotFoundError()
    return order

async def find_order(order_id: UUID) -> OrderModel | None:
    return await repo.find(order_id)
```

### 5. No Magic Values

No inline string literals, numeric thresholds, or status codes in logic. All constants belong in `constants.py` or `config.py`.

```python
# Wrong
if order.status == "pending" and amount > 500_000_000:
    ...

# Correct
if order.status == OrderStatus.PENDING and amount > settings.MAX_DEPOSIT_AMOUNT:
    ...
```

### 6. Logging

Use `from loguru import logger` everywhere. Never use `print()` for runtime output.

```python
from loguru import logger

logger.info("Order confirmed: order_id={}, customer={}", order.id, order.customer_name)
logger.warning("Payment webhook duplicate: vnp_TxnRef={}", txn_ref)
logger.error("Email dispatch failed: order_id={}, error={}", order_id, err)
```

---

## Error Handling & Standard Responses

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

## Database & Migration Guidelines

1. **SQLAlchemy 2.0 Async Style**: Always use `select()`, `update()`, `delete()` with `await session.execute()` and `.scalars()`. Avoid legacy 1.x `session.query()` syntax.
2. **Alembic Migrations**: Any modification to `model.py` files MUST be followed by generating an Alembic migration script (`uv run alembic revision --autogenerate -m "description"`).
3. **Foreign Keys & Indexes**: Always add index on columns used frequently in `WHERE` clauses (e.g., `slug`, `order_code`, `email`, `phone`, `status`).

---

## Testing Standards

- **Unit Tests (`tests/unit/`)**: Test business services in isolation. Mock external dependencies (e.g., payment gateways, email senders).
- **Integration Tests (`tests/integration/`)**: Test end-to-end API endpoints against a test PostgreSQL instance. Verify status codes and exact response structure.
- **Idempotency & State Machine Tests**: Write explicit tests verifying payment webhook idempotency (duplicate call safety) and invalid order state transitions.

---

## Summary Checklist for Developers & AI Agents

Before submitting or generating any code:
- [ ] Are all classes, methods, and functions documented with clear **English docstrings**?
- [ ] Are there **ZERO hardcoded** strings, keys, URLs, or magic numbers?
- [ ] Are imports from other modules restricted **ONLY** to their `service.py`?
- [ ] Is `AsyncSession` passed across inter-module service calls for atomic transactions?
- [ ] Are function signatures 100% type-hinted?
- [ ] Are error cases throwing appropriate `AppError` exceptions?
- [ ] Does the code adhere to the `src.app...` package import format?
