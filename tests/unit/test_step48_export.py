"""
Step 48 — 결과 내보내기 (Export) 테스트.

JSON/PDF/Image 내보내기 및 ExportDialog 테스트.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest

from PyQt6.QtWidgets import QApplication

from core.models import (
    AlignResult,
    EvaluationResult,
    FailureAnalysisResult,
    FeasibilityResult,
    InspectionCandidate,
    InspectionPurpose,
    OptimizationResult,
)
from core.export.json_exporter import ArgosJSONExporter
from core.export.pdf_exporter import ArgosPDFExporter
from core.export.image_exporter import ArgosImageExporter
from ui.dialogs.export_dialog import ExportDialog

# ── Ensure QApplication exists ───────────────────────────────────────────────

_app = QApplication.instance() or QApplication([])


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_purpose() -> InspectionPurpose:
    return InspectionPurpose(
        inspection_type="결함검출",
        description="스크래치 검출",
        ok_ng_criteria="스크래치 없음=OK",
        target_feature="표면 스크래치",
        measurement_unit="px",
        tolerance="10px",
    )


def _make_align() -> AlignResult:
    return AlignResult(
        success=True,
        strategy_name="PatternMatch",
        score=0.95,
        transform_matrix=np.eye(3),
    )


def _make_candidate() -> InspectionCandidate:
    return InspectionCandidate(
        candidate_id="C001",
        method="blob",
        params={"threshold": 128, "min_area": 50},
        design_doc={"layout": {}, "parameters": {}, "result_calculation": {}, "rationale": "best fit"},
        library_mapping={"Keyence": "BLOB", "Cognex": "CogBlob"},
        ok_pass_rate=0.90,
        ng_detect_rate=0.85,
        score=0.88,
        rationale="Blob detection is suitable",
        overlay_image_path=None,
    )


def _make_evaluation() -> EvaluationResult:
    return EvaluationResult(
        best_strategy="blob",
        ok_pass_rate=0.90,
        ng_detect_rate=0.85,
        final_score=0.88,
        margin=0.15,
        is_margin_warning=False,
    )


def _make_failure() -> FailureAnalysisResult:
    return FailureAnalysisResult(
        fp_overlay_paths=[],
        fn_overlay_paths=[],
        cause_summary="Minor threshold mismatch",
        improvement_directions=["Adjust threshold"],
        fp_count=2,
        fn_count=1,
    )


def _make_feasibility() -> FeasibilityResult:
    return FeasibilityResult(
        rule_based_sufficient=True,
        recommended_approach="Rule-based",
        reasoning="High score with rule-based approach",
    )


def _make_optimization() -> OptimizationResult:
    return OptimizationResult(
        best_candidate=_make_candidate(),
        best_evaluation=_make_evaluation(),
    )


def _make_results() -> dict:
    """Build a full aggregate results dict."""
    return {
        "purpose": _make_purpose(),
        "align": _make_align(),
        "inspection": _make_optimization(),
        "evaluation": {
            "failure_result": _make_failure(),
            "feasibility_result": _make_feasibility(),
        },
    }


# ── JSON Exporter Tests ─────────────────────────────────────────────────────


class TestArgosJSONExporter:
    """Tests for ArgosJSONExporter."""

    def test_export_creates_file(self, tmp_path: Path):
        """Export should create argos_results.json."""
        results = _make_results()
        path = ArgosJSONExporter().export(results, tmp_path)
        assert path.exists()
        assert path.name == "argos_results.json"

    def test_export_valid_json(self, tmp_path: Path):
        """Exported file should be parseable JSON."""
        results = _make_results()
        path = ArgosJSONExporter().export(results, tmp_path)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_export_contains_purpose(self, tmp_path: Path):
        """JSON should contain inspection purpose fields."""
        results = _make_results()
        path = ArgosJSONExporter().export(results, tmp_path)
        data = json.loads(path.read_text(encoding="utf-8"))
        purpose = data["purpose"]
        assert purpose["inspection_type"] == "결함검출"
        assert purpose["description"] == "스크래치 검출"

    def test_export_ndarray_as_metadata(self, tmp_path: Path):
        """numpy arrays should be stored as shape/dtype metadata, not raw data."""
        results = _make_results()
        path = ArgosJSONExporter().export(results, tmp_path)
        data = json.loads(path.read_text(encoding="utf-8"))
        matrix = data["align"]["transform_matrix"]
        assert matrix["__ndarray__"] is True
        assert matrix["shape"] == [3, 3]

    def test_export_empty_results(self, tmp_path: Path):
        """Empty dict should produce a valid JSON file."""
        path = ArgosJSONExporter().export({}, tmp_path)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data == {}

    def test_export_creates_directory(self, tmp_path: Path):
        """Export should create output directory if it doesn't exist."""
        nested = tmp_path / "sub" / "dir"
        path = ArgosJSONExporter().export(_make_results(), nested)
        assert path.exists()

    def test_export_align_score(self, tmp_path: Path):
        """JSON should contain correct align score."""
        results = _make_results()
        path = ArgosJSONExporter().export(results, tmp_path)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["align"]["score"] == 0.95

    def test_serialize_numpy_types(self, tmp_path: Path):
        """numpy scalar types should be serialized to Python types."""
        results = {"value_int": np.int64(42), "value_float": np.float32(3.14)}
        path = ArgosJSONExporter().export(results, tmp_path)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["value_int"] == 42
        assert abs(data["value_float"] - 3.14) < 0.01


