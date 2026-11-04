"""
SoliZer Intelligence Platform - Plant Pydantic Schemas.

Pydantic v2 models for Plant CRUD operations:

* :class:`PlantCreate` – used when registering a new plant via the wizard.
* :class:`PlantUpdate` – partial update (all fields optional).
* :class:`PlantResponse` – full plant detail returned by the API.
* :class:`PlantListResponse` – lightweight summary for listing plants.
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ═══════════════════════════════════════════════════════════════════════════
# PlantCreate
# ═══════════════════════════════════════════════════════════════════════════
class PlantCreate(BaseModel):
    """Schema for creating a new plant (all wizard fields)."""

    # -- General info -------------------------------------------------------
    name: str = Field(..., min_length=1, max_length=255, description="Plant name")
    location: str = Field(..., min_length=1, max_length=255, description="Plant location / city")
    country: str = Field(..., min_length=1, max_length=100, description="Country")

    # -- Capacity -----------------------------------------------------------
    installed_dc_capacity_mw: float = Field(..., gt=0, description="Installed DC capacity in MW")
    installed_ac_capacity_mw: float = Field(..., gt=0, description="Installed AC capacity in MW")
    commission_date: date = Field(..., description="Date the plant was commissioned")

    # -- Plant topology -----------------------------------------------------
    number_of_blocks: int = Field(1, ge=1, description="Number of plant blocks")
    inverter_type: str = Field(
        "central",
        pattern=r"^(central|string)$",
        description='Inverter type: "central" or "string"',
    )
    number_of_inverters: int = Field(1, ge=1, description="Total number of inverters")

    # -- Panel info ---------------------------------------------------------
    panel_manufacturer: str = Field(..., min_length=1, max_length=255)
    panel_model: str = Field(..., min_length=1, max_length=255)
    total_panel_area_sqm: float = Field(..., gt=0, description="Total panel area in m²")
    module_efficiency: float = Field(
        ..., gt=0, le=100,
        description="Module efficiency as a percentage (e.g. 19.5)",
    )

    # -- Operational parameters ---------------------------------------------
    daily_running_hours: float = Field(..., gt=0, le=24, description="Average daily sun hours")
    annual_degradation_rate: float = Field(
        ..., ge=0, le=100,
        description="Annual degradation rate as a percentage (e.g. 0.5)",
    )

    # -- Expected performance -----------------------------------------------
    expected_pr: float = Field(
        ..., gt=0, le=100,
        description="Expected Performance Ratio (percentage)",
    )
    expected_cuf: float = Field(
        ..., gt=0, le=100,
        description="Expected Capacity Utilisation Factor (percentage)",
    )
    expected_availability: float = Field(
        ..., gt=0, le=100,
        description="Expected availability (percentage)",
    )

    # -- Grid & monitoring --------------------------------------------------
    grid_operator: str = Field(..., min_length=1, max_length=255)
    timezone: str = Field("UTC", max_length=50, description="IANA timezone string")
    has_weather_station: bool = Field(False, description="Does the plant have a weather station?")
    has_string_monitoring: bool = Field(False, description="Does the plant have string-level monitoring?")

    # -- Notes --------------------------------------------------------------
    notes: Optional[str] = Field(None, description="Free-form notes")

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "name": "Sunfield Solar Park",
                "location": "Anuradhapura",
                "country": "Sri Lanka",
                "installed_dc_capacity_mw": 10.0,
                "installed_ac_capacity_mw": 8.5,
                "commission_date": "2022-06-15",
                "number_of_blocks": 2,
                "inverter_type": "central",
                "number_of_inverters": 4,
                "panel_manufacturer": "JA Solar",
                "panel_model": "JAM72S30-545/MR",
                "total_panel_area_sqm": 52000.0,
                "module_efficiency": 21.3,
                "daily_running_hours": 5.5,
                "annual_degradation_rate": 0.5,
                "expected_pr": 78.0,
                "expected_cuf": 18.5,
                "expected_availability": 98.0,
                "grid_operator": "CEB",
                "timezone": "Asia/Colombo",
                "has_weather_station": True,
                "has_string_monitoring": False,
                "notes": "Phase 1 of the project.",
            }
        },
    )


# ═══════════════════════════════════════════════════════════════════════════
# PlantUpdate
# ═══════════════════════════════════════════════════════════════════════════
class PlantUpdate(BaseModel):
    """Schema for partially updating an existing plant (all fields optional)."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    location: Optional[str] = Field(None, min_length=1, max_length=255)
    country: Optional[str] = Field(None, min_length=1, max_length=100)

    installed_dc_capacity_mw: Optional[float] = Field(None, gt=0)
    installed_ac_capacity_mw: Optional[float] = Field(None, gt=0)
    commission_date: Optional[date] = None

    number_of_blocks: Optional[int] = Field(None, ge=1)
    inverter_type: Optional[str] = Field(None, pattern=r"^(central|string)$")
    number_of_inverters: Optional[int] = Field(None, ge=1)

    panel_manufacturer: Optional[str] = Field(None, min_length=1, max_length=255)
    panel_model: Optional[str] = Field(None, min_length=1, max_length=255)
    total_panel_area_sqm: Optional[float] = Field(None, gt=0)
    module_efficiency: Optional[float] = Field(None, gt=0, le=100)

    daily_running_hours: Optional[float] = Field(None, gt=0, le=24)
    annual_degradation_rate: Optional[float] = Field(None, ge=0, le=100)

    expected_pr: Optional[float] = Field(None, gt=0, le=100)
    expected_cuf: Optional[float] = Field(None, gt=0, le=100)
    expected_availability: Optional[float] = Field(None, gt=0, le=100)

    grid_operator: Optional[str] = Field(None, min_length=1, max_length=255)
    timezone: Optional[str] = Field(None, max_length=50)
    has_weather_station: Optional[bool] = None
    has_string_monitoring: Optional[bool] = None

    notes: Optional[str] = None

    model_config = ConfigDict(str_strip_whitespace=True)


