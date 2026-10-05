"""PostgreSQL file store — schema + seed for Michelin Bois."""
from __future__ import annotations
import hashlib
import hmac
import json
import logging
import math
import secrets
import psycopg
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from homate.modules.home.domain.defaults import default_devices
from homate.infrastructure.postgres.connection import connect
from homate.modules.identity.domain.security import hash_pin, verify_pin
from homate.modules.home.domain.device import Device
logger = logging.getLogger(__name__)
HOME_ID = 'home-michelin-bois'
DEFAULT_PIN = '1234'
_LOCK = threading.RLock()
KIND_TO_TYPE: dict[str, str] = {'bulb': 'light', 'snowflake': 'ac', 'flame': 'heater', 'lock': 'lock', 'curtain': 'curtain', 'speaker': 'speaker', 'tv': 'tv', 'fan': 'fan', 'plug': 'plug', 'camera': 'camera', 'droplet': 'water_heater'}
EXTRA_ALIASES: dict[str, list[str]] = {'light-living': ['đèn phòng khách', 'den phong khach'], 'ac-living': ['điều hòa phòng khách', 'máy lạnh phòng khách'], 'speaker-living': ['loa phòng khách', 'loa'], 'curtain': ['rèm', 'rèm cửa', 'rèm phòng ngủ', 'kéo rèm'], 'door': ['cửa', 'cửa chính', 'khóa cửa', 'đóng khóa', 'mở khóa'], 'light-bed': ['đèn phòng ngủ'], 'ac-bed': ['điều hòa phòng ngủ'], 'heater-living': ['lò sưởi', 'máy sưởi', 'lò sưởi phòng khách', 'máy sưởi phòng khách']}

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def get_user(path: str, user_id: str) -> dict[str, Any] | None:
    with _LOCK:
        conn = connect(path)
        try:
            row = conn.execute("""
                SELECT id, home_id, display_name, initial, role, email, phone,
                       pin_hash, is_active
                FROM users WHERE id = %s
                """, (user_id,)).fetchone()
        finally:
            conn.close()
    if row is None:
        return None
    return {'id': row['id'], 'home_id': row['home_id'], 'name': row['display_name'], 'initial': row['initial'], 'role': row['role'], 'email': row['email'], 'phone': row['phone'], 'pin_hash': row['pin_hash'], 'is_active': bool(row['is_active'])}

def list_users(path: str, home_id: str) -> list[dict[str, Any]]:
    with _LOCK:
        conn = connect(path)
        try:
            rows = conn.execute("""SELECT id, display_name, initial, role, email, phone, is_active
                   FROM users WHERE home_id = %s AND is_active = 1
                   ORDER BY CASE role WHEN 'admin' THEN 0 ELSE 1 END, display_name""", (home_id,)).fetchall()
        finally:
            conn.close()
    return [{'id': row['id'], 'name': row['display_name'], 'initial': row['initial'], 'role': row['role'], 'email': row['email'], 'phone': row['phone'], 'is_active': bool(row['is_active'])} for row in rows]

def create_user(path: str, home_id: str, data: dict[str, Any]) -> dict[str, Any]:
    user_id = f'user-{uuid.uuid4().hex[:12]}'
    name = str(data['name']).strip()
    initial = str(data.get('initial') or name[:1]).strip()[:3].upper()
    now = _now()
    with _LOCK:
        conn = connect(path)
        try:
            conn.execute("""INSERT INTO users
                   (id, home_id, display_name, initial, role, email, phone,
                    pin_hash, is_active, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1, %s, %s)""", (user_id, home_id, name, initial, data['role'], data.get('email'), data.get('phone'), hash_pin(data['pin']), now, now))
            conn.commit()
        finally:
            conn.close()
    return get_user(path, user_id) or {}

def update_user(path: str, home_id: str, user_id: str, data: dict[str, Any]) -> dict[str, Any]:
    with _LOCK:
        conn = connect(path)
        try:
            current = conn.execute('SELECT id, role FROM users WHERE id=%s AND home_id=%s AND is_active=1', (user_id, home_id)).fetchone()
            if current is None:
                raise LookupError('Không tìm thấy thành viên')
            if current['role'] == 'admin' and data.get('role') == 'member':
                admins = conn.execute("SELECT COUNT(*) n FROM users WHERE home_id=%s AND role='admin' AND is_active=1", (home_id,)).fetchone()['n']
                if admins <= 1:
                    raise ValueError('Ngôi nhà phải có ít nhất một quản trị viên')
            field_map = {'name': 'display_name', 'initial': 'initial', 'role': 'role', 'email': 'email', 'phone': 'phone'}
            updates = {field_map[key]: value for key, value in data.items() if key in field_map}
            if 'name' in data and 'initial' not in data:
                updates['initial'] = str(data['name']).strip()[:1].upper()
            if data.get('pin'):
                updates['pin_hash'] = hash_pin(data['pin'])
            updates['updated_at'] = _now()
            set_clause = ', '.join((f'{key}=%s' for key in updates))
            conn.execute(f'UPDATE users SET {set_clause} WHERE id=%s AND home_id=%s', (*updates.values(), user_id, home_id))
            conn.commit()
        finally:
            conn.close()
    return get_user(path, user_id) or {}

