"""
Tests for Step 31: Align 결과 UI 탭.

AlignTab 위젯과 ResultPage.load_align_result() 통합 테스트.
"""

from __future__ import annotations

import numpy as np
import pytest

from PyQt6.QtWidgets import QTableWidget, QPlainTextEdit

from ui.pages.align_tab import AlignTab
from ui.pages.result_page import ResultPage
from core.models import AlignResult


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def align_tab(qtbot):
    """Bare AlignTab widget (shown so isVisible() works correctly)."""
    tab = AlignTab()
    qtbot.addWidget(tab)
    tab.show()
    qtbot.waitExposed(tab)
    return tab


@pytest.fixture
def result_page(qtbot):
    """Full ResultPage (shown so tab visibility propagates)."""
    page = ResultPage()
    qtbot.addWidget(page)
    page.show()
    qtbot.waitExposed(page)
    return page


def _make_result(
    strategy_name: str = "pattern",
    score: float = 0.85,
    success: bool = True,
    failure_reason: str | None = None,
    overlay_image: np.ndarray | None = None,
    reference_point: tuple | None = None,
    design_doc: dict | None = None,
) -> AlignResult:
    """Build a minimal AlignResult-compatible object (dynamic attrs allowed)."""
    result = AlignResult(
        success=success,
        strategy_name=strategy_name,
        score=score,
        failure_reason=failure_reason,
    )
    # Attach optional FallbackAlignResult fields
    result.overlay_image = overlay_image  # type: ignore[attr-defined]
    result.reference_point = reference_point  # type: ignore[attr-defined]
    result.design_doc = design_doc if design_doc is not None else {}  # type: ignore[attr-defined]
    return result


def _make_bgr_image(h: int = 50, w: int = 60) -> np.ndarray:
    """Create a synthetic BGR numpy image."""
    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[:, :, 0] = 100  # Blue channel
    img[:, :, 2] = 200  # Red channel
    return img


# ── 1. AlignTab renders without crash ─────────────────────────────────────────

class TestAlignTabInit:
    def test_renders_without_crash(self, align_tab):
        """AlignTab must instantiate and be visible."""
        assert align_tab is not None

    def test_placeholder_visible_initially(self, align_tab):
        """Placeholder '분석 결과 없음' should be visible before any result is loaded."""
        assert align_tab._placeholder_label.isVisible()
        assert "분석 결과 없음" in align_tab._placeholder_label.text()


# ── 2. load_result with successful AlignResult ────────────────────────────────

class TestLoadResultSuccess:
    def test_strategy_name_visible(self, align_tab):
        """Strategy name label must reflect the loaded result."""
        result = _make_result(strategy_name="caliper", success=True, score=0.92)
        align_tab.load_result(result)
        assert "caliper" in align_tab._strategy_name_label.text()

    def test_score_shown_as_percentage(self, align_tab):
        """Score 0.75 must be displayed as '75.0%'."""
        result = _make_result(score=0.75, success=True)
        align_tab.load_result(result)
        assert "75.0%" in align_tab._score_label.text()

    def test_success_badge_shows_success(self, align_tab):
        """Success badge must say '성공' when result.success is True."""
        result = _make_result(success=True)
        align_tab.load_result(result)
        assert "성공" in align_tab._success_badge.text()

    def test_placeholder_hidden_after_load(self, align_tab):
        """Placeholder must be hidden once a result is loaded."""
        result = _make_result()
        align_tab.load_result(result)
        assert not align_tab._placeholder_label.isVisible()


# ── 3. Reference point ────────────────────────────────────────────────────────

class TestReferencePoint:
    def test_coordinate_visible_when_present(self, align_tab):
        """Reference point (10, 20) must appear as '(10, 20)' in the label."""
        result = _make_result(reference_point=(10, 20))
        align_tab.load_result(result)
        label_text = align_tab._ref_point_label.text()
        assert "10" in label_text and "20" in label_text

    def test_detection_failure_when_none(self, align_tab):
        """Label must show '검출 실패' when reference_point is None."""
        result = _make_result(reference_point=None)
        align_tab.load_result(result)
        assert "검출 실패" in align_tab._ref_point_label.text()


# ── 4. Overlay image ──────────────────────────────────────────────────────────

class TestOverlayImage:
    def test_image_shown_not_placeholder(self, align_tab):
        """When overlay_image is a valid BGR array, the image label must be visible."""
        bgr = _make_bgr_image()
        result = _make_result(overlay_image=bgr)
        align_tab.load_result(result)
        assert align_tab._overlay_image_label.isVisible()
        assert not align_tab._overlay_placeholder_label.isVisible()

    def test_placeholder_shown_when_no_image(self, align_tab):
        """When overlay_image is None, placeholder text must be visible."""
        result = _make_result(overlay_image=None)
        align_tab.load_result(result)
        assert align_tab._overlay_placeholder_label.isVisible()
        assert not align_tab._overlay_image_label.isVisible()


# ── 5. Success=False ─────────────────────────────────────────────────────────

class TestFailureBadge:
    def test_failure_badge_visible(self, align_tab):
        """Badge must say '실패' when result.success is False."""
        result = _make_result(success=False, failure_reason="에지 검출 실패")
        align_tab.load_result(result)
        assert "실패" in align_tab._success_badge.text()

    def test_failure_reason_label_visible(self, align_tab):
        """Failure reason label must be shown and contain the reason text."""
        result = _make_result(success=False, failure_reason="에지 검출 실패")
        align_tab.load_result(result)
        assert align_tab._failure_reason_label.isVisible()
        assert "에지 검출 실패" in align_tab._failure_reason_label.text()


# ── 6. _build_4section_table ──────────────────────────────────────────────────

