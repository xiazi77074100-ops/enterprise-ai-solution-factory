from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import ApiError

router = APIRouter()


class Health(BaseModel):
    status: Literal["ok", "degraded"]


@router.get("/health", response_model=Health, operation_id="getHealth")
def get_health() -> Health:
    return Health(status="ok")


@router.get("/ready", response_model=Health, operation_id="getReady")
def get_ready(db: Session = Depends(get_db)) -> Health:  # noqa: B008
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise ApiError("service_unavailable", "現在利用できません。しばらく待ってからお試しください。", 503) from exc
    return Health(status="ok")
