"""
Step 46 — Failure 케이스 뷰어 테스트.

FailureTab, FailureDetailDialog, ResultPage 연동을 검증한다.
"""

import os
import tempfile
import types

import cv2
import numpy as np
import pytest

from ui.pages.failure_tab import FailureTab, _ThumbnailWidget
from ui.dialogs.failure_detail_dialog import FailureDetailDialog
from ui.pages.result_page import ResultPage


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_overlay_image(tmpdir: str, name: str) -> str:
    """Create a small test overlay PNG and return its path."""
    img = np.ones((120, 160, 3), dtype=np.uint8) * 200
    cv2.rectangle(img, (0, 0), (159, 119), (0, 0, 255), 3)
    path = os.path.join(tmpdir, name)
    cv2.imwrite(path, img)
    return path


def _make_failure_result(
    fp_count: int = 2,
    fn_count: int = 1,
    tmpdir: str | None = None,
    cause: str = "밝기 변화로 인한 오탐 발생",
    improvements: list[str] | None = None,
) -> object:
    """Create a FailureAnalysisResult-like object."""
    if tmpdir is None:
        tmpdir = tempfile.mkdtemp(prefix="argos_test_")
    if improvements is None:
        improvements = ["임계값 조정", "전처리 필터 추가"]

    fp_paths = [_make_overlay_image(tmpdir, f"FP_{i}.png") for i in range(fp_count)]
    fn_paths = [_make_overlay_image(tmpdir, f"FN_{i}.png") for i in range(fn_count)]

    return types.SimpleNamespace(
        fp_overlay_paths=fp_paths,
        fn_overlay_paths=fn_paths,
        cause_summary=cause,
        improvement_directions=improvements,
        fp_count=fp_count,
        fn_count=fn_count,
    )


# ── FailureTab Tests ────────────────────────────────────────────────────────


class TestFailureTabInstantiation:
    """FailureTab 생성 검증."""

    def test_instantiation(self, qtbot):
        tab = FailureTab()
        qtbot.addWidget(tab)
        tab.show()
        assert tab is not None
        assert not tab._summary_card.isVisible()
        assert tab._message_label.isVisible()


class TestFailureTabLoadResult:
    """load_result 호출 시 UI 상태 검증."""

    def test_load_none_shows_empty(self, qtbot):
        tab = FailureTab()
        qtbot.addWidget(tab)
        tab.show()
        tab.load_result(None)

        assert tab._message_label.isVisible()
        assert not tab._summary_card.isVisible()
        assert not tab._grid_frame.isVisible()

    def test_load_empty_failures_shows_success(self, qtbot):
        tab = FailureTab()
        qtbot.addWidget(tab)
        tab.show()

        result = _make_failure_result(fp_count=0, fn_count=0)
        tab.load_result(result)

        assert tab._summary_card.isVisible()
        assert tab._message_label.isVisible()
        assert "정상 판정" in tab._message_label.text()
        assert not tab._grid_frame.isVisible()

    def test_load_with_fp_fn_shows_grid(self, qtbot):
        tab = FailureTab()
        qtbot.addWidget(tab)
        tab.show()

        result = _make_failure_result(fp_count=2, fn_count=1)
        tab.load_result(result)

        assert tab._summary_card.isVisible()
        assert not tab._message_label.isVisible()
        assert tab._grid_frame.isVisible()
        assert len(tab._thumbnails) == 3

    def test_fp_count_display(self, qtbot):
        tab = FailureTab()
        qtbot.addWidget(tab)
        result = _make_failure_result(fp_count=5, fn_count=2)
        tab.load_result(result)

        assert tab._fp_count_label.text() == "5"
        assert tab._fn_count_label.text() == "2"
        assert tab._total_label.text() == "7"

    def test_fn_count_display(self, qtbot):
        tab = FailureTab()
        qtbot.addWidget(tab)
        result = _make_failure_result(fp_count=0, fn_count=3)
        tab.load_result(result)

        assert tab._fn_count_label.text() == "3"
        assert tab._total_label.text() == "3"


