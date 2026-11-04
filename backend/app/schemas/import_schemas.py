"""
SoliZer Intelligence Platform - Import Pydantic Schemas.

Pydantic v2 models used during Excel data import.
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ═══════════════════════════════════════════════════════════════════════════
# ImportConfig
# ═══════════════════════════════════════════════════════════════════════════
class ImportConfig(BaseModel):
    """Configuration options for an Excel import job."""

    import_type: str = Field(
        ...,
        pattern=r"^(multi_sheet|single_sheet)$",
        description='Import layout: "multi_sheet" or "single_sheet"',
    )
    date_format: str = Field(
        "dd/mm/yyyy",
        description="Expected date format in the Excel file (e.g. 'dd/mm/yyyy', 'yyyy-mm-dd')",
    )

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "import_type": "multi_sheet",
                "date_format": "dd/mm/yyyy",
            }
        },
    )


# ═══════════════════════════════════════════════════════════════════════════
# ValidationError
# ═══════════════════════════════════════════════════════════════════════════
class ValidationError(BaseModel):
    """A single validation issue found during file import."""

    row: int = Field(..., ge=1, description="Row number (1-indexed)")
    column: str = Field(..., description="Column name or letter")
    message: str = Field(..., description="Human-readable error description")
    value: str = Field("", description="The invalid value encountered")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "row": 15,
                "column": "Irradiation",
                "message": "Value is negative. Irradiation must be >= 0.",
                "value": "-3.2",
            }
        },
    )


# ═══════════════════════════════════════════════════════════════════════════
# ImportValidationResult
# ═══════════════════════════════════════════════════════════════════════════
class ImportValidationResult(BaseModel):
    """Overall result of a data import operation."""

    is_valid: bool = Field(
        ..., description="Whether the import completed without critical errors",
    )
    total_rows: int = Field(
        0, ge=0, description="Total number of rows processed",
    )
    valid_rows: int = Field(
        0, ge=0, description="Total number of valid rows imported",
    )
    errors: List[ValidationError] = Field(
        default_factory=list,
        description="List of validation errors found in the file",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="List of non-critical warnings",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "is_valid": True,
                "total_rows": 1460,
                "valid_rows": 1458,
                "errors": [
                    {
                        "row": 15,
                        "column": "Irradiation",
                        "message": "Value is negative. Irradiation must be >= 0.",
                        "value": "-3.2",
                    }
                ],
                "warnings": [
                    "Sheet 'INV-03' had 2 rows with missing irradiation values (set to 0)."
                ],
            }
        },
    )
