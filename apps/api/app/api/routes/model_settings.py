from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_any_authenticated_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.model_settings import ModelSettingsResponse, ModelSettingsUpdateRequest
from app.services.model_settings import ModelSettingsError, get_or_create_user_model_settings, serialize_model_settings, update_model_settings

router = APIRouter()


@router.get("/model-settings", response_model=ModelSettingsResponse)
def get_model_settings(
    db: Session = Depends(get_db),
    user: User = Depends(get_any_authenticated_user),
) -> ModelSettingsResponse:
    record = get_or_create_user_model_settings(db, user.id)
    return serialize_model_settings(record)


@router.put("/model-settings", response_model=ModelSettingsResponse)
def put_model_settings(
    payload: ModelSettingsUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_any_authenticated_user),
) -> ModelSettingsResponse:
    try:
        return update_model_settings(db=db, user=user, payload=payload)
    except ModelSettingsError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
