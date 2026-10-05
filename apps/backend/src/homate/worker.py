import asyncio
import logging
from datetime import datetime, timezone

from homate.application.household import HOME_ID
from homate.modules.home.application.ambient import cooldown_active, devices_on_in_room, vacant_minutes
from homate.modules.home.application.pending import pending_ambient

logger = logging.getLogger(__name__)


async def schedule_worker(service, manager):
    while True:
        try:
            service.execute_due()
            for event in service.drain_execution_events():
                for device in event["devices"]:
                    await manager.broadcast_json({"type": "device.updated", "device_id": device["device_id"], "state": device["state"], "ts": event["finished_at"]})
                await manager.broadcast_json(event)
        except Exception: logger.exception("Schedule worker failed")
        await asyncio.sleep(5)


async def energy_worker(service, devices, interval):
    last_day = None
    while True:
        try:
            service.record_all(devices.list())
            today = datetime.now(timezone.utc).date()
            if today != last_day:
                service.aggregate_daily_and_cleanup()
                last_day = today
        except Exception: logger.exception("Energy worker failed")
        await asyncio.sleep(interval)


async def ambient_worker(service, devices, manager, settings):
    while True:
        try:
            for room in service.load_rooms_ambient(HOME_ID):
                minutes = vacant_minutes(room["occupancy_changed_at"])
                identifiers = devices_on_in_room(devices, room["id"])
                if room["occupied"] or minutes < settings.occupancy_vacant_minutes or not identifiers: continue
                if cooldown_active(room["last_suggested_at"], settings.occupancy_cooldown_minutes): continue
                message = f"{room['label']} đã trống {minutes} phút. Bạn có muốn tắt các thiết bị đang bật không?"
                pending = pending_ambient.create(room_id=room["id"], room_label=room["label"], device_ids=identifiers, message=message)
                service.repository.mark_room_suggested(HOME_ID, room["id"])
                await manager.broadcast_json({"type": "ambient.suggestion", "session_id": f"ambient-{room['id']}", "request_id": pending.request_id, "expires_in_seconds": 60, "room": room["id"], "room_label": room["label"], "vacant_minutes": minutes, "message": message, "audio_format": "", "audio_base64": "", "actions": [{"device_id": d, "action": "turn_off"} for d in identifiers]})
        except Exception: logger.exception("Ambient worker failed")
        await asyncio.sleep(settings.occupancy_watchdog_interval_seconds)
