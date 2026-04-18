"""
Failure 케이스 탭 — Step 46.

FP/FN 실패 이미지 썸네일 그리드, 요약 통계, 클릭 시 상세 팝업.
"""

from __future__ import annotations

import os
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea,
    QGridLayout, QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap

from ui.style import Colors
from ui.dialogs.failure_detail_dialog import FailureDetailDialog

# ── Style constants ──────────────────────────────────────────────────────────

_CARD_STYLE = f"""
QFrame {{
    background-color: {Colors.CARD_BG};
    border: 1px solid {Colors.BORDER};
    border-radius: 8px;
}}
"""

_STAT_STYLE = f"""
QFrame {{
    background-color: #1E2A4A;
    border: 1px solid {Colors.BORDER};
    border-left: 4px solid {{accent}};
    border-radius: 8px;
    min-width: 150px;
}}
"""

_EMPTY_MSG = "Failure 분석 데이터를 불러오는 중이거나 아직 로드되지 않았습니다."
_SUCCESS_MSG = "모든 이미지가 정상 판정되었습니다"

_THUMB_SIZE = 120


class _ThumbnailWidget(QFrame):
    """Single failure case thumbnail with image preview and label."""

    clicked = pyqtSignal()

    def __init__(
        self,
        overlay_path: str,
        failure_type: str,
        filename: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.overlay_path = overlay_path
        self.failure_type = failure_type
        self.filename = filename
        self._setup_ui()

    def _setup_ui(self) -> None:
        border_color = Colors.ERROR if self.failure_type == "FP" else Colors.WARNING
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.CARD_BG};
                border: 2px solid {border_color};
                border-radius: 6px;
            }}
            QFrame:hover {{
                background-color: #1E2A4A;
            }}
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(_THUMB_SIZE + 16, _THUMB_SIZE + 44)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        # Image preview
        self._image_label = QLabel()
        self._image_label.setFixedSize(_THUMB_SIZE, _THUMB_SIZE)
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setStyleSheet("border: none;")

        if self.overlay_path and os.path.isfile(str(self.overlay_path)):
            pm = QPixmap(str(self.overlay_path))
            if not pm.isNull():
                scaled = pm.scaled(
                    _THUMB_SIZE, _THUMB_SIZE,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self._image_label.setPixmap(scaled)
            else:
                self._image_label.setText("N/A")
        else:
            self._image_label.setText("N/A")
        layout.addWidget(self._image_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Type badge
        badge_color = Colors.ERROR if self.failure_type == "FP" else Colors.WARNING
        type_label = QLabel(self.failure_type)
        type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        type_label.setStyleSheet(
            f"color: {badge_color}; font-weight: bold; font-size: 11px; border: none;"
        )
        layout.addWidget(type_label)

        # Filename
        name_label = QLabel(self.filename)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 10px; border: none;"
        )
        name_label.setWordWrap(True)
        layout.addWidget(name_label)

    def mousePressEvent(self, event) -> None:
        """Emit clicked signal on mouse press."""
        self.clicked.emit()
        super().mousePressEvent(event)


class FailureTab(QWidget):
    """Failure 케이스 뷰어 탭."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._failure_result = None
        self._thumbnails: list[_ThumbnailWidget] = []
        self._setup_ui()

    # ── UI Setup ─────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        self._content_layout = QVBoxLayout(content)
        self._content_layout.setContentsMargins(24, 24, 24, 24)
        self._content_layout.setSpacing(16)

        # Summary card
        self._summary_card = self._build_summary_card()
        self._content_layout.addWidget(self._summary_card)

        # Empty / success message
        self._message_label = QLabel(_EMPTY_MSG)
        self._message_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 13px;"
        )
        self._message_label.setWordWrap(True)
        self._content_layout.addWidget(self._message_label)

        # Thumbnail grid container
        self._grid_frame = QFrame()
        self._grid_frame.setStyleSheet(_CARD_STYLE)
        grid_outer = QVBoxLayout(self._grid_frame)
        grid_outer.setContentsMargins(16, 16, 16, 16)
        grid_outer.setSpacing(8)

        grid_title = QLabel("실패 이미지 목록")
        grid_title.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: 16px; font-weight: bold;"
        )
        grid_outer.addWidget(grid_title)

        self._grid_widget = QWidget()
        self._grid_layout = QGridLayout(self._grid_widget)
        self._grid_layout.setSpacing(12)
        grid_outer.addWidget(self._grid_widget)

        self._content_layout.addWidget(self._grid_frame)

        self._content_layout.addStretch()
        scroll.setWidget(content)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

        # Initial state
        self._summary_card.setVisible(False)
        self._grid_frame.setVisible(False)
        self._message_label.setVisible(True)

    # ── Summary Card ─────────────────────────────────────────────────────────

    def _build_summary_card(self) -> QFrame:
        card = QFrame()
        card.setFrameShape(QFrame.Shape.Box)
        card.setStyleSheet(_CARD_STYLE)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(12)

        title = QLabel("Failure 분석 요약")
        title.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: 16px; font-weight: bold;"
        )
        card_layout.addWidget(title)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)

        self._fp_count_label = QLabel("0")
        stats_row.addWidget(
            self._build_stat_box("FP (오탐)", self._fp_count_label, Colors.ERROR)
        )

        self._fn_count_label = QLabel("0")
        stats_row.addWidget(
            self._build_stat_box("FN (미탐)", self._fn_count_label, Colors.WARNING)
        )

        self._total_label = QLabel("0")
        stats_row.addWidget(
            self._build_stat_box("전체 실패", self._total_label, Colors.ACCENT)
        )

        stats_row.addStretch()
        card_layout.addLayout(stats_row)

        return card

    def _build_stat_box(
        self, title: str, value_label: QLabel, accent: str,
    ) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            _STAT_STYLE.replace("{accent}", accent)
        )
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(4)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 11px;"
        )
        lay.addWidget(title_lbl)

        value_label.setStyleSheet(
            f"color: {accent}; font-size: 24px; font-weight: bold;"
        )
        lay.addWidget(value_label)
        return frame

    # ── Data Loading ─────────────────────────────────────────────────────────

    def load_result(self, failure_result) -> None:
        """
        Load FailureAnalysisResult and populate the UI.

        Args:
            failure_result: FailureAnalysisResult or None.
        """
        self._failure_result = failure_result

        if failure_result is None:
            self._show_empty()
            return

        fp_count = getattr(failure_result, "fp_count", 0)
        fn_count = getattr(failure_result, "fn_count", 0)
        fp_paths = getattr(failure_result, "fp_overlay_paths", []) or []
        fn_paths = getattr(failure_result, "fn_overlay_paths", []) or []
        cause = getattr(failure_result, "cause_summary", "")
        improvements = getattr(failure_result, "improvement_directions", []) or []

        # Update summary stats
        self._fp_count_label.setText(str(fp_count))
        self._fn_count_label.setText(str(fn_count))
        self._total_label.setText(str(fp_count + fn_count))
        self._summary_card.setVisible(True)

        if fp_count == 0 and fn_count == 0:
            self._show_success()
            return

        # Build thumbnails
        self._clear_grid()
        col = 0
        row = 0
        cols_per_row = 5

        for path in fp_paths:
            fname = os.path.basename(path) if path else "unknown"
            thumb = _ThumbnailWidget(path, "FP", fname, self)
            thumb.clicked.connect(
                lambda p=path: self._open_detail(p, "FP", cause, improvements)
            )
            self._grid_layout.addWidget(thumb, row, col)
            self._thumbnails.append(thumb)
            col += 1
            if col >= cols_per_row:
                col = 0
                row += 1

        for path in fn_paths:
            fname = os.path.basename(path) if path else "unknown"
            thumb = _ThumbnailWidget(path, "FN", fname, self)
            thumb.clicked.connect(
                lambda p=path: self._open_detail(p, "FN", cause, improvements)
            )
            self._grid_layout.addWidget(thumb, row, col)
            self._thumbnails.append(thumb)
            col += 1
            if col >= cols_per_row:
                col = 0
                row += 1

        self._message_label.setVisible(False)
        self._grid_frame.setVisible(True)

    def _show_empty(self) -> None:
        """Show empty state."""
        self._message_label.setText(_EMPTY_MSG)
        self._message_label.setVisible(True)
        self._summary_card.setVisible(False)
        self._grid_frame.setVisible(False)

    def _show_success(self) -> None:
        """Show success state when there are no failures."""
        self._message_label.setText(_SUCCESS_MSG)
        self._message_label.setStyleSheet(
            f"color: {Colors.SUCCESS}; font-size: 15px; font-weight: bold;"
        )
        self._message_label.setVisible(True)
        self._grid_frame.setVisible(False)

    def _clear_grid(self) -> None:
        """Remove all thumbnails from the grid."""
        for thumb in self._thumbnails:
            self._grid_layout.removeWidget(thumb)
            thumb.deleteLater()
        self._thumbnails.clear()

    def _open_detail(
        self,
        overlay_path: str,
        failure_type: str,
        cause_summary: str,
        improvement_directions: list[str],
    ) -> None:
        """Open the failure detail dialog."""
        dialog = FailureDetailDialog(
            overlay_path=overlay_path,
            failure_type=failure_type,
            cause_summary=cause_summary,
            improvement_directions=improvement_directions,
            parent=self,
        )
        dialog.exec()
