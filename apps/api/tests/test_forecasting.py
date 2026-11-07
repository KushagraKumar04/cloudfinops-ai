import math
from datetime import date, timedelta

import pytest

from app.services.forecasting import DailySeries, ForecastError, fit_forecast


def _make_series(values: list[float]) -> DailySeries:
    start = date.today() - timedelta(days=len(values) - 1)
    dates = [start + timedelta(days=i) for i in range(len(values))]
    return DailySeries(dates=dates, values=list(values))


def test_flat_series_forecasts_flat():
    series = _make_series([100.0] * 30)
    result = fit_forecast(series, 7)
    assert len(result.forecast) == 7
    avg = sum(result.forecast) / len(result.forecast)
    assert math.isclose(avg, 100.0, rel_tol=0.25)
    assert len(result.lower) == 7
    assert len(result.upper) == 7


def test_upward_trend_forecasts_higher():
    series = _make_series([100.0 + i * 2 for i in range(30)])
    result = fit_forecast(series, 7)
    last_hist = series.values[-1]
    forecast_avg = sum(result.forecast) / len(result.forecast)
    assert forecast_avg > last_hist


def test_seasonal_pattern_detected():
    values = []
    for i in range(35):
        dow = i % 7
        base = 100.0
        if dow >= 5:
            base *= 0.5
        values.append(base)
    series = _make_series(values)
    result = fit_forecast(series, 7)
    assert result.seasonal_periods == 7
    assert result.method == "holt-winters-additive"


def test_confidence_bands_widen():
    series = _make_series([100.0 + i for i in range(30)])
    result = fit_forecast(series, 14)
    first_width = result.upper[0] - result.lower[0]
    last_width = result.upper[-1] - result.lower[-1]
    assert last_width >= first_width


def test_all_zero_series():
    series = _make_series([0.0] * 30)
    result = fit_forecast(series, 7)
    assert result.method == "flat-zero"
    assert all(v == 0.0 for v in result.forecast)


def test_insufficient_history_raises():
    series = _make_series([100.0] * 5)
    with pytest.raises(ForecastError):
        fit_forecast(series, 7)


def test_invalid_horizon_raises():
    series = _make_series([100.0] * 30)
    with pytest.raises(ForecastError):
        fit_forecast(series, 0)