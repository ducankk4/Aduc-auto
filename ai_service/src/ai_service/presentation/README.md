# `presentation/` — biên HTTP, nơi duy nhất (cùng `bootstrap/`) được biết FastAPI

## `presentation/` nghĩa là gì?

Đây là tầng ngoài cùng — nơi request HTTP đi vào và response HTTP đi ra. Route
handler ở đây **cố tình rất mỏng**: validate input (nhờ Pydantic schema) →
gọi đúng 1 use case ở `application/` → bọc kết quả vào envelope. Không có
logic gì khác. Nếu thấy route handler dài hơn ~10 dòng thân hàm, thường là
dấu hiệu logic đang bị đặt sai chỗ (nên nằm ở use case).

## `dependencies.py::get_auth_context` — decode JWT nhưng không verify

Điểm dễ gây hiểu lầm nhất trong toàn bộ codebase, nên nhắc lại rõ ở đây:
`_decode_unverified_claims()` tự tay base64url-decode phần payload của JWT
(`token.split(".")[1]`) bằng thư viện chuẩn (`base64`, `json`) — **không**
dùng thư viện JWT nào để verify chữ ký. Đây là chủ đích, không phải thiếu sót:
- ai-service không giữ `SECRET_KEY` của backend, nên **không thể** verify chữ
  ký thật kể cả khi muốn.
- Giá trị đọc ra (`role`, `permissions`) chỉ dùng để quyết định UI (ẩn/hiện
  subagent), không bao giờ dùng để cấp quyền — nên "ai đó giả mạo token để
  đọc sai role" không tạo ra lỗ hổng bảo mật thật (họ vẫn bị backend chặn khi
  gọi API thật, vì backend mới verify chữ ký).
- Token decode lỗi (`ValueError`/`JSONDecodeError`) → trả `{}` thay vì raise,
  vì hậu quả tệ nhất là "ẩn nhầm 1 subagent", không đáng làm cả request fail.

## `envelope.py::success()` — vì sao mirror response của `backend`

FE (frontend) gọi cả `backend` lẫn `ai-service`. Nếu 2 service trả JSON khác
hình dạng, FE phải viết 2 bộ code parse response. `success(data, meta)` cố
tình dựng dict y hệt `backend/src/app/core/response.py::success()` —
`{"success": true, "data": ..., "meta": ...}` (bỏ hẳn key `meta` nếu `None`,
không phải `null`). **Response lỗi lại không được build ở đây** — nó tập
trung một chỗ duy nhất ở `bootstrap/app_factory.py` (xem file đó, mục "vì sao
tập trung"), route handler chỉ raise exception rồi thôi.

## `schemas/chat.py` — biên validate thật sự của hệ thống

Đây là nơi duy nhất trong ai-service **bắt buộc phải validate chặt**
(`extra="forbid"`, `min_length`/`max_length` trên `message`) — vì đây là dữ
liệu đến từ client, không tin tưởng được. Bên trong `application/`, dữ liệu
đã qua biên này rồi nên không validate lại (dùng dataclass thuần ở `dto/`) —
tránh validate 2 lần cùng một dữ liệu ở 2 layer khác nhau.

## `api/chat.py` — vì sao lấy `container` qua `Depends(get_container)`

`get_container(request: Request)` đọc `request.app.state.container` — container
được build **một lần duy nhất** lúc app khởi động (ở `bootstrap/app_factory.py`
lifespan), route handler không tự tạo `BackendHttpClient` hay tự build graph
mỗi request (vừa chậm — mở kết nối HTTP/DB mới mỗi lần — vừa phá vỡ việc
checkpointer cần giữ chung 1 connection). Đây là kiểu dependency injection
đơn giản nhất có thể trong FastAPI: không cần container framework (như
`dependency-injector`), chỉ cần "build 1 lần, treo vào `app.state`, đọc lại
qua Depends".

`post_chat_stream` trả `StreamingResponse` với `media_type="text/event-stream"`
— mỗi dòng SSE có prefix bắt buộc `data: ` và kết thúc bằng `\n\n` (chuẩn
SSE, không phải quy ước riêng của ai-service) — thiếu 1 trong 2 thứ đó,
trình duyệt/EventSource sẽ không parse được stream.

## Bẫy hay gặp

- Route handler gọi thẳng `BackendHttpClient`/`graph.ainvoke` thay vì qua
  `application/use_cases/`? Sai — presentation không được nhảy cóc qua
  application để chạm infra/orchestration trực tiếp.
- Muốn trả lỗi tuỳ biến ngay trong route bằng `HTTPException` hay tự build
  `JSONResponse`? Đừng — raise đúng subclass của `AiServiceError`
  (`ConversationNotFoundError`, `BackendNotFoundError`...), để
  `bootstrap/app_factory.py` xử lý tập trung, tránh mỗi route tự dựng response
  lỗi một kiểu khác nhau.
