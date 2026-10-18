"""Authentication, CSRF/Origin and project-level authorization dependencies (permissions.md).

Every non-public router uses `authenticated` as a router dependency (deny by default). State-changing
methods also require a matching Origin and X-CSRF-Token.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User, UserSession
from app.core.config import Settings
from app.core.db import get_db
from app.core.errors import ApiError
from app.core.security import csrf_valid, hash_session_id
from app.project.models import ProjectMember

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


@dataclass(frozen=True)
class AuthContext:
    user: User
    session_id: str


def get_settings_dep(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def unauthenticated() -> ApiError:
    return ApiError("unauthenticated", "ログインしてください。", 401)


def forbidden() -> ApiError:
    return ApiError("forbidden", "この操作を行う権限がありません。", 403)


def not_found() -> ApiError:
    return ApiError("not_found", "対象が見つかりません。", 404)


def check_origin(request: Request, settings: Settings) -> None:
    """Same-origin check for state-changing requests (also used by login, which has no CSRF token yet)."""
    origin = request.headers.get("origin")
    if origin is None and request.headers.get("referer", "").startswith(settings.site_origin + "/"):
        origin = settings.site_origin
    if origin != settings.site_origin:
        raise forbidden()


def authenticated(
    request: Request,
    db: Session = Depends(get_db),  # noqa: B008
    settings: Settings = Depends(get_settings_dep),  # noqa: B008
) -> AuthContext:
    session_id = request.cookies.get(settings.session_cookie_name)
    if not session_id or len(session_id) > 128:
        raise unauthenticated()
    record = db.get(UserSession, hash_session_id(session_id))
    now = datetime.now(UTC)
    if (
        record is None
        or record.expires_at <= now
        or record.last_seen_at + timedelta(minutes=settings.session_idle_minutes) <= now
    ):
        if record is not None:
            db.delete(record)
            db.commit()
        raise unauthenticated()
    user = db.get(User, record.user_id)
    if user is None or not user.is_active:
        raise unauthenticated()
    if request.method not in SAFE_METHODS:
        check_origin(request, settings)
        if not csrf_valid(settings.secret_key.get_secret_value(), session_id, request.headers.get("x-csrf-token")):
            raise forbidden()
    record.last_seen_at = now
    db.commit()
    return AuthContext(user=user, session_id=session_id)


def project_roles(db: Session, project_id: uuid.UUID, user: User) -> list[str]:
    """Roles of the user in the project. Non-members get 404 (same as non-existent)."""
    member = db.execute(
        select(ProjectMember).where(ProjectMember.project_id == project_id, ProjectMember.user_id == user.id)
    ).scalar_one_or_none()
    if member is None:
        raise not_found()
    return list(member.roles)


def require_project_role(db: Session, project_id: uuid.UUID, user: User, allowed: set[str]) -> list[str]:
    roles = project_roles(db, project_id, user)
    if not allowed & set(roles):
        raise forbidden()
    return roles