def deactivate_user(path: str, home_id: str, user_id: str) -> None:
    with _LOCK:
        conn = connect(path)
        try:
            row = conn.execute('SELECT role FROM users WHERE id=%s AND home_id=%s AND is_active=1', (user_id, home_id)).fetchone()
            if row is None:
                raise LookupError('Không tìm thấy thành viên')
            if row['role'] == 'admin':
                admins = conn.execute("SELECT COUNT(*) n FROM users WHERE home_id=%s AND role='admin' AND is_active=1", (home_id,)).fetchone()['n']
                if admins <= 1:
                    raise ValueError('Không thể xóa quản trị viên cuối cùng')
            conn.execute('UPDATE users SET is_active=0, updated_at=%s WHERE id=%s AND home_id=%s', (_now(), user_id, home_id))
            conn.execute('UPDATE sessions SET revoked_at=%s WHERE user_id=%s AND revoked_at IS NULL', (_now(), user_id))
            conn.commit()
        finally:
            conn.close()
ROOM_AMBIENT_COLUMNS: dict[str, str] = {'occupied': 'INTEGER NOT NULL DEFAULT 1', 'occupancy_changed_at': 'TEXT', 'indoor_temp_c': 'REAL', 'indoor_humidity': 'REAL DEFAULT 55.0', 'last_suggested_at': 'TEXT'}
USER_PROFILE_COLUMNS: dict[str, str] = {'email': 'TEXT', 'phone': 'TEXT'}

def _ensure_energy_defaults(conn: psycopg.Connection) -> None:
    """Create conservative estimated-power profiles for every catalog device."""
    now = _now()
    conn.execute("""
        INSERT INTO device_energy_profiles
            (device_id, model_type, rated_power_w, standby_power_w, parameters,
             enabled, created_at, updated_at)
        SELECT id,
               CASE
                   WHEN kind = 'bulb' THEN 'brightness_linear'
                   WHEN kind = 'fan' THEN 'speed_levels'
                   WHEN kind IN ('snowflake', 'flame', 'droplet') THEN 'duty_cycle'
                   WHEN kind IN ('curtain', 'lock') THEN 'motor_event'
                   ELSE 'constant'
               END,
               CASE kind
                   WHEN 'bulb' THEN 12 WHEN 'snowflake' THEN 1200
                   WHEN 'flame' THEN 1800 WHEN 'droplet' THEN 2500
                   WHEN 'fan' THEN 55 WHEN 'tv' THEN 100
                   WHEN 'speaker' THEN 20 WHEN 'plug' THEN 60
                   WHEN 'camera' THEN 8 WHEN 'curtain' THEN 80
                   WHEN 'lock' THEN 5 ELSE 25
               END,
               CASE kind
                   WHEN 'tv' THEN 1 WHEN 'speaker' THEN 1
                   WHEN 'camera' THEN 8 WHEN 'plug' THEN 0.5
                   ELSE 0
               END,
               CASE
                   WHEN kind = 'fan' THEN '{"speed_power_w":{"0":0,"1":18,"2":35,"3":55}}'
                   WHEN kind = 'snowflake' THEN '{"duty_cycle":0.65}'
                   WHEN kind IN ('flame', 'droplet') THEN '{"duty_cycle":0.75}'
                   WHEN kind IN ('curtain', 'lock') THEN '{"event_seconds":8}'
                   ELSE '{}'
               END::jsonb,
               1, %s, %s
        FROM devices ON CONFLICT DO NOTHING""", (now, now))
    conn.execute("""
        INSERT INTO electricity_tariffs
            (id, home_id, name, pricing_type, currency, config, valid_from,
             is_active, created_at, updated_at)
        SELECT 'default-flat-' || id, id, 'Giá điện ước tính', 'flat', 'VND',
               '{"price_per_kwh":2500,"vat_rate":0.1}',
               '2020-01-01T00:00:00+00:00', 1, %s, %s
        FROM homes ON CONFLICT DO NOTHING""", (now, now))
    _seed_energy_demo(conn)

