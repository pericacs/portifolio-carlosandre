from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.config import get_settings
from app.db import get_engine
from app.admin import router as admin_router

settings = get_settings()
app = FastAPI(title="Carlos André | Technology & Ventures", version="0.1.0",
              docs_url="/api/docs" if settings.app_env == "development" else None,
              redoc_url=None, openapi_url="/api/openapi.json" if settings.app_env == "development" else None)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                   allow_credentials=True, allow_methods=["GET"], allow_headers=["Content-Type"])
app.include_router(admin_router)
from app.cms import router as cms_router, public as public_router, messages as message_router
app.include_router(cms_router)
app.include_router(public_router)
app.include_router(message_router)
from app.docx_import import router as docx_router
app.include_router(docx_router)


@app.middleware("http")
async def protect_admin_responses(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/admin"):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


@app.get("/api/health/live")
def liveness():
    return {"status": "ok"}


@app.get("/api/health/ready")
def readiness(response: Response):
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
            revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
            if not revision:
                raise ValueError("Schema not initialized")
    except (SQLAlchemyError, ValueError):
        response.status_code = 503
        return {"status": "unavailable"}
    return {"status": "ok", "database": "connected", "schema": revision}
