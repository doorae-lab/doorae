"""FastAPI 애플리케이션 팩토리."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from doorae.server.routes import router
from doorae.server.config import get_server_settings


def create_app() -> FastAPI:
    """FastAPI 애플리케이션 생성.

    Returns:
        FastAPI 애플리케이션 인스턴스
    """
    settings = get_server_settings()

    app = FastAPI(
        title="Doorae Server",
        description="WebSocket 기반 AI 회의 채팅 서버",
        version="0.1.0",
    )

    # CORS 설정
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 라우터 등록
    app.include_router(router)

    # 정적 파일 서빙 (프론트엔드)
    try:
        app.mount("/static", StaticFiles(directory="doorae/static"), name="static")
    except RuntimeError:
        # 정적 파일 디렉토리가 없으면 스킵
        pass

    return app