class TestThumbnailStyling:
    """FP/FN 썸네일 스타일링 검증."""

    def test_fp_thumbnail_has_red_border(self, qtbot):
        tmpdir = tempfile.mkdtemp()
        path = _make_overlay_image(tmpdir, "FP_test.png")
        thumb = _ThumbnailWidget(path, "FP", "FP_test.png")
        qtbot.addWidget(thumb)
        thumb.show()

        style = thumb.styleSheet()
        assert "#E53935" in style  # Colors.ERROR

    def test_fn_thumbnail_has_orange_border(self, qtbot):
        tmpdir = tempfile.mkdtemp()
        path = _make_overlay_image(tmpdir, "FN_test.png")
        thumb = _ThumbnailWidget(path, "FN", "FN_test.png")
        qtbot.addWidget(thumb)
        thumb.show()

        style = thumb.styleSheet()
        assert "#FF9800" in style  # Colors.WARNING

    def test_thumbnail_click_emits_signal(self, qtbot):
        tmpdir = tempfile.mkdtemp()
        path = _make_overlay_image(tmpdir, "FP_click.png")
        thumb = _ThumbnailWidget(path, "FP", "FP_click.png")
        qtbot.addWidget(thumb)
        thumb.show()

        with qtbot.waitSignal(thumb.clicked, timeout=1000):
            qtbot.mouseClick(thumb, Qt.MouseButton.LeftButton)


class TestMultipleThumbnailsInGrid:
    """다수의 FP/FN 이미지가 그리드에 배치되는지 검증."""

    def test_many_thumbnails(self, qtbot):
        tab = FailureTab()
        qtbot.addWidget(tab)

        result = _make_failure_result(fp_count=4, fn_count=3)
        tab.load_result(result)

        assert len(tab._thumbnails) == 7
        # Check type distribution
        fp_thumbs = [t for t in tab._thumbnails if t.failure_type == "FP"]
        fn_thumbs = [t for t in tab._thumbnails if t.failure_type == "FN"]
        assert len(fp_thumbs) == 4
        assert len(fn_thumbs) == 3


class TestThumbnailOpensDialog:
    """썸네일 클릭 시 FailureDetailDialog 열기 검증."""

    def test_open_detail_creates_dialog(self, qtbot, monkeypatch):
        tab = FailureTab()
        qtbot.addWidget(tab)

        result = _make_failure_result(fp_count=1, fn_count=0)
        tab.load_result(result)

        # Monkeypatch exec to prevent blocking
        dialog_created = []
        original_init = FailureDetailDialog.__init__

        def patched_init(self_dialog, *args, **kwargs):
            original_init(self_dialog, *args, **kwargs)
            dialog_created.append(self_dialog)

        monkeypatch.setattr(FailureDetailDialog, "__init__", patched_init)
        monkeypatch.setattr(FailureDetailDialog, "exec", lambda self: None)

        tab._open_detail(
            result.fp_overlay_paths[0], "FP",
            result.cause_summary, result.improvement_directions,
        )
        assert len(dialog_created) == 1


# ── FailureDetailDialog Tests ───────────────────────────────────────────────


