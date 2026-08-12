# `ai_service/` — tổng quan package (đọc file này trước, rồi vào từng layer)

Đây là file tổng hợp, nối các file `README.md` trong từng layer
(`domain/`, `application/`, `infrastructure/`, `presentation/`, `bootstrap/`)
thành một bức tranh chung: **một request đi qua hệ thống theo đường nào**.
Muốn hiểu sâu 1 layer cụ thể, đọc README của layer đó — file này chỉ nối các
điểm lại với nhau.

Bối cảnh/quyết định kiến trúc đầy đủ: `docs/roadmap-ai-service.md`. Quy ước
code, error handling: `.claude/CLAUDE.md` và `.claude/rules/`.

## Bản đồ thư mục

```text
config.py            Settings — mọi giá trị đọc từ .env, không hard-code gì
domain/               khái niệm nghiệp vụ thuần, không phụ thuộc công nghệ
application/           use case + agent orchestration, biết domain + ports
infrastructure/        implement ports, nơi duy nhất "bẩn tay" httpx/LangChain
presentation/           biên HTTP: route, schema validate, auth decode
bootstrap/              composition root: ráp toàn bộ object graph 1 lần
```

Quy tắc phụ thuộc (bắt buộc, xem thêm `.claude/CLAUDE.md`):

```text
presentation → application → domain
infrastructure → application.ports + domain   (implement, không bị import ngược)
bootstrap → biết và nối tất cả các layer trên
```

## Đường đi của 1 request thật: `POST /api/v1/chat`

Ví dụ: client gửi `{"session_id": null, "message": "Cho tôi xem vài mẫu xe"}`,
không kèm token. Theo đúng thứ tự file/hàm được gọi:

1. **`presentation/api/chat.py::post_chat`** nhận request.
   - `Depends(get_auth_context)` (`presentation/dependencies.py`) → không có
     Bearer token → trả `AuthContext.anonymous()`.
   - `ChatRequestSchema` (`presentation/schemas/chat.py`) validate body — nếu
     `message` rỗng hoặc thừa field lạ, FastAPI tự trả 422 ở đây, code Python
     của mình còn chưa kịp chạy.
   - `Depends(get_container)` đọc `request.app.state.container` — object đã
     được ráp sẵn từ lúc app khởi động (`bootstrap/app_factory.py`), không
     tạo mới gì ở bước này.
2. Gọi **`application/use_cases/chat_use_case.py::ChatUseCase.send_message(None, message, auth)`**
   (trên `container.chat_use_case`, instance đã cầm sẵn `graph` qua constructor).
   - Vì `session_id=None` → sinh `uuid4()` mới làm `thread_id`.
   - Build `context = {"auth_token": None}` (kiểu `AgentContext`) — kênh
     runtime-only, không bị lưu xuống checkpoint.
   - Gọi `graph.ainvoke({"messages": [...]}, config=..., context=...)`.
3. Bên trong `graph` (được `application/orchestration/supervisor.py::build_supervisor`
   dựng sẵn 1 lần lúc `bootstrap/container.py::build_container` chạy):
   - LangGraph tự **load lại state cũ** từ `AsyncSqliteSaver`
     (`infrastructure/persistence/checkpointer.py`) theo `thread_id` — lần
     đầu tiên với session mới thì state rỗng.
   - Chat model (dựng bởi `infrastructure/llm/factory.py`, hiện là `ChatGroq`)
     đọc
     system prompt (`application/orchestration/prompts/supervisor_prompt.py`)
     + lịch sử + câu hỏi mới → quyết định gọi tool `list_vehicles`.
   - **`application/tools/catalog_tools.py::list_vehicles`** chạy: gọi
     `backend_port.list_vehicles(page, limit)` — tham số `backend_port` chính
     là `BackendHttpClient` đã được inject từ lúc build container.
   - **`infrastructure/backend/client.py::BackendHttpClient.list_vehicles`**
     gọi thật `GET {BACKEND_BASE_URL}/catalog/vehicles` qua httpx.
     - Thành công → parse JSON thành `VehicleSummaryDTO` list, trả lên.
     - Thất bại (backend down, 404, 422...) → raise đúng subclass
       `BackendError` (`infrastructure/backend/exceptions.py`).
   - Tool **bắt** các `BackendError` đó, **không** để bay lên phá graph —
     trả về 1 chuỗi text (`"Danh sách xe:\n- ..."` hoặc `"Error: ..."`).
   - Model đọc tool result, sinh câu trả lời cuối bằng tiếng Việt (theo chỉ
     dẫn cuối system prompt).
   - LangGraph tự **lưu state mới** (toàn bộ message list, gồm cả tool
     call/tool result) xuống `AsyncSqliteSaver` theo `thread_id` — nhưng
     **không lưu `context`** (token) vì đó là runtime-only, đây chính là cơ
     chế giữ bất biến "token không lọt vào checkpoint".
4. `send_message` lấy `AIMessage` cuối cùng trong `result["messages"]`, đóng
   gói thành `ChatResultDTO(session_id, reply)` — dataclass thuần, không dính
   gì tới LangChain nữa từ đây trở lên.
5. `post_chat` bọc DTO vào `presentation/envelope.py::success(data=...)`,
   trả về `{"success": true, "data": {"session_id", "reply", "pending_action": null}}`.

Lần chat thứ 2 với **cùng `session_id`**: y hệt luồng trên, chỉ khác ở bước 3
— checkpointer load được state cũ (câu hỏi + câu trả lời + cả tool call
trước đó), nên model "nhớ" ngữ cảnh mà không cần gọi lại tool nếu câu hỏi mới
chỉ tham chiếu tới thông tin đã có.

### Khi có lỗi thật sự (không phải lỗi backend mà tool đã bắt được)

Ví dụ `GROQ_API_KEY` sai/hết hạn → SDK provider raise exception ngay
lúc model gọi API — exception này **không** đi qua đường "tool bắt lỗi" ở
bước 3 (vì nó không phải lỗi từ `backend_port`), nó bay thẳng lên qua
`send_message` → `post_chat` → không route nào bắt riêng → rơi vào
catch-all `Exception` handler ở `bootstrap/app_factory.py` → client nhận
`500 {"success": false, "error": {"code": "INTERNAL_ERROR", ...}}`, và log
server có đầy đủ traceback để debug. Đây là lý do tại sao catch-all bắt buộc
phải tồn tại (xem `bootstrap/README.md`).

## Trạng thái hiện tại (Phase 0)

Chỉ có 1 tool đọc (`list_vehicles`), supervisor không có subagent, chưa có
RAG/PendingAction/HITL. Xem `docs/roadmap-ai-service.md` mục 11 cho lộ trình
đầy đủ Phase 1-6, và mục 9 cho các khoảng trống bên `backend` cần biết trước
khi làm phase sau.
