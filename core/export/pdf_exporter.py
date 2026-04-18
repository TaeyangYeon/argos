"""
PDF report exporter for the Argos vision algorithm design system.

Generates a formatted PDF report using reportlab, following
the final output format defined in PLAN.md section 15.
"""

from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Any, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from core.logger import get_logger
from core.models import (
    AlignResult,
    EvaluationResult,
    FailureAnalysisResult,
    FeasibilityResult,
    InspectionCandidate,
    InspectionPurpose,
    OptimizationResult,
)


def _safe_str(value: Any) -> str:
    """Convert value to string, handling None and special types."""
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


class ArgosPDFExporter:
    """Generates a formatted PDF report from analysis results."""

    def __init__(self) -> None:
        self._logger = get_logger("pdf_exporter")

    def export(self, results: dict, output_path: Path) -> Path:
        """
        Export analysis results to a PDF report.

        Args:
            results: Aggregate result dict from AnalysisWorker.
            output_path: Directory to write the PDF file into.

        Returns:
            Path to the created PDF file.
        """
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)
        file_path = output_path / "argos_report.pdf"

        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=A4,
            leftMargin=20 * mm,
            rightMargin=20 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
        )

        styles = getSampleStyleSheet()
        elements = self._build_elements(results, styles)
        doc.build(elements, onFirstPage=self._add_page_number, onLaterPages=self._add_page_number)

        self._logger.info("PDF export complete: %s", file_path)
        return file_path

    def _build_elements(self, results: dict, styles) -> list:
        """Build the list of flowable elements for the PDF."""
        elements: list = []

        title_style = ParagraphStyle(
            "ArgosTitle", parent=styles["Title"], fontSize=18, spaceAfter=12
        )
        heading_style = ParagraphStyle(
            "ArgosHeading", parent=styles["Heading2"], fontSize=14, spaceBefore=12, spaceAfter=6
        )
        body_style = ParagraphStyle(
            "ArgosBody", parent=styles["Normal"], fontSize=10, spaceAfter=4
        )

        # Header
        elements.append(Paragraph("AI Vision Engineer Agent", title_style))
        elements.append(Spacer(1, 6))

        # 1. Inspection Purpose
        purpose = results.get("purpose") or results.get("inspection_purpose")
        elements.append(Paragraph("[Inspection Purpose]", heading_style))
        if isinstance(purpose, InspectionPurpose):
            data = [
                ["Type", _safe_str(purpose.inspection_type)],
                ["Description", _safe_str(purpose.description)],
                ["OK/NG Criteria", _safe_str(purpose.ok_ng_criteria)],
                ["Target Feature", _safe_str(purpose.target_feature)],
                ["Tolerance", _safe_str(purpose.tolerance)],
            ]
            elements.append(self._make_table(data))
        else:
            elements.append(Paragraph("No inspection purpose data.", body_style))
        elements.append(Spacer(1, 6))

        # 2. Align Strategy
        align = results.get("align")
        elements.append(Paragraph("[Align Strategy]", heading_style))
        if isinstance(align, AlignResult):
            data = [
                ["Strategy", _safe_str(align.strategy_name)],
                ["Score", _safe_str(align.score)],
                ["Success", _safe_str(align.success)],
            ]
            elements.append(self._make_table(data))
        else:
            elements.append(Paragraph("No align data.", body_style))
        elements.append(Spacer(1, 6))

        # 3. Inspection Algorithm (best candidate)
        inspection = results.get("inspection")
        best_candidate = self._extract_best_candidate(inspection)
        elements.append(Paragraph("[Inspection Algorithm]", heading_style))
        if best_candidate is not None:
            data = [
                ["Method", _safe_str(best_candidate.method)],
                ["Score", _safe_str(best_candidate.score)],
                ["OK Pass Rate", _safe_str(best_candidate.ok_pass_rate)],
                ["NG Detect Rate", _safe_str(best_candidate.ng_detect_rate)],
                ["Rationale", _safe_str(best_candidate.rationale)],
            ]
            elements.append(self._make_table(data))
        else:
            elements.append(Paragraph("No inspection candidate data.", body_style))
        elements.append(Spacer(1, 6))

        # 4. Accuracy
        best_eval = self._extract_best_evaluation(inspection)
        elements.append(Paragraph("[Accuracy]", heading_style))
        if best_eval is not None:
            data = [
                ["OK Pass Rate", _safe_str(best_eval.ok_pass_rate)],
                ["NG Detect Rate", _safe_str(best_eval.ng_detect_rate)],
                ["Separation Margin", _safe_str(best_eval.margin)],
                ["Final Score", _safe_str(best_eval.final_score)],
            ]
            elements.append(self._make_table(data))
        else:
            elements.append(Paragraph("No accuracy data.", body_style))
        elements.append(Spacer(1, 6))

        # 5. Failure Cases
        eval_dict = results.get("evaluation")
        failure: Optional[FailureAnalysisResult] = None
        if isinstance(eval_dict, dict):
            failure = eval_dict.get("failure_result")

        elements.append(Paragraph("[Failure Cases]", heading_style))
        if isinstance(failure, FailureAnalysisResult):
            data = [
                ["FP Count", _safe_str(failure.fp_count)],
                ["FN Count", _safe_str(failure.fn_count)],
                ["Cause Summary", _safe_str(failure.cause_summary)],
            ]
            elements.append(self._make_table(data))
        else:
            elements.append(Paragraph("No failure analysis data.", body_style))
        elements.append(Spacer(1, 6))

        # 6. Feasibility Analysis
        feasibility: Optional[FeasibilityResult] = None
        if isinstance(eval_dict, dict):
            feasibility = eval_dict.get("feasibility_result")

        elements.append(Paragraph("[Feasibility Analysis]", heading_style))
        if isinstance(feasibility, FeasibilityResult):
            data = [
                ["Rule-based Sufficient", _safe_str(feasibility.rule_based_sufficient)],
                ["Recommended Approach", _safe_str(feasibility.recommended_approach)],
                ["Reasoning", _safe_str(feasibility.reasoning)],
            ]
            if feasibility.model_suggestion:
                data.append(["Model Suggestion", _safe_str(feasibility.model_suggestion)])
            elements.append(self._make_table(data))
        else:
            elements.append(Paragraph("No feasibility data.", body_style))
        elements.append(Spacer(1, 6))

        # 7. Recommended Approach
        elements.append(Paragraph("[Recommended Approach]", heading_style))
        if isinstance(feasibility, FeasibilityResult):
            elements.append(Paragraph(feasibility.recommended_approach, body_style))
            elements.append(Paragraph(feasibility.reasoning, body_style))
        else:
            elements.append(Paragraph("No recommendation available.", body_style))

        return elements

    @staticmethod
    def _extract_best_candidate(inspection: Any) -> Optional[InspectionCandidate]:
        """Extract best candidate from inspection result."""
        if inspection is None:
            return None
        # OptimizationResult
        best = getattr(inspection, "best_candidate", None)
        if isinstance(best, InspectionCandidate):
            return best
        # Dict fallback
        if isinstance(inspection, dict):
            best = inspection.get("best_candidate")
            if isinstance(best, InspectionCandidate):
                return best
        return None

    @staticmethod
    def _extract_best_evaluation(inspection: Any) -> Optional[EvaluationResult]:
        """Extract best evaluation from inspection result."""
        if inspection is None:
            return None
        best_eval = getattr(inspection, "best_evaluation", None)
        if isinstance(best_eval, EvaluationResult):
            return best_eval
        if isinstance(inspection, dict):
            best_eval = inspection.get("best_evaluation")
            if isinstance(best_eval, EvaluationResult):
                return best_eval
        return None

    @staticmethod
    def _make_table(data: list[list[str]]) -> Table:
        """Create a styled two-column table."""
        col_widths = [120, 350]
        table = Table(data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E8EAF6")),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BDBDBD")),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return table

    @staticmethod
    def _add_page_number(canvas, doc) -> None:
        """Add page number at the bottom of each page."""
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        page_num = canvas.getPageNumber()
        text = f"Page {page_num}"
        canvas.drawCentredString(A4[0] / 2, 10 * mm, text)
        canvas.restoreState()
