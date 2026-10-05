import asyncio

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect

from homate.modules.home.application.devices import DeviceNotFoundError, InvalidDeviceActionError
from homate.modules.home.domain.device import Device, DeviceActionRequest, DeviceActionResponse
from homate.infrastructure.realtime import notify_device_updated
from homate.presentation.dependencies import get_current_user, get_device_store, get_ws_manager, get_household_service, authenticated_user

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])
ws_router = APIRouter(tags=["realtime"])


@router.get("/home")
def home(service=Depends(get_household_service)):
    return service.load_home()


@router.get("/status")
def status():
    return {"status": "ready", "ai_enabled": False}


@router.get("/devices", response_model=list[Device])
def devices(store=Depends(get_device_store), user=Depends(get_current_user)):
    return store.list()


@router.get("/devices/{identifier}", response_model=Device)
def device(identifier: str, store=Depends(get_device_store), user=Depends(get_current_user)):
    try: return store.get(identifier)
    except DeviceNotFoundError as error: raise HTTPException(404, str(error)) from error


@router.post("/devices/{identifier}/actions", response_model=DeviceActionResponse)
async def action(identifier: str, body: DeviceActionRequest, store=Depends(get_device_store), manager=Depends(get_ws_manager), service=Depends(get_household_service), user=Depends(get_current_user)):
    try: result = store.apply_action(identifier, body.key, body.value)
    except DeviceNotFoundError as error: raise HTTPException(404, str(error)) from error
    except InvalidDeviceActionError as error: raise HTTPException(400, str(error)) from error
    await notify_device_updated(manager, result.device)
    service.append_command_log(user['home_id'], utterance=f"{result.device.name}: {body.key} → {result.new_value}", intent="manual_control", result="success", user_id=user['id'], actions=[{"device_id": identifier, "action": body.key, "parameters": {"value": result.new_value}}])
    return result


@ws_router.websocket("/ws/devices")
async def device_socket(socket: WebSocket):
    token = socket.query_params.get("token", "")
    try: authenticated_user(token, socket.app.state.household_service)
    except HTTPException:
        await socket.close(code=4401)
        return
    manager = socket.app.state.ws_manager
    await manager.connect(socket)
    try:
        await manager.send_json(socket, {"type": "snapshot", "devices": [d.model_dump(mode="json") for d in socket.app.state.device_store.list()]})
        while True:
            try:
                message = await asyncio.wait_for(socket.receive_json(), timeout=30)
            except asyncio.TimeoutError:
                message = {"type": "ping"}
            if message.get("type") == "ping": await manager.send_json(socket, {"type": "ping"})
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(socket)


@router.post("/chat")
@router.post("/clarify")
def ai_pending(user=Depends(get_current_user)):
    raise HTTPException(503, "Trợ lý AI sẽ được tích hợp ở giai đoạn tiếp theo.")
