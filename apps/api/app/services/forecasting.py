import math
import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from app.models.cost import CostRecord


class ForecastError(Exception):
    pass


@dataclass
class DailySeries:
    dates: list[date]
    values: list[float]

    def as_numpy(self) -> np.ndarray:
        return np.array(self.values, dtype=float)


@dataclass
class ForecastResult:
    method: str
    forecast: list[float]
    lower: list[float]
    upper: list[float]
    residual_std: float
    seasonal_periods: int | None


SEASONAL_PERIODS = 7
MIN_HISTORY = 14
Z_80 = 1.2816


def load_daily_series(
    db: Session,
    tenant_id: uuid.UUID,
    provider: str | None = None,
    service: str | None = None,
) -> DailySeries:
    stmt = select(CostRecord.date, CostRecord.cost).where(CostRecord.tenant_id == tenant_id)
    if provider and provider != "all":
        stmt = stmt.where(CostRecord.provider == provider)
    if service and service != "all":
        stmt = stmt.where(CostRecord.service == service)
    rows = list(db.execute(stmt).all())
    if not rows:
        return DailySeries(dates=[], values=[])

    by_date: dict[date, float] = {}
    for d, cost in rows:
        by_date[d] = by_date.get(d, 0.0) + float(cost)

    sorted_dates = sorted(by_date.keys())
    start = sorted_dates[0]
    end = sorted_dates[-1]
    span = (end - start).days + 1
    full_dates = [start + timedelta(days=i) for i in range(span)]
    full_values = [by_date.get(d, 0.0) for d in full_dates]
    return DailySeries(dates=full_dates, values=full_values)


def _fit_seasonal(arr: np.ndarray, horizon: int) -> tuple[np.ndarray, np.ndarray, str]:
    model = ExponentialSmoothing(
        arr,
        trend="add",
        seasonal="add",
        seasonal_periods=SEASONAL_PERIODS,
        initialization_method="estimated",
    )
    fit = model.fit(optimized=True)
    return np.asarray(fit.forecast(horizon)), np.asarray(fit.fittedvalues), "holt-winters-additive"


def _fit_trend(arr: np.ndarray, horizon: int) -> tuple[np.ndarray, np.ndarray, str]:
    model = ExponentialSmoothing(
        arr,
        trend="add",
        seasonal=None,
        initialization_method="estimated",
    )
    fit = model.fit(optimized=True)
    return np.asarray(fit.forecast(horizon)), np.asarray(fit.fittedvalues), "holt-linear"


def _band(forecast: list[float], residual_std: float) -> tuple[list[float], list[float]]:
    lower: list[float] = []
    upper: list[float] = []
    for i, v in enumerate(forecast):
        width = residual_std * Z_80 * math.sqrt(i + 1)
        lower.append(max(0.0, v - width))
        upper.append(v + width)
    return lower, upper


def fit_forecast(series: DailySeries, horizon: int) -> ForecastResult:
    if len(series.values) < MIN_HISTORY:
        raise ForecastError(f"Need at least {MIN_HISTORY} days of history")
    if horizon < 1:
        raise ForecastError("Horizon must be at least 1 day")

    arr = np.maximum(np.asarray(series.values, dtype=float), 0.0)

    if np.all(arr == 0):
        zeros = [0.0] * horizon
        return ForecastResult(
            method="flat-zero",
            forecast=zeros,
            lower=list(zeros),
            upper=list(zeros),
            residual_std=0.0,
            seasonal_periods=None,
        )

    forecast_arr: np.ndarray | None = None
    fitted_arr: np.ndarray | None = None
    method = ""
    seasonal_periods: int | None = None

    if len(arr) >= 2 * SEASONAL_PERIODS:
        try:
            forecast_arr, fitted_arr, method = _fit_seasonal(arr, horizon)
            seasonal_periods = SEASONAL_PERIODS
        except Exception:
            forecast_arr = None
            fitted_arr = None

    if forecast_arr is None:
        try:
            forecast_arr, fitted_arr, method = _fit_trend(arr, horizon)
        except Exception as exc:
            raise ForecastError(f"Model fitting failed: {exc}") from exc

    assert forecast_arr is not None and fitted_arr is not None

    aligned = arr[-len(fitted_arr):]
    residuals = aligned - fitted_arr
    residual_std = float(np.std(residuals)) if residuals.size > 0 else 0.0
    if residual_std <= 0:
        mean_val = float(np.mean(arr))
        residual_std = mean_val * 0.08 if mean_val > 0 else 0.0

    forecast_values = [max(0.0, float(v)) for v in forecast_arr]
    lower, upper = _band(forecast_values, residual_std)

    return ForecastResult(
        method=method,
        forecast=forecast_values,
        lower=lower,
        upper=upper,
        residual_std=residual_std,
        seasonal_periods=seasonal_periods,
    )


def trend_pct(result: ForecastResult, horizon_days: int) -> float:
    if not result.forecast:
        return 0.0
    first = result.forecast[0]
    last = result.forecast[-1]
    if first <= 0:
        return 0.0
    return round((last - first) / first * 100, 2)


def trend_direction(pct: float) -> str:
    if pct > 1:
        return "up"
    if pct < -1:
        return "down"
    return "flat"


def list_services(db: Session, tenant_id: uuid.UUID, provider: str | None = None) -> list[tuple[str, str]]:
    stmt = select(CostRecord.service, CostRecord.provider).where(CostRecord.tenant_id == tenant_id)
    if provider and provider != "all":
        stmt = stmt.where(CostRecord.provider == provider)
    rows = db.execute(stmt).all()
    seen: dict[str, str] = {}
    for service, prov in rows:
        if service not in seen:
            seen[service] = prov
    return sorted(seen.items())


def current_window_total(series: DailySeries, days: int = 30) -> float:
    if not series.values:
        return 0.0
    window = series.values[-days:]
    return round(float(sum(window)), 2)