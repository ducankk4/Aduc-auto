# Phase 1b — Tổng kết (Dọn cấu trúc + Lịch sử hội thoại)

> Trạng thái: **code xong, chưa nghiệm thu** — chờ chạy `uv sync` + smoke test theo mục cuối file.
> Đọc kèm `phase-1-summary.md`. Phase này không có trong lộ trình 6 phase gốc: nó sinh ra từ một
> đợt refactor cấu trúc, cộng thêm scope mới là lưu lịch sử hội thoại.

## Quyết định đã chốt

| Quyết định | Lựa chọn | Ghi chú |
|---|---|---|
| Contract | **ABC + `@abstractmethod`**, tên `I<Danh từ>` | Đổi từ `Protocol`; implementation kế thừa tường minh, thiếu method là `TypeError` ngay lúc khởi tạo |
| Gom contract | Mọi repository contract chung `core/interface/repository.py` | Không mỗi contract một file |
| `__init__.py` | **Bỏ hoàn toàn** | Namespace package; đổi lại là không có lớp re-export, mọi import trỏ thẳng module |
| Upload tài liệu qua API | **Bỏ**, cân nhắc lại sau khi dự án hoàn thiện | Kéo theo: `IDocumentRepository` chỉ còn `vector_search`, ingest vẫn là script chạy tay |
| `IEmbeddingService` | **Bỏ** | `Embeddings` của LangChain đã là interface đó; đổi sang Bedrock/AzureOpenAI chỉ cần sửa `build_embeddings()` |
| Đơn vị `Session` | **Một cặp hỏi/đáp** | `Conversation` → `Session[]`, giống Chatbot |
| `thread_id` LangGraph | **Gắn với Session** (mỗi lượt một thread) | Hệ quả: checkpointer KHÔNG mang ngữ cảnh giữa các lượt — history phải nạp lại tường minh |
| Domain message | **Tự định nghĩa**, không dùng `HumanMessage`/`AIMessage` | `core/domain/` cấm import framework; dữ liệu này đem đi lưu, không nên bám schema LangChain |
| Config default | Chia theo hậu quả khi sai | Secret/endpoint/model + giá trị gắn với dữ liệu đã ingest: bắt buộc. Tunable + đường dẫn local: được default |

## Đã có gì, ở đâu

**Lịch sử hội thoại (mới):**
- `core/domain/message.py` — `MessageRole`, `UserMessage`, `AssistantMessage` (có `response_time_seconds`), `Session`, `Conversation`.
- `core/interface/repository.py` — `IMessageRepository`: `find_conversation` / `create_conversation` / `update_conversation`.
- `repository/message_repository.py` — `SqliteMessageRepository` trên **aiosqlite**; cả `Conversation` lưu thành một blob JSON ở cột `data`; `init()` tạo bảng, gọi từ lifespan chứ không trong `__init__`.
- `services/message_service.py` — `MessageService.get_recent_sessions()` (giới hạn `CONVERSATION_HISTORY_LIMIT`), `append_session()` (chưa có thì create, có rồi thì update).
- `agent/history.py` — `build_agent_messages(history, question)`: chỗ DUY NHẤT map domain → `HumanMessage`/`AIMessage`.
- `api/routes/conversation.py` + `api/schemas/conversation.py` — `GET /api/v1/conversation/{id}`.

**Đổi ở luồng chat:**
- `POST /api/v1/chat` nhận `{message, conversation_id?, user_id?}` → trả `{conversation_id, session_id, reply}`.
  Trước đây là `thread_id` cả vào lẫn ra; giờ `thread_id` là chuyện nội bộ, mỗi lượt sinh `sess-xxxx` mới.
- Route đo `response_time_seconds` quanh `ainvoke`, nạp history trước khi gọi, lưu session sau khi có reply.

**Dọn từ đợt refactor:**
- `agent/checkpointer.py` — chuyển từ `core/` sang (nó là thứ chỉ tồn tại vì LangGraph).
- `infrastructure/vector_store/qdrant.py` — gộp `factory.py` + `qdrant_retriever.py` cũ; class đổi tên thành `QdrantDocumentRepository`.
- `infrastructure/llm/groq.py` — đổi tên từ `factory.py` (file = tên vendor).
- `core/domain/rag.py` — đổi tên từ `knowledge.py`; `VectorSearchResult` giờ **chứa** `Chunk` thay vì lặp lại field của nó.

## Bẫy đã biết

1. **Mỗi lượt chat là một `thread_id` mới.** Agent không tự nhớ gì cả — nếu quên nạp history qua
   `build_agent_messages()` thì nó trả lời như chưa từng nói chuyện, mà không báo lỗi gì.
2. **`conversation_id` mới là thứ client phải gửi lại**, không phải `thread_id`. Gửi nhầm sẽ tạo
   hội thoại mới im lặng.
3. **4 bug cũ đã vá, đừng tái tạo:** `chunk.score` (đúng là `similarity_score`), `Chunk` thiếu `id`,
   `IRetriever`/`RAGService` lệch kiểu trả về, và ingest chỉ ghi metadata `source` trong khi
   retriever đọc `document_id`/`title`/`source_file`/`chunk_index` → **mọi nguồn hiện ra đều là
   `unknown`**. Sửa ingest thì phải ingest lại mới thấy tác dụng.
4. Qdrant chết/chưa ingest → `InfrastructureError` (502). Kiểm container trước khi đổ lỗi cho code.
5. Đổi `EMBEDDING_MODEL` mà quên ingest lại → search trả rác hoặc lỗi dimension.
6. `CarRepository` vẫn **chưa có luồng nào gọi** — Phase 2 là người dùng đầu tiên.

## Lệnh hay dùng

```bash
uv sync
uv run ruff check . && uv run ruff format .

docker run -d --name aduc-auto-qdrant -p 6333:6333 -v qdrant_data:/qdrant/storage qdrant/qdrant
uv run python scripts/ingest_knowledge.py            # chạy lại khi đổi knowledge/ hoặc embedding model
uv run uvicorn api.main:app --reload --port 8001
```

## Mối nối cho Phase 2 (data-ops thật + HITL)

1. Mối nối cũ ở `phase-1-summary.md` vẫn còn nguyên giá trị, trừ hai điểm đổi tên:
   `CarRepositoryProtocol` → `ICarRepository`, `api/chat.py` → `api/routes/chat.py`.
2. **HITL va vào thiết kế thread mới.** `interrupt()` xảy ra giữa một lượt, mà lượt đó là một
   thread riêng — resume phải dùng đúng `session_id` của lượt bị treo, không phải `conversation_id`.
   Endpoint resume nhận `Command(resume=...)` cần nhận `session_id`.
3. Lượt bị interrupt thì **chưa có answer** để lưu — cần quyết định lưu session dở dang hay chỉ lưu
   sau khi approve. Hiện `append_session()` đòi đủ cả question lẫn answer.
4. Audit log bắt buộc: mọi interrupt/approve/reject log `INFO` kèm `thread_id`, tên tool, tham số
   đã che nhạy cảm.
