"""
SoliZer Intelligence Platform - Report Generation Service.

Generates DOCX and PDF reports containing:
1. Cover page.
2. Section 1: Plant-Level Performance Analysis (including Table 1: Annual Summary,
   PR chart, Specific Yield chart).
3. Section 2: Inverter-Level Performance Analysis (including Table 2.1: Inverter Gen,
   Table 2.2: Inverter PR, Table 2.3 Block Comparison, and comparative charts).
4. Section 3: Irradiation Analysis (including Table 3.1: Annual Irradiation,
   monthly irradiation comparison chart).
5. Section 4: Generation Analysis (including monthly detail tables for each year).
6. Section 5: Performance Ratio Assessment (including monthly PR trend regression line).
7. Section 6: Loss Analysis (including Table 6.1: Annual Loss Summary,
   monthly loss breakdown stacked bar chart, and inverter loss comparison chart).
8. Section 7: Findings (detailed key performance, inverter, loss, and irradiation findings).
9. Section 8: Recommendations (actionable maintenance, monitoring, and long-term recommendations).
"""

from __future__ import annotations

import os
from collections import defaultdict
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")  # Non-interactive background rendering
import matplotlib.pyplot as plt
import numpy as np
from sqlalchemy.orm import Session

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    PageBreak,
    KeepTogether,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from app.db.models import Plant, DailyRecord, Report, Alert, Recommendation, Inverter
from app.engines.aggregation import (
    get_daily_plant_records,
    aggregate_to_lifetime,
    aggregate_to_monthly,
)
from app.engines.kpi_calculator import (
    calculate_pr,
    calculate_cuf,
    calculate_specific_yield,
    calculate_availability,
    compute_lifetime_kpis,
    compute_monthly_kpis,
)
from app.engines.degradation import compute_degradation
from app.engines.inverter_analysis import analyze_inverters
from app.engines.loss_analysis import compute_loss_analysis, compute_monthly_losses
from app.engines.irradiation_analysis import compute_irradiation_analysis


_MONTH_NAMES = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


# ═══════════════════════════════════════════════════════════════════════
# Helper: Format inverter name to match example report
# ═══════════════════════════════════════════════════════════════════════
def format_inverter_name(name: str) -> str:
    """Format inverter name like 'B1 Inv 1' to 'B1-I1'."""
    parts = name.strip().split()
    if len(parts) >= 3 and parts[0].upper().startswith("B") and parts[2].isdigit():
        return f"{parts[0].upper()}-I{parts[2]}"
    return name


def get_company_logo_path(plant_id: int) -> Optional[str]:
    """Retrieve file path of custom company logo if available."""
    import sys
    if getattr(sys, "frozen", False):
        base_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "Solizer")
    else:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
    b_dir = os.path.join(base_dir, "branding")
    plant_logo = os.path.join(b_dir, f"logo_plant_{plant_id}.png")
    default_logo = os.path.join(b_dir, "logo.png")
    if os.path.exists(plant_logo):
        return plant_logo
    if os.path.exists(default_logo):
        return default_logo
    return None



# ═══════════════════════════════════════════════════════════════════════
# Helper: Setup DOCX table styling
# ═══════════════════════════════════════════════════════════════════════
def set_cell_background(cell, color_hex: str):
    """Set cell shading color in DOCX."""
    shading_xml = f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>'
    cell._tc.get_or_add_tcPr().append(parse_xml(shading_xml))


def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Set padding for a table cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('w:top', top), ('w:bottom', bottom), ('w:left', left), ('w:right', right)]:
        node = OxmlElement(m)
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)


