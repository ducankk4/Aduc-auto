# ai-service — Hướng dẫn cho Claude Code

Supervisor agent + subagent cho nền tảng Aduc Auto. Chạy độc lập với `backend/` (port 8001,
backend chiếm 8000), lấy dữ liệu nghiệp vụ từ backend qua HTTP chứ không đụng DB của backend.

Quy ước chung cả monorepo nằm ở [CLAUDE.md ở root](../../CLAUDE.md).

@rules/code-style.md

## Trạng thái hiện tại

Lộ trình 6 phase mô tả ở [docs/ai_service_architecture_overview.md](../docs/ai_service_architecture_overview.md).

- **Phase 0 (shared kernel) — xong.** Config, logger, exception hierarchy, checkpointer SQLite.
- **Phase 1 (supervisor + RAG) — xong.** Supervisor DeepAgents, RAG tool trên Qdrant, `/chat`.
- **Phase 1b (lịch sử hội thoại) — code xong, chưa nghiệm thu.** Phát sinh ngoài lộ trình.
  `Conversation` → `Session`, lưu SQLite, mỗi lượt chat một `thread_id` riêng nên history phải
  nạp lại tường minh. Xem `docs/phase-1b-conversation-summary.md`.
- **Phase 2 (data-ops subagent + HITL) — đang tới.** `_DATA_OPS_STUB` trong `agent/supervisor.py`
  là chỗ cần thay. `CarRepository` đã viết xong nhưng **chưa có luồng nào gọi** — Phase 2 là
  người dùng đầu tiên của nó.

**Đọc `docs/phase-N-summary.md` của phase gần nhất trước khi bắt tay vào việc** — quyết định đã
chốt và bẫy đã biết nằm ở đó, đừng mở lại nếu không có lý do mạnh.

## Đặt code ở đâu

File này **không mô tả cấu trúc thư mục** — cấu trúc còn đổi nhiều qua các phase, chép ra hai chỗ
thì chỉ tạo thêm một bản mốc. Luật để suy ra chỗ đặt cho một file mới (chọn layer, khi nào tách
thư mục, chiều import hợp lệ) nằm ở **mục 2 của `rules/code-style.md`** — đã import ở đầu file này,
sửa cấu trúc thì sửa đúng một chỗ đó. Cấu trúc đang có thì mở repo ra xem.

## Bẫy đã biết

1. **`thread_id` phải giống hệt giữa lần interrupt và lần resume.** Sai chỗ này LangGraph
   **im lặng** mở luồng mới chứ không báo lỗi — cực khó nhận ra.
2. **Mỗi lượt chat là một `thread_id` mới** (`thread_id` = `session_id`), nên checkpointer không
   mang ngữ cảnh giữa các lượt. Quên nạp history qua `agent/history.py` thì agent trả lời như
   chưa từng nói chuyện, cũng không báo lỗi. Thứ client gửi lại là `conversation_id`.
2. **HITL là rủi ro kỹ thuật lớn nhất của dự án.** Phải kiểm tra `interrupt()` phát sinh trong
   subagent có propagate lên tới supervisor không, chứ không chỉ test riêng subagent.
3. **State chỉ chứa dữ liệu serialize được.** Client, connection, session truyền qua
   constructor/config — nhét vào state thì chỉ vỡ khi dùng checkpointer thật.
4. **Qdrant chết hoặc chưa ingest** → `InfrastructureError` (502). Kiểm container trước khi đổ
   lỗi cho code.
5. **Đổi `EMBEDDING_MODEL` mà quên ingest lại** → search trả rác hoặc lỗi sai dimension.
6. Mọi lần interrupt / approve / reject / gọi tool sensitive **bắt buộc** log `INFO` kèm
   `thread_id`, tên tool, tham số đã che dữ liệu nhạy cảm. Đây là audit trail bắt buộc.

## Lệnh hay dùng

```bash
uv sync
uv run ruff check . && uv run ruff format .

docker run -d --name aduc-auto-qdrant -p 6333:6333 -v qdrant_data:/qdrant/storage qdrant/qdrant
uv run python scripts/ingest_knowledge.py            # chạy lại khi đổi knowledge/ hoặc embedding model
uv run uvicorn api.main:app --reload --port 8001     # API (backend chiếm 8000)
```

Phase 2 trở đi cần `backend/` chạy sẵn ở port 8000 thì `repository/` mới có dữ liệu.

## Test

**Không tự chạy test.** Chỉ viết test khi được yêu cầu, kèm mô tả cách chạy và điểm cần chú ý;
việc chạy và xác nhận kết quả do người dùng làm. Quy ước test từng layer xem mục 15 của
`rules/code-style.md` (đã import ở trên).
