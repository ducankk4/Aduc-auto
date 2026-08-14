# Phase 2 — Tổng kết (Data-ops subagent + HITL)

> Trạng thái: **code xong cả 4 bước**. Spike console (bước 1) đã chứng minh interrupt phát sinh
> trong subagent propagate lên supervisor — rủi ro lớn nhất của phase đã gỡ. Luồng HTTP
> (interrupted/resume, bước 4) chưa nghiệm thu end-to-end.
> Đọc kèm `phase-1-summary.md` và `phase-1b-conversation-summary.md`.

## Quyết định đã chốt

| Quyết định | Lựa chọn | Ghi chú |
|---|---|---|
| Cơ chế HITL | **`interrupt_on` per-subagent của DeepAgents** (0.7.5, chạy trên `HumanInTheLoopMiddleware`) | Không tự viết middleware; cần checkpointer (đã có từ Phase 0) |
| Phân loại tool sensitive | Metadata **`requires_approval=True`** trên tool; `interrupt_on` **suy ra từ metadata** trong `build_data_ops_subagent` | Không hardcode tên tool ở hai nơi; thêm tool sensitive mới chỉ cần set metadata |
| Quyết định phê duyệt | **approve / edit / reject** | Bỏ "respond" — không có tool kiểu "hỏi người dùng" |
| Session bị interrupt | **Lưu ngay ở `pending_approval`** (chỉ câu hỏi), resume xong thì `complete_session` điền answer | Bỏ ngang thì session nằm lại pending → thành dữ liệu "bỏ ngang" cho báo cáo Phase 4 |
| Đặt lái thử phía backend | Dùng **`POST /api/v1/leads` có sẵn** (public, rate limit 10 req/phút/IP) | Backend không phải sửa gì; domain bên mình đặt tên `TestDriveBooking`, map "lead" ở repository |
| Tham số tool booking | **`car_slug`**, không phải tên xe | `BookingService` resolve slug → `vehicle_id` qua `ICarRepository`; ép luồng "tra xe trước, đặt sau" |
| Wire format HITL | Đóng gói trong **`agent/hitl.py`** | Nơi duy nhất ngoài middleware biết `HITLRequest`/`HITLResponse`; `api/` và `scripts/` chỉ chạm dict thuần |
| Lỗi trong tool | `NotFoundError` bắt tại chỗ, trả text cho LLM tự xử lý; `InfrastructureError` để nổ xuyên | Nhất quán với cách `rag_search` xử lý Qdrant chết từ Phase 1 |

## Đã có gì, ở đâu

**Lát cắt dữ liệu (bước 2):**
- `core/domain/booking.py` — `TestDriveBooking`, `BookingStatus` (mirror 5 trạng thái lead backend).
- `core/interface/repository.py` — thêm `IBookingRepository.create(...)`.
- `repository/booking_repository.py` — POST `/api/v1/leads`, map envelope → domain, log không chứa phone/email.
- `services/car_service.py` — `list_cars()` (phân trang), `get_car(slug)` (raise `NotFoundError`).
- `services/booking_service.py` — resolve slug → `vehicle_id` rồi tạo booking.

**Session phương án B (bước 2):**
- `core/domain/message.py` — `SessionStatus` (`completed`/`pending_approval`); `Session.answer` giờ `Optional`.
- `services/message_service.py` — thêm `append_pending_session()`, `complete_session()`; upsert gom về `_append()`.
- `agent/history.py` — nạp ngữ cảnh bỏ qua session chưa có answer.
- `repository/message_repository.py` — chịu `answer=None`; row cũ thiếu `status` mặc nhiên `completed`, **không cần migrate**.

**Agent (bước 1 + 3):**
- `agent/tools/car.py` — `search_cars` (kèm slug), `get_car_detail` — tool view, chạy thẳng.
- `agent/tools/booking.py` — `create_test_drive_booking` (sensitive, `requires_approval=True`).
- `agent/tools/constants.py` — key `REQUIRES_APPROVAL`.
- `agent/subagent/data_ops.py` — spec subagent nhận `CarService` + `BookingService`; `interrupt_on` suy từ metadata.
- `agent/hitl.py` — `pending_approvals()`, `build_decision()`, `build_resume_command()`.
- `agent/supervisor.py` — nhận `subagents` bơm từ wiring, không còn stub.
- `agent/prompt/prompts.py` — `DATA_OPS_SYSTEM_PROMPT` (luồng: tra slug → đủ thông tin khách → mới gọi booking).

