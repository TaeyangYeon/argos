"""
Inspection 결과 탭 (스켈레톤) — Step 44.

Best candidate 알고리즘명과 점수만 표시하는 최소 뷰.
상세 파라미터 테이블, 라이브러리 매핑 등은 Step 45/46에서 구현.
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
    "Inspection 결과 없음 — NG 이미지가 없어 Inspection 단계를 건너뛰었습니다."
)


class InspectionTab(QWidget):
    """Inspection 결과 스켈레톤 탭."""

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

        # Card
        card = QFrame()
        card.setFrameShape(QFrame.Shape.Box)
        card.setStyleSheet(_CARD_STYLE)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(8)

        title = QLabel("Inspection 결과")
        title.setStyleSheet(
            "color: #E0E0E0; font-size: 16px; font-weight: bold;"
        )
        card_layout.addWidget(title)

        # Content label (empty state or filled)
        self._content_label = QLabel(_EMPTY_MSG)
        self._content_label.setStyleSheet("color: #9E9E9E; font-size: 13px;")
        self._content_label.setWordWrap(True)
        card_layout.addWidget(self._content_label)

        # Algorithm name
        self._algo_name_label = QLabel("")
        self._algo_name_label.setStyleSheet(
            "color: #1E88E5; font-size: 18px; font-weight: bold;"
        )
        self._algo_name_label.setVisible(False)
        card_layout.addWidget(self._algo_name_label)

        # Score
        self._score_label = QLabel("")
        self._score_label.setStyleSheet("color: #E0E0E0; font-size: 14px;")
        self._score_label.setVisible(False)
        card_layout.addWidget(self._score_label)

        # Note
        self._note_label = QLabel(
            "상세 파라미터 및 라이브러리 매핑은 다음 스텝에서 제공됩니다."
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
        """Load OptimizationResult or None."""
        if result is None:
            self._content_label.setText(_EMPTY_MSG)
            self._content_label.setVisible(True)
            self._algo_name_label.setVisible(False)
            self._score_label.setVisible(False)
            self._note_label.setVisible(False)
            return

        best = getattr(result, "best_candidate", None)
        best_eval = getattr(result, "best_evaluation", None)

        name = getattr(best, "engine_name", "Unknown") if best else "Unknown"
        score = getattr(best_eval, "final_score", 0.0) if best_eval else 0.0

        self._content_label.setVisible(False)
        self._algo_name_label.setText(f"Best: {name}")
        self._algo_name_label.setVisible(True)
        self._score_label.setText(f"Score: {score:.1f}")
        self._score_label.setVisible(True)
        self._note_label.setVisible(True)
