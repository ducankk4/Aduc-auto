# ai-service — Code style & convention

Quy ước bắt buộc cho toàn bộ `ai-service/`. Áp dụng cho cả 5 phase trong
[ai_service_architecture_overview.md](../../docs/ai_service_architecture_overview.md).

Nguyên tắc nền: **ai-service kế thừa style của `backend/`** (docstring, đặt tên, loguru,
pydantic-settings, async) để hai service đọc như một codebase. Chỗ nào lệch là do ràng buộc
kiến trúc riêng của ai-service, và đều được ghi rõ lý do ở mục tương ứng.

---

## 1. Môi trường & tooling

| Hạng mục | Quy định |
|---|---|
| Python | 3.11 (khớp `backend/.python-version`) |
| Package manager | `uv` — mọi dependency khai báo trong `pyproject.toml`, commit `uv.lock` |
| Build backend | `hatchling` |
| Lint + format | `ruff` (xem mục 12) |
| Logging | `loguru` |
| Config | `pydantic-settings` |

Không dùng `black`, `isort`, `flake8` riêng lẻ — `ruff` đã lo cả ba.

---

## 2. Đặt code đúng thư mục

Bảng dưới là bản rút gọn của mục 0 trong overview. Khi phân vân "file này để đâu", tra bảng
này trước, không tự tạo thư mục mới cho layer đã có chỗ.

| Đặt gì | Vào đâu |
|---|---|
| Entity thuần, enum nghiệp vụ, business rule không I/O | `core/domain/` |
| Protocol (contract) cho repository / LLM / vector store | `core/interface/` |
| Config, logger, exception hierarchy, checkpointer | `core/` (file phẳng: `core/config.py`, `core/logger.py`...) |
| Use case, orchestration logic | `services/` |
| LangGraph graph, node, state schema, tool definition | `agent/` |
| Implement Protocol: gọi DB / backend API | `repository/` |
| Implement Protocol: LLM client, vector store client | `infrastructure/llm/`, `infrastructure/vector_store/` |
| FastAPI router, request/response schema, dependency wiring | `api/` |

**Dependency rule — chiều import hợp lệ:**

```
api/  ──►  services/, agent/  ──►  core/domain/, core/interface/
                                          ▲
                    repository/, infrastructure/  ──┘  (implement Protocol)
```

Cụ thể, những import sau là **sai** và sẽ bị ruff chặn (mục 12):

- `core/domain/` import bất cứ thứ gì ngoài stdlib và `core/domain/` khác.
- `services/` hoặc `agent/` import trực tiếp từ `repository/` hay `infrastructure/`
  (phải đi qua Protocol ở `core/interface/`).
- `core/domain/`, `core/interface/`, `services/` import `fastapi`, `langchain`, `langgraph`,
  `sqlalchemy`, `httpx`.
- `repository/` hoặc `infrastructure/` import từ `services/` hay `api/` (ngược chiều).

Ngoại lệ được phép: `agent/` **được** import `langgraph`/`langchain` (đó là bản chất của nó),
`api/` **được** import `fastapi`.

---

## 3. Đặt tên

### File & thư mục

`snake_case.py`, danh từ số ít, không viết tắt: `car_repository.py`, không phải `car_repo.py`.

Tên file lặp lại vai trò của thư mục cha là chấp nhận được và được khuyến khích
(`repository/car_repository.py`) — giúp phân biệt khi mở nhiều tab.

### Class

| Loại | Quy tắc | Ví dụ |
|---|---|---|
| Domain entity | Danh từ trần, không hậu tố | `Car`, `TestDriveBooking`, `ComparisonResult` |
| Enum | Danh từ + trạng thái/loại | `BookingStatus`, `ComparisonCriteria` |
| Protocol | `<Danh từ>Protocol` | `CarRepositoryProtocol`, `RetrieverProtocol` |
| Repository impl | `<Danh từ>Repository` | `CarRepository`, `BookingRepository` |
| Service (use case) | `<Danh từ>Service` | `CarService`, `ComparisonService` |
| API schema (DTO) | `<Danh từ><Hành động>Schema` | `ChatRequestSchema`, `ChatResponseSchema` |
| Exception | `<Lý do>Error` | `CarNotFoundError`, `ApprovalRejectedError` |
| LangGraph state | `<Phạm vi>State` | `SupervisorState`, `ComparisonState` |