# ── PDF Exporter Tests ───────────────────────────────────────────────────────


class TestArgosPDFExporter:
    """Tests for ArgosPDFExporter."""

    def test_export_creates_file(self, tmp_path: Path):
        """Export should create argos_report.pdf."""
        results = _make_results()
        path = ArgosPDFExporter().export(results, tmp_path)
        assert path.exists()
        assert path.name == "argos_report.pdf"

    def test_export_valid_pdf(self, tmp_path: Path):
        """Exported file should start with PDF magic bytes."""
        results = _make_results()
        path = ArgosPDFExporter().export(results, tmp_path)
        header = path.read_bytes()[:5]
        assert header == b"%PDF-"

    def test_export_empty_results(self, tmp_path: Path):
        """Empty results should still produce a valid PDF."""
        path = ArgosPDFExporter().export({}, tmp_path)
        assert path.exists()
        header = path.read_bytes()[:5]
        assert header == b"%PDF-"

    def test_export_creates_directory(self, tmp_path: Path):
        """Export should create output directory if it doesn't exist."""
        nested = tmp_path / "sub" / "dir"
        path = ArgosPDFExporter().export(_make_results(), nested)
        assert path.exists()

    def test_export_with_feasibility(self, tmp_path: Path):
        """PDF with feasibility data should not raise."""
        results = _make_results()
        path = ArgosPDFExporter().export(results, tmp_path)
        assert path.stat().st_size > 0

    def test_korean_font_registered(self):
        """Font registration should not crash and return valid names."""
        regular, bold = ArgosPDFExporter._register_korean_font()
        assert isinstance(regular, str)
        assert isinstance(bold, str)
        assert len(regular) > 0
        assert len(bold) > 0

    def test_pdf_export_with_korean_content(self, tmp_path: Path):
        """PDF with Korean strings should be created and non-empty."""
        results = {
            "purpose": InspectionPurpose(
                inspection_type="결함검출",
                description="표면 스크래치 검출",
                ok_ng_criteria="스크래치 없음=OK",
                target_feature="표면 결함",
                tolerance="±0.1mm",
            ),
        }
        path = ArgosPDFExporter().export(results, tmp_path)
        assert path.exists()
        assert path.stat().st_size > 0
        header = path.read_bytes()[:5]
        assert header == b"%PDF-"


# ── Image Exporter Tests ─────────────────────────────────────────────────────


