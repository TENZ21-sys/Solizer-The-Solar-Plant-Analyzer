"""
SoliZer Intelligence Platform - SQLAlchemy ORM Models.

Defines all database tables used by SoliZer:

* **Plant** – core entity representing a solar power plant.
* **Inverter** – individual inverter within a plant.
* **DailyRecord** – per-inverter daily performance data.
* **Alert** – operational alerts raised during analysis.
* **Recommendation** – AI-generated recommendations for a plant.
* **Report** – generated PDF/DOCX report metadata.
* **SystemSettings** – key/value settings (global or per-plant).

All models include ``created_at`` / ``updated_at`` audit timestamps
(where applicable) and use SQLAlchemy 2.0 ``mapped_column`` syntax.
"""

from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


# ---------------------------------------------------------------------------
# Helper: default timestamp functions
# ---------------------------------------------------------------------------
def _utcnow() -> datetime:
    """Return the current UTC datetime (timezone-naive)."""
    return datetime.utcnow()


# ═══════════════════════════════════════════════════════════════════════════
# Plant
# ═══════════════════════════════════════════════════════════════════════════
class Plant(Base):
    """A solar power plant registered in SoliZer.

    Stores all static configuration data collected during the plant-setup
    wizard: capacity, panel specs, expected performance ratios, etc.
    """

    __tablename__ = "plants"

    # -- Primary key --------------------------------------------------------
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # -- General info -------------------------------------------------------
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False)

    # -- Capacity -----------------------------------------------------------
    installed_dc_capacity_mw: Mapped[float] = mapped_column(Float, nullable=False)
    installed_ac_capacity_mw: Mapped[float] = mapped_column(Float, nullable=False)
    commission_date: Mapped[date] = mapped_column(Date, nullable=False)

    # -- Plant topology -----------------------------------------------------
    number_of_blocks: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    inverter_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="central",
        comment='Either "central" or "string"',
    )
    number_of_inverters: Mapped[int] = mapped_column(Integer, nullable=False)

    # -- Panel info ---------------------------------------------------------
    panel_manufacturer: Mapped[str] = mapped_column(String(255), nullable=False)
    panel_model: Mapped[str] = mapped_column(String(255), nullable=False)
    total_panel_area_sqm: Mapped[float] = mapped_column(Float, nullable=False)
    module_efficiency: Mapped[float] = mapped_column(
        Float, nullable=False,
        comment="Module efficiency as a percentage (e.g. 19.5)",
    )

    # -- Operational parameters ---------------------------------------------
    daily_running_hours: Mapped[float] = mapped_column(Float, nullable=False)
    annual_degradation_rate: Mapped[float] = mapped_column(
        Float, nullable=False,
        comment="Expected annual degradation as a percentage (e.g. 0.5)",
    )

    # -- Expected performance -----------------------------------------------
    expected_pr: Mapped[float] = mapped_column(
        Float, nullable=False,
        comment="Expected Performance Ratio (0-1 or percentage)",
    )
    expected_cuf: Mapped[float] = mapped_column(
        Float, nullable=False,
        comment="Expected Capacity Utilisation Factor (0-1 or percentage)",
    )
    expected_availability: Mapped[float] = mapped_column(
        Float, nullable=False,
        comment="Expected availability (0-1 or percentage)",
    )

    # -- Grid & monitoring --------------------------------------------------
    grid_operator: Mapped[str] = mapped_column(String(255), nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="UTC")
    has_weather_station: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_string_monitoring: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # -- Notes --------------------------------------------------------------
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # -- Audit timestamps ---------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow, onupdate=_utcnow,
    )

    # -- Relationships ------------------------------------------------------
    inverters: Mapped[List["Inverter"]] = relationship(
        "Inverter", back_populates="plant", cascade="all, delete-orphan",
    )
    alerts: Mapped[List["Alert"]] = relationship(
        "Alert", back_populates="plant", cascade="all, delete-orphan",
    )
    recommendations: Mapped[List["Recommendation"]] = relationship(
        "Recommendation", back_populates="plant", cascade="all, delete-orphan",
    )
    reports: Mapped[List["Report"]] = relationship(
        "Report", back_populates="plant", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Plant(id={self.id}, name='{self.name}', capacity={self.installed_dc_capacity_mw} MW)>"


# ═══════════════════════════════════════════════════════════════════════════
# Inverter
# ═══════════════════════════════════════════════════════════════════════════
class Inverter(Base):
    """An inverter (central or string) belonging to a :class:`Plant`."""

    __tablename__ = "inverters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("plants.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    block_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # -- Audit timestamps ---------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow, onupdate=_utcnow,
    )

    # -- Relationships ------------------------------------------------------
    plant: Mapped["Plant"] = relationship("Plant", back_populates="inverters")
    daily_records: Mapped[List["DailyRecord"]] = relationship(
        "DailyRecord", back_populates="inverter", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Inverter(id={self.id}, name='{self.name}', block='{self.block_name}')>"


# ═══════════════════════════════════════════════════════════════════════════
# DailyRecord
# ═══════════════════════════════════════════════════════════════════════════
class DailyRecord(Base):
    """Daily generation & loss data for a single inverter.

    A unique constraint on ``(inverter_id, record_date)`` prevents
    duplicate entries for the same inverter on the same day.
    """

    __tablename__ = "daily_records"
    __table_args__ = (
        UniqueConstraint("inverter_id", "record_date", name="uq_inverter_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    inverter_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("inverters.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    record_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # -- Generation ---------------------------------------------------------
    irradiation: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    generation: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # -- Losses -------------------------------------------------------------
    grid_failure: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    curtailment: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    grid_loss: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    machine_loss: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # -- Totals -------------------------------------------------------------
    total_generation: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_possible_generation: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # -- Audit timestamps ---------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow, onupdate=_utcnow,
    )

    # -- Relationships ------------------------------------------------------
    inverter: Mapped["Inverter"] = relationship("Inverter", back_populates="daily_records")

    def __repr__(self) -> str:
        return (
            f"<DailyRecord(id={self.id}, inverter_id={self.inverter_id}, "
            f"date={self.record_date}, gen={self.generation})>"
        )


# ═══════════════════════════════════════════════════════════════════════════
# Alert
# ═══════════════════════════════════════════════════════════════════════════
class Alert(Base):
    """An operational alert raised for a :class:`Plant`.

    Severity levels: ``info``, ``warning``, ``critical``.
    Status: ``active`` or ``resolved``.
    """

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("plants.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    alert_date: Mapped[date] = mapped_column(Date, nullable=False)
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, default="info",
        comment='One of: "info", "warning", "critical"',
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active",
        comment='One of: "active", "resolved"',
    )
    resolved_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # -- Audit timestamps ---------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow, onupdate=_utcnow,
    )

    # -- Relationships ------------------------------------------------------
    plant: Mapped["Plant"] = relationship("Plant", back_populates="alerts")

    def __repr__(self) -> str:
        return f"<Alert(id={self.id}, severity='{self.severity}', status='{self.status}')>"


# ═══════════════════════════════════════════════════════════════════════════
# Recommendation
# ═══════════════════════════════════════════════════════════════════════════
class Recommendation(Base):
    """An AI-generated recommendation for a :class:`Plant`.

    Priority levels: ``low``, ``medium``, ``high``.
    Status: ``pending``, ``implemented``, ``dismissed``.
    """

    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("plants.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    generated_date: Mapped[date] = mapped_column(Date, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(
        String(20), nullable=False, default="medium",
        comment='One of: "low", "medium", "high"',
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
        comment='One of: "pending", "implemented", "dismissed"',
    )

    # -- Audit timestamps ---------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow, onupdate=_utcnow,
    )

    # -- Relationships ------------------------------------------------------
    plant: Mapped["Plant"] = relationship("Plant", back_populates="recommendations")

    def __repr__(self) -> str:
        return (
            f"<Recommendation(id={self.id}, category='{self.category}', "
            f"priority='{self.priority}')>"
        )


