# `infrastructure/` — nơi duy nhất được "bẩn tay" với công nghệ cụ thể

## `infrastructure/` nghĩa là gì?

Đây là layer **implement** các `Protocol` khai báo ở `application/ports/`.
Quy tắc ngược hẳn với `application/`: layer này *được phép* — và là nơi
**duy nhất được phép** — import `httpx`, thư viện chat model provider cụ thể
(hiện là `langchain_groq`), `langgraph.checkpoint.sqlite`. Nếu sau này thấy
`httpx` được import ở bất kỳ
đâu ngoài `infrastructure/backend/client.py`, đó là dấu hiệu sai layer.

Ý nghĩa thực dụng: muốn đổi từ SQLite checkpoint sang Postgres (chắc chắn sẽ
làm ở Phase 2+, xem `docs/roadmap-ai-service.md` mục 12), hoặc đổi model/
provider chat, hoặc đổi thư viện gọi HTTP — chỉ sửa trong folder này,
`application/` và `presentation/` không biết gì đã đổi.

## `backend/client.py` — nơi duy nhất biết backend "nói chuyện" thế nào

`BackendHttpClient` implement `BackendPort`. Điểm đáng chú ý nhất — vì là một
phát hiện thực tế khi đọc code backend chứ không phải suy đoán — là backend
trả lỗi theo **2 hình dạng khác nhau** tuỳ loại lỗi:

| Nguồn lỗi backend | Hình dạng response |
|---|---|
| Raise `AppError` (và subclass: `NotFoundError`, `ForbiddenError`...) | `{"success": false, "error": {"code", "message"}}` — có handler riêng ở `backend/src/app/main.py` |
| `HTTPException` trần, lỗi validate Pydantic tự động (422) | `{"detail": ...}` — rơi vào handler mặc định của FastAPI, **không** qua envelope |

`_extract_error_message()` trong `client.py` thử đọc `error.message` trước,
không có thì fallback sang `detail` (str hoặc list lỗi validate) — nếu chỉ xử
lý 1 trong 2 dạng, một nửa số lỗi thật từ backend sẽ hiện ra message rác
"không xác định" thay vì lý do thật.

`_STATUS_TO_ERROR` map status code → đúng subclass `BackendError` — đây là
"exception translation" (mục 1, lý do #2 hợp lệ để `try/except` theo
`error-handling-logging.md`): lỗi hạ tầng bên ngoài (HTTP status) được dịch
thành lỗi domain của chính ai-service (`BackendNotFoundError`...), để phần
code phía trên không cần biết gì về HTTP status.

## `backend/schemas.py` — vì sao không tái dùng schema của `backend`

`VehicleSummarySchema` khai báo lại y hệt một phần `VehicleResponseSchema`
bên `backend`, thay vì import thẳng class Python của backend cho nhanh. Lý
do: hai service này **chỉ được giao tiếp qua HTTP** (nguyên tắc kiến trúc ở
đầu `roadmap-ai-service.md`) — import code Python của nhau sẽ biến 2 service
độc lập thành 1 monolith trá hình, và mọi thay đổi nội bộ của backend (đổi
tên field, đổi package) sẽ làm ai-service vỡ ngay lúc import chứ không phải
lúc gọi API. `extra="ignore"` trong `model_config` để field thừa (`variants`,
`colors`...) không làm parse fail — ai-service chỉ lấy đúng phần cần.

## `backend/exceptions.py` — vì sao kế thừa từ `domain.exceptions`

`BackendError(AiServiceError)` — infra được phép import `domain` (domain nằm
dưới, ai cũng được import nó), nhưng domain không bao giờ import ngược lại
infra. Nhờ `bootstrap/app_factory.py` chỉ cần biết duy nhất `AiServiceError`
để build response, mọi exception con (kể cả về sau thêm `RagUnavailableError`,
`LLMProviderError`...) tự động được xử lý đúng mà không cần sửa exception
handler.

## `llm/factory.py` — 1 chỗ duy nhất tạo chat model, và duy nhất biết provider

Nhỏ nhưng quan trọng: nếu code ở nhiều nơi tự dựng client provider riêng, đổi
model hay đổi hẳn provider cho toàn hệ thống sẽ phải grep-and-replace nhiều
file, dễ sót. Provider cụ thể (hiện là `ChatGroq`) **không** được coi là
quyết định cố định — chỉ sống ở đúng file này, đổi provider chỉ sửa 1 chỗ.
Tên model **luôn đọc từ `Settings.model_supervisor`**, không hard-code trong
factory (đúng yêu cầu "không được hard code" — xem `config.py`).

## `persistence/checkpointer.py` — vì sao là async context manager

`AsyncSqliteSaver` (từ `langgraph-checkpoint-sqlite`) cần mở kết nối và giữ
sống suốt vòng đời app — không mở/đóng mỗi request (tốn kém, và checkpoint
giữa các request phải dùng chung 1 connection để nhìn thấy nhau). Vì vậy
`build_checkpointer()` là `@asynccontextmanager`, được `async with` ngay trong
`lifespan` của `bootstrap/app_factory.py` — mở lúc app start, đóng lúc app
shutdown. Đây là lựa chọn Phase 0 (anh đã chọn SQLite thay vì `InMemorySaver`
lúc lập plan) — khi Phase 2 cần `PendingAction` sống bền hơn qua nhiều
instance/server, đây là chỗ duy nhất cần đổi sang Postgres.

## Bẫy hay gặp

- Thêm 1 lệnh gọi backend mới? Thêm method vào `BackendPort` trước
  (`application/ports/backend_port.py`), rồi mới cài đặt ở đây — không thêm
  thẳng method vào `BackendHttpClient` rồi gọi tuỳ tiện từ tool (tool chỉ
  được biết `BackendPort`, không được biết `BackendHttpClient` tồn tại).
- Đừng để kiểu dữ liệu httpx/Pydantic-của-backend "rò rỉ" lên trên — luôn trả
  về DTO (`application/dto/`) hoặc raise đúng `BackendError` subclass.