class TestArgosImageExporter:
    """Tests for ArgosImageExporter."""

    def test_export_no_images(self, tmp_path: Path):
        """No images in results should return empty list."""
        results = {"align": None, "inspection": None, "evaluation": {}}
        saved = ArgosImageExporter().export(results, tmp_path)
        assert saved == []

    def test_export_ndarray_image(self, tmp_path: Path):
        """ndarray overlay should be saved as PNG."""
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        align = AlignResult(success=True, strategy_name="test", score=0.9)
        # Monkey-patch an overlay_image attribute
        align.overlay_image = img
        results = {"align": align, "inspection": None, "evaluation": {}}
        saved = ArgosImageExporter().export(results, tmp_path)
        assert len(saved) == 1
        assert saved[0].name == "argos_align_overlay.png"
        # Verify it's a valid image
        loaded = cv2.imread(str(saved[0]))
        assert loaded is not None

    def test_export_file_path_image(self, tmp_path: Path):
        """File path overlay should be copied."""
        # Create a source image file
        src_img = np.zeros((50, 50, 3), dtype=np.uint8)
        src_path = tmp_path / "source.png"
        cv2.imwrite(str(src_path), src_img)

        candidate = _make_candidate()
        candidate.overlay_image_path = str(src_path)
        opt = OptimizationResult(best_candidate=candidate, best_evaluation=_make_evaluation())
        results = {"align": None, "inspection": opt, "evaluation": {}}
        saved = ArgosImageExporter().export(results, tmp_path)
        assert len(saved) == 1
        assert saved[0].name == "argos_inspection_overlay.png"

    def test_export_failure_overlays(self, tmp_path: Path):
        """Failure FP/FN overlays should be saved."""
        # Create source images
        src1 = tmp_path / "fp1.png"
        src2 = tmp_path / "fn1.png"
        img = np.zeros((50, 50, 3), dtype=np.uint8)
        cv2.imwrite(str(src1), img)
        cv2.imwrite(str(src2), img)

        failure = FailureAnalysisResult(
            fp_overlay_paths=[str(src1)],
            fn_overlay_paths=[str(src2)],
            cause_summary="test",
            improvement_directions=[],
            fp_count=1,
            fn_count=1,
        )
        results = {
            "align": None,
            "inspection": None,
            "evaluation": {"failure_result": failure},
        }
        out_dir = tmp_path / "export"
        saved = ArgosImageExporter().export(results, out_dir)
        assert len(saved) == 2
        names = {p.name for p in saved}
        assert "argos_failure_fp_001.png" in names
        assert "argos_failure_fn_001.png" in names

    def test_export_missing_source_file(self, tmp_path: Path):
        """Missing source file should be skipped gracefully."""
        failure = FailureAnalysisResult(
            fp_overlay_paths=["/nonexistent/path.png"],
            fn_overlay_paths=[],
            cause_summary="test",
            improvement_directions=[],
            fp_count=1,
            fn_count=0,
        )
        results = {
            "align": None,
            "inspection": None,
            "evaluation": {"failure_result": failure},
        }
        saved = ArgosImageExporter().export(results, tmp_path)
        assert saved == []

    def test_export_creates_directory(self, tmp_path: Path):
        """Export should create output directory if it doesn't exist."""
        nested = tmp_path / "sub" / "dir"
        saved = ArgosImageExporter().export({}, nested)
        assert nested.is_dir()


# ── ExportDialog Tests ───────────────────────────────────────────────────────


class TestExportDialog:
    """Tests for ExportDialog."""

    def test_creation(self):
        """Dialog should be created without errors."""
        dialog = ExportDialog()
        assert dialog.windowTitle() == "결과 내보내기"

    def test_default_checkboxes(self):
        """All checkboxes should be checked by default."""
        dialog = ExportDialog()
        assert dialog.export_json is True
        assert dialog.export_pdf is True
        assert dialog.export_images is True

    def test_export_button_disabled_initially(self):
        """Export button should be disabled until path is selected."""
        dialog = ExportDialog()
        assert dialog._export_btn.isEnabled() is False

    def test_path_selection_enables_button(self):
        """Setting a path should enable the export button."""
        dialog = ExportDialog()
        dialog._selected_path = "/tmp/test"
        dialog._export_btn.setEnabled(True)
        assert dialog._export_btn.isEnabled() is True
        assert dialog.selected_path == "/tmp/test"

    def test_checkbox_toggle(self):
        """Toggling checkboxes should update properties."""
        dialog = ExportDialog()
        dialog._json_checkbox.setChecked(False)
        assert dialog.export_json is False
        dialog._pdf_checkbox.setChecked(False)
        assert dialog.export_pdf is False
        dialog._image_checkbox.setChecked(False)
        assert dialog.export_images is False


# ── Integration Tests ────────────────────────────────────────────────────────


class TestExportIntegration:
    """Integration tests: full export pipeline."""

    def test_full_export_all_types(self, tmp_path: Path):
        """Running all three exporters on full results should succeed."""
        results = _make_results()

        json_path = ArgosJSONExporter().export(results, tmp_path)
        assert json_path.exists()

        pdf_path = ArgosPDFExporter().export(results, tmp_path)
        assert pdf_path.exists()

        images = ArgosImageExporter().export(results, tmp_path)
        # No overlay images in the default test data
        assert isinstance(images, list)

    def test_full_export_to_same_directory(self, tmp_path: Path):
        """All exports to the same directory should not conflict."""
        results = _make_results()
        json_path = ArgosJSONExporter().export(results, tmp_path)
        pdf_path = ArgosPDFExporter().export(results, tmp_path)
        assert json_path.parent == pdf_path.parent
        assert json_path.name != pdf_path.name

    def test_export_with_overlay_images(self, tmp_path: Path):
        """Full export including overlay images."""
        results = _make_results()

        # Add overlay to align
        results["align"].overlay_image = np.zeros((100, 100, 3), dtype=np.uint8)

        images = ArgosImageExporter().export(results, tmp_path)
        assert len(images) == 1
        assert images[0].name == "argos_align_overlay.png"