def _seed_energy_demo(conn: psycopg.Connection) -> None:
    """Seed 30 rolling days once so energy dashboards are useful immediately."""
    marker = conn.execute("SELECT 1 FROM settings WHERE home_id=%s AND key='energy.demo_seeded'", (HOME_ID,)).fetchone()
    if marker is not None:
        return
    devices = conn.execute("""SELECT d.id, d.room_id, d.kind, p.rated_power_w
           FROM devices d JOIN device_energy_profiles p ON p.device_id=d.id
           WHERE d.home_id=%s AND p.enabled=1""", (HOME_ID,)).fetchall()
    end = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start = end - timedelta(days=30)
    now_text = _now()

    def utilization(kind: str, hour: int, day_index: int) -> float:
        day_wave = 0.9 + 0.12 * math.sin(day_index * 1.7)
        schedules = {'bulb': 0.55 if hour >= 18 or hour < 6 else 0.04, 'snowflake': 0.5 if 10 <= hour < 22 else 0.12, 'flame': 0.08 if hour < 7 or hour >= 21 else 0.01, 'droplet': 0.32 if hour in {6, 7, 19, 20} else 0.025, 'fan': 0.34 if 11 <= hour < 23 else 0.08, 'tv': 0.48 if 18 <= hour < 23 else 0.025, 'speaker': 0.22 if 7 <= hour < 10 or 18 <= hour < 22 else 0.02, 'plug': 0.28 if 8 <= hour < 23 else 0.09, 'camera': 1.0, 'curtain': 8 / 3600 if hour in {6, 18} else 0.0, 'lock': 4 / 3600 if hour in {7, 19} else 0.0}
        return max(0.0, schedules.get(kind, 0.1) * day_wave)
    hourly_rows: list[tuple] = []
    cursor = start
    while cursor < end:
        local = cursor + timedelta(hours=7)
        day_index = (cursor - start).days
        for device in devices:
            energy_wh = float(device['rated_power_w']) * utilization(device['kind'], local.hour, day_index)
            hourly_rows.append((HOME_ID, device['id'], device['room_id'], cursor.isoformat(), energy_wh, energy_wh, 1, now_text))
        cursor += timedelta(hours=1)
    conn.executemany("""INSERT INTO energy_hourly
           (home_id, device_id, room_id, bucket_start, energy_wh, measured_wh,
            estimated_wh, sample_count, coverage_ratio, updated_at)
           VALUES (%s, %s, %s, %s, %s, 0, %s, %s, 1, %s) ON CONFLICT DO NOTHING""", hourly_rows)
    conn.execute("""INSERT INTO settings(home_id, key, value, updated_at)
           VALUES (%s, 'energy.demo_seeded', 'true', %s)
           ON CONFLICT(home_id, key) DO UPDATE SET value='true', updated_at=excluded.updated_at""", (HOME_ID, now_text))

def init_and_seed(path: str) -> None:
    with _LOCK:
        conn = connect(path)
        try:
            conn.execute('SELECT pg_advisory_xact_lock(726072)')
            conn.execute("""UPDATE users SET
                       email=COALESCE(email, 'minh.nguyen@homemate.vn'),
                       phone=COALESCE(phone, '+84 912 345 678')
                   WHERE id='minh-duc'""")
            existing = conn.execute('SELECT COUNT(*) AS n FROM homes').fetchone()['n']
            if existing:
                added = _insert_missing_devices(conn)
                conflicts_added = _insert_missing_conflicts(conn)
                _ensure_energy_defaults(conn)
                conn.commit()
                if added or conflicts_added:
                    logger.info('[POSTGRES] added %s devices and %s conflicts', added, conflicts_added)
                else:
                    logger.info('[POSTGRES] already seeded (%s home rows)', existing)
                return
            _seed(conn)
            _ensure_energy_defaults(conn)
            conn.commit()
            logger.info('[POSTGRES] seeded Michelin Bois')
        except psycopg.IntegrityError:
            conn.rollback()
            logger.info('[POSTGRES] seed skipped, another writer already filled the database')
        finally:
            conn.close()

def load_devices(path: str) -> list[Device]:
    with _LOCK:
        conn = connect(path)
        try:
            rows = conn.execute('SELECT id, name, room_id, kind, state, capabilities FROM devices ORDER BY id').fetchall()
        finally:
            conn.close()
    devices: list[Device] = []
    for row in rows:
        devices.append(Device.model_validate({'id': row['id'], 'name': row['name'], 'room': row['room_id'], 'kind': row['kind'], 'state': json.loads(row['state']), 'controls': json.loads(row['capabilities'])}))
    return devices

def load_device_aliases(path: str) -> dict[str, list[str]]:
    with _LOCK:
        conn = connect(path)
        try:
            rows = conn.execute('SELECT device_id, alias FROM device_aliases ORDER BY device_id, alias').fetchall()
        finally:
            conn.close()
    aliases: dict[str, list[str]] = {}
    for row in rows:
        aliases.setdefault(row['device_id'], []).append(row['alias'])
    return aliases

def load_device_conflicts(path: str) -> dict[str, list[dict[str, str]]]:
    """Map device_id → list of {device_id, scope, on_conflict} peers."""
    with _LOCK:
        conn = connect(path)
        try:
            rows = conn.execute("""
                SELECT device_id, conflicts_with, scope, on_conflict
                FROM device_conflicts
                ORDER BY device_id, conflicts_with
                """).fetchall()
        except psycopg.ProgrammingError:
            return {}
        finally:
            conn.close()
    out: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        out.setdefault(row['device_id'], []).append({'device_id': row['conflicts_with'], 'scope': row['scope'], 'on_conflict': row['on_conflict']})
    return out

def load_rooms(path: str) -> dict[str, str]:
    with _LOCK:
        conn = connect(path)
        try:
            rows = conn.execute('SELECT id, label FROM rooms ORDER BY sort_order, label').fetchall()
        finally:
            conn.close()
    return {row['id']: row['label'] for row in rows}