# ═══════════════════════════════════════════════════════════════════════
# Chart Generation
# ═══════════════════════════════════════════════════════════════════════
def generate_charts(
    plant: Plant,
    sorted_study_years: list[str],
    monthly_kpis_by_year: dict,
    inverter_yearly_data: dict,
    block_yearly_data: dict,
    sorted_inverters: list[Inverter],
    monthly_losses: list,
    output_dir: str,
) -> dict[str, str]:
    """Generate all required report charts and save to output_dir as PNGs."""
    os.makedirs(output_dir, exist_ok=True)
    chart_paths = {}

    plt.close('all')
    try:
        # Standard styling
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = ["Helvetica", "Arial", "DejaVu Sans"]

        # Modern color palette: Year 1 (Navy), Year 2 (Steel Blue), Year 3 (Teal)
        colors_list = ["#1A365D", "#2B6CB0", "#319795", "#DD6B20", "#ECC94B"]
        months_labels = ['May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr']
        months_nums = [5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3, 4]
        
        n_years = len(sorted_study_years)
        x = np.arange(len(months_labels))
        width = 0.8 / max(n_years, 1)

        # 1. Performance Ratio Chart (Monthly PR grouped by year)
        fig, ax = plt.subplots(figsize=(7, 3.5), dpi=150)
        for idx, sy in enumerate(sorted_study_years):
            offset = (idx - (n_years - 1) / 2) * width
            prs = [monthly_kpis_by_year[sy].get(m_num, {}).get("pr", 0.0) for m_num in months_nums]
            ax.bar(x + offset, prs, width=width, label=sy, color=colors_list[idx % len(colors_list)])
        ax.axhline(plant.expected_pr, color="#e53935", linestyle="--", label=f"Expected ({plant.expected_pr}%)")
        ax.set_title("Monthly Performance Ratio Comparison (%)", fontsize=11, fontweight="bold", pad=10)
        ax.set_xticks(x)
        ax.set_xticklabels(months_labels, fontsize=8)
        ax.set_ylabel("PR (%)")
        ax.set_ylim(0, 100)
        ax.grid(axis="y", linestyle=":", alpha=0.4)
        ax.legend(loc="lower left", fontsize=8)
        plt.tight_layout()
        pr_path = os.path.join(output_dir, "pr_chart.png")
        plt.savefig(pr_path)
        plt.close(fig)
        chart_paths["pr"] = pr_path

        # 2. Specific Yield Chart (Monthly Spec Yield grouped by year)
        fig, ax = plt.subplots(figsize=(7, 3.5), dpi=150)
        for idx, sy in enumerate(sorted_study_years):
            offset = (idx - (n_years - 1) / 2) * width
            sys = [monthly_kpis_by_year[sy].get(m_num, {}).get("specific_yield", 0.0) for m_num in months_nums]
            ax.bar(x + offset, sys, width=width, label=sy, color=colors_list[idx % len(colors_list)])
        ax.set_title("Monthly Specific Yield Comparison (kWh/kWp)", fontsize=11, fontweight="bold", pad=10)
        ax.set_xticks(x)
        ax.set_xticklabels(months_labels, fontsize=8)
        ax.set_ylabel("Specific Yield (kWh/kWp)")
        ax.grid(axis="y", linestyle=":", alpha=0.4)
        ax.legend(loc="upper right", fontsize=8)
        plt.tight_layout()
        sy_path = os.path.join(output_dir, "specific_yield_chart.png")
        plt.savefig(sy_path)
        plt.close(fig)
        chart_paths["specific_yield"] = sy_path

        # 3. Inverter Generation Chart
        fig, ax = plt.subplots(figsize=(7, 3.5), dpi=150)
        inv_names = [format_inverter_name(inv.name) for inv in sorted_inverters]
        x_inv = np.arange(len(inv_names))
        width_inv = 0.8 / max(n_years, 1)
        for idx, sy in enumerate(sorted_study_years):
            offset = (idx - (n_years - 1) / 2) * width_inv
            gens = [inverter_yearly_data[inv.id][sy]["generation"] / 1000.0 for inv in sorted_inverters]
            ax.bar(x_inv + offset, gens, width=width_inv, label=sy, color=colors_list[idx % len(colors_list)])
        ax.set_title("Inverter-Level Annual Generation Comparison (MWh)", fontsize=11, fontweight="bold", pad=10)
        ax.set_xticks(x_inv)
        ax.set_xticklabels(inv_names, rotation=20, ha="right", fontsize=8)
        ax.set_ylabel("Generation (MWh)")
        ax.grid(axis="y", linestyle=":", alpha=0.4)
        ax.legend(loc="upper right", fontsize=8)
        plt.tight_layout()
        inv_path = os.path.join(output_dir, "inverter_chart.png")
        plt.savefig(inv_path)
        plt.close(fig)
        chart_paths["inverters_gen"] = inv_path

        # 4. Inverter Performance Ratio Chart
        fig, ax = plt.subplots(figsize=(7, 3.5), dpi=150)
        eff_frac = plant.module_efficiency / 100.0
        inv_area = plant.total_panel_area_sqm / max(plant.number_of_inverters, 1)
        for idx, sy in enumerate(sorted_study_years):
            offset = (idx - (n_years - 1) / 2) * width_inv
            prs = []
            for inv in sorted_inverters:
                gen = inverter_yearly_data[inv.id][sy]["generation"]
                irrad = inverter_yearly_data[inv.id][sy]["irradiation"]
                pr_val = calculate_pr(gen, irrad, inv_area, eff_frac, plant.daily_running_hours)
                prs.append(pr_val)
            ax.bar(x_inv + offset, prs, width=width_inv, label=sy, color=colors_list[idx % len(colors_list)])
        ax.set_title("Inverter-Level Annual Performance Ratio Summary (%)", fontsize=11, fontweight="bold", pad=10)
        ax.set_xticks(x_inv)
        ax.set_xticklabels(inv_names, rotation=20, ha="right", fontsize=8)
        ax.set_ylabel("PR (%)")
        ax.set_ylim(0, 100)
        ax.grid(axis="y", linestyle=":", alpha=0.4)
        ax.legend(loc="lower left", fontsize=8)
        plt.tight_layout()
        inv_pr_path = os.path.join(output_dir, "inverter_pr_chart.png")
        plt.savefig(inv_pr_path)
        plt.close(fig)
        chart_paths["inverters_pr"] = inv_pr_path

        # 5. Block-Level Annual Generation Chart
        fig, ax = plt.subplots(figsize=(7, 3.5), dpi=150)
        sorted_blocks = sorted(list(set(inv.block_name for inv in sorted_inverters)))
        x_blk = np.arange(len(sorted_blocks))
        width_blk = 0.8 / max(n_years, 1)
        for idx, sy in enumerate(sorted_study_years):
            offset = (idx - (n_years - 1) / 2) * width_blk
            gens = [block_yearly_data[block][sy]["generation"] / 1000.0 for block in sorted_blocks]
            ax.bar(x_blk + offset, gens, width=width_blk, label=sy, color=colors_list[idx % len(colors_list)])
        ax.set_title("Block-Level Annual Generation Comparison (MWh)", fontsize=11, fontweight="bold", pad=10)
        ax.set_xticks(x_blk)
        ax.set_xticklabels(sorted_blocks, fontsize=8)
        ax.set_ylabel("Generation (MWh)")
        ax.grid(axis="y", linestyle=":", alpha=0.4)
        ax.legend(loc="upper right", fontsize=8)
        plt.tight_layout()
        blk_path = os.path.join(output_dir, "block_chart.png")
        plt.savefig(blk_path)
        plt.close(fig)
        chart_paths["blocks_gen"] = blk_path

        # 6. Monthly Irradiation Chart
        fig, ax = plt.subplots(figsize=(7, 3.5), dpi=150)
        for idx, sy in enumerate(sorted_study_years):
            offset = (idx - (n_years - 1) / 2) * width
            irrads = [monthly_kpis_by_year[sy].get(m_num, {}).get("irradiation", 0.0) for m_num in months_nums]
            ax.bar(x + offset, irrads, width=width, label=sy, color=colors_list[idx % len(colors_list)])
        ax.set_title("Monthly Solar Irradiation Comparison (kWh/m²)", fontsize=11, fontweight="bold", pad=10)
        ax.set_xticks(x)
        ax.set_xticklabels(months_labels, fontsize=8)
        ax.set_ylabel("Irradiation (kWh/m²)")
        ax.grid(axis="y", linestyle=":", alpha=0.4)
        ax.legend(loc="upper right", fontsize=8)
        plt.tight_layout()
        irr_path = os.path.join(output_dir, "irradiation_chart.png")
        plt.savefig(irr_path)
        plt.close(fig)
        chart_paths["irradiation"] = irr_path

        # 7. Annual Total Generation Chart (Figure 4.1)
        fig, ax = plt.subplots(figsize=(7, 3.5), dpi=150)
        annual_gens = []
        for sy in sorted_study_years:
            total_gen_sy = sum(monthly_kpis_by_year[sy].get(m_num, {}).get("generation_mwh", 0.0) for m_num in months_nums)
            annual_gens.append(total_gen_sy)
            
        x_ann = np.arange(len(sorted_study_years))
        bars = ax.bar(x_ann, annual_gens, width=0.4, color="#1A365D")
        
        # Add values on top of bars
        for bar in bars:
            yval = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width()/2.0,
                yval + max(annual_gens or [1.0])*0.02,
                f"{yval:,.1f} MWh",
                ha='center',
                va='bottom',
                fontsize=8,
                fontweight='bold',
                color='#2D3748'
            )
            
        ax.set_title("Annual Total Generation (MWh)", fontsize=11, fontweight="bold", pad=10)
        ax.set_xticks(x_ann)
        ax.set_xticklabels(sorted_study_years, fontsize=9)
        ax.set_ylabel("Generation (MWh)")
        ax.set_ylim(0, max(annual_gens or [1.0]) * 1.18)
        ax.grid(axis="y", linestyle=":", alpha=0.4)
        plt.tight_layout()
        ann_gen_path = os.path.join(output_dir, "annual_generation_chart.png")
        plt.savefig(ann_gen_path)
        plt.close(fig)
        chart_paths["annual_generation"] = ann_gen_path

        # 8. Monthly Generation Chart
        fig, ax = plt.subplots(figsize=(7, 3.5), dpi=150)
        for idx, sy in enumerate(sorted_study_years):
            offset = (idx - (n_years - 1) / 2) * width
            gens = [monthly_kpis_by_year[sy].get(m_num, {}).get("generation_mwh", 0.0) for m_num in months_nums]
            ax.bar(x + offset, gens, width=width, label=sy, color=colors_list[idx % len(colors_list)])
        ax.set_title("Monthly Total Generation Comparison Across Years", fontsize=11, fontweight="bold", pad=10)
        ax.set_xticks(x)
        ax.set_xticklabels(months_labels, fontsize=8)
        ax.set_ylabel("Generation (MWh)")
        ax.grid(axis="y", linestyle=":", alpha=0.4)
        ax.legend(loc="upper right", fontsize=8)
        plt.tight_layout()
        gen_path = os.path.join(output_dir, "generation_chart.png")
        plt.savefig(gen_path)
        plt.close(fig)
        chart_paths["generation"] = gen_path

        # 9. Monthly PR Trend Line (Regression trend across all months)
        fig, ax = plt.subplots(figsize=(7, 3.5), dpi=150)
        chron_labels = []
        chron_prs = []
        for sy in sorted_study_years:
            for m_num in months_nums:
                if m_num in monthly_kpis_by_year[sy]:
                    chron_labels.append(monthly_kpis_by_year[sy][m_num]["label"])
                    chron_prs.append(monthly_kpis_by_year[sy][m_num]["pr"])
        x_chron = np.arange(len(chron_prs))
        ax.plot(x_chron, chron_prs, marker="o", color="#2B6CB0", linestyle="-", label="Monthly PR", markersize=4)
        if len(x_chron) > 1:
            slope, intercept = np.polyfit(x_chron, chron_prs, 1)
            trend_y = slope * x_chron + intercept
            ax.plot(x_chron, trend_y, color="#e53935", linestyle="--", linewidth=1.5, label="Trendline")
        ax.set_title("Monthly Average Performance Ratio Trend", fontsize=11, fontweight="bold", pad=10)
        step = max(len(chron_labels) // 8, 1)
        ax.set_xticks(x_chron[::step])
        ax.set_xticklabels([chron_labels[i] for i in range(0, len(chron_labels), step)], rotation=20, ha="right", fontsize=8)
        ax.set_ylabel("PR (%)")
        ax.set_ylim(0, 100)
        ax.grid(axis="both", linestyle=":", alpha=0.4)
        ax.legend(loc="lower left", fontsize=8)
        plt.tight_layout()
        trend_path = os.path.join(output_dir, "trend_chart.png")
        plt.savefig(trend_path)
        plt.close(fig)
        chart_paths["trend"] = trend_path

        # 10, 11, 12. Stacked Losses Chart by Year (Figures 6.1, 6.2, 6.3)
        losses_by_year = defaultdict(list)
        for m_loss in monthly_losses:
            start_year = m_loss.year if m_loss.month >= 5 else m_loss.year - 1
            sy_label = f"{start_year}-{start_year+1}"
            losses_by_year[sy_label].append(m_loss)

        for sy in sorted_study_years:
            fig, ax = plt.subplots(figsize=(7, 3.5), dpi=150)
            sy_losses = losses_by_year[sy]
            sy_loss_map = {m.month: m for m in sy_losses}
            
            grid_fail_mwh = []
            curt_mwh = []
            mach_mwh = []
            for m_num in months_nums:
                m_loss = sy_loss_map.get(m_num)
                if m_loss:
                    grid_fail_mwh.append(m_loss.grid_failure_mwh)
                    curt_mwh.append(m_loss.curtailment_mwh)
                    mach_mwh.append(m_loss.machine_loss_mwh)
                else:
                    grid_fail_mwh.append(0.0)
                    curt_mwh.append(0.0)
                    mach_mwh.append(0.0)
                    
            x_loss = np.arange(len(months_labels))
            
            # Plot stacked bar (Grid Failure = red, Curtailment = orange, Machine Loss = yellow)
            ax.bar(x_loss, grid_fail_mwh, label="Grid Failure", color="#e53935", width=0.5)
            ax.bar(x_loss, curt_mwh, bottom=grid_fail_mwh, label="Curtailment", color="#dd6b20", width=0.5)
            ax.bar(
                x_loss,
                mach_mwh,
                bottom=[g + c for g, c in zip(grid_fail_mwh, curt_mwh)],
                label="Machine Loss",
                color="#ecc94b",
                width=0.5,
            )
            
            ax.set_title(f"Monthly Loss Breakdown - {sy} (MWh)", fontsize=11, fontweight="bold", pad=10)
            ax.set_xticks(x_loss)
            ax.set_xticklabels(months_labels, fontsize=8)
            ax.set_ylabel("Losses (MWh)")
            ax.grid(axis="y", linestyle=":", alpha=0.4)
            ax.legend(loc="upper right", fontsize=8)
            plt.tight_layout()
            loss_path = os.path.join(output_dir, f"loss_chart_{sy}.png")
            plt.savefig(loss_path)
            plt.close(fig)
            chart_paths[f"losses_{sy}"] = loss_path

        # 13. Inverter-level Loss Chart (Figure 6.3)
        fig, ax = plt.subplots(figsize=(7, 3.5), dpi=150)
        for idx, sy in enumerate(sorted_study_years):
            offset = (idx - (n_years - 1) / 2) * width_inv
            losses_val = [
                (
                    inverter_yearly_data[inv.id][sy]["grid_failure"] +
                    inverter_yearly_data[inv.id][sy]["curtailment"] +
                    inverter_yearly_data[inv.id][sy]["machine_loss"]
                ) / 1000.0
                for inv in sorted_inverters
            ]
            ax.bar(x_inv + offset, losses_val, width=width_inv, label=sy, color=colors_list[idx % len(colors_list)])
        ax.set_title("Inverter-Level Annual Loss Comparison (MWh)", fontsize=11, fontweight="bold", pad=10)
        ax.set_xticks(x_inv)
        ax.set_xticklabels(inv_names, rotation=20, ha="right", fontsize=8)
        ax.set_ylabel("Losses (MWh)")
        ax.grid(axis="y", linestyle=":", alpha=0.4)
        ax.legend(loc="upper right", fontsize=8)
        plt.tight_layout()
        inv_loss_path = os.path.join(output_dir, "inverter_loss_chart.png")
        plt.savefig(inv_loss_path)
        plt.close(fig)
        chart_paths["losses_inv"] = inv_loss_path

    finally:
        plt.close('all')

    return chart_paths


# ═══════════════════════════════════════════════════════════════════════
# DOCX Document Generation
# ═══════════════════════════════════════════════════════════════════════
# Helper: Format cell in DOCX with font, padding, and alignment
def write_cell(cell, text: str, bold: bool = False, color_rgb: Optional[RGBColor] = None, font_size_pt: float = 9.5, align: str = "LEFT"):
    p = cell.paragraphs[0]
    p.text = ""  # clear existing text
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.05
    
    if align == "RIGHT":
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    elif align == "CENTER":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    else:
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        
    run = p.add_run(text)
    run.font.name = "Arial"
    run.font.size = Pt(font_size_pt)
    run.bold = bold
    if color_rgb:
        run.font.color.rgb = color_rgb


# Helper: Set column widths and cell margins for a DOCX table
def set_table_col_widths_and_padding(table, col_widths: List[float], top=80, bottom=80, left=120, right=120):
    for row in table.rows:
        for idx, cell in enumerate(row.cells):
            if idx < len(col_widths):
                cell.width = Inches(col_widths[idx])
            set_cell_margins(cell, top, bottom, left, right)


def generate_docx_report(
    plant: Plant,
    lifetime: any,
    kpis: any,
    monthly_kpis: list,
    sorted_study_years: list[str],
    study_year_records: dict,
    monthly_kpis_by_year: dict,
    inverter_yearly_data: dict,
    block_yearly_data: dict,
    sorted_inverters: list[Inverter],
    loss: any,
    monthly_losses: list,
    deg: any,
    alerts: list[Alert],
    recommendations: list[Recommendation],
    charts: dict[str, str],
    file_path: str,
    daily_records: list,
) -> None:
    """Create the professional Word report (.docx) matching Example report outlines."""
    doc = Document()

    # Page Margins
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    # Base styling
    style_normal = doc.styles["Normal"]
    style_normal.font.name = "Arial"
    style_normal.font.size = Pt(10.5)
    style_normal.font.color.rgb = RGBColor(0x33, 0x33, 0x33)

    # ───────────────────────────────────────────────────────────────────────
    # Cover Page (Headerless layout matching example report)
    # ───────────────────────────────────────────────────────────────────────
    # Custom Company Logo if available
    logo_path = get_company_logo_path(plant.id)
    if logo_path and os.path.exists(logo_path):
        logo_p = doc.add_paragraph()
        logo_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        logo_p.paragraph_format.space_before = Pt(40)
        logo_p.paragraph_format.space_after = Pt(10)
        logo_run = logo_p.add_run()
        try:
            logo_run.add_picture(logo_path, width=Inches(2.2))
        except Exception:
            pass

    # Title
    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_p.paragraph_format.space_before = Pt(30) if logo_path else Pt(80)
    title_p.paragraph_format.space_after = Pt(12)
    title_run = title_p.add_run(plant.name.upper() + " SOLAR POWER PLANT")

    title_run.font.name = "Arial"
    title_run.font.size = Pt(28)
    title_run.font.bold = True
    title_run.font.color.rgb = RGBColor(0x1A, 0x52, 0x76)  # Hex #1A5276

    # Subtitle
    sub_p = doc.add_paragraph()
    sub_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub_p.paragraph_format.space_after = Pt(80)
    sub_run = sub_p.add_run("Performance and Degradation Assessment Report")
    sub_run.font.name = "Arial"
    sub_run.font.size = Pt(18)
    sub_run.font.color.rgb = RGBColor(0x2C, 0x3E, 0x50)  # Hex #2C3E50

    # Study Period label
    sp_label_p = doc.add_paragraph()
    sp_label_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sp_label_p.paragraph_format.space_after = Pt(6)
    sp_label_run = sp_label_p.add_run("Study Period")
    sp_label_run.font.name = "Arial"
    sp_label_run.font.size = Pt(14)
    sp_label_run.font.bold = True
    sp_label_run.font.color.rgb = RGBColor(0x2C, 0x3E, 0x50)

    # Study Period values
    sp_val_p = doc.add_paragraph()
    sp_val_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sp_val_p.paragraph_format.space_after = Pt(80)
    
    study_periods_list = []
    for sy in sorted_study_years:
        start, end = sy.split("-")
        study_periods_list.append(f"May {start} – April {end}")
        
    for idx, period in enumerate(study_periods_list):
        if idx > 0:
            sp_val_p.add_run("\n")
        r = sp_val_p.add_run(period)
        r.font.name = "Arial"
        r.font.size = Pt(12)
        r.font.color.rgb = RGBColor(0x34, 0x49, 0x5E)  # Hex #34495E

    # Other metadata paragraphs (Plant Capacity, Location, Commissioned, Prepared by, Date)
    meta_items = [
        ("Plant Capacity: ", f"DC: {plant.installed_dc_capacity_mw} MW | AC: {int(plant.installed_ac_capacity_mw) if plant.installed_ac_capacity_mw.is_integer() else plant.installed_ac_capacity_mw} MW"),
        ("Location: ", f"{plant.location.title()}, Northern Province, {'Sri Lanka' if plant.country.lower() in ('srilanka', 'sri lanka') else plant.country.title()}" if plant.location.lower() == "vavuniya" else f"{plant.location.title()}, {'Sri Lanka' if plant.country.lower() in ('srilanka', 'sri lanka') else plant.country.title()}"),
        ("Commissioned: ", plant.commission_date.strftime("%B %Y")),
        ("Prepared by: ", "WindForce (Pvt) Ltd" if plant.name.lower() == "vydexa" else "SoliZer Intelligence Platform"),
        ("Date: ", datetime.now().strftime("%B %Y"))
    ]

    for label, val in meta_items:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(6)
        
        r1 = p.add_run(label)
        r1.font.name = "Arial"
        r1.font.bold = True
        r1.font.color.rgb = RGBColor(0x2C, 0x3E, 0x50)
        
        r2 = p.add_run(val)
        r2.font.name = "Arial"
        r2.font.color.rgb = RGBColor(0x34, 0x49, 0x5E)

    doc.add_page_break()

    # ───────────────────────────────────────────────────────────────────────
    # Section 1. Plant-Level Performance Analysis
    # ───────────────────────────────────────────────────────────────────────
    h1 = doc.add_heading(level=1)
    h1_run = h1.add_run("1. Plant-Level Performance Analysis")
    h1_run.font.name = "Arial"
    h1_run.font.size = Pt(18)
    h1_run.font.color.rgb = RGBColor(0x1a, 0x36, 0x5d)

    p1 = doc.add_paragraph(
        f"This section presents the overall performance metrics of the {plant.name.title()} Solar Power Plant across "
        f"the three study periods ({', '.join(sorted_study_years)}). Key performance indicators "
        f"including Performance Ratio (PR), Capacity Utilization Factor (CUF), Specific Yield, and Plant Availability "
        f"are evaluated."
    )
    p1.paragraph_format.space_after = Pt(12)

    # Heading for Table 1.1
    h_t1_1 = doc.add_heading(level=2)
    h_t1_1_run = h_t1_1.add_run("Annual Performance Summary")
    h_t1_1_run.font.name = "Arial"
    h_t1_1_run.font.size = Pt(14)
    h_t1_1_run.font.color.rgb = RGBColor(0x2D, 0x37, 0x48)

    # Table caption in Quote style BEFORE table
    cap_t1 = doc.add_paragraph(style="Quote")
    cap_t1.add_run(f"Table 1.1: Annual Performance Summary of {plant.name.title()} Solar Power Plant")
    
    # Note BEFORE table
    note_t1 = doc.add_paragraph()
    note_t1_r = note_t1.add_run(
        "Note: Total Inverter Generation = Generation + Curtailment. \n"
        "Total Possible Generation = Generation + Curtailment + Grid Loss + Machine Loss"
    )
    note_t1_r.font.size = Pt(9)
    note_t1_r.font.italic = True
    note_t1_r.font.color.rgb = RGBColor(0x71, 0x80, 0x96)

    # Table 1.1 structure
    t1 = doc.add_table(rows=8, cols=3 + len(sorted_study_years))
    t1.style = 'Light Shading Accent 1'
    headers_t1 = ["Parameter", "Unit"] + sorted_study_years + ["Avg"]
    for idx, h in enumerate(headers_t1):
        cell = t1.rows[0].cells[idx]
        write_cell(cell, h, bold=True, color_rgb=RGBColor(0xff, 0xff, 0xff), align="LEFT" if idx < 2 else "RIGHT")
        set_cell_background(cell, "1A365D")

    years_data = []
    for label in sorted_study_years:
        recs = study_year_records[label]
        y_lt = aggregate_to_lifetime(recs)
        y_kp = compute_lifetime_kpis(plant, y_lt)
        y_avail = calculate_availability(y_lt.total_generation, y_lt.total_possible_generation)
        y_irr = sum(d.irradiation for d in recs) / 100.0
        years_data.append({
            "gen": y_lt.total_generation / 1000.0,
            "possible_gen": y_lt.total_possible_generation / 1000.0,
            "irrad": y_irr,
            "pr": y_kp.performance_ratio,
            "cuf": y_kp.cuf,
            "sy": y_kp.specific_yield,
            "avail": y_avail
        })

    # Calculations for Avg column
    avg_gen = sum(yd["gen"] for yd in years_data) / len(years_data)
    avg_poss = sum(yd["possible_gen"] for yd in years_data) / len(years_data)
    avg_irr = sum(yd["irrad"] for yd in years_data) / len(years_data)
    avg_pr = kpis.performance_ratio
    avg_cuf = kpis.cuf
    avg_sy = sum(yd["sy"] for yd in years_data) / len(years_data)
    avg_avail = sum(yd["avail"] for yd in years_data) / len(years_data)

    rows_data_t1 = [
        ("Total Generation", "MWh", [f"{yd['gen']:,.1f}" for yd in years_data] + [f"{avg_gen:,.1f}"]),
        ("Total Possible Generation", "MWh", [f"{yd['possible_gen']:,.1f}" for yd in years_data] + [f"{avg_poss:,.1f}"]),
        ("Total Irradiation", "kWh/m²", [f"{yd['irrad']:,.1f}" for yd in years_data] + [f"{avg_irr:,.1f}"]),
        ("Performance Ratio", "%", [f"{yd['pr']:.2f}%" for yd in years_data] + [f"{avg_pr:.2f}%"]),
        ("CUF", "%", [f"{yd['cuf']:.2f}%" for yd in years_data] + [f"{avg_cuf:.2f}%"]),
        ("Specific Yield", "kWh/kWp", [f"{yd['sy']:.1f}" for yd in years_data] + [f"{avg_sy:.1f}"]),
        ("Plant Availability", "%", [f"{yd['avail']:.2f}%" for yd in years_data] + [f"{avg_avail:.2f}%"]),
    ]

    for row_idx, (param, unit, vals) in enumerate(rows_data_t1):
        row = t1.rows[row_idx + 1]
        write_cell(row.cells[0], param, bold=False, align="LEFT")
        write_cell(row.cells[1], unit, bold=False, align="LEFT")
        for val_idx, val in enumerate(vals):
            is_avg = (val_idx == len(vals) - 1)
            formatted_val = val
            if row_idx == 3:  # PR
                # Year columns have "%", Avg column does NOT.
                if is_avg and formatted_val.endswith("%"):
                    formatted_val = formatted_val[:-1]
                elif not is_avg and not formatted_val.endswith("%"):
                    formatted_val += "%"
            elif row_idx == 4:  # CUF
                # All columns have "%".
                if not formatted_val.endswith("%"):
                    formatted_val += "%"
            elif row_idx == 6:  # Plant Availability
                # None of the columns have "%".
                if formatted_val.endswith("%"):
                    formatted_val = formatted_val[:-1]
                    
            write_cell(row.cells[2 + val_idx], formatted_val, bold=False, align="RIGHT")
        if row_idx % 2 == 0:
            for cell in row.cells:
                set_cell_background(cell, "F7FAFC")

    col_widths_t1 = [2.2, 0.8] + [0.8] * (len(sorted_study_years) + 1)
    set_table_col_widths_and_padding(t1, col_widths_t1)

    doc.add_paragraph().paragraph_format.space_before = Pt(12)

    # Monthly PR Chart
    h_pr = doc.add_heading("1.2 Monthly Performance Ratio", level=2)
    h_pr_r = h_pr.runs[0]
    h_pr_r.font.name = "Arial"
    h_pr_r.font.size = Pt(14)
    h_pr_r.font.color.rgb = RGBColor(0x2D, 0x37, 0x48)
    
    p_pr_intro = doc.add_paragraph(
        "The Performance Ratio (PR) is a key indicator of plant efficiency, representing the ratio of actual energy output to the theoretically possible output based on the received irradiation and installed DC capacity. A higher PR indicates better plant performance."
    )
    p_pr_intro.paragraph_format.space_after = Pt(6)
    p_pr_calc_lbl = doc.add_paragraph()
    p_pr_calc_lbl.add_run("PR Calculation:").bold = True
    p_pr_calc_p = doc.add_paragraph(
        "Performance Ratio (%) = Generation (kWh)/(Irradiance(W/sqm) x Total Panel Area (sqm) x Module Efficiency x Running Hours per day) x 100%"
    )
    p_pr_calc_p.paragraph_format.space_after = Pt(12)

    doc.add_picture(charts["pr"], width=Inches(6.0))
    p_fig = doc.add_paragraph(style="Quote")
    p_fig.add_run("Figure 1.1: Monthly Average Performance Ratio Comparison")
    p_fig.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_fig.paragraph_format.space_after = Pt(12)

    # Monthly Specific Yield Chart
    h_sy = doc.add_heading("1.3 Specific Yield", level=2)
    h_sy_r = h_sy.runs[0]
    h_sy_r.font.name = "Arial"
    h_sy_r.font.size = Pt(14)
    h_sy_r.font.color.rgb = RGBColor(0x2D, 0x37, 0x48)
    
    p_sy_intro = doc.add_paragraph(
        "Specific Yield represents the energy generated per unit of installed DC capacity (kWh/kWp). It is a standardized metric that allows comparison across plants of different sizes."
    )
    p_sy_intro.paragraph_format.space_after = Pt(12)

    doc.add_picture(charts["specific_yield"], width=Inches(6.0))
    p_fig_sy = doc.add_paragraph(style="Quote")
    p_fig_sy.add_run("Figure 1.3: Monthly Specific Yield Comparison")
    p_fig_sy.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_fig_sy.paragraph_format.space_after = Pt(24)

    doc.add_page_break()

    # ───────────────────────────────────────────────────────────────────────
    # Section 2. Inverter-Level Performance Analysis
    # ───────────────────────────────────────────────────────────────────────
    h2 = doc.add_heading(level=1)
    h2_run = h2.add_run("2. Inverter-Level Performance Analysis")
    h2_run.font.name = "Arial"
    h2_run.font.size = Pt(18)
    h2_run.font.color.rgb = RGBColor(0x1a, 0x36, 0x5d)

    p2 = doc.add_paragraph(
        f"The {plant.name.title()} plant consists of {plant.number_of_blocks} inverter blocks, "
        f"each containing {plant.number_of_inverters // plant.number_of_blocks} inverters, "
        f"totaling {plant.number_of_inverters} inverters. This section examines individual inverter performance to identify underperforming or degraded units."
    )
    p2.paragraph_format.space_after = Pt(12)

    # Heading 2.1 Inverter Annual Generation
    h_t2_1 = doc.add_heading("2.1 Inverter Annual Generation", level=2)
    h_t2_1.runs[0].font.name = "Arial"
    h_t2_1.runs[0].font.size = Pt(14)
    h_t2_1.runs[0].font.color.rgb = RGBColor(0x2D, 0x37, 0x48)
    
    p_t2_1_note = doc.add_paragraph()
    p_t2_1_note_r = p_t2_1_note.add_run("Note: Inverter Generation = Generation + Curtailment")
    p_t2_1_note_r.font.size = Pt(9)
    p_t2_1_note_r.font.italic = True
    p_t2_1_note_r.font.color.rgb = RGBColor(0x71, 0x80, 0x96)

    # Caption BEFORE Table 2.1
    cap_t2 = doc.add_paragraph(style="Quote")
    cap_t2.add_run("Table 2.1: Inverter Annual Generation Summary")

    t2 = doc.add_table(rows=len(sorted_inverters) + 1, cols=2 + len(sorted_study_years))
    t2.style = 'Light Shading Accent 1'
    headers_t2 = ["Inverter"] + [f"{sy} (MWh)" for sy in sorted_study_years] + ["Change (%)"]
    for idx, h in enumerate(headers_t2):
        cell = t2.rows[0].cells[idx]
        write_cell(cell, h, bold=True, color_rgb=RGBColor(0xff, 0xff, 0xff), align="LEFT" if idx == 0 else "RIGHT")
        set_cell_background(cell, "1A365D")

    for row_idx, inv in enumerate(sorted_inverters):
        row = t2.rows[row_idx + 1]
        write_cell(row.cells[0], format_inverter_name(inv.name), bold=False, align="LEFT")
        y_vals = []
        for sy_idx, sy in enumerate(sorted_study_years):
            val_mwh = inverter_yearly_data[inv.id][sy]["generation"] / 1000.0
            y_vals.append(val_mwh)
            write_cell(row.cells[1 + sy_idx], f"{val_mwh:,.1f}", bold=False, align="RIGHT")
        
        # Calculate percentage change
        chg = 0.0
        if len(y_vals) > 1 and y_vals[0] > 0:
            chg = (y_vals[-1] - y_vals[0]) / y_vals[0] * 100.0
        write_cell(row.cells[1 + len(sorted_study_years)], f"{chg:+.2f}%", bold=False, align="RIGHT")
        
        if row_idx % 2 == 0:
            for cell in row.cells:
                set_cell_background(cell, "F7FAFC")

    col_widths_t2 = [2.0] + [1.0] * (len(sorted_study_years) + 1)
    set_table_col_widths_and_padding(t2, col_widths_t2)

    doc.add_paragraph().paragraph_format.space_before = Pt(12)
    doc.add_picture(charts["inverters_gen"], width=Inches(6.0))
    p_fig2 = doc.add_paragraph(style="Quote")
    p_fig2.add_run("Figure 2.1: Inverter-Level Annual Generation Comparison")
    p_fig2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_fig2.paragraph_format.space_after = Pt(24)

    doc.add_page_break()

    # Heading 2.2 Inverter Performance Ratio
    h_t2_2 = doc.add_heading("2.2 Inverter Performance Ratio", level=2)
    h_t2_2.runs[0].font.name = "Arial"
    h_t2_2.runs[0].font.size = Pt(14)
    h_t2_2.runs[0].font.color.rgb = RGBColor(0x2D, 0x37, 0x48)
    
    p_t2_2_intro = doc.add_paragraph(
        "The following chart and table present the annual Performance Ratio for each inverter. Variations across inverters may indicate issues such as soiling, shading, or equipment degradation."
    )
    p_t2_2_intro.paragraph_format.space_after = Pt(12)

    # Caption BEFORE Table 2.2
    cap_t3 = doc.add_paragraph(style="Quote")
    cap_t3.add_run("Table 2.2: Inverter Annual Performance Ratio")

    t3 = doc.add_table(rows=len(sorted_inverters) + 1, cols=2 + len(sorted_study_years))
    t3.style = 'Light Shading Accent 1'
    headers_t3 = ["Inverter"] + [f"{sy} (%)" for sy in sorted_study_years] + ["Change"]
    for idx, h in enumerate(headers_t3):
        cell = t3.rows[0].cells[idx]
        write_cell(cell, h, bold=True, color_rgb=RGBColor(0xff, 0xff, 0xff), align="LEFT" if idx == 0 else "RIGHT")
        set_cell_background(cell, "1A365D")

    eff_frac = plant.module_efficiency / 100.0
    inv_area = plant.total_panel_area_sqm / max(plant.number_of_inverters, 1)

    for row_idx, inv in enumerate(sorted_inverters):
        row = t3.rows[row_idx + 1]
        write_cell(row.cells[0], format_inverter_name(inv.name), bold=False, align="LEFT")
        y_prs = []
        for sy_idx, sy in enumerate(sorted_study_years):
            gen = inverter_yearly_data[inv.id][sy]["generation"]
            irrad = inverter_yearly_data[inv.id][sy]["irradiation"]
            pr_val = calculate_pr(gen, irrad, inv_area, eff_frac, plant.daily_running_hours)
            y_prs.append(pr_val)
            # No % symbol inside cell, just number format matching example
            write_cell(row.cells[1 + sy_idx], f"{pr_val:.2f}", bold=False, align="RIGHT")
        
        # Calculate PR difference (absolute points)
        chg = 0.0
        if len(y_prs) > 1:
            chg = y_prs[-1] - y_prs[0]
        write_cell(row.cells[1 + len(sorted_study_years)], f"{chg:+.2f}%", bold=False, align="RIGHT")
        
        if row_idx % 2 == 0:
            for cell in row.cells:
                set_cell_background(cell, "F7FAFC")

    set_table_col_widths_and_padding(t3, col_widths_t2)

    doc.add_paragraph().paragraph_format.space_before = Pt(12)
    doc.add_picture(charts["inverters_pr"], width=Inches(6.0))
    p_fig_inv_pr = doc.add_paragraph(style="Quote")
    p_fig_inv_pr.add_run("Figure 2.2: Inverter-Level Annual Performance Ratio")
    p_fig_inv_pr.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_fig_inv_pr.paragraph_format.space_after = Pt(24)

    doc.add_page_break()

    # Block-Level Comparison (Section 2.3)
    h_blk = doc.add_heading("2.3 Block-Level Comparison", level=2)
    h_blk.runs[0].font.name = "Arial"
    h_blk.runs[0].font.size = Pt(14)
    h_blk.runs[0].font.color.rgb = RGBColor(0x2D, 0x37, 0x48)
    
    p_block = doc.add_paragraph(
        f"The following chart compares the annual generation at the block level. Each block consists of multiple inverters, "
        f"and contributes approximately {100 // plant.number_of_blocks}% of the total plant capacity."
    )
    p_block.paragraph_format.space_after = Pt(12)
    
    doc.add_picture(charts["blocks_gen"], width=Inches(6.0))
    p_fig2_blk = doc.add_paragraph(style="Quote")
    p_fig2_blk.add_run("Figure 2.3: Block-Level Annual Generation Comparison")
    p_fig2_blk.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_fig2_blk.paragraph_format.space_after = Pt(24)

    doc.add_page_break()

    # ───────────────────────────────────────────────────────────────────────
    # Section 3. Irradiation Analysis
    # ───────────────────────────────────────────────────────────────────────
    h3 = doc.add_heading(level=1)
    h3_run = h3.add_run("3. Irradiation Analysis")
    h3_run.font.name = "Arial"
    h3_run.font.size = Pt(18)
    h3_run.font.color.rgb = RGBColor(0x1a, 0x36, 0x5d)

    p3_intro = doc.add_paragraph(
        f"Irradiation is the primary driver of solar energy generation. This section analyzes the solar resource received "
        f"at the {plant.name.title()} plant site over the study periods. The irradiation data is measured in Wh/m² (daily) "
        f"and presented as kWh/m² for monthly and annual aggregations."
    )
    p3_intro.paragraph_format.space_after = Pt(12)

    # Heading 3.1 Annual Irradiation Summary
    h_t3_1 = doc.add_heading("3.1 Annual Irradiation Summary", level=2)
    h_t3_1.runs[0].font.name = "Arial"
    h_t3_1.runs[0].font.size = Pt(14)
    h_t3_1.runs[0].font.color.rgb = RGBColor(0x2D, 0x37, 0x48)

    # Caption BEFORE Table 3.1
    cap_t4 = doc.add_paragraph(style="Quote")
    cap_t4.add_run("Table 3.1: Annual Irradiation Summary")

    t4 = doc.add_table(rows=1 + len(sorted_study_years), cols=5)
    t4.style = 'Light Shading Accent 1'
    headers_t4 = ["Year", "Total Irradiation (kWh/m²)", "Avg Daily (Wh/m²)", "Peak Month", "Lowest Month"]
    for idx, h in enumerate(headers_t4):
        cell = t4.rows[0].cells[idx]
        write_cell(cell, h, bold=True, color_rgb=RGBColor(0xff, 0xff, 0xff), align="LEFT" if idx in (0, 3, 4) else "RIGHT")
        set_cell_background(cell, "1A365D")

    for idx, label in enumerate(sorted_study_years):
        recs = study_year_records[label]
        num_days = len(recs)
        total_irr = sum(d.irradiation for d in recs) / 100.0
        avg_daily = sum(d.irradiation for d in recs) / max(num_days, 1)
        
        # Find peak/lowest month
        m_recs = aggregate_to_monthly(recs)
        max_m = max(m_recs, key=lambda mr: mr.irradiation)
        min_m = min(m_recs, key=lambda mr: mr.irradiation)
        peak_month = f"{_MONTH_NAMES[max_m.month]} {max_m.year}"
        lowest_month = f"{_MONTH_NAMES[min_m.month]} {min_m.year}"

        row = t4.rows[idx + 1]
        write_cell(row.cells[0], label, bold=False, align="LEFT")
        write_cell(row.cells[1], f"{total_irr:,.1f}", bold=False, align="RIGHT")
        write_cell(row.cells[2], f"{avg_daily:.1f}", bold=False, align="RIGHT")
        write_cell(row.cells[3], peak_month, bold=False, align="LEFT")
        write_cell(row.cells[4], lowest_month, bold=False, align="LEFT")
        
        if idx % 2 == 0:
            for cell in row.cells:
                set_cell_background(cell, "F7FAFC")

    col_widths_t4 = [1.2, 1.8, 1.2, 1.1, 1.1]
    set_table_col_widths_and_padding(t4, col_widths_t4)

    # Heading 3.2 Monthly Irradiation Comparison
    doc.add_heading("3.2 Monthly Irradiation Comparison", level=2)
    p_t3_2 = doc.add_paragraph(
        f"The monthly irradiation pattern shows typical seasonal variation for the region of {plant.location.title()}. "
        f"Higher irradiation is generally observed during dry season months, while lower values occur during monsoon periods."
    )
    p_t3_2.paragraph_format.space_after = Pt(12)

    doc.add_picture(charts["irradiation"], width=Inches(6.0))
    p_fig3 = doc.add_paragraph(style="Quote")
    p_fig3.add_run("Figure 3.1: Monthly Irradiation Comparison")
    p_fig3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_fig3.paragraph_format.space_after = Pt(24)

    doc.add_page_break()

    # ───────────────────────────────────────────────────────────────────────
    # Section 4. Generation Analysis
    # ───────────────────────────────────────────────────────────────────────
    h4 = doc.add_heading(level=1)
    h4_run = h4.add_run("4. Generation Analysis")
    h4_run.font.name = "Arial"
    h4_run.font.size = Pt(18)
    h4_run.font.color.rgb = RGBColor(0x1a, 0x36, 0x5d)

    p4_intro = doc.add_paragraph(
        f"This section provides a detailed analysis of the energy generation at the {plant.name.title()} Solar Power Plant over "
        f"the study period, including annual totals, monthly patterns, and trends. All generation values in this section represent "
        f"Total Generation (Generation + Curtailment), which reflects the actual energy produced by the plant before any curtailment losses."
    )
    p4_intro.paragraph_format.space_after = Pt(12)

    # 4.1 Annual Generation Summary
    doc.add_heading("4.1 Annual Generation Summary", level=2)
    p_gen_ann_note = doc.add_paragraph()
    p_gen_ann_note_r = p_gen_ann_note.add_run("Note: Total Generation = Generation + Curtailments")
    p_gen_ann_note_r.font.size = Pt(9)
    p_gen_ann_note_r.font.italic = True
    p_gen_ann_note_r.font.color.rgb = RGBColor(0x71, 0x80, 0x96)

    doc.add_picture(charts["annual_generation"], width=Inches(6.0))
    p_fig4_1 = doc.add_paragraph(style="Quote")
    p_fig4_1.add_run("Figure 4.1: Annual Total Generation")
    p_fig4_1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_fig4_1.paragraph_format.space_after = Pt(24)

    doc.add_page_break()

    # 4.2 Monthly Generation Details
    doc.add_heading("4.2 Monthly Generation Details", level=2)
    
    # Generate tables for each study year
    table_num = 1
    for sy in sorted_study_years:
        h_sy_tbl = doc.add_heading(sy, level=3)
        h_sy_tbl.runs[0].font.name = "Arial"
        h_sy_tbl.runs[0].font.size = Pt(12)
        h_sy_tbl.runs[0].font.color.rgb = RGBColor(0x2D, 0x37, 0x48)

        # Caption BEFORE monthly performance table
        cap_t5 = doc.add_paragraph(style="Quote")
        cap_t5.add_run(f"Table 4.{table_num}: Monthly Generation Details - {sy}")

        t5_sy = doc.add_table(rows=14, cols=6)
        t5_sy.style = 'Light Shading Accent 1'
        headers_t5 = ["Month", "Generation (MWh)", "Irradiation (kWh/m²)", "PR (%)", "CUF (%)", "Spec. Yield (kWh/kWp)"]
        for idx, h in enumerate(headers_t5):
            cell = t5_sy.rows[0].cells[idx]
            write_cell(cell, h, bold=True, color_rgb=RGBColor(0xff, 0xff, 0xff), align="LEFT" if idx == 0 else "RIGHT")
            set_cell_background(cell, "1A365D")

        months_nums = [5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3, 4]
        sy_recs = study_year_records[sy]
        m_records = aggregate_to_monthly(sy_recs)
        m_kpis = compute_monthly_kpis(plant, m_records)
        
        # Build map for easy ordering
        kpi_map = {mk.month: mk for mk in m_kpis}
        
        total_gen = 0.0
        total_irr = 0.0
        total_days = 0
        
        for row_idx, m_num in enumerate(months_nums):
            row = t5_sy.rows[row_idx + 1]
            mk = kpi_map.get(m_num)
            if mk:
                mr = next(mr for mr in m_records if mr.month == m_num)
                total_gen += mr.total_generation
                total_irr += mr.irradiation
                total_days += mr.days
                
                write_cell(row.cells[0], mk.label, bold=False, align="LEFT")
                write_cell(row.cells[1], f"{mk.generation_mwh:,.1f}", bold=False, align="RIGHT")
                write_cell(row.cells[2], f"{mk.irradiation_kwh_m2:,.1f}", bold=False, align="RIGHT")
                write_cell(row.cells[3], f"{mk.pr:.2f}", bold=False, align="RIGHT")
                write_cell(row.cells[4], f"{mk.cuf:.2f}", bold=False, align="RIGHT")
                write_cell(row.cells[5], f"{mk.specific_yield:.1f}", bold=False, align="RIGHT")
            else:
                label_name = f"{_MONTH_NAMES[m_num]} {sy.split('-')[0] if m_num >= 5 else sy.split('-')[1]}"
                write_cell(row.cells[0], label_name, bold=False, align="LEFT")
                for c in range(1, 6):
                    write_cell(row.cells[c], "0.0", bold=False, align="RIGHT")
            if row_idx % 2 == 0:
                for cell in row.cells:
                    set_cell_background(cell, "F7FAFC")
                    
        # Total/Avg Row
        total_row = t5_sy.rows[13]
        write_cell(total_row.cells[0], "Total/Avg", bold=True, align="LEFT")
        avg_pr_val = calculate_pr(total_gen, total_irr, plant.total_panel_area_sqm, eff_frac, plant.daily_running_hours)
        avg_cuf_val = calculate_cuf(total_gen, plant.installed_ac_capacity_mw, total_days * 24.0)
        tot_sy_val = calculate_specific_yield(total_gen, plant.installed_dc_capacity_mw)
        
        write_cell(total_row.cells[1], f"{total_gen/1000.0:,.1f}", bold=True, align="RIGHT")
        write_cell(total_row.cells[2], f"{total_irr/100.0:,.1f}", bold=True, align="RIGHT")
        write_cell(total_row.cells[3], f"{avg_pr_val:.2f}", bold=True, align="RIGHT")
        write_cell(total_row.cells[4], f"{avg_cuf_val:.2f}", bold=True, align="RIGHT")
        write_cell(total_row.cells[5], f"{tot_sy_val:.1f}", bold=True, align="RIGHT")
        for cell in total_row.cells:
            set_cell_background(cell, "EDF2F7")
            
        col_widths_t5 = [1.2, 1.1, 1.2, 0.8, 0.8, 1.2]
        set_table_col_widths_and_padding(t5_sy, col_widths_t5)
        
        doc.add_paragraph().paragraph_format.space_before = Pt(12)
        table_num += 1

    # Section 4.3: Monthly Generation Comparison
    doc.add_heading("4.3 Monthly Generation Comparison", level=2)
    doc.add_picture(charts["generation"], width=Inches(6.0))
    p_fig_gen = doc.add_paragraph(style="Quote")
    p_fig_gen.add_run("Figure 4.2: Monthly Total Generation Comparison Across Years")
    p_fig_gen.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_fig_gen.paragraph_format.space_after = Pt(24)

    doc.add_page_break()

    # ───────────────────────────────────────────────────────────────────────
    # Section 5. Performance Ratio Assessment
    # ───────────────────────────────────────────────────────────────────────
    h5 = doc.add_heading(level=1)
    h5_run = h5.add_run("5. Performance Ratio Assessment")
    h5_run.font.name = "Arial"
    h5_run.font.size = Pt(18)
    h5_run.font.color.rgb = RGBColor(0x1a, 0x36, 0x5d)

    p_pr_assess_intro = doc.add_paragraph(
        f"The Performance Ratio (PR) is a key indicator used to evaluate the operational performance of a solar photovoltaic power plant. "
        f"It measures how effectively the plant converts available solar irradiation into electrical energy after accounting for system losses. "
        f"The {plant.name.title()} Solar Power Plant was evaluated using monthly PR values over the study period. Trend analysis of PR was conducted to assess changes in overall plant performance and identify long-term performance patterns."
    )
    p_pr_assess_intro.paragraph_format.space_after = Pt(12)

    doc.add_heading("5.1 Plant-Level Performance Ratio Trend", level=2)
    p_pr_trend_p = doc.add_paragraph(
        f"The Performance Ratio trend over the three-year study period was analysed to assess the overall performance evolution of the {plant.name.title()} Solar Power Plant. A linear regression was applied to the monthly PR values to identify the long-term performance trend."
    )
    p_pr_trend_p.paragraph_format.space_after = Pt(12)

    doc.add_picture(charts["trend"], width=Inches(6.0))
    p_fig5 = doc.add_paragraph(style="Quote")
    p_fig5.add_run("Figure 5.1: Monthly Average Performance Ratio Trend")
    p_fig5.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_fig5.paragraph_format.space_after = Pt(24)

    p_observed_trend_rate = doc.add_paragraph()
    p_observed_trend_rate.add_run(f"Observed PR Trend Rate: -{deg.annual_degradation_rate}% per year").bold = True
    
    p_deg_desc = doc.add_paragraph(
        f"Based on the linear regression analysis of monthly Performance Ratio values, the plant exhibited an overall PR decline "
        f"of approximately {deg.annual_degradation_rate}% per year during the study period. While this trend indicates a reduction "
        f"in overall system performance, it may be influenced by multiple factors including equipment ageing, inverter performance variations, "
        f"operational losses, maintenance activities, and grid-related events. Therefore, the observed PR trend represents the overall "
        f"performance change of the plant rather than photovoltaic module degradation alone."
    )
    p_deg_desc.paragraph_format.space_after = Pt(24)

    doc.add_page_break()

    # ───────────────────────────────────────────────────────────────────────
    # Section 6. Loss Analysis
    # ───────────────────────────────────────────────────────────────────────
    h6 = doc.add_heading(level=1)
    h6_run = h6.add_run("6. Loss Analysis")
    h6_run.font.name = "Arial"
    h6_run.font.size = Pt(18)
    h6_run.font.color.rgb = RGBColor(0x1a, 0x36, 0x5d)

    p_loss_intro = doc.add_paragraph(
        f"This section quantifies the energy losses at the {plant.name.title()} plant. Energy production at the {plant.name.title()} Solar Power Plant "
        f"is limited by three primary operational and technical losses:"
    )
    p_loss_intro.paragraph_format.space_after = Pt(6)
    
    # Loss Bullets
    bullets_losses = [
        ("Machine Losses: ", "Energy lost due to internal equipment issues, such as failures or routine maintenance."),
        ("Grid Failure Losses: ", "Un-exported power caused by utility grid outages."),
        ("Curtailment Losses: ", "Intentional generation limits imposed by the Electricity Board.")
    ]
    for bullet_lbl, bullet_txt in bullets_losses:
        bp = doc.add_paragraph(style="List Bullet")
        r_lbl = bp.add_run(bullet_lbl)
        r_lbl.bold = True
        bp.add_run(bullet_txt)
        
    p_loss_summary_intro = doc.add_paragraph(
        "Combined, grid failures and curtailment make up the plant's total Grid Loss. Tracking these metrics is essential for evaluating and improving overall plant performance."
    )
    p_loss_summary_intro.paragraph_format.space_after = Pt(12)

    # Heading 6.1 Annual Loss Summary
    doc.add_heading("6.1 Annual Loss Summary", level=2)
    
    # Caption BEFORE Table 6.1
    cap_t6 = doc.add_paragraph(style="Quote")
    cap_t6.add_run("Table 6.1: Annual Loss Summary")

    t6 = doc.add_table(rows=1 + len(sorted_study_years), cols=6)
    t6.style = 'Light Shading Accent 1'
    headers_t6 = ["Year", "Grid Loss (MWh)", "Machine Loss (MWh)", "Total Loss (MWh)", "Loss %", "Generation (MWh)"]
    for idx, h in enumerate(headers_t6):
        cell = t6.rows[0].cells[idx]
        write_cell(cell, h, bold=True, color_rgb=RGBColor(0xff, 0xff, 0xff), align="LEFT" if idx == 0 else "RIGHT")
        set_cell_background(cell, "1A365D")

    for idx, label in enumerate(sorted_study_years):
        recs = study_year_records[label]
        y_lt = aggregate_to_lifetime(recs)
        y_loss_sum = (y_lt.grid_loss + y_lt.machine_loss) / 1000.0
        y_loss_pct = ((y_lt.grid_loss + y_lt.machine_loss) / max(y_lt.total_possible_generation, 1.0)) * 100.0
        
        row = t6.rows[idx + 1]
        write_cell(row.cells[0], label, bold=False, align="LEFT")
        write_cell(row.cells[1], f"{y_lt.grid_loss/1000.0:,.1f}", bold=False, align="RIGHT")
        write_cell(row.cells[2], f"{y_lt.machine_loss/1000.0:,.1f}", bold=False, align="RIGHT")
        write_cell(row.cells[3], f"{y_loss_sum:,.1f}", bold=False, align="RIGHT")
        write_cell(row.cells[4], f"{y_loss_pct:.2f}%", bold=False, align="RIGHT")
        write_cell(row.cells[5], f"{y_lt.total_generation/1000.0:,.1f}", bold=False, align="RIGHT")
        
        if idx % 2 == 0:
            for cell in row.cells:
                set_cell_background(cell, "F7FAFC")

    col_widths_t6 = [1.2, 1.1, 1.2, 1.0, 0.8, 1.0]
    set_table_col_widths_and_padding(t6, col_widths_t6)

    # Heading 6.2 Monthly Loss Breakdown
    doc.add_heading("6.2 Monthly Loss Breakdown", level=2)
    doc.add_paragraph("The stacked bar charts below illustrate the monthly distribution of losses by type for each year.")
    doc.add_paragraph().paragraph_format.space_before = Pt(12)
    
    fig_idx = 1
    for sy in sorted_study_years:
        doc.add_picture(charts[f"losses_{sy}"], width=Inches(6.0))
        p_fig6_item = doc.add_paragraph(style="Quote")
        p_fig6_item.add_run(f"Figure 6.{fig_idx}: Monthly Loss Breakdown - {sy}")
        p_fig6_item.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_fig6_item.paragraph_format.space_after = Pt(24)
        fig_idx += 1

    doc.add_page_break()

    # Section 6.3 Inverter Level Loss Comparison
    doc.add_heading("6.3 Inverter-Level Loss Comparison", level=2)
    p_t6_3_intro = doc.add_paragraph("The chart below compares total losses across all inverters to identify units with higher-than-average losses.")
    p_t6_3_intro.paragraph_format.space_after = Pt(12)
    
    doc.add_picture(charts["losses_inv"], width=Inches(6.0))
    p_fig6_inv = doc.add_paragraph(style="Quote")
    p_fig6_inv.add_run("Figure 6.3: Inverter-Level Total Losses")
    p_fig6_inv.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_fig6_inv.paragraph_format.space_after = Pt(24)

    doc.add_page_break()

    # ───────────────────────────────────────────────────────────────────────
    # Section 7. Findings
    # ───────────────────────────────────────────────────────────────────────
    h7 = doc.add_heading(level=1)
    h7_run = h7.add_run("7. Findings")
    h7_run.font.name = "Arial"
    h7_run.font.size = Pt(18)
    h7_run.font.color.rgb = RGBColor(0x1a, 0x36, 0x5d)

    # 7.1 Key Performance Findings
    doc.add_heading("7.1 Key Performance Findings", level=2)
    y_first = sorted_study_years[0]
    y_last = sorted_study_years[-1]
    gen_first = sum(d.total_generation for d in study_year_records[y_first]) / 1000.0
    gen_last = sum(d.total_generation for d in study_year_records[y_last]) / 1000.0
    diff_pct = (gen_last - gen_first) / gen_first * 100.0
    direction = "decreased" if diff_pct < 0 else "increased"

    p_f1 = doc.add_paragraph(style="List Bullet")
    p_f1.add_run(f"The plant generated a total of {lifetime.total_generation/1000.0:,.1f} MWh over the {len(sorted_study_years)}-year study period.")
    p_f2 = doc.add_paragraph(style="List Bullet")
    p_f2.add_run(f"Annual generation {direction} by {abs(diff_pct):.1f}% from {y_first} to {y_last} ({gen_first:,.1f} MWh to {gen_last:,.1f} MWh).")
    p_f3 = doc.add_paragraph(style="List Bullet")
    p_f3.add_run(f"The average annual Performance Ratio across the study period was {kpis.performance_ratio:.2f}%.")

    # 7.2 Inverter Performance Findings
    doc.add_heading("7.2 Inverter Performance Findings", level=2)
    best_inv_name = ""
    best_inv_pr = -1.0
    worst_inv_name = ""
    worst_inv_pr = 999.0
    for inv in sorted_inverters:
        gen = inverter_yearly_data[inv.id][y_last]["generation"]
        irrad = inverter_yearly_data[inv.id][y_last]["irradiation"]
        pr_val = calculate_pr(gen, irrad, inv_area, eff_frac, plant.daily_running_hours)
        if pr_val > best_inv_pr:
            best_inv_pr = pr_val
            best_inv_name = inv.name
        if pr_val < worst_inv_pr:
            worst_inv_pr = pr_val
            worst_inv_name = inv.name

    p_i1 = doc.add_paragraph(style="List Bullet")
    p_i1.add_run(f"Best performing inverter in {y_last}: {format_inverter_name(best_inv_name)} with PR of {best_inv_pr:.2f}%.")
    p_i2 = doc.add_paragraph(style="List Bullet")
    p_i2.add_run(f"Lowest performing inverter in {y_last}: {format_inverter_name(worst_inv_name)} with PR of {worst_inv_pr:.2f}%.")
    p_i3 = doc.add_paragraph(style="List Bullet")
    p_i3.add_run(f"The PR variation among inverters is {best_inv_pr - worst_inv_pr:.2f} percentage points, indicating notable variation in performance across inverters.")

    # 7.3 Loss Findings
    doc.add_heading("7.3 Loss Findings", level=2)
    dominant = "Grid Losses" if lifetime.grid_loss > lifetime.machine_loss else "Machine Losses"
    loss_pct = ((lifetime.grid_loss + lifetime.machine_loss) / max(lifetime.total_possible_generation, 1.0)) * 100.0

    p_l1 = doc.add_paragraph(style="List Bullet")
    p_l1.add_run(f"Total Grid Losses over the study period: {lifetime.grid_loss/1000.0:,.1f} MWh.")
    p_l2 = doc.add_paragraph(style="List Bullet")
    p_l2.add_run(f"Total Machine Losses over the study period: {lifetime.machine_loss/1000.0:,.1f} MWh.")
    p_l3 = doc.add_paragraph(style="List Bullet")
    p_l3.add_run(f"{dominant} represent the dominant source of energy loss at the plant.")
    p_l4 = doc.add_paragraph(style="List Bullet")
    p_l4.add_run(f"Combined losses represent approximately {loss_pct:.2f}% of total possible generation.")

    # 7.4 Irradiation Findings
    doc.add_heading("7.4 Irradiation Findings", level=2)
    annual_irrads = []
    for label in sorted_study_years:
        recs = study_year_records[label]
        annual_irrads.append(sum(d.irradiation for d in recs) / 100.0)

    p_ir1 = doc.add_paragraph(style="List Bullet")
    p_ir1.add_run(f"Annual irradiation ranged from {min(annual_irrads):,.1f} to {max(annual_irrads):,.1f} kWh/m².")

    doc.add_page_break()

    # ───────────────────────────────────────────────────────────────────────
    # Section 8. Recommendations
    # ───────────────────────────────────────────────────────────────────────
    h8 = doc.add_heading(level=1)
    h8_run = h8.add_run("8. Recommendations")
    h8_run.font.name = "Arial"
    h8_run.font.size = Pt(18)
    h8_run.font.color.rgb = RGBColor(0x1a, 0x36, 0x5d)

    # 8.1 Performance Improvement Recommendations
    doc.add_heading("8.1 Performance Improvement Recommendations", level=2)
    
    p_rec1 = doc.add_paragraph()
    p_rec1.add_run("Module Cleaning Program: ").bold = True
    p_rec1.add_run(f"Implement a regular cleaning schedule for all PV modules, particularly during dry and dusty months. Soiling can significantly reduce power output, especially in the dry zone of {plant.location.title()}. A monthly or bi-weekly cleaning schedule is recommended.")

    p_rec2 = doc.add_paragraph()
    p_rec2.add_run("Inverter Maintenance: ").bold = True
    p_rec2.add_run(f"Focus maintenance attention on underperforming inverters, particularly {format_inverter_name(worst_inv_name)}. Conduct detailed inspection of DC input connections, string performance. Regular preventive maintenance should be scheduled quarterly.")

    p_rec3 = doc.add_paragraph()
    p_rec3.add_run("Grid Loss Mitigation: ").bold = True
    p_rec3.add_run(f"Coordinate with the utility ({plant.grid_operator}) to minimize grid-related outages. Consider installing power quality monitoring equipment to document and quantify grid-related losses. Explore options for grid stability improvements at the point of connection.")

    p_rec4 = doc.add_paragraph()
    p_rec4.add_run("Vegetation Management: ").bold = True
    p_rec4.add_run("Ensure proper vegetation management around the plant perimeter and between module rows to prevent shading losses. Schedule regular vegetation clearing, especially during monsoon seasons when growth rates are highest.")

    # 8.2 Monitoring Recommendations
    doc.add_heading("8.2 Monitoring Recommendations", level=2)

    p_mon1 = doc.add_paragraph()
    p_mon1.add_run("String-Level Monitoring: ").bold = True
    p_mon1.add_run("Install string-level monitoring to identify underperforming strings and modules. This will enable targeted maintenance and early detection of module-level issues.")

    p_mon2 = doc.add_paragraph()
    p_mon2.add_run("Weather Station Calibration: ").bold = True
    p_mon2.add_run("Ensure the plant weather station and pyranometer are regularly calibrated (annually at minimum) to maintain data accuracy for performance analysis.")

    p_mon3 = doc.add_paragraph()
    p_mon3.add_run("Data Quality Improvement: ").bold = True
    p_mon3.add_run("Implement automated data quality checks to identify and flag data anomalies. Ensure consistent data recording across all inverter blocks.")

    # 8.3 Long-Term Recommendations
    doc.add_heading("8.3 Long-Term Recommendations", level=2)

    p_lt1 = doc.add_paragraph()
    p_lt1.add_run("Degradation Monitoring: ").bold = True
    p_lt1.add_run("Continue tracking the degradation rate annually. The current rate should be monitored to ensure it does not accelerate. Consider periodic I-V curve testing to validate module-level degradation.")

    p_lt2 = doc.add_paragraph()
    p_lt2.add_run("Performance Benchmarking: ").bold = True
    region = "Northern Province" if plant.name.lower() == "vydexa" else plant.country.title()
    p_lt2.add_run(f"Compare plant performance against similar installations in the {region} to identify opportunities for improvement and validate that performance is within expected bounds.")

    p_end = doc.add_paragraph("\n\nEnd of Report")
    p_end.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_end.runs[0].font.italic = True

    doc.save(file_path)


# ═══════════════════════════════════════════════════════════════════════
# PDF Document Generation
# ═══════════════════════════════════════════════════════════════════════
def generate_pdf_report(
    plant: Plant,
    lifetime: any,
    kpis: any,
    monthly_kpis: list,
    sorted_study_years: list[str],
    study_year_records: dict,
    monthly_kpis_by_year: dict,
    inverter_yearly_data: dict,
    block_yearly_data: dict,
    sorted_inverters: list[Inverter],
    loss: any,
    monthly_losses: list,
    deg: any,
    alerts: list[Alert],
    recommendations: list[Recommendation],
    charts: dict[str, str],
    file_path: str,
    daily_records: list,
) -> None:
    """Create the professional PDF report using ReportLab Flowables matching Example report outlines."""
    doc = SimpleDocTemplate(
        file_path,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()

    # Custom styles matching DOCX
    style_cover_title = ParagraphStyle(
        name="CoverTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=28,
        leading=34,
        textColor=colors.HexColor("#1A5276"), # Hex #1A5276
        spaceAfter=12,
        alignment=1,  # Center
    )
    style_cover_subtitle = ParagraphStyle(
        name="CoverSubTitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#2C3E50"), # Hex #2C3E50
        alignment=1,
        spaceAfter=80,
    )
    style_cover_sp_label = ParagraphStyle(
        name="CoverSpLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#2C3E50"),
        alignment=1,
        spaceAfter=6,
    )
    style_cover_sp_val = ParagraphStyle(
        name="CoverSpVal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#34495E"), # Hex #34495E
        alignment=1,
        spaceAfter=80,
    )
    style_cover_meta = ParagraphStyle(
        name="CoverMeta",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#34495E"),
        alignment=1,
        spaceAfter=6,
    )
    style_h1 = ParagraphStyle(
        name="Header1",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1A365D"),
        spaceBefore=18,
        spaceAfter=12,
        keepWithNext=True,
    )
    style_h2 = ParagraphStyle(
        name="Header2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#2D3748"),
        spaceBefore=14,
        spaceAfter=8,
        keepWithNext=True,
    )
    style_h3 = ParagraphStyle(
        name="Header3",
        parent=styles["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#2D3748"),
        spaceBefore=10,
        spaceAfter=6,
        keepWithNext=True,
    )
    style_body = ParagraphStyle(
        name="BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=14.5,
        textColor=colors.HexColor("#333333"),
        spaceAfter=12,
    )
    style_bullet = ParagraphStyle(
        name="BulletPoint",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=14.5,
        textColor=colors.HexColor("#333333"),
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=6,
    )
    style_caption = ParagraphStyle(
        name="ReportCaption",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#718096"),
        alignment=1, # Center
        spaceBefore=6,
        spaceAfter=24,
    )
    style_table_caption = ParagraphStyle(
        name="TableCaption",
        parent=styles["Normal"],
        fontName="Helvetica-BoldOblique",
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#1A365D"),
        spaceBefore=12,
        spaceAfter=6,
    )
    style_table_note = ParagraphStyle(
        name="TableNote",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#718096"),
        spaceAfter=6,
    )
    style_th = ParagraphStyle(
        name="TableHeaderBase",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=11,
        textColor=colors.white,
    )
    style_td = ParagraphStyle(
        name="TableCellBase",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#333333"),
    )
    style_td_left = ParagraphStyle(
        name="TableCellLeft",
        parent=style_td,
        alignment=0,
    )
    style_td_right = ParagraphStyle(
        name="TableCellRight",
        parent=style_td,
        alignment=2,
    )
    style_th_left = ParagraphStyle(
        name="TableHeaderLeft",
        parent=style_th,
        alignment=0,
    )
    style_th_right = ParagraphStyle(
        name="TableHeaderRight",
        parent=style_th,
        alignment=2,
    )

    story = []

    # Helper: Wrap values in Paragraph flowable for proper cell alignment
    def cell_p(text: str, is_header: bool = False, align: str = "LEFT", is_bold: bool = False) -> Paragraph:
        if is_header:
            p_style = style_th_left if align == "LEFT" else style_th_right
        else:
            p_style = style_td_left if align == "LEFT" else style_td_right
            
        t = text
        if is_bold:
            t = f"<b>{t}</b>"
        return Paragraph(t, p_style)

    # ───────────────────────────────────────────────────────────────────────
    # Cover Page (Headerless layout matching docx report)
    # ───────────────────────────────────────────────────────────────────────
    pdf_logo_path = get_company_logo_path(plant.id)
    if pdf_logo_path and os.path.exists(pdf_logo_path):
        story.append(Spacer(1, 0.3 * inch))
        try:
            story.append(Image(pdf_logo_path, width=2.0 * inch, height=0.9 * inch))
            story.append(Spacer(1, 0.2 * inch))
        except Exception:
            story.append(Spacer(1, 0.4 * inch))
    else:
        story.append(Spacer(1, 0.8 * inch))

    story.append(Paragraph(f"{plant.name.upper()} SOLAR POWER PLANT", style_cover_title))
    story.append(Paragraph("Performance and Degradation Assessment Report", style_cover_subtitle))

    
    story.append(Paragraph("Study Period", style_cover_sp_label))
    
    study_periods_list = []
    for sy in sorted_study_years:
        start, end = sy.split("-")
        study_periods_list.append(f"May {start} – April {end}")
        
    study_periods_str = "<br/>".join(study_periods_list)
    story.append(Paragraph(study_periods_str, style_cover_sp_val))
    
    story.append(Spacer(1, 0.4 * inch))
    
    country_name = "Sri Lanka" if plant.country.lower() in ("srilanka", "sri lanka") else plant.country.title()
    prepared_by = "WindForce (Pvt) Ltd" if plant.name.lower() == "vydexa" else "SoliZer Intelligence Platform"
    
    meta_items = [
        ("Plant Capacity: ", f"DC: {plant.installed_dc_capacity_mw} MW | AC: {int(plant.installed_ac_capacity_mw) if plant.installed_ac_capacity_mw.is_integer() else plant.installed_ac_capacity_mw} MW"),
        ("Location: ", f"{plant.location.title()}, Northern Province, {country_name}" if plant.location.lower() == "vavuniya" else f"{plant.location.title()}, {country_name}"),
        ("Commissioned: ", plant.commission_date.strftime("%B %Y")),
        ("Prepared by: ", prepared_by),
        ("Date: ", datetime.now().strftime("%B %Y"))
    ]

    for label, val in meta_items:
        meta_html = f"<b>{label}</b>{val}"
        story.append(Paragraph(meta_html, style_cover_meta))
        
    story.append(PageBreak())

    # ───────────────────────────────────────────────────────────────────────
    # Section 1. Plant-Level Performance Analysis
    # ───────────────────────────────────────────────────────────────────────
    story.append(Paragraph("1. Plant-Level Performance Analysis", style_h1))
    story.append(
        Paragraph(
            f"This section presents the overall performance metrics of the {plant.name.title()} Solar Power Plant across "
            f"the three study periods ({', '.join(sorted_study_years)}). Key performance indicators "
            f"including Performance Ratio (PR), Capacity Utilization Factor (CUF), Specific Yield, and Plant Availability "
            f"are evaluated.",
            style_body,
        )
    )

    story.append(Paragraph("Annual Performance Summary", style_h2))
    story.append(Paragraph(f"Table 1.1: Annual Performance Summary of {plant.name.title()} Solar Power Plant", style_table_caption))
    story.append(
        Paragraph(
            "Note: Total Inverter Generation = Generation + Curtailment. <br/>"
            "Total Possible Generation = Generation + Curtailment + Grid Loss + Machine Loss",
            style_table_note
        )
    )
    
    header_row = [
        cell_p("Parameter", is_header=True, align="LEFT"),
        cell_p("Unit", is_header=True, align="LEFT")
    ]
    for label in sorted_study_years:
        header_row.append(cell_p(label, is_header=True, align="RIGHT"))
    header_row.append(cell_p("Avg", is_header=True, align="RIGHT"))
        
    table1_data = [header_row]
    
    years_data = []
    for label in sorted_study_years:
        recs = study_year_records[label]
        y_lt = aggregate_to_lifetime(recs)
        y_kp = compute_lifetime_kpis(plant, y_lt)
        y_avail = calculate_availability(y_lt.total_generation, y_lt.total_possible_generation)
        y_irr = sum(d.irradiation for d in recs) / 100.0
        years_data.append({
            "gen": y_lt.total_generation / 1000.0,
            "possible_gen": y_lt.total_possible_generation / 1000.0,
            "irrad": y_irr,
            "pr": y_kp.performance_ratio,
            "cuf": y_kp.cuf,
            "sy": y_kp.specific_yield,
            "avail": y_avail
        })
        
    avg_gen = sum(yd["gen"] for yd in years_data) / len(years_data)
    avg_poss = sum(yd["possible_gen"] for yd in years_data) / len(years_data)
    avg_irr = sum(yd["irrad"] for yd in years_data) / len(years_data)
    avg_pr = kpis.performance_ratio
    avg_cuf = kpis.cuf
    avg_sy = sum(yd["sy"] for yd in years_data) / len(years_data)
    avg_avail = sum(yd["avail"] for yd in years_data) / len(years_data)

    rows_data_t1 = [
        ("Total Generation", "MWh", [f"{yd['gen']:,.1f}" for yd in years_data] + [f"{avg_gen:,.1f}"]),
        ("Total Possible Generation", "MWh", [f"{yd['possible_gen']:,.1f}" for yd in years_data] + [f"{avg_poss:,.1f}"]),
        ("Total Irradiation", "kWh/m²", [f"{yd['irrad']:,.1f}" for yd in years_data] + [f"{avg_irr:,.1f}"]),
        ("Performance Ratio", "%", [f"{yd['pr']:.2f}%" for yd in years_data] + [f"{avg_pr:.2f}%"]),
        ("CUF", "%", [f"{yd['cuf']:.2f}%" for yd in years_data] + [f"{avg_cuf:.2f}%"]),
        ("Specific Yield", "kWh/kWp", [f"{yd['sy']:.1f}" for yd in years_data] + [f"{avg_sy:.1f}"]),
        ("Plant Availability", "%", [f"{yd['avail']:.2f}%" for yd in years_data] + [f"{avg_avail:.2f}%"]),
    ]
    
    for row_idx, (param, unit, vals) in enumerate(rows_data_t1):
        row_cells = [cell_p(param, align="LEFT"), cell_p(unit, align="LEFT")]
        for val_idx, val in enumerate(vals):
            is_avg = (val_idx == len(vals) - 1)
            formatted_val = val
            if row_idx == 3:  # PR
                if is_avg and formatted_val.endswith("%"):
                    formatted_val = formatted_val[:-1]
                elif not is_avg and not formatted_val.endswith("%"):
                    formatted_val += "%"
            elif row_idx == 4:  # CUF
                if not formatted_val.endswith("%"):
                    formatted_val += "%"
            elif row_idx == 6:  # Plant Availability
                if formatted_val.endswith("%"):
                    formatted_val = formatted_val[:-1]
            
            row_cells.append(cell_p(formatted_val, align="RIGHT"))
        table1_data.append(row_cells)
        
    col_widths_t1 = [2.2 * inch, 0.8 * inch] + [0.8 * inch] * (len(sorted_study_years) + 1)
    t1 = Table(table1_data, colWidths=col_widths_t1)
    t1.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1A365D")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F7FAFC"), colors.white]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ]
        )
    )
    story.append(t1)
    story.append(Spacer(1, 15))

    story.append(Paragraph("1.2 Monthly Performance Ratio", style_h2))
    story.append(
        Paragraph(
            "The Performance Ratio (PR) is a key indicator of plant efficiency, representing the ratio of actual energy output to the theoretically possible output based on the received irradiation and installed DC capacity. A higher PR indicates better plant performance.",
            style_body,
        )
    )
    story.append(Paragraph("<b>PR Calculation:</b>", style_body))
    story.append(
        Paragraph(
            "Performance Ratio (%) = Generation (kWh)/(Irradiance(W/sqm) x Total Panel Area (sqm) x Module Efficiency x Running Hours per day) x 100%",
            style_body,
        )
    )
    story.append(Spacer(1, 10))
    story.append(Image(charts["pr"], width=6.0 * inch, height=3.0 * inch))
    story.append(Paragraph("Figure 1.1: Monthly Average Performance Ratio Comparison", style_caption))
    story.append(PageBreak())

    story.append(Paragraph("1.3 Specific Yield", style_h2))
    story.append(
        Paragraph(
            "Specific Yield represents the energy generated per unit of installed DC capacity (kWh/kWp). It is a standardized metric that allows comparison across plants of different sizes.",
            style_body,
        )
    )
    story.append(Spacer(1, 10))
    story.append(Image(charts["specific_yield"], width=6.0 * inch, height=3.0 * inch))
    story.append(Paragraph("Figure 1.3: Monthly Specific Yield Comparison", style_caption))
    story.append(PageBreak())

    # ───────────────────────────────────────────────────────────────────────
    # Section 2. Inverter-Level Performance Analysis
    # ───────────────────────────────────────────────────────────────────────
    story.append(Paragraph("2. Inverter-Level Performance Analysis", style_h1))
    story.append(
        Paragraph(
            f"The {plant.name.title()} plant consists of {plant.number_of_blocks} inverter blocks, "
            f"each containing {plant.number_of_inverters // plant.number_of_blocks} inverters, "
            f"totaling {plant.number_of_inverters} inverters. This section examines individual inverter performance to identify underperforming or degraded units.",
            style_body,
        )
    )

    story.append(Paragraph("2.1 Inverter Annual Generation", style_h2))
    story.append(Paragraph("Note: Inverter Generation = Generation + Curtailment", style_table_note))
    story.append(Paragraph("Table 2.1: Inverter Annual Generation Summary", style_table_caption))
    
    table2_headers = [cell_p("Inverter", is_header=True, align="LEFT")]
    for sy in sorted_study_years:
        table2_headers.append(cell_p(f"{sy} (MWh)", is_header=True, align="RIGHT"))
    table2_headers.append(cell_p("Change (%)", is_header=True, align="RIGHT"))
    
    table2_data = [table2_headers]
    for idx, inv in enumerate(sorted_inverters):
        row_cells = [cell_p(format_inverter_name(inv.name), align="LEFT")]
        y_vals = []
        for sy in sorted_study_years:
            val_mwh = inverter_yearly_data[inv.id][sy]["generation"] / 1000.0
            y_vals.append(val_mwh)
            row_cells.append(cell_p(f"{val_mwh:,.1f}", align="RIGHT"))
        chg = 0.0
        if len(y_vals) > 1 and y_vals[0] > 0:
            chg = (y_vals[-1] - y_vals[0]) / y_vals[0] * 100.0
        row_cells.append(cell_p(f"{chg:+.2f}%", align="RIGHT"))
        table2_data.append(row_cells)

    col_widths_t2 = [2.0 * inch] + [1.0 * inch] * (len(sorted_study_years) + 1)
    t2 = Table(table2_data, colWidths=col_widths_t2)
    t2.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1A365D")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F7FAFC"), colors.white]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ]
        )
    )
    story.append(t2)
    story.append(Spacer(1, 15))
    story.append(Image(charts["inverters_gen"], width=6.0 * inch, height=3.0 * inch))
    story.append(Paragraph("Figure 2.1: Inverter-Level Annual Generation Comparison", style_caption))
    story.append(PageBreak())

    # Inverter PR Table
    story.append(Paragraph("2.2 Inverter Performance Ratio", style_h2))
    story.append(
        Paragraph(
            "The following chart and table present the annual Performance Ratio for each inverter. Variations across inverters may indicate issues such as soiling, shading, or equipment degradation.",
            style_body,
        )
    )
    story.append(Paragraph("Table 2.2: Inverter Annual Performance Ratio", style_table_caption))
    
    table3_headers = [cell_p("Inverter", is_header=True, align="LEFT")]
    for sy in sorted_study_years:
        table3_headers.append(cell_p(f"{sy} (%)", is_header=True, align="RIGHT"))
    table3_headers.append(cell_p("Change", is_header=True, align="RIGHT"))
    
    table3_data = [table3_headers]
    eff_frac = plant.module_efficiency / 100.0
    inv_area = plant.total_panel_area_sqm / max(plant.number_of_inverters, 1)
    for inv in sorted_inverters:
        row_cells = [cell_p(format_inverter_name(inv.name), align="LEFT")]
        y_prs = []
        for sy in sorted_study_years:
            gen = inverter_yearly_data[inv.id][sy]["generation"]
            irrad = inverter_yearly_data[inv.id][sy]["irradiation"]
            pr_val = calculate_pr(gen, irrad, inv_area, eff_frac, plant.daily_running_hours)
            y_prs.append(pr_val)
            # No % symbol inside cell
            row_cells.append(cell_p(f"{pr_val:.2f}", align="RIGHT"))
        chg = 0.0
        if len(y_prs) > 1:
            chg = y_prs[-1] - y_prs[0]
        # Change column has %
        row_cells.append(cell_p(f"{chg:+.2f}%", align="RIGHT"))
        table3_data.append(row_cells)

    t3 = Table(table3_data, colWidths=col_widths_t2)
    t3.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1A365D")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F7FAFC"), colors.white]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ]
        )
    )
    story.append(t3)
    story.append(Spacer(1, 15))
    story.append(Image(charts["inverters_pr"], width=6.0 * inch, height=3.0 * inch))
    story.append(Paragraph("Figure 2.2: Inverter-Level Annual Performance Ratio", style_caption))
    story.append(PageBreak())

    # Section 2.3 Block-Level Comparison
    story.append(Paragraph("2.3 Block-Level Comparison", style_h2))
    story.append(
        Paragraph(
            f"The following chart compares the annual generation at the block level. Each block consists of multiple inverters, "
            f"and contributes approximately {100 // plant.number_of_blocks}% of the total plant capacity.",
            style_body
        )
    )
    story.append(Spacer(1, 10))
    story.append(Image(charts["blocks_gen"], width=6.0 * inch, height=3.0 * inch))
    story.append(Paragraph("Figure 2.3: Block-Level Annual Generation Comparison", style_caption))
    story.append(PageBreak())

    # ───────────────────────────────────────────────────────────────────────
    # Section 3: Irradiation Analysis
    # ───────────────────────────────────────────────────────────────────────
    story.append(Paragraph("3. Irradiation Analysis", style_h1))
    story.append(
        Paragraph(
            f"Irradiation is the primary driver of solar energy generation. This section analyzes the solar resource received "
            f"at the {plant.name.title()} plant site over the study periods. The irradiation data is measured in Wh/m² (daily) "
            f"and presented as kWh/m² for monthly and annual aggregations.",
            style_body
        )
    )
    story.append(Paragraph("3.1 Annual Irradiation Summary", style_h2))
    story.append(Paragraph("Table 3.1: Annual Irradiation Summary", style_table_caption))
    
    table4_data = [
        [
            cell_p("Year", is_header=True, align="LEFT"),
            cell_p("Total Irradiation (kWh/m²)", is_header=True, align="RIGHT"),
            cell_p("Avg Daily (Wh/m²)", is_header=True, align="RIGHT"),
            cell_p("Peak Month", is_header=True, align="LEFT"),
            cell_p("Lowest Month", is_header=True, align="LEFT"),
        ]
    ]
    for label in sorted_study_years:
        recs = study_year_records[label]
        num_days = len(recs)
        total_irr = sum(d.irradiation for d in recs) / 100.0
        avg_daily = sum(d.irradiation for d in recs) / max(num_days, 1)
        m_recs = aggregate_to_monthly(recs)
        max_m = max(m_recs, key=lambda mr: mr.irradiation)
        min_m = min(m_recs, key=lambda mr: mr.irradiation)
        peak_month = f"{_MONTH_NAMES[max_m.month]} {max_m.year}"
        lowest_month = f"{_MONTH_NAMES[min_m.month]} {min_m.year}"
        table4_data.append(
            [
                cell_p(label, align="LEFT"),
                cell_p(f"{total_irr:,.1f}", align="RIGHT"),
                cell_p(f"{avg_daily:.1f}", align="RIGHT"),
                cell_p(peak_month, align="LEFT"),
                cell_p(lowest_month, align="LEFT"),
            ]
        )
    col_widths_t4 = [1.2 * inch, 1.8 * inch, 1.2 * inch, 1.1 * inch, 1.1 * inch]
    t4 = Table(table4_data, colWidths=col_widths_t4)
    t4.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1A365D")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F7FAFC"), colors.white]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ]
        )
    )
    story.append(t4)
    story.append(Spacer(1, 15))

    story.append(Paragraph("3.2 Monthly Irradiation Comparison", style_h2))
    story.append(
        Paragraph(
            f"The monthly irradiation pattern shows typical seasonal variation for the region of {plant.location.title()}. "
            f"Higher irradiation is generally observed during dry season months, while lower values occur during monsoon periods.",
            style_body
        )
    )
    story.append(Spacer(1, 10))
    story.append(Image(charts["irradiation"], width=6.0 * inch, height=3.0 * inch))
    story.append(Paragraph("Figure 3.1: Monthly Irradiation Comparison", style_caption))
    story.append(PageBreak())

    # ───────────────────────────────────────────────────────────────────────
    # Section 4: Generation Analysis
    # ───────────────────────────────────────────────────────────────────────
    story.append(Paragraph("4. Generation Analysis", style_h1))
    story.append(
        Paragraph(
            f"This section provides a detailed analysis of the energy generation at the {plant.name.title()} Solar Power Plant over "
            f"the study period, including annual totals, monthly patterns, and trends. All generation values in this section represent "
            f"Total Generation (Generation + Curtailment), which reflects the actual energy produced by the plant before any curtailment losses.",
            style_body,
        )
    )
    story.append(Paragraph("4.1 Annual Generation Summary", style_h2))
    story.append(Paragraph("Note: Total Generation = Generation + Curtailments", style_table_note))
    story.append(Spacer(1, 10))
    story.append(Image(charts["annual_generation"], width=6.0 * inch, height=3.0 * inch))
    story.append(Paragraph("Figure 4.1: Annual Total Generation", style_caption))
    story.append(PageBreak())

    story.append(Paragraph("4.2 Monthly Generation Details", style_h2))

    # Multiple monthly detail tables for each study year
    col_widths_t5 = [1.2 * inch, 1.1 * inch, 1.2 * inch, 0.8 * inch, 0.8 * inch, 1.2 * inch]
    table_num = 1
    for sy in sorted_study_years:
        story.append(Paragraph(sy, style_h3))
        story.append(Paragraph(f"Table 4.{table_num}: Monthly Generation Details - {sy}", style_table_caption))
        
        table5_data = [
            [
                cell_p("Month", is_header=True, align="LEFT"),
                cell_p("Generation (MWh)", is_header=True, align="RIGHT"),
                cell_p("Irradiation (kWh/m²)", is_header=True, align="RIGHT"),
                cell_p("PR (%)", is_header=True, align="RIGHT"),
                cell_p("CUF (%)", is_header=True, align="RIGHT"),
                cell_p("Spec. Yield (kWh/kWp)", is_header=True, align="RIGHT"),
            ]
        ]
        months_nums = [5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3, 4]
        sy_recs = study_year_records[sy]
        m_records = aggregate_to_monthly(sy_recs)
        m_kpis = compute_monthly_kpis(plant, m_records)
        kpi_map = {mk.month: mk for mk in m_kpis}
        
        total_gen = 0.0
        total_irr = 0.0
        total_days = 0

        for m_num in months_nums:
            mk = kpi_map.get(m_num)
            if mk:
                mr = next(mr for mr in m_records if mr.month == m_num)
                total_gen += mr.total_generation
                total_irr += mr.irradiation
                total_days += mr.days
                
                table5_data.append(
                    [
                        cell_p(mk.label, align="LEFT"),
                        cell_p(f"{mk.generation_mwh:,.1f}", align="RIGHT"),
                        cell_p(f"{mk.irradiation_kwh_m2:,.1f}", align="RIGHT"),
                        # Omit % symbol
                        cell_p(f"{mk.pr:.2f}", align="RIGHT"),
                        cell_p(f"{mk.cuf:.2f}", align="RIGHT"),
                        cell_p(f"{mk.specific_yield:.1f}", align="RIGHT"),
                    ]
                )
            else:
                label_name = f"{_MONTH_NAMES[m_num]} {sy.split('-')[0] if m_num >= 5 else sy.split('-')[1]}"
                table5_data.append(
                    [
                        cell_p(label_name, align="LEFT"),
                        cell_p("0.0", align="RIGHT"),
                        cell_p("0.0", align="RIGHT"),
                        cell_p("0.00", align="RIGHT"),
                        cell_p("0.00", align="RIGHT"),
                        cell_p("0.0", align="RIGHT"),
                    ]
                )
        
        avg_pr_val = calculate_pr(total_gen, total_irr, plant.total_panel_area_sqm, eff_frac, plant.daily_running_hours)
        avg_cuf_val = calculate_cuf(total_gen, plant.installed_ac_capacity_mw, total_days * 24.0)
        tot_sy_val = calculate_specific_yield(total_gen, plant.installed_dc_capacity_mw)

        table5_data.append(
            [
                cell_p("Total/Avg", align="LEFT", is_bold=True),
                cell_p(f"{total_gen/1000.0:,.1f}", align="RIGHT", is_bold=True),
                cell_p(f"{total_irr/100.0:,.1f}", align="RIGHT", is_bold=True),
                cell_p(f"{avg_pr_val:.2f}", align="RIGHT", is_bold=True),
                cell_p(f"{avg_cuf_val:.2f}", align="RIGHT", is_bold=True),
                cell_p(f"{tot_sy_val:.1f}", align="RIGHT", is_bold=True),
            ]
        )
        
        t5_sy = Table(table5_data, colWidths=col_widths_t5)
        t5_sy.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1A365D")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.HexColor("#F7FAFC"), colors.white]),
                    ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#EDF2F7")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ]
            )
        )
        story.append(t5_sy)
        story.append(Spacer(1, 15))
        table_num += 1

    story.append(Paragraph("4.3 Monthly Generation Comparison", style_h2))
    story.append(Image(charts["generation"], width=6.0 * inch, height=3.0 * inch))
    story.append(Paragraph("Figure 4.2: Monthly Total Generation Comparison Across Years", style_caption))
    story.append(PageBreak())

    # ───────────────────────────────────────────────────────────────────────
    # Section 5: PR Assessment & Degradation
    # ───────────────────────────────────────────────────────────────────────
    story.append(Paragraph("5. Performance Ratio Assessment", style_h1))
    story.append(
        Paragraph(
            f"The Performance Ratio (PR) is a key indicator used to evaluate the operational performance of a solar photovoltaic power plant. "
            f"It measures how effectively the plant converts available solar irradiation into electrical energy after accounting for system losses. "
            f"The {plant.name.title()} Solar Power Plant was evaluated using monthly PR values over the study period. Trend analysis of PR was conducted to assess changes in overall plant performance and identify long-term performance patterns.",
            style_body,
        )
    )
    story.append(Paragraph("5.1 Plant-Level Performance Ratio Trend", style_h2))
    story.append(
        Paragraph(
            f"The Performance Ratio trend over the three-year study period was analysed to assess the overall performance evolution of the {plant.name.title()} Solar Power Plant. A linear regression was applied to the monthly PR values to identify the long-term performance trend.",
            style_body,
        )
    )
    story.append(Spacer(1, 10))
    story.append(Image(charts["trend"], width=6.0 * inch, height=3.0 * inch))
    story.append(Paragraph("Figure 5.1: Monthly Average Performance Ratio Trend", style_caption))
    
    story.append(Paragraph(f"<b>Observed PR Trend Rate: -{deg.annual_degradation_rate}% per year</b>", style_body))
    story.append(
        Paragraph(
            f"Based on the linear regression analysis of monthly Performance Ratio values, the plant exhibited an overall PR decline "
            f"of approximately {deg.annual_degradation_rate}% per year during the study period. While this trend indicates a reduction "
            f"in overall system performance, it may be influenced by multiple factors including equipment ageing, inverter performance variations, "
            f"operational losses, maintenance activities, and grid-related events. Therefore, the observed PR trend represents the overall "
            f"performance change of the plant rather than photovoltaic module degradation alone.",
            style_body,
        )
    )
    story.append(PageBreak())

    # ───────────────────────────────────────────────────────────────────────
    # Section 6: Loss Analysis
    # ───────────────────────────────────────────────────────────────────────
    story.append(Paragraph("6. Loss Analysis", style_h1))
    story.append(
        Paragraph(
            f"This section quantifies the energy losses at the {plant.name.title()} plant. Energy production at the {plant.name.title()} Solar Power Plant "
            f"is limited by three primary operational and technical losses:",
            style_body,
        )
    )
    
    # Bullet points
    story.append(Paragraph("<b>Machine Losses:</b> Energy lost due to internal equipment issues, such as failures or routine maintenance.", style_bullet))
    story.append(Paragraph("<b>Grid Failure Losses:</b> Un-exported power caused by utility grid outages.", style_bullet))
    story.append(Paragraph("<b>Curtailment Losses:</b> Intentional generation limits imposed by the Electricity Board.", style_bullet))
    
    story.append(
        Paragraph(
            "Combined, grid failures and curtailment make up the plant's total Grid Loss. Tracking these metrics is essential for evaluating and improving overall plant performance.",
            style_body,
        )
    )
    
    story.append(Paragraph("6.1 Annual Loss Summary", style_h2))
    story.append(Paragraph("Table 6.1: Annual Loss Summary", style_table_caption))
    
    table6_data = [
        [
            cell_p("Year", is_header=True, align="LEFT"),
            cell_p("Grid Loss (MWh)", is_header=True, align="RIGHT"),
            cell_p("Machine Loss (MWh)", is_header=True, align="RIGHT"),
            cell_p("Total Loss (MWh)", is_header=True, align="RIGHT"),
            cell_p("Loss %", is_header=True, align="RIGHT"),
            cell_p("Generation (MWh)", is_header=True, align="RIGHT"),
        ],
    ]
    for label in sorted_study_years:
        recs = study_year_records[label]
        y_lt = aggregate_to_lifetime(recs)
        y_loss_sum = (y_lt.grid_loss + y_lt.machine_loss) / 1000.0
        y_loss_pct = ((y_lt.grid_loss + y_lt.machine_loss) / max(y_lt.total_possible_generation, 1.0)) * 100.0
        table6_data.append(
            [
                cell_p(label, align="LEFT"),
                cell_p(f"{y_lt.grid_loss/1000.0:,.1f}", align="RIGHT"),
                cell_p(f"{y_lt.machine_loss/1000.0:,.1f}", align="RIGHT"),
                cell_p(f"{y_loss_sum:,.1f}", align="RIGHT"),
                cell_p(f"{y_loss_pct:.2f}%", align="RIGHT"),
                cell_p(f"{y_lt.total_generation/1000.0:,.1f}", align="RIGHT"),
            ]
        )
    col_widths_t6 = [1.2 * inch, 1.1 * inch, 1.2 * inch, 1.0 * inch, 0.8 * inch, 1.0 * inch]
    t6 = Table(table6_data, colWidths=col_widths_t6)
    t6.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1A365D")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F7FAFC"), colors.white]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ]
        )
    )
    story.append(t6)
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("6.2 Monthly Loss Breakdown", style_h2))
    story.append(
        Paragraph(
            "The stacked bar charts below illustrate the monthly distribution of losses by type for each year.",
            style_body,
        )
    )
    story.append(Spacer(1, 10))
    
    fig_idx = 1
    for sy in sorted_study_years:
        story.append(Image(charts[f"losses_{sy}"], width=6.0 * inch, height=3.0 * inch))
        story.append(Paragraph(f"Figure 6.{fig_idx}: Monthly Loss Breakdown - {sy}", style_caption))
        fig_idx += 1

    story.append(Paragraph("6.3 Inverter-Level Loss Comparison", style_h2))
    story.append(
        Paragraph(
            "The chart below compares total losses across all inverters to identify units with higher-than-average losses.",
            style_body,
        )
    )
    story.append(Spacer(1, 10))
    story.append(Image(charts["losses_inv"], width=6.0 * inch, height=3.0 * inch))
    story.append(Paragraph("Figure 6.3: Inverter-Level Total Losses", style_caption))
    story.append(PageBreak())

    # Calculate findings variables
    y_first = sorted_study_years[0]
    y_last = sorted_study_years[-1]
    gen_first = sum(d.total_generation for d in study_year_records[y_first]) / 1000.0
    gen_last = sum(d.total_generation for d in study_year_records[y_last]) / 1000.0
    diff_pct = (gen_last - gen_first) / gen_first * 100.0 if gen_first > 0 else 0.0
    direction = "decreased" if diff_pct < 0 else "increased"

    eff_frac = plant.module_efficiency / 100.0
    inv_area = plant.total_panel_area_sqm / max(plant.number_of_inverters, 1)

    best_inv_name = ""
    best_inv_pr = -1.0
    worst_inv_name = ""
    worst_inv_pr = 999.0
    for inv in sorted_inverters:
        gen = inverter_yearly_data[inv.id][y_last]["generation"]
        irrad = inverter_yearly_data[inv.id][y_last]["irradiation"]
        pr_val = calculate_pr(gen, irrad, inv_area, eff_frac, plant.daily_running_hours)
        if pr_val > best_inv_pr:
            best_inv_pr = pr_val
            best_inv_name = inv.name
        if pr_val < worst_inv_pr:
            worst_inv_pr = pr_val
            worst_inv_name = inv.name

    dominant = "Grid Losses" if lifetime.grid_loss > lifetime.machine_loss else "Machine Losses"
    loss_pct = ((lifetime.grid_loss + lifetime.machine_loss) / max(lifetime.total_possible_generation, 1.0)) * 100.0

    annual_irrads = []
    for label in sorted_study_years:
        recs = study_year_records[label]
        annual_irrads.append(sum(d.irradiation for d in recs) / 100.0)

    # ───────────────────────────────────────────────────────────────────────
    # Section 7: Findings
    # ───────────────────────────────────────────────────────────────────────
    story.append(Paragraph("7. Findings", style_h1))
    
    story.append(Paragraph("7.1 Key Performance Findings", style_h2))
    story.append(Paragraph(f"• The plant generated a total of {lifetime.total_generation/1000.0:,.1f} MWh over the {len(sorted_study_years)}-year study period.", style_bullet))
    story.append(Paragraph(f"• Annual generation {direction} by {abs(diff_pct):.1f}% from {y_first} to {y_last} ({gen_first:,.1f} MWh to {gen_last:,.1f} MWh).", style_bullet))
    story.append(Paragraph(f"• The average annual Performance Ratio across the study period was {kpis.performance_ratio:.2f}%.", style_bullet))

    story.append(Spacer(1, 10))
    story.append(Paragraph("7.2 Inverter Performance Findings", style_h2))
    story.append(Paragraph(f"• Best performing inverter in {y_last}: {format_inverter_name(best_inv_name)} with PR of {best_inv_pr:.2f}%.", style_bullet))
    story.append(Paragraph(f"• Lowest performing inverter in {y_last}: {format_inverter_name(worst_inv_name)} with PR of {worst_inv_pr:.2f}%.", style_bullet))
    story.append(Paragraph(f"• The PR variation among inverters is {best_inv_pr - worst_inv_pr:.2f} percentage points, indicating notable variation in performance across inverters.", style_bullet))

    story.append(Spacer(1, 10))
    story.append(Paragraph("7.3 Loss Findings", style_h2))
    story.append(Paragraph(f"• Total Grid Losses over the study period: {lifetime.grid_loss/1000.0:,.1f} MWh.", style_bullet))
    story.append(Paragraph(f"• Total Machine Losses over the study period: {lifetime.machine_loss/1000.0:,.1f} MWh.", style_bullet))
    story.append(Paragraph(f"• {dominant} represent the dominant source of energy loss at the plant.", style_bullet))
    story.append(Paragraph(f"• Combined losses represent approximately {loss_pct:.2f}% of total possible generation.", style_bullet))

    story.append(Spacer(1, 10))
    story.append(Paragraph("7.4 Irradiation Findings", style_h2))
    story.append(Paragraph(f"• Annual irradiation ranged from {min(annual_irrads):,.1f} to {max(annual_irrads):,.1f} kWh/m².", style_bullet))

    story.append(PageBreak())

    # ───────────────────────────────────────────────────────────────────────
    # Section 8: Recommendations
    # ───────────────────────────────────────────────────────────────────────
    story.append(Paragraph("8. Recommendations", style_h1))
    
    story.append(Paragraph("8.1 Performance Improvement Recommendations", style_h2))
    story.append(Paragraph(f"<b>Module Cleaning Program:</b> Implement a regular cleaning schedule for all PV modules, particularly during dry and dusty months. Soiling can significantly reduce power output, especially in the dry zone of {plant.location.title()}. A monthly or bi-weekly cleaning schedule is recommended.", style_body))
    story.append(Paragraph(f"<b>Inverter Maintenance:</b> Focus maintenance attention on underperforming inverters, particularly {format_inverter_name(worst_inv_name)}. Conduct detailed inspection of DC input connections, string performance. Regular preventive maintenance should be scheduled quarterly.", style_body))
    story.append(Paragraph(f"<b>Grid Loss Mitigation:</b> Coordinate with the utility ({plant.grid_operator}) to minimize grid-related outages. Consider installing power quality monitoring equipment to document and quantify grid-related losses. Explore options for grid stability improvements at the point of connection.", style_body))
    story.append(Paragraph("<b>Vegetation Management:</b> Ensure proper vegetation management around the plant perimeter and between module rows to prevent shading losses. Schedule regular vegetation clearing, especially during monsoon seasons when growth rates are highest.", style_body))

    story.append(Spacer(1, 10))
    story.append(Paragraph("8.2 Monitoring Recommendations", style_h2))
    story.append(Paragraph("<b>String-Level Monitoring:</b> Install string-level monitoring to identify underperforming strings and modules. This will enable targeted maintenance and early detection of module-level issues.", style_body))
    story.append(Paragraph("<b>Weather Station Calibration:</b> Ensure the plant weather station and pyranometer are regularly calibrated (annually at minimum) to maintain data accuracy for performance analysis.", style_body))
    story.append(Paragraph("<b>Data Quality Improvement:</b> Implement automated data quality checks to identify and flag data anomalies. Ensure consistent data recording across all inverter blocks.", style_body))

    story.append(Spacer(1, 10))
    story.append(Paragraph("8.3 Long-Term Recommendations", style_h2))
    story.append(Paragraph("<b>Degradation Monitoring:</b> Continue tracking the degradation rate annually. The current rate should be monitored to ensure it does not accelerate. Consider periodic I-V curve testing to validate module-level degradation.", style_body))
    
    region = "Northern Province" if plant.name.lower() == "vydexa" else plant.country.title()
    story.append(Paragraph(f"<b>Performance Benchmarking:</b> Compare plant performance against similar installations in the {region} to identify opportunities for improvement and validate that performance is within expected bounds.", style_body))

    story.append(Spacer(1, 20))
    p_end = Paragraph("<i>End of Report</i>", style_cover_sp_val)
    story.append(p_end)

    doc.build(story)


