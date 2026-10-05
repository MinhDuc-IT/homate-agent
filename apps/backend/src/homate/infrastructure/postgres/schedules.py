"""Durable schedule CRUD, recurrence calculation, and execution worker."""
from __future__ import annotations
import asyncio
import json
import logging
import uuid
from datetime import UTC, datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo
from homate.modules.home.domain.actions import resolve_turn_on_off
from homate.modules.home.domain.actions import action_writes
from homate.modules.home.application.devices import DeviceStore
from homate.infrastructure.postgres.household import connect, get_scene
logger = logging.getLogger(__name__)

def _now() -> datetime:
    return datetime.now(UTC)

class ScheduleService:

    def __init__(self, db_path: str, store: DeviceStore | None=None) -> None:
        self.db_path = db_path
        self.store = store
        self._execution_events: list[dict[str, Any]] = []

    def drain_execution_events(self) -> list[dict[str, Any]]:
        events, self._execution_events = (self._execution_events, [])
        return events

    @staticmethod
    def _row(row) -> dict[str, Any]:
        result = dict(row)
        result['enabled'] = bool(result['enabled'])
        result['parameters'] = json.loads(result.get('parameters') or '{}')
        result['recurrence_rule'] = json.loads(result.get('recurrence_rule') or 'null')
        return result

    def list(self, home_id: str, *, room_id: str | None=None, scene_id: str | None=None, include_finished: bool=False) -> list[dict[str, Any]]:
        conn = connect(self.db_path)
        try:
            filters = ['s.home_id=%s', "s.status!='deleted'"]
            args: list[Any] = [home_id]
            if not include_finished:
                filters.append("s.status IN ('active','paused')")
            if room_id:
                filters.append('d.room_id=%s')
                args.append(room_id)
            if scene_id:
                filters.append('s.scene_id=%s')
                args.append(scene_id)
            rows = conn.execute(f"SELECT s.*, d.name device_name, d.room_id, sc.name scene_name\n                    FROM schedules s\n                    LEFT JOIN devices d ON d.id=s.device_id\n                    LEFT JOIN scenes sc ON sc.id=s.scene_id\n                    WHERE {' AND '.join(filters)}\n                    ORDER BY s.enabled DESC, s.next_run_at, s.name", args).fetchall()
            return [self._row(row) for row in rows]
        finally:
            conn.close()

    def get(self, home_id: str, schedule_id: str) -> dict[str, Any]:
        items = [item for item in self.list(home_id, include_finished=True) if item['id'] == schedule_id]
        if not items:
            raise LookupError('Không tìm thấy lịch tự động')
        return items[0]

    def create(self, home_id: str, created_by: str, data: dict[str, Any]) -> dict[str, Any]:
        schedule_id = str(uuid.uuid4())
        next_run = calculate_next_run(**{k: data.get(k) for k in ('schedule_type', 'timezone', 'run_at', 'recurrence_rule')})
        if next_run is None:
            raise ValueError('Không xác định được lần chạy tiếp theo')
        now = _now().isoformat()
        conn = connect(self.db_path)
        try:
            conn.execute("""INSERT INTO schedules
                   (id,home_id,name,schedule_type,target_type,device_id,action,parameters,scene_id,
                    timezone,run_at,recurrence_rule,next_run_at,enabled,created_by,created_at,updated_at,status)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", (schedule_id, home_id, data['name'], data['schedule_type'], data['target_type'], data.get('device_id'), data.get('action'), json.dumps(data.get('parameters') or {}, ensure_ascii=False), data.get('scene_id'), data['timezone'], data.get('run_at'), json.dumps(data.get('recurrence_rule'), ensure_ascii=False), next_run.isoformat(), int(bool(data.get('enabled', True))), created_by, now, now, 'active' if data.get('enabled', True) else 'paused'))
            conn.commit()
        finally:
            conn.close()
        return self.get(home_id, schedule_id)

    def update(self, home_id: str, schedule_id: str, data: dict[str, Any]) -> dict[str, Any]:
        current = self.get(home_id, schedule_id)
        if current['schedule_type'] == 'once' and current['status'] in {'completed', 'failed'} and (data.get('enabled') is True):
            raise ValueError('Lịch một lần đã kết thúc, không thể bật lại; hãy tạo lịch mới')
        merged = {**current, **data}
        next_run = calculate_next_run(**{k: merged.get(k) for k in ('schedule_type', 'timezone', 'run_at', 'recurrence_rule')})
        fields = {k: merged.get(k) for k in ('name', 'schedule_type', 'target_type', 'device_id', 'action', 'scene_id', 'timezone', 'run_at')}
        fields['parameters'] = json.dumps(merged.get('parameters') or {}, ensure_ascii=False)
        fields['recurrence_rule'] = json.dumps(merged.get('recurrence_rule'), ensure_ascii=False)
        fields['enabled'] = int(bool(merged.get('enabled', True)))
        fields['status'] = 'active' if fields['enabled'] else 'paused'
        fields['next_run_at'] = next_run.isoformat() if next_run and fields['enabled'] else None
        fields['updated_at'] = _now().isoformat()
        conn = connect(self.db_path)
        try:
            conn.execute(f"UPDATE schedules SET {', '.join((f'{key}=%s' for key in fields))} WHERE id=%s AND home_id=%s", (*fields.values(), schedule_id, home_id))
            conn.commit()
        finally:
            conn.close()
        return self.get(home_id, schedule_id)

    def delete(self, home_id: str, schedule_id: str) -> None:
        self.get(home_id, schedule_id)
        conn = connect(self.db_path)
        try:
            now = _now().isoformat()
            conn.execute("UPDATE schedules SET enabled=0,status='deleted',deleted_at=%s,updated_at=%s WHERE id=%s AND home_id=%s", (now, now, schedule_id, home_id))
            conn.commit()
        finally:
            conn.close()

    def runs(self, home_id: str, schedule_id: str, limit: int=50) -> list[dict[str, Any]]:
        self.get(home_id, schedule_id)
        conn = connect(self.db_path)
        try:
            return [dict(row) for row in conn.execute("""SELECT r.* FROM schedule_runs r JOIN schedules s ON s.id=r.schedule_id
                   WHERE r.schedule_id=%s AND s.home_id=%s ORDER BY r.scheduled_at DESC LIMIT %s""", (schedule_id, home_id, limit)).fetchall()]
        finally:
            conn.close()

    def _apply_action(self, device_id: str, action: str, parameters: dict[str, Any]) -> dict[str, Any]:
        if self.store is None:
            raise RuntimeError('Device store is unavailable')
        for key, value in action_writes(self.store.get(device_id), action, parameters):
            result = self.store.apply_action(device_id, key, value)
        return {'device_id': device_id, 'action': action, 'state': result.device.state}

    def execute_due(self, now: datetime | None=None) -> int:
        now = now or _now()
        conn = connect(self.db_path)
        try:
            due = conn.execute("SELECT * FROM schedules WHERE enabled=1 AND status='active' AND next_run_at<=%s ORDER BY next_run_at LIMIT 20", (now.isoformat(),)).fetchall()
        finally:
            conn.close()
        completed = 0
        for row in due:
            scheduled_at = row['next_run_at']
            run_id = str(uuid.uuid4())
            conn = connect(self.db_path)
            try:
                try:
                    conn.execute("INSERT INTO schedule_runs(id,schedule_id,scheduled_at,started_at,status) VALUES(%s,%s,%s,%s, 'running')", (run_id, row['id'], scheduled_at, now.isoformat()))
                    conn.commit()
                except Exception:
                    continue
            finally:
                conn.close()
            try:
                if row['target_type'] == 'scene':
                    scene = get_scene(self.db_path, row['home_id'], row['scene_id'])
                    if not scene['is_enabled']:
                        raise ValueError('Kịch bản đã bị tắt')
                    result = [self._apply_action(step['device_id'], step['action'], step['parameters']) for step in scene['steps']]
                else:
                    result = self._apply_action(row['device_id'], row['action'], json.loads(row['parameters'] or '{}'))
                run_status, error = ('success', None)
            except Exception as exc:
                logger.exception('schedule execution failed id=%s', row['id'])
                result, run_status, error = (None, 'failed', str(exc))
            next_run = calculate_next_run(schedule_type=row['schedule_type'], timezone=row['timezone'], run_at=row['run_at'], recurrence_rule=json.loads(row['recurrence_rule'] or 'null'), after=now) if row['schedule_type'] == 'recurring' else None
            status_value = 'active' if next_run else 'completed' if run_status == 'success' else 'failed'
            conn = connect(self.db_path)
            try:
                conn.execute('UPDATE schedule_runs SET finished_at=%s,status=%s,result=%s,error_message=%s WHERE id=%s', (now.isoformat(), run_status, json.dumps(result, ensure_ascii=False), error, run_id))
                conn.execute('UPDATE schedules SET last_run_at=%s,next_run_at=%s,status=%s,enabled=%s WHERE id=%s', (scheduled_at, next_run.isoformat() if next_run else None, status_value, int(next_run is not None), row['id']))
                conn.commit()
            finally:
                conn.close()
            completed += 1
            device_results = result if isinstance(result, list) else [result] if isinstance(result, dict) else []
            self._execution_events.append({'type': 'schedule.executed', 'schedule_id': row['id'], 'schedule_name': row['name'], 'status': run_status, 'scheduled_at': scheduled_at, 'finished_at': now.isoformat(), 'error_message': error, 'devices': device_results})
        return completed

async def schedule_worker(service: ScheduleService, ws_manager=None, interval_seconds: int=15) -> None:
    while True:
        try:
            service.execute_due()
            for event in service.drain_execution_events():
                if ws_manager is not None:
                    for device in event.get('devices', []):
                        await ws_manager.broadcast_json({'type': 'device.updated', 'device_id': device['device_id'], 'state': device['state'], 'ts': event['finished_at']})
                    await ws_manager.broadcast_json(event)
        except Exception:
            logger.exception('schedule worker tick failed')
        await asyncio.sleep(interval_seconds)

from homate.modules.automation.domain.recurrence import calculate_next_run
