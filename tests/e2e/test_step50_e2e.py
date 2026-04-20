"""
E2E 워크플로우 테스트 — Step 50.

4가지 시나리오:
1. Full Inspection Workflow (해피 패스)
2. Align-Only Workflow
3. Export Workflow
4. Session Reset / New Project
"""

import sys
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import numpy as np
import pytest

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from core.image_store import ImageStore, ImageType
from core.models import (
    ROIConfig, InspectionPurpose, AlignResult,
    OptimizationResult, EvaluationResult, FailureAnalysisResult,
    FeasibilityResult,
)
from core.analyzers.feature_analyzer import FullFeatureAnalysis


# ─── QApplication fixture ────────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


# ─── Helper: 더미 이미지 파일 생성 ────────────────────────────────────────────

def _create_test_image(tmp_path: Path, name: str = "test.png") -> str:
    """테스트용 더미 PNG 파일 생성."""
    import cv2
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[:] = (128, 128, 128)
    filepath = str(tmp_path / name)
    cv2.imwrite(filepath, img)
    return filepath


def _make_feature_result():
    """FullFeatureAnalysis 더미 결과 생성."""
    hist = MagicMock()
    hist.mean_gray = 128.0
    hist.std_gray = 30.0
    hist.dynamic_range = 200
    hist.separation_score = 50.0

    noise = MagicMock()
    noise.noise_level = "Low"

    edge = MagicMock()
    edge.mean_edge_strength = 45.0
    edge.edge_density = 0.12
    edge.is_suitable_for_caliper = True

    shape = MagicMock()
    shape.blob_count = 3
    shape.has_circular_structure = False

    result = MagicMock(spec=FullFeatureAnalysis)
    result.histogram = hist
    result.noise = noise
    result.edge = edge
    result.shape = shape
    result.ai_summary = "테스트 AI 요약"
    result.preprocessing_recommendations = ["가우시안 블러 적용"]
    return result


def _make_align_result():
    """AlignResult 더미 결과."""
    return AlignResult(
        success=True,
        strategy_name="pattern",
        score=0.95,
    )


def _make_eval_result():
    """EvaluationResult 더미."""
    return EvaluationResult(
        best_strategy="blob",
        ok_pass_rate=0.9,
        ng_detect_rate=0.85,
        final_score=87.5,
        margin=10.0,
        is_margin_warning=False,
    )


def _make_optimization_result():
    """OptimizationResult 더미."""
    eval_result = _make_eval_result()
    best_candidate = MagicMock()
    best_candidate.engine_name = "blob"
    return OptimizationResult(
        best_candidate=best_candidate,
        best_evaluation=eval_result,
    )


def _make_aggregate():
    """분석 완료 aggregate dict 생성."""
    return {
        "feature": _make_feature_result(),
        "align": _make_align_result(),
        "inspection": _make_optimization_result(),
        "evaluation": {
            "failure_result": FailureAnalysisResult(
                fp_overlay_paths=[], fn_overlay_paths=[],
                cause_summary="없음", improvement_directions=[],
                fp_count=0, fn_count=0,
            ),
            "feasibility_result": FeasibilityResult(
                rule_based_sufficient=True,
                recommended_approach="Rule-based",
                reasoning="테스트",
            ),
        },
        "inspection_purpose": InspectionPurpose(
            inspection_type="결함검출",
            description="테스트 검사 목적입니다. 최소 10자 이상 입력해야 합니다.",
            target_feature="스크래치",
        ),
    }


# ─── Scenario 1: Full Inspection Workflow ─────────────────────────────────────

