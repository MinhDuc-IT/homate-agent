"""Scene CRUD for the dashboard."""
from __future__ import annotations
from typing import Any
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from homate.presentation.dependencies import get_current_user, require_admin
from homate.presentation.dependencies import get_household_service
router = APIRouter(prefix='/api/dashboard/scenes', tags=['scenes'])

class SceneStepWrite(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=64)
    action: str = Field(..., min_length=1, max_length=64)
    parameters: dict[str, Any] = Field(default_factory=dict)

class SceneWrite(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    voice_keyword: str = Field(..., min_length=1, max_length=80)
    is_enabled: bool = True
    steps: list[SceneStepWrite] = Field(default_factory=list)

class SceneStepOut(BaseModel):
    id: str
    sort_order: int
    device_id: str
    device_name: str
    device_kind: str
    action: str
    parameters: dict[str, Any] = Field(default_factory=dict)

class SceneOut(BaseModel):
    id: str
    name: str
    voice_keyword: str
    is_enabled: bool
    steps: list[SceneStepOut] = Field(default_factory=list)

def _home_id(user: dict[str, Any]) -> str:
    home_id = user.get('home_id')
    if not home_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Missing home')
    return str(home_id)

def _map_write_error(exc: Exception) -> HTTPException:
    if isinstance(exc, LookupError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

@router.get('', response_model=list[SceneOut])
async def get_scenes(db_path=Depends(get_household_service), user: dict=Depends(get_current_user)) -> list[SceneOut]:
    return [SceneOut.model_validate(row) for row in db_path.list_scenes(_home_id(user))]

@router.get('/{scene_id}', response_model=SceneOut)
async def get_one_scene(scene_id: str, db_path=Depends(get_household_service), user: dict=Depends(get_current_user)) -> SceneOut:
    try:
        return SceneOut.model_validate(db_path.get_scene(_home_id(user), scene_id))
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

@router.post('', response_model=SceneOut, status_code=status.HTTP_201_CREATED)
async def post_scene(body: SceneWrite, background_tasks: BackgroundTasks, db_path=Depends(get_household_service), user: dict=Depends(require_admin)) -> SceneOut:
    try:
        row = db_path.create_scene(_home_id(user), name=body.name, voice_keyword=body.voice_keyword, created_by=str(user.get('id') or ''), is_enabled=body.is_enabled, steps=[s.model_dump() for s in body.steps])
    except (LookupError, ValueError) as exc:
        raise _map_write_error(exc) from exc
    return SceneOut.model_validate(row)

@router.put('/{scene_id}', response_model=SceneOut)
async def put_scene(scene_id: str, body: SceneWrite, background_tasks: BackgroundTasks, db_path=Depends(get_household_service), user: dict=Depends(require_admin)) -> SceneOut:
    try:
        row = db_path.update_scene(_home_id(user), scene_id, name=body.name, voice_keyword=body.voice_keyword, is_enabled=body.is_enabled, steps=[s.model_dump() for s in body.steps])
    except (LookupError, ValueError) as exc:
        raise _map_write_error(exc) from exc
    return SceneOut.model_validate(row)

@router.delete('/{scene_id}', status_code=status.HTTP_204_NO_CONTENT)
async def remove_scene(scene_id: str, background_tasks: BackgroundTasks, db_path=Depends(get_household_service), user: dict=Depends(require_admin)) -> None:
    try:
        db_path.delete_scene(_home_id(user), scene_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