**Interface (bước 4):**
- `api/routes/chat.py` — `POST /chat` trả `{interrupted: true, approval_requests}` + lưu session pending khi gặp interrupt; `POST /chat/resume` nhận decisions, resume đúng `thread_id = session_id`, xử lý cả interrupt nối tiếp.
- `api/schemas/chat.py` — `ApprovalRequest`, `ResumeRequest`/`ResumeDecision` (validator: `edit` phải kèm `tool` + `args`); `ChatResponse.reply` thành Optional.
- `core/masking.py` — `mask_sensitive_args()` che `phone`/`email` trong audit log, dùng chung API + console.
- `api/dependencies.py` — `build_supervisor(checkpointer)` giữ chữ ký cũ; trong ruột dựng 1 httpx client chung cho `CarRepository` + `BookingRepository`.
- `scripts/chat.py` — console chat (viết lại, file cũ đã mất từ đợt refactor 1b): mỗi lượt một thread như production, phê duyệt `y/e/n` tại chỗ.

## Bẫy đã biết

1. **Resume phải dùng đúng `session_id` của lượt bị treo** làm `thread_id`. Route resume đã có
   guard `aget_state` → không có interrupt treo thì 404, chặn vụ LangGraph im lặng mở thread mới.
2. **Interrupt là đồ dùng một lần** — resume xong mà gọi resume lại cùng `session_id` sẽ 404.
   Client phải cầm đúng cặp `conversation_id`/`session_id` từ response `interrupted`.
3. **Rate limit backend `/leads`: 10 req/phút/IP.** Test đặt lịch liên tục sẽ dính 429 → phía mình
   nổ `InfrastructureError` (502). Là hành vi đúng, không phải bug.
4. Backend :8000 không chạy → mọi tool data-ops (kể cả `search_cars`) nổ 502. Kiểm backend trước
   khi đổ lỗi cho agent.
5. Audit log là luật: mọi interrupt/approve/reject log `INFO` kèm `thread_id`, tên tool, args đã
   che qua `core/masking.py`. Thêm tool sensitive mới phải giữ nguyên luật này.
6. Session pending bị `build_agent_messages` bỏ qua khi nạp history — lượt bỏ ngang không vào
   ngữ cảnh LLM. Muốn đổi hành vi này thì sửa đúng chỗ đó.
7. httpx client dùng chung **không được `aclose()`** lúc shutdown (như trước giờ) — việc dọn dẹp
   để Phase 5.
8. `agent/state/state.py` (`SupervisorState`) hiện chưa được graph nào dùng trực tiếp — đừng tưởng
   nó là state thật của supervisor (DeepAgents tự quản state của nó).

## Lệnh hay dùng

```bash
# hạ tầng: Qdrant + backend chạy trước
docker run -d --name aduc-auto-qdrant -p 6333:6333 -v qdrant_data:/qdrant/storage qdrant/qdrant
# backend/:  uv run uvicorn src.app.main:app --reload --port 8000

# ai-service/
uv sync
uv run ruff check . && uv run ruff format .
uv run python scripts/chat.py                        # test nhanh + HITL console (y/e/n)
uv run uvicorn api.main:app --reload --port 8001

# HITL qua HTTP
curl -X POST localhost:8001/api/v1/chat -H "Content-Type: application/json" \
  -d '{"message": "Đặt lái thử xe <slug>, tên A, sđt 09xxx, email a@b.c"}'
curl -X POST localhost:8001/api/v1/chat/resume -H "Content-Type: application/json" \
  -d '{"conversation_id": "conv-...", "session_id": "sess-...", "decisions": [{"type": "approve"}]}'
```

## Mối nối cho Phase 3 (comparison subagent)

1. **Tái dùng, không viết lại**: subgraph so sánh lấy dữ liệu xe qua `CarService`/`ICarRepository`
   sẵn có (overview đã chốt). Cần thêm truy vấn mới (ví dụ lấy nhiều xe theo list slug) thì thêm
   method vào contract + repository hiện có, đừng mở client httpx riêng.
2. Comparison là **`CompiledSubAgent`** (graph tự build + compile) thay vì dict spec — đăng ký vẫn
   qua tham số `subagents` của `build_supervisor_agent`, cùng chỗ với data-ops.
3. Comparison **không gọi RAG** (chốt từ overview) và không có tool sensitive → không cần
   `interrupt_on`; nếu sau này phát sinh, dùng lại pattern metadata `requires_approval`.
4. Card so sánh là payload có cấu trúc, nhưng `ChatResponse` hiện chỉ trả `reply` text — Phase 3
   phải quyết cách chở structured payload qua API (field mới trong response? artifact riêng?).
5. State cho subgraph: định nghĩa `ComparisonState` ở module riêng trong `agent/state/`, theo quy
   ước mục 11 của code-style.
