# `bootstrap/` — Composition Root: nơi duy nhất biết TẤT CẢ các layer cùng lúc

## `bootstrap/` nghĩa là gì?

Mọi layer khác chỉ được biết layer "dưới" mình (`presentation` biết
`application`, `application` biết `domain` + `ports`, `infrastructure` biết
`domain` + implement `ports`). Câu hỏi tự nhiên: vậy **ai** là người thật sự
tạo ra `BackendHttpClient` rồi nhét nó vào nơi cần dùng? Câu trả lời là
`bootstrap/` — layer duy nhất được phép import và "quen mặt" mọi thứ: FastAPI,
httpx, LangChain, các concrete class ở `infrastructure/`. Pattern này gọi là
**Composition Root** — toàn bộ object graph của app được ráp ở đúng 1 chỗ,
lúc khởi động, một lần duy nhất.

## `container.py::AppContainer` / `build_container()`

`build_container()` làm đúng theo thứ tự: tạo `BackendHttpClient` (infra) →
tạo chat model qua `build_chat_model` (infra — hiện đang là `ChatGroq`, xem
`infrastructure/README.md` về vì sao chọn provider nào là quyết định riêng
của tầng này) → tạo tool list qua
`build_catalog_tools(backend_client)` (application, nhận infra làm tham số
— đây chính là dependency injection) → build `graph` qua `build_supervisor`
(application). Kết quả đóng gói vào `AppContainer` — một dataclass "túi đựng"
mọi thứ đã ráp xong, không có logic gì trong chính nó.

## `app_factory.py::create_app()` — 4 việc

1. **Đọc `Settings()`** — nếu thiếu biến môi trường bắt buộc trong `.env`,
   app sẽ crash ngay ở bước này (cố ý — thà crash lúc khởi động còn hơn chạy
   với config sai âm thầm, vì `config.py` không có default hard-code nào).
2. **`lifespan`** — mở `AsyncSqliteSaver` (qua `build_checkpointer`), build
   `container`, gắn vào `app.state.container`; lúc shutdown thì đóng
   `backend_client` (đóng kết nối httpx). Đây là lý do `lifespan` tồn tại
   thay vì code chạy thẳng ở module level: tài nguyên async (kết nối DB, HTTP
   client) cần async context để mở/đóng đúng cách, và FastAPI chỉ cho làm
   việc đó trong `lifespan`.
3. **Exception handler tập trung** — đây là điểm khác biệt rõ nhất so với
   `backend` (backend hiện chỉ bắt `AppError`, không có catch-all — đã ghi
   nhận là một gap khi đọc code backend). `error-handling-logging.md` mục 2
   yêu cầu `presentation/` **bắt buộc** phải có catch-all để tránh process
   sập khi có lỗi lập trình chưa lường trước (`AttributeError`, `KeyError`
   do bug thật) — ai-service tự làm đúng quy tắc riêng của nó ngay từ Phase 0
   thay vì để dành "sau này thêm".
   - `AiServiceError` → đọc đúng `code`/`status_code` của từng exception, log
     `ERROR` một lần duy nhất tại đây (không log lại ở tầng dưới nữa — xem
     `error-handling-logging.md` mục 4.1 "log tại boundary").
   - `Exception` trần (bug thật) → log kèm traceback đầy đủ (`logger.exception`),
     trả 500 generic, **không** để lộ chi tiết lỗi thật cho client.
4. **Đăng ký router** — `chat_router` gắn prefix `/api/v1`, `health_router`
   thì không (mirror đúng cách `backend/src/app/main.py` để `/health` ngoài
   prefix — dùng cho healthcheck của hạ tầng, thường không muốn version hoá).

## Vì sao `Settings()` được gọi bên trong `create_app()`, không phải ở module level

Nếu `settings = Settings()` nằm ở top-level của `app_factory.py`, nó sẽ chạy
ngay lúc file được **import** — kể cả khi chỉ import để test hoặc để đọc
type, không thật sự chạy app. Đặt trong `create_app()` nghĩa là nó chỉ chạy
khi ai đó **thật sự gọi hàm** để tạo app — tách biệt "import module" khỏi
"khởi tạo side-effect", một nguyên tắc chung nên áp dụng bất cứ đâu có
side-effect lúc import (đọc file, đọc env, mở kết nối).

## Bẫy hay gặp

- Muốn build thêm 1 service/client mới (vd RAG retriever ở Phase 1)? Thêm
  bước build vào `container.py`, đừng build rải rác ở nơi dùng nó — giữ đúng
  nguyên tắc "1 chỗ duy nhất ráp toàn bộ object graph".
- `CORSMiddleware` đang để `allow_origins=["*"]` — đúng là cấu hình dev, đã
  ghi nhận trong roadmap (mục 9.10) là cần siết lại trước khi lên staging,
  không phải quên.
