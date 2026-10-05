from fastapi import HTTPException

from homate.application.household import HOME_ID
from homate.modules.home.application.pending import pending_ambient
from homate.modules.home.domain.actions import resolve_turn_on_off
from homate.infrastructure.realtime import notify_device_updated


async def execute_ambient_decision(request_id, approved, *, db_path, store, ws_manager):
    pending = pending_ambient.pop(request_id)
    if pending is None: raise HTTPException(410, "Yêu cầu đã hết hạn hoặc đã được xử lý.")
    if not approved: return {"ok": True, "status": "rejected", "executed": False, "device_ids": []}
    room = next((r for r in db_path.load_rooms_ambient(HOME_ID) if r["id"] == pending.room_id), None)
    if not room or room["occupied"]: raise HTTPException(409, "Phòng hiện đã có người; không thiết bị nào được tắt.")
    executed = []
    for identifier in pending.device_ids:
        device = store.get(identifier)
        if device.room != pending.room_id or device.state.get("power") is not True: continue
        action = resolve_turn_on_off(device, "turn_off")
        if action:
            result = store.apply_action(identifier, *action)
            await notify_device_updated(ws_manager, result.device)
            executed.append(identifier)
    return {"ok": True, "status": "executed", "executed": bool(executed), "device_ids": executed}
