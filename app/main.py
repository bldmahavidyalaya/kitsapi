from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlmodel import SQLModel
import os

from app.api.v1 import health, items, convert, convert_advanced, convert_advanced_extended
from app.db.session import engine


def create_app() -> FastAPI:
    app = FastAPI(title="Kits API", version="0.1.0")

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(items.router, prefix="/api/v1")
    app.include_router(convert.router, prefix="/api/v1")
    app.include_router(convert_advanced.router, prefix="/api/v1")
    app.include_router(convert_advanced_extended.router, prefix="/api/v1")

    app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

    @app.on_event("startup")
    def on_startup():
        SQLModel.metadata.create_all(engine)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
