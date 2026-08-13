# Phase 0 — Tổng kết (Shared kernel)

> Trạng thái: **DONE**, đã nghiệm thu bằng `scripts/smoke_checkpoint.py` (interrupt → resume OK).
> Đọc file này trước khi làm phase mới để biết nền tảng đã có gì — đừng dựng lại.

## Quyết định đã chốt (không mở lại nếu không có lý do mạnh)

| Quyết định | Lựa chọn | Ghi chú |
|---|---|---|
| Checkpointer LangGraph | **SQLite** (`AsyncSqliteSaver`) | File `checkpoints.db`; lên production sẽ phải cân nhắc Postgres lại |
| Data access nghiệp vụ | **Gọi backend HTTP API** (httpx) | KHÔNG query thẳng Postgres của backend |
| LLM provider | **Groq**, model `openai/gpt-oss-120b` | Factory ở `infrastructure/llm/factory.py`; Groq KHÔNG có embedding API |
| DI pattern | **Instance + constructor injection** qua Protocol | Khác backend (backend dùng @staticmethod) — có chủ đích |
| Type hint | `Optional[X]`, `List[X]` (typing cổ điển) | Ruff tắt UP006/UP035 |
| Config | **Tuyệt đối không hardcode** — Settings không có default | Thiếu key trong `.env` là app chết ngay lúc import (fail-fast, chủ đích) |
| Lint | ruff (lint + format), có `banned-api` chặn import sai layer | `uv run ruff check .` phải sạch |

## Đã có gì, ở đâu

- `core/config.py` — `Settings` (pydantic-settings) + singleton `settings`. Thêm field mới → **bắt buộc** thêm key vào cả `.env` lẫn `.env.example`.
- `core/logger.py` — loguru + intercept stdlib logging. Gọi `setup_logger()` một lần ở entry point; mọi nơi khác chỉ `from loguru import logger`.
- `core/exceptions.py` — hierarchy thuần Python: `AIServiceError` → `DomainError` / `NotFoundError` / `InfrastructureError` / `ApprovalRejectedError`. Chỉ `api/` được map sang HTTP status.
- `core/checkpointer.py` — `open_checkpointer()` async context manager, mở 1 lần cho cả vòng đời app. Được phép import langgraph (ngoại lệ ruff duy nhất ngoài agent/).
- `core/domain/car.py` — `Car`, `CarVariant`, `CarColor` (dataclass frozen, tiền dùng `Decimal`).
- `core/interface/car_repository.py` — `CarRepositoryProtocol` (`find_many`, `find_by_slug`).
- `repository/car_repository.py` — implement Protocol bằng httpx: `GET /api/v1/catalog/vehicles[/{slug}]`, bóc envelope `{"success", "data", "meta"}`, 404 → `None`, lỗi khác → `InfrastructureError`.
- `infrastructure/llm/factory.py` — `build_chat_model()` → `ChatGroq` từ settings.
- `agent/state/state.py` — `SupervisorState` (TypedDict, `messages` + reducer `add_messages`). Re-export qua `agent/state/__init__.py`.
- `scripts/smoke_checkpoint.py` — nghiệm thu exit criteria: graph 1 node interrupt, resume cùng `thread_id` chạy nốt.

## Bẫy đã biết

- Resume mà truyền **khác `thread_id`** → LangGraph im lặng mở luồng mới, không báo lỗi.
- State chỉ chứa dữ liệu serialize được — client/connection truyền qua constructor/config, không nhét vào state.
- Import phải tuyệt đối (`from core.domain.car import ...`), mọi thư mục Python phải có `__init__.py`.

## Lệnh hay dùng

```bash
uv sync && uv run ruff check .
uv run python scripts/smoke_checkpoint.py
```
