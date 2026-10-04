from interface.weather import (
    weather_code_to_condition,
)


def test_clear_weather():
    assert weather_code_to_condition(
        0
    ) == "sunny"


def test_cloud_weather():
    assert weather_code_to_condition(
        3
    ) == "cloudy"


def test_rain_weather():
    assert weather_code_to_condition(
        61
    ) == "rain"

    assert weather_code_to_condition(
        82
    ) == "rain"


def test_storm_weather():
    assert weather_code_to_condition(
        95
    ) == "storm"


def test_snow_weather():
    assert weather_code_to_condition(
        71
    ) == "snow"


def test_fog_weather():
    assert weather_code_to_condition(
        45
    ) == "fog"


def test_unknown_weather():
    assert weather_code_to_condition(
        999
    ) == "unknown"

    assert weather_code_to_condition(
        None
    ) == "unknown"