def load_rooms_ambient(path: str, home_id: str) -> list[dict[str, Any]]:
    """Rooms with their mocked occupancy/temperature state, sort_order first."""
    with _LOCK:
        conn = connect(path)
        try:
            rows = conn.execute("""
                SELECT id, label, occupied, occupancy_changed_at, indoor_temp_c,
                       indoor_humidity, last_suggested_at
                FROM rooms
                WHERE home_id = %s
                ORDER BY sort_order, label
                """, (home_id,)).fetchall()
        finally:
            conn.close()
    return [{'id': row['id'], 'label': row['label'], 'occupied': bool(row['occupied']), 'occupancy_changed_at': row['occupancy_changed_at'], 'indoor_temp_c': row['indoor_temp_c'], 'indoor_humidity': row['indoor_humidity'], 'last_suggested_at': row['last_suggested_at']} for row in rows]

def set_room_mock(path: str, home_id: str, room_id: str, *, occupied: bool | None=None, indoor_temp_c: float | None=None, indoor_humidity: float | None=None, vacant_minutes: int | None=None) -> dict[str, Any]:
    """Update the tab-mock fields for one room. `vacant_minutes` backdates
    occupancy_changed_at so demos don't have to wait out the real threshold."""
    now = datetime.now(timezone.utc)
    with _LOCK:
        conn = connect(path)
        try:
            row = conn.execute('SELECT id, occupied FROM rooms WHERE id = %s AND home_id = %s', (room_id, home_id)).fetchone()
            if row is None:
                raise LookupError(f'Không tìm thấy phòng {room_id}')
            updates: dict[str, Any] = {}
            if occupied is not None:
                if bool(row['occupied']) != occupied:
                    updates['occupied'] = int(occupied)
                    updates['occupancy_changed_at'] = now.isoformat()
                else:
                    updates['occupied'] = int(occupied)
            if indoor_temp_c is not None:
                updates['indoor_temp_c'] = indoor_temp_c
            if indoor_humidity is not None:
                updates['indoor_humidity'] = indoor_humidity
            if vacant_minutes is not None:
                updates['occupied'] = 0
                updates['occupancy_changed_at'] = (now - timedelta(minutes=vacant_minutes)).isoformat()
                updates['last_suggested_at'] = None
            if updates:
                set_clause = ', '.join((f'{key} = %s' for key in updates))
                conn.execute(f'UPDATE rooms SET {set_clause} WHERE id = %s AND home_id = %s', (*updates.values(), room_id, home_id))
                conn.commit()
        finally:
            conn.close()
    return next((r for r in load_rooms_ambient(path, home_id) if r['id'] == room_id))

def mark_room_suggested(path: str, home_id: str, room_id: str) -> None:
    with _LOCK:
        conn = connect(path)
        try:
            conn.execute('UPDATE rooms SET last_suggested_at = %s WHERE id = %s AND home_id = %s', (_now(), room_id, home_id))
            conn.commit()
        finally:
            conn.close()

def load_home(path: str) -> dict[str, Any]:
    with _LOCK:
        conn = connect(path)
        try:
            home = conn.execute('SELECT id, name, timezone FROM homes LIMIT 1').fetchone()
            if home is None:
                raise LookupError('No home row in PostgreSQL')
            members = conn.execute("""
                SELECT id, display_name, initial, role
                FROM users
                WHERE home_id = %s AND is_active = 1
                ORDER BY CASE role WHEN 'admin' THEN 0 ELSE 1 END, display_name
                """, (home['id'],)).fetchall()
            rooms = conn.execute("""
                SELECT id, label
                FROM rooms
                WHERE home_id = %s
                ORDER BY sort_order, label
                """, (home['id'],)).fetchall()
        finally:
            conn.close()
    return {'id': home['id'], 'name': home['name'], 'timezone': home['timezone'], 'members': [{'id': row['id'], 'name': row['display_name'], 'initial': row['initial'], 'role': row['role']} for row in members], 'rooms': [{'id': row['id'], 'label': row['label']} for row in rooms]}

def _scene_dict(conn: psycopg.Connection, row: dict) -> dict[str, Any]:
    steps = conn.execute("""
        SELECT s.id, s.sort_order, s.device_id, s.action, s.parameters,
               d.name AS device_name, d.kind AS device_kind
        FROM scene_steps s
        JOIN devices d ON d.id = s.device_id
        WHERE s.scene_id = %s
        ORDER BY s.sort_order
        """, (row['id'],)).fetchall()
    return {'id': row['id'], 'name': row['name'], 'voice_keyword': row['voice_keyword'], 'is_enabled': bool(row['is_enabled']), 'steps': [{'id': step['id'], 'sort_order': step['sort_order'], 'device_id': step['device_id'], 'device_name': step['device_name'], 'device_kind': step['device_kind'], 'action': step['action'], 'parameters': json.loads(step['parameters'] or '{}')} for step in steps]}

def list_scenes(path: str, home_id: str) -> list[dict[str, Any]]:
    with _LOCK:
        conn = connect(path)
        try:
            rows = conn.execute("""
                SELECT id, name, voice_keyword, is_enabled
                FROM scenes
                WHERE home_id = %s
                ORDER BY created_at, name
                """, (home_id,)).fetchall()
            return [_scene_dict(conn, row) for row in rows]
        finally:
            conn.close()