### Hàm

- Public: `snake_case`, bắt đầu bằng động từ — `get_car`, `build_comparison_card`.
- Private (chỉ dùng trong module/class): prefix `_` — `_normalize_spec`.
- Repository dùng tiền tố `find_` cho truy vấn có thể không ra kết quả (trả `Optional`),
  `get_` cho truy vấn bắt buộc có (raise nếu không thấy). Đây là quy ước đang dùng ở
  `backend/src/app/modules/*/repository.py`, giữ nguyên cho nhất quán.
- Factory dựng graph: `build_<tên>_graph()` — `build_supervisor_graph()`.

### Hằng số

`UPPER_SNAKE_CASE`, đặt trong `constants.py` của thư mục tương ứng hoặc cạnh nơi dùng nếu
chỉ dùng một chỗ. Không hardcode magic number/string rải rác trong logic.

---

## 4. Type hint

**Dùng cú pháp `typing` cổ điển, khớp với `backend/`:**

```python
from typing import Optional, List, Dict, Tuple, Any
```

| Dùng | Không dùng |
|---|---|
| `Optional[str]` | `str \| None` |
| `List[Car]` | `list[Car]` |
| `Dict[str, Any]` | `dict[str, Any]` |
| `Tuple[List[Car], int]` | `tuple[list[Car], int]` |

Mọi hàm public **bắt buộc** có type hint đầy đủ cho tham số và giá trị trả về. Hàm không trả
gì thì ghi rõ `-> None`.

---

## 5. Docstring

Google style, **viết bằng tiếng Anh**, có type trong ngoặc — y hệt backend.

Module docstring: một dòng tóm tắt, xuống dòng trống rồi mới đến đoạn mô tả (nếu cần).

```python
"""Data Access Layer (Repository) for vehicle catalog.

Calls the backend catalog API and maps responses into domain entities.
"""
```

Hàm/method public bắt buộc có docstring với đủ section liên quan:

```python
async def get_car(self, car_id: UUID) -> Car:
    """Retrieve a vehicle by its unique identifier.

    Args:
        car_id (UUID): Unique vehicle identifier.

    Returns:
        Car: The matching vehicle entity.

    Raises:
        CarNotFoundError: If no vehicle matches the given id.
    """
```

Hàm private ngắn và hiển nhiên thì một dòng docstring là đủ. Không viết docstring chỉ để lặp
lại tên hàm (`"""Get car."""` cho `get_car` là vô nghĩa — hoặc viết cho có ích, hoặc bỏ).

**Comment trong code** chỉ viết khi giải thích *tại sao*, không giải thích *cái gì*:

```python
# Reconfigure stdout encoding in-place so isatty() is preserved and
# loguru can still detect the terminal for colored output.
sys.stdout.reconfigure(encoding="utf-8")
```

---

## 6. Dependency injection & Protocol

**Đây là điểm lệch có chủ đích lớn nhất so với `backend/`.** Backend dùng class toàn
`@staticmethod`; ai-service dùng **instance + constructor injection**, vì Protocol chỉ kiểm
tra được trên instance và dependency rule của ai-service dựa hoàn toàn vào Protocol.

Quy trình chuẩn cho mọi dependency vượt qua ranh giới layer:

**Bước 1 — Định nghĩa Protocol ở `core/interface/`:**

