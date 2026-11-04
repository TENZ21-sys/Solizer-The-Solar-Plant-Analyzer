"""
SoliZer Intelligence Platform - Plant Aggregation Engine.

Aggregates inverter-level daily records into plant-level metrics
at daily, monthly, annual, and lifetime granularities.

Key conventions
───────────────
* **Irradiation** is stored per-inverter but represents a plant-wide
  measurement (all inverters share the same pyranometer).  When
  aggregating to the plant level we therefore take the **average**
  across inverters for each day rather than summing.
* **Generation / losses** are additive across inverters, so they are
  **summed**.
* The raw irradiation values in the database are in **Wh/m²** (daily
  totals).  Divide by 100 to convert to **kWh/m²** (verified against
  Example report: sum of daily values ÷ 100 ≈ 1907.5 kWh/m²/year).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import DailyRecord, Inverter, Plant


# ═══════════════════════════════════════════════════════════════════════
# Data classes for aggregated results
# ═══════════════════════════════════════════════════════════════════════
@dataclass
class DailyPlantRecord:
    """Plant-level aggregated record for a single day."""
    record_date: date
    generation: float            # kWh (sum of all inverters)
    irradiation: float           # Wh/m² daily (average across inverters)
    grid_failure: float          # kWh
    curtailment: float           # kWh
    grid_loss: float             # kWh
    machine_loss: float          # kWh
    total_generation: float      # kWh  (Gen + Curtailment)
    total_possible_generation: float  # kWh
    num_inverters: int           # count of inverters reporting that day


@dataclass
class MonthlyPlantRecord:
    """Plant-level aggregated record for a single month."""
    year: int
    month: int
    generation: float            # kWh
    irradiation: float           # Wh/m² monthly total (avg daily per day, summed)
    grid_failure: float
    curtailment: float
    grid_loss: float
    machine_loss: float
    total_generation: float
    total_possible_generation: float
    days: int                    # calendar days with data


@dataclass
class AnnualPlantRecord:
    """Plant-level aggregated record for a fiscal/study year."""
    label: str                   # e.g. "2023-2024" (May-Apr)
    generation: float
    irradiation: float           # Wh/m² annual total
    grid_failure: float
    curtailment: float
    grid_loss: float
    machine_loss: float
    total_generation: float
    total_possible_generation: float
    days: int
    monthly_records: List[MonthlyPlantRecord] = field(default_factory=list)


@dataclass
class LifetimePlantRecord:
    """Plant-level aggregated record across all imported data."""
    generation: float
    irradiation: float
    grid_failure: float
    curtailment: float
    grid_loss: float
    machine_loss: float
    total_generation: float
    total_possible_generation: float
    days: int
    date_start: Optional[date] = None
    date_end: Optional[date] = None


# ═══════════════════════════════════════════════════════════════════════
# Aggregation functions
# ═══════════════════════════════════════════════════════════════════════

def get_daily_plant_records(
    db: Session,
    plant_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> List[DailyPlantRecord]:
    """Aggregate inverter-level daily records to plant-level daily records.

    For each calendar date that has at least one inverter record:
      - generation, losses → SUM across inverters
      - irradiation → AVG across inverters (plant-wide sensor)
    """
    inverter_ids = [
        r[0] for r in db.query(Inverter.id).filter(Inverter.plant_id == plant_id).all()
    ]

    query = db.query(
        DailyRecord.record_date,
        func.sum(DailyRecord.generation).label("generation"),
        func.avg(DailyRecord.irradiation).label("irradiation"),
        func.sum(DailyRecord.grid_failure).label("grid_failure"),
        func.sum(DailyRecord.curtailment).label("curtailment"),
        func.sum(DailyRecord.grid_loss).label("grid_loss"),
        func.sum(DailyRecord.machine_loss).label("machine_loss"),
        func.sum(DailyRecord.total_generation).label("total_generation"),
        func.sum(DailyRecord.total_possible_generation).label("total_possible_generation"),
        func.count(DailyRecord.id).label("num_inverters"),
    ).filter(DailyRecord.inverter_id.in_(inverter_ids))

    if start_date:
        query = query.filter(DailyRecord.record_date >= start_date)
    if end_date:
        query = query.filter(DailyRecord.record_date <= end_date)

    rows = query.group_by(DailyRecord.record_date).order_by(DailyRecord.record_date).all()

    return [
        DailyPlantRecord(
            record_date=r.record_date,
            generation=float(r.generation or 0),
            irradiation=float(r.irradiation or 0),
            grid_failure=float(r.grid_failure or 0),
            curtailment=float(r.curtailment or 0),
            grid_loss=float(r.grid_loss or 0),
            machine_loss=float(r.machine_loss or 0),
            total_generation=float(r.total_generation or 0),
            total_possible_generation=float(r.total_possible_generation or 0),
            num_inverters=int(r.num_inverters or 0),
        )
        for r in rows
    ]


def aggregate_to_monthly(
    daily_records: List[DailyPlantRecord],
) -> List[MonthlyPlantRecord]:
    """Roll up daily plant records into monthly plant records."""
    buckets: Dict[Tuple[int, int], List[DailyPlantRecord]] = defaultdict(list)
    for d in daily_records:
        buckets[(d.record_date.year, d.record_date.month)].append(d)

    monthly: List[MonthlyPlantRecord] = []
    for (year, month), days in sorted(buckets.items()):
        monthly.append(
            MonthlyPlantRecord(
                year=year,
                month=month,
                generation=sum(d.generation for d in days),
                irradiation=sum(d.irradiation for d in days),
                grid_failure=sum(d.grid_failure for d in days),
                curtailment=sum(d.curtailment for d in days),
                grid_loss=sum(d.grid_loss for d in days),
                machine_loss=sum(d.machine_loss for d in days),
                total_generation=sum(d.total_generation for d in days),
                total_possible_generation=sum(
                    d.total_possible_generation for d in days
                ),
                days=len(days),
            )
        )
    return monthly


def aggregate_to_lifetime(
    daily_records: List[DailyPlantRecord],
) -> LifetimePlantRecord:
    """Aggregate all daily records into a single lifetime summary."""
    if not daily_records:
        return LifetimePlantRecord(
            generation=0, irradiation=0, grid_failure=0,
            curtailment=0, grid_loss=0, machine_loss=0,
            total_generation=0, total_possible_generation=0,
            days=0,
        )

    return LifetimePlantRecord(
        generation=sum(d.generation for d in daily_records),
        irradiation=sum(d.irradiation for d in daily_records),
        grid_failure=sum(d.grid_failure for d in daily_records),
        curtailment=sum(d.curtailment for d in daily_records),
        grid_loss=sum(d.grid_loss for d in daily_records),
        machine_loss=sum(d.machine_loss for d in daily_records),
        total_generation=sum(d.total_generation for d in daily_records),
        total_possible_generation=sum(
            d.total_possible_generation for d in daily_records
        ),
        days=len(daily_records),
        date_start=daily_records[0].record_date,
        date_end=daily_records[-1].record_date,
    )


# ═══════════════════════════════════════════════════════════════════════
# Per-Inverter aggregation
# ═══════════════════════════════════════════════════════════════════════
@dataclass
class InverterAggregation:
    """Aggregated metrics for a single inverter."""
    inverter_id: int
    name: str
    block_name: str
    generation: float
    irradiation: float
    grid_failure: float
    curtailment: float
    grid_loss: float
    machine_loss: float
    total_generation: float
    total_possible_generation: float
    days: int


def get_per_inverter_aggregations(
    db: Session,
    plant_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> List[InverterAggregation]:
    """Return lifetime aggregated metrics per inverter."""
    query = (
        db.query(
            Inverter.id,
            Inverter.name,
            Inverter.block_name,
            func.sum(DailyRecord.generation).label("generation"),
            func.sum(DailyRecord.irradiation).label("irradiation"),
            func.sum(DailyRecord.grid_failure).label("grid_failure"),
            func.sum(DailyRecord.curtailment).label("curtailment"),
            func.sum(DailyRecord.grid_loss).label("grid_loss"),
            func.sum(DailyRecord.machine_loss).label("machine_loss"),
            func.sum(DailyRecord.total_generation).label("total_generation"),
            func.sum(DailyRecord.total_possible_generation).label("total_possible_generation"),
            func.count(DailyRecord.id).label("days"),
        )
        .join(DailyRecord, DailyRecord.inverter_id == Inverter.id)
        .filter(Inverter.plant_id == plant_id)
    )

    if start_date:
        query = query.filter(DailyRecord.record_date >= start_date)
    if end_date:
        query = query.filter(DailyRecord.record_date <= end_date)

    rows = query.group_by(Inverter.id).order_by(Inverter.id).all()

    return [
        InverterAggregation(
            inverter_id=r.id,
            name=r.name,
            block_name=r.block_name,
            generation=float(r.generation or 0),
            irradiation=float(r.irradiation or 0),
            grid_failure=float(r.grid_failure or 0),
            curtailment=float(r.curtailment or 0),
            grid_loss=float(r.grid_loss or 0),
            machine_loss=float(r.machine_loss or 0),
            total_generation=float(r.total_generation or 0),
            total_possible_generation=float(r.total_possible_generation or 0),
            days=int(r.days or 0),
        )
        for r in rows
    ]
