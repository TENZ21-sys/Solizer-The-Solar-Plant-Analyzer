"""
SoliZer Intelligence Platform - Irradiation Analysis Engine.

Computes irradiation metrics matching the Example report's
Table 4 (Annual Irradiation Summary) and Section 3.

The raw irradiation values in the database are in Wh/m² (daily).
Annual totals are converted to kWh/m² by dividing the sum by 100
(verified: 190748.9 / 100 = 1907.5 kWh/m²).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from app.engines.aggregation import (
    DailyPlantRecord,
    MonthlyPlantRecord,
    LifetimePlantRecord,
)


@dataclass
class IrradiationResult:
    """Lifetime irradiation summary."""
    total_irradiation_kwh_m2: float     # kWh/m²
    average_daily_wh_m2: float          # Wh/m² per day
    average_daily_kwh_m2: float         # kWh/m² per day
    peak_sun_hours: float               # equivalent peak sun hours per day
    days: int


@dataclass
class MonthlyIrradiation:
    """Monthly irradiation data point."""
    year: int
    month: int
    label: str
    irradiation_kwh_m2: float           # total for the month
    avg_daily_wh_m2: float              # daily average in Wh/m²
    days: int


def compute_irradiation_analysis(
    lifetime: LifetimePlantRecord,
    daily_records: List[DailyPlantRecord],
) -> IrradiationResult:
    """Compute irradiation summary from lifetime and daily data.

    Peak Sun Hours = total irradiation (kWh/m²) / days
    (equivalent to the average daily insolation in kWh/m²/day,
     which also represents peak sun hours at 1 kW/m² standard).
    """
    if not daily_records:
        return IrradiationResult(
            total_irradiation_kwh_m2=0,
            average_daily_wh_m2=0,
            average_daily_kwh_m2=0,
            peak_sun_hours=0,
            days=0,
        )

    # Total irradiation: sum of daily Wh/m² values / 100 = kWh/m²
    total_kwh_m2 = lifetime.irradiation / 100.0
    avg_daily_wh_m2 = lifetime.irradiation / lifetime.days if lifetime.days > 0 else 0
    avg_daily_kwh_m2 = total_kwh_m2 / lifetime.days if lifetime.days > 0 else 0

    # Peak sun hours = average daily kWh/m² (since 1 peak sun hour = 1 kWh/m²)
    peak_sun_hours = avg_daily_kwh_m2

    return IrradiationResult(
        total_irradiation_kwh_m2=round(total_kwh_m2, 1),
        average_daily_wh_m2=round(avg_daily_wh_m2, 1),
        average_daily_kwh_m2=round(avg_daily_kwh_m2, 2),
        peak_sun_hours=round(peak_sun_hours, 2),
        days=lifetime.days,
    )


def compute_monthly_irradiation(
    monthly_records: List[MonthlyPlantRecord],
) -> List[MonthlyIrradiation]:
    """Compute monthly irradiation breakdowns.

    Each monthly record's ``irradiation`` field is the sum of
    daily Wh/m² values for that month.
    """
    _MONTH_NAMES = [
        "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]
    results: List[MonthlyIrradiation] = []
    for m in monthly_records:
        irr_kwh_m2 = m.irradiation / 100.0
        avg_daily = m.irradiation / m.days if m.days > 0 else 0
        results.append(
            MonthlyIrradiation(
                year=m.year,
                month=m.month,
                label=f"{_MONTH_NAMES[m.month]} {m.year}",
                irradiation_kwh_m2=round(irr_kwh_m2, 1),
                avg_daily_wh_m2=round(avg_daily, 1),
                days=m.days,
            )
        )
    return results


def find_peak_and_lowest_months(
    monthly_irr: List[MonthlyIrradiation],
) -> tuple[Optional[str], Optional[str]]:
    """Find the month with highest and lowest irradiation."""
    if not monthly_irr:
        return None, None

    peak = max(monthly_irr, key=lambda m: m.irradiation_kwh_m2)
    lowest = min(monthly_irr, key=lambda m: m.irradiation_kwh_m2)
    return peak.label, lowest.label