```python
"""Contract for vehicle data access."""

from typing import Optional, List
from uuid import UUID
from typing import Protocol

from core.domain.car import Car


class CarRepositoryProtocol(Protocol):
    """Contract any vehicle data source must satisfy."""

    async def find_by_id(self, car_id: UUID) -> Optional[Car]:
        """Return the vehicle matching the given id, or None if absent."""
        ...

    async def find_many(self, car_ids: List[UUID]) -> List[Car]:
        """Return all vehicles matching the given ids, skipping missing ones."""
        ...
```

**Bước 2 — Service nhận Protocol, không biết implementation:**

```python
class CarService:
    """Use cases for vehicle lookup."""

    def __init__(self, car_repository: CarRepositoryProtocol) -> None:
        self._car_repository = car_repository

    async def get_car(self, car_id: UUID) -> Car:
        """..."""
        car = await self._car_repository.find_by_id(car_id)
        if car is None:
            raise CarNotFoundError(f"Không tìm thấy xe với id: {car_id}")
        return car
```

**Bước 3 — Implementation ở `repository/`, không cần kế thừa Protocol** (Python dùng
structural typing — chỉ cần khớp signature):

```python
class CarRepository:
    """Vehicle data access backed by the catalog HTTP API."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def find_by_id(self, car_id: UUID) -> Optional[Car]:
        """..."""
```

**Bước 4 — Nối dây (wiring) chỉ xảy ra ở `api/`.** Đây là nơi duy nhất được biết cả Protocol
lẫn implementation cụ thể:

```python
# api/dependencies.py
def get_car_service() -> CarService:
    """Build a CarService wired to the real repository."""
    return CarService(car_repository=CarRepository(client=get_http_client()))
```

Quy tắc phụ:
- Thuộc tính giữ dependency đặt tên `_<tên>`, gán trong `__init__`, không đổi sau đó.
- Hàm thuần túy không có dependency ngoài (tính toán, biến đổi dữ liệu) thì cứ để là
  module-level function, không cần bọc vào class cho có.
- Không dùng biến global hay singleton để né việc truyền dependency. Ngoại lệ duy nhất:
  `settings` và `logger`.

---

## 7. Exception

**Không dùng lại `AppError` của backend** — nó kế thừa `HTTPException` của FastAPI, mà
`core/`, `services/`, `agent/` bị cấm import FastAPI.

Hierarchy riêng ở `core/exceptions.py`, thuần Python:

```python
"""Framework-free exception hierarchy for ai-service."""


class AIServiceError(Exception):
    """Base exception for every error raised inside ai-service."""

    code: str = "AI_SERVICE_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class DomainError(AIServiceError):
    """Business rule violation detected in the domain layer."""

    code = "DOMAIN_ERROR"


class NotFoundError(AIServiceError):
    """A requested resource does not exist."""

    code = "NOT_FOUND"


class InfrastructureError(AIServiceError):
    """An external dependency (DB, API, LLM, vector store) failed."""

    code = "INFRASTRUCTURE_ERROR"


class ApprovalRejectedError(AIServiceError):
    """A sensitive tool call was rejected by the human approver."""

    code = "APPROVAL_REJECTED"
```

Quy tắc:
- Message hướng tới người dùng cuối viết **tiếng Việt** (khớp backend). Message chỉ để debug
  viết tiếng Anh.
- Chỉ `api/` được map exception sang HTTP status. Map ở một exception handler tập trung,
  không rải `try/except` dịch lỗi trong từng router.
- `repository/` và `infrastructure/` bắt lỗi thư viện (httpx, asyncpg, LLM SDK) rồi bọc lại
  thành `InfrastructureError` — không để lỗi thư viện rò lên `services/`.
- Không `except Exception: pass`. Nếu thật sự cần nuốt lỗi thì phải log kèm lý do.

---

## 8. Logging

Dùng `loguru`, cấu hình một lần ở `core/logger.py` (port thẳng từ `backend/src/app/core/logger.py`,
kể cả phần intercept stdlib logging).

