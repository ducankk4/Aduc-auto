# ai-service — Code style & convention

Quy ước bắt buộc cho toàn bộ `ai-service/`. Áp dụng cho cả 6 phase trong
[ai_service_architecture_overview.md](../../docs/ai_service_architecture_overview.md).

Nguyên tắc nền: **ai-service tự đặt chuẩn cho chính nó.** Mọi luật dưới đây phải đứng vững bằng
lý do kỹ thuật của riêng nó — layered architecture, dependency rule, hay ràng buộc của LangGraph.
Không luật nào tồn tại chỉ vì "chỗ khác đang làm thế". Thấy một luật mà lý do duy nhất là sự
nhất quán với code nằm ngoài `ai-service/`, đó là luật cần xem lại chứ không phải luật cần theo.

Nguyên tắc nền thứ hai: **tài liệu này chứa luật, không chứa hiện trạng.** Cây thư mục, danh sách
file, bản sao của `pyproject.toml` — tất cả đều mốc sau vài lần refactor và ép phải sync tay ở
nhiều chỗ. Hiện trạng đọc thẳng từ repo. Ở đây chỉ có thứ đủ ổn định để một luật mới suy ra
được chỗ đặt cho file chưa tồn tại.

---

## 1. Môi trường & tooling

| Hạng mục | Quy định |
|---|---|
| Python | 3.11 — pin ở `.python-version` |
| Package manager | `uv` — mọi dependency khai báo trong `pyproject.toml`, commit `uv.lock` |
| Build backend | `hatchling` |
| Lint + format | `ruff` (xem mục 12) |
| Logging | `loguru` |
| Config | `pydantic-settings` |

Không dùng `black`, `isort`, `flake8` riêng lẻ — `ruff` đã lo cả ba.

---

## 2. Đặt code ở đâu

Không có bảng "thứ này để thư mục kia" ở đây (lý do: nguyên tắc nền thứ hai ở đầu file). Thay vào
đó là ba câu hỏi, trả lời theo thứ tự.

### 2.1 Layer nào? — hỏi "phụ thuộc vào cái gì", không hỏi "tên gọi là gì"

| Bản chất file | Layer |
|---|---|
| Mô tả nghiệp vụ, không import gì ngoài stdlib | domain |
| Là contract (`ABC`), method đánh dấu `@abstractmethod` | interface |
| Điều phối use case, chỉ chạm thế giới ngoài qua contract ở `core/interface/` | service |
| Nói chuyện thật với thế giới ngoài (HTTP, DB, LLM, vector store), kế thừa contract nó implement | implementation |
| Chỉ tồn tại vì LangGraph/LangChain: graph, node, state, tool, prompt, checkpointer | agent |
| Cửa vào HTTP: app, lifespan, router, schema, wiring | api |
| Hạ tầng dùng chung toàn app, độc nhất, không thuộc framework nào | file phẳng ở `core/` |

Phân loại theo **thứ nó phụ thuộc vào**, không theo cái tên nghe giống thư mục nào. Một file chỉ
tồn tại vì một framework thì thuộc về layer sở hữu framework đó, kể cả khi nghe rất "hạ tầng
dùng chung" — checkpointer LangGraph là của `agent/`, không phải của `core/`.

Dấu hiệu máy kiểm được cho việc đặt sai chỗ: **phải đục thêm một ngoại lệ trong `banned-api` /
`per-file-ignores` thì file mới lint sạch.** Ngoại lệ đó chính là lint đang nói file nằm nhầm
layer — sửa chỗ đặt, đừng sửa cấu hình lint.

### 2.2 File phẳng hay thư mục? — đếm theo lộ trình, không theo hiện tại

- Loại artifact mà cả vòng đời app chỉ có **đúng một** thành viên (config, logger, exception
  hierarchy) → file phẳng.
- Loại mà lộ trình 6 phase chắc chắn đẻ thêm thành viên (agent, tool, prompt, state, feature của
  API) → **thư mục ngay từ thành viên đầu tiên**, dù hiện tại mới có một file.

Không chờ tới file thứ hai mới tách. Đổi từ file phẳng sang thư mục là đổi đường import của mọi
nơi đang gọi, cộng một lần cập nhật tài liệu; tạo sẵn thư mục thì tốn đúng một `__init__.py`.
Ba file `supervisor.py` + `tools.py` + `prompts.py` nằm phẳng cạnh nhau trông gọn ở Phase 1 và
thành đống hỗn độn ngay khi Phase 2 thêm subagent đầu tiên.

