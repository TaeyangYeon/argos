"""
Toast notification component for displaying temporary messages.

This module provides a toast notification widget that appears as a
floating overlay with slide-in/fade-out animations.
"""

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QWidget
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QRect, QEasingCurve
from PyQt6.QtGui import QFont


class ToastMessage(QFrame):
    """
    Floating toast notification widget with animations.
    
    Features:
    - Auto-positioning at bottom-right of parent
    - Slide-in from bottom animation
    - Fade-out animation before dismissal
    - Success, error, and warning variants
    - Auto-dismiss with configurable duration
    """
    
    def __init__(self, parent=None):
        """
        Initialize the toast message widget.
        
        Args:
            parent: Parent widget for positioning
        """
        super().__init__(parent)
        
        self._parent_widget = parent
        
        self._setup_ui()
        self._setup_animations()
        
        # Start hidden
        self.hide()
        
    def _setup_ui(self) -> None:
        """Setup the toast message UI layout."""
        # Make toast floating over parent
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setObjectName("toast")
        
        # Set size constraints
        self.setMinimumWidth(200)
        self.setMaximumWidth(400)
        self.setMinimumHeight(48)
        
        # Main horizontal layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)
        
        # Icon label
        self._icon_label = QLabel()
        icon_font = QFont()
        icon_font.setPointSize(16)
        self._icon_label.setFont(icon_font)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._icon_label)
        
        # Message label
        self._message_label = QLabel()
        message_font = QFont()
        message_font.setPointSize(12)
        self._message_label.setFont(message_font)
        self._message_label.setWordWrap(True)
        self._message_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._message_label, 1)  # Expand
        
        # Close button
        self._close_button = QPushButton("✕")
        self._close_button.setFixedSize(20, 20)
        close_font = QFont()
        close_font.setPointSize(10)
        self._close_button.setFont(close_font)
        self._close_button.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: rgba(255, 255, 255, 0.7);
                border-radius: 10px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.1);
                color: #FFFFFF;
            }
        """)
        self._close_button.clicked.connect(self.hide)
        layout.addWidget(self._close_button)
        
    def _setup_animations(self) -> None:
        """Setup slide-in and fade-out animations."""
        # Slide in animation
        self._slide_animation = QPropertyAnimation(self, b"geometry")
        self._slide_animation.setDuration(300)
        self._slide_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Fade out animation  
        self._fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self._fade_animation.setDuration(300)
        self._fade_animation.setStartValue(1.0)
        self._fade_animation.setEndValue(0.0)
        self._fade_animation.finished.connect(self.hide)
        
        # Auto-dismiss timer
        self._dismiss_timer = QTimer()
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self._start_fade_out)
        
    def _position_toast(self) -> None:
        """Position toast at bottom-right of parent widget."""
        if not self._parent_widget:
            return
            
        # Ensure proper size calculation
        self.adjustSize()
        
        parent_rect = self._parent_widget.rect()
        toast_width = self.width()
        toast_height = self.height()
        
        # Position 16px from right and bottom edges
        x = parent_rect.width() - toast_width - 16
        y = parent_rect.height() - toast_height - 16
        
        # Convert to global coordinates if parent widget is shown
        if self._parent_widget.isVisible():
            global_pos = self._parent_widget.mapToGlobal(self._parent_widget.rect().topLeft())
            x += global_pos.x()
            y += global_pos.y()
            
        # Set initial position (below visible area for slide-in effect)
        start_rect = QRect(x, y + 50, toast_width, toast_height)
        end_rect = QRect(x, y, toast_width, toast_height)
        
        self.setGeometry(start_rect)
        
        # Setup slide animation
        self._slide_animation.setStartValue(start_rect)
        self._slide_animation.setEndValue(end_rect)
        
    def _start_fade_out(self) -> None:
        """Start fade-out animation."""
        self._fade_animation.start()
        
    def show_success(self, message: str, duration: int = 3000) -> None:
        """
        Show success toast message.
        
        Args:
            message: Success message text
            duration: Auto-dismiss duration in milliseconds
        """
        self._icon_label.setText("✅")
        self._message_label.setText(message)
        
        self.setStyleSheet("""
            QFrame#toast {
                background-color: #43A047;
                border-radius: 8px;
                border: 1px solid #388E3C;
            }
            QLabel {
                color: #FFFFFF;
            }
        """)
        
        self._show_toast(duration)
        
    def show_error(self, message: str, duration: int = 4000) -> None:
        """
        Show error toast message.
        
        Args:
            message: Error message text
            duration: Auto-dismiss duration in milliseconds
        """
        self._icon_label.setText("❌")
        self._message_label.setText(message)
        
        self.setStyleSheet("""
            QFrame#toast {
                background-color: #E53935;
                border-radius: 8px;
                border: 1px solid #D32F2F;
            }
            QLabel {
                color: #FFFFFF;
            }
        """)
        
        self._show_toast(duration)
        
    def show_warning(self, message: str, duration: int = 4000) -> None:
        """
        Show warning toast message.
        
        Args:
            message: Warning message text
            duration: Auto-dismiss duration in milliseconds
        """
        self._icon_label.setText("⚠️")
        self._message_label.setText(message)
        
        self.setStyleSheet("""
            QFrame#toast {
                background-color: #FB8C00;
                border-radius: 8px;
                border: 1px solid #F57C00;
            }
            QLabel {
                color: #FFFFFF;
            }
        """)
        
        self._show_toast(duration)
        
    def _show_toast(self, duration: int) -> None:
        """
        Show toast with slide-in animation and auto-dismiss.
        
        Args:
            duration: Auto-dismiss duration in milliseconds
        """
        # Reset opacity in case it was faded out
        self.setWindowOpacity(1.0)
        
        # Position and show
        self._position_toast()
        self.show()
        self.raise_()  # Bring to front
        
        # Start slide-in animation
        self._slide_animation.start()
        
        # Start auto-dismiss timer
        self._dismiss_timer.stop()  # Stop any existing timer
        self._dismiss_timer.start(duration)
        
    def hideEvent(self, event) -> None:
        """Handle hide event to stop timers."""
        self._dismiss_timer.stop()
        self._fade_animation.stop()
        self._slide_animation.stop()
        super().hideEvent(event)