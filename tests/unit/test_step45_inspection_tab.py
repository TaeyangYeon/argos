"""
Step 45 — Inspection 결과 카드 및 파라미터 테이블 테스트.

InspectionTab의 load_data 동작, 점수 색상, 비교 테이블, 오버레이,
파라미터 테이블, 라이브러리 매핑 등을 검증한다.
"""

import types

import numpy as np
import pytest

from ui.pages.inspection_tab import InspectionTab, _score_color, _ndarray_to_qpixmap


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_opt_result(
    score=75.0,
    ok_rate=0.9,
    ng_rate=0.85,
    margin=15.0,
    is_warning=False,
    n_candidates=3,
    engine_name="Blob Inspection",
    design_doc=None,
    library_mapping=None,
    overlay_image=None,
):
    best = types.SimpleNamespace(
        engine_name=engine_name,
        engine_class=object,
        priority=0.8,
        rationale="Test rationale",
        source="rule_based",
    )
    if design_doc is not None:
        best.design_doc = design_doc
    if library_mapping is not None:
        best.library_mapping = library_mapping
    if overlay_image is not None:
        best.overlay_image = overlay_image

    best_eval = types.SimpleNamespace(
        final_score=score,
        ok_pass_rate=ok_rate,
        ng_detect_rate=ng_rate,
        margin=margin,
        is_margin_warning=is_warning,
        best_strategy=engine_name,
        fp_images=[],
        fn_images=[],
    )

    all_results = []
    for i in range(n_candidates):
        c = types.SimpleNamespace(
            engine_name=f"Engine_{i}",
            source="rule_based",
        )
        e = types.SimpleNamespace(
            final_score=max(0, score - i * 10),
            ok_pass_rate=max(0, ok_rate - i * 0.1),
            ng_detect_rate=max(0, ng_rate - i * 0.05),
            margin=margin - i * 5,
            is_margin_warning=i > 0,
        )
        all_results.append((c, e))

    if n_candidates > 0:
        all_results[0] = (best, best_eval)

    return types.SimpleNamespace(
        best_candidate=best,
        best_evaluation=best_eval,
        all_results=all_results,
        optimization_log=["[OK] Test: score=75.0"],
    )


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestInspectionTabLoadData:
    """load_data 호출 시 UI 상태 검증."""

    def test_load_data_none_shows_empty(self, qtbot):
        tab = InspectionTab()
        qtbot.addWidget(tab)
        tab.show()
        tab.load_data(None)

        assert tab._content_label.isVisible()
        assert "Inspection 결과 없음" in tab._content_label.text()
        assert not tab._summary_card.isVisible()
        assert not tab._detail_tabs.isVisible()

    def test_load_data_full_shows_summary(self, qtbot):
        tab = InspectionTab()
        qtbot.addWidget(tab)
        tab.show()
        tab.load_data(_make_opt_result())

        assert not tab._content_label.isVisible()
        assert tab._summary_card.isVisible()
        assert tab._detail_tabs.isVisible()
        assert "Blob Inspection" in tab._algo_name_label.text()

    def test_score_display_value(self, qtbot):
        tab = InspectionTab()
        qtbot.addWidget(tab)
        tab.load_data(_make_opt_result(score=82.5))

        assert "82.5" in tab._score_label.text()

    def test_ok_ng_rate_display(self, qtbot):
        tab = InspectionTab()
        qtbot.addWidget(tab)
        tab.load_data(_make_opt_result(ok_rate=0.95, ng_rate=0.88))

        assert "95.0" in tab._ok_rate_label.text()
        assert "88.0" in tab._ng_rate_label.text()

    def test_margin_display(self, qtbot):
        tab = InspectionTab()
        qtbot.addWidget(tab)
        tab.load_data(_make_opt_result(margin=22.5))

        assert "22.5" in tab._margin_label.text()


class TestMarginWarning:
    """분리 마진 경고 표시 검증."""

    def test_margin_warning_visible_when_flagged(self, qtbot):
        tab = InspectionTab()
        qtbot.addWidget(tab)
        tab.show()
        tab.load_data(_make_opt_result(margin=10.0, is_warning=True))

        assert tab._margin_warning.isVisible()
        assert "10.0" in tab._margin_warning.text()

    def test_margin_warning_hidden_when_ok(self, qtbot):
        tab = InspectionTab()
        qtbot.addWidget(tab)
        tab.show()
        tab.load_data(_make_opt_result(margin=20.0, is_warning=False))

        assert not tab._margin_warning.isVisible()


