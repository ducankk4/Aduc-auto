# ai-service — Hướng dẫn cho Claude Code

`ai-service` là chatbot AI cho hệ thống đặt cọc xe Aduc Auto, chạy **độc lập** với `backend` (FastAPI Modular Monolith), giao tiếp với nhau **chỉ qua HTTP**. Kiến trúc: Layered Architecture ở khung ngoài, Multi-agent (Deep Agent kiểu supervisor + subagent trên LangGraph) ở lõi Application.

Kế hoạch đầy đủ (scope, tool catalog, RBAC, RAG, lộ trình phase, khoảng trống backend cần xử lý): đọc `docs/roadmap-ai-service.md` trước khi làm bất kỳ việc gì liên quan tới thiết kế. Đừng lặp lại nội dung file đó ở đây.

## Quy tắc bất biến — không được vi phạm

1. **Không kết nối DB nghiệp vụ của backend.** ai-service chỉ có DB riêng cho conversation/checkpoint/vector store.
2. **Không chứa business logic nghiệp vụ xe** (tính giá, tính tiền cọc, validate state machine đơn). Nếu thấy mình đang làm việc đó trong `application/tools/` — đó là dấu hiệu sai layer, chuyển yêu cầu đó sang gọi backend.
3. **Không tự làm RBAC.** ai-service forward nguyên JWT của user xuống backend; quyết định cho phép luôn do `check_permission()` của backend. ai-service chỉ decode token (không cần verify chữ ký) để ẩn/hiện subagent cho gọn UX.
4. **Mọi tool có ghi dữ liệu (create/update/delete) phải qua `PendingAction` + xác nhận người dùng.** Không bao giờ gọi thẳng API ghi từ trong 1 lượt suy luận của agent.
5. **RAG chỉ chứa nội dung tĩnh** (mô tả dài, FAQ, chính sách). Giá, tồn kho, trạng thái đơn luôn lấy từ API backend tại thời điểm trả lời — không bao giờ lấy từ vector store.
6. **Subagent không gọi lẫn nhau.** Chỉ supervisor điều phối và tổng hợp.
7. **Không lưu JWT vào LangGraph checkpoint hay conversation store.** Token chỉ sống trong request scope.
8. **Không hard-code giá trị phụ thuộc môi trường/triển khai** — URL, host, port, timeout, tên model, API key... Mọi giá trị loại này phải là field trong `config.py::Settings`, đọc từ `.env`, **không** có default hard-code trong code Python (kể cả trong `Settings` — field không có default, thiếu biến env thì phải crash lúc khởi động, không âm thầm dùng giá trị đoán). Không áp dụng cho hằng số nội tại của chương trình (mã lỗi, HTTP status gắn với 1 loại exception, route path, tên field DTO...) — những cái đó là định danh của code, đổi qua `.env` sẽ vô nghĩa, không phải "hard code" theo nghĩa này.

## Cấu trúc thư mục (Layered Architecture)

```text
src/ai_service/
├── presentation/    # FastAPI routes, DTO — chỉ gọi application/use_cases
├── application/      # use_cases, orchestration (supervisor/subagents), tools, ports, dto
├── domain/            # Conversation, PendingAction, AuthContext — KHÔNG copy entity backend
├── infrastructure/     # backend HTTP client, RAG, persistence, LLM — implement application/ports
└── bootstrap/            # wiring DI, build agent graph lúc startup
```

Quy tắc phụ thuộc: `presentation → application → domain`; `infrastructure` implement `application/ports` và không được import ngược lên `application`; `domain` không import FastAPI/LangChain/LangGraph/httpx. Tool trong `application/tools/` chỉ chuyển đổi input/output rồi gọi port — không tự tính toán nghiệp vụ.

## Rules

- `.claude/rules/code-style.md` — quy ước code style Python/FastAPI/LangChain cho dự án này.
- `.claude/rules/error-handling-logging.md` — nguyên tắc try/except và logging, áp cho từng layer + riêng cho tool-calling.

## Trạng thái hiện tại

Dự án đã qua Phase 0: có `chat`/`chat/stream`/`chat/{session_id}` endpoint, checkpoint SQLite, chat model provider (xem `infrastructure/llm/factory.py` — provider cụ thể quyết định ở đó, không pre-lock ở tài liệu). Chưa có embedding client trong `pyproject.toml` — xem mục 12 của roadmap trước khi thêm dependency để tránh trùng lặp quyết định.
