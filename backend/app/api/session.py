import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, authenticated, check_origin, get_settings_dep, unauthenticated
from app.api.models import StrictModel
from app.auth import service
from app.auth.models import User, UserSession
from app.core.config import Settings
from app.core.db import get_db
from app.core.security import csrf_token, hash_session_id

public_router = APIRouter(prefix="/api/v1")
router = APIRouter(prefix="/api/v1", dependencies=[Depends(authenticated)])


class LoginRequest(StrictModel):
    login_id: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class SessionUser(BaseModel):
    id: uuid.UUID
    display_name: str
    roles: list[str]


class SessionInfo(BaseModel):
    user: SessionUser
    csrf_token: str
    expires_at: datetime


def _info(db: Session, settings: Settings, user: User, session_id: str) -> SessionInfo:
    record = db.get(UserSession, hash_session_id(session_id))
    if record is None:
        raise unauthenticated()
    return SessionInfo(
        user=SessionUser(id=user.id, display_name=user.display_name, roles=["admin"] if user.is_admin else []),
        csrf_token=csrf_token(settings.secret_key.get_secret_value(), session_id),
        expires_at=record.expires_at,
    )


@public_router.post("/session", response_model=SessionInfo, operation_id="login")
def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),  # noqa: B008
    settings: Settings = Depends(get_settings_dep),  # noqa: B008
) -> SessionInfo:
    check_origin(request, settings)  # login CSRF
    user, session_id = service.login(
        db, settings, body.login_id, body.password, request.cookies.get(settings.session_cookie_name)
    )
    response.set_cookie(
        settings.session_cookie_name,
        session_id,
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return _info(db, settings, user, session_id)


@router.get("/session", response_model=SessionInfo, operation_id="getSession")
def get_session(
    ctx: AuthContext = Depends(authenticated),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
    settings: Settings = Depends(get_settings_dep),  # noqa: B008
) -> SessionInfo:
    return _info(db, settings, ctx.user, ctx.session_id)


@router.delete("/session", status_code=204, operation_id="logout")
def logout(
    response: Response,
    ctx: AuthContext = Depends(authenticated),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
    settings: Settings = Depends(get_settings_dep),  # noqa: B008
) -> Response:
    service.logout(db, ctx.session_id)
    response.status_code = 204
    response.delete_cookie(settings.session_cookie_name, path="/", secure=settings.cookie_secure, httponly=True)
    return response
