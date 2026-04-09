"""
Step 25 분석 실행 화면 UI 구성 요소 테스트
- AnalysisStepWidget, AnalysisProgressPanel
- LogViewer
- AnalysisWorker
- AnalysisPage
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QTextCursor

from core.image_store import ImageStore, ImageType, ImageMeta
from core.models import ROIConfig, InspectionPurpose
from core.analyzers.feature_analyzer import FullFeatureAnalysis
from ui.components.progress_steps import (
    AnalysisStep, StepStatus, AnalysisStepWidget, AnalysisProgressPanel
)
from ui.components.log_viewer import LogViewer
from ui.workers.analysis_worker import AnalysisWorker
from ui.pages.analysis_page import AnalysisPage


class TestProgressSteps:
    """AnalysisStepWidget and AnalysisProgressPanel 테스트"""
    
    def test_progress_panel_created(self, qtbot):
        """AnalysisProgressPanel 생성 테스트"""
        panel = AnalysisProgressPanel()
        qtbot.addWidget(panel)
        assert panel is not None
        assert len(panel.step_widgets) == 4

    def test_progress_panel_reset(self, qtbot):
        """reset_all() 테스트 - 모든 스텝을 PENDING으로 설정"""
        panel = AnalysisProgressPanel()
        qtbot.addWidget(panel)
        
        # 일부 스텝을 DONE으로 설정
        panel.set_step_status(AnalysisStep.FEATURE_ANALYSIS, StepStatus.DONE, 2.5)
        panel.set_step_status(AnalysisStep.ALIGN_DESIGN, StepStatus.RUNNING)
        
        # reset 실행
        panel.reset_all()
        
        # 모든 스텝이 PENDING 상태인지 확인
        for step_widget in panel.step_widgets.values():
            assert step_widget.status == StepStatus.PENDING
        
        # 전체 진행률이 0%인지 확인
        assert panel.get_overall_progress() == 0

    def test_progress_panel_one_done(self, qtbot):
        """하나의 스텝이 완료된 경우 진행률 테스트"""
        panel = AnalysisProgressPanel()
        qtbot.addWidget(panel)
        
        panel.set_step_status(AnalysisStep.FEATURE_ANALYSIS, StepStatus.DONE, 3.2)
        
        # 1/4 완료 = 25%
        assert panel.get_overall_progress() == 25

    def test_progress_panel_all_done(self, qtbot):
        """모든 스텝이 완료된 경우 진행률 테스트"""
        panel = AnalysisProgressPanel()
        qtbot.addWidget(panel)
        
        panel.set_step_status(AnalysisStep.FEATURE_ANALYSIS, StepStatus.DONE, 3.2)
        panel.set_step_status(AnalysisStep.ALIGN_DESIGN, StepStatus.DONE, 1.5)
        panel.set_step_status(AnalysisStep.INSPECTION_DESIGN, StepStatus.DONE, 2.1)
        panel.set_step_status(AnalysisStep.EVALUATION, StepStatus.DONE, 0.8)
        
        # 4/4 완료 = 100%
        assert panel.get_overall_progress() == 100

    def test_step_widget_status_change(self, qtbot):
        """AnalysisStepWidget 상태 변경 테스트"""
        widget = AnalysisStepWidget(AnalysisStep.FEATURE_ANALYSIS)
        qtbot.addWidget(widget)
        
        # 모든 상태를 순환하며 오류 없이 설정되는지 확인
        for status in StepStatus:
            if status == StepStatus.RUNNING:
                widget.set_status(status, None)
                assert widget.status == status
            else:
                widget.set_status(status, 2.5 if status == StepStatus.DONE else None)
                assert widget.status == status


class TestLogViewer:
    """LogViewer 테스트"""
    
    def test_log_viewer_append_info(self, qtbot):
        """INFO 로그 추가 테스트"""
        viewer = LogViewer()
        qtbot.addWidget(viewer)
        
        viewer.append_info("Test info message")
        
        text = viewer.toPlainText()
        assert "INFO" in text
        assert "Test info message" in text

    def test_log_viewer_append_warning(self, qtbot):
        """WARNING 로그 추가 테스트"""
        viewer = LogViewer()
        qtbot.addWidget(viewer)
        
        viewer.append_warning("Test warning message")
        
        text = viewer.toPlainText()
        assert "WARNING" in text
        assert "Test warning message" in text

    def test_log_viewer_append_error(self, qtbot):
        """ERROR 로그 추가 테스트"""
        viewer = LogViewer()
        qtbot.addWidget(viewer)
        
        viewer.append_error("Test error message")
        
        text = viewer.toPlainText()
        assert "ERROR" in text
        assert "Test error message" in text

    def test_log_viewer_clear(self, qtbot):
        """로그 클리어 테스트"""
        viewer = LogViewer()
        qtbot.addWidget(viewer)
        
        viewer.append_info("Test message")
        assert viewer.toPlainText() != ""
        
        viewer.clear_log()
        assert viewer.toPlainText() == ""

    def test_log_viewer_max_lines(self, qtbot):
        """최대 라인 수 제한 테스트 (500라인)"""
        viewer = LogViewer()
        qtbot.addWidget(viewer)
        
        # 600개 라인 추가
        for i in range(600):
            viewer.append_info(f"Line {i}")
        
        # 라인 수가 500 이하인지 확인
        line_count = viewer.document().blockCount()
        assert line_count <= 500


class TestAnalysisWorker:
    """AnalysisWorker 테스트"""
    
    @patch('ui.workers.analysis_worker.FeatureAnalyzer')
    def test_analysis_worker_signals(self, mock_analyzer_class):
        """AnalysisWorker 시그널 발생 테스트"""
        mock_analyzer = Mock()
        mock_feature_result = Mock(spec=FullFeatureAnalysis)
        mock_analyzer.analyze_full.return_value = mock_feature_result
        mock_analyzer_class.return_value = mock_analyzer
        
        image_store = ImageStore()
        worker = AnalysisWorker(image_store)
        
        # 시그널 연결 확인
        assert hasattr(worker, 'step_started')
        assert hasattr(worker, 'step_finished')
        assert hasattr(worker, 'step_failed')
        assert hasattr(worker, 'log_message')
        assert hasattr(worker, 'analysis_complete')
        assert hasattr(worker, 'analysis_failed')

    def test_analysis_worker_cancel(self):
        """AnalysisWorker 취소 기능 테스트"""
        image_store = ImageStore()
        worker = AnalysisWorker(image_store)
        
        assert not worker.is_cancelled()
        
        worker.cancel()
        assert worker.is_cancelled()


class TestAnalysisPage:
    """AnalysisPage 테스트"""
    
    def test_analysis_page_created(self, qtbot):
        """AnalysisPage 생성 테스트"""
        image_store = ImageStore()
        page = AnalysisPage(image_store=image_store)
        qtbot.addWidget(page)
        
        assert page is not None
        assert page.page_id.value == "analysis"
        assert page.title == "분석 실행"

    def test_start_button_disabled_no_images(self, qtbot):
        """이미지가 없을 때 시작 버튼 비활성화 테스트"""
        image_store = ImageStore()
        page = AnalysisPage(image_store=image_store)
        qtbot.addWidget(page)
        
        # 빈 이미지 스토어로 pre-flight 체크 업데이트
        page.update_preflight(image_store, None, None)
        
        assert not page.start_button.isEnabled()

    def test_start_button_disabled_no_purpose(self, qtbot, make_image_meta):
        """이미지는 있지만 목적이 없을 때 시작 버튼 비활성화 테스트"""
        image_store = ImageStore()
        
        # 이미지 추가
        image_meta = make_image_meta(ImageType.ALIGN_OK, "test.jpg")
        image_store.add_image(image_meta)
        
        page = AnalysisPage(image_store=image_store)
        qtbot.addWidget(page)
        
        # ROI 설정
        roi_config = ROIConfig(x=10, y=10, width=100, height=100)
        
        # 목적 없이 pre-flight 체크 업데이트
        page.update_preflight(image_store, roi_config, None)
        
        assert not page.start_button.isEnabled()

    def test_start_button_enabled_all_ready(self, qtbot, make_image_meta):
        """모든 조건이 충족될 때 시작 버튼 활성화 테스트"""
        image_store = ImageStore()
        
        # 모든 타입의 이미지 추가
        for img_type in [ImageType.ALIGN_OK, ImageType.INSPECTION_OK, ImageType.INSPECTION_NG]:
            image_meta = make_image_meta(img_type, f"test_{img_type.value}.jpg")
            image_store.add_image(image_meta)
        
        page = AnalysisPage(image_store=image_store)
        qtbot.addWidget(page)
        
        # ROI 및 목적 설정
        roi_config = ROIConfig(x=10, y=10, width=100, height=100)
        purpose = InspectionPurpose(inspection_type="외관 검사", target_feature="스크래치")
        
        # 모든 조건 충족 상태로 pre-flight 체크 업데이트
        page.update_preflight(image_store, roi_config, purpose)
        
        assert page.start_button.isEnabled()

    def test_cancel_button_disabled_initially(self, qtbot):
        """초기 상태에서 중단 버튼 비활성화 테스트"""
        image_store = ImageStore()
        page = AnalysisPage(image_store=image_store)
        qtbot.addWidget(page)
        
        assert not page.cancel_button.isEnabled()

    def test_result_button_disabled_initially(self, qtbot):
        """초기 상태에서 결과 보기 버튼 비활성화 테스트"""
        image_store = ImageStore()
        page = AnalysisPage(image_store=image_store)
        qtbot.addWidget(page)
        
        assert not page.result_button.isEnabled()

    def test_update_preflight_reflects_image_store(self, qtbot, make_image_meta):
        """update_preflight가 이미지 스토어 상태를 반영하는지 테스트"""
        image_store = ImageStore()
        page = AnalysisPage(image_store=image_store)
        qtbot.addWidget(page)
        
        # 초기 상태 - 모든 항목이 ❌
        page.update_preflight(image_store, None, None)
        
        # ALIGN 이미지 3장 추가
        for i in range(3):
            image_meta = make_image_meta(ImageType.ALIGN_OK, f"align_{i}.jpg")
            image_store.add_image(image_meta)
        
        # ROI 설정
        roi_config = ROIConfig(x=10, y=10, width=100, height=100)
        
        # pre-flight 업데이트
        page.update_preflight(image_store, roi_config, None)
        
        # ALIGN 이미지 항목이 ✅로 변경되었는지 확인
        align_label_text = page.preflight_rows[0].text()
        assert "✅" in align_label_text
        assert "3장" in align_label_text

    def test_set_roi_config(self, qtbot):
        """ROI 설정 메서드 테스트"""
        image_store = ImageStore()
        page = AnalysisPage(image_store=image_store)
        qtbot.addWidget(page)
        
        roi_config = ROIConfig(x=10, y=10, width=100, height=100)
        page.set_roi_config(roi_config)
        
        assert page.roi_config == roi_config

    def test_set_inspection_purpose(self, qtbot):
        """검사 목적 설정 메서드 테스트"""
        image_store = ImageStore()
        page = AnalysisPage(image_store=image_store)
        qtbot.addWidget(page)
        
        purpose = InspectionPurpose(inspection_type="외관 검사", target_feature="스크래치")
        page.set_inspection_purpose(purpose)
        
        assert page.inspection_purpose == purpose

    def test_get_last_result_none_initially(self, qtbot):
        """초기 상태에서 마지막 결과가 None인지 테스트"""
        image_store = ImageStore()
        page = AnalysisPage(image_store=image_store)
        qtbot.addWidget(page)
        
        assert page.get_last_result() is None