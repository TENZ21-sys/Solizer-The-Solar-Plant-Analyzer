"""
SoliZer - Report Generation Verification Script.
Generates PDF and DOCX reports for Plant ID 2 and verifies file output.
"""
import os
from app.db.database import SessionLocal
from app.services.report_generator import generate_and_save_report

def verify_reports():
    print("=== STARTING REPORT GENERATION TEST ===")
    db = SessionLocal()
    try:
        # Generate DOCX
        print("1. Generating DOCX report for Plant 2...")
        docx_report = generate_and_save_report(db, 2, "docx")
        print(f"   Success! DOCX file path: {docx_report.file_path}")
        assert os.path.exists(docx_report.file_path), "DOCX report file was not created on disk!"
        print(f"   DOCX File Size: {os.path.getsize(docx_report.file_path)} bytes")

        # Generate PDF
        print("2. Generating PDF report for Plant 2...")
        pdf_report = generate_and_save_report(db, 2, "pdf")
        print(f"   Success! PDF file path: {pdf_report.file_path}")
        assert os.path.exists(pdf_report.file_path), "PDF report file was not created on disk!"
        print(f"   PDF File Size: {os.path.getsize(pdf_report.file_path)} bytes")

        print("=== REPORT GENERATION TEST SUCCESSFUL ===")
    except Exception as e:
        print(f"!!! ERROR: Report generation failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    verify_reports()