class TestFullInspectionWorkflow:
    """전체 검사 워크플로우 E2E 테스트 (해피 패스)."""

    def test_full_workflow_loads_all_tabs(self, tmp_path):
        """이미지 업로드 → ROI → 목적 → 분석 → 결과 탭 6개 모두 로딩."""
        from ui.main_window import MainWindow

        window = MainWindow()
        image_store = window.image_store

        # 1. 이미지 업로드
        for name, img_type in [
            ("align.png", ImageType.ALIGN_OK),
            ("ok.png", ImageType.INSPECTION_OK),
            ("ng.png", ImageType.INSPECTION_NG),
        ]:
            filepath = _create_test_image(tmp_path, name)
            image_store.add(filepath, img_type)

        assert image_store.count() == 3

        # 2. ROI 설정
        roi = ROIConfig(x=10, y=10, width=80, height=80)
        window._on_roi_confirmed(roi)
        assert window._roi_config is not None

        # 3. 검사 목적 설정
        purpose = InspectionPurpose(
            inspection_type="결함검출",
            description="표면 스크래치 검출 테스트입니다. 최소 글자 충족.",
            target_feature="스크래치",
        )
        window._on_purpose_confirmed(purpose)
        assert window._inspection_purpose is not None

        # 4. 분석 완료 시뮬레이션 (워커 대신 직접 호출)
        aggregate = _make_aggregate()
        result_page = window._pages[
            __import__("ui.components.sidebar", fromlist=["PageID"]).PageID.RESULTS
        ]
        result_page.load_all(aggregate)

        # 5. 결과 탭 6개 확인
        tab_widget = result_page._tab_widget
        assert tab_widget.count() == 6

        # 탭이 표시되는지 확인
        assert tab_widget.isVisible() or not result_page._empty_label.isVisible()

        window.close()

    def test_dashboard_stat_cards_update(self, tmp_path):
        """이미지 업로드 후 대시보드 StatCard 수치 갱신."""
        from ui.main_window import MainWindow

        window = MainWindow()
        image_store = window.image_store

        # 이미지 추가
        filepath = _create_test_image(tmp_path, "ok1.png")
        image_store.add(filepath, ImageType.INSPECTION_OK)

        # 대시보드 갱신
        from ui.components.sidebar import PageID
        dashboard = window._pages[PageID.DASHBOARD]
        dashboard.refresh()

        assert dashboard._inspection_ok_card is not None
        assert dashboard._total_card is not None

        window.close()


# ─── Scenario 2: Align-Only Workflow ──────────────────────────────────────────

class TestAlignOnlyWorkflow:
    """위치정렬(Align) 전용 워크플로우."""

    def test_align_only_skips_inspection_gracefully(self, tmp_path):
        """위치정렬 타입 선택 시 Inspection 스킵, Align 결과 표시."""
        from ui.main_window import MainWindow
        from ui.components.sidebar import PageID

        window = MainWindow()
        image_store = window.image_store

        # Align OK 이미지만 업로드
        filepath = _create_test_image(tmp_path, "align1.png")
        image_store.add(filepath, ImageType.ALIGN_OK)

        # ROI + 목적 설정
        roi = ROIConfig(x=5, y=5, width=90, height=90)
        purpose = InspectionPurpose(
            inspection_type="위치정렬",
            description="부품 중심 정렬 테스트입니다. 최소 글자 충족합니다.",
            target_feature="부품 위치",
        )
        window._on_roi_confirmed(roi)
        window._on_purpose_confirmed(purpose)

        # 분석 결과 — inspection=None
        aggregate = {
            "feature": _make_feature_result(),
            "align": _make_align_result(),
            "inspection": None,
            "evaluation": None,
            "inspection_purpose": purpose,
        }

        result_page = window._pages[PageID.RESULTS]
        result_page.load_all(aggregate)

        # Align 탭에 결과 로딩 확인
        assert result_page._align_tab is not None

        window.close()

    def test_preflight_align_only_needs_align_images(self, tmp_path):
        """위치정렬: ALIGN_OK만 있으면 preflight 통과."""
        from ui.pages.analysis_page import AnalysisPage

        image_store = ImageStore()
        filepath = _create_test_image(tmp_path, "align.png")
        image_store.add(filepath, ImageType.ALIGN_OK)

        page = AnalysisPage(image_store)
        page.roi_config = ROIConfig(x=0, y=0, width=50, height=50)
        page.inspection_purpose = InspectionPurpose(
            inspection_type="위치정렬",
            description="위치정렬 테스트 최소 글자 이상 입력합니다.",
            target_feature="위치",
        )

        result = page._validate_images_for_vision_type(
            align_count=1, ok_count=0, ng_count=0
        )
        assert result["overall_valid"] is True