def get_scene(path: str, home_id: str, scene_id: str) -> dict[str, Any]:
    with _LOCK:
        conn = connect(path)
        try:
            row = conn.execute("""
                SELECT id, name, voice_keyword, is_enabled
                FROM scenes
                WHERE id = %s AND home_id = %s
                """, (scene_id, home_id)).fetchone()
            if row is None:
                raise LookupError('Không tìm thấy kịch bản')
            return _scene_dict(conn, row)
        finally:
            conn.close()

def _keyword_taken(conn: psycopg.Connection, home_id: str, keyword: str, *, exclude_id: str | None=None) -> bool:
    keyword = keyword.strip()
    if exclude_id is None:
        row = conn.execute("""
            SELECT id FROM scenes
            WHERE home_id = %s AND lower(voice_keyword) = lower(%s)
            """, (home_id, keyword)).fetchone()
    else:
        row = conn.execute("""
            SELECT id FROM scenes
            WHERE home_id = %s AND lower(voice_keyword) = lower(%s) AND id != %s
            """, (home_id, keyword, exclude_id)).fetchone()
    return row is not None
_ACTIVATING_ACTIONS = frozenset({'turn_on', 'set_temperature', 'set_brightness', 'set_volume', 'set_speed', 'set_mode', 'set_fan', 'open', 'unlock', 'start_recording'})

def _is_activating_step(action: str, parameters: dict[str, Any] | None) -> bool:
    if action not in _ACTIVATING_ACTIONS:
        return False
    if action == 'set_speed':
        speed = (parameters or {}).get('speed')
        return isinstance(speed, (int, float)) and speed > 0
    return True

def _scope_applies(scope: str, room_a: str, room_b: str) -> bool:
    if scope in {'explicit', 'same_home'}:
        return True
    return room_a == room_b

def _validate_scene_step_conflicts(conn: psycopg.Connection, home_id: str, steps: list[dict[str, Any]]) -> None:
    """Reject scene steps that activate both sides of a declared device conflict pair."""
    activating: list[tuple[str, str, dict[str, Any]]] = []
    for step in steps:
        device_id = str(step['device_id']).strip()
        action = str(step.get('action') or '').strip()
        params = step.get('parameters') if isinstance(step.get('parameters'), dict) else {}
        if not device_id or not _is_activating_step(action, params):
            continue
        activating.append((device_id, action, params))
    if len(activating) < 2:
        return
    device_ids = {device_id for device_id, _, _ in activating}
    placeholders = ','.join(('%s' for _ in device_ids))
    rows = conn.execute(f'\n        SELECT id, name, room_id FROM devices\n        WHERE home_id = %s AND id IN ({placeholders})\n        ', (home_id, *device_ids)).fetchall()
    devices = {row['id']: row for row in rows}
    try:
        conflict_rows = conn.execute(f'\n            SELECT device_id, conflicts_with, scope\n            FROM device_conflicts\n            WHERE device_id IN ({placeholders})\n            ', tuple(device_ids)).fetchall()
    except psycopg.ProgrammingError:
        return
    active_ids = {device_id for device_id, _, _ in activating}
    for row in conflict_rows:
        left_id = row['device_id']
        right_id = row['conflicts_with']
        if left_id not in active_ids or right_id not in active_ids:
            continue
        left = devices.get(left_id)
        right = devices.get(right_id)
        if left is None or right is None:
            continue
        if not _scope_applies(row['scope'], left['room_id'], right['room_id']):
            continue
        raise ValueError(f"Không thể bật {left['name'].lower()} và {right['name'].lower()} cùng lúc trong một kịch bản.")

def _replace_steps(conn: psycopg.Connection, home_id: str, scene_id: str, steps: list[dict[str, Any]]) -> None:
    _validate_scene_step_conflicts(conn, home_id, steps)
    conn.execute('DELETE FROM scene_steps WHERE scene_id = %s', (scene_id,))
    for order, step in enumerate(steps, start=1):
        device_id = str(step['device_id'])
        owned = conn.execute('SELECT id FROM devices WHERE id = %s AND home_id = %s', (device_id, home_id)).fetchone()
        if owned is None:
            raise ValueError(f'Thiết bị không hợp lệ: {device_id}')
        conn.execute("""
            INSERT INTO scene_steps (id, scene_id, sort_order, device_id, action, parameters)
            VALUES (%s, %s, %s, %s, %s, %s)
            """, (str(uuid.uuid4()), scene_id, order, device_id, str(step['action']).strip(), json.dumps(step.get('parameters') or {}, ensure_ascii=False)))

