"""
재사용 가능한 빈 상태 메시지 위젯.

데이터가 없거나 사전 조건이 충족되지 않은 경우 표시.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ui.style import Colors


class EmptyStateWidget(QWidget):
    """아이콘 + 메시지를 표시하는 빈 상태 위젯."""

    def __init__(self, icon: str = "📭", message: str = "", parent=None):
        """
        Args:
            icon: 표시할 이모지/아이콘 문자
            message: 안내 메시지
            parent: 부모 위젯
        """
        super().__init__(parent)
        self._setup_ui(icon, message)

    def _setup_ui(self, icon: str, message: str) -> None:
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(12)

        icon_label = QLabel(icon)
        icon_font = QFont()
        icon_font.setPointSize(36)
        icon_label.setFont(icon_font)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("background: transparent;")
        layout.addWidget(icon_label)

        self._message_label = QLabel(message)
        msg_font = QFont()
        msg_font.setPointSize(14)
        self._message_label.setFont(msg_font)
        self._message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._message_label.setWordWrap(True)
        self._message_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; background: transparent;"
        )
        layout.addWidget(self._message_label)

    def set_message(self, message: str) -> None:
        """메시지 텍스트 업데이트."""
        self._message_label.setText(message)