### 2.3 Đặt vào thư mục đó thế nào?

- Các thư mục song song cùng mô tả một feature thì dùng **cùng tên module** (`routes/chat.py` ↔
  `schemas/chat.py`) — nhìn tên là biết cặp, không cần mở file.
- Thêm vào feature **đã có** → viết tiếp vào module sẵn có, không đẻ file mới.
- Thêm feature **mới** → tạo module cùng tên ở mọi thư mục song song liên quan, rồi import thẳng
  từ module đó ở nơi cần (không có lớp re-export — xem mục 13).
- Thứ thuộc về một feature không bao giờ nằm ở gốc layer; hạ tầng dùng chung của layer không bao
  giờ nằm trong thư mục chia theo feature.
- **Contract gom theo nhóm, không mỗi ABC một file**: mọi repository contract chung một module
  (`core/interface/repository.py`), retriever/LLM tương tự theo nhóm của nó. Thêm contract mới
  cùng nhóm → viết vào file sẵn có. Contract là thứ ít và ổn định — rừng file 15 dòng khó đọc
  hơn một file 100 dòng.
- **Implementation chia theo entity trước, backend sau** khi có từ hai thành viên trở lên
  (`repository/car/http.py`, `repository/booking/http.py`) — nhìn cây là thấy entity nào đổi
  backend nào được. Một implementation duy nhất thì file phẳng (`repository/car_repository.py`)
  là đủ; tách khi thành viên thứ hai xuất hiện, trong cùng thay đổi thêm nó.

### 2.4 Dependency rule — chiều import hợp lệ

```
api/  ──►  services/, agent/  ──►  core/domain/, core/interface/
                                          ▲
                    repository/, infrastructure/  ──┘  (kế thừa contract)
```

Cụ thể, những import sau là **sai** và sẽ bị ruff chặn (mục 12):

- `core/domain/` import bất cứ thứ gì ngoài stdlib và `core/domain/` khác.
- `services/` hoặc `agent/` import trực tiếp từ `repository/` hay `infrastructure/`
  (phải đi qua contract ở `core/interface/`).
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
| Contract (ABC) | `I<Danh từ>` | `ICarRepository`, `IRetriever` |
| Repository impl | `<Danh từ>Repository` | `CarRepository`, `BookingRepository` |
| Service (use case) | `<Danh từ>Service` | `CarService`, `ComparisonService` |
| API schema (DTO) | `<Danh từ>Request` / `<Danh từ>Response` | `ChatRequest`, `ChatResponse` |
| Exception | `<Lý do>Error` | `CarNotFoundError`, `ApprovalRejectedError` |
| LangGraph state | `<Phạm vi>State` | `SupervisorState`, `ComparisonState` |

**Tên class theo khái niệm nó mô tả, không theo tên module chứa nó.** Module là chỗ để nhóm, không
phải tiền tố phải mang theo: trong `domain/knowledge.py`, khái niệm cần tên là `Chunk` và
`MetadataChunk` chứ không phải `KnowledgeChunk` — đường dẫn import đã nói "knowledge" một lần rồi,
nhắc lại trong tên class chỉ làm dài mà không thêm thông tin. Ngoại lệ: tên trần quá chung đến mức
trùng với khái niệm khác trong cùng service thì mới thêm định ngữ để phân biệt.

### Hàm

- Public: `snake_case`, bắt đầu bằng động từ — `get_car`, `build_comparison_card`.
- Private (chỉ dùng trong module/class): prefix `_` — `_normalize_spec`.
- Repository dùng tiền tố `find_` cho truy vấn có thể không ra kết quả (trả `Optional`),
  `get_` cho truy vấn bắt buộc có (raise nếu không thấy). Nhìn tên hàm là biết ngay phía gọi
  có phải xử lý `None` hay không, không cần mở implementation ra đọc.
- Factory dựng graph: `build_<tên>_graph()` — `build_supervisor_graph()`.

### Hằng số

