"""
SoliZer Intelligence Platform - Plant CRUD Router.

Provides endpoints for creating, reading, updating, and deleting
solar power plants.  Deleting a plant cascades to all associated data
(inverters, daily records, alerts, recommendations, reports).
"""
import os
import sys
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Plant, Inverter, DailyRecord
from app.schemas.plant_schemas import (
    PlantCreate,
    PlantUpdate,
    PlantResponse,
    PlantListResponse,
    DailyRecordInput,
    DailyRecordInputResponse,
)
from app.engines.health_alerts import generate_alerts_and_recommendations

router = APIRouter()


@router.post(
    "/",
    response_model=PlantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new plant",
)
def create_plant(plant_in: PlantCreate, db: Session = Depends(get_db)):
    """
    Register a new solar power plant in the system.

    Accepts plant metadata (name, location, capacity, etc.) and persists it
    to the database.  Returns the full plant record including its generated ID.
    """
    plant = Plant(**plant_in.dict())
    db.add(plant)
    db.commit()
    db.refresh(plant)
    return plant


@router.get(
    "/",
    response_model=List[PlantListResponse],
    summary="List all plants",
)
def list_plants(db: Session = Depends(get_db)):
    """
    Retrieve a lightweight list of every registered plant.

    Returns basic metadata suitable for a dashboard / sidebar listing.
    """
    plants = db.query(Plant).order_by(Plant.created_at.desc()).all()
    return plants


@router.get(
    "/{plant_id}",
    response_model=PlantResponse,
    summary="Get plant details",
)
def get_plant(plant_id: int, db: Session = Depends(get_db)):
    """
    Retrieve the full details for a single plant identified by *plant_id*.

    Raises **404** if the plant does not exist.
    """
    plant = db.query(Plant).filter(Plant.id == plant_id).first()
    if not plant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plant with id {plant_id} not found.",
        )
    return plant


@router.put(
    "/{plant_id}",
    response_model=PlantResponse,
    summary="Update plant details",
)
def update_plant(
    plant_id: int,
    plant_in: PlantUpdate,
    db: Session = Depends(get_db),
):
    """
    Update one or more fields of an existing plant.

    Only the fields provided in the request body will be modified.
    Raises **404** if the plant does not exist.
    """
    plant = db.query(Plant).filter(Plant.id == plant_id).first()
    if not plant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plant with id {plant_id} not found.",
        )

    update_data = plant_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(plant, field, value)

    db.commit()
    db.refresh(plant)
    return plant


@router.delete(
    "/{plant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a plant",
)
def delete_plant(plant_id: int, db: Session = Depends(get_db)):
    """
    Permanently delete a plant and **all** associated data (inverters,
    daily records, alerts, recommendations, and reports).

    Raises **404** if the plant does not exist.
    """
    plant = db.query(Plant).filter(Plant.id == plant_id).first()
    if not plant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plant with id {plant_id} not found.",
        )

    db.delete(plant)
    db.commit()
    return None


