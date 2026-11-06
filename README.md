# Solize — The Solar Plant Performance & Analytics Platform

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.0+-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![MUI](https://img.shields.io/badge/MUI-v5-007FFF?style=for-the-badge&logo=mui&logoColor=white)](https://mui.com)
[![Vite](https://img.shields.io/badge/Vite-5.0+-646CFF?style=for-the-badge&logo=vite&logoColor=white)](https://vitejs.dev)
[![Standard](https://img.shields.io/badge/Standard-IEC%2061724-F39C12?style=for-the-badge)](https://www.iec.ch)

**Solize** is an enterprise-grade desktop & hybrid solar intelligence platform engineered to analyze, monitor, and audit utility-scale solar photovoltaic (PV) power plants. Built with precision engineering benchmarks, it translates raw multi-inverter SCADA time-series data into actionable performance analytics, health scores, financial revenue impact assessments, and audit-ready technical reports.

---

## 🌟 Key Features

### 1. IEC 61724 Standard KPI Engine
* **Performance Ratio (PR)**: Evaluates overall plant efficiency against theoretical irradiation potential.
* **Temperature-Corrected PR (PR_STC)**: Implements temperature coefficients ($\gamma$) to normalize seasonal cell temperature effects to Standard Test Conditions ($25^\circ\text{C}$).
* **Capacity Utilization Factor (CUF)**: Normalized metric evaluating actual MWh produced relative to rated AC capacity over 24-hour periods.
* **Specific Yield (Y_f)**: Generation normalized by installed DC capacity (kWh/kWp/day).
* **Plant & Inverter Availability**: High-accuracy uptime and operational availability metrics.

### 2. Longitudinal Degradation Assessment
* **OLS Linear Regression**: Performs monthly Ordinary Least Squares regression on rolling PR time-series to determine annual degradation rates ($\%/\text{year}$).
* **Expected vs. Actual Degradation**: Compares historical degradation with manufacturer module degradation warranty thresholds (typically $0.5\%/\text{year}$).

### 3. Financial Revenue & Loss Intelligence
* **Loss Categorization**: Quantifies energy lost to **Grid Failures**, **Grid Curtailment**, **Transmission Losses**, and **Machine/Inverter Downtime**.
* **Financial Monetization**: Calculates lost revenue using customizable feed-in tariff (FIT) rates:

$$
\text{Revenue Lost} = \text{Lost Energy (kWh)} \times \text{Tariff Rate}
$$

* Realized revenue, lost revenue, and gross potential revenue tracking on the live dashboard.

### 4. Multi-Format Ingestion & Operator Logging
* **Multi-Format Ingestion Engine**: Parses multi-sheet Excel files (one sheet per inverter), single-sheet aggregated workbooks, and CSV logs from SCADA or dataloggers.
* **Live Progress Indicator**: Multi-stage visual feedback during data parsing, mathematical verification, and database persistence.
* **Manual Daily Operations Modal**: Operators can log daily generation, solar radiation, and downtime events directly from the UI without needing spreadsheet imports.

### 5. Automated Engineering Dossiers & Custom Branding
* **Dual Output Formats**: Compiles comprehensive 8-section technical dossiers in both **Word (.docx)** and **PDF** formats.
* **Cover Page Branding**: Operators can upload their company or client logo, automatically resized and embedded on cover pages.
* Sections include: Executive Summary, Plant Performance, Inverter-level Discrepancies, Loss Breakdowns, Degradation Regression, and Maintenance Recommendations.

### 6. Modern Desktop UI & Packaging
* **Adaptive Light / Dark Modes**: Material UI v5 design with high-contrast data visualization, custom SVG charts via Recharts, and sleek status badges.
* **Standalone Windows Distribution**: Packaged via PyInstaller and Inno Setup 6 into a single `.exe` installer with a custom solar icon (`solizer.ico`).

---

## 📐 Engineering Equations & Standards

### 1. Performance Ratio (PR)

$$
\text{PR} = \frac{\text{Actual Generation (kWh)}}{\frac{\text{Irradiation (Wh/m}^2\text{)} \times \text{Total Area (m}^2\text{)} \times \eta_{\text{module}} \times \text{Sun Hours}}{1000}} \times 100
$$

### 2. IEC 61724 Temperature-Corrected PR (PR_STC)

$$
\text{PR}_{\text{STC}} = \frac{\text{PR}}{1 + \gamma \times (T_{\text{cell}} - 25^\circ\text{C})}
$$

*where $\gamma \approx -0.004 / ^\circ\text{C}$ (temperature coefficient of power).*

### 3. Capacity Utilization Factor (CUF)

$$
\text{CUF} = \frac{\text{Generation (MWh)}}{\text{Installed AC Capacity (MW)} \times \text{Total Hours}} \times 100
$$

### 4. Specific Yield (Y_f)

$$
Y_f = \frac{\text{Total Generation (kWh)}}{\text{Installed DC Capacity (kWp)}}
$$

### 5. Annual Degradation Rate (OLS)

$$
\text{Degradation Rate (\%/year)} = m \times 12
$$

*where $m$ is the slope of the linear regression line on monthly average PR values over time.*

---

## 🏗 System Architecture

```
Solize/
├── backend/                  # FastAPI 0.100+ Backend Engine
│   ├── app/
│   │   ├── api/              # RESTful API endpoints (Plants, Import, Reports, Analytics)
│   │   ├── db/               # SQLAlchemy 2.0 ORM & SQLite Models
│   │   ├── engines/          # KPI, Degradation (OLS), Loss & Alert Algorithms
│   │   ├── schemas/          # Pydantic v2 validation models
│   │   └── services/         # Excel/CSV Parser & ReportLab/DOCX Generator
│   ├── main.py               # Fast-boot daemon & PyWebView wrapper
│   └── solizer-release.spec  # PyInstaller packaging configuration
├── frontend/                 # React 18 + TypeScript + Vite SPA
│   ├── src/
│   │   ├── components/       # Layout, Navigation, Filter Bars, Modal Dialogs
│   │   ├── context/          # Plant and Theme Context providers
│   │   ├── pages/            # Dashboard, Import, Degradation, Reports, Profile
│   │   ├── services/         # Axios API Client
│   │   └── theme/            # Dual Light / Dark MUI theme definitions
├── setup.iss                 # Inno Setup 6 installer compilation script
└── README.md                 # Project technical documentation
```

---

## 🚀 Getting Started

### Prerequisites
* **Python 3.11+**
* **Node.js 18+ & npm**
* **Inno Setup 6** *(Optional, for building desktop installer)*

### Running Backend Locally
```bash
cd backend
python -m venv venv
venv\Scripts\activate       # On Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Running Frontend Locally
```bash
cd frontend
npm install
npm run dev
```

### Building Desktop Installer
```bash
# 1. Compile frontend
cd frontend
npm run build

# 2. Package backend with PyInstaller
cd ../backend
pyinstaller solizer-release.spec -y

# 3. Compile Windows Installer
cd ..
iscc setup.iss
```

---

## 📄 License
This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
