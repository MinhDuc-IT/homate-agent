import asyncio
import logging
from contextlib import asynccontextmanager, suppress

import psycopg
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from homate.application.household import HouseholdService, HOME_ID
from homate.config import get_settings
from homate.infrastructure.postgres import household
from homate.infrastructure.postgres.connection import connect
from homate.infrastructure.postgres.repository import PostgresHouseholdRepository
from homate.infrastructure.postgres.energy import EnergyService as PostgresEnergy
from homate.infrastructure.postgres.schedules import ScheduleService as PostgresSchedules
from homate.infrastructure.realtime import ConnectionManager, pending_hitl
from homate.infrastructure.weather import WeatherCache
from homate.modules.home.application.devices import DeviceStore
from homate.modules.energy.application.service import EnergyService
from homate.modules.automation.application.service import ScheduleService
from homate.presentation import auth, dashboard, users, scenes, schedules, settings, ambient, energy
from homate.worker import schedule_worker, energy_worker, ambient_worker


def create_app(database_url=None, *, start_workers=True):
    configuration = get_settings()
    database_url = database_url or configuration.database_url

    @asynccontextmanager
    async def lifespan(app):
        household.init_and_seed(database_url)
        service = HouseholdService(PostgresHouseholdRepository(database_url))
        meter = EnergyService(PostgresEnergy(database_url, home_id=HOME_ID, timezone="Asia/Ho_Chi_Minh"))

        def persist(device):
            household.persist_device_state(database_url, device)
            try: meter.record(device)
            except Exception: logging.getLogger(__name__).exception("Energy sample failed after state was saved")

        store = DeviceStore(household.load_devices(database_url), on_change=persist)
        manager = ConnectionManager()
        scheduler = ScheduleService(PostgresSchedules(database_url, store), service, store)
        app.state.household_service = service
        app.state.device_store = store
        app.state.ws_manager = manager
        app.state.energy_service = meter
        app.state.schedule_service = scheduler
        app.state.weather_cache = WeatherCache(api_key=configuration.weather_api_key, lat=configuration.weather_lat, lon=configuration.weather_lon, ttl_seconds=configuration.weather_ttl_seconds)
        app.state.database_url = database_url
        pending_hitl.bind_ui_manager(manager)
        pending_hitl.set_ttl_seconds(service.get_home_settings(HOME_ID)["hitl_timeout_seconds"])
        meter.record_all(store.list())
        tasks = []
        if start_workers:
            tasks = [asyncio.create_task(schedule_worker(scheduler, manager)), asyncio.create_task(energy_worker(meter, store, configuration.energy_sampler_interval_seconds)), asyncio.create_task(ambient_worker(service, store, manager, configuration))]
        try: yield
        finally:
            for task in tasks: task.cancel()
            for task in tasks:
                with suppress(asyncio.CancelledError): await task

    app = FastAPI(title="HomeMate Software API", version="0.2.0", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=configuration.cors_origins.split(","), allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
    for module in (auth, dashboard, users, scenes, schedules, settings, ambient, energy): app.include_router(module.router)
    app.include_router(dashboard.ws_router)

    @app.exception_handler(psycopg.IntegrityError)
    async def invalid_relation(request: Request, error):
        return JSONResponse(status_code=409, content={"detail": "Dữ liệu đang được sử dụng hoặc vi phạm ràng buộc liên kết."})

    @app.exception_handler(ValueError)
    async def invalid_value(request: Request, error):
        return JSONResponse(status_code=400, content={"detail": str(error)})

    @app.get("/health")
    def health():
        with connect(database_url) as connection: connection.execute("SELECT 1")
        return {"status": "ok", "database": "postgresql", "ai_enabled": False, "device_mode": "simulation"}
    return app