`UPPER_SNAKE_CASE`, đặt trong `constants.py` của thư mục tương ứng hoặc cạnh nơi dùng nếu
chỉ dùng một chỗ. Không hardcode magic number/string rải rác trong logic.

---

## 4. Type hint

**Dùng cú pháp `typing` cổ điển:**

```python
from typing import Optional, List, Dict, Tuple, Any
```

| Dùng | Không dùng |
|---|---|
| `Optional[str]` | `str \| None` |
| `List[Car]` | `list[Car]` |
| `Dict[str, Any]` | `dict[str, Any]` |
| `Tuple[List[Car], int]` | `tuple[list[Car], int]` |

Đây là lựa chọn nội tại của ai-service, không phải để khớp với codebase nào khác: **một cú pháp
duy nhất trong toàn service**, không trộn hai kiểu giữa các file hay trong cùng một file. Ruff
enforce bằng cách tắt `UP006`/`UP035` (mục 12). Muốn đổi sang `list[X]` / `X | None` thì đổi ở
một chỗ đó rồi sửa toàn bộ trong một lần, không đổi lẻ tẻ theo từng file mới.

Mọi hàm public **bắt buộc** có type hint đầy đủ cho tham số và giá trị trả về. Hàm không trả
gì thì ghi rõ `-> None`.

---

## 5. Docstring

Google style, **viết bằng tiếng Anh**, có type trong ngoặc.

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

## 6. Dependency injection & contract (ABC)

ai-service dùng **instance + constructor injection**, không dùng class toàn `@staticmethod`.
Contract định nghĩa bằng `abc.ABC` + `@abstractmethod` — implementation phải **kế thừa tường
minh**, Python tự chặn instantiate nếu thiếu method. Đây cũng là thứ khiến `services/` test
được bằng fake tự viết, không cần mock: fake chỉ cần kế thừa cùng ABC và implement đủ method.

Quy trình chuẩn cho mọi dependency vượt qua ranh giới layer:

**Bước 1 — Định nghĩa contract ở `core/interface/`:**

```python
from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID

from core.domain.car import Car


class ICarRepository(ABC):
    """Contract any vehicle data source must satisfy."""

    @abstractmethod
    async def find_by_id(self, car_id: UUID) -> Optional[Car]:
        """Return the vehicle matching the given id, or None if absent."""
        ...

    @abstractmethod
    async def find_many(self, car_ids: List[UUID]) -> List[Car]:
        """Return all vehicles matching the given ids, skipping missing ones."""
        ...
```

**Bước 2 — Service nhận contract, không biết implementation:**

```python
class CarService:
    """Use cases for vehicle lookup."""

    def __init__(self, car_repository: ICarRepository) -> None:
        self._car_repository = car_repository

    async def get_car(self, car_id: UUID) -> Car:
        """..."""
        car = await self._car_repository.find_by_id(car_id)
        if car is None:
            raise CarNotFoundError(f"Không tìm thấy xe với id: {car_id}")
        return car
```

**Bước 3 — Implementation ở `repository/`, kế thừa tường minh contract nó thỏa:**

```python
class CarRepository(ICarRepository):
    """Vehicle data access backed by the catalog HTTP API."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def find_by_id(self, car_id: UUID) -> Optional[Car]:
        """..."""
```

Thiếu implement một `@abstractmethod` thì `CarRepository(...)` raise `TypeError` ngay lúc
khởi tạo — bắt lỗi sớm hơn Protocol (Protocol chỉ báo qua static type checker, không raise
runtime).

**Bước 4 — Nối dây (wiring) chỉ xảy ra ở `api/`.** Đây là nơi duy nhất được biết cả contract
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

Exception của ai-service **tuyệt đối không dính tới FastAPI** — `core/`, `services/`, `agent/`
bị cấm import FastAPI, nên mọi hierarchy kế thừa `HTTPException` đều dùng không được.

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
- Message hướng tới người dùng cuối viết **tiếng Việt** (người dùng cuối là khách Việt).
  Message chỉ để debug viết tiếng Anh.
- Chỉ `api/` được map exception sang HTTP status. Map ở một exception handler tập trung,
  không rải `try/except` dịch lỗi trong từng router.
- `repository/` và `infrastructure/` bắt lỗi thư viện (httpx, asyncpg, LLM SDK) rồi bọc lại
  thành `InfrastructureError` — không để lỗi thư viện rò lên `services/`.