class TestScoreColor:
    """점수 색상 임계값 검증."""

    def test_green_above_70(self):
        assert _score_color(75.0) == "#4CAF50"

    def test_green_at_70(self):
        assert _score_color(70.0) == "#4CAF50"

    def test_yellow_above_50(self):
        assert _score_color(55.0) == "#FF9800"

    def test_yellow_at_50(self):
        assert _score_color(50.0) == "#FF9800"

    def test_red_below_50(self):
        assert _score_color(40.0) == "#E53935"

    def test_red_at_zero(self):
        assert _score_color(0.0) == "#E53935"


class TestComparisonTable:
    """Candidate 비교 테이블 검증."""

    def test_comparison_table_row_count(self, qtbot):
        tab = InspectionTab()
        qtbot.addWidget(tab)
        tab.show()
        tab.load_data(_make_opt_result(n_candidates=4))

        assert tab._comp_table.rowCount() == 4
        assert not tab._comp_table.isHidden()

    def test_comparison_placeholder_when_empty(self, qtbot):
        tab = InspectionTab()
        qtbot.addWidget(tab)
        tab.show()
        result = _make_opt_result(n_candidates=0)
        result.all_results = []
        tab.load_data(result)

        assert not tab._comp_placeholder.isHidden()
        assert tab._comp_table.isHidden()

    def test_best_candidate_highlighted(self, qtbot):
        tab = InspectionTab()
        qtbot.addWidget(tab)
        tab.load_data(_make_opt_result(n_candidates=3))

        first_item = tab._comp_table.item(0, 0)
        assert first_item is not None
        bg_color = first_item.background().color().name()
        assert bg_color == "#1a3a6e"


class TestOverlay:
    """오버레이 이미지 뷰어 검증."""

    def test_overlay_placeholder_when_none(self, qtbot):
        tab = InspectionTab()
        qtbot.addWidget(tab)
        tab.load_data(_make_opt_result())

        assert tab._overlay_label.text() == "오버레이 없음"
        assert tab._overlay_pixmap is None

    def test_overlay_from_ndarray(self, qtbot):
        tab = InspectionTab()
        qtbot.addWidget(tab)
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        img[:, :, 2] = 255
        tab.load_data(_make_opt_result(overlay_image=img))

        assert tab._overlay_pixmap is not None
        assert not tab._overlay_pixmap.isNull()

    def test_ndarray_to_qpixmap_grayscale(self):
        gray = np.ones((50, 60), dtype=np.uint8) * 128
        pm = _ndarray_to_qpixmap(gray)
        assert pm is not None
        assert pm.width() == 60
        assert pm.height() == 50

    def test_ndarray_to_qpixmap_none(self):
        assert _ndarray_to_qpixmap(None) is None

    def test_ndarray_to_qpixmap_empty(self):
        assert _ndarray_to_qpixmap(np.array([])) is None


class TestParamTable:
    """파라미터 테이블 검증."""

    def test_param_shows_rationale_when_no_design_doc(self, qtbot):
        tab = InspectionTab()
        qtbot.addWidget(tab)
        tab.show()
        tab.load_data(_make_opt_result())

        assert not tab._param_placeholder.isHidden()
        assert "Test rationale" in tab._param_placeholder.text()

    def test_param_table_from_design_doc(self, qtbot):
        tab = InspectionTab()
        qtbot.addWidget(tab)
        tab.show()
        doc = {
            "layout": {"description": "Test layout", "area_range": [100, 5000]},
            "parameters": {"threshold": 30, "min_area": 50},
        }
        tab.load_data(_make_opt_result(design_doc=doc))

        assert not tab._param_table.isHidden()
        assert tab._param_table.rowCount() > 0
        # layout header + 2 data + parameters header + 2 data = 6
        assert tab._param_table.rowCount() == 6

    def test_param_table_section_labels(self, qtbot):
        tab = InspectionTab()
        qtbot.addWidget(tab)
        doc = {
            "배치구조": {"검사_유형": "차분 기반"},
            "결과계산": {"방법": "점수 계산"},
        }
        tab.load_data(_make_opt_result(design_doc=doc))

        first_item = tab._param_table.item(0, 0)
        assert first_item is not None
        assert "배치 구조" in first_item.text()


