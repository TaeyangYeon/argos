"""
Failure Detail Dialog — Step 46.

Modal dialog showing full-size overlay image with zoom controls
and AI cause analysis text for a single FP/FN failure case.
"""

from __future__ import annotations

import os
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea,
    QPushButton, QSizePolicy, QTextEdit,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

from ui.style import Colors


_DIALOG_STYLE = f"""
QDialog {{
    background-color: {Colors.BG_PRIMARY};
    color: {Colors.TEXT_PRIMARY};
}}
"""

_CARD_STYLE = f"""
QFrame {{
    background-color: {Colors.CARD_BG};
    border: 1px solid {Colors.BORDER};
    border-radius: 8px;
}}
"""

_BADGE_FP_STYLE = f"""
QLabel {{
    background-color: {Colors.ERROR};
    color: #FFFFFF;
    border-radius: 16px;
    padding: 6px 16px;
    font-weight: bold;
    font-size: 13px;
}}
"""

_BADGE_FN_STYLE = f"""
QLabel {{
    background-color: {Colors.WARNING};
    color: #FFFFFF;
    border-radius: 16px;
    padding: 6px 16px;
    font-weight: bold;
    font-size: 13px;
}}
"""


class FailureDetailDialog(QDialog):
    """Modal dialog for viewing a single failure case in detail."""

    def __init__(
        self,
        overlay_path: str,
        failure_type: str,
        cause_summary: str,
        improvement_directions: list[str],
        parent=None,
    ) -> None:
        """
        Initialise the dialog.

        Args:
            overlay_path: Absolute path to the overlay image.
            failure_type: "FP" or "FN".
            cause_summary: AI-generated failure cause summary.
            improvement_directions: List of improvement suggestions.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._overlay_path = overlay_path
        self._failure_type = failure_type
        self._cause_summary = cause_summary
        self._improvement_directions = improvement_directions
        self._scale_factor = 1.0
        self._overlay_pixmap: Optional[QPixmap] = None
        self._setup_ui()
        self._load_overlay()

    def _setup_ui(self) -> None:
        """Build the dialog layout."""
        self.setWindowTitle("실패 케이스 상세")
        self.setMinimumSize(800, 500)
        self.setStyleSheet(_DIALOG_STYLE)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Main content: left (image) + right (analysis)
        content_row = QHBoxLayout()
        content_row.setSpacing(16)

        # ── Left: overlay image viewer ──
        left_panel = QVBoxLayout()

        btn_row = QHBoxLayout()
        zoom_in = QPushButton("+")
        zoom_in.setFixedSize(32, 32)
        zoom_in.setToolTip("확대")
        zoom_in.clicked.connect(self._zoom_in)
        zoom_out = QPushButton("\u2212")
        zoom_out.setFixedSize(32, 32)
        zoom_out.setToolTip("축소")
        zoom_out.clicked.connect(self._zoom_out)
        zoom_reset = QPushButton("1:1")
        zoom_reset.setFixedSize(48, 32)
        zoom_reset.setToolTip("원본 크기")
        zoom_reset.clicked.connect(self._zoom_reset)
        self._zoom_label = QLabel("100%")
        self._zoom_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 12px;"
        )
        btn_row.addWidget(zoom_in)
        btn_row.addWidget(zoom_out)
        btn_row.addWidget(zoom_reset)
        btn_row.addWidget(self._zoom_label)
        btn_row.addStretch()
        left_panel.addLayout(btn_row)

        img_scroll = QScrollArea()
        img_scroll.setWidgetResizable(False)
        img_scroll.setStyleSheet(
            f"background-color: {Colors.BG_PRIMARY}; "
            f"border: 1px solid {Colors.BORDER};"
        )
        self._overlay_label = QLabel("오버레이 이미지 없음")
        self._overlay_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._overlay_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; padding: 40px;"
        )
        self._overlay_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        img_scroll.setWidget(self._overlay_label)
        left_panel.addWidget(img_scroll, 1)
        content_row.addLayout(left_panel, 3)

        # ── Right: analysis panel ──
        right_panel = QFrame()
        right_panel.setStyleSheet(_CARD_STYLE)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(12)

        # Classification badge
        self._badge_label = QLabel()
        self._badge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._badge_label.setFixedHeight(36)
        if self._failure_type == "FP":
            self._badge_label.setText("False Positive \u2014 정상을 불량으로 판정")
            self._badge_label.setStyleSheet(_BADGE_FP_STYLE)
        else:
            self._badge_label.setText("False Negative \u2014 불량을 정상으로 판정")
            self._badge_label.setStyleSheet(_BADGE_FN_STYLE)
        right_layout.addWidget(self._badge_label)

        # Cause analysis
        cause_title = QLabel("원인 분석")
        cause_title.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: 14px; font-weight: bold;"
        )
        right_layout.addWidget(cause_title)

        self._cause_text = QTextEdit()
        self._cause_text.setReadOnly(True)
        self._cause_text.setText(self._cause_summary)
        self._cause_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                color: {Colors.TEXT_PRIMARY};
                padding: 8px;
                font-size: 13px;
            }}
        """)
        right_layout.addWidget(self._cause_text, 1)

        # Improvement directions
        improvement_title = QLabel("개선 방향")
        improvement_title.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: 14px; font-weight: bold;"
        )
        right_layout.addWidget(improvement_title)

        self._improvement_text = QTextEdit()
        self._improvement_text.setReadOnly(True)
        if self._improvement_directions:
            text = "\n".join(f"\u2022 {d}" for d in self._improvement_directions)
        else:
            text = "개선 방향 정보가 없습니다."
        self._improvement_text.setText(text)
        self._improvement_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                color: {Colors.TEXT_PRIMARY};
                padding: 8px;
                font-size: 13px;
            }}
        """)
        right_layout.addWidget(self._improvement_text, 1)

        content_row.addWidget(right_panel, 2)
        root.addLayout(content_row, 1)

        # Close button
        close_btn = QPushButton("닫기")
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(self.accept)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        root.addLayout(btn_layout)

    # ── Overlay loading ─────────────────────────────────────────────────────

    def _load_overlay(self) -> None:
        """Load the overlay image from path."""
        if self._overlay_path and os.path.isfile(str(self._overlay_path)):
            pm = QPixmap(str(self._overlay_path))
            if not pm.isNull():
                self._overlay_pixmap = pm
                self._overlay_label.setPixmap(pm)
                self._overlay_label.setText("")
                self._overlay_label.adjustSize()
                return
        self._overlay_label.setText("오버레이 이미지 없음")
        self._zoom_label.setText("\u2014")

    # ── Zoom controls ───────────────────────────────────────────────────────

    def _zoom_in(self) -> None:
        self._scale_factor = min(5.0, self._scale_factor * 1.25)
        self._apply_zoom()

    def _zoom_out(self) -> None:
        self._scale_factor = max(0.1, self._scale_factor / 1.25)
        self._apply_zoom()

    def _zoom_reset(self) -> None:
        self._scale_factor = 1.0
        self._apply_zoom()

    def _apply_zoom(self) -> None:
        """Apply current zoom factor to the overlay image."""
        self._zoom_label.setText(f"{int(self._scale_factor * 100)}%")
        if self._overlay_pixmap is not None:
            scaled = self._overlay_pixmap.scaled(
                int(self._overlay_pixmap.width() * self._scale_factor),
                int(self._overlay_pixmap.height() * self._scale_factor),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._overlay_label.setPixmap(scaled)
            self._overlay_label.adjustSize()
