# Nguyên tắc xử lý lỗi (try/except) và Logging — ai-service

Tài liệu này mô tả nguyên tắc chung khi viết exception handling và logging trong `ai-service`, áp dụng cho mọi layer của kiến trúc (`presentation`, `application` gồm use_case/orchestration/tools, `infrastructure`, `domain`). Mục tiêu: bắt lỗi hiệu quả, log dễ tra cứu khi debug production, tránh log trùng lặp, tránh che giấu bug thật — và riêng với agent, tránh làm graph "chết cứng" vì một lỗi tool lẽ ra model có thể tự sửa.

Bản gốc của file này copy từ một dự án khác; đã chỉnh lại bảng phân tầng và bổ sung mục 5 cho khớp kiến trúc Layered + Multi-agent của `ai-service` (xem `docs/roadmap-ai-service.md`). Toàn bộ code trong các ví dụ dưới đây — tên exception, comment, log message — viết bằng tiếng Anh, theo đúng quy tắc ở `code-style.md` mục 8; phần diễn giải bằng tiếng Việt trong file này chỉ là prose hướng dẫn, không phải nội dung sẽ được gõ vào code.

---

## 1. Triết lý cốt lõi

> Chỉ `catch` một exception khi trả lời được **có**, cho một trong 4 câu hỏi sau. Nếu không, để exception tự bay lên tầng trên.

| # | Lý do hợp lệ để catch | Ví dụ |
|---|---|---|
| 1 | **Retry / fallback** | Gọi API ngoài timeout → thử lại 1 lần, hoặc dùng cache cũ |
| 2 | **Dịch loại lỗi (exception translation)** | Lỗi thư viện hạ tầng (`sqlite3.OperationalError`, driver Qdrant...) → lỗi domain của app (`RepositoryUnavailableError`) |
| 3 | **Thêm ngữ cảnh rồi ném tiếp** | Biết thêm "đang xử lý document nào" mà tầng dưới không biết → gắn context, `raise ... from e` |
| 4 | **Đang ở biên hệ thống (boundary)** | Route/controller: bắt buộc phải biến exception thành HTTP response, message queue response, hay exit code |

Nếu một đoạn `try/except` không phục vụ 1 trong 4 mục đích trên — nó là "catch cho chắc", nên bỏ. Catch dư thừa là nguyên nhân chính của log trùng lặp, mất traceback, và che giấu bug thật (biến `TypeError` do lỗi lập trình thành "lỗi hệ thống chung chung").

---

## 2. Trách nhiệm theo từng layer (map với cấu trúc `src/ai_service/`)

| Layer | Có nên `try/except` rộng? | Vai trò |
|---|---|---|
| **`infrastructure/`** (`backend/*Client`, `rag/*`, `persistence/*`, `llm/*`) | Có — nhưng chỉ catch **exception cụ thể** của thư viện đang dùng (`httpx.HTTPStatusError`, `httpx.TimeoutException`, lỗi driver vector store, lỗi SDK chat model provider) | Dịch lỗi hạ tầng → domain exception của ai-service. Đây là nơi **duy nhất** biết `httpx`, driver DB, SDK LLM tồn tại — không để các exception đó rò rỉ lên `application/` |
| **`application/ports/`** (Protocol) | Không — port không có implementation, không có gì để catch | Chỉ khai báo contract |
| **`application/tools/`** | Có, nhưng theo quy tắc riêng ở mục 5 — không giống các layer khác | Bọc lỗi từ port thành `tool_result` lỗi cho model, thay vì để exception phá graph |
| **`application/use_cases/`, `application/orchestration/`** | Hầu như không | Nơi chứa logic điều phối hội thoại/agent — càng ít try/except càng dễ đọc luồng chính. Chỉ catch khi có ý nghĩa nghiệp vụ thật (vd: hết `PendingAction` TTL thì tạo lại), không catch "cho chắc" |
| **`domain/`** (`Conversation`, `PendingAction`, `AuthContext`) | Không bao giờ | Domain object không biết gì về HTTP, LangGraph, hay logging |
| **`presentation/api/`** (route `/chat`, `/chat/confirm`...) | **Có — đây là nơi chính, bắt buộc** | Nơi duy nhất catch-all để tránh sập process, map exception → response `{success:false, error:{code,message}}` giống format của `backend` |

Nguyên tắc chung: **exception nên bị catch ít nhất có thể ở giữa luồng xử lý, và bắt buộc phải bị catch ở đầu (biên vào) hoặc cuối (biên ra) của hệ thống.** Riêng `application/tools/` có một biên "ra" khác nữa — biên giữa code Python và model — xem mục 5.

---

## 3. Thiết kế exception hierarchy

