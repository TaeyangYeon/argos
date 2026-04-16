"""
분석 실행 페이지
Pre-flight 체크, 진행 상황 표시, 로그 뷰어가 포함된 분석 실행 화면
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QGroupBox, QLabel, 
    QPushButton, QSplitter, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from core.image_store import ImageStore, ImageType
from core.models import ROIConfig, InspectionPurpose
from core.analyzers.feature_analyzer import FullFeatureAnalysis
from ui.pages.base_page import BasePage
from ui.components.sidebar import PageID
from ui.components.progress_steps import AnalysisStep, StepStatus, AnalysisProgressPanel
from ui.components.log_viewer import LogViewer
from ui.workers.analysis_worker import AnalysisWorker
from ui.style import Colors, Fonts


class AnalysisPage(BasePage):
    """분석 실행 페이지"""

    # 시그널
    analysis_complete = pyqtSignal(object)   # FullFeatureAnalysis
    align_completed = pyqtSignal(object)     # AlignResult (or FallbackAlignResult)
    navigate_to_result = pyqtSignal()

    def __init__(self, image_store: ImageStore, parent=None):
        """
        분석 실행 페이지 초기화

        Args:
            image_store: 이미지 스토어
            parent: 부모 위젯
        """
        # Initialize instance variables first
        self.image_store = image_store
        self.roi_config = None
        self.inspection_purpose = None
        self.analysis_worker = None
        self.last_result = None
        self._last_align_result = None
        
        # Now call parent init which will call setup_ui
        super().__init__(
            page_id=PageID.ANALYSIS,
            title="분석 실행",
            parent=parent
        )
    
    def setup_ui(self):
        """Base page UI 설정"""
        from ui.pages.base_page import PageHeader
        
        # 메인 레이아웃 생성
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 페이지 헤더
        header = PageHeader("분석 실행", "사전 체크를 확인하고 분석을 실행하세요")
        layout.addWidget(header)
        
        # 콘텐츠 영역을 위한 레이아웃
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(16, 16, 16, 16)
        
        content_widget = QWidget()
        content_widget.setLayout(self.content_layout)
        layout.addWidget(content_widget)
        
        self.setup_content()
        self.update_preflight_ui()
    
    def setup_content(self):
        """콘텐츠 영역 설정"""
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(20)
        
        # 스플리터 생성
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        
        # 좌측 패널 (Pre-flight 체크)
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # 우측 패널 (진행 상황 + 로그)
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # 스플리터 비율 설정 (1:2)
        splitter.setSizes([300, 600])
        
        content_layout.addWidget(splitter)
        self.content_layout.addWidget(content_widget)
    
    def create_left_panel(self) -> QWidget:
        """좌측 패널 생성 (Pre-flight 체크)"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        # Pre-flight 체크 그룹박스
        self.preflight_group = QGroupBox("사전 체크")
        self.preflight_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                font-size: 12px;
                color: {Colors.TEXT_PRIMARY};
                border: 2px solid {Colors.BORDER};
                border-radius: 8px;
                margin: 8px 0px;
                padding-top: 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px 0 8px;
                background-color: {Colors.BG_PRIMARY};
            }}
        """)
        
        preflight_layout = QVBoxLayout(self.preflight_group)
        preflight_layout.setSpacing(8)
        
        # Pre-flight 체크 항목들
        self.preflight_rows = []
        check_items = [
            "Align OK 이미지",
            "Insp OK 이미지",
            "Insp NG 이미지",
            "ROI 설정",
            "검사 목적"
        ]
        
        for item in check_items:
            label = QLabel(f"❌ {item} (미설정)")
            label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 11px; padding: 4px;")
            self.preflight_rows.append(label)
            preflight_layout.addWidget(label)
        
        layout.addWidget(self.preflight_group)
        
        # 버튼들
        self.create_buttons(layout)
        
        layout.addStretch()
        return panel
    
    def create_buttons(self, layout: QVBoxLayout):
        """버튼들 생성"""
        # 시작 버튼
        self.start_button = QPushButton("🚀 분석 시작")
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self.start_analysis)
        self.start_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.ACCENT};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Colors.ACCENT_HOVER};
            }}
            QPushButton:disabled {{
                background-color: {Colors.BG_SECONDARY};
                color: {Colors.TEXT_DISABLED};
            }}
        """)
        layout.addWidget(self.start_button)
        
        # 중단 버튼
        self.cancel_button = QPushButton("⏹ 분석 중단")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_analysis)
        self.cancel_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.ERROR};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #FF6666;
            }}
            QPushButton:disabled {{
                background-color: {Colors.BG_SECONDARY};
                color: {Colors.TEXT_DISABLED};
            }}
        """)
        layout.addWidget(self.cancel_button)
        
        # 결과 보기 버튼
        self.result_button = QPushButton("📊 결과 보기")
        self.result_button.setEnabled(False)
        self.result_button.clicked.connect(self.navigate_to_result.emit)
        self.result_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.SUCCESS};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #66FF99;
            }}
            QPushButton:disabled {{
                background-color: {Colors.BG_SECONDARY};
                color: {Colors.TEXT_DISABLED};
            }}
        """)
        layout.addWidget(self.result_button)
    
    def create_right_panel(self) -> QWidget:
        """우측 패널 생성 (진행 상황 + 로그)"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        # 진행 상황 패널
        progress_group = QGroupBox("분석 진행 상황")
        progress_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                font-size: 12px;
                color: {Colors.TEXT_PRIMARY};
                border: 2px solid {Colors.BORDER};
                border-radius: 8px;
                margin: 8px 0px;
                padding-top: 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px 0 8px;
                background-color: {Colors.BG_PRIMARY};
            }}
        """)
        
        progress_layout = QVBoxLayout(progress_group)
        self.progress_panel = AnalysisProgressPanel()
        progress_layout.addWidget(self.progress_panel)
        
        layout.addWidget(progress_group)
        
        # 로그 뷰어
        log_group = QGroupBox("실행 로그")
        log_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                font-size: 12px;
                color: {Colors.TEXT_PRIMARY};
                border: 2px solid {Colors.BORDER};
                border-radius: 8px;
                margin: 8px 0px;
                padding-top: 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px 0 8px;
                background-color: {Colors.BG_PRIMARY};
            }}
        """)
        
        log_layout = QVBoxLayout(log_group)
        self.log_viewer = LogViewer()
        log_layout.addWidget(self.log_viewer)
        
        layout.addWidget(log_group)
        
        return panel
    
    def update_preflight(self, image_store: ImageStore, roi_config: ROIConfig, inspection_purpose: InspectionPurpose):
        """
        Pre-flight 체크 상태 업데이트
        
        Args:
            image_store: 이미지 스토어
            roi_config: ROI 설정
            inspection_purpose: 검사 목적
        """
        self.image_store = image_store
        self.roi_config = roi_config
        self.inspection_purpose = inspection_purpose
        
        self.update_preflight_ui()
    
    def update_preflight_ui(self):
        """Pre-flight UI 상태 업데이트"""
        # 이미지 개수 확인
        align_count = len(self.image_store.get_all(ImageType.ALIGN_OK))
        ok_count = len(self.image_store.get_all(ImageType.INSPECTION_OK))
        ng_count = len(self.image_store.get_all(ImageType.INSPECTION_NG))
        
        # ROI 설정 확인
        roi_valid = self.roi_config is not None
        
        # 검사 목적 확인
        purpose_valid = (self.inspection_purpose is not None and 
                        self.inspection_purpose.inspection_type.strip() != "")
        
        # Vision type 기반 이미지 요구사항 확인
        image_validation_result = self._validate_images_for_vision_type(align_count, ok_count, ng_count)
        
        # Pre-flight 상태 리스트 (vision type aware)
        checks = [
            (image_validation_result["align_valid"], f"Align OK 이미지", f"{align_count}장"),
            (image_validation_result["ok_valid"], f"Insp OK 이미지", f"{ok_count}장"),
            (image_validation_result["ng_valid"], f"Insp NG 이미지", f"{ng_count}장"),
            (roi_valid, "ROI 설정", "완료"),
            (purpose_valid, "검사 목적", "완료")
        ]
        
        # UI 업데이트
        all_ready = True
        for i, (is_valid, item_name, detail) in enumerate(checks):
            if is_valid:
                text = f"✅ {item_name} ({detail})"
            else:
                text = f"❌ {item_name} (미설정)"
                all_ready = False
            
            self.preflight_rows[i].setText(text)
        
        # Vision type별 에러 메시지 표시
        if not image_validation_result["overall_valid"] and purpose_valid:
            error_msg = self._get_image_validation_error_message()
            self.preflight_rows[0].setText(f"❌ 이미지 검증 실패: {error_msg}")
        
        # 시작 버튼 활성화 상태 업데이트
        self.start_button.setEnabled(all_ready and self.analysis_worker is None)
    
    def _validate_images_for_vision_type(self, align_count: int, ok_count: int, ng_count: int) -> dict:
        """
        Vision type에 따른 이미지 유효성 검사
        
        Args:
            align_count: ALIGN_OK 이미지 수
            ok_count: INSPECTION_OK 이미지 수  
            ng_count: INSPECTION_NG 이미지 수
            
        Returns:
            검증 결과 딕셔너리
        """
        if not self.inspection_purpose:
            return {
                "align_valid": True, "ok_valid": True, "ng_valid": True, 
                "overall_valid": False
            }
        
        inspection_type = self.inspection_purpose.inspection_type.strip()
        
        # Vision type 결정
        is_align_only = inspection_type == "위치정렬"
        is_inspection_only = inspection_type in ["치수측정", "결함검출", "형상검사", "기타"]
        is_mixed = False  # 현재 UI에서는 혼합 모드 설정 불가능하므로 False
        
        if is_align_only:
            # ALIGN only: ALIGN_OK ≥ 1 필요
            return {
                "align_valid": align_count > 0,
                "ok_valid": True,  # 불필요하므로 항상 valid
                "ng_valid": True,  # 불필요하므로 항상 valid
                "overall_valid": align_count > 0
            }
        elif is_inspection_only:
            # INSPECTION only: INSP_OK ≥ 1 AND INSP_NG ≥ 1 필요
            return {
                "align_valid": True,  # 불필요하므로 항상 valid
                "ok_valid": ok_count > 0,
                "ng_valid": ng_count > 0,
                "overall_valid": ok_count > 0 and ng_count > 0
            }
        elif is_mixed:
            # ALIGN + INSPECTION: 모든 이미지 필요
            return {
                "align_valid": align_count > 0,
                "ok_valid": ok_count > 0,
                "ng_valid": ng_count > 0,
                "overall_valid": align_count > 0 and ok_count > 0 and ng_count > 0
            }
        else:
            # 알 수 없는 타입: 모든 이미지 필요 (기존 동작 유지)
            return {
                "align_valid": align_count > 0,
                "ok_valid": ok_count > 0,
                "ng_valid": ng_count > 0,
                "overall_valid": align_count > 0 and ok_count > 0 and ng_count > 0
            }
    
    def _get_image_validation_error_message(self) -> str:
        """
        Vision type별 이미지 검증 에러 메시지 반환
        
        Returns:
            에러 메시지
        """
        if not self.inspection_purpose:
            return "검사 목적이 설정되지 않았습니다."
        
        inspection_type = self.inspection_purpose.inspection_type.strip()
        
        if inspection_type == "위치정렬":
            return "Align 분석: ALIGN_OK 이미지가 필요합니다."
        elif inspection_type in ["치수측정", "결함검출", "형상검사", "기타"]:
            return "Inspection 분석: OK 및 NG 이미지가 모두 필요합니다."
        else:
            return "알 수 없는 검사 유형: 모든 이미지가 필요합니다."
    
    def set_roi_config(self, roi_config: ROIConfig):
        """
        ROI 설정
        
        Args:
            roi_config: ROI 설정
        """
        self.roi_config = roi_config
        self.update_preflight_ui()
    
    def set_inspection_purpose(self, purpose: InspectionPurpose):
        """
        검사 목적 설정
        
        Args:
            purpose: 검사 목적
        """
        self.inspection_purpose = purpose
        self.update_preflight_ui()
    
    def start_analysis(self):
        """분석 시작"""
        if self.analysis_worker is not None:
            return
        
        # 진행 상황 리셋
        self.progress_panel.reset_all()
        
        # 로그 초기화
        self.log_viewer.clear_log()
        
        # 워커 생성 및 시그널 연결
        self.analysis_worker = AnalysisWorker(
            self.image_store,
            self.roi_config,
            self.inspection_purpose,
            ai_provider=None,  # ai_provider는 향후 툴바에서 주입
        )

        # 워커 시그널 연결
        self.analysis_worker.step_started.connect(self.on_step_started)
        self.analysis_worker.step_finished.connect(self.on_step_finished)
        self.analysis_worker.step_failed.connect(self.on_step_failed)
        self.analysis_worker.log_message.connect(self.on_log_message)
        self.analysis_worker.analysis_complete.connect(self.on_analysis_complete)
        self.analysis_worker.align_complete.connect(self._on_align_complete)
        self.analysis_worker.analysis_failed.connect(self.on_analysis_failed)
        
        # 워커 시작
        self.analysis_worker.start()
        
        # 버튼 상태 업데이트
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.result_button.setEnabled(False)
        
        self.log_viewer.append_info("분석 워커를 시작했습니다")
    
    def cancel_analysis(self):
        """분석 중단"""
        if self.analysis_worker is not None:
            self.analysis_worker.cancel()
    
    def on_step_started(self, step_value: str):
        """단계 시작 처리"""
        step = AnalysisStep(step_value)
        self.progress_panel.set_step_status(step, StepStatus.RUNNING)
    
    def on_step_finished(self, step_value: str, elapsed: float):
        """단계 완료 처리"""
        step = AnalysisStep(step_value)
        self.progress_panel.set_step_status(step, StepStatus.DONE, elapsed)
    
    def on_step_failed(self, step_value: str, error_message: str):
        """단계 실패 처리"""
        step = AnalysisStep(step_value)
        self.progress_panel.set_step_status(step, StepStatus.FAILED)
    
    def on_log_message(self, level: str, message: str):
        """로그 메시지 처리"""
        self.log_viewer.append_log(level, message)
    
    def _on_align_complete(self, result) -> None:
        """Align 완료 처리 — align_completed 시그널로 ResultPage에 전달"""
        self._last_align_result = result
        self.align_completed.emit(result)

    def on_analysis_complete(self, aggregate):
        """분석 완료 처리 — aggregate dict 또는 FullFeatureAnalysis를 전달받음"""
        if isinstance(aggregate, dict):
            self.last_result = aggregate.get("feature")
        else:
            self.last_result = aggregate
        self.cleanup_worker()

        # 버튼 상태 업데이트
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.result_button.setEnabled(True)

        # 시그널 발생 (페이지 전환 먼저, 데이터 로딩 나중)
        self.analysis_complete.emit(aggregate)  # 데이터 로딩 나중
        self.navigate_to_result.emit()  # 페이지 전환 먼저
    
    def on_analysis_failed(self, error_message: str):
        """분석 실패 처리"""
        self.cleanup_worker()
        
        # 버튼 상태 업데이트
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.result_button.setEnabled(False)
        
        self.log_viewer.append_error(f"분석 실패: {error_message}")
    
    def cleanup_worker(self):
        """워커 정리"""
        if self.analysis_worker is not None:
            self.analysis_worker.deleteLater()
            self.analysis_worker = None
    
    def get_last_result(self) -> FullFeatureAnalysis | None:
        """
        마지막 분석 결과 반환
        
        Returns:
            마지막 분석 결과
        """
        return self.last_result