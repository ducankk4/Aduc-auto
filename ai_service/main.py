import uvicorn

from ai_service.config import Settings


def main() -> None:
    settings = Settings()
    uvicorn.run(
        "ai_service.bootstrap.app_factory:create_app",
        factory=True,
        host="0.0.0.0",
        port=settings.ai_service_port,
        reload=settings.app_debug,
    )


if __name__ == "__main__":
    main()