### 3.1 Quy tắc bắt buộc
- Custom exception **luôn kế thừa từ `Exception`**, không bao giờ từ `BaseException` (vì `except Exception` — pattern phổ biến nhất — sẽ không bắt được `BaseException`, gây crash khó hiểu ở nơi không ngờ tới).
- Xây một cây phân cấp lỗi riêng cho `ai-service`, chia theo **nguồn gốc lỗi**, không phải theo tên nghiệp vụ tùy hứng:
  - **Lỗi do client / input sai** (map sang HTTP 4xx): `ValidationError`, `PendingActionNotFoundError`, `PendingActionExpiredError`, `PendingActionPayloadChangedError`...
  - **Lỗi do gọi `backend` thất bại** — nhóm riêng, bọc trong `BackendHttpClient` (xem mục 3.3): `BackendNotFoundError` (404), `BackendValidationError` (400/422), `BackendUnauthorizedError` (401 — token hết hạn/không hợp lệ), `BackendForbiddenError` (403 — thiếu permission), `BackendUnavailableError` (timeout/5xx/network).
  - **Lỗi hạ tầng khác** (RAG, LLM, persistence — map sang HTTP 5xx, đáng alert): `RetrieverUnavailableError`, `LLMProviderError`, `CheckpointStoreError`...
- Mỗi exception nên mang theo:
  - Một `code` ổn định (dùng để client/FE xử lý theo logic, không parse message tiếng Việt/Anh tự do).
  - Một `context` (dict) chứa thông tin phục vụ debug (id liên quan, tham số đầu vào đã sanitize — **không** chứa JWT, xem mục 4.5).

### 3.2 Nguyên tắc đặt tên & phạm vi
- Đặt tên theo **loại lỗi**, không theo tầng phát sinh (vd: `ConversationNotFoundError` chứ không phải `SqliteConversationError`) — vì domain không nên biết implementation đang là Postgres hay Redis.
- Không tái sử dụng builtin exception (`ValueError`, `KeyError`...) để biểu diễn lỗi nghiệp vụ — dễ nhầm với bug lập trình thật khi debug.
- `BackendNotFoundError`/`BackendValidationError`... luôn giữ nguyên `message` gốc từ response `{success:false, error:{code,message}}` của `backend` (thường là tiếng Việt) làm nội dung hiển thị — không tự diễn giải lại. Đây là nơi duy nhất chuyển response HTTP của `backend` thành exception; phía trên (`application/tools/`) không tự parse `httpx.Response`.

### 3.3 Xử lý tập trung tại boundary
- Ở tầng API, map exception → response tại **một chỗ tập trung** (exception handler / middleware), không lặp lại `try/except` + build response thủ công trong từng route/controller.
- Chỉ cần map theo họ lỗi cha (`AppError`) và các lỗi con quan trọng cần response riêng (`NotFoundError` → 404), phần còn lại fallback về lỗi hệ thống chung (500).

---

## 4. Nguyên tắc logging

### 4.1 Log một lỗi đúng một lần
- **Không** log ở mọi tầng mà exception đi qua. Một lỗi đi qua 4 tầng mà tầng nào cũng `log.error()` thì log production sẽ có 4 dòng trùng nội dung, gây nhiễu khi tra cứu.
- Chọn một chiến lược nhất quán trong toàn dự án — khuyến nghị: **log tại boundary** (route/exception handler), các tầng dưới chỉ `raise` (hoặc `raise ... from e` để giữ traceback gốc). Boundary luôn có đủ ngữ cảnh (request, user, endpoint) để log đầy đủ một lần.
- Ngoại lệ: log ở tầng dưới **chỉ khi** tầng đó có thông tin quan trọng sẽ mất nếu không log ngay (vd: đã catch để retry, muốn ghi lại số lần đã thử) — trường hợp này log ở mức `WARNING`, không phải `ERROR`, vì hệ thống chưa thực sự fail.

### 4.2 Luôn giữ traceback
- Dùng hàm log có đính kèm stack trace đầy đủ trong khối `except` (không chỉ ghi `str(e)`), vì `str(e)` chỉ có message, mất hoàn toàn thông tin dòng/file gây lỗi — rất khó debug production nếu thiếu.
- Khi ném lại lỗi đã dịch loại, luôn giữ liên kết với exception gốc (`raise NewError(...) from e`), không ném lỗi mới "trần trụi" làm mất traceback chain.

### 4.3 Log có cấu trúc (structured), không phải câu văn tự do
- Log nên đính kèm các field có thể lọc/query được: `request_id`, `user_id`, `conversation_id`, tên operation... thay vì nhồi hết vào một câu string.
- `request_id`/`trace_id` nên được gắn **một lần** ở middleware đầu request, sau đó mọi log trong request đó tự động kế thừa — không phải truyền tay qua từng hàm.
- Structured log cho phép filter theo field trong hệ thống log tập trung (Loki/Datadog/CloudWatch...); log dạng câu văn tự do chỉ full-text search được, rất chậm và dễ sót khi debug ở quy mô lớn.

