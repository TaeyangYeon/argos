"""
분석 진행 단계 컴포넌트
- AnalysisStep, StepStatus 열거형
- AnalysisStepWidget: 개별 단계 위젯
- AnalysisProgressPanel: 전체 진행 상황 패널
"""

from enum import Enum
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QFont

from ui.style import Colors, Fonts


class AnalysisStep(Enum):
    """분석 단계 열거형"""
    FEATURE_ANALYSIS = "feature_analysis"
    ALIGN_DESIGN = "align_design"
    INSPECTION_DESIGN = "inspection_design"
    EVALUATION = "evaluation"


class StepStatus(Enum):
    """단계 상태 열거형"""
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


class AnalysisStepWidget(QWidget):
    """개별 분석 단계 위젯"""
    
    # 단계별 한국어 라벨
    STEP_LABELS = {
        AnalysisStep.FEATURE_ANALYSIS: "특성 분석",
        AnalysisStep.ALIGN_DESIGN: "Align 설계",
        AnalysisStep.INSPECTION_DESIGN: "검사 설계",
        AnalysisStep.EVALUATION: "평가"
    }
    
    # 상태별 아이콘
    STATUS_ICONS = {
        StepStatus.PENDING: "⏳",
        StepStatus.RUNNING: "▶",
        StepStatus.DONE: "✅",
        StepStatus.FAILED: "❌",
        StepStatus.SKIPPED: "⏭"
    }
    
    def __init__(self, step: AnalysisStep, parent=None):
        """
        개별 분석 단계 위젯 초기화
        
        Args:
            step: 분석 단계
            parent: 부모 위젯
        """
        super().__init__(parent)
        self.step = step
        self.status = StepStatus.PENDING
        self.elapsed_time = None
        self.opacity_effect = None
        self.animation = None
        
        self.setup_ui()
    
    def setup_ui(self):
        """UI 설정"""
        self.setFixedHeight(48)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)
        
        # 상태 아이콘
        self.status_icon = QLabel(self.STATUS_ICONS[StepStatus.PENDING])
        self.status_icon.setFont(QFont(Fonts.DEFAULT_FONT, 14))
        self.status_icon.setFixedWidth(24)
        
        # 단계 라벨
        self.step_label = QLabel(self.STEP_LABELS[self.step])
        self.step_label.setFont(QFont(Fonts.DEFAULT_FONT, 11, QFont.Weight.Medium))
        self.step_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        
        # 경과 시간 라벨
        self.time_label = QLabel()
        self.time_label.setFont(QFont(Fonts.MONO_FONT, 10))
        self.time_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        self.time_label.setVisible(False)
        
        # 레이아웃 구성
        layout.addWidget(self.status_icon)
        layout.addWidget(self.step_label)
        layout.addStretch()
        layout.addWidget(self.time_label)
        
        # 스타일 적용
        self.setStyleSheet(f"""
            AnalysisStepWidget {{
                background-color: {Colors.CARD_BG};
                border-radius: 8px;
                border: 1px solid {Colors.BORDER};
            }}
            AnalysisStepWidget:hover {{
                border-color: {Colors.BORDER_HOVER};
            }}
        """)
    
    def set_status(self, status: StepStatus, elapsed: float | None = None):
        """
        단계 상태 설정
        
        Args:
            status: 새로운 상태
            elapsed: 경과 시간 (초)
        """
        self.status = status
        self.elapsed_time = elapsed
        
        # 아이콘 업데이트
        self.status_icon.setText(self.STATUS_ICONS[status])
        
        # 경과 시간 업데이트
        if elapsed is not None and status in [StepStatus.DONE, StepStatus.FAILED]:
            self.time_label.setText(f"{elapsed:.1f}s")
            self.time_label.setVisible(True)
        else:
            self.time_label.setVisible(False)
        
        # RUNNING 상태일 때 펄스 애니메이션 시작
        if status == StepStatus.RUNNING:
            self.start_pulse_animation()
        else:
            self.stop_pulse_animation()
        
        # 상태별 스타일 업데이트
        self.update_status_style()
    
    def start_pulse_animation(self):
        """펄스 애니메이션 시작"""
        if self.opacity_effect is None:
            self.opacity_effect = QGraphicsOpacityEffect()
            self.setGraphicsEffect(self.opacity_effect)
        
        if self.animation is None:
            self.animation = QPropertyAnimation(self.opacity_effect, b"opacity")
            self.animation.setDuration(800)
            self.animation.setStartValue(0.4)
            self.animation.setEndValue(1.0)
            self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
            self.animation.setLoopCount(-1)  # 무한 반복
        
        self.animation.start()
    
    def stop_pulse_animation(self):
        """펄스 애니메이션 중지"""
        if self.animation is not None:
            self.animation.stop()
        
        if self.opacity_effect is not None:
            self.opacity_effect.setOpacity(1.0)
    
    def update_status_style(self):
        """상태별 스타일 업데이트"""
        border_color = Colors.BORDER
        
        if self.status == StepStatus.RUNNING:
            border_color = Colors.ACCENT
        elif self.status == StepStatus.DONE:
            border_color = Colors.SUCCESS
        elif self.status == StepStatus.FAILED:
            border_color = Colors.ERROR
        
        self.setStyleSheet(f"""
            AnalysisStepWidget {{
                background-color: {Colors.CARD_BG};
                border-radius: 8px;
                border: 1px solid {border_color};
            }}
            AnalysisStepWidget:hover {{
                border-color: {Colors.BORDER_HOVER};
            }}
        """)


class AnalysisProgressPanel(QWidget):
    """분석 진행 상황 패널"""
    
    def __init__(self, parent=None):
        """
        분석 진행 상황 패널 초기화
        
        Args:
            parent: 부모 위젯
        """
        super().__init__(parent)
        self.step_widgets = {}
        
        self.setup_ui()
    
    def setup_ui(self):
        """UI 설정"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # 각 단계별 위젯 생성
        for step in AnalysisStep:
            widget = AnalysisStepWidget(step)
            self.step_widgets[step] = widget
            layout.addWidget(widget)
        
        layout.addStretch()
    
    def reset_all(self):
        """모든 단계를 PENDING 상태로 리셋"""
        for widget in self.step_widgets.values():
            widget.set_status(StepStatus.PENDING)
    
    def set_step_status(self, step: AnalysisStep, status: StepStatus, elapsed: float | None = None):
        """
        특정 단계의 상태 설정
        
        Args:
            step: 대상 단계
            status: 새로운 상태
            elapsed: 경과 시간 (초)
        """
        if step in self.step_widgets:
            self.step_widgets[step].set_status(status, elapsed)
    
    def get_overall_progress(self) -> int:
        """
        전체 진행률 계산
        
        Returns:
            진행률 (0-100)
        """
        total_steps = len(self.step_widgets)
        completed_steps = sum(
            1 for widget in self.step_widgets.values()
            if widget.status == StepStatus.DONE
        )
        
        return int((completed_steps / total_steps) * 100) if total_steps > 0 else 0