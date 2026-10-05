"""Energy reporting endpoints for dashboard, room, device and report screens."""
from __future__ import annotations
from datetime import date
from typing import Any, Literal
from fastapi import APIRouter, Depends, Query, Request
from homate.presentation.dependencies import get_current_user
from homate.modules.energy.application.service import EnergyService
router = APIRouter(prefix='/api/dashboard/energy', tags=['energy'])

def get_energy_service(request: Request) -> EnergyService:
    return request.app.state.energy_service

@router.get('')
async def energy_report(period: Literal['today', '7days', '30days', '3months', 'week', 'month', 'year']='today', room_id: str | None=Query(default=None), device_id: str | None=Query(default=None), anchor: date | None=Query(default=None), service: EnergyService=Depends(get_energy_service), _user: dict[str, Any]=Depends(get_current_user)) -> dict:
    return service.report(period=period, room_id=room_id, device_id=device_id, anchor=anchor)
