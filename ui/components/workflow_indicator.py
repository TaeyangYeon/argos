"""
Workflow indicator components for the Argos vision algorithm design application.

This module provides visual indicators for workflow progress with step states
and animations for active steps.
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QPainter, QColor, QPen

from core.image_store import ImageStore


class WorkflowStep(QWidget):
    """
    Individual workflow step widget with state visualization.
    
    Shows step number, label, and visual state indicator with appropriate
    styling for each state (pending, active, done, warning).
    """
    
    def __init__(self, step_number: int, label: str, parent=None):
        """
        Initialize the workflow step.
        
        Args:
            step_number: Step number (1, 2, 3, 4)
            label: Step description text
            parent: Parent widget
        """
        super().__init__(parent)
        
        self._step_number = step_number
        self._label = label
        self._state = "pending"  # pending, active, done, warning
        
        self._setup_ui()
        self._setup_animation()
        
    def _setup_ui(self) -> None:
        """Setup the step UI layout."""
        # Main horizontal layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        
        # Step circle indicator
        self._circle_widget = QWidget()
        self._circle_widget.setFixedSize(24, 24)
        layout.addWidget(self._circle_widget)
        
        # Step label
        self._label_widget = QLabel(self._label)
        label_font = QFont()
        label_font.setPointSize(12)
        self._label_widget.setFont(label_font)
        layout.addWidget(self._label_widget)
        
        # Apply initial styling
        self._update_styling()
        
    def _setup_animation(self) -> None:
        """Setup pulsing animation for active state."""
        self._pulse_timer = QTimer()
        self._pulse_timer.timeout.connect(self._pulse_animation)
        self._pulse_timer.setInterval(800)  # Pulse every 800ms
        self._pulse_opacity = 1.0
        self._pulse_direction = -1
        
    def _update_styling(self) -> None:
        """Update styling based on current state."""
        if self._state == "pending":
            circle_color = "#616161"
            text_color = "#9E9E9E"
        elif self._state == "active":
            circle_color = "#1E88E5"
            text_color = "#E0E0E0"
        elif self._state == "done":
            circle_color = "#43A047"
            text_color = "#E0E0E0"
        elif self._state == "warning":
            circle_color = "#FB8C00"
            text_color = "#E0E0E0"
        else:
            circle_color = "#616161"
            text_color = "#9E9E9E"
            
        # Update label styling
        self._label_widget.setStyleSheet(f"color: {text_color};")
        
        # Store color for circle painting
        self._circle_color = QColor(circle_color)
        
        # Update circle
        self._circle_widget.update()
        
    def _pulse_animation(self) -> None:
        """Handle pulsing animation for active state."""
        if self._state == "active":
            self._pulse_opacity += self._pulse_direction * 0.1
            if self._pulse_opacity <= 0.3:
                self._pulse_direction = 1
            elif self._pulse_opacity >= 1.0:
                self._pulse_direction = -1
                
            self._circle_widget.update()
            
    def paintEvent(self, event) -> None:
        """Paint the step circle with appropriate state styling."""
        super().paintEvent(event)
        
        # Create custom widget with paint method
        def paint_circle():
            painter = QPainter(self._circle_widget)
            if not painter.isActive():
                return
                
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Circle properties
            rect = self._circle_widget.rect()
            center_x = rect.width() // 2
            center_y = rect.height() // 2
            radius = min(rect.width(), rect.height()) // 2 - 2
            
            # Apply pulsing opacity for active state
            color = QColor(self._circle_color)
            if self._state == "active":
                color.setAlphaF(self._pulse_opacity)
                
            # Draw circle
            painter.setPen(QPen(color, 2))
            painter.setBrush(color)
            painter.drawEllipse(center_x - radius, center_y - radius, radius * 2, radius * 2)
            
            # Draw inner content based on state
            painter.setPen(QPen(QColor("#FFFFFF"), 2))
            
            if self._state == "done":
                # Draw checkmark
                checkmark_size = radius // 2
                painter.drawLine(
                    center_x - checkmark_size // 2, center_y,
                    center_x - checkmark_size // 4, center_y + checkmark_size // 2
                )
                painter.drawLine(
                    center_x - checkmark_size // 4, center_y + checkmark_size // 2,
                    center_x + checkmark_size // 2, center_y - checkmark_size // 2
                )
            elif self._state == "warning":
                # Draw exclamation mark
                painter.drawLine(center_x, center_y - radius // 2, center_x, center_y)
                painter.drawPoint(center_x, center_y + radius // 3)
            else:
                # Draw step number
                painter.setPen(QPen(QColor("#FFFFFF"), 1))
                font = painter.font()
                font.setPointSize(10)
                font.setBold(True)
                painter.setFont(font)
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(self._step_number))
                
            painter.end()
        
        # Only paint if widget is visible and has valid geometry
        if self._circle_widget.isVisible() and self._circle_widget.width() > 0:
            paint_circle()
        
    def set_state(self, state: str) -> None:
        """
        Set the visual state of the step.
        
        Args:
            state: One of "pending", "active", "done", "warning"
        """
        if state not in ["pending", "active", "done", "warning"]:
            raise ValueError(f"Invalid state: {state}")
            
        self._state = state
        
        # Start/stop animation based on state
        if state == "active":
            self._pulse_timer.start()
        else:
            self._pulse_timer.stop()
            self._pulse_opacity = 1.0
            
        self._update_styling()
        
    def get_state(self) -> str:
        """Get the current state of the step."""
        return self._state


class WorkflowIndicator(QWidget):
    """
    Complete workflow indicator showing all 4 steps of the analysis process.
    
    Automatically manages step states based on ImageStore data and analysis progress.
    Steps: 이미지 업로드 → ROI 설정 → 분석 실행 → 결과 확인
    """
    
    def __init__(self, parent=None):
        """Initialize the workflow indicator."""
        super().__init__(parent)
        
        self._steps = []
        self._setup_ui()
        
    def _setup_ui(self) -> None:
        """Setup the workflow indicator UI."""
        # Main vertical layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(12)
        
        # Title
        title_label = QLabel("워크플로우 진행 단계")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #E0E0E0;")
        main_layout.addWidget(title_label)
        
        # Steps container
        steps_layout = QVBoxLayout()
        steps_layout.setSpacing(8)
        
        # Step definitions (in fixed order)
        step_definitions = [
            (1, "이미지 업로드"),
            (2, "ROI 설정"),
            (3, "분석 실행"),
            (4, "결과 확인")
        ]
        
        # Create step widgets
        for step_num, step_label in step_definitions:
            step = WorkflowStep(step_num, step_label)
            self._steps.append(step)
            steps_layout.addWidget(step)
            
        main_layout.addLayout(steps_layout)
        
    def update_from_store(
        self, 
        image_store: ImageStore, 
        has_roi: bool, 
        has_results: bool
    ) -> None:
        """
        Update step states based on current data and progress.
        
        Args:
            image_store: Current ImageStore instance
            has_roi: Whether ROI has been set
            has_results: Whether analysis results are available
        """
        # Step 1: 이미지 업로드 - done if any images exist
        step1_done = image_store.count() > 0
        
        # Step 2: ROI 설정 - done if ROI is set
        step2_done = has_roi
        
        # Step 3: 분석 실행 - done if results exist, active if steps 1&2 done but no results
        step3_done = has_results
        step3_active = step1_done and step2_done and not has_results
        
        # Step 4: 결과 확인 - active if results exist
        step4_active = has_results
        
        # Update step states
        if step1_done:
            self._steps[0].set_state("done")
        else:
            self._steps[0].set_state("pending")
            
        if step2_done:
            self._steps[1].set_state("done")
        else:
            self._steps[1].set_state("pending")
            
        if step3_done:
            self._steps[2].set_state("done")
        elif step3_active:
            self._steps[2].set_state("active")
        else:
            self._steps[2].set_state("pending")
            
        if step4_active:
            self._steps[3].set_state("active")
        else:
            self._steps[3].set_state("pending")
            
    def reset(self) -> None:
        """Reset all steps to pending state."""
        for step in self._steps:
            step.set_state("pending")