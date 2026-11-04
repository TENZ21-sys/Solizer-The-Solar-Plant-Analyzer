"""
SoliZer Intelligence Platform - Inverter Analysis Engine.

Computes per-inverter performance metrics for comparison and
ranking.  Matches the report's Table 2 (Inverter Generation)
and Table 3 (Inverter PR) formats.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from app.db.models import Plant
from app.engines.aggregation import InverterAggregation
from app.engines.kpi_calculator import (
    calculate_availability,
    calculate_pr,
)


@dataclass
class InverterAnalysisResult:
    """Full analysis result for a single inverter."""
    inverter_id: int
    name: str
    block_name: str
    total_generation_kwh: float
    total_possible_generation_kwh: float
    irradiation_kwh_m2: float
    performance_ratio: float        # %
    availability: float             # %
    efficiency: float               # Gen / Possible ratio
    contribution_pct: float         # % of total plant generation
    status: str                     # 'healthy' | 'warning' | 'critical'
    grid_failure_kwh: float
    curtailment_kwh: float
    grid_loss_kwh: float
    machine_loss_kwh: float
    total_loss_kwh: float


def analyze_inverters(
    plant: Plant,
    inverter_aggs: List[InverterAggregation],
) -> List[InverterAnalysisResult]:
    """Analyze all inverters of a plant.

    Parameters
    ----------
    plant : Plant
        The plant ORM instance.
    inverter_aggs : list
        Per-inverter aggregated data from the aggregation engine.

    Returns
    -------
    list[InverterAnalysisResult]
        Sorted by inverter ID.
    """
    if not inverter_aggs:
        return []

    # Plant-level total generation for contribution %
    plant_total_gen = sum(a.total_generation for a in inverter_aggs)

    eff_frac = plant.module_efficiency / 100.0
    inv_area = plant.total_panel_area_sqm / max(plant.number_of_inverters, 1)

    results: List[InverterAnalysisResult] = []
    for inv in inverter_aggs:
        pr = calculate_pr(
            generation_kwh=inv.total_generation,
            irradiation_wh_m2_sum=inv.irradiation,
            panel_area_sqm=inv_area,
            module_efficiency_frac=eff_frac,
            daily_running_hours=plant.daily_running_hours,
        )
        avail = calculate_availability(
            total_generation_kwh=inv.total_generation,
            total_possible_generation_kwh=inv.total_possible_generation,
        )
        efficiency = (
            (inv.total_generation / inv.total_possible_generation * 100.0)
            if inv.total_possible_generation > 0
            else 0.0
        )
        contribution = (
            (inv.total_generation / plant_total_gen * 100.0)
            if plant_total_gen > 0
            else 0.0
        )

        # Total losses for this inverter
        total_loss = (
            inv.grid_failure
            + inv.curtailment
            + inv.grid_loss
            + inv.machine_loss
        )

        # Status determination
        if pr >= plant.expected_pr * 0.95:
            status = "healthy"
        elif pr >= plant.expected_pr * 0.80:
            status = "warning"
        else:
            status = "critical"

        results.append(
            InverterAnalysisResult(
                inverter_id=inv.inverter_id,
                name=inv.name,
                block_name=inv.block_name,
                total_generation_kwh=round(inv.total_generation, 1),
                total_possible_generation_kwh=round(inv.total_possible_generation, 1),
                irradiation_kwh_m2=round(inv.irradiation / 100.0, 1),
                performance_ratio=round(pr, 2),
                availability=round(avail, 2),
                efficiency=round(efficiency, 2),
                contribution_pct=round(contribution, 2),
                status=status,
                grid_failure_kwh=round(inv.grid_failure, 1),
                curtailment_kwh=round(inv.curtailment, 1),
                grid_loss_kwh=round(inv.grid_loss, 1),
                machine_loss_kwh=round(inv.machine_loss, 1),
                total_loss_kwh=round(total_loss, 1),
            )
        )

    return results