# ═══════════════════════════════════════════════════════════════════════════
# PlantResponse
# ═══════════════════════════════════════════════════════════════════════════
class PlantResponse(BaseModel):
    """Full plant detail returned by the API (includes id & timestamps)."""

    id: int
    name: str
    location: str
    country: str

    installed_dc_capacity_mw: float
    installed_ac_capacity_mw: float
    commission_date: date

    number_of_blocks: int
    inverter_type: str
    number_of_inverters: int

    panel_manufacturer: str
    panel_model: str
    total_panel_area_sqm: float
    module_efficiency: float

    daily_running_hours: float
    annual_degradation_rate: float

    expected_pr: float
    expected_cuf: float
    expected_availability: float

    grid_operator: str
    timezone: str
    has_weather_station: bool
    has_string_monitoring: bool

    notes: Optional[str] = None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ═══════════════════════════════════════════════════════════════════════════
# PlantListResponse
# ═══════════════════════════════════════════════════════════════════════════
class PlantListResponse(BaseModel):
    """Lightweight plant summary for list/table views."""

    id: int
    name: str
    location: str
    installed_dc_capacity_mw: float
    commission_date: date

    model_config = ConfigDict(from_attributes=True)


# ═══════════════════════════════════════════════════════════════════════════
# Daily Record Manual Entry
# ═══════════════════════════════════════════════════════════════════════════
class DailyRecordInput(BaseModel):
    """Schema for manual daily log entry."""
    record_date: date = Field(..., description="Date of the record")
    generation_kwh: float = Field(..., ge=0, description="Generation in kWh")
    irradiation_wh_m2: float = Field(..., ge=0, description="Irradiation in Wh/m²")
    inverter_id: Optional[int] = Field(None, description="Optional specific inverter ID. If None, distributed across all plant inverters.")
    grid_failure_kwh: float = Field(0.0, ge=0, description="Grid failure loss in kWh")
    curtailment_kwh: float = Field(0.0, ge=0, description="Curtailment loss in kWh")
    grid_loss_kwh: float = Field(0.0, ge=0, description="Grid loss in kWh")
    machine_loss_kwh: float = Field(0.0, ge=0, description="Machine/inverter loss in kWh")


class DailyRecordInputResponse(BaseModel):
    """Response returned after manual daily record entry."""
    success: bool
    message: str
    records_updated: int
    record_date: date