```python
from loguru import logger

logger.info("Car lookup completed [car_id={}, found={}]", car_id, found)
```

- Dùng lazy formatting `{}` của loguru, **không** dùng f-string trong lời gọi log.
- Format ngữ cảnh theo kiểu `[key=value, key=value]` như trên cho dễ grep.
- Mức log: `DEBUG` chi tiết nội bộ, `INFO` mốc nghiệp vụ, `WARNING` bất thường vẫn xử lý được,
  `ERROR` thất bại có ảnh hưởng tới response.
- **Bắt buộc:** mọi lần trigger HITL (`interrupt()`), mọi quyết định approve/reject, và mọi
  lần gọi tool sensitive đều phải log ở mức `INFO` kèm đủ `thread_id`, tên tool, tham số đã
  che dữ liệu nhạy cảm. Đây là audit trail bắt buộc theo Phase 5 của overview.
- Không log token, mật khẩu, API key, hay toàn bộ prompt chứa dữ liệu cá nhân.

---

## 9. Config — tuyệt đối không hardcode

`core/config.py`, dùng `pydantic-settings`. **Mọi giá trị cấu hình đều phải đến từ
environment/.env — không có bất kỳ giá trị hardcode nào trong code**, kể cả dưới dạng
"default an toàn". (Điểm này khác backend: backend đặt default trong `Settings`, ai-service
không cho phép.)

```python
"""Centralized settings for ai-service."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings loaded from environment variables or .env file."""

    APP_ENV: str
    APP_DEBUG: bool

    # LLM Settings (Groq)
    GROQ_API_KEY: str
    LLM_MODEL: str
    LLM_TEMPERATURE: float

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
```

- **Field khai báo không có default** — thiếu biến nào thì app fail ngay lúc khởi động với
  validation error rõ ràng, thay vì âm thầm chạy với giá trị nướng sẵn trong code rồi vỡ ở
  môi trường thật. Fail-fast là chủ đích, không phải thiếu sót.
- Mọi URL, đường dẫn file, tên model, timeout, API key... đều là field của `Settings`.
  Thấy chuỗi `http://`, đường dẫn, hay tên model nằm ngoài `.env` là sai style.
- Field `UPPER_SNAKE_CASE`, nhóm theo comment.
- Không đọc `os.environ` ở bất kỳ đâu khác ngoài file này.
- Không commit `.env`. Duy trì `.env.example` liệt kê **đủ 100% key** với giá trị mẫu —
  đây là nơi duy nhất "default" được phép tồn tại, và nó nằm ngoài code.
- Thêm field mới vào `Settings` mà quên thêm vào `.env.example` là một bug.

---

## 10. Async

Toàn bộ I/O là `async` (khớp backend). Cụ thể:

- Mọi method của repository, infrastructure client, service có I/O đều `async def`.
- Node của LangGraph viết `async def` kể cả khi hiện tại chưa await gì — tránh phải đổi
  chữ ký về sau khi thêm I/O.
- Không gọi hàm blocking trong async context. Nếu buộc phải dùng thư viện sync, bọc bằng
  `asyncio.to_thread`.
- Hàm thuần túy không I/O thì để `def` thường, không `async` cho có.

---

## 11. Quy ước riêng cho LangGraph / LangChain

Chỉ áp dụng trong `agent/`.

**State schema** — đặt ở `agent/<phạm vi>/state.py`, dùng `TypedDict` với `Annotated` reducer:

```python
class SupervisorState(TypedDict):
    """Shared state flowing through the supervisor graph."""

    messages: Annotated[List[AnyMessage], add_messages]
    thread_id: str
```

- State chỉ chứa dữ liệu cần đi qua checkpoint. Đừng nhét object không serialize được
  (client, session, connection) vào state — truyền qua config/dependency thay vì state.
- State dùng domain entity từ `core/domain/`, không định nghĩa lại struct dữ liệu xe trong state.

**Node** — `async def <động từ>_node(state: XState) -> Dict[str, Any]`, trả về **dict chỉ
chứa các key thay đổi**, không trả nguyên state.

**Tool** — định nghĩa ở `agent/<phạm vi>/tools.py`:

- Tên tool `snake_case`, là động từ, mô tả đúng việc nó làm: `search_cars`,
  `create_test_drive_booking`.
- Docstring của tool chính là prompt cho LLM — viết rõ ràng, nêu rõ khi nào nên gọi và tham
  số nghĩa là gì. Đây là docstring hiếm hoi được ưu tiên viết cho LLM đọc hơn cho dev đọc.
- Tool **không chứa business logic** — chỉ parse tham số, gọi xuống service tương ứng, và
  format kết quả trả về. Logic nằm ở `services/`.
- Tool sensitive **bắt buộc** khai báo metadata `requires_approval=True`. Việc chặn và
  `interrupt()` do middleware xử lý tập trung, tuyệt đối không tự gọi `interrupt()` rải rác
  trong từng tool.

**Graph** — mỗi graph có một hàm `build_<tên>_graph()` trả về graph đã compile. Không tạo
graph ở module level (khiến import có side effect và không truyền được checkpointer).

**Prompt** — tách ra file riêng `agent/<phạm vi>/prompts.py` dưới dạng hằng số
`UPPER_SNAKE_CASE`, không nhúng chuỗi prompt dài giữa logic.

---

## 12. Cấu hình ruff

Thêm vào `ai-service/pyproject.toml`:

```toml
[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "TID"]
# UP006/UP035: ruff khuyên dùng list[X] thay Optional/List[X].
# Dự án cố ý dùng cú pháp typing cổ điển cho khớp backend nên tắt hai rule này.
ignore = ["UP006", "UP035"]

[tool.ruff.lint.flake8-tidy-imports]
ban-relative-imports = "all"

# Chặn import sai layer — biến dependency rule thành thứ máy kiểm tra được.
[tool.ruff.lint.flake8-tidy-imports.banned-api]
"fastapi".msg = "Chỉ api/ được import FastAPI."
"langgraph".msg = "Chỉ agent/ được import LangGraph."
"langchain".msg = "Chỉ agent/ được import LangChain."
"sqlalchemy".msg = "Chỉ repository/ và infrastructure/ được import SQLAlchemy."
"httpx".msg = "Chỉ repository/ và infrastructure/ được import httpx."

[tool.ruff.lint.per-file-ignores]
"api/**" = ["TID251"]
"agent/**" = ["TID251"]
"repository/**" = ["TID251"]
"infrastructure/**" = ["TID251"]
```

Lệnh chạy: `uv run ruff check .` và `uv run ruff format .`

Lưu ý: `banned-api` chặn theo module chứ không chặn được chiều import nội bộ
(`services/` import `repository/`). Chỗ đó vẫn phải dựa vào review — hoặc thêm
`import-linter` về sau nếu thấy cần siết.

---

## 13. `__init__.py`

- Mỗi thư mục Python đều có `__init__.py` (kể cả rỗng) để tránh namespace package ngoài ý muốn.
- `__init__.py` của thư mục có API công khai thì re-export tên chính kèm `__all__`:

```python
"""Domain entities shared across ai-service."""

from core.domain.car import Car, CarStatus
from core.domain.booking import TestDriveBooking, BookingStatus

__all__ = ["Car", "CarStatus", "TestDriveBooking", "BookingStatus"]
```

- Tuyệt đối không đặt logic khởi tạo (kết nối DB, dựng client, compile graph) trong
  `__init__.py` — import phải luôn không có side effect.
- Import tuyệt đối, không import tương đối (`from core.domain.car import Car`, không phải
  `from ..domain.car import Car`). Ruff `ban-relative-imports` đã enforce.

---

## 14. Domain entity

Domain phải "thuần" theo overview, nên **dùng `@dataclass`, không dùng Pydantic ở
`core/domain/`**:

