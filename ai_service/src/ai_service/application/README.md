# `application/` — tầng orchestration (use case + agent)

## `application/` nghĩa là gì?

Đây là tầng "biết cách phối hợp" — nó biết `domain` (import thoải mái) và biết
**hợp đồng** (`ports/`) mà `infrastructure` phải tuân theo, nhưng **không được
import `infrastructure` trực tiếp** (xem `code-style.md` mục 6). Đây chính là
Dependency Inversion Principle bằng code: `application` định nghĩa nó *cần*
gì (`BackendPort.list_vehicles(...)`), còn `infrastructure/backend/client.py`
mới là nơi *thực hiện* bằng httpx thật. Nhờ vậy test `application/` chỉ cần
mock đúng cái Protocol, không cần biết httpx tồn tại (xem `tests/unit/`).

Layer này được phép import LangChain/LangGraph — khác với `domain` (không
được). Vì "cách điều phối hội thoại" (agent, tool, graph) là **cơ chế**, không
phải "khái niệm nghiệp vụ vĩnh viễn" như domain — nếu mai sau đổi hẳn từ
LangGraph sang framework agent khác, chỉ tầng này bị ảnh hưởng.

## `dto/` — 3 tầng "hình dạng dữ liệu" khác nhau, đừng nhầm

Dự án có **3 chỗ định nghĩa lại cùng một khái niệm "xe"**, cố tình không dùng
chung 1 class:
1. `infrastructure/backend/schemas.py::VehicleSummarySchema` — mirror đúng
   response JSON của backend (Pydantic, để `model_validate` parse JSON).
2. `application/dto/vehicle.py::VehicleSummaryDTO` — dataclass thuần, dùng để
   truyền dữ liệu **giữa các layer trong ai-service** sau khi đã parse xong.
3. (Không có domain riêng cho "xe" ở Phase 0 vì ai-service không sở hữu khái
   niệm nghiệp vụ "xe" — backend mới là chủ, ai-service chỉ mượn tạm).

Vì sao tách 1 và 2 dù nhìn giống hệt nhau: nếu backend đổi tên field JSON
(vd `base_price` → `list_price`), chỉ `infrastructure/backend/schemas.py` sửa
— `VehicleSummaryDTO` và mọi chỗ dùng nó (tool, use case) không suy suyển.
Đây là lý do tồn tại của Anti-Corruption Layer: cách ly thay đổi bên ngoài.

`dto/chat.py::ChatResultDTO` cũng vậy — là "hình dạng" `send_message` trả về,
tách khỏi `presentation/schemas/chat.py::ChatRequestSchema` (schema request
từ client) và tách khỏi dict thô mà route handler build ra cho `envelope.py`.

## `ports/backend_port.py` — hợp đồng, không phải implementation

`BackendPort` là `typing.Protocol` — chỉ khai báo chữ ký hàm + docstring mô tả
sẽ raise gì, **không có 1 dòng code thực thi nào**. Đọc file này để biết
"ai-service cần gì từ backend" mà không cần quan tâm httpx được cấu hình ra
sao. Khi Phase 1+ cần thêm `get_vehicle_detail`, thêm method vào đây trước,
rồi mới cài đặt ở `infrastructure/backend/client.py`.

## `tools/catalog_tools.py` — vì sao là factory function, không phải hàm trần

`build_catalog_tools(backend_port)` trả về list tool thay vì viết
`list_vehicles` như một hàm module-level cố định, vì tool cần "cầm" một
`backend_port` cụ thể (được inject lúc `bootstrap/container.py` chạy) — đây
là dependency injection kiểu closure, không cần framework DI riêng.

Quy tắc bắt buộc (xem `error-handling-logging.md` mục 5): tool **không bao
giờ để exception bay lên phá graph**. Nó bắt đúng exception biết cách nói cho
model nghe (`BackendUnavailableError`, `BackendError`) và trả về **chuỗi text**
bắt đầu bằng `"Error: ..."` — model đọc chuỗi này và tự quyết định phải làm gì
tiếp (báo user, thử lại, hỏi lại) thay vì cả request bị crash 500.

Docstring của tool **là một phần prompt thật sự** gửi cho Claude (LangChain
lấy docstring làm mô tả tool) — nên viết tiếng Anh, nêu rõ "dùng khi nào /
KHÔNG dùng khi nào" để model không gọi nhầm tool khi có nhiều tool cùng lúc
(sẽ rõ hơn từ Phase 1 khi có thêm `get_vehicle_detail`, `rag_search`...).

## `orchestration/` — nơi dựng "bộ não" của agent

- `context.py::AgentContext` — kênh truyền dữ liệu **runtime-only** vào graph
  (khác với `state`, thứ bị checkpointer ghi xuống đĩa). Đây là cơ chế giữ
  đúng bất biến #7 (JWT không được lọt vào checkpoint) — token đi qua
  `context=`, không đi qua `state["messages"]`.
- `prompts/supervisor_prompt.py` — system prompt tách riêng file (không nhúng
  thẳng trong `supervisor.py`) để dễ version/diff riêng khi prompt thay đổi
  nhiều lần trong quá trình tune — một file Python code hiếm khi đổi, một file
  prompt thì đổi liên tục, tách ra tránh diff noise.
- `supervisor.py::build_supervisor` — gọi `create_agent(...)` của LangChain
  1.3.14, truyền `tools`, `checkpointer`, `context_schema` vào. Phase 0 chưa
  có subagent — supervisor tự cầm tool đọc luôn. Từ Phase 1, khi có
  `catalog_advisor` v.v., LangChain **không có sẵn** hàm "biến 1 agent thành
  tool cho agent khác" (đã tự xác minh trong `.venv`, không phải giả định) —
  sẽ phải tự viết một `@tool` wrapper gọi `subagent_graph.ainvoke(...)`.

## `use_cases/` — mỗi hàm là một "động từ nghiệp vụ", không giữ state

`send_message`, `stream_message`, `get_history` — mỗi hàm nhận input đã
validate (từ `presentation/`), build `config`/`context` cho graph, gọi đúng
1 thao tác trên `graph` (`ainvoke`/`astream`/`aget_state`), rồi map kết quả
sang DTO/domain object. **Không có business logic thật ở đây** — chúng chỉ
điều phối, đúng nghĩa "use case" trong Clean Architecture: một kịch bản, một
lần chạy, không giữ state giữa các lần gọi (khác với route handler ở
`presentation/api/chat.py` — nơi đó cũng mỏng, chỉ gọi use case rồi bọc
envelope).

## Bẫy hay gặp

- Thấy mình đang cộng giá, so sánh trạng thái đơn, hay validate business rule
  trong `tools/` hoặc `use_cases/`? Dừng lại — logic đó thuộc về `backend`,
  gọi API chứ đừng tự tính (nguyên tắc bất biến #2 trong `CLAUDE.md`).
- Muốn gọi `httpx` hay `ChatAnthropic()` trực tiếp trong layer này để "tiện"?
  Không — phải qua port/factory ở `infrastructure/`, nếu không sẽ phá vỡ khả
  năng test bằng fake port.
