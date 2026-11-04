"""
SoliZer Intelligence Platform - KPI Calculator Engine.

Computes the three core Key Performance Indicators:

1. **Performance Ratio (PR %)**
   PR = Gen_kWh / (Σ daily_Irr_Wm2 × Area_m2 × Eff × Hours / 1000) × 100

2. **Capacity Utilisation Factor (CUF %)**
   CUF = Total_Gen_MWh / (AC_Capacity_MW × Total_Hours) × 100

3. **Specific Yield (kWh/kWp)**
   SY = Total_Gen_kWh / DC_Capacity_kWp

All formulas match the PR calculation documented in the Example report:
  PR(%) = Generation(kWh) / (Irradiance(W/sqm) × Panel Area(sqm)
           × Module Efficiency × Running Hours/day) × 100%
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from app.db.models import Plant
from app.engines.aggregation import (
    DailyPlantRecord,
    MonthlyPlantRecord,
    LifetimePlantRecord,
    InverterAggregation,
)


@dataclass
class KPIResult:
    """Calculated KPIs for a given aggregation period."""
    performance_ratio: float    # %
    cuf: float                  # %
    specific_yield: float       # kWh/kWp
    energy_yield_kwh: float     # total generation kWh
    average_daily_generation_kwh: float


@dataclass
class MonthlyKPI:
    """Monthly KPI data point (for charting)."""
    year: int
    month: int
    label: str                  # e.g. "May 2023"
    generation_mwh: float
    irradiation_kwh_m2: float
    pr: float                   # %
    cuf: float                  # %
    specific_yield: float       # kWh/kWp


# ═══════════════════════════════════════════════════════════════════════
# Core calculation functions
# ═══════════════════════════════════════════════════════════════════════

def calculate_pr(
    generation_kwh: float,
    irradiation_wh_m2_sum: float,
    panel_area_sqm: float,
    module_efficiency_frac: float,
    daily_running_hours: float,
) -> float:
    """Calculate Performance Ratio (%).

    Parameters
    ----------
    generation_kwh : float
        Total generation in kWh for the period.
    irradiation_wh_m2_sum : float
        Sum of daily irradiation values in Wh/m² for the period.
    panel_area_sqm : float
        Total panel area in m².
    module_efficiency_frac : float
        Module efficiency as a fraction (e.g. 0.21 for 21%).
    daily_running_hours : float
        Assumed daily running hours (e.g. 5.5).

    Returns
    -------
    float
        Performance Ratio as a percentage.
    """
    denominator = (
        irradiation_wh_m2_sum
        * panel_area_sqm
        * module_efficiency_frac
        * daily_running_hours
        / 1000.0  # convert Wh to kWh
    )
    if denominator <= 0:
        return 0.0
    return (generation_kwh / denominator) * 100.0


def calculate_temperature_corrected_pr(
    pr: float,
    cell_temperature_c: float = 35.0,
    temp_coefficient: float = -0.004,
) -> float:
    """Calculate IEC 61724 Temperature-Corrected Performance Ratio (%).

    PR_STC = PR / [1 + gamma * (T_cell - 25)]
    Where:
    - gamma: temperature coefficient of power (fraction/°C, default -0.004 / -0.40%/°C)
    - cell_temperature_c: average PV cell temperature in °C (default 35°C)
    """
    correction_factor = 1.0 + temp_coefficient * (cell_temperature_c - 25.0)
    if correction_factor <= 0:
        return pr
    return pr / correction_factor


def calculate_cuf(
    generation_kwh: float,
    ac_capacity_mw: float,
    total_hours: float,
) -> float:
    """Calculate Capacity Utilisation Factor (%).

    CUF = Gen(MWh) / (AC_Capacity(MW) × Hours) × 100
    """
    if ac_capacity_mw <= 0 or total_hours <= 0:
        return 0.0
    generation_mwh = generation_kwh / 1000.0
    return (generation_mwh / (ac_capacity_mw * total_hours)) * 100.0


def calculate_specific_yield(
    generation_kwh: float,
    dc_capacity_mw: float,
) -> float:
    """Calculate Specific Yield (kWh/kWp).

    SY = Gen(kWh) / DC_Capacity(kWp)
    """
    dc_capacity_kwp = dc_capacity_mw * 1000.0  # MW → kWp
    if dc_capacity_kwp <= 0:
        return 0.0
    return generation_kwh / dc_capacity_kwp


def calculate_availability(
    total_generation_kwh: float,
    total_possible_generation_kwh: float,
) -> float:
    """Calculate Plant Availability (%).

    Availability = Actual Generation / Possible Generation × 100
    """
    if total_possible_generation_kwh <= 0:
        return 0.0
    return (total_generation_kwh / total_possible_generation_kwh) * 100.0


# ═══════════════════════════════════════════════════════════════════════
# High-level KPI computation
# ═══════════════════════════════════════════════════════════════════════

def compute_lifetime_kpis(
    plant: Plant,
    lifetime: LifetimePlantRecord,
) -> KPIResult:
    """Compute KPIs from a lifetime aggregation."""
    eff_frac = plant.module_efficiency / 100.0
    total_hours = lifetime.days * 24.0

    pr = calculate_pr(
        generation_kwh=lifetime.total_generation,
        irradiation_wh_m2_sum=lifetime.irradiation,
        panel_area_sqm=plant.total_panel_area_sqm,
        module_efficiency_frac=eff_frac,
        daily_running_hours=plant.daily_running_hours,
    )
    cuf = calculate_cuf(
        generation_kwh=lifetime.total_generation,
        ac_capacity_mw=plant.installed_ac_capacity_mw,
        total_hours=total_hours,
    )
    sy = calculate_specific_yield(
        generation_kwh=lifetime.total_generation,
        dc_capacity_mw=plant.installed_dc_capacity_mw,
    )
    avg_daily = (
        lifetime.total_generation / lifetime.days
        if lifetime.days > 0
        else 0.0
    )

    return KPIResult(
        performance_ratio=round(pr, 2),
        cuf=round(cuf, 2),
        specific_yield=round(sy, 1),
        energy_yield_kwh=round(lifetime.total_generation, 1),
        average_daily_generation_kwh=round(avg_daily, 1),
    )


_MONTH_NAMES = [
    "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


def compute_monthly_kpis(
    plant: Plant,
    monthly_records: List[MonthlyPlantRecord],
) -> List[MonthlyKPI]:
    """Compute KPIs for each month."""
    eff_frac = plant.module_efficiency / 100.0
    results: List[MonthlyKPI] = []

    for m in monthly_records:
        total_hours = m.days * 24.0
        pr = calculate_pr(
            generation_kwh=m.total_generation,
            irradiation_wh_m2_sum=m.irradiation,
            panel_area_sqm=plant.total_panel_area_sqm,
            module_efficiency_frac=eff_frac,
            daily_running_hours=plant.daily_running_hours,
        )
        cuf = calculate_cuf(
            generation_kwh=m.total_generation,
            ac_capacity_mw=plant.installed_ac_capacity_mw,
            total_hours=total_hours,
        )
        sy = calculate_specific_yield(
            generation_kwh=m.total_generation,
            dc_capacity_mw=plant.installed_dc_capacity_mw,
        )
        label = f"{_MONTH_NAMES[m.month]} {m.year}"
        irr_kwh_m2 = m.irradiation / 100.0  # Wh/m² → kWh/m² (÷100 per report convention)

        results.append(
            MonthlyKPI(
                year=m.year,
                month=m.month,
                label=label,
                generation_mwh=round(m.total_generation / 1000.0, 1),
                irradiation_kwh_m2=round(irr_kwh_m2, 1),
                pr=round(pr, 2),
                cuf=round(cuf, 2),
                specific_yield=round(sy, 1),
            )
        )

    return results


def compute_inverter_pr(
    plant: Plant,
    inv_agg: InverterAggregation,
) -> float:
    """Compute PR for a single inverter.

    Uses per-inverter area = total_area / number_of_inverters.
    """
    eff_frac = plant.module_efficiency / 100.0
    inv_area = plant.total_panel_area_sqm / max(plant.number_of_inverters, 1)

    return calculate_pr(
        generation_kwh=inv_agg.total_generation,
        irradiation_wh_m2_sum=inv_agg.irradiation,
        panel_area_sqm=inv_area,
        module_efficiency_frac=eff_frac,
        daily_running_hours=plant.daily_running_hours,
    )
