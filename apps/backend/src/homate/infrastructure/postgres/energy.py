"""State-based energy estimates used until real telemetry is available."""
from __future__ import annotations
import asyncio
import json
import logging
import psycopg
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from homate.modules.home.domain.device import Device
from homate.infrastructure.postgres.household import connect
logger = logging.getLogger(__name__)

def _parse(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed

def _utc_now() -> datetime:
    return datetime.now(UTC)

class EnergyService:

    def __init__(self, db_path: str, *, home_id: str, timezone: str) -> None:
        self.db_path = db_path
        self.home_id = home_id
        self.timezone = timezone

    def _profile(self, conn: psycopg.Connection, device_id: str) -> dict | None:
        return conn.execute('SELECT * FROM device_energy_profiles WHERE device_id = %s AND enabled = 1', (device_id,)).fetchone()

    @staticmethod
    def _reading_is_active(reading: dict) -> bool:
        state = json.loads(reading['state_snapshot'] or '{}')
        if isinstance(state.get('power'), bool):
            return state['power']
        speed = state.get('speed')
        if isinstance(speed, (int, float)):
            return speed > 0
        if reading['model_type'] == 'motor_event':
            return False
        return float(reading['power_w']) > 0

    def _activity_metrics(self, conn: psycopg.Connection, device_id: str, *, now: datetime) -> tuple[float, float]:
        """Return active minutes today and minutes in the current active session."""
        readings = conn.execute("""SELECT er.recorded_at, er.power_w, er.state_snapshot, p.model_type
               FROM energy_readings er
               JOIN device_energy_profiles p ON p.device_id = er.device_id
               WHERE er.device_id = %s AND er.recorded_at <= %s
               ORDER BY er.recorded_at, er.id""", (device_id, now.isoformat())).fetchall()
        if not readings:
            return (0.0, 0.0)
        today_start = now.astimezone(ZoneInfo(self.timezone)).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)
        active_today_seconds = 0.0
        for index, reading in enumerate(readings):
            if not self._reading_is_active(reading):
                continue
            interval_start = max(_parse(reading['recorded_at']), today_start)
            interval_end = min(_parse(readings[index + 1]['recorded_at']), now) if index + 1 < len(readings) else now
            if interval_end > interval_start:
                active_today_seconds += (interval_end - interval_start).total_seconds()
        current_session_seconds = 0.0
        if self._reading_is_active(readings[-1]):
            session_start = _parse(readings[-1]['recorded_at'])
            for reading in reversed(readings[:-1]):
                if not self._reading_is_active(reading):
                    break
                session_start = _parse(reading['recorded_at'])
            current_session_seconds = max(0.0, (now - session_start).total_seconds())
        return (active_today_seconds / 60, current_session_seconds / 60)

    @staticmethod
    def _estimated_power(device: Device, profile: dict) -> float:
        state = device.state
        rated = float(profile['rated_power_w'])
        standby = float(profile['standby_power_w'])
        params = json.loads(profile['parameters'] or '{}')
        model = profile['model_type']
        if model == 'motor_event':
            return standby
        if state.get('power') is False:
            return standby
        if model == 'brightness_linear':
            return rated * float(state.get('brightness', 100)) / 100
        if model == 'speed_levels':
            levels = params.get('speed_power_w') or {}
            speed = state.get('speed', 0)
            return float(levels.get(str(speed), rated if speed else standby))
        if model == 'duty_cycle':
            return rated * float(params.get('duty_cycle', 0.65))
        if state.get('power') is True or 'power' not in state:
            return rated
        return standby

    def record(self, device: Device, *, now: datetime | None=None) -> None:
        now = now or _utc_now()
        now_text = now.isoformat()
        conn = connect(self.db_path)
        try:
            profile = self._profile(conn, device.id)
            if profile is None:
                return
            current_power = max(0.0, self._estimated_power(device, profile))
            previous = conn.execute("""SELECT recorded_at, power_w, state_snapshot
                   FROM energy_readings WHERE device_id = %s
                   ORDER BY recorded_at DESC, id DESC LIMIT 1""", (device.id,)).fetchone()
            delta_wh = 0.0
            interval_parts: list[tuple[str, float]] = []
            event_wh = 0.0
            if previous is not None:
                interval_start = _parse(previous['recorded_at'])
                cursor = interval_start
                tz = ZoneInfo(self.timezone)
                while cursor < now:
                    local_cursor = cursor.astimezone(tz)
                    next_hour = (local_cursor.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)).astimezone(UTC)
                    part_end = min(now, next_hour)
                    seconds = max(0.0, (part_end - cursor).total_seconds())
                    part_wh = float(previous['power_w']) * seconds / 3600
                    bucket = local_cursor.replace(minute=0, second=0, microsecond=0).astimezone(UTC).isoformat()
                    interval_parts.append((bucket, part_wh))
                    delta_wh += part_wh
                    cursor = part_end
                if profile['model_type'] == 'motor_event':
                    old_state = json.loads(previous['state_snapshot'] or '{}')
                    if old_state != device.state:
                        params = json.loads(profile['parameters'] or '{}')
                        event_wh = float(profile['rated_power_w']) * float(params.get('event_seconds', 8)) / 3600
                        delta_wh += event_wh
            cumulative = conn.execute('SELECT COALESCE(SUM(energy_wh_delta), 0) AS total FROM energy_readings WHERE device_id = %s', (device.id,)).fetchone()['total'] + delta_wh
            conn.execute("""INSERT INTO energy_readings
                   (home_id, device_id, recorded_at, power_w, energy_wh_delta,
                    cumulative_energy_wh, source, quality, state_snapshot)
                   VALUES (%s, %s, %s, %s, %s, %s, 'estimated', 'good', %s)""", (self.home_id, device.id, now_text, current_power, delta_wh, cumulative, json.dumps(device.state, ensure_ascii=False)))
            current_bucket = now.astimezone(ZoneInfo(self.timezone)).replace(minute=0, second=0, microsecond=0).astimezone(UTC).isoformat()
            totals: dict[str, float] = {}
            for bucket, part_wh in interval_parts:
                totals[bucket] = totals.get(bucket, 0.0) + part_wh
            totals[current_bucket] = totals.get(current_bucket, 0.0) + event_wh
            for bucket, bucket_wh in totals.items():
                sample_count = 1 if bucket == current_bucket else 0
                conn.execute("""INSERT INTO energy_hourly
                       (home_id, device_id, room_id, bucket_start, energy_wh,
                        measured_wh, estimated_wh, sample_count, coverage_ratio, updated_at)
                       VALUES (%s, %s, %s, %s, %s, 0, %s, %s, 1, %s)
                       ON CONFLICT(device_id, bucket_start) DO UPDATE SET
                         room_id=excluded.room_id,
                         energy_wh=energy_hourly.energy_wh + excluded.energy_wh,
                         estimated_wh=energy_hourly.estimated_wh + excluded.estimated_wh,
                         sample_count=energy_hourly.sample_count + excluded.sample_count,
                         coverage_ratio=1,
                         updated_at=excluded.updated_at""", (self.home_id, device.id, device.room, bucket, bucket_wh, bucket_wh, sample_count, now_text))
            conn.commit()
        finally:
            conn.close()

    def record_all(self, devices: list[Device]) -> None:
        now = _utc_now()
        for device in devices:
            self.record(device, now=now)

    def _range(self, period: str, anchor: date | None=None) -> tuple[datetime, datetime]:
        tz = ZoneInfo(self.timezone)
        local_now = _utc_now().astimezone(tz)
        anchor_date = anchor or local_now.date()
        anchor_time = datetime.combine(anchor_date, datetime.min.time(), tzinfo=tz)
        if period == 'today':
            start = anchor_time
            end = start + timedelta(days=1)
        elif period == 'week':
            start = anchor_time - timedelta(days=anchor_time.weekday())
            end = start + timedelta(days=7)
        elif period == 'month':
            start = anchor_time.replace(day=1)
            end = start.replace(year=start.year + 1, month=1) if start.month == 12 else start.replace(month=start.month + 1)
        elif period == '3months':
            quarter_month = (anchor_time.month - 1) // 3 * 3 + 1
            start = anchor_time.replace(month=quarter_month, day=1)
            end_month = quarter_month + 3
            end = start.replace(year=start.year + 1, month=end_month - 12) if end_month > 12 else start.replace(month=end_month)
        elif period == 'year':
            start = anchor_time.replace(month=1, day=1)
            end = start.replace(year=start.year + 1)
        else:
            days = {'7days': 7, '30days': 30, '3months': 90, 'year': 365}.get(period, 7)
            end = anchor_time + timedelta(days=1)
            start = end - timedelta(days=days)
        if start <= local_now < end:
            end = local_now
        return (start.astimezone(UTC), end.astimezone(UTC))

    def report(self, *, period: str, room_id: str | None=None, device_id: str | None=None, anchor: date | None=None) -> dict:
        start, end = self._range(period, anchor)
        conn = connect(self.db_path)
        try:
            filters = ['h.home_id = %s', 'h.bucket_start >= %s', 'h.bucket_start < %s']
            args: list[object] = [self.home_id, start.isoformat(), end.isoformat()]
            if room_id:
                filters.append('h.room_id = %s')
                args.append(room_id)
            if device_id:
                filters.append('h.device_id = %s')
                args.append(device_id)
            where = ' AND '.join(filters)
            totals = conn.execute(f'SELECT COALESCE(SUM(h.energy_wh), 0) total,\n                           COALESCE(SUM(h.measured_wh), 0) measured,\n                           COALESCE(SUM(h.estimated_wh), 0) estimated\n                    FROM energy_hourly h WHERE {where}', args).fetchone()
            total_wh = float(totals['total'])
            measured_wh = float(totals['measured'])
            estimated_wh = float(totals['estimated'])
            duration = end - start
            previous_start = start - duration
            previous_end = start
            previous_args: list[object] = [self.home_id, previous_start.isoformat(), previous_end.isoformat()]
            if room_id:
                previous_args.append(room_id)
            if device_id:
                previous_args.append(device_id)
            previous_total_wh = float(conn.execute(f'SELECT COALESCE(SUM(h.energy_wh), 0) total FROM energy_hourly h WHERE {where}', previous_args).fetchone()['total'])
            change_percent = (total_wh - previous_total_wh) / previous_total_wh * 100 if previous_total_wh > 0 else None
            tariff = conn.execute('SELECT currency, config FROM electricity_tariffs WHERE home_id=%s AND is_active=1 ORDER BY valid_from DESC LIMIT 1', (self.home_id,)).fetchone()
            config = json.loads(tariff['config'] or '{}') if tariff else {}
            price = float(config.get('price_per_kwh', 0))
            vat = float(config.get('vat_rate', 0))
            measurement_coverage = measured_wh / total_wh if total_wh > 0 else 0.0
            if measured_wh > 0 and estimated_wh > 0:
                source = 'mixed'
            elif measured_wh > 0:
                source = 'measured'
            else:
                source = 'estimated'
            by_device = [dict(row) for row in conn.execute(f'SELECT h.device_id id, d.name, d.kind, h.room_id,\n                            SUM(h.energy_wh)/1000.0 kwh,\n                            COALESCE((\n                                SELECT er.power_w\n                                FROM energy_readings er\n                                WHERE er.device_id = h.device_id\n                                ORDER BY er.recorded_at DESC, er.id DESC\n                                LIMIT 1\n                            ), 0) current_power_w\n                     FROM energy_hourly h JOIN devices d ON d.id=h.device_id\n                     WHERE {where} GROUP BY h.device_id, d.name, d.kind, h.room_id\n                     ORDER BY kwh DESC', args).fetchall()]
            activity_now = _utc_now()
            for item in by_device:
                active_today, current_session = self._activity_metrics(conn, item['id'], now=activity_now)
                item['active_minutes_today'] = active_today
                item['current_session_minutes'] = current_session
            by_room = [dict(row) for row in conn.execute(f'SELECT h.room_id id, r.label name, SUM(h.energy_wh)/1000.0 kwh\n                     FROM energy_hourly h JOIN rooms r ON r.id=h.room_id AND r.home_id=h.home_id\n                     WHERE {where} GROUP BY h.room_id, r.label ORDER BY kwh DESC', args).fetchall()]
            local_expr = "(h.bucket_start AT TIME ZONE 'Asia/Ho_Chi_Minh')"
            if period == 'today':
                group_expr = f"""to_char({local_expr}, 'YYYY-MM-DD"T"HH24:00:00')"""
            elif period == '3months':
                group_expr = f"""to_char({local_expr}, 'IYYY-"W"IW')"""
            elif period == 'year':
                group_expr = f"to_char({local_expr}, 'YYYY-MM')"
            else:
                group_expr = f"to_char({local_expr}, 'YYYY-MM-DD')"
            timeseries = [dict(row) for row in conn.execute(f'SELECT {group_expr} bucket, SUM(h.energy_wh)/1000.0 kwh\n                     FROM energy_hourly h WHERE {where} GROUP BY bucket ORDER BY bucket', args).fetchall()]
            return {'period': period, 'from': start.isoformat(), 'to': end.isoformat(), 'total_kwh': total_wh / 1000, 'previous_total_kwh': previous_total_wh / 1000, 'change_percent': change_percent, 'estimated_cost': total_wh / 1000 * price * (1 + vat) if tariff else None, 'currency': tariff['currency'] if tariff else 'VND', 'source': source, 'measurement_coverage': measurement_coverage, 'timeseries': timeseries, 'by_device': by_device, 'by_room': by_room}
        finally:
            conn.close()

    def aggregate_daily_and_cleanup(self, *, now: datetime | None=None) -> dict[str, int]:
        """Roll up completed local days, then enforce raw/hourly retention."""
        now = now or _utc_now()
        local_now = now.astimezone(ZoneInfo(self.timezone))
        today = local_now.date().isoformat()
        readings_cutoff = (now - timedelta(days=14)).isoformat()
        try:
            twelve_months_ago = local_now.replace(year=local_now.year - 1)
        except ValueError:
            twelve_months_ago = local_now.replace(year=local_now.year - 1, day=28)
        hourly_cutoff = twelve_months_ago.astimezone(UTC).isoformat()
        conn = connect(self.db_path)
        try:
            result = conn.execute("""INSERT INTO energy_daily
                   (home_id, device_id, room_id, local_date, energy_wh,
                    measured_wh, estimated_wh, sample_count, updated_at)
                   SELECT home_id, device_id, room_id,
                          to_char(bucket_start AT TIME ZONE 'Asia/Ho_Chi_Minh', 'YYYY-MM-DD') local_date,
                          SUM(energy_wh), SUM(measured_wh), SUM(estimated_wh),
                          SUM(sample_count), %s
                   FROM energy_hourly
                   WHERE home_id=%s
                     AND to_char(bucket_start AT TIME ZONE 'Asia/Ho_Chi_Minh', 'YYYY-MM-DD') < %s
                   GROUP BY home_id, device_id, room_id, local_date
                   ON CONFLICT(device_id, local_date) DO UPDATE SET
                     room_id=excluded.room_id,
                     energy_wh=excluded.energy_wh,
                     measured_wh=excluded.measured_wh,
                     estimated_wh=excluded.estimated_wh,
                     sample_count=excluded.sample_count,
                     updated_at=excluded.updated_at""", (now.isoformat(), self.home_id, today))
            daily_rows = result.rowcount
            result = conn.execute('DELETE FROM energy_readings WHERE recorded_at < %s', (readings_cutoff,))
            deleted_readings = result.rowcount
            result = conn.execute('DELETE FROM energy_hourly WHERE bucket_start < %s', (hourly_cutoff,))
            deleted_hourly = result.rowcount
            conn.commit()
            return {'daily_rows': daily_rows, 'deleted_readings': deleted_readings, 'deleted_hourly': deleted_hourly}
        finally:
            conn.close()

async def energy_sampler(service: EnergyService, devices_provider, interval_seconds: int) -> None:
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            service.record_all(devices_provider())
        except Exception:
            logger.exception('[ENERGY] sampler tick failed')

async def energy_daily_maintenance(service: EnergyService) -> None:
    while True:
        try:
            service.aggregate_daily_and_cleanup()
        except Exception:
            logger.exception('[ENERGY] daily maintenance failed')
        local_now = _utc_now().astimezone(ZoneInfo(service.timezone))
        tomorrow = (local_now + timedelta(days=1)).replace(hour=0, minute=5, second=0, microsecond=0)
        await asyncio.sleep(max(60.0, (tomorrow - local_now).total_seconds()))