# ═══════════════════════════════════════════════════════════════════════════
# Report
# ═══════════════════════════════════════════════════════════════════════════
class Report(Base):
    """Metadata for a generated report (PDF or DOCX) for a :class:`Plant`."""

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("plants.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    generated_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    report_title: Mapped[str] = mapped_column(String(255), nullable=False)
    report_type: Mapped[str] = mapped_column(
        String(10), nullable=False, default="pdf",
        comment='One of: "pdf", "docx"',
    )
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)

    # -- Audit timestamps ---------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow, onupdate=_utcnow,
    )

    # -- Relationships ------------------------------------------------------
    plant: Mapped["Plant"] = relationship("Plant", back_populates="reports")

    def __repr__(self) -> str:
        return (
            f"<Report(id={self.id}, title='{self.report_title}', "
            f"type='{self.report_type}')>"
        )


# ═══════════════════════════════════════════════════════════════════════════
# SystemSettings
# ═══════════════════════════════════════════════════════════════════════════
class SystemSettings(Base):
    """Key-value settings storage.

    When ``plant_id`` is ``NULL`` the setting is global; otherwise it
    applies only to the specified plant.
    """

    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plant_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("plants.id", ondelete="CASCADE"), nullable=True, index=True,
    )
    setting_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    setting_value: Mapped[str] = mapped_column(String(1000), nullable=False)

    # -- Audit timestamps ---------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow, onupdate=_utcnow,
    )

    def __repr__(self) -> str:
        return (
            f"<SystemSettings(id={self.id}, key='{self.setting_key}', "
            f"plant_id={self.plant_id})>"
        )
