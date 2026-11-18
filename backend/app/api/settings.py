"""
SoliZer Intelligence Platform - Settings API Router.

Manages application settings, auditor profile, module toggles,
engineering thresholds, currency configuration, database backups, and maintenance.
"""

import os
import sys
import shutil
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.db.database import get_db, DB_PATH
from app.db.models import SystemSettings, Report, DailyRecord, Plant

router = APIRouter()

DEFAULT_SETTINGS = {
    # Account & Auditor Profile
    "auditor_name": "Akalanka",
    "organization": "Solar Intelligence Engineering",
    "email": "auditor@solizer.com",
    "designation": "Lead Solar Asset Auditor",
    "license_id": "PV-ENG-49201",

    # Module Visibility (Sidebar & Dashboard)
    "enabled_inverters": "true",
    "enabled_losses": "true",
    "enabled_degradation": "true",
    "enabled_irradiation": "true",
    "enabled_alerts": "true",

    # Report Chapter Inclusion
    "report_include_exec_summary": "true",
    "report_include_kpi_analysis": "true",
    "report_include_inverters": "true",
    "report_include_losses": "true",
    "report_include_degradation": "true",
    "report_include_recommendations": "true",

    # Engineering Thresholds & IEC Calibration
    "pr_alert_threshold": "75.0",
    "inverter_discrepancy_threshold": "5.0",
    "cuf_threshold": "15.0",
    "temp_coefficient": "-0.0040",
    "reference_cell_temp": "25.0",

    # Financial Economics & Currency
    "tariff_rate": "0.12",
    "currency_code": "USD",
    "currency_symbol": "$",

    # Content & Disclaimers
    "report_disclaimer": "This report is generated using the Solize Intelligence Platform adhering to the IEC 61724 standard. All mathematical figures are derived from logged operational SCADA and irradiation telemetry.",
}


class SettingsUpdateRequest(BaseModel):
    settings: Dict[str, str] = Field(..., description="Key-value mapping of settings")


@router.get(
    "/",
    summary="Get all system settings",
)
def get_all_settings(db: Session = Depends(get_db)):
    """Retrieve all configuration settings merged with defaults."""
    db_settings = db.query(SystemSettings).filter(SystemSettings.plant_id.is_(None)).all()
    merged = dict(DEFAULT_SETTINGS)
    for s in db_settings:
        merged[s.setting_key] = s.setting_value
    return {"settings": merged}


@router.post(
    "/",
    summary="Update system settings",
)
def update_settings(payload: SettingsUpdateRequest, db: Session = Depends(get_db)):
    """Save or update one or multiple settings."""
    for key, value in payload.settings.items():
        setting = (
            db.query(SystemSettings)
            .filter(SystemSettings.plant_id.is_(None), SystemSettings.setting_key == key)
            .first()
        )
        if setting:
            setting.setting_value = str(value)
        else:
            new_s = SystemSettings(
                plant_id=None,
                setting_key=key,
                setting_value=str(value),
            )
            db.add(new_s)
    db.commit()
    return {"success": True, "message": "Settings updated successfully."}


@router.get(
    "/stats",
    summary="Get system storage and data stats",
)
def get_system_stats(db: Session = Depends(get_db)):
    """Retrieve statistics about database size, report counts, and logs."""
    db_size_bytes = 0
    if os.path.exists(DB_PATH):
        db_size_bytes = os.path.getsize(DB_PATH)

    reports_count = db.query(Report).count()
    daily_records_count = db.query(DailyRecord).count()
    plants_count = db.query(Plant).count()

    appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
    reports_dir = os.path.join(appdata, "Solizer", "data", "reports")
    reports_dir_size = 0
    if os.path.exists(reports_dir):
        for root, _, files in os.walk(reports_dir):
            for f in files:
                reports_dir_size += os.path.getsize(os.path.join(root, f))

    db_size_mb = round(db_size_bytes / (1024 * 1024), 2)
    reports_dir_size_mb = round(reports_dir_size / (1024 * 1024), 2)

    return {
        "database_path": DB_PATH,
        "db_size_bytes": db_size_bytes,
        "db_size_mb": db_size_mb,
        "database_size_kb": round(db_size_bytes / 1024, 1),
        "total_plants": plants_count,
        "total_reports": reports_count,
        "total_records": daily_records_count,
        "total_daily_records": daily_records_count,
        "reports_dir": reports_dir,
        "reports_folder": reports_dir,
        "reports_dir_size_mb": reports_dir_size_mb,
        "reports_folder_size_kb": round(reports_dir_size / 1024, 1),
    }


@router.get(
    "/backup",
    summary="Download database backup",
)
def download_database_backup():
    """Create and download a clean backup copy of the SQLite database."""
    if not os.path.exists(DB_PATH):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Database file not found.",
        )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"solizer_backup_{timestamp}.db"
    backup_path = os.path.join(os.path.dirname(DB_PATH), backup_filename)
    shutil.copy2(DB_PATH, backup_path)

    return FileResponse(
        backup_path,
        media_type="application/octet-stream",
        filename=backup_filename,
    )


@router.post(
    "/optimize-db",
    summary="Optimize SQLite database and rebuild query indexes",
)
def optimize_database(db: Session = Depends(get_db)):
    """Run SQLite VACUUM, ANALYZE, and PRAGMA optimize for maximum query and storage performance."""
    from sqlalchemy import text
    from app.db.database import engine
    try:
        db.commit()
        db.execute(text("PRAGMA optimize;"))
        db.execute(text("ANALYZE;"))
        db.commit()

        # VACUUM runs outside active transaction
        raw_conn = engine.raw_connection()
        try:
            raw_conn.isolation_level = None
            cur = raw_conn.cursor()
            cur.execute("VACUUM;")
            cur.close()
        finally:
            raw_conn.close()

        db_size_bytes = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
        db_size_mb = round(db_size_bytes / (1024 * 1024), 2)
        return {
            "success": True,
            "message": f"Database optimized and defragmented! Current size: {db_size_mb} MB.",
            "db_size_mb": db_size_mb,
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Optimization notice: {str(e)}",
        }


@router.post(
    "/clear-cache",
    summary="Clear temporary report files",
)
def clear_temporary_cache():
    """Remove orphaned temporary files and caches."""
    appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
    temp_dir = os.path.join(appdata, "Solizer", "data", "temp")
    cleared = 0
    if os.path.exists(temp_dir):
        for f in os.listdir(temp_dir):
            fp = os.path.join(temp_dir, f)
            try:
                if os.path.isfile(fp):
                    os.remove(fp)
                    cleared += 1
            except Exception:
                pass
    return {
        "success": True,
        "message": f"Cache cleared successfully ({cleared} temporary files purged).",
        "files_cleared": cleared,
    }
