from __future__ import annotations

import time

from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Optional


# ============================================================
# CONTEXTO
# ============================================================

@dataclass(frozen=True)
class AvatarContext:
    time_of_day: str = "day"
    weather: str = "unknown"
    agent_state: str = "idle"
    mood: str = "neutral"


# ============================================================
# HORA
# ============================================================

def get_time_of_day(
    now: Optional[datetime] = None,
) -> str:

    now = now or datetime.now()
    hour = now.hour

    if 5 <= hour < 12:
        return "morning"

    if 12 <= hour < 18:
        return "afternoon"

    if 18 <= hour < 22:
        return "evening"

    return "night"


# ============================================================
# NORMALIZACIÓN
# ============================================================

def normalize_weather(value: str) -> str:
    value = str(value).strip().lower()

    aliases = {
        "sun": "sunny",
        "soleado": "sunny",
        "despejado": "sunny",

        "cloud": "cloudy",
        "nublado": "cloudy",

        "partly_cloudy": "partly_cloudy",
        "parcialmente_nublado": "partly_cloudy",

        "fog": "fog",
        "niebla": "fog",

        "rain": "rain",
        "lluvia": "rain",
        "lluvioso": "rain",

        "storm": "storm",
        "tormenta": "storm",

        "snow": "snow",
        "nieve": "snow",
    }

    return aliases.get(
        value,
        value or "unknown",
    )


def normalize_agent_state(value: str) -> str:
    value = str(value).strip().lower()

    allowed = {
        "idle",
        "thinking",
        "working",
        "success",
        "error",
        "waiting",
    }

    return (
        value
        if value in allowed
        else "idle"
    )


def normalize_mood(value: str) -> str:
    value = str(value).strip().lower()

    aliases = {
        "feliz": "happy",
        "contenta": "happy",
        "alegre": "happy",

        "seria": "serious",
        "serio": "serious",

        "cansada": "tired",
        "cansado": "tired",

        "dormida": "sleepy",
        "soñolienta": "sleepy",

        "divertida": "amused",
        "divertido": "amused",

        "preocupada": "concerned",
        "preocupado": "concerned",

        "concentrada": "focused",
        "concentrado": "focused",
    }

    normalized = aliases.get(
        value,
        value or "neutral",
    )

    allowed = {
        "neutral",
        "happy",
        "focused",
        "serious",
        "amused",
        "concerned",
        "tired",
        "sleepy",
    }

    return (
        normalized
        if normalized in allowed
        else "neutral"
    )


# ============================================================
# HUMOR AMBIENTAL
# ============================================================

def ambient_mood(
    now: Optional[datetime] = None,
) -> str:

    now = now or datetime.now()
    hour = now.hour

    if 0 <= hour < 5:
        return "sleepy"

    if 5 <= hour < 12:
        return "happy"

    if 12 <= hour < 18:
        return "focused"

    return "neutral"


# ============================================================
# DURACIÓN DEL HUMOR
# ============================================================

MOOD_TTL = {
    "neutral": 0.0,
    "happy": 12.0,
    "focused": 30.0,
    "serious": 30.0,
    "amused": 15.0,
    "concerned": 20.0,
    "tired": 45.0,
    "sleepy": 60.0,
}


# ============================================================
# ESTADO
# ============================================================

class AvatarState:

    def __init__(self):
        self._lock = RLock()

        self._context = AvatarContext(
            time_of_day=get_time_of_day(),
            mood=ambient_mood(),
        )

        self._mood_until = 0.0


    def get(self) -> AvatarContext:
        with self._lock:
            return self._context


    def mood_remaining(self) -> float:
        with self._lock:
            return max(
                0.0,
                self._mood_until - time.monotonic(),
            )


    def update(
        self,
        *,
        weather: Optional[str] = None,
        agent_state: Optional[str] = None,
        mood: Optional[str] = None,
        mood_ttl: Optional[float] = None,
    ) -> AvatarContext:

        with self._lock:

            now = time.monotonic()

            changes = {
                "time_of_day": get_time_of_day(),
            }

            # --------------------------------------------------
            # CLIMA
            # --------------------------------------------------

            if weather is not None:
                changes["weather"] = (
                    normalize_weather(weather)
                )

            # --------------------------------------------------
            # ESTADO DEL AGENTE
            # --------------------------------------------------

            if agent_state is not None:
                changes["agent_state"] = (
                    normalize_agent_state(
                        agent_state
                    )
                )

            effective_state = changes.get(
                "agent_state",
                self._context.agent_state,
            )

            # --------------------------------------------------
            # HUMOR EXPLÍCITO
            # --------------------------------------------------

            if mood is not None:

                normalized = normalize_mood(
                    mood
                )

                changes["mood"] = normalized

                ttl = (
                    mood_ttl
                    if mood_ttl is not None
                    else MOOD_TTL.get(
                        normalized,
                        0.0,
                    )
                )

                if ttl > 0:
                    self._mood_until = (
                        now + float(ttl)
                    )
                else:
                    self._mood_until = 0.0

            # --------------------------------------------------
            # HUMOR EXPIRADO
            # --------------------------------------------------

            elif (
                self._mood_until > 0
                and now >= self._mood_until
            ):
                self._mood_until = 0.0

                if effective_state == "idle":
                    changes["mood"] = (
                        ambient_mood()
                    )

            # --------------------------------------------------
            # HUMOR AMBIENTAL
            # --------------------------------------------------

            elif (
                self._mood_until == 0
                and effective_state == "idle"
            ):
                changes["mood"] = (
                    ambient_mood()
                )

            self._context = replace(
                self._context,
                **changes,
            )

            return self._context


# ============================================================
# RESOLVER
# ============================================================

class AvatarResolver:

    def __init__(
        self,
        avatar_dir: Optional[Path] = None,
    ):
        self.avatar_dir = (
            avatar_dir
            or Path.home()
            / "yuna"
            / "assets"
            / "avatars"
        )


    def resolve(
        self,
        context: AvatarContext,
    ) -> Optional[Path]:

        candidates = (
            self._candidate_names(
                context
            )
        )

        extensions = (
            ".png",
            ".jpg",
            ".jpeg",
            ".webp",
            ".gif",
        )

        for name in candidates:

            for ext in extensions:

                path = (
                    self.avatar_dir
                    / f"{name}{ext}"
                )

                if path.is_file():
                    return path

        return None


    def _candidate_names(
        self,
        c: AvatarContext,
    ) -> list[str]:

        if c.agent_state == "idle":
            candidates = [
                f"{c.time_of_day}_{c.weather}",
                f"{c.weather}_{c.mood}",
                f"{c.time_of_day}_{c.mood}",

                c.weather,
                c.time_of_day,
                c.mood,

                f"{c.agent_state}_{c.mood}",
                c.agent_state,

                "Avatar",
                "avatar",
                "default",
            ]

        else:
            candidates = [
                f"{c.agent_state}_{c.mood}",
                c.agent_state,

                f"{c.time_of_day}_{c.mood}",
                f"{c.weather}_{c.mood}",
                f"{c.time_of_day}_{c.weather}",

                c.mood,
                c.weather,
                c.time_of_day,

                "Avatar",
                "avatar",
                "default",
            ]

        return list(
            dict.fromkeys(
                candidates
            )
        )


avatar_state = AvatarState()
avatar_resolver = AvatarResolver()