class TestFailureDetailDialog:
    """FailureDetailDialog 검증."""

    def test_dialog_renders_overlay(self, qtbot):
        tmpdir = tempfile.mkdtemp()
        path = _make_overlay_image(tmpdir, "FP_detail.png")

        dialog = FailureDetailDialog(
            overlay_path=path,
            failure_type="FP",
            cause_summary="테스트 원인",
            improvement_directions=["방향1", "방향2"],
        )
        qtbot.addWidget(dialog)
        dialog.show()

        assert dialog._overlay_pixmap is not None
        assert not dialog._overlay_label.pixmap().isNull()

    def test_dialog_shows_cause_text(self, qtbot):
        tmpdir = tempfile.mkdtemp()
        path = _make_overlay_image(tmpdir, "FP_cause.png")

        dialog = FailureDetailDialog(
            overlay_path=path,
            failure_type="FP",
            cause_summary="밝기 변화가 원인입니다",
            improvement_directions=[],
        )
        qtbot.addWidget(dialog)
        dialog.show()

        assert "밝기 변화가 원인입니다" in dialog._cause_text.toPlainText()

    def test_dialog_fp_badge(self, qtbot):
        tmpdir = tempfile.mkdtemp()
        path = _make_overlay_image(tmpdir, "FP_badge.png")

        dialog = FailureDetailDialog(
            overlay_path=path,
            failure_type="FP",
            cause_summary="",
            improvement_directions=[],
        )
        qtbot.addWidget(dialog)

        assert "False Positive" in dialog._badge_label.text()

    def test_dialog_fn_badge(self, qtbot):
        tmpdir = tempfile.mkdtemp()
        path = _make_overlay_image(tmpdir, "FN_badge.png")

        dialog = FailureDetailDialog(
            overlay_path=path,
            failure_type="FN",
            cause_summary="",
            improvement_directions=[],
        )
        qtbot.addWidget(dialog)

        assert "False Negative" in dialog._badge_label.text()

    def test_dialog_improvement_directions(self, qtbot):
        tmpdir = tempfile.mkdtemp()
        path = _make_overlay_image(tmpdir, "FP_imp.png")

        dialog = FailureDetailDialog(
            overlay_path=path,
            failure_type="FP",
            cause_summary="원인",
            improvement_directions=["방향A", "방향B"],
        )
        qtbot.addWidget(dialog)
        dialog.show()

        text = dialog._improvement_text.toPlainText()
        assert "방향A" in text
        assert "방향B" in text

    def test_dialog_zoom_in(self, qtbot):
        tmpdir = tempfile.mkdtemp()
        path = _make_overlay_image(tmpdir, "FP_zoom.png")

        dialog = FailureDetailDialog(
            overlay_path=path,
            failure_type="FP",
            cause_summary="",
            improvement_directions=[],
        )
        qtbot.addWidget(dialog)
        dialog.show()

        initial_factor = dialog._scale_factor
        dialog._zoom_in()
        assert dialog._scale_factor > initial_factor

    def test_dialog_zoom_out(self, qtbot):
        tmpdir = tempfile.mkdtemp()
        path = _make_overlay_image(tmpdir, "FP_zout.png")

        dialog = FailureDetailDialog(
            overlay_path=path,
            failure_type="FP",
            cause_summary="",
            improvement_directions=[],
        )
        qtbot.addWidget(dialog)
        dialog.show()

        dialog._zoom_in()
        prev = dialog._scale_factor
        dialog._zoom_out()
        assert dialog._scale_factor < prev

    def test_dialog_zoom_reset(self, qtbot):
        tmpdir = tempfile.mkdtemp()
        path = _make_overlay_image(tmpdir, "FP_zreset.png")

        dialog = FailureDetailDialog(
            overlay_path=path,
            failure_type="FP",
            cause_summary="",
            improvement_directions=[],
        )
        qtbot.addWidget(dialog)
        dialog.show()

        dialog._zoom_in()
        dialog._zoom_in()
        dialog._zoom_reset()
        assert dialog._scale_factor == 1.0
        assert "100%" in dialog._zoom_label.text()


# ── ResultPage Integration ──────────────────────────────────────────────────


class TestResultPageFailureIntegration:
    """ResultPage의 Failure 탭 연동 검증."""

    def test_result_page_has_failure_tab(self, qtbot):
        page = ResultPage()
        qtbot.addWidget(page)
        page.show()

        assert hasattr(page, "_failure_tab")
        assert isinstance(page._failure_tab, FailureTab)

    def test_result_page_6_tabs(self, qtbot):
        page = ResultPage()
        qtbot.addWidget(page)
        page.show()

        assert page._tab_widget.count() == 6

    def test_load_failure_result_method(self, qtbot):
        page = ResultPage()
        qtbot.addWidget(page)
        page.show()

        result = _make_failure_result(fp_count=1, fn_count=1)
        page.load_failure_result(result)

        assert page._failure_tab._fp_count_label.text() == "1"
        assert page._failure_tab._fn_count_label.text() == "1"

    def test_load_all_includes_failure(self, qtbot):
        page = ResultPage()
        qtbot.addWidget(page)

        failure = _make_failure_result(fp_count=2, fn_count=0)
        aggregate = {
            "feature": None,
            "align": None,
            "inspection": None,
            "evaluation": {
                "failure_result": failure,
                "feasibility_result": None,
            },
            "inspection_purpose": None,
        }
        page.load_all(aggregate)

        assert page._failure_tab._fp_count_label.text() == "2"
        assert page._failure_tab._fn_count_label.text() == "0"

    def test_load_all_no_evaluation(self, qtbot):
        page = ResultPage()
        qtbot.addWidget(page)

        aggregate = {
            "feature": None,
            "align": None,
            "inspection": None,
            "evaluation": None,
            "inspection_purpose": None,
        }
        page.load_all(aggregate)

        # Failure tab stays empty — no crash
        assert not page._failure_tab._summary_card.isVisible()

    def test_existing_tabs_still_render(self, qtbot):
        """Regression: existing tabs still work correctly."""
        page = ResultPage()
        qtbot.addWidget(page)
        page.show()

        tab_names = [
            page._tab_widget.tabText(i)
            for i in range(page._tab_widget.count())
        ]
        assert "요약" in tab_names
        assert "Feature 분석" in tab_names
        assert "Align 결과" in tab_names
        assert "Inspection 결과" in tab_names
        assert "Feasibility" in tab_names
        assert "Failure 분석" in tab_names


# Required for QWidget tests
from PyQt6.QtCore import Qt
