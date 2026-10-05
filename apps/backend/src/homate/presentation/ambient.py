"""Visual UI ambient context — weather snapshot + room occupancy mock tab."""
from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from homate.presentation.ambient_decision import execute_ambient_decision
from homate.modules.home.application.ambient import build_ambient_snapshot
from homate.infrastructure.weather import WeatherCache
from homate.presentation.dependencies import get_current_user, require_admin
from homate.config import get_settings
from homate.modules.home.application.devices import DeviceStore
from homate.presentation.dependencies import get_device_store, get_household_service
from homate.modules.home.domain.ambient import AmbientSnapshot, RoomMockPatch
router = APIRouter(prefix='/api/dashboard', tags=['ambient'])

class AmbientSuggestionDecision(BaseModel):
    approved: bool

def get_weather_cache(request: Request) -> WeatherCache:
    cache = getattr(request.app.state, 'weather_cache', None)
    if cache is None:
        raise RuntimeError('WeatherCache is not initialized (check app lifespan)')
    return cache

async def _snapshot(db_path, store: DeviceStore, weather: WeatherCache) -> AmbientSnapshot:
    settings = get_settings()
    rooms = db_path.load_rooms_ambient(HOME_ID)
    weather_snapshot = await weather.get() if settings.weather_api_key else None
    return build_ambient_snapshot(rooms=rooms, store=store, weather=weather_snapshot, tz_name='Asia/Ho_Chi_Minh')

@router.get('/ambient', response_model=AmbientSnapshot)
async def get_ambient(store: DeviceStore=Depends(get_device_store), db_path=Depends(get_household_service), weather: WeatherCache=Depends(get_weather_cache), _user: dict[str, Any]=Depends(get_current_user)) -> AmbientSnapshot:
    return await _snapshot(db_path, store, weather)

@router.patch('/rooms/{room_id}/mock', response_model=AmbientSnapshot)
async def patch_room_mock(room_id: str, body: RoomMockPatch, store: DeviceStore=Depends(get_device_store), db_path=Depends(get_household_service), weather: WeatherCache=Depends(get_weather_cache), _user: dict[str, Any]=Depends(require_admin)) -> AmbientSnapshot:
    try:
        db_path.set_room_mock(HOME_ID, room_id, occupied=body.occupied, indoor_temp_c=body.indoor_temp_c, indoor_humidity=body.indoor_humidity, vacant_minutes=body.vacant_minutes)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return await _snapshot(db_path, store, weather)

@router.post('/ambient/suggestions/{request_id}/respond')
async def respond_to_ambient_suggestion(request_id: str, body: AmbientSuggestionDecision, request: Request, store: DeviceStore=Depends(get_device_store), db_path=Depends(get_household_service), _user: dict[str, Any]=Depends(get_current_user)) -> dict[str, Any]:
    """Consume a one-shot occupancy suggestion and act only after approval."""
    return await execute_ambient_decision(request_id, body.approved, db_path=db_path, store=store, ws_manager=request.app.state.ws_manager)
from homate.application.household import HOME_ID