# ═══════════════════════════════════════════════════════════════════════
# Main Report Builder orchestrator
# ═══════════════════════════════════════════════════════════════════════
def generate_and_save_report(
    db: Session,
    plant_id: int,
    report_type: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Report:
    """Generate the PDF or DOCX report for the plant, saves it to disk, and records metadata in database."""
    plant = db.query(Plant).filter(Plant.id == plant_id).first()
    if not plant:
        raise ValueError(f"Plant with id {plant_id} not found.")

    daily_records = get_daily_plant_records(db, plant_id, start_date=start_date, end_date=end_date)
    if not daily_records:
        raise ValueError("No daily records available for this plant.")

    inverters = db.query(Inverter).filter(Inverter.plant_id == plant_id).all()
    sorted_inverters = sorted(inverters, key=lambda inv: inv.name)
    inverter_ids = {inv.id: inv.name for inv in sorted_inverters}
    
    query = (
        db.query(
            DailyRecord.record_date,
            DailyRecord.inverter_id,
            DailyRecord.generation,
            DailyRecord.irradiation,
            DailyRecord.total_possible_generation,
            DailyRecord.grid_failure,
            DailyRecord.curtailment,
            DailyRecord.machine_loss,
        )
        .filter(DailyRecord.inverter_id.in_(inverter_ids.keys()))
    )
    if start_date:
        query = query.filter(DailyRecord.record_date >= start_date)
    if end_date:
        query = query.filter(DailyRecord.record_date <= end_date)
    daily_inv_records = query.order_by(DailyRecord.record_date).all()

    # Group daily records by study year
    study_year_records = defaultdict(list)
    for r in daily_records:
        start_year = r.record_date.year if r.record_date.month >= 5 else r.record_date.year - 1
        label = f"{start_year}-{start_year+1}"
        study_year_records[label].append(r)
    sorted_study_years = sorted(study_year_records.keys())

    # Run analytics engines
    lifetime = aggregate_to_lifetime(daily_records)
    kpis = compute_lifetime_kpis(plant, lifetime)
    monthly_records = aggregate_to_monthly(daily_records)
    monthly_kpis = compute_monthly_kpis(plant, monthly_records)
    loss_result = compute_loss_analysis(lifetime)
    monthly_losses = compute_monthly_losses(monthly_records)
    deg = compute_degradation(monthly_kpis, plant.expected_pr, plant.annual_degradation_rate, plant.commission_date)

    # Process monthly KPIs by year for plotting
    monthly_kpis_by_year = defaultdict(dict)
    for mk in monthly_kpis:
        start_year = mk.year if mk.month >= 5 else mk.year - 1
        sy_label = f"{start_year}-{start_year+1}"
        monthly_kpis_by_year[sy_label][mk.month] = {
            "generation_mwh": mk.generation_mwh,
            "irradiation": mk.irradiation_kwh_m2,
            "pr": mk.pr,
            "cuf": mk.cuf,
            "specific_yield": mk.specific_yield,
            "label": mk.label,
        }

    # Process inverter data per-year
    inverter_yearly_data = defaultdict(lambda: defaultdict(lambda: {
        "generation": 0.0,
        "irradiation": 0.0,
        "possible_generation": 0.0,
        "grid_failure": 0.0,
        "curtailment": 0.0,
        "machine_loss": 0.0,
        "days": 0
    }))
    
    block_yearly_data = defaultdict(lambda: defaultdict(lambda: {
        "generation": 0.0
    }))
    
    inv_by_id = {inv.id: inv for inv in sorted_inverters}
    for r in daily_inv_records:
        start_year = r.record_date.year if r.record_date.month >= 5 else r.record_date.year - 1
        sy = f"{start_year}-{start_year+1}"
        inv_id = r.inverter_id
        
        inverter_yearly_data[inv_id][sy]["generation"] += r.generation
        inverter_yearly_data[inv_id][sy]["irradiation"] += r.irradiation
        inverter_yearly_data[inv_id][sy]["possible_generation"] += r.total_possible_generation
        inverter_yearly_data[inv_id][sy]["grid_failure"] += r.grid_failure
        inverter_yearly_data[inv_id][sy]["curtailment"] += r.curtailment
        inverter_yearly_data[inv_id][sy]["machine_loss"] += r.machine_loss
        inverter_yearly_data[inv_id][sy]["days"] += 1
        
        inv = inv_by_id.get(inv_id)
        if inv:
            block_yearly_data[inv.block_name][sy]["generation"] += r.generation

    # Fetch alerts and recommendations
    alerts = db.query(Alert).filter(Alert.plant_id == plant_id).order_by(Alert.severity.desc()).all()
    recs = db.query(Recommendation).filter(Recommendation.plant_id == plant_id).order_by(Recommendation.priority.desc()).all()

    # Directories relative to working directory
    base_dir = os.path.abspath(".")
    data_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "Solizer", "data")
    temp_dir = os.path.join(data_dir, "temp_charts")
    reports_dir = os.path.join(data_dir, "reports")
    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(reports_dir, exist_ok=True)

    # Generate charts
    charts = generate_charts(
        plant=plant,
        sorted_study_years=sorted_study_years,
        monthly_kpis_by_year=monthly_kpis_by_year,
        inverter_yearly_data=inverter_yearly_data,
        block_yearly_data=block_yearly_data,
        sorted_inverters=sorted_inverters,
        monthly_losses=monthly_losses,
        output_dir=temp_dir
    )

    # File naming
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"SoliZer_Report_{plant.name.replace(' ', '_')}_{timestamp}.{report_type}"
    file_path = os.path.join(reports_dir, file_name)

    # Generate document
    if report_type == "docx":
        generate_docx_report(
            plant=plant,
            lifetime=lifetime,
            kpis=kpis,
            monthly_kpis=monthly_kpis,
            sorted_study_years=sorted_study_years,
            study_year_records=study_year_records,
            monthly_kpis_by_year=monthly_kpis_by_year,
            inverter_yearly_data=inverter_yearly_data,
            block_yearly_data=block_yearly_data,
            sorted_inverters=sorted_inverters,
            loss=loss_result,
            monthly_losses=monthly_losses,
            deg=deg,
            alerts=alerts,
            recommendations=recs,
            charts=charts,
            file_path=file_path,
            daily_records=daily_records,
        )
    elif report_type == "pdf":
        generate_pdf_report(
            plant=plant,
            lifetime=lifetime,
            kpis=kpis,
            monthly_kpis=monthly_kpis,
            sorted_study_years=sorted_study_years,
            study_year_records=study_year_records,
            monthly_kpis_by_year=monthly_kpis_by_year,
            inverter_yearly_data=inverter_yearly_data,
            block_yearly_data=block_yearly_data,
            sorted_inverters=sorted_inverters,
            loss=loss_result,
            monthly_losses=monthly_losses,
            deg=deg,
            alerts=alerts,
            recommendations=recs,
            charts=charts,
            file_path=file_path,
            daily_records=daily_records,
        )
    else:
        raise ValueError(f"Unsupported report type: {report_type}")

    # Remove temporary charts
    for p in charts.values():
        try:
            os.remove(p)
        except OSError:
            pass

    # Save metadata to DB
    period_start = daily_records[0].record_date
    period_end = daily_records[-1].record_date
    report = Report(
        plant_id=plant_id,
        report_title=f"Performance Assessment Report ({period_start.year}-{period_end.year})",
        report_type=report_type,
        file_path=file_path,
        period_start=period_start,
        period_end=period_end,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return report
