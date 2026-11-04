"""
SoliZer Intelligence Platform - Core Configuration
Application-wide settings and constants.
"""
import os
from pathlib import Path


# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = DATA_DIR / "reports"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# --- Database ---
DATABASE_URL = f"sqlite:///{DATA_DIR / 'solizer.db'}"

# --- Application ---
APP_NAME = "SoliZer Intelligence Platform"
APP_VERSION = "1.0.0-mvp"

# --- Default KPI Thresholds ---
DEFAULT_PR_WARNING = 70.0      # PR below this triggers warning
DEFAULT_PR_CRITICAL = 60.0     # PR below this triggers critical alert
DEFAULT_CUF_WARNING = 15.0     # CUF below this triggers warning
DEFAULT_CUF_CRITICAL = 10.0    # CUF below this triggers critical alert
DEFAULT_LOSS_WARNING = 5.0     # Loss % above this triggers warning
DEFAULT_LOSS_CRITICAL = 10.0   # Loss % above this triggers critical alert
DEFAULT_AVAILABILITY_WARNING = 95.0  # Below this triggers warning
DEFAULT_AVAILABILITY_CRITICAL = 90.0  # Below this triggers critical alert

# --- Health Score Weights (must sum to 1.0) ---
HEALTH_SCORE_WEIGHTS = {
    "pr": 0.30,
    "cuf": 0.20,
    "availability": 0.20,
    "loss": 0.15,
    "degradation": 0.15,
}

# --- Degradation Status Thresholds ---
DEGRADATION_NORMAL_THRESHOLD = 1.0    # Index < 1.0 = Normal
DEGRADATION_WARNING_THRESHOLD = 1.5   # Index < 1.5 = Warning
# Above 1.5 = Critical