### 4.4 Log level phải nhất quán, có ý nghĩa lọc được
| Level | Khi dùng |
|---|---|
| `DEBUG` | Chi tiết kỹ thuật, chỉ bật khi debug local/staging |
| `INFO` | Mốc nghiệp vụ quan trọng (vd: "user tạo document thành công") — không log mọi bước nội bộ nhỏ lẻ |
| `WARNING` | Có vấn đề nhưng hệ thống tự phục hồi được (fallback dùng được, retry thành công) |
| `ERROR` | Một request/operation thất bại thật sự, cần người xem log biết — nhưng hệ thống vẫn sống |
| `CRITICAL` | Nguy cơ sập hệ thống / mất dữ liệu, cần alert ngay |

Nếu mọi thứ đều log ở cùng 1-2 level, log level mất tác dụng lọc — production log sẽ quá ồn để tìm ra vấn đề thật.

### 4.5 Không log dữ liệu nhạy cảm
- Không log token, password, thông tin định danh cá nhân đầy đủ. Nếu cần phục vụ debug, log ID tham chiếu hoặc dữ liệu đã mask (vd: `email: a***@gmail.com`).
- Không log Bearer JWT của user dưới bất kỳ hình thức nào (kể cả log ở mức `DEBUG`) — token pass-through xuống `backend` chỉ sống trong request scope, không đi vào log hay `context` của exception (xem nguyên tắc bất biến #7 ở `CLAUDE.md`).

### 4.6 Log message viết bằng tiếng Anh, dùng `loguru`
- Dự án dùng `loguru` (giống `backend`) — `from loguru import logger`. Chuỗi message truyền vào `logger.info(...)`/`logger.error(...)` là code, nên viết **tiếng Anh** (theo `code-style.md` mục 8), không viết tiếng Việt như log tự do.
- Gắn field có cấu trúc bằng `logger.bind(...)`, không nhồi vào f-string:

```python
# Sai — không structured, không tiếng Anh
logger.error(f"Không gọi được backend cho conversation {conversation_id}: {err}")

# Đúng
logger.bind(conversation_id=str(conversation_id), operation="backend_call").error(
    "Failed to call backend: {}", err
)
```

---

## 5. Xử lý lỗi trong tool-calling (`application/tools/`)

Đây là quy tắc **khác hẳn** các layer thông thường, vì `application/tools/` có 2 biên cùng lúc: biên kỹ thuật bình thường (port trả lỗi) và biên "giao tiếp với model" (tool phải trả về được thứ model đọc và tự sửa được).

### 5.1 Không để exception từ tool phá graph
Khi một tool gọi port (thường là `BackendPort`) và port raise domain exception (`BackendNotFoundError`, `BackendValidationError`...), tool **không** để exception đó bay lên LangGraph runtime chưa qua xử lý. Một exception chưa bắt ở node tool sẽ làm graph dừng giữa chừng, mất toàn bộ context hội thoại đã tích luỹ — trải nghiệm tệ hơn nhiều so với việc model biết lỗi và tự đề xuất bước tiếp theo.

Thay vào đó, tool bắt đúng những exception mà nó biết cách nói cho model nghe, và trả về một **kết quả lỗi dạng text** (tool result với `is_error=True` — theo cơ chế `ToolMessage`/`is_error` chuẩn của LangChain) thay vì raise:

```python
async def create_order_draft(variant_id: str, color_id: str, ...) -> str:
    """Build a deposit order draft for confirmation. Does not create the order —
    see the pending-action confirmation flow before this tool's result is acted on.
    """
    try:
        preview = await backend_port.preview_order(variant_id, color_id, ...)
    except BackendNotFoundError as err:
        # The model can recover from this: ask the user to re-select variant/color.
        return f"Error: {err.message}"
    except BackendUnavailableError as err:
        logger.bind(variant_id=variant_id, operation="create_order_draft").warning(
            "Backend unavailable while previewing order: {}", err
        )
        return "Error: the ordering system is temporarily unavailable, please try again shortly."
    return format_order_preview(preview)
```

### 5.2 Quy tắc phân loại lỗi tool
- **Lỗi mà model có cơ hội tự sửa** (input sai, không tìm thấy resource, thiếu thông tin) → trả về text lỗi rõ ràng, đúng nguyên nhân, để model đổi chiến lược hoặc hỏi lại người dùng. Không che giấu, không trả "đã xảy ra lỗi" chung chung.
- **Lỗi hạ tầng thật sự** (backend down, timeout, LLM provider lỗi) → log ở mức `WARNING`/`ERROR` (theo mục 4.4) **rồi mới** trả text lỗi ngắn gọn cho model — đây là ngoại lệ hợp lệ của nguyên tắc "log tại boundary" (mục 4.1), vì tool là boundary thật sự với model.
- **Không** catch `Exception` trần trong tool để "cho chắc chắn graph không chết" — chỉ catch đúng những exception type mà `BackendPort`/port khác đã định nghĩa (mục 3). Một lỗi lập trình thật (`AttributeError`, `KeyError` do bug) vẫn phải bay lên và làm request fail rõ ràng, không được nuốt thành "Error: đã có lỗi xảy ra".

### 5.3 Tool ghi dữ liệu không tự raise khi thiếu xác nhận
Tool tương ứng với thao tác ghi (`create_order`, `admin_update_order_status`...) không tự gọi port ghi ngay trong một lượt gọi tool — nó tạo `PendingAction` (xem nguyên tắc bất biến #4) và trả về bản tóm tắt cho model trình bày, chờ endpoint `/chat/confirm` gọi port thật. Việc thực thi thật ở use case xử lý confirm mới áp dụng đầy đủ mục 2–4 như một layer bình thường (không còn là biên với model nữa).

---

## 6. Các anti-pattern cần tránh

1. **Catch rồi nuốt lỗi âm thầm, trả về giá trị rỗng/mặc định** — chỉ chấp nhận khi đó là quyết định nghiệp vụ có chủ đích và được ghi chú rõ lý do; nếu không, nó che giấu lỗi hạ tầng thật dưới vỏ bọc "không có kết quả".
2. **`try/except` bọc cả một hàm dài** — nên bọc phạm vi nhỏ nhất cần thiết, để biết chính xác dòng nào gây lỗi và không vô tình nuốt luôn lỗi của logic không liên quan tới lý do catch.
3. **Catch `Exception` chung chung ở tầng business logic "cho chắc"** — dễ nuốt luôn cả lỗi lập trình thật (`TypeError`, `KeyError` do bug), khiến bug bị che thành "lỗi hệ thống chung chung" và khó phát hiện qua test.
4. **Dùng try/except để xử lý control-flow bình thường** (vd: check tồn tại bằng try/except thay vì kiểm tra điều kiện trước) — chậm hơn, khó đọc hơn, và dễ bắt nhầm lỗi khác không liên quan.
5. **Log rồi raise ở mọi tầng exception đi qua** — gây log trùng lặp, khó biết đâu là log gốc khi tra cứu.
6. **Custom exception kế thừa `BaseException`** — phá vỡ giả định `except Exception` ở nơi khác trong code.
7. **Route/controller tự build response lỗi thủ công lặp lại ở từng endpoint** — nên xử lý tập trung qua exception handler.
8. **Tool để exception bay thẳng lên LangGraph runtime thay vì trả `tool_result` lỗi** (mục 5.1) — làm graph dừng giữa chừng, mất context hội thoại.
9. **Tool ghi dữ liệu tự gọi port ghi mà không qua `PendingAction`** (mục 5.3) — vi phạm nguyên tắc bất biến #4, không phải lỗi logging nhưng cùng nhóm "catch cho chắc rồi làm liều".
10. **Log message viết tiếng Việt hoặc nhồi biến trực tiếp vào f-string thay vì `logger.bind(...)`** (mục 4.6).

---

## 7. Checklist khi review code

- [ ] Đoạn `try/except` này phục vụ 1 trong 4 lý do hợp lệ (retry / dịch lỗi / thêm context / boundary)? Nếu không → bỏ.
- [ ] Exception tự định nghĩa có kế thừa `Exception` (không phải `BaseException`) và có `code` để map response không?
- [ ] Lỗi này có bị log nhiều hơn 1 lần khi đi qua các tầng không?
- [ ] Khối `except` có giữ traceback đầy đủ (không chỉ `str(e)`) không?
- [ ] Log có gắn `request_id`/context liên quan để tra cứu theo request không, và message có viết bằng tiếng Anh không?
- [ ] Log level có đúng ý nghĩa (INFO cho mốc nghiệp vụ, ERROR cho thất bại thật) không?
- [ ] Log/exception `context` có vô tình chứa JWT hoặc dữ liệu nhạy cảm không?
- [ ] `infrastructure/` có để lỗi của thư viện ngoài (httpx, driver DB, SDK LLM...) rò rỉ lên `application/` không?
- [ ] Route có tự catch/build response lỗi thủ công thay vì dùng exception handler tập trung không?
- [ ] Tool trong `application/tools/` có raise exception thẳng thay vì trả `tool_result` lỗi cho model không (mục 5)?
- [ ] Tool ghi dữ liệu có đi qua `PendingAction` thay vì gọi thẳng port ghi không (mục 5.3)?
