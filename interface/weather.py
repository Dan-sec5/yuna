"""
interface/weather.py

Proveedor meteorológico ligero para Yuna.

- Open-Meteo
- Sin API key
- Geocodificación por nombre de ciudad
- Caché en memoria
- Fallos de red nunca rompen la TUI
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from threading import RLock
from typing import Optional

from config import get


@dataclass(frozen=True)
class WeatherSnapshot:
    condition: str = "unknown"
    temperature: Optional[float] = None
    weather_code: Optional[int] = None
    location: str = ""
    updated_at: float = 0.0


def weather_code_to_condition(code: int | None) -> str:
    """
    Convierte códigos WMO/Open-Meteo en estados simples
    entendidos por AvatarContext.
    """

    if code is None:
        return "unknown"

    if code == 0:
        return "sunny"

    if code in {1, 2}:
        return "partly_cloudy"

    if code == 3:
        return "cloudy"

    if code in {45, 48}:
        return "fog"

    if code in {
        51, 53, 55,
        56, 57,
        61, 63, 65,
        66, 67,
        80, 81, 82,
    }:
        return "rain"

    if code in {
        71, 73, 75, 77,
        85, 86,
    }:
        return "snow"

    if code in {95, 96, 99}:
        return "storm"

    return "unknown"


class WeatherProvider:
    def __init__(self):
        self._lock = RLock()
        self._cache = WeatherSnapshot()

    def _config(self):
        enabled = bool(
            get("weather.enabled", False)
        )

        location = str(
            get("weather.location", "")
            or ""
        ).strip()

        refresh_minutes = int(
            get(
                "weather.refresh_minutes",
                45,
            )
            or 45
        )

        return (
            enabled,
            location,
            max(
                refresh_minutes,
                10,
            ),
        )

    def get(
        self,
        *,
        force: bool = False,
    ) -> WeatherSnapshot:

        enabled, location, refresh_minutes = (
            self._config()
        )

        if not enabled or not location:
            return WeatherSnapshot(
                condition="unknown",
                location=location,
            )

        now = time.time()

        with self._lock:
            cached = self._cache

            cache_valid = (
                cached.updated_at > 0
                and cached.location == location
                and (
                    now - cached.updated_at
                    < refresh_minutes * 60
                )
            )

            if cache_valid and not force:
                return cached

        try:
            snapshot = self._fetch(
                location
            )
        except Exception:
            # Nunca romper Yuna por un fallo meteorológico.
            with self._lock:
                if self._cache.updated_at > 0:
                    return self._cache

            return WeatherSnapshot(
                condition="unknown",
                location=location,
            )

        with self._lock:
            self._cache = snapshot

        return snapshot

    def _fetch(
        self,
        location: str,
    ) -> WeatherSnapshot:

        latitude, longitude, resolved_name = (
            self._geocode(location)
        )

        params = urllib.parse.urlencode({
            "latitude": latitude,
            "longitude": longitude,
            "current": (
                "temperature_2m,"
                "weather_code"
            ),
            "timezone": "auto",
        })

        url = (
            "https://api.open-meteo.com/v1/"
            f"forecast?{params}"
        )

        data = self._get_json(url)

        current = (
            data.get("current")
            or {}
        )

        code = current.get(
            "weather_code"
        )

        temperature = current.get(
            "temperature_2m"
        )

        return WeatherSnapshot(
            condition=weather_code_to_condition(
                code
            ),
            temperature=temperature,
            weather_code=code,
            location=resolved_name,
            updated_at=time.time(),
        )

    def _geocode(
        self,
        location: str,
    ):
        params = urllib.parse.urlencode({
            "name": location,
            "count": 1,
            "language": "es",
            "format": "json",
        })

        url = (
            "https://geocoding-api.open-meteo.com/"
            f"v1/search?{params}"
        )

        data = self._get_json(url)

        results = (
            data.get("results")
            or []
        )

        if not results:
            raise ValueError(
                f"Ubicación no encontrada: {location}"
            )

        item = results[0]

        name_parts = [
            item.get("name"),
            item.get("admin1"),
            item.get("country"),
        ]

        resolved_name = ", ".join(
            str(x)
            for x in name_parts
            if x
        )

        return (
            float(item["latitude"]),
            float(item["longitude"]),
            resolved_name,
        )

    @staticmethod
    def _get_json(
        url: str,
    ) -> dict:

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "YunaLocalAgent/1.0"
                ),
            },
        )

        with urllib.request.urlopen(
            request,
            timeout=8,
        ) as response:

            raw = response.read()

        return json.loads(
            raw.decode("utf-8")
        )


weather_provider = WeatherProvider()