# ─── Scenario 3: Export Workflow ──────────────────────────────────────────────

class TestExportWorkflow:
    """내보내기 기능 E2E 테스트."""

    def test_json_export_creates_file(self, tmp_path):
        """JSON 내보내기 시 파일 생성 확인."""
        from core.export.json_exporter import ArgosJSONExporter

        aggregate = _make_aggregate()
        exporter = ArgosJSONExporter()
        exporter.export(aggregate, tmp_path)

        json_files = list(tmp_path.glob("*.json"))
        assert len(json_files) >= 1

    def test_pdf_export_creates_file(self, tmp_path):
        """PDF 내보내기 시 파일 생성 확인."""
        from core.export.pdf_exporter import ArgosPDFExporter

        aggregate = _make_aggregate()
        exporter = ArgosPDFExporter()
        exporter.export(aggregate, tmp_path)

        pdf_files = list(tmp_path.glob("*.pdf"))
        assert len(pdf_files) >= 1

    def test_export_dialog_checkboxes_have_tooltips(self):
        """Export 다이얼로그 체크박스에 툴팁 존재."""
        from ui.dialogs.export_dialog import ExportDialog

        dialog = ExportDialog()
        assert dialog._json_checkbox.toolTip() != ""
        assert dialog._pdf_checkbox.toolTip() != ""
        assert dialog._image_checkbox.toolTip() != ""


# ─── Scenario 4: Session Reset / New Project ─────────────────────────────────

class TestSessionReset:
    """세션 초기화 / 새 프로젝트 시작."""

    def test_session_reset_clears_all_state(self, tmp_path):
        """새 프로젝트 시작 시 모든 상태 초기화."""
        from ui.main_window import MainWindow
        from ui.components.sidebar import PageID

        window = MainWindow()
        image_store = window.image_store

        # 이미지 + ROI + 목적 설정
        filepath = _create_test_image(tmp_path, "test.png")
        image_store.add(filepath, ImageType.INSPECTION_OK)
        window._on_roi_confirmed(ROIConfig(x=0, y=0, width=50, height=50))
        window._on_purpose_confirmed(InspectionPurpose(
            inspection_type="결함검출",
            description="테스트 목적 설명 충분히 길게 입력합니다.",
            target_feature="홀",
        ))

        assert window._roi_config is not None
        assert window._inspection_purpose is not None

        # 세션 리셋 시뮬레이션
        dashboard = window._pages[PageID.DASHBOARD]
        dashboard._image_store.clear()
        dashboard._has_roi = False
        dashboard._has_purpose = False
        dashboard._has_results = False
        dashboard._purpose_type = ""
        if dashboard._workflow_indicator:
            dashboard._workflow_indicator.reset()
        dashboard.refresh()
        dashboard.session_reset.emit()

        # MainWindow 상태 초기화 확인
        assert window._roi_config is None
        assert window._inspection_purpose is None

        # 이미지 스토어 초기화 확인
        assert image_store.count() == 0

        # 워크플로우 단계 모두 pending 확인
        indicator = dashboard._workflow_indicator
        for step in indicator._steps:
            assert step.get_state() == "pending"

        window.close()

    def test_reset_dashboard_workflow_indicator_back_to_step1(self, tmp_path):
        """리셋 후 워크플로우 인디케이터 모든 단계가 pending."""
        from ui.components.workflow_indicator import WorkflowIndicator

        indicator = WorkflowIndicator()

        # 일부 완료 상태 설정
        indicator._steps[0].set_state("done")
        indicator._steps[1].set_state("done")
        indicator._steps[2].set_state("active")

        # 리셋
        indicator.reset()

        for step in indicator._steps:
            assert step.get_state() == "pending"