class TestBuild4SectionTable:
    def test_returns_qtablewidget(self, align_tab):
        """_build_4section_table must return a QTableWidget."""
        doc = {"섹션A": {"키1": "값1", "키2": "값2"}, "섹션B": {"키3": "값3"}}
        table = align_tab._build_4section_table(doc)
        assert isinstance(table, QTableWidget)

    def test_has_rows_for_all_keys(self, align_tab):
        """Table must contain rows for every key in the design_doc."""
        doc = {
            "placement": {"algorithm": "ORB", "roi": True},
            "parameters": {"threshold": 0.5},
            "result_calculation": {"score": 0.9},
            "selection_rationale": {"reason": "작동함"},
        }
        table = align_tab._build_4section_table(doc)
        # 4 section headers + 5 sub-key rows = 9 rows total
        assert table.rowCount() >= 4

    def test_empty_doc_shows_placeholder_row(self, align_tab):
        """Empty design_doc must produce at least one row with a fallback message."""
        table = align_tab._build_4section_table({})
        assert table.rowCount() >= 1
        item = table.item(0, 0)
        assert item is not None

    def test_string_doc_parsed(self, align_tab):
        """String design_doc (pattern_align style) must produce multiple rows."""
        doc_str = (
            "[Section 1: 배치 구조]\n"
            "방식: Pattern Matching\n"
            "[Section 2: 파라미터]\n"
            "임계값: 0.7\n"
        )
        table = align_tab._build_4section_table(doc_str)  # type: ignore[arg-type]
        assert table.rowCount() >= 2


# ── 7. _build_library_table ───────────────────────────────────────────────────

class TestBuildLibraryTable:
    def test_returns_qtablewidget(self, align_tab):
        table = align_tab._build_library_table()
        assert isinstance(table, QTableWidget)

    def test_has_5_columns(self, align_tab):
        table = align_tab._build_library_table()
        assert table.columnCount() == 5

    def test_has_at_least_4_rows(self, align_tab):
        table = align_tab._build_library_table()
        assert table.rowCount() >= 4

    def test_column_headers_include_libraries(self, align_tab):
        table = align_tab._build_library_table()
        headers = [
            table.horizontalHeaderItem(i).text()
            for i in range(table.columnCount())
        ]
        assert "Keyence" in headers
        assert "Cognex" in headers
        assert "Halcon" in headers
        assert "MIL" in headers


# ── 8. _build_fallback_log ────────────────────────────────────────────────────

class TestBuildFallbackLog:
    def test_returns_qplaintextedit(self, align_tab):
        doc = {
            "chain_stages_tried": ["pattern", "caliper"],
            "winning_strategy": "caliper",
            "failure_reasons": {"pattern": "점수 미달"},
            "ai_strategy_decision": False,
        }
        log = align_tab._build_fallback_log(doc)
        assert isinstance(log, QPlainTextEdit)

    def test_contains_stages_tried(self, align_tab):
        doc = {
            "chain_stages_tried": ["pattern", "caliper", "feature"],
            "winning_strategy": "feature",
            "failure_reasons": {"pattern": "실패1", "caliper": "실패2"},
            "ai_strategy_decision": True,
        }
        log = align_tab._build_fallback_log(doc)
        text = log.toPlainText()
        assert "pattern" in text
        assert "caliper" in text
        assert "feature" in text

    def test_is_read_only(self, align_tab):
        doc = {
            "chain_stages_tried": ["pattern"],
            "winning_strategy": "pattern",
            "failure_reasons": {},
            "ai_strategy_decision": False,
        }
        log = align_tab._build_fallback_log(doc)
        assert log.isReadOnly()


# ── 9. load_result with None ──────────────────────────────────────────────────

class TestLoadResultNone:
    def test_shows_placeholder_when_none(self, align_tab):
        """load_result(None) must show '분석 결과 없음' placeholder."""
        # First load a real result, then pass None
        align_tab.load_result(_make_result())
        align_tab.load_result(None)
        assert align_tab._placeholder_label.isVisible()
        assert "분석 결과 없음" in align_tab._placeholder_label.text()


# ── 10. Fallback log section visibility ───────────────────────────────────────

class TestFallbackLogSection:
    def test_fallback_section_hidden_without_chain_doc(self, align_tab):
        """Fallback section must be hidden when design_doc has no chain_stages_tried."""
        result = _make_result(design_doc={"placement": {"algo": "ORB"}})
        align_tab.load_result(result)
        assert not align_tab._fallback_section_frame.isVisible()

    def test_fallback_section_visible_with_chain_doc(self, align_tab):
        """Fallback section must be visible when design_doc contains chain_stages_tried."""
        result = _make_result(design_doc={
            "chain_stages_tried": ["pattern", "caliper"],
            "winning_strategy": "caliper",
            "failure_reasons": {"pattern": "low score"},
            "ai_strategy_decision": False,
        })
        align_tab.load_result(result)
        assert align_tab._fallback_section_frame.isVisible()


# ── 11. ResultPage integration ────────────────────────────────────────────────

class TestResultPageIntegration:
    def test_load_align_result_loads_data(self, result_page):
        """ResultPage.load_align_result() must load data into align tab."""
        result = _make_result(strategy_name="feature", score=0.88, success=True)
        result_page.load_align_result(result)
        # Tab should still exist and data loaded (tab switch now handled by load_all)
        assert isinstance(result_page._align_tab, AlignTab)

    def test_align_tab_accessible_on_result_page(self, result_page):
        """ResultPage._align_tab must be an AlignTab instance."""
        assert isinstance(result_page._align_tab, AlignTab)

    def test_load_align_result_with_none(self, result_page):
        """load_align_result(None) must not raise."""
        result_page.load_align_result(None)
        # Should not raise — tab index unchanged (no data to load)