def create_scene(path: str, home_id: str, *, name: str, voice_keyword: str, created_by: str | None, is_enabled: bool=True, steps: list[dict[str, Any]] | None=None) -> dict[str, Any]:
    scene_id = str(uuid.uuid4())
    now = _now()
    keyword = voice_keyword.strip()
    title = name.strip()
    if not title or not keyword:
        raise ValueError('Tên và từ khóa không được trống')
    with _LOCK:
        conn = connect(path)
        try:
            if _keyword_taken(conn, home_id, keyword):
                raise ValueError('Từ khóa đã được dùng cho kịch bản khác')
            conn.execute("""
                INSERT INTO scenes
                    (id, home_id, name, voice_keyword, is_enabled, created_by, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (scene_id, home_id, title, keyword, int(is_enabled), created_by, now, now))
            _replace_steps(conn, home_id, scene_id, steps or [])
            conn.commit()
            row = conn.execute('SELECT id, name, voice_keyword, is_enabled FROM scenes WHERE id = %s', (scene_id,)).fetchone()
            return _scene_dict(conn, row)
        finally:
            conn.close()

def update_scene(path: str, home_id: str, scene_id: str, *, name: str, voice_keyword: str, is_enabled: bool=True, steps: list[dict[str, Any]] | None=None) -> dict[str, Any]:
    keyword = voice_keyword.strip()
    title = name.strip()
    if not title or not keyword:
        raise ValueError('Tên và từ khóa không được trống')
    with _LOCK:
        conn = connect(path)
        try:
            row = conn.execute('SELECT id FROM scenes WHERE id = %s AND home_id = %s', (scene_id, home_id)).fetchone()
            if row is None:
                raise LookupError('Không tìm thấy kịch bản')
            if _keyword_taken(conn, home_id, keyword, exclude_id=scene_id):
                raise ValueError('Từ khóa đã được dùng cho kịch bản khác')
            conn.execute("""
                UPDATE scenes
                SET name = %s, voice_keyword = %s, is_enabled = %s, updated_at = %s
                WHERE id = %s
                """, (title, keyword, int(is_enabled), _now(), scene_id))
            _replace_steps(conn, home_id, scene_id, steps or [])
            conn.commit()
            updated = conn.execute('SELECT id, name, voice_keyword, is_enabled FROM scenes WHERE id = %s', (scene_id,)).fetchone()
            return _scene_dict(conn, updated)
        finally:
            conn.close()

def delete_scene(path: str, home_id: str, scene_id: str) -> None:
    with _LOCK:
        conn = connect(path)
        try:
            cur = conn.execute('DELETE FROM scenes WHERE id = %s AND home_id = %s', (scene_id, home_id))
            if cur.rowcount == 0:
                raise LookupError('Không tìm thấy kịch bản')
            conn.commit()
        finally:
            conn.close()

def persist_device_state(path: str, device: Device) -> None:
    payload = json.dumps(device.state, ensure_ascii=False)
    with _LOCK:
        conn = connect(path)
        try:
            conn.execute('UPDATE devices SET state = %s, last_seen_at = %s, updated_at = %s WHERE id = %s', (payload, _now(), _now(), device.id))
            conn.commit()
        finally:
            conn.close()

def _seed(conn: psycopg.Connection) -> None:
    now = _now()
    conn.execute('INSERT INTO homes (id, name, timezone, created_at) VALUES (%s, %s, %s, %s)', (HOME_ID, 'Michelin Bois', 'Asia/Ho_Chi_Minh', now))
    rooms = [('living', 'Phòng khách', 1), ('bed', 'Phòng ngủ', 2), ('kitchen', 'Bếp', 3), ('bath', 'Phòng tắm', 4), ('office', 'Phòng làm việc', 5), ('balcony', 'Ban công', 6)]
    for room_id, label, order in rooms:
        conn.execute('INSERT INTO rooms (id, home_id, label, sort_order) VALUES (%s, %s, %s, %s)', (room_id, HOME_ID, label, order))
    pin = hash_pin(DEFAULT_PIN)
    members = [('minh-duc', 'Minh Đức', 'Đ', 'admin', 'minh.nguyen@homemate.vn', '+84 912 345 678'), ('vinh', 'Vinh', 'V', 'member', None, None), ('thanh', 'Thành', 'T', 'member', None, None), ('truong', 'Trượng', 'Tr', 'member', None, None)]
    for user_id, name, initial, role, email, phone in members:
        conn.execute("""
            INSERT INTO users
                (id, home_id, display_name, initial, role, email, phone, pin_hash, is_active, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1, %s, %s)
            """, (user_id, HOME_ID, name, initial, role, email, phone, pin, now, now))
    for device in default_devices():
        _insert_device(conn, device, now)
    _seed_conflicts(conn)
    _seed_scenes(conn, now)
    _seed_settings(conn, now)

def _seed_conflicts(conn: psycopg.Connection) -> None:
    """Idempotent symmetric climate pairs (same room)."""
    device_ids = {row['id'] for row in conn.execute('SELECT id FROM devices')}
    pairs = [('ac-living', 'heater-living', 'same_room', 'ask')]
    for left, right, scope, on_conflict in pairs:
        if left not in device_ids or right not in device_ids:
            continue
        for a, b in ((left, right), (right, left)):
            conn.execute("""
                INSERT INTO device_conflicts
                    (device_id, conflicts_with, scope, on_conflict)
                VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING""", (a, b, scope, on_conflict))

def _insert_missing_conflicts(conn: psycopg.Connection) -> int:
    before = conn.execute('SELECT COUNT(*) AS n FROM device_conflicts').fetchone()['n']
    _seed_conflicts(conn)
    after = conn.execute('SELECT COUNT(*) AS n FROM device_conflicts').fetchone()['n']
    return max(0, after - before)

def _insert_missing_devices(conn: psycopg.Connection) -> int:
    existing = {row['id'] for row in conn.execute('SELECT id FROM devices')}
    now = _now()
    added = 0
    for device in default_devices():
        if device.id in existing:
            continue
        _insert_device(conn, device, now)
        added += 1
    return added

def _insert_device(conn: psycopg.Connection, device: Device, now: str) -> None:
    device_type = KIND_TO_TYPE.get(device.kind, device.kind)
    topic = f'home/{device.room}/{device_type}/{device.id}'
    conn.execute("""
        INSERT INTO devices (
            id, home_id, room_id, hardware_uid, protocol, mqtt_topic,
            name, kind, device_type, capabilities, state, online,
            paired_at, last_seen_at, created_at, updated_at
        ) VALUES (%s, %s, %s, %s, 'mqtt', %s, %s, %s, %s, %s, %s, 1, %s, %s, %s, %s)
        """, (device.id, HOME_ID, device.room, f'mock:{device.id}', topic, device.name, device.kind, device_type, json.dumps([c.model_dump(exclude_none=True) for c in device.controls], ensure_ascii=False), json.dumps(device.state, ensure_ascii=False), now, now, now, now))
    aliases = {device.name.lower(), *EXTRA_ALIASES.get(device.id, [])}
    for alias in aliases:
        conn.execute('INSERT INTO device_aliases (id, device_id, alias) VALUES (%s, %s, %s)', (str(uuid.uuid4()), device.id, alias))

def _seed_scenes(conn: psycopg.Connection, now: str) -> None:
    scenes: list[tuple[str, str, str, list[tuple[str, str, dict[str, Any]]]]] = [('guests', 'Đón khách', 'đón khách', [('light-living', 'set_brightness', {'brightness': 60}), ('speaker-living', 'turn_on', {}), ('ac-living', 'set_temperature', {'temperature': 26})]), ('sleep', 'Đi ngủ', 'đi ngủ', [('light-living', 'turn_off', {}), ('light-bed', 'turn_off', {}), ('curtain', 'close', {}), ('door', 'lock', {})]), ('home', 'Đi làm về', 'về nhà', [('light-living', 'turn_on', {}), ('ac-living', 'turn_on', {})])]
    for scene_id, name, keyword, steps in scenes:
        conn.execute("""
            INSERT INTO scenes
                (id, home_id, name, voice_keyword, is_enabled, created_by, created_at, updated_at)
            VALUES (%s, %s, %s, %s, 1, 'minh-duc', %s, %s)
            """, (scene_id, HOME_ID, name, keyword, now, now))
        for order, (device_id, action, params) in enumerate(steps, start=1):
            conn.execute("""
                INSERT INTO scene_steps (id, scene_id, sort_order, device_id, action, parameters)
                VALUES (%s, %s, %s, %s, %s, %s)
                """, (str(uuid.uuid4()), scene_id, order, device_id, action, json.dumps(params, ensure_ascii=False)))

def _seed_settings(conn: psycopg.Connection, now: str) -> None:
    rows = [('command_log_enabled', True), ('command_log_retention_days', 30), ('hitl_timeout_seconds', 30)]
    for key, value in rows:
        conn.execute('INSERT INTO settings (home_id, key, value, updated_at) VALUES (%s, %s, %s, %s)', (HOME_ID, key, json.dumps(value), now))
    conn.execute("""
        INSERT INTO hitl_policies (id, home_id, device_id, action, require_confirm)
        VALUES (%s, %s, 'door', 'unlock', 1)
        """, (str(uuid.uuid4()), HOME_ID))

def get_home_settings(path: str, home_id: str) -> dict[str, Any]:
    with _LOCK:
        conn = connect(path)
        try:
            rows = conn.execute('SELECT key, value FROM settings WHERE home_id = %s', (home_id,)).fetchall()
        finally:
            conn.close()
    result: dict[str, Any] = {'command_log_enabled': True, 'command_log_retention_days': 30, 'hitl_timeout_seconds': 30}
    for row in rows:
        try:
            result[row['key']] = json.loads(row['value'])
        except json.JSONDecodeError:
            result[row['key']] = row['value']
    return result

def update_home_settings(path: str, home_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    allowed = {'command_log_enabled', 'command_log_retention_days', 'hitl_timeout_seconds'}
    unknown = set(updates) - allowed
    if unknown:
        raise ValueError(f"Unsupported setting keys: {', '.join(sorted(unknown))}")
    if 'command_log_enabled' in updates and (not isinstance(updates['command_log_enabled'], bool)):
        raise ValueError('command_log_enabled must be a boolean')
    if 'command_log_retention_days' in updates:
        days = updates['command_log_retention_days']
        if not isinstance(days, int) or days < 1 or days > 365:
            raise ValueError('command_log_retention_days must be an integer from 1 to 365')
    if 'hitl_timeout_seconds' in updates:
        seconds = updates['hitl_timeout_seconds']
        if not isinstance(seconds, int) or seconds < 5 or seconds > 300:
            raise ValueError('hitl_timeout_seconds must be an integer from 5 to 300')
    now = _now()
    with _LOCK:
        conn = connect(path)
        try:
            for key, value in updates.items():
                conn.execute("""
                    INSERT INTO settings (home_id, key, value, updated_at)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT(home_id, key) DO UPDATE SET
                        value = excluded.value,
                        updated_at = excluded.updated_at
                    """, (home_id, key, json.dumps(value), now))
            conn.commit()
        finally:
            conn.close()
    return get_home_settings(path, home_id)

def is_command_log_enabled(path: str, home_id: str) -> bool:
    return bool(get_home_settings(path, home_id).get('command_log_enabled', True))

def list_hitl_policies(path: str, home_id: str) -> list[dict[str, Any]]:
    with _LOCK:
        conn = connect(path)
        try:
            rows = conn.execute("""
                SELECT p.id, p.device_id, p.action, p.require_confirm,
                       d.name AS device_name, d.kind AS device_kind
                FROM hitl_policies p
                LEFT JOIN devices d ON d.id = p.device_id
                WHERE p.home_id = %s
                ORDER BY p.device_id, p.action
                """, (home_id,)).fetchall()
        finally:
            conn.close()
    return [{'id': row['id'], 'device_id': row['device_id'], 'device_name': row['device_name'] or row['device_id'] or '', 'device_kind': row['device_kind'] or '', 'action': row['action'], 'require_confirm': bool(row['require_confirm'])} for row in rows]

def replace_hitl_policies(path: str, home_id: str, policies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Replace all HITL policies for a home. Each item: device_id, action, require_confirm."""
    normalized: list[tuple[str, str, bool]] = []
    seen: set[tuple[str, str]] = set()
    with _LOCK:
        conn = connect(path)
        try:
            for item in policies:
                device_id = str(item.get('device_id') or '').strip()
                action = str(item.get('action') or '').strip()
                if not device_id or not action:
                    raise ValueError('Mỗi policy cần device_id và action')
                key = (device_id, action)
                if key in seen:
                    raise ValueError(f'Trùng policy {device_id}/{action}')
                seen.add(key)
                device = conn.execute('SELECT id FROM devices WHERE id = %s AND home_id = %s', (device_id, home_id)).fetchone()
                if device is None:
                    raise LookupError(f'Không tìm thấy thiết bị {device_id}')
                require_confirm = bool(item.get('require_confirm', True))
                normalized.append((device_id, action, require_confirm))
            conn.execute('DELETE FROM hitl_policies WHERE home_id = %s', (home_id,))
            for device_id, action, require_confirm in normalized:
                conn.execute("""
                    INSERT INTO hitl_policies (id, home_id, device_id, action, require_confirm)
                    VALUES (%s, %s, %s, %s, %s)
                    """, (str(uuid.uuid4()), home_id, device_id, action, 1 if require_confirm else 0))
            conn.commit()
        finally:
            conn.close()
    return list_hitl_policies(path, home_id)

def append_command_log(path: str, home_id: str, *, utterance: str, intent: str | None, result: str, note: str | None=None, session_id: str | None=None, user_id: str | None=None, actions: list[dict[str, Any]] | None=None) -> dict[str, Any]:
    """Insert one command log row (+ optional action children). Honors retention setting."""
    settings = get_home_settings(path, home_id)
    if not settings.get('command_log_enabled', True):
        return {}
    log_id = str(uuid.uuid4())
    now = _now()
    retention_days = int(settings.get('command_log_retention_days') or 30)
    action_rows = actions or []
    cutoff = (datetime.now(timezone.utc).replace(microsecond=0) - timedelta(days=retention_days)).isoformat()
    with _LOCK:
        conn = connect(path)
        try:
            conn.execute("""
                INSERT INTO command_logs
                    (id, home_id, user_id, session_id, utterance, intent, result, note, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (log_id, home_id, user_id, session_id, utterance, intent, result, note, now))
            for item in action_rows:
                device_id = str(item.get('device_id') or '').strip()
                action = str(item.get('action') or '').strip()
                if not device_id or not action:
                    continue
                conn.execute("""
                    INSERT INTO command_log_actions
                        (id, log_id, device_id, action, parameters, status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """, (str(uuid.uuid4()), log_id, device_id, action, json.dumps(item.get('parameters') or {}, ensure_ascii=False), str(item.get('status') or 'ok')))
            conn.execute('DELETE FROM command_logs WHERE home_id = %s AND created_at < %s', (home_id, cutoff))
            conn.commit()
        finally:
            conn.close()
    return {'id': log_id, 'utterance': utterance, 'intent': intent, 'result': result, 'note': note, 'session_id': session_id, 'created_at': now}

def list_command_logs(path: str, home_id: str, *, limit: int=50) -> list[dict[str, Any]]:
    limit = max(1, min(limit, 200))
    with _LOCK:
        conn = connect(path)
        try:
            rows = conn.execute("""
                SELECT id, utterance, intent, result, note, session_id, created_at
                FROM command_logs
                WHERE home_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """, (home_id, limit)).fetchall()
        finally:
            conn.close()
    return [{'id': row['id'], 'utterance': row['utterance'], 'intent': row['intent'], 'result': row['result'], 'note': row['note'] or '', 'session_id': row['session_id'] or '', 'created_at': row['created_at']} for row in rows]
