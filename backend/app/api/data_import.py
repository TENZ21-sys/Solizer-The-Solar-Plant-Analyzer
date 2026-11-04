"""
SoliZer Intelligence Platform - Data Import Router.

Provides the endpoint for uploading XLSX monitoring data files
and triggering the parsing / validation pipeline.
"""

from typing import Optional
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Plant, DailyRecord
from app.schemas.import_schemas import ImportValidationResult
from app.services.parser import parse_and_validate_xlsx, parse_and_validate_csv
from app.engines.health_alerts import generate_alerts_and_recommendations

router = APIRouter()


@router.post(
    "/{plant_id}/import",
    response_model=ImportValidationResult,
    summary="Import monitoring data from XLSX or CSV",
)
async def import_data(
    plant_id: int,
    file: UploadFile = File(..., description="XLSX or CSV monitoring data file"),
    import_type: str = Query(
        "multi_sheet",
        description="Import format type",
        pattern="^(multi_sheet|single_sheet|csv)$",
    ),
    db: Session = Depends(get_db),
):
    """Upload an XLSX or CSV file containing solar plant monitoring data for the specified plant."""
    # Verify the plant exists
    plant = db.query(Plant).filter(Plant.id == plant_id).first()
    if not plant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plant with id {plant_id} not found.",
        )

    filename_lower = (file.filename or "").lower()
    is_csv = filename_lower.endswith(".csv") or file.content_type in ("text/csv", "application/csv", "text/plain")
    is_excel = filename_lower.endswith((".xlsx", ".xls")) or file.content_type in (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
    )

    if not (is_csv or is_excel):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only XLSX, XLS, or CSV files are supported.",
        )

    try:
        # Read file bytes
        file_bytes = await file.read()
        
        if is_csv:
            result, records = parse_and_validate_csv(db, plant, file_bytes)
        else:
            result, records = parse_and_validate_xlsx(db, plant, file_bytes, import_type)
        
        if len(records) > 0:
            # Clear previous daily records for this plant's inverters only on the specific dates being imported
            inverter_ids = [inv.id for inv in plant.inverters]
            new_dates = {rec.record_date for rec in records}
            if len(inverter_ids) > 0 and len(new_dates) > 0:
                db.query(DailyRecord).filter(
                    DailyRecord.inverter_id.in_(inverter_ids),
                    DailyRecord.record_date.in_(list(new_dates))
                ).delete(synchronize_session=False)
                db.commit()
                
            # Insert the new records
            db.add_all(records)
            db.commit()
            
            # Generate alerts and recommendations
            generate_alerts_and_recommendations(db, plant_id)
            
        return result
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error processing Excel file: {e}"
        )
