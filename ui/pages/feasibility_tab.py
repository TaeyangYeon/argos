"""
Feasibility 탭 (스켈레톤) — Step 44.

기술 수준 배지와 짧은 근거 텍스트만 표시하는 최소 뷰.
상세 근거 및 추천 모델 정보는 Step 46/47에서 구현.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame, QScrollArea,
)
from PyQt6.QtCore import Qt

_CARD_STYLE = """
QFrame {
    background-color: #16213E;
    border: 1px solid #2A2A4A;
    border-radius: 8px;
}
"""

_EMPTY_MSG = (
    "Feasibility 결과 없음 — Inspection 단계가 실행되지 않아 "
    "기술 수준 판단을 수행하지 못했습니다."
)

_BADGE_COLORS = {
    "Rule-based": "#4CAF50",
    "Edge Learning": "#FF9800",
    "Deep Learning": "#E53935",
}


class FeasibilityTab(QWidget):
    """Feasibility 결과 스켈레톤 탭."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        card = QFrame()
        card.setFrameShape(QFrame.Shape.Box)
        card.setStyleSheet(_CARD_STYLE)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(8)

        title = QLabel("Feasibility 분석")
        title.setStyleSheet(
            "color: #E0E0E0; font-size: 16px; font-weight: bold;"
        )
        card_layout.addWidget(title)

        # Content label (empty state)
        self._content_label = QLabel(_EMPTY_MSG)
        self._content_label.setStyleSheet("color: #9E9E9E; font-size: 13px;")
        self._content_label.setWordWrap(True)
        card_layout.addWidget(self._content_label)

        # Level badge
        self._level_badge = QLabel("")
        self._level_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._level_badge.setFixedHeight(40)
        self._level_badge.setStyleSheet(
            "QLabel { background-color: #424242; color: #FFFFFF;"
            " border-radius: 20px; padding: 8px 16px; font-weight: bold; }"
        )
        self._level_badge.setVisible(False)
        card_layout.addWidget(self._level_badge)

        # Rationale
        self._rationale_label = QLabel("")
        self._rationale_label.setStyleSheet(
            "color: #E0E0E0; font-size: 13px; padding-top: 4px;"
        )
        self._rationale_label.setWordWrap(True)
        self._rationale_label.setVisible(False)
        card_layout.addWidget(self._rationale_label)

        # Note
        self._note_label = QLabel(
            "상세 근거 및 추천 모델은 다음 스텝에서 제공됩니다."
        )
        self._note_label.setStyleSheet("color: #616161; font-size: 11px; padding-top: 8px;")
        self._note_label.setVisible(False)
        card_layout.addWidget(self._note_label)

        layout.addWidget(card)
        layout.addStretch()
        scroll.setWidget(content)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

    def load_data(self, result) -> None:
        """Load FeasibilityResult or None."""
        if result is None:
            self._content_label.setText(_EMPTY_MSG)
            self._content_label.setVisible(True)
            self._level_badge.setVisible(False)
            self._rationale_label.setVisible(False)
            self._note_label.setVisible(False)
            return

        approach = getattr(result, "recommended_approach", "Unknown")
        reasoning = getattr(result, "reasoning", "")

        self._content_label.setVisible(False)

        # Badge
        color = _BADGE_COLORS.get(approach, "#424242")
        self._level_badge.setText(approach)
        self._level_badge.setStyleSheet(
            f"QLabel {{ background-color: {color}; color: #FFFFFF;"
            " border-radius: 20px; padding: 8px 16px; font-weight: bold; }"
        )
        self._level_badge.setVisible(True)

        # Rationale
        self._rationale_label.setText(reasoning)
        self._rationale_label.setVisible(True)

        # Note
        self._note_label.setVisible(True)