# ═══════════════════════════════════════════════════════════════════════════
# Manual Daily Log Entry
# ═══════════════════════════════════════════════════════════════════════════
@router.post(
    "/{plant_id}/daily-record",
    response_model=DailyRecordInputResponse,
    status_code=status.HTTP_200_OK,
    summary="Add or update a daily record manually",
)
def add_daily_record(
    plant_id: int,
    payload: DailyRecordInput,
    db: Session = Depends(get_db),
):
    """
    Manually add or update daily operational figures for a plant.
    If inverter_id is not specified, data is distributed across all plant inverters.
    """
    plant = db.query(Plant).filter(Plant.id == plant_id).first()
    if not plant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plant with id {plant_id} not found.",
        )

    inverters = db.query(Inverter).filter(Inverter.plant_id == plant_id).all()
    if not inverters:
        # Create default inverters for the plant if none exist yet
        num_inv = max(plant.number_of_inverters, 1)
        inverters = []
        for i in range(1, num_inv + 1):
            inv = Inverter(
                plant_id=plant_id,
                name=f"Inverter {i}",
                block_name=f"Block 1",
            )
            db.add(inv)
        db.commit()
        inverters = db.query(Inverter).filter(Inverter.plant_id == plant_id).all()

    target_inverters = []
    if payload.inverter_id:
        target = next((inv for inv in inverters if inv.id == payload.inverter_id), None)
        if not target:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Inverter with id {payload.inverter_id} does not belong to plant {plant_id}.",
            )
        target_inverters = [target]
    else:
        target_inverters = inverters

    n = len(target_inverters)
    split_gen = payload.generation_kwh / n if payload.inverter_id is None else payload.generation_kwh
    split_gf = payload.grid_failure_kwh / n if payload.inverter_id is None else payload.grid_failure_kwh
    split_curt = payload.curtailment_kwh / n if payload.inverter_id is None else payload.curtailment_kwh
    split_gl = payload.grid_loss_kwh / n if payload.inverter_id is None else payload.grid_loss_kwh
    split_ml = payload.machine_loss_kwh / n if payload.inverter_id is None else payload.machine_loss_kwh

    records_count = 0
    for inv in target_inverters:
        record = (
            db.query(DailyRecord)
            .filter(
                DailyRecord.inverter_id == inv.id,
                DailyRecord.record_date == payload.record_date,
            )
            .first()
        )
        total_gen = split_gen + split_curt
        total_possible = split_gen + split_gf + split_curt + split_gl + split_ml

        if record:
            record.irradiation = payload.irradiation_wh_m2
            record.generation = split_gen
            record.grid_failure = split_gf
            record.curtailment = split_curt
            record.grid_loss = split_gl
            record.machine_loss = split_ml
            record.total_generation = total_gen
            record.total_possible_generation = total_possible
        else:
            record = DailyRecord(
                inverter_id=inv.id,
                record_date=payload.record_date,
                irradiation=payload.irradiation_wh_m2,
                generation=split_gen,
                grid_failure=split_gf,
                curtailment=split_curt,
                grid_loss=split_gl,
                machine_loss=split_ml,
                total_generation=total_gen,
                total_possible_generation=total_possible,
            )
            db.add(record)
        records_count += 1

    db.commit()

    # Re-evaluate alerts and recommendations
    try:
        generate_alerts_and_recommendations(db, plant_id)
    except Exception:
        pass

    return DailyRecordInputResponse(
        success=True,
        message=f"Successfully saved daily records for {payload.record_date}.",
        records_updated=records_count,
        record_date=payload.record_date,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Company Logo Branding
# ═══════════════════════════════════════════════════════════════════════════
def _get_branding_dir() -> str:
    if getattr(sys, "frozen", False):
        base_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "Solizer")
    else:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
    b_dir = os.path.join(base_dir, "branding")
    os.makedirs(b_dir, exist_ok=True)
    return b_dir


@router.post(
    "/{plant_id}/logo",
    summary="Upload company logo for reports and branding",
)
async def upload_company_logo(
    plant_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload custom company logo (PNG, JPG, SVG, WebP) for PDF and Word reports."""
    plant = db.query(Plant).filter(Plant.id == plant_id).first()
    if not plant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plant with id {plant_id} not found.",
        )

    b_dir = _get_branding_dir()
    # Save plant-specific logo, and also as default logo.png
    plant_logo_path = os.path.join(b_dir, f"logo_plant_{plant_id}.png")
    default_logo_path = os.path.join(b_dir, "logo.png")

    contents = await file.read()
    with open(plant_logo_path, "wb") as f:
        f.write(contents)
    with open(default_logo_path, "wb") as f:
        f.write(contents)

    return {
        "success": True,
        "message": "Company logo uploaded successfully.",
        "plant_id": plant_id,
        "logo_url": f"/api/plants/{plant_id}/logo",
    }


@router.get(
    "/{plant_id}/logo",
    summary="Get company logo",
)
def get_company_logo(plant_id: int, db: Session = Depends(get_db)):
    """Retrieve company logo if one has been uploaded."""
    b_dir = _get_branding_dir()
    plant_logo_path = os.path.join(b_dir, f"logo_plant_{plant_id}.png")
    default_logo_path = os.path.join(b_dir, "logo.png")

    target_path = plant_logo_path if os.path.exists(plant_logo_path) else default_logo_path
    if os.path.exists(target_path):
        return FileResponse(target_path, media_type="image/png")

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="No custom company logo found.",
    )

