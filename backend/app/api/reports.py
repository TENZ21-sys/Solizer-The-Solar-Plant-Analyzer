"""
SoliZer Intelligence Platform - Reports Router.

Provides endpoints for generating and listing plant performance reports
in PDF or DOCX format.
"""

from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
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
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
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


@router.delete(
    "/{plant_id}/reports/{report_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a generated report",
)
def delete_report(plant_id: int, report_id: int, db: Session = Depends(get_db)):
    """Permanently delete a generated report record and remove the file from disk."""
    import os
    report = (
        db.query(Report)
        .filter(Report.id == report_id, Report.plant_id == plant_id)
        .first()
    )
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with id {report_id} not found.",
        )

    if report.file_path and os.path.exists(report.file_path):
        try:
            os.remove(report.file_path)
        except Exception:
            pass

    db.delete(report)
    db.commit()
    return {"success": True, "message": f"Report '{report.report_title}' deleted successfully."}


@router.get(
    "/{plant_id}/reports/{report_id}/download",
    summary="Download a generated report file",
)
def download_report(plant_id: int, report_id: int, db: Session = Depends(get_db)):
    """Stream the generated PDF or DOCX file as an attachment download."""
    import os
    report = (
        db.query(Report)
        .filter(Report.id == report_id, Report.plant_id == plant_id)
        .first()
    )
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with id {report_id} not found.",
        )

    if not report.file_path or not os.path.exists(report.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report file does not exist on disk.",
        )

    filename = os.path.basename(report.file_path)
    media_type = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if report.report_type.lower() == "docx" or filename.lower().endswith(".docx")
        else "application/pdf"
    )

    return FileResponse(
        path=report.file_path,
        media_type=media_type,
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/{plant_id}/reports/{report_id}/open",
    summary="Open report file in default desktop application",
)
def open_report(plant_id: int, report_id: int, db: Session = Depends(get_db)):
    """Open the generated report directly on the host machine using Microsoft Word or default PDF reader."""
    import os
    import platform
    import subprocess

    report = (
        db.query(Report)
        .filter(Report.id == report_id, Report.plant_id == plant_id)
        .first()
    )
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with id {report_id} not found.",
        )

    if not report.file_path or not os.path.exists(report.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report file does not exist on disk.",
        )

    filename = os.path.basename(report.file_path)
    try:
        if platform.system() == "Windows":
            os.startfile(report.file_path)
        elif platform.system() == "Darwin":
            subprocess.run(["open", report.file_path], check=True)
        else:
            subprocess.run(["xdg-open", report.file_path], check=True)
        return {"success": True, "message": f"Opened '{filename}' in default application."}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to open report file: {e}",
        )



