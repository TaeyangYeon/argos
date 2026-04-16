"""
요약 탭 — Step 44.

분석 결과 전체를 4개 카드로 요약하는 QWidget.
ResultPage의 QTabWidget에 "요약" 탭으로 삽입된다.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea,
)
from PyQt6.QtCore import Qt

# ── Shared style constants (matches FeatureTab / AlignTab dark theme) ───────

_CARD_STYLE = """
QFrame {
    background-color: #16213E;
    border: 1px solid #2A2A4A;
    border-radius: 8px;
}
"""

_TITLE_STYLE = "color: #E0E0E0; font-size: 16px; font-weight: bold;"
_LABEL_STYLE = "color: #9E9E9E; font-size: 12px;"
_VALUE_STYLE = "color: #E0E0E0; font-size: 14px;"
_ACCENT_VALUE_STYLE = "color: #1E88E5; font-size: 20px; font-weight: bold;"


class SummaryTab(QWidget):
    """검사 결과 요약 탭 — 4개 카드 (검사 목적, 사용 전략, 최종 스코어, 권장 접근법)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    # ── UI setup ────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        self._content_layout = QVBoxLayout(content)
        self._content_layout.setContentsMargins(24, 24, 24, 24)
        self._content_layout.setSpacing(20)

        # Card 1 — 검사 목적
        self._build_purpose_card()
        # Card 2 — 사용 전략
        self._build_strategy_card()
        # Card 3 — 최종 스코어
        self._build_score_card()
        # Card 4 — 권장 접근법
        self._build_approach_card()

        self._content_layout.addStretch()
        scroll.setWidget(content)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

    # ── Card builders ───────────────────────────────────────────────────────

    def _build_purpose_card(self) -> None:
        card = self._make_card("검사 목적")
        layout = card.layout()

        self._purpose_type_label = self._add_row(layout, "검사 유형", "—")
        self._purpose_desc_label = self._add_row(layout, "설명", "—")
        self._purpose_criteria_label = self._add_row(layout, "판정 기준", "—")

        self._content_layout.addWidget(card)

    def _build_strategy_card(self) -> None:
        card = self._make_card("사용 전략")
        layout = card.layout()

        self._align_strategy_label = self._add_row(layout, "Align 전략", "—")
        self._inspection_algo_label = self._add_row(layout, "Inspection 알고리즘", "N/A")

        self._content_layout.addWidget(card)

    def _build_score_card(self) -> None:
        card = self._make_card("최종 스코어")
        layout = card.layout()

        row_layout = QHBoxLayout()
        row_layout.setSpacing(24)

        box1, self._align_score_label = self._make_score_box("Align 점수", "—")
        box2, self._inspection_score_label = self._make_score_box("Inspection 점수", "—")
        box3, self._feasibility_level_label = self._make_score_box("Feasibility", "—")

        row_layout.addWidget(box1)
        row_layout.addWidget(box2)
        row_layout.addWidget(box3)
        row_layout.addStretch()

        layout.addLayout(row_layout)
        self._content_layout.addWidget(card)

    def _build_approach_card(self) -> None:
        card = self._make_card("권장 접근법")
        layout = card.layout()

        self._approach_label = QLabel("—")
        self._approach_label.setStyleSheet(
            "color: #E0E0E0; font-size: 15px; padding: 4px 0px;"
        )
        self._approach_label.setWordWrap(True)
        layout.addWidget(self._approach_label)

        self._content_layout.addWidget(card)

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _make_card(self, title: str) -> QFrame:
        card = QFrame()
        card.setFrameShape(QFrame.Shape.Box)
        card.setStyleSheet(_CARD_STYLE)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        lbl = QLabel(title)
        lbl.setStyleSheet(_TITLE_STYLE)
        layout.addWidget(lbl)

        return card

    def _add_row(self, layout: QVBoxLayout, label_text: str, default: str) -> QLabel:
        row = QHBoxLayout()
        key = QLabel(f"{label_text}:")
        key.setStyleSheet(_LABEL_STYLE)
        key.setFixedWidth(100)
        val = QLabel(default)
        val.setStyleSheet(_VALUE_STYLE)
        val.setWordWrap(True)
        row.addWidget(key)
        row.addWidget(val)
        row.addStretch()
        layout.addLayout(row)
        return val

    def _make_score_box(self, title: str, default: str) -> tuple[QFrame, QLabel]:
        """Create a small score display box. Returns (container, value_label)."""
        container = QFrame()
        container.setStyleSheet(
            "QFrame { background-color: #1E2A4A; border: 1px solid #2A2A4A;"
            " border-left: 4px solid #1E88E5; border-radius: 8px; min-width: 150px; }"
        )
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(12, 8, 12, 8)
        vbox.setSpacing(4)

        t = QLabel(title)
        t.setStyleSheet(_LABEL_STYLE)
        vbox.addWidget(t)

        v = QLabel(default)
        v.setStyleSheet(_ACCENT_VALUE_STYLE)
        vbox.addWidget(v)

        return container, v

    # ── Data loading ────────────────────────────────────────────────────────

    def load_data(self, aggregate: dict) -> None:
        """Fill all four cards from the aggregate dict. Null-safe."""
        if aggregate is None:
            return

        # ── 검사 목적 ──
        purpose = aggregate.get("inspection_purpose")
        if purpose is not None:
            self._purpose_type_label.setText(
                getattr(purpose, "inspection_type", "—") or "—"
            )
            self._purpose_desc_label.setText(
                getattr(purpose, "description", "—") or "—"
            )
            self._purpose_criteria_label.setText(
                getattr(purpose, "ok_ng_criteria", "—") or "—"
            )

        # ── 사용 전략 ──
        align = aggregate.get("align")
        if align is not None:
            self._align_strategy_label.setText(
                getattr(align, "strategy_name", "—") or "—"
            )

        inspection = aggregate.get("inspection")
        if inspection is not None:
            best = getattr(inspection, "best_candidate", None)
            name = getattr(best, "engine_name", "N/A") if best else "N/A"
            self._inspection_algo_label.setText(name)
        else:
            self._inspection_algo_label.setText("N/A")

        # ── 최종 스코어 ──
        if align is not None:
            score_pct = getattr(align, "score", 0.0) * 100
            self._align_score_label.setText(f"{score_pct:.1f}%")
        else:
            self._align_score_label.setText("—")

        if inspection is not None:
            best_eval = getattr(inspection, "best_evaluation", None)
            if best_eval is not None:
                fs = getattr(best_eval, "final_score", None)
                self._inspection_score_label.setText(
                    f"{fs:.1f}" if fs is not None else "—"
                )
            else:
                self._inspection_score_label.setText("—")
        else:
            self._inspection_score_label.setText("—")

        eval_dict = aggregate.get("evaluation")
        feas = (
            eval_dict.get("feasibility_result")
            if isinstance(eval_dict, dict)
            else None
        )
        if feas is not None:
            self._feasibility_level_label.setText(
                getattr(feas, "recommended_approach", "—")
            )
        else:
            self._feasibility_level_label.setText("—")

        # ── 권장 접근법 ──
        if feas is not None:
            approach = getattr(feas, "recommended_approach", "")
            if approach == "Rule-based":
                self._approach_label.setText("Rule-based 충분")
            elif approach == "Edge Learning":
                self._approach_label.setText("Edge Learning 권장")
            elif approach == "Deep Learning":
                self._approach_label.setText("Deep Learning 필요")
            else:
                self._approach_label.setText(approach or "—")
        else:
            self._approach_label.setText("Feasibility 결과 없음")
