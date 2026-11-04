"""
SoliZer Intelligence Platform - Reports Router.

Provides endpoints for generating and listing plant performance reports
in PDF or DOCX format.
"""

from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Plant, Report
from app.schemas.analytics_schemas import ReportGenerateRequest, ReportResponse
from app.services.report_generator import generate_and_save_report

router = APIRouter()


@router.post(
    "/{plant_id}/reports",
    response_model=ReportResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate a performance report",
)
def generate_report(
    plant_id: int,
    payload: ReportGenerateRequest,
    db: Session = Depends(get_db),
):
    """Request generation of a performance report for the specified plant."""
    plant = db.query(Plant).filter(Plant.id == plant_id).first()
    if not plant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plant with id {plant_id} not found.",
        )

    # Validate report type
    req_type = payload.report_type.lower()
    if req_type not in ("pdf", "docx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported report format: {payload.report_type}. Use 'pdf' or 'docx'.",
        )

    try:
        report_db = generate_and_save_report(
            db, plant_id, req_type,
            start_date=payload.start_date,
            end_date=payload.end_date,
        )
        return ReportResponse(
            id=report_db.id,
            plant_id=report_db.plant_id,
            report_type=report_db.report_type,
            title=report_db.report_title,
            file_path=report_db.file_path,
            generated_at=report_db.generated_date,
            period_start=report_db.period_start,
            period_end=report_db.period_end,
            status="completed",
            message="Report generated successfully.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {e}",
        )


@router.get(
    "/{plant_id}/reports",
    response_model=List[ReportResponse],
    summary="List generated reports",
)
def list_reports(plant_id: int, db: Session = Depends(get_db)):
    """Return all previously generated reports for the specified plant."""
    plant = db.query(Plant).filter(Plant.id == plant_id).first()
    if not plant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plant with id {plant_id} not found.",
        )

    reports = (
        db.query(Report)
        .filter(Report.plant_id == plant_id)
        .order_by(Report.created_at.desc())
        .all()
    )

    return [
        ReportResponse(
            id=r.id,
            plant_id=r.plant_id,
            report_type=r.report_type,
            title=r.report_title,
            file_path=r.file_path,
            generated_at=r.generated_date,
            period_start=r.period_start,
            period_end=r.period_end,
            status="completed",
            message="Retrieved successfully.",
        )
        for r in reports
    ]