```python
"""Vehicle domain entity."""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Optional, List
from uuid import UUID


class CarStatus(str, Enum):
    """Availability status of a vehicle."""

    AVAILABLE = "available"
    OUT_OF_STOCK = "out_of_stock"


@dataclass(frozen=True)
class Car:
    """A vehicle offered in the catalog."""

    id: UUID
    name: str
    price: Decimal
    status: CarStatus
    colors: List[str]
    description: Optional[str] = None
```

- `frozen=True` mặc định. Cần đổi giá trị thì tạo bản mới bằng `dataclasses.replace`.
- Tiền dùng `Decimal`, không dùng `float`.
- Pydantic chỉ dùng ở `api/` (request/response schema) và `core/config.py`.
- Việc chuyển đổi dữ liệu ngoài → domain entity là trách nhiệm của `repository/` và
  `infrastructure/`. Domain entity không có method `from_api_response()` hay `to_dict()`
  gắn với format bên ngoài.

---

## 15. Test — quy ước & cách chạy

Claude **không tự chạy test**. Claude chỉ viết test khi được yêu cầu và mô tả cách chạy;
việc chạy và xác nhận kết quả do người thực hiện.

Cấu hình khớp backend:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

Bố cục `tests/` phản chiếu cấu trúc source: `tests/services/test_car_service.py`.
Tên test mô tả hành vi: `test_get_car_raises_when_id_not_found`.

Cách test từng layer:

| Layer | Kiểu test | Cách làm |
|---|---|---|
| `core/domain/` | Unit thuần | Gọi thẳng, không mock gì cả. Nhanh, không I/O. |
| `services/` | Unit với fake | Tự viết class fake khớp Protocol rồi truyền vào constructor. Không cần `unittest.mock` — đây là lợi ích chính của constructor injection. |
| `agent/` | Integration nhẹ | Compile graph với `MemorySaver` thay checkpointer thật, LLM thay bằng fake trả response cố định. |
| `repository/`, `infrastructure/` | Integration thật | Chạy với DB/API thật hoặc container. Đánh dấu `@pytest.mark.integration` để tách khỏi lượt chạy nhanh. |

Lệnh chạy:

```bash
uv run pytest                          # toàn bộ
uv run pytest tests/services           # một layer
uv run pytest -k "not integration"     # bỏ qua test cần hạ tầng thật
uv run pytest -s -vv                   # xem log/print khi debug
```

**Điểm cần chú ý khi tự chạy:**

1. **HITL là rủi ro lớn nhất** (overview đã cảnh báo ở Phase 2). Test luồng này phải kiểm tra
   `interrupt()` phát sinh trong subagent có propagate lên tới supervisor không, chứ không chỉ
   kiểm tra bản thân subagent. Chạy `graph.invoke()` rồi assert kết quả có `__interrupt__`,
   sau đó `graph.invoke(Command(resume=...), config)` và assert nó chạy tiếp đúng nhánh.
2. **`thread_id` phải cố định** giữa lần interrupt và lần resume — truyền cùng một
   `config={"configurable": {"thread_id": ...}}`. Sai chỗ này thì resume sẽ im lặng bắt đầu
   một luồng mới thay vì báo lỗi, rất khó nhận ra.
3. **Checkpointer trong test** dùng `MemorySaver`, không đụng vào Postgres — nhưng phải có
   ít nhất một test dùng checkpointer thật để chắc state serialize được (state chứa object
   không serialize được sẽ chỉ lộ ra ở checkpointer thật).
4. **Test có LLM thật thì tách riêng và không chạy trong lượt mặc định** — chậm, tốn tiền, và
   kết quả không ổn định. Mặc định luôn dùng fake LLM.
5. `asyncio_mode = "auto"` nghĩa là không cần `@pytest.mark.asyncio`. Nếu thấy test async bị
   skip im lặng, kiểm tra config này trước tiên.
