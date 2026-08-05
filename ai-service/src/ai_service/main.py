"""AI Service Entrypoint."""

from fastapi import FastAPI

app = FastAPI(
    title="Aduc-auto AI Service",
    version="0.1.0",
    description="Multi-agent orchestration and RAG service for Aduc-auto",
)


@app.get("/healthz")
async def health_check():
    return {"status": "ok", "service": "ai-service"}
