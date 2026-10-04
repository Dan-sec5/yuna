from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Optional


@dataclass(frozen=True)
class AvatarContext:
    time_of_day: str = "day"
    weather: str = "unknown"
    agent_state: str = "idle"
    mood: str = "neutral"


def get_time_of_day(now: Optional[datetime] = None) -> str:
    now = now or datetime.now()
    hour = now.hour

    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 18:
        return "afternoon"
    if 18 <= hour < 22:
        return "evening"
    return "night"


def normalize_weather(value: str) -> str:
    value = str(value).strip().lower()

    aliases = {
        "sun": "sunny",
        "soleado": "sunny",
        "despejado": "sunny",
        "cloud": "cloudy",
        "nublado": "cloudy",
        "rain": "rain",
        "lluvia": "rain",
        "lluvioso": "rain",
        "storm": "storm",
        "tormenta": "storm",
        "snow": "snow",
        "nieve": "snow",
    }

    return aliases.get(value, value or "unknown")


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

    return value if value in allowed else "idle"


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


class AvatarState:
    def __init__(self):
        self._lock = RLock()
        self._context = AvatarContext(
            time_of_day=get_time_of_day()
        )

    def get(self) -> AvatarContext:
        with self._lock:
            return self._context

    def update(
        self,
        *,
        weather: Optional[str] = None,
        agent_state: Optional[str] = None,
        mood: Optional[str] = None,
    ) -> AvatarContext:
        with self._lock:
            changes = {
                "time_of_day": get_time_of_day(),
            }

            if weather is not None:
                changes["weather"] = normalize_weather(weather)

            if agent_state is not None:
                changes["agent_state"] = normalize_agent_state(
                    agent_state
                )

            if mood is not None:
                changes["mood"] = normalize_mood(mood)

            # Humor ambiental automático.
            #
            # Solo se aplica cuando Yuna está realmente idle
            # y nadie ha solicitado un humor explícito.
            effective_state = changes.get(
                "agent_state",
                self._context.agent_state,
            )

            if (
                mood is None
                and effective_state == "idle"
            ):
                hour = datetime.now().hour

                if 0 <= hour < 5:
                    changes["mood"] = "sleepy"

                elif 5 <= hour < 12:
                    changes["mood"] = "happy"

                elif 12 <= hour < 18:
                    changes["mood"] = "focused"

                else:
                    changes["mood"] = "neutral"

            self._context = replace(
                self._context,
                **changes,
            )

            return self._context


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

        candidates = self._candidate_names(
            context
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
                path = self.avatar_dir / f"{name}{ext}"

                if path.is_file():
                    return path

        return None

    def _candidate_names(
        self,
        c: AvatarContext,
    ) -> list[str]:

        candidates = [
            f"{c.agent_state}_{c.mood}",
            f"{c.time_of_day}_{c.mood}",
            f"{c.weather}_{c.mood}",
            f"{c.time_of_day}_{c.weather}",

            c.agent_state,
            c.mood,
            c.weather,
            c.time_of_day,

            "Avatar",
            "avatar",
            "default",
        ]

        return list(
            dict.fromkeys(candidates)
        )


avatar_state = AvatarState()
avatar_resolver = AvatarResolver()
