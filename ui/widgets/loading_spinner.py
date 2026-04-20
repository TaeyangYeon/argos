"""
재사용 가능한 로딩 스피너 위젯.

QWidget 기반 커스텀 회전 스피너. QMovie/GIF 없이 QPainter로 직접 렌더링.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen

from ui.style import Colors


class LoadingSpinner(QWidget):
    """회전 애니메이션 로딩 스피너."""

    def __init__(self, size: int = 48, parent=None):
        super().__init__(parent)
        self._size = size
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self._timer.setInterval(50)
        self.setFixedSize(size, size)

    def start(self) -> None:
        """스피너 애니메이션 시작."""
        self._timer.start()
        self.setVisible(True)

    def stop(self) -> None:
        """스피너 애니메이션 정지."""
        self._timer.stop()
        self.setVisible(False)

    def _rotate(self) -> None:
        self._angle = (self._angle + 10) % 360
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 배경 투명
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))

        # 스피너 원호
        pen_width = max(3, self._size // 12)
        margin = pen_width + 2
        rect = QRectF(margin, margin, self._size - 2 * margin, self._size - 2 * margin)

        # 배경 트랙
        track_pen = QPen(QColor(Colors.BORDER), pen_width)
        track_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(track_pen)
        painter.drawArc(rect, 0, 360 * 16)

        # 회전 원호
        arc_pen = QPen(QColor(Colors.ACCENT), pen_width)
        arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(arc_pen)
        start_angle = int(self._angle * 16)
        span_angle = 90 * 16
        painter.drawArc(rect, start_angle, span_angle)

        painter.end()


class LoadingOverlay(QWidget):
    """스피너 + 텍스트를 포함한 오버레이 위젯."""

    def __init__(self, message: str = "분석 중...", parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setStyleSheet(f"background-color: rgba(26, 26, 46, 200);")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._spinner = LoadingSpinner(64, self)
        layout.addWidget(self._spinner, 0, Qt.AlignmentFlag.AlignCenter)

        self._label = QLabel(message)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: 14px; background: transparent;"
        )
        layout.addWidget(self._label)

    def start(self, message: str | None = None) -> None:
        if message:
            self._label.setText(message)
        self._spinner.start()
        self.setVisible(True)
        self.raise_()

    def stop(self) -> None:
        self._spinner.stop()
        self.setVisible(False)

    def set_message(self, message: str) -> None:
        self._label.setText(message)
