# Aduc Auto — Hướng dẫn cho Claude Code

Monorepo của nền tảng đặt cọc mua xe: một backend nghiệp vụ và một AI service chạy agent.
Hai service **độc lập hoàn toàn** — riêng `.venv`, riêng `pyproject.toml`, riêng `.env`, giao
tiếp với nhau qua HTTP chứ không import chéo code.

## Bản đồ repo

| Thư mục | Là gì | Port | Stack |
|---|---|---|---|
| `backend/` | API nghiệp vụ (catalog, leads, orders, payments, users). Modular 3-layer monolith. | 8000 | FastAPI, SQLAlchemy async, Postgres, Alembic |
| `ai-service/` | Supervisor agent + subagent + RAG. Nguồn dữ liệu nghiệp vụ lấy từ `backend/` qua HTTP. | 8001 | FastAPI, LangGraph, DeepAgents, Groq, Qdrant |

Chi tiết quy ước của `ai-service/` nằm ở
[ai-service/.claude/CLAUDE.md](ai-service/.claude/CLAUDE.md) — **đọc file đó trước khi động vào
bất cứ thứ gì trong `ai-service/`**, và không lặp lại nội dung của nó ở đây.

## Tài liệu là nguồn sự thật

Đọc trước khi đề xuất thay đổi kiến trúc, đừng suy diễn từ code:

- [ai-service/docs/ai_service_architecture_overview.md](ai-service/docs/ai_service_architecture_overview.md)
  — kiến trúc + lộ trình 6 phase của ai-service.
- `ai-service/docs/phase-N-summary.md` — quyết định đã chốt, bẫy đã biết, mối nối sang phase
  sau. **Phase đang làm dở: xem file summary mới nhất trước tiên.**
- [backend/docs/erd-design.md](backend/docs/erd-design.md) — mô hình dữ liệu.
- [backend/docs/roadmap-car-deposit-website.md](backend/docs/roadmap-car-deposit-website.md) — lộ trình sản phẩm.

## Môi trường & lệnh

Cả hai service dùng Python 3.11 + `uv`. Mọi lệnh chạy **từ trong thư mục service**, không phải
từ root. Dependency khai báo trong `pyproject.toml` và commit kèm `uv.lock` — không `pip install`.

```bash
# backend/
uv sync
uv run uvicorn src.app.main:app --reload --port 8000
uv run alembic upgrade head
uv run python scripts/seed_db.py

# ai-service/
uv sync
uv run ruff check . && uv run ruff format .
uv run uvicorn api.main:app --reload --port 8001
uv run python scripts/chat.py          # thử agent nhanh, không cần HTTP
```

Hạ tầng phụ thuộc (chạy bằng container, khởi động trước khi bật service):

- Postgres cho `backend/` — `backend/docker-compose.yml`, port 5432.
- Qdrant cho `ai-service/` — port 6333. Chưa ingest knowledge thì RAG trả `InfrastructureError`.

## Quy ước làm việc

- **Không tự chạy test, script, hay khởi động server để tự xác minh.** Viết code xong thì mô tả
  cách chạy và những điểm cần chú ý, để người dùng tự chạy và báo lại kết quả.
- **Xong một phase thì viết `ai-service/docs/phase-N-summary.md`** theo đúng bố cục file cũ:
  quyết định đã chốt / đã có gì, ở đâu / bẫy đã biết / lệnh hay dùng / mối nối cho phase sau.
  Việc này là một phần của phase, không đợi được nhắc.
- Task nhiều bước thì chia nhỏ: báo trước việc sắp làm, xong một khối thì dừng chờ xác nhận.
- Quyết định thiết kế có nhiều lựa chọn thật sự (chọn thư viện, chọn kiến trúc) thì liệt kê
  phương án kèm ưu/nhược để người dùng chọn, không tự quyết rồi thông báo sau.

## Luật chung cho cả hai service

- **Không hardcode config.** Mọi URL, port, tên model, timeout, secret đều là field của
  `Settings` (`pydantic-settings`), đọc từ `.env`. Thêm field mới mà quên cập nhật `.env.example`
  là một bug.
- **Không commit `.env`** (đã có trong `.gitignore`). `.env.example` phải liệt kê đủ 100% key.
- **Logging bằng `loguru`**, lazy format `{}` chứ không f-string, ngữ cảnh viết kiểu
  `[key=value, key=value]` cho dễ grep. Không log token, mật khẩu, API key, dữ liệu cá nhân.
- **Docstring Google style, viết tiếng Anh**; message lỗi hướng tới người dùng cuối viết tiếng
  Việt. Comment trong code chỉ giải thích *tại sao*, không giải thích *cái gì*.
- **I/O luôn `async`.** Không gọi hàm blocking trong async context; buộc phải dùng lib sync thì
  bọc `asyncio.to_thread`.
- Tài liệu và trao đổi viết tiếng Việt; code, tên biến, docstring viết tiếng Anh.