- Không `except Exception: pass`. Nếu thật sự cần nuốt lỗi thì phải log kèm lý do.

---

## 8. Logging

Dùng `loguru`, cấu hình một lần ở `core/logger.py` — kể cả phần intercept stdlib logging, để log
của uvicorn và thư viện bên thứ ba cùng chảy qua một sink duy nhất.

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

## 9. Config

`core/config.py`, dùng `pydantic-settings`. Mọi giá trị cấu hình là field của `Settings` —
thấy chuỗi `http://`, đường dẫn, tên model, hay magic number nằm rải trong logic là sai style.
Nhưng field **có default hay không** thì chia theo hậu quả khi cấu hình sai:

```python
class Settings(BaseSettings):
    """Settings loaded from environment variables or .env file."""

    # Bắt buộc từ .env — thiếu là fail lúc khởi động (chủ đích, không phải thiếu sót)
    GROQ_API_KEY: str
    QDRANT_URL: str
    EMBEDDING_MODEL: str

    # Tunable — default chạy được ngay, .env chỉ ghi đè khi cần
    LLM_TEMPERATURE: float = 0.0
    RAG_TOP_K: int = 4
```

- **Bắt buộc, không default**: secret/API key, URL/endpoint, tên model, và mọi giá trị **gắn
  với dữ liệu đã ingest** (`EMBEDDING_MODEL`, `QDRANT_COLLECTION`...). Nhóm này cấu hình sai
  thì hoặc lộ secret, hoặc gọi nhầm môi trường, hoặc vỡ âm thầm kiểu bẫy "đổi model quên
  ingest lại" — default ở đây là giấu bom. Fail-fast lúc khởi động rẻ hơn debug lúc chạy.
- **Được default trong `Settings`**: tunable thuần (timeout, temperature, chunk size, top_k)
  và đường dẫn local. Nhóm này sai thì chỉ lệch chất lượng/hiệu năng, dễ thấy dễ chỉnh —
  bắt khai đủ 30 dòng `.env` mới chạy được là phức tạp hóa không đổi lấy an toàn nào.
- Default chỉ sống ở `Settings`, không rải trong logic — đổi vẫn đúng một chỗ.
- Field `UPPER_SNAKE_CASE`, nhóm theo comment.
- Không đọc `os.environ` ở bất kỳ đâu khác ngoài file này.
- Không commit `.env`. `.env.example` liệt kê **đủ 100% key** (kể cả key có default — ghi đúng
  giá trị default để làm tài liệu) — một chỗ duy nhất xem được toàn bộ cấu hình.
- Thêm field mới vào `Settings` mà quên thêm vào `.env.example` là một bug.

---

## 10. Async

Toàn bộ I/O là `async`. Cụ thể:

- Mọi method của repository, infrastructure client, service có I/O đều `async def`.
- Node của LangGraph viết `async def` kể cả khi hiện tại chưa await gì — tránh phải đổi
  chữ ký về sau khi thêm I/O.
- Không gọi hàm blocking trong async context. Nếu buộc phải dùng thư viện sync, bọc bằng
  `asyncio.to_thread`.
- Hàm thuần túy không I/O thì để `def` thường, không `async` cho có.

---

## 11. Quy ước riêng cho LangGraph / LangChain

Chỉ áp dụng trong `agent/`.

**State schema** — mỗi phạm vi graph (supervisor, từng subagent) một state riêng, một module riêng;
dùng `TypedDict` với `Annotated` reducer:

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

**Tool** — mỗi nhóm tool (theo miền nghiệp vụ, không theo agent tiêu thụ nó) một module riêng
trong thư mục tool của agent:

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

**Prompt** — hằng số `UPPER_SNAKE_CASE` trong module prompt riêng của từng phạm vi, không nhúng
chuỗi prompt dài giữa logic.

---

## 12. Lint

Lệnh chạy: `uv run ruff check .` và `uv run ruff format .`

Cấu hình thật nằm ở `ai-service/pyproject.toml` — **đó là nguồn sự thật duy nhất, tài liệu này
không chép lại nó**. Phần cần hiểu để không sửa bừa:

- `UP006`/`UP035` tắt **có chủ đích** để giữ cú pháp typing ở mục 4. Thấy ruff gợi ý `list[X]`
  thì đó là rule đã tắt bị bật lại, không phải style mới.
