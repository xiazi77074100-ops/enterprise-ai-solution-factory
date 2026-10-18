from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.auth.models import User, UserSession
from app.core.config import Settings
from app.core.errors import ApiError
from app.core.security import hash_session_id, new_session_id, verify_password


def login_failed() -> ApiError:
    return ApiError("login_failed", "ユーザー ID またはパスワードが正しくありません。", 401)


def login(
    db: Session, settings: Settings, login_id: str, password: str, old_session_id: str | None
) -> tuple[User, str]:
    """Returns (user, new session id). One failure message for unknown user, wrong password and lock."""
    now = datetime.now(UTC)
    user = db.execute(select(User).where(User.login_id == login_id)).scalar_one_or_none()
    password_ok = verify_password(user.password_hash if user else None, password)
    if user is None or not user.is_active:
        raise login_failed()
    if user.locked_until is not None and user.locked_until > now:
        raise login_failed()
    if not password_ok:
        user.failed_logins += 1
        if user.failed_logins >= settings.login_max_failures:
            user.locked_until = now + timedelta(minutes=settings.login_lock_minutes)
            user.failed_logins = 0
        db.commit()
        raise login_failed()
    user.failed_logins = 0
    user.locked_until = None
    if old_session_id:  # session fixation: never keep a pre-login id
        db.execute(delete(UserSession).where(UserSession.id_hash == hash_session_id(old_session_id)))
    session_id = new_session_id()
    db.add(
        UserSession(
            id_hash=hash_session_id(session_id),
            user_id=user.id,
            created_at=now,
            last_seen_at=now,
            expires_at=now + timedelta(hours=settings.session_absolute_hours),
        )
    )
    db.commit()
    return user, session_id


def logout(db: Session, session_id: str) -> None:
    db.execute(delete(UserSession).where(UserSession.id_hash == hash_session_id(session_id)))
    db.commit()