class TestLibraryMapping:
    """라이브러리 매핑 테이블 검증."""

    def test_lib_placeholder_when_no_mapping(self, qtbot):
        tab = InspectionTab()
        qtbot.addWidget(tab)
        tab.show()
        tab.load_data(_make_opt_result())

        assert not tab._lib_placeholder.isHidden()
        assert tab._lib_table.isHidden()

    def test_vendor_keyed_mapping(self, qtbot):
        tab = InspectionTab()
        qtbot.addWidget(tab)
        tab.show()
        mapping = {
            "keyence": {
                "description": "BlobMeasure",
                "area_min": "Min Area = 100",
            },
            "cognex": {
                "description": "CogBlobTool",
                "area_min": "MinBlobArea = 100",
            },
        }
        tab.load_data(_make_opt_result(library_mapping=mapping))

        assert not tab._lib_table.isHidden()
        assert tab._lib_table.rowCount() > 0
        # "area_min" should be a row (description excluded)
        assert tab._lib_table.rowCount() == 1

    def test_concept_table_mapping(self, qtbot):
        tab = InspectionTab()
        qtbot.addWidget(tab)
        tab.show()
        mapping = {
            "concept_table": {
                "Search Length": {
                    "Keyence": "탐색 폭 = 40px",
                    "Cognex": "SearchLength = 40",
                    "Halcon": "SearchExtent = 40",
                    "MIL": "M_SEARCH_LENGTH = 40",
                },
                "Caliper Count": {
                    "Keyence": "Caliper 수 = 12",
                    "Cognex": "NumCalipers = 12",
                    "Halcon": "NumMeasureObjects = 12",
                    "MIL": "M_CALIPER_COUNT = 12",
                },
            }
        }
        tab.load_data(_make_opt_result(library_mapping=mapping))

        assert not tab._lib_table.isHidden()
        assert tab._lib_table.rowCount() == 2
        assert tab._lib_table.columnCount() == 5  # concept + 4 vendors

    def test_pattern_concept_mapping(self, qtbot):
        """Pattern inspector uses flat concept-keyed format."""
        tab = InspectionTab()
        qtbot.addWidget(tab)
        tab.show()
        mapping = {
            "Difference Map": {
                "Keyence": "차분 검사",
                "Cognex": "Difference Image",
                "Halcon": "DiffImage",
                "MIL": "MimArith",
            },
            "Threshold": {
                "Keyence": "2진화 임계값",
                "Cognex": "Threshold",
                "Halcon": "Threshold",
                "MIL": "M_THRESHOLD",
            },
        }
        tab.load_data(_make_opt_result(library_mapping=mapping))

        assert not tab._lib_table.isHidden()
        assert tab._lib_table.rowCount() == 2


class TestEdgeCases:
    """엣지 케이스 검증."""

    def test_load_data_empty_namespace(self, qtbot):
        """Result with no best_candidate / best_evaluation shows empty state."""
        tab = InspectionTab()
        qtbot.addWidget(tab)
        tab.show()
        result = types.SimpleNamespace()
        tab.load_data(result)

        assert tab._content_label.isVisible()

    def test_reload_replaces_previous(self, qtbot):
        """Calling load_data twice replaces previous data."""
        tab = InspectionTab()
        qtbot.addWidget(tab)
        tab.load_data(_make_opt_result(engine_name="First"))
        assert "First" in tab._algo_name_label.text()

        tab.load_data(_make_opt_result(engine_name="Second"))
        assert "Second" in tab._algo_name_label.text()

    def test_reload_none_after_data(self, qtbot):
        """Loading None after data restores empty state."""
        tab = InspectionTab()
        qtbot.addWidget(tab)
        tab.show()
        tab.load_data(_make_opt_result())
        assert tab._summary_card.isVisible()

        tab.load_data(None)
        assert not tab._summary_card.isVisible()
        assert tab._content_label.isVisible()
