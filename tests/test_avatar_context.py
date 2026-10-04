from datetime import datetime
from pathlib import Path

from interface.avatar_context import (
    AvatarContext,
    AvatarResolver,
    get_time_of_day,
    normalize_agent_state,
    normalize_mood,
    normalize_weather,
)


def test_time_of_day():
    assert get_time_of_day(
        datetime(2026, 1, 1, 8, 0)
    ) == "morning"

    assert get_time_of_day(
        datetime(2026, 1, 1, 14, 0)
    ) == "afternoon"

    assert get_time_of_day(
        datetime(2026, 1, 1, 20, 0)
    ) == "evening"

    assert get_time_of_day(
        datetime(2026, 1, 1, 23, 0)
    ) == "night"


def test_normalize_mood():
    assert normalize_mood(
        "feliz"
    ) == "happy"

    assert normalize_mood(
        "concentrada"
    ) == "focused"

    assert normalize_mood(
        "cualquier_cosa"
    ) == "neutral"


def test_normalize_weather():
    assert normalize_weather(
        "lluvia"
    ) == "rain"

    assert normalize_weather(
        "soleado"
    ) == "sunny"


def test_normalize_agent_state():
    assert normalize_agent_state(
        "working"
    ) == "working"

    assert normalize_agent_state(
        "inventado"
    ) == "idle"


def test_avatar_fallback(tmp_path: Path):
    avatar = (
        tmp_path
        / "Avatar.jpeg"
    )

    avatar.write_bytes(
        b"fake-image"
    )

    resolver = AvatarResolver(
        tmp_path
    )

    result = resolver.resolve(
        AvatarContext(
            time_of_day="night",
            weather="rain",
            agent_state="working",
            mood="focused",
        )
    )

    assert result == avatar


def test_specific_avatar_has_priority(
    tmp_path: Path,
):
    default = (
        tmp_path
        / "Avatar.jpeg"
    )

    specific = (
        tmp_path
        / "working_focused.jpeg"
    )

    default.write_bytes(
        b"default"
    )

    specific.write_bytes(
        b"specific"
    )

    resolver = AvatarResolver(
        tmp_path
    )

    result = resolver.resolve(
        AvatarContext(
            time_of_day="night",
            weather="unknown",
            agent_state="working",
            mood="focused",
        )
    )

    assert result == specific


def test_ambient_mood():
    from interface.avatar_context import ambient_mood

    assert ambient_mood(
        datetime(2026, 1, 1, 2, 0)
    ) == "sleepy"

    assert ambient_mood(
        datetime(2026, 1, 1, 8, 0)
    ) == "happy"

    assert ambient_mood(
        datetime(2026, 1, 1, 14, 0)
    ) == "focused"

    assert ambient_mood(
        datetime(2026, 1, 1, 20, 0)
    ) == "neutral"


def test_explicit_mood_has_ttl():
    from interface.avatar_context import AvatarState

    state = AvatarState()

    state.update(
        agent_state="success",
        mood="happy",
    )

    ctx = state.get()

    assert ctx.mood == "happy"
    assert state.mood_remaining() > 0


def test_idle_does_not_immediately_destroy_mood():
    from interface.avatar_context import AvatarState

    state = AvatarState()

    state.update(
        agent_state="success",
        mood="happy",
    )

    state.update(
        agent_state="idle",
    )

    assert state.get().mood == "happy"
