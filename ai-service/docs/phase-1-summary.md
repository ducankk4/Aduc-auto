# Phase 1 — Tổng kết (Supervisor + RAG)

> Trạng thái: **DONE** — chat console đã nghiệm thu cả 2 tiêu chí (RAG + delegation stub).
> Endpoint FastAPI đã viết xong, đang chờ test bằng uvicorn.
> Đọc kèm `phase-0-summary.md`. Phase 2 cắm vào đúng các mối nối ghi ở cuối file.

## Quyết định đã chốt

| Quyết định | Lựa chọn | Ghi chú |
|---|---|---|
| Framework supervisor | **DeepAgents** (`create_deep_agent`) | `agent/supervisor.py` là nơi DUY NHẤT import deepagents |
| Vector store | **Qdrant** (docker container, port 6333) | Dashboard: `http://localhost:6333/dashboard` |
| Embedding | **HuggingFace local** `paraphrase-multilingual-MiniLM-L12-v2` | Đã đổi từ bge-m3 sang cho nhẹ; đổi model → BẮT BUỘC ingest lại (số chiều khác) |
| Phạm vi RAG | **Chỉ supervisor được gọi rag_search** | Subagent không tự truy cập RAG (chốt từ overview) |
| Trả lời RAG | Service chỉ retrieve, LLM supervisor tự synthesize | `RAGService` test được không cần LLM |
| Docker | **Anh tự quản** — không tạo Dockerfile/compose trong repo | Chỉ dùng lệnh `docker run` đơn lẻ khi cần |

## Đã có gì, ở đâu

**RAG pipeline:**
- `knowledge/*.md` — 3 file tiếng Việt (FAQ, chính sách đặt cọc/hủy/hoàn tiền, hướng dẫn lái thử), khôi phục từ git history của folder `ai_service` cũ. Nội dung là nháp AI soạn, nghiệp vụ chưa rà.
- `core/domain/knowledge.py` — `KnowledgeChunk` (content, source, score).
- `core/interface/retriever.py` — `RetrieverProtocol.search(query, top_k)`.
- `infrastructure/vector_store/factory.py` — `build_embeddings()`, `build_vector_store()` (`from_existing_collection` — fail nếu chưa ingest).
- `infrastructure/vector_store/qdrant_retriever.py` — `QdrantRetriever` implement Protocol.
- `services/rag_service.py` — `RAGService.search_knowledge()` (top_k từ `RAG_TOP_K`).
- `scripts/ingest_knowledge.py` — chunk (`RAG_CHUNK_SIZE`/`OVERLAP`) → embed → `force_recreate` collection. Chạy lại mỗi khi sửa knowledge/đổi embedding model.

**Supervisor (lưu ý: agent/ đã tái tổ chức thành subpackage):**
- `agent/prompt/prompts.py` — `SUPERVISOR_SYSTEM_PROMPT` (luật chọn tool), `DATA_OPS_STUB_PROMPT`.
- `agent/tools/rag.py` — `build_rag_search_tool(rag_service)`: tool = closure nhận service bơm từ ngoài; docstring tool là prompt cho LLM, viết tiếng Việt.
- `agent/supervisor.py` — `build_supervisor_agent(model, rag_service, checkpointer)` → `create_deep_agent` với subagent `data-ops` (hiện là **stub** dict spec: không tool, chỉ trả `[STUB data-ops] Đã nhận nhiệm vụ: ...`).
- Delegation dùng **task tool built-in** của DeepAgents — không tự viết cơ chế route.

**Interface:**
- `api/dependencies.py` — wiring duy nhất: `build_backend_client()`, `build_car_repository()`, `build_rag_service()`, `build_supervisor(checkpointer)`.
- `api/main.py` — lifespan build supervisor 1 lần/process vào `app.state`; exception handler map code → status (`NOT_FOUND`→404, `INFRASTRUCTURE_ERROR`→502...); `/health`.
- `api/chat.py` — `POST /api/v1/chat` `{message, thread_id?}` → `{thread_id, reply}`; thread_id thiếu thì server sinh `web-xxxx`.
- `api/schemas.py`, `api/response.py` — DTO + envelope `{"success": ...}` giống backend.
- `scripts/chat.py` — chat console, log mỗi tool call.

## Bẫy đã biết

- Qdrant chết/chưa ingest → `InfrastructureError` (502 qua API). Kiểm container trước khi đổ lỗi cho code.
- Model embedding đổi mà quên ingest lại → search trả rác hoặc lỗi dimension.
- `CarRepository` đã sẵn sàng nhưng **chưa có luồng nào gọi** — Phase 2 là người dùng đầu tiên, cần backend chạy ở port 8000.

## Lệnh hay dùng

```bash
docker run -d --name aduc-auto-qdrant -p 6333:6333 -v qdrant_data:/qdrant/storage qdrant/qdrant
uv run python scripts/ingest_knowledge.py
uv run python scripts/chat.py                        # test nhanh không cần HTTP
uv run uvicorn api.main:app --reload --port 8001     # API (backend chiếm 8000)
```

## Mối nối cho Phase 2 (data-ops thật + HITL)

1. Thay `_DATA_OPS_STUB` trong `agent/supervisor.py` bằng subagent có tools thật; tool view gọi `CarService` (viết mới ở `services/`, nhận `CarRepositoryProtocol`), tool sensitive (tạo lái thử) khai báo qua `interrupt_on={"tên_tool": True}` của DeepAgents.
2. Backend cần thêm: endpoint tạo test-drive booking phía leads — kiểm tra `backend/src/app/modules/leads/` trước, có sẵn thì `repository/` chỉ thêm method POST.
3. HITL qua HTTP: `POST /chat` phải nhận diện kết quả có `__interrupt__` → trả `{"interrupted": true, "approval_payload": ...}`; thêm endpoint resume nhận `Command(resume=...)` với cùng `thread_id`. Đây là rủi ro kỹ thuật lớn nhất (overview đã cảnh báo) — test interrupt propagate từ subagent lên supervisor TRƯỚC khi làm gì khác.
4. Audit log bắt buộc: mọi interrupt/approve/reject log `INFO` kèm `thread_id`, tên tool, tham số đã che nhạy cảm.
