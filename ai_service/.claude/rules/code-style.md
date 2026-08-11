# Code Style — ai-service

Áp dụng cho toàn bộ `src/ai_service/`. Mục tiêu: nhất quán với style của `backend` (cùng hệ sinh thái FastAPI + Pydantic + async) ở những chỗ hợp lý, đồng thời khớp với đặc thù của một service điều phối multi-agent (nhiều I/O ra ngoài: backend API, LLM, vector store).

---

## 1. Runtime & tooling

- Python **3.11+**, toàn bộ code I/O (gọi backend, gọi LLM, gọi vector store, đọc/ghi checkpoint) phải là `async def`. Không dùng thư viện HTTP đồng bộ (`requests`) — dùng `httpx.AsyncClient`.
- Quản lý dependency bằng `uv` (đã có `uv.lock`), không dùng `pip install` trực tiếp.
- Format & lint bằng `ruff` (thêm vào `pyproject.toml` khi setup CI — chưa có ở thời điểm viết rule này). Line length 100. Import order: stdlib → third-party → `ai_service.*`, không import wildcard (`from x import *`).
- Type hint bắt buộc trên mọi function signature công khai (public API của mỗi layer: port, tool, use_case, route handler). Cho phép bỏ qua ở hàm nội bộ rất ngắn, hiển nhiên từ tên biến.

## 2. Naming convention

| Đối tượng | Quy ước | Ví dụ |
|---|---|---|
| Pydantic DTO (request/response) | `...Schema` | `ChatRequestSchema`, `VehicleSummarySchema` |
| Port (interface tầng application) | `...Port`, định nghĩa bằng `Protocol` hoặc `ABC` | `BackendPort`, `RetrieverPort`, `ConversationPort` |
| Implementation của port ở infrastructure | `...Client` / `...Adapter` / `...Repository` | `BackendHttpClient`, `PgVectorRetriever` |
| Domain exception | `...Error`, kế thừa từ base exception của ai-service (không kế thừa `BaseException`) | `PendingActionExpiredError`, `BackendUnavailableError` |
| Agent tool (hàm dùng làm LangChain tool) | verb-first, snake_case, đúng nghĩa vụ nghiệp vụ chứ không đúng tên endpoint | `get_vehicle_detail`, `create_order_draft` — không đặt `call_orders_post_api` |
| Module | snake_case, mỗi module có `__init__.py` re-export những gì layer trên cần dùng | |

## 3. Cấu trúc một agent tool

Mỗi tool là một hàm mỏng: nhận input đã được LangChain parse theo schema, gọi đúng 1 port, trả output đã format cho model đọc. Không đặt logic nghiệp vụ, không tự retry ngầm im lặng (retry nếu cần thì làm ở tầng `infrastructure` client, không phải trong tool).

```python
async def get_vehicle_detail(slug: str) -> str:
    """Get full detail of a single vehicle by slug, including variants and colors.

    Use when the user asks about the price, configuration, or specs of ONE
    specific vehicle whose slug is already known. Do not use this to search or
    list multiple vehicles — use `list_vehicles` for that.

    Args:
        slug: URL slug identifying the vehicle, e.g. "vf8-2026".

    Returns:
        Formatted text describing the vehicle (name, price, variants, colors)
        ready for the model to read. Returns a Vietnamese-language error
        message if the vehicle is not found — that message is user-facing
        conversation content, not code, so it follows the product's chat
        language, not this docstring's language.
    """
    ...
```

Docstring của tool **là một phần của prompt** (LangChain lấy docstring làm `description` truyền cho model) — vẫn viết **bằng tiếng Anh** như mọi docstring/comment khác trong code (xem mục 8), nêu rõ: dùng khi nào, KHÔNG dùng khi nào nếu dễ nhầm với tool khác. Model đọc hiểu tiếng Anh tốt và điều này giữ toàn bộ codebase nhất quán một ngôn ngữ. Tiếng Việt chỉ xuất hiện trong **giá trị trả về** khi giá trị đó là nội dung hội thoại thật sự hiển thị cho người dùng cuối (message lỗi, câu trả lời) — không xuất hiện trong docstring, comment, hay tên định danh. Không nhồi ví dụ hội thoại giả vào docstring — nếu cần dạy hành vi phức tạp, đưa vào system prompt của subagent (system prompt cũng viết tiếng Anh; phần hướng dẫn model trả lời bằng tiếng Việt là một câu trong đó, không phải lý do viết cả prompt bằng tiếng Việt).

