# `domain/` — tầng nghiệp vụ lõi của ai-service

## `domain/` nghĩa là gì trong kiến trúc Layered?

Đây là tầng **không phụ thuộc vào bất kỳ công nghệ nào** — không FastAPI, không
LangChain/LangGraph, không httpx. Lý do: domain diễn tả "khái niệm nghiệp vụ"
(AuthContext là ai, một lượt hội thoại trông ra sao, lỗi nào thuộc loại nào) —
những khái niệm này phải sống được dù mai sau đổi từ FastAPI sang framework
khác, đổi LangGraph sang thư viện agent khác. Nếu domain import `fastapi` hay
`langchain`, nghĩa là khái niệm nghiệp vụ đang bị trói vào một công cụ cụ thể —
đó là dấu hiệu sai layer (xem `code-style.md` mục 6, `application/tools/` chỉ
được "chuyển đổi input/output rồi gọi port", không tính toán nghiệp vụ ở đây).

Trong kiến trúc 4 tầng của ai-service (`presentation → application → domain`,
`infrastructure` implement `application/ports`), domain nằm **ở đáy** — mọi
tầng khác được phép biết domain, nhưng domain không được biết ai đang dùng nó.

## Có gì trong folder này (Phase 0)

### `actor.py` — `AuthContext`
Đại diện cho "người đang chat là ai", dựng từ Bearer token gửi lên request.

Điểm quan trọng nhất — **và dễ hiểu nhầm nhất** — là `AuthContext` **không**
dùng để quyết định quyền hạn. Nó chỉ để:
1. Forward `token` xuống backend khi gọi API (backend mới là nơi verify chữ ký
   JWT và check permission thật sự — xem bất biến #3 trong `CLAUDE.md`).
2. Đọc `role`/`permissions` (đã decode nhưng **không verify chữ ký**) chỉ để
   quyết định UI hiện/ẩn subagent nào (vd: từ Phase 5, user không phải admin
   sẽ không thấy `admin_agent` trong danh sách agent có thể dùng) — đây gọi là
   "defense in depth ở UX", không phải bảo mật thật. Backend vẫn luôn là nơi
   chặn thật nếu ai đó cố tình sửa token giả mạo role=admin.

`AuthContext.anonymous()` là factory cho case không có token (khách vãng lai) —
dùng thay vì tạo `AuthContext(None, False, None, [])` thủ công ở khắp nơi.

### `exceptions.py` — `AiServiceError` + `ConversationNotFoundError`
Đây là **gốc của toàn bộ cây exception** trong ai-service (kể cả
`BackendError` ở `infrastructure/backend/exceptions.py` cũng kế thừa từ
`AiServiceError`, xem file đó). Mỗi exception mang theo:
- `code`: chuỗi ổn định để client/FE code theo (vd `"CONVERSATION_NOT_FOUND"`),
  không parse message tiếng Việt để rẽ nhánh logic.
- `status_code`: HTTP status tương ứng — được `bootstrap/app_factory.py` đọc
  ra để build response, xem mục "Vì sao tách code khỏi status_code" bên dưới.

Vì sao base class kế thừa `Exception` chứ không phải `BaseException`: nếu kế
thừa `BaseException`, pattern rất phổ biến `except Exception:` ở nơi khác
trong code sẽ **không bắt được** exception này — gây crash khó hiểu ở chỗ
tưởng đã có try/except bọc rồi (xem `error-handling-logging.md` mục 3.1).

## Vì sao Phase 0 domain "mỏng" (không có method, chỉ có field)?

Đây là câu hỏi anh đã hỏi hôm trước — ghi lại ở đây luôn để nhớ lý do: domain
giàu behavior (có method, tự validate invariant) chỉ đáng làm khi **có quy tắc
nghiệp vụ thật cần bảo vệ**. `AuthContext` ở Phase 0 chỉ đi qua hệ thống
chứ chưa bị ràng buộc gì đặc biệt. Khi tới Phase 2 làm `PendingAction` (có TTL,
có `payload_hash`, có cờ `consumed`), đó mới là lúc domain cần method thật sự,
vd `is_expired() -> bool`, `matches_payload(new_hash: str) -> bool` — lúc đó
class sẽ "dày" lên tự nhiên vì có invariant cần giữ, không phải vì "domain thì
phải dày".

## Bẫy hay gặp khi sửa/thêm code ở đây

- Thêm field mới vào `AuthContext`? Được, miễn là kiểu dữ liệu thuần
  Python (`str`, `list`, dataclass khác) — **không** import Pydantic/LangChain
  vào đây dù rất tiện (Pydantic cho validate free). Validate thuộc về
  `presentation/schemas/`.
- Thêm exception mới? Luôn kế thừa `AiServiceError` (hoặc một subclass có sẵn
  như `BackendError`), luôn set `code` + `status_code` riêng — đừng dùng
  `ValueError`/`KeyError` để biểu diễn lỗi nghiệp vụ (dễ nhầm với bug lập
  trình thật khi debug, xem `error-handling-logging.md` mục 3.2).