- `ban-relative-imports = "all"` — enforce mục 13.
- `banned-api` + `per-file-ignores` là bản dịch máy-kiểm-được của dependency rule (mục 2.4): mỗi
  thư viện framework khai báo đúng những layer được phép chạm vào, layer khác import là lint đỏ.
- Thêm thư viện vượt ranh giới layer → sửa `banned-api` và `per-file-ignores` **trong cùng một
  lần**, và giữ chúng nói giống nhau. Message ghi "chỉ `agent/`" mà `per-file-ignores` lại mở
  thêm cho một file ở `core/` là mâu thuẫn — đọc lại mục 2.1 trước khi thêm ngoại lệ đó.

Giới hạn đã biết: `banned-api` chặn theo tên thư viện bên thứ ba, **không** chặn được chiều import
nội bộ (`services/` import `repository/`). Chỗ đó vẫn dựa vào review, hoặc thêm `import-linter`
nếu thấy cần siết.

---

## 13. Import & package

- **Không dùng `__init__.py`.** ai-service chạy trực tiếp từ thư mục gốc (`package = false`),
  Python 3.11 import namespace package bình thường, nên file rỗng chỉ để "đánh dấu package" là
  nhiễu. Đổi lại: **không có lớp re-export** — mọi import trỏ thẳng tới module định nghĩa
  (`from core.domain.car import Car`), một tên chỉ có đúng một đường import, không tồn tại hai
  đường vào cùng một thứ.
- Import tuyệt đối, không import tương đối (`from core.domain.car import Car`, không phải
  `from ..domain.car import Car`). Ruff `ban-relative-imports` đã enforce.
- Import phải luôn không có side effect: tuyệt đối không đặt logic khởi tạo (kết nối DB, dựng
  client, compile graph) ở module level. Dựng bằng hàm `build_*()` để phía gọi quyết định thời điểm.

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

### Tách concept cho đủ

Một khái niệm nghiệp vụ hiếm khi là đúng một class. Trước khi gom mọi field vào một dataclass cho
nhanh, soi từng nhóm field bằng ba câu hỏi — dính câu nào thì tách ra thành type riêng:

1. **Sinh ra ở thời điểm khác nhau?** Metadata của một mẩu kiến thức cố định từ lúc ingest;
   `similarity_score` chỉ tồn tại sau một lần truy vấn. Hai vòng đời khác nhau → hai type khác
   nhau, không nhồi chung.
2. **Đi cùng nhau ở nhiều nơi khác nhau?** Cùng một nhóm field lặp lại ở nhiều entity là một value
   object đang trốn — đặt tên cho nó rồi tái sử dụng.
3. **`Optional` vì "lúc có lúc không" chứ không phải "được phép trống"?** Field chỉ có nghĩa
   trong một số trường hợp là dấu hiệu hai khái niệm đang bị ép vào một class.

Ví dụ chuẩn là `core/domain/knowledge.py`: `MetadataChunk` (định danh nguồn, cố định từ ingest),
`Chunk` (nội dung + metadata), `VectorSearchResult` (một `Chunk` kèm điểm số của lần tìm này) —
ba khái niệm, ba vòng đời, ba type. Một class `KnowledgeChunk` phẳng gom cả ba thì lúc ingest phải
để `similarity_score = None`, và câu hỏi "field này có nghĩa gì ở đây" không có câu trả lời.

Chiều ngược lại cũng là lỗi: **không tách khi chưa có lý do.** Các mảnh luôn sinh cùng lúc, luôn
đi cùng nhau và chưa ai dùng lẻ thì để yên — một wrapper bọc đúng một field là chi phí đọc chứ
không phải kiến trúc. Tiêu chí là *đầy đủ và hợp lý*, không phải *nhiều tầng*.

---

## 15. Test — quy ước & cách chạy

Claude **không tự chạy test**. Claude chỉ viết test khi được yêu cầu và mô tả cách chạy;
việc chạy và xác nhận kết quả do người thực hiện.

Cấu hình:

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
| `services/` | Unit với fake | Tự viết class fake kế thừa cùng ABC rồi truyền vào constructor. Không cần `unittest.mock` — đây là lợi ích chính của constructor injection. |
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