# ─── Additional: UI Polish Verification ──────────────────────────────────────

class TestUIPolish:
    """UI 품질 개선 검증."""

    def test_version_in_window_title(self):
        """MainWindow 타이틀바에 버전 정보 포함."""
        from ui.main_window import MainWindow
        from core import __version__

        window = MainWindow()
        assert __version__ in window.windowTitle()
        window.close()

    def test_result_page_empty_state_visible_initially(self):
        """ResultPage 초기 상태에서 빈 상태 메시지 표시, 탭 숨김."""
        from ui.pages.result_page import ResultPage

        page = ResultPage()
        assert page._empty_label is not None
        # 초기 상태: empty_label은 숨기지 않았고, tab_widget은 명시적으로 숨겨짐
        assert not page._empty_label.isHidden()
        assert page._tab_widget.isHidden()

    def test_result_page_tabs_visible_after_load(self):
        """결과 로딩 후 탭이 보이고 빈 상태 숨김."""
        from ui.pages.result_page import ResultPage

        page = ResultPage()
        aggregate = _make_aggregate()
        page.load_all(aggregate)

        assert not page._tab_widget.isHidden()
        assert page._empty_label.isHidden()

    def test_workflow_indicator_tooltips(self):
        """워크플로우 단계에 툴팁 존재."""
        from ui.components.workflow_indicator import WorkflowIndicator

        indicator = WorkflowIndicator()
        for step in indicator._steps:
            assert step.toolTip() != ""

    def test_settings_page_slider_tooltips(self):
        """설정 페이지 슬라이더에 툴팁 존재."""
        from ui.pages.settings_page import SettingsPage

        page = SettingsPage()
        assert page._threshold_slider.toolTip() != ""
        assert page._ok_weight_slider.toolTip() != ""
        assert page._ng_weight_slider.toolTip() != ""
        assert page._margin_slider.toolTip() != ""

    def test_toolbar_tooltips(self):
        """툴바 버튼에 툴팁 존재."""
        from core.key_manager import KeyManager
        from core.providers.provider_factory import ProviderFactory
        from ui.components.toolbar import ArgosToolbar

        toolbar = ArgosToolbar(KeyManager(), ProviderFactory())
        assert toolbar._api_button.toolTip() != ""
        assert toolbar._status_widget.toolTip() != ""

    def test_result_tab_tooltips(self):
        """결과 뷰어 탭에 툴팁 존재."""
        from ui.pages.result_page import ResultPage

        page = ResultPage()
        for i in range(page._tab_widget.count()):
            assert page._tab_widget.tabToolTip(i) != ""

    def test_loading_spinner_start_stop(self):
        """로딩 스피너 시작/정지."""
        from ui.widgets.loading_spinner import LoadingSpinner

        spinner = LoadingSpinner()
        spinner.start()
        assert spinner.isVisible()
        spinner.stop()
        assert not spinner.isVisible()

    def test_empty_state_widget(self):
        """빈 상태 위젯 생성."""
        from ui.widgets.empty_state import EmptyStateWidget

        widget = EmptyStateWidget("📭", "테스트 메시지")
        assert widget._message_label.text() == "테스트 메시지"

        widget.set_message("변경됨")
        assert widget._message_label.text() == "변경됨"

    def test_theme_module_exports(self):
        """theme 모듈의 디자인 토큰 접근."""
        from ui.theme import Colors, Fonts, Spacing, FontSize, Radius, Tooltips

        assert Colors.ACCENT == "#1E88E5"
        assert Spacing.CARD_PADDING == 16
        assert FontSize.PAGE_TITLE == 20
        assert Radius.LG == 8
        assert Tooltips.THRESHOLD != ""