## 4. Pydantic (schema tầng presentation & dto)

- Dùng Pydantic v2 API: `model_config = ConfigDict(...)`, không dùng cú pháp v1 (`class Config`).
- Validate chặt ở `presentation/schemas/` (đây là biên hệ thống — request từ client). Bên trong `application/`, truyền dữ liệu qua `dto/` thuần Python (dataclass hoặc Pydantic tuỳ, không bắt buộc validate lại).
- Không tái sử dụng schema của backend. Nếu cần hình dạng dữ liệu giống backend (vd. `OrderResponseSchema`), định nghĩa DTO riêng trong `application/dto/` hoặc `infrastructure/backend/schemas.py` — ai-service không import code Python của `backend`.

## 5. Async, LangGraph node & use_case

- `application/use_cases/`: mỗi use case là một async function nhận DTO, trả DTO — không cần bọc class nếu không giữ state giữa các lần gọi. Chỉ dùng class khi cần giữ dependency đã inject qua constructor (khi đó constructor chỉ nhận port, không tự khởi tạo infrastructure bên trong).
- LangGraph node (trong `application/orchestration/`) là async function thuần, nhận `state` đã typed, trả partial state update — không side-effect ngoài việc gọi port.
- Không block event loop: không gọi thư viện sync (DB driver sync, `time.sleep`) trong code chạy trong graph.

## 6. Ports (Protocol) và Infrastructure

- Định nghĩa port bằng `typing.Protocol` trong `application/ports/`, chỉ khai báo method signature + docstring mô tả hợp đồng (contract), không chứa implementation.
- `infrastructure/` implement đúng port đó, không thêm method public ngoài port (nếu cần method thêm, thêm vào port trước).
- `BackendHttpClient` (infrastructure/backend/) là nơi **duy nhất** biết `BACKEND_BASE_URL`, cấu trúc response `{success, data, meta, error}` của backend, và cách forward Bearer token. Không nơi nào khác trong `application/` được tự gọi `httpx` trực tiếp.

## 7. Testing

- `pytest` + `pytest-asyncio`, đặt song song `unit/` (mock port, test use_case/tool logic) và `integration/` (test thật với backend chạy ở môi trường test — dùng cho contract test theo mục 13 roadmap).
- Mock ở biên port (`BackendPort`, `RetrieverPort`), không mock sâu vào `httpx.AsyncClient` — giữ test độc lập với implementation.
- Không mock response của LLM bằng chuỗi tự viết tay cho test hành vi agent phức tạp — dùng fixture ghi lại (cassette) hoặc test ở mức tool/use_case thay vì test full graph khi có thể.

## 8. Docstring & comment — luôn tiếng Anh

- **Mọi docstring và comment trong code, không ngoại lệ, viết bằng tiếng Anh** — kể cả docstring của agent tool (mục 3), kể cả comment giải thích inline. Đây là quy tắc cứng, không phải khuyến nghị.
- Theo style Google (Args/Returns/Raises) cho method public của `application/ports/`, `application/use_cases/`, `infrastructure/*Client`, `presentation/api/`, và `application/tools/` — đồng bộ với style hiện có ở `backend`.
- Module-level docstring 1-2 câu ở đầu file mô tả trách nhiệm của file, giống style `backend` (`"""Business Logic & Service Interface for the X Module."""`).
- Tiếng Việt **chỉ** được phép xuất hiện trong: (a) giá trị chuỗi là nội dung hội thoại/response thật sự trả cho người dùng cuối (message lỗi hiển thị, câu trả lời của agent), và (b) tài liệu markdown dạng prose ở `docs/`, `.claude/`. Không viết trong tên biến/hàm/class, docstring, comment, hay log message.
