"""
SoliZer Intelligence Platform - Analytics Pydantic Schemas.

Pydantic v2 response models used by the analytics / dashboard endpoints.
"""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ═══════════════════════════════════════════════════════════════════════════
# Alert & Recommendation Responses
# ═══════════════════════════════════════════════════════════════════════════
class AlertResponse(BaseModel):
    """Schema for returning Alert records."""

    id: int
    plant_id: int
    severity: str  # 'info', 'warning', 'critical'
    category: str
    title: Optional[str] = None
    message: str
    status: str  # 'active', 'resolved'
    resolved_date: Optional[date] = None
    is_read: Optional[bool] = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecommendationResponse(BaseModel):
    """Schema for returning Recommendation records."""

    id: int
    plant_id: int
    generated_date: date
    category: str
    title: Optional[str] = None
    description: str
    priority: str  # 'low', 'medium', 'high'
    potential_gain_kwh: Optional[float] = 0.0
    status: str  # 'pending', 'in_progress', 'completed', 'dismissed'
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ═══════════════════════════════════════════════════════════════════════════
# Dashboard Components
# ═══════════════════════════════════════════════════════════════════════════
class GenerationDataPoint(BaseModel):
    """A single actual vs expected generation data point."""

    date: str
    actual_kwh: float
    expected_kwh: float
    pr: Optional[float] = None
    cuf: Optional[float] = None
    irradiation: Optional[float] = None
    specific_yield: Optional[float] = None



class LossCategory(BaseModel):
    """Categorized loss figure with styling details."""

    category: str
    value: float
    color: str


class DashboardSummary(BaseModel):
    """High-level KPIs and summaries displayed on the plant dashboard."""

    total_generation_kwh: float
    possible_generation_kwh: float
    performance_ratio: float
    cuf: float
    availability: float
    loss_percentage: float
    health_score: float
    degradation_index: float
    generation_trend: List[GenerationDataPoint] = Field(default_factory=list)
    loss_breakdown: List[LossCategory] = Field(default_factory=list)
    recent_alerts: List[AlertResponse] = Field(default_factory=list)
    top_recommendations: List[RecommendationResponse] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# Generation Analysis
# ═══════════════════════════════════════════════════════════════════════════
class GenerationData(BaseModel):
    """Generation overview and details for a selected period."""

    period: str
    data: List[GenerationDataPoint] = Field(default_factory=list)
    total_actual_kwh: float
    total_expected_kwh: float
    average_pr: float


# ═══════════════════════════════════════════════════════════════════════════
# Key Performance Indicators (KPI)
# ═══════════════════════════════════════════════════════════════════════════
class KPIData(BaseModel):
    """Calculated plant key performance indicators."""

    plant_id: int
    performance_ratio: float
    capacity_utilisation_factor: float
    specific_yield: float
    energy_yield_kwh: float
    average_daily_generation_kwh: float


# ═══════════════════════════════════════════════════════════════════════════
# Inverter Analysis
# ═══════════════════════════════════════════════════════════════════════════
class InverterSummary(BaseModel):
    """Per-inverter performance summary for comparison views."""

    inverter_id: str
    name: str
    capacity_kw: float
    total_generation_kwh: float
    performance_ratio: float
    availability: float
    status: str  # 'healthy' | 'warning' | 'critical' | 'offline'
    efficiency: float
    specific_yield: Optional[float] = None
    machine_loss_kwh: Optional[float] = None


class InverterTimeSeriesPoint(BaseModel):
    """Comparative inverter metric data point for time-series charts."""

    date: str
    inverter_name: str
    generation_kwh: float
    pr: float
    specific_yield: float
    machine_loss_kwh: float


class InverterResponse(BaseModel):
    """Inverter list summary and comparative time series."""

    summaries: List[InverterSummary]
    time_series: List[InverterTimeSeriesPoint] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# Loss Breakdown
# ═══════════════════════════════════════════════════════════════════════════
class LossDetail(BaseModel):
    """Categorized loss details."""

    category: str
    loss_kwh: float
    loss_percentage: float
    description: str
    color: str


class LossDataPoint(BaseModel):
    """A point representing loss figures grouped by period."""

    date: str
    grid_failure_kwh: float
    curtailment_kwh: float
    machine_loss_kwh: float
    total_loss_kwh: float


class LossBreakdown(BaseModel):
    """Detailed loss analysis for the plant."""

    total_loss_kwh: float
    total_loss_percentage: float
    categories: List[LossDetail] = Field(default_factory=list)
    time_series: List[LossDataPoint] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# Degradation Analysis
# ═══════════════════════════════════════════════════════════════════════════
class DegradationDataPoint(BaseModel):
    """A year-over-year degradation comparison point."""

    year: str
    pr: float
    expected_pr: float


class DegradationData(BaseModel):
    """Year-over-year degradation metrics."""

    annual_degradation_rate: float
    cumulative_degradation: float
    expected_lifetime_years: float
    expected_degradation: float = 0.0
    trend: List[DegradationDataPoint] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# Irradiation
# ═══════════════════════════════════════════════════════════════════════════
class IrradiationDataPoint(BaseModel):
    """A point representing irradiation figures grouped by period."""

    date: str
    ghi_kwh_m2: float
    poa_kwh_m2: float
    peak_sun_hours: float


class IrradiationData(BaseModel):
    """Irradiation metrics (GHI, POA, etc.)."""

    plant_id: int
    total_ghi_kwh_m2: float
    total_poa_kwh_m2: float
    average_daily_ghi: float
    average_daily_poa: float
    peak_sun_hours: float
    data: List[IrradiationDataPoint] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# Report Generation
# ═══════════════════════════════════════════════════════════════════════════
class ReportGenerateRequest(BaseModel):
    """Request payload for report generation."""

    report_type: str  # 'pdf' or 'docx'
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class ReportResponse(BaseModel):
    """Metadata for a generated report."""

    id: int
    plant_id: int
    report_type: str
    title: str
    file_path: Optional[str] = None
    generated_at: datetime
    period_start: date
    period_end: date
    status: str  # 'generating' | 'completed' | 'failed'
    message: Optional[str] = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )
