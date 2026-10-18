from fastapi import FastAPI

from app.api import catalog, projects, session, solutions, system
from app.core.config import Settings, get_settings
from app.core.db import make_session_factory
from app.core.errors import install_error_handlers
from app.core.middleware import SecurityMiddleware


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    docs = settings.expose_docs
    app = FastAPI(
        title="EASF API",
        version="1.0.2",  # contracts/openapi.yaml
        docs_url="/docs" if docs else None,
        redoc_url=None,
        openapi_url="/openapi.json" if docs else None,
        # VA-005: the trailing-slash redirect builds Location from the Host header; contract paths have no slash.
        redirect_slashes=False,
    )
    app.state.settings = settings
    app.state.session_factory = make_session_factory(settings)  # engine connects lazily
    install_error_handlers(app)
    app.add_middleware(SecurityMiddleware, settings=settings)
    app.include_router(system.router)
    app.include_router(session.public_router)
    app.include_router(session.router)
    app.include_router(projects.router)
    app.include_router(catalog.router)
    app.include_router(solutions.router)
    return app
