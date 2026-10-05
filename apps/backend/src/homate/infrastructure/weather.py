"""OpenWeatherMap current-weather cache — TTL-bound, degrades to None on error."""

from __future__ import annotations

import asyncio
import logging
import time

import httpx

from homate.modules.home.domain.ambient import WeatherSnapshot

logger = logging.getLogger(__name__)

_ENDPOINT = "https://api.openweathermap.org/data/2.5/weather"


class WeatherCache:
    """Fetch OpenWeather at most once per TTL; shared by every request.

    Never raises — a missing API key, network error, or bad response all
    resolve to `None` so ambient context degrades softly instead of failing
    the request that asked for it.
    """

    def __init__(
        self,
        *,
        api_key: str,
        lat: float,
        lon: float,
        ttl_seconds: int = 600,
        timeout: float = 5.0,
    ) -> None:
        self.api_key = api_key
        self.lat = lat
        self.lon = lon
        self.ttl_seconds = ttl_seconds
        self.timeout = timeout
        self._snapshot: WeatherSnapshot | None = None
        self._fetched_at: float = 0.0
        self._lock = asyncio.Lock()

    async def get(self, *, force_refresh: bool = False) -> WeatherSnapshot | None:
        if not self.api_key:
            return None
        now = time.time()
        if not force_refresh and self._snapshot is not None and now - self._fetched_at < self.ttl_seconds:
            return self._snapshot
        async with self._lock:
            now = time.time()
            if not force_refresh and self._snapshot is not None and now - self._fetched_at < self.ttl_seconds:
                return self._snapshot
            fetched = await self._fetch()
            if fetched is not None:
                self._snapshot = fetched
                self._fetched_at = now
                return fetched
            # Fetch failed: serve the stale snapshot (marked) rather than nothing.
            if self._snapshot is not None:
                return self._snapshot.model_copy(update={"stale": True})
            return None

    async def _fetch(self) -> WeatherSnapshot | None:
        params = {
            "lat": self.lat,
            "lon": self.lon,
            "units": "metric",
            "lang": "vi",
            "appid": self.api_key,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(_ENDPOINT, params=params)
                response.raise_for_status()
                body = response.json()
        except httpx.HTTPError as exc:
            logger.warning("[WEATHER] fetch failed: %s", exc)
            return None
        try:
            main = body["main"]
            weather = (body.get("weather") or [{}])[0]
            wind = body.get("wind") or {}
            return WeatherSnapshot(
                temp_c=float(main["temp"]),
                feels_like_c=float(main.get("feels_like", main["temp"])),
                humidity=int(main.get("humidity", 0)),
                condition=str(weather.get("main") or ""),
                description=str(weather.get("description") or ""),
                wind_ms=float(wind.get("speed", 0.0)),
                fetched_at=str(int(time.time())),
                stale=False,
            )
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("[WEATHER] unexpected response shape: %s", exc)
            return None
