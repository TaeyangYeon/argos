"""
Feasibility 탭 — Step 47.

기술 수준 배지, 점수 상세, AI 판단 근거, 추천 모델, Feature 요약,
의사결정 흐름도를 포함한 전체 Feasibility 결과 뷰.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
)
from PyQt6.QtCore import Qt

from ui.style import Colors

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
    border-left: 4px solid {Colors.ACCENT};
    border-radius: 8px;
    min-width: 140px;
}}
"""

_TABLE_STYLE = f"""
QTableWidget {{
    background-color: {Colors.CARD_BG};
    alternate-background-color: {Colors.BG_PRIMARY};
    gridline-color: {Colors.BORDER};
    selection-background-color: {Colors.ACCENT};
    color: {Colors.TEXT_PRIMARY};
    border: 1px solid {Colors.BORDER};
    border-radius: 4px;
}}
QHeaderView::section {{
    background-color: {Colors.BG_DARK};
    border: 1px solid {Colors.BORDER};
    padding: 6px;
    color: {Colors.TEXT_PRIMARY};
    font-weight: 600;
}}
"""

_RATIONALE_STYLE = f"""
QFrame {{
    background-color: {Colors.BG_PRIMARY};
    border: none;
    border-left: 4px solid {Colors.ACCENT};
    border-radius: 0px;
    padding: 12px;
}}
"""

_EMPTY_MSG = (
    "Feasibility 결과 없음 — Inspection 단계가 실행되지 않아 "
    "기술 수준 판단을 수행하지 못했습니다."
)

_BADGE_COLORS = {
    "Rule-based": "#4CAF50",
    "Edge Learning": "#FFA726",
    "Deep Learning": "#EF5350",
}

_BADGE_SUBTITLES = {
    "Rule-based": "기존 Rule-based 알고리즘으로 충분합니다.",
    "Edge Learning": "Edge Learning 기반 모델이 권장됩니다.",
    "Deep Learning": "Deep Learning 기반 모델이 필요합니다.",
}

# Feature metric display labels
_FEATURE_LABELS = {
    "noise_level": "노이즈 수준",
    "edge_strength": "에지 강도",
    "contrast": "대비",
    "blob_count": "Blob 수",
    "edge_density": "에지 밀도",
    "mean_gray": "평균 밝기",
    "std_gray": "밝기 표준편차",
    "dynamic_range": "동적 범위",
}

_FEATURE_COLORS = {
    "Low": Colors.SUCCESS,
    "Medium": Colors.WARNING,
    "High": Colors.ERROR,
}


def _score_color(score: float) -> str:
    """Return hex color for score: green >=70, yellow >=50, red <50."""
    if score >= 70:
        return Colors.SUCCESS
    if score >= 50:
        return Colors.WARNING
    return Colors.ERROR


class FeasibilityTab(QWidget):
    """Feasibility 분석 결과 전체 탭."""

    def __init__(self, parent=None):
        super().__init__(parent)
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

        # Empty state
        self._empty_label = QLabel(_EMPTY_MSG)
        self._empty_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 13px;"
        )
        self._empty_label.setWordWrap(True)
        self._content_layout.addWidget(self._empty_label)

        # 1. Level Badge Section
        self._badge_card = self._build_badge_section()
        self._content_layout.addWidget(self._badge_card)

        # 2. Score Details Card
        self._score_card = self._build_score_card()
        self._content_layout.addWidget(self._score_card)

        # 3. AI Judgment Rationale Card
        self._rationale_card = self._build_rationale_card()
        self._content_layout.addWidget(self._rationale_card)

        # 4. Recommended Models Table
        self._models_card = self._build_models_card()
        self._content_layout.addWidget(self._models_card)

        # 5. Feature Summary Card
        self._feature_card = self._build_feature_card()
        self._content_layout.addWidget(self._feature_card)

        # 6. Decision Flow Diagram
        self._flow_card = self._build_flow_card()
        self._content_layout.addWidget(self._flow_card)

        self._content_layout.addStretch()
        scroll.setWidget(content)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

        # Initial state: hide all sections
        self._set_sections_visible(False)
        self._empty_label.setVisible(True)

    # ── Section Builders ─────────────────────────────────────────────────────

    def _build_badge_section(self) -> QFrame:
        """Build the Technology Level Badge section."""
        card = QFrame()
        card.setFrameShape(QFrame.Shape.Box)
        card.setStyleSheet(_CARD_STYLE)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("기술 수준 판단")
        title.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: 16px; font-weight: bold;"
        )
        layout.addWidget(title)

        # Large badge
        self._level_badge = QLabel("")
        self._level_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._level_badge.setFixedHeight(48)
        self._level_badge.setStyleSheet(
            "QLabel { background-color: #424242; color: #FFFFFF;"
            " border-radius: 24px; padding: 10px 24px;"
            " font-size: 18px; font-weight: bold; }"
        )
        layout.addWidget(self._level_badge)

        # Subtitle
        self._level_subtitle = QLabel("")
        self._level_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._level_subtitle.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 13px;"
        )
        self._level_subtitle.setWordWrap(True)
        layout.addWidget(self._level_subtitle)

        # Score bar section
        bar_frame = QFrame()
        bar_layout = QVBoxLayout(bar_frame)
        bar_layout.setContentsMargins(0, 8, 0, 0)
        bar_layout.setSpacing(4)

        self._score_bar_title = QLabel("Score vs Threshold")
        self._score_bar_title.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 12px;"
        )
        bar_layout.addWidget(self._score_bar_title)

        self._score_bar = QProgressBar()
        self._score_bar.setRange(0, 100)
        self._score_bar.setValue(0)
        self._score_bar.setFixedHeight(24)
        self._score_bar.setTextVisible(True)
        self._score_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid {Colors.BORDER};
                border-radius: 12px;
                background-color: {Colors.BG_PRIMARY};
                text-align: center;
                color: {Colors.TEXT_PRIMARY};
                font-weight: bold;
                font-size: 11px;
            }}
            QProgressBar::chunk {{
                background-color: {Colors.ACCENT};
                border-radius: 10px;
            }}
        """)
        bar_layout.addWidget(self._score_bar)

        # Threshold marker label
        self._threshold_marker = QLabel("")
        self._threshold_marker.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 11px;"
        )
        bar_layout.addWidget(self._threshold_marker)

        self._score_bar_frame = bar_frame
        layout.addWidget(bar_frame)

        return card

    def _build_score_card(self) -> QFrame:
        """Build the Score Details card."""
        card = QFrame()
        card.setFrameShape(QFrame.Shape.Box)
        card.setStyleSheet(_CARD_STYLE)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("점수 상세")
        title.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: 16px; font-weight: bold;"
        )
        layout.addWidget(title)

        # Stats row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)

        self._best_score_label = QLabel("—")
        stats_row.addWidget(self._build_stat_box("최고 점수", self._best_score_label))

        self._threshold_label = QLabel("—")
        stats_row.addWidget(self._build_stat_box("임계값", self._threshold_label))

        self._gap_label = QLabel("—")
        stats_row.addWidget(self._build_stat_box("점수 차이", self._gap_label))

        stats_row.addStretch()
        layout.addLayout(stats_row)

        # Interpretation
        self._score_interpretation = QLabel("")
        self._score_interpretation.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 12px; padding-top: 4px;"
        )
        self._score_interpretation.setWordWrap(True)
        layout.addWidget(self._score_interpretation)

        return card

    def _build_stat_box(self, title: str, value_label: QLabel) -> QFrame:
        """Build a stat display box."""
        frame = QFrame()
        frame.setStyleSheet(_STAT_STYLE)
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(4)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 11px;"
        )
        lay.addWidget(title_lbl)

        value_label.setStyleSheet(
            f"color: {Colors.ACCENT}; font-size: 24px; font-weight: bold;"
        )
        lay.addWidget(value_label)
        return frame

    def _build_rationale_card(self) -> QFrame:
        """Build the AI Judgment Rationale card."""
        card = QFrame()
        card.setFrameShape(QFrame.Shape.Box)
        card.setStyleSheet(_CARD_STYLE)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("AI 판단 근거")
        title.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: 16px; font-weight: bold;"
        )
        layout.addWidget(title)

        # Quote-style rationale block
        quote_frame = QFrame()
        quote_frame.setStyleSheet(_RATIONALE_STYLE)
        quote_layout = QVBoxLayout(quote_frame)
        quote_layout.setContentsMargins(12, 8, 12, 8)

        self._rationale_text = QLabel("")
        self._rationale_text.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: 13px;"
        )
        self._rationale_text.setWordWrap(True)
        quote_layout.addWidget(self._rationale_text)

        layout.addWidget(quote_frame)
        return card

    def _build_models_card(self) -> QFrame:
        """Build the Recommended Models card."""
        card = QFrame()
        card.setFrameShape(QFrame.Shape.Box)
        card.setStyleSheet(_CARD_STYLE)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("추천 모델")
        title.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: 16px; font-weight: bold;"
        )
        layout.addWidget(title)

        self._models_table = QTableWidget()
        self._models_table.setColumnCount(2)
        self._models_table.setHorizontalHeaderLabels(["항목", "값"])
        self._models_table.horizontalHeader().setStretchLastSection(True)
        self._models_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self._models_table.setAlternatingRowColors(True)
        self._models_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self._models_table.setStyleSheet(_TABLE_STYLE)
        layout.addWidget(self._models_table)

        return card

    def _build_feature_card(self) -> QFrame:
        """Build the Feature Summary card."""
        card = QFrame()
        card.setFrameShape(QFrame.Shape.Box)
        card.setStyleSheet(_CARD_STYLE)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("이미지 특성 요약")
        title.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: 16px; font-weight: bold;"
        )
        layout.addWidget(title)

        self._feature_container = QVBoxLayout()
        self._feature_container.setSpacing(6)
        layout.addLayout(self._feature_container)

        self._feature_empty_label = QLabel("Feature 데이터 없음")
        self._feature_empty_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 13px;"
        )
        self._feature_container.addWidget(self._feature_empty_label)

        # Keep references for dynamic metric rows
        self._feature_rows: list[QWidget] = []

        return card

    def _build_flow_card(self) -> QFrame:
        """Build the Decision Flow Diagram card."""
        card = QFrame()
        card.setFrameShape(QFrame.Shape.Box)
        card.setStyleSheet(_CARD_STYLE)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("의사결정 흐름")
        title.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: 16px; font-weight: bold;"
        )
        layout.addWidget(title)

        self._flow_labels: list[QLabel] = []
        flow_steps = [
            "step_score_check",
            "step_rule_based",
            "step_ai_decision",
            "step_el",
            "step_dl",
        ]
        self._flow_step_labels: dict[str, QLabel] = {}

        for step_id in flow_steps:
            lbl = QLabel("")
            lbl.setWordWrap(True)
            lbl.setStyleSheet(
                f"color: {Colors.TEXT_SECONDARY}; font-size: 12px;"
                f" padding: 6px 12px;"
                f" background-color: {Colors.BG_PRIMARY};"
                f" border-radius: 4px;"
            )
            layout.addWidget(lbl)
            self._flow_step_labels[step_id] = lbl

        return card

    # ── Visibility Management ────────────────────────────────────────────────

    def _set_sections_visible(self, visible: bool) -> None:
        """Show/hide all result sections."""
        self._badge_card.setVisible(visible)
        self._score_card.setVisible(visible)
        self._rationale_card.setVisible(visible)
        self._models_card.setVisible(visible)
        self._feature_card.setVisible(visible)
        self._flow_card.setVisible(visible)

    # ── Data Loading ─────────────────────────────────────────────────────────

    def load_data(self, result, context=None) -> None:
        """
        Load FeasibilityResult and optional context.

        Args:
            result: FeasibilityResult instance or None.
            context: Optional dict with extra info:
                - best_score (float)
                - threshold (float)
                - feature_summary (dict)
        """
        if result is None:
            self._show_empty()
            return

        ctx = context or {}

        approach = getattr(result, "recommended_approach", "Unknown")
        reasoning = getattr(result, "reasoning", "")
        model_suggestion = getattr(result, "model_suggestion", None)
        rule_based_sufficient = getattr(result, "rule_based_sufficient", False)

        best_score = ctx.get("best_score")
        threshold = ctx.get("threshold")
        feature_summary = ctx.get("feature_summary")

        self._empty_label.setVisible(False)
        self._set_sections_visible(True)

        # 1. Badge section
        self._fill_badge(approach, best_score, threshold)

        # 2. Score details
        self._fill_score_details(best_score, threshold, rule_based_sufficient)

        # 3. Rationale
        self._fill_rationale(reasoning)

        # 4. Recommended models (hidden for Rule-based)
        self._fill_models(approach, model_suggestion)

        # 5. Feature summary
        self._fill_features(feature_summary)

        # 6. Decision flow
        self._fill_flow(approach, rule_based_sufficient, best_score, threshold)

    def clear_result(self) -> None:
        """Reset all widgets to initial empty state."""
        self._show_empty()

    def _show_empty(self) -> None:
        """Show empty state and hide all sections."""
        self._empty_label.setText(_EMPTY_MSG)
        self._empty_label.setVisible(True)
        self._set_sections_visible(False)

    # ── Fill Helpers ─────────────────────────────────────────────────────────

    def _fill_badge(self, approach: str, best_score, threshold) -> None:
        """Fill the technology level badge section."""
        color = _BADGE_COLORS.get(approach, "#424242")
        self._level_badge.setText(approach)
        self._level_badge.setStyleSheet(
            f"QLabel {{ background-color: {color}; color: #FFFFFF;"
            " border-radius: 24px; padding: 10px 24px;"
            " font-size: 18px; font-weight: bold; }"
        )

        subtitle = _BADGE_SUBTITLES.get(approach, "")
        self._level_subtitle.setText(subtitle)

        # Score bar
        if best_score is not None and threshold is not None and threshold > 0:
            score_pct = min(100, max(0, int(best_score)))
            self._score_bar.setValue(score_pct)
            self._score_bar.setFormat(f"Score: {best_score:.1f}")

            bar_color = _score_color(best_score)
            self._score_bar.setStyleSheet(f"""
                QProgressBar {{
                    border: 2px solid {Colors.BORDER};
                    border-radius: 12px;
                    background-color: {Colors.BG_PRIMARY};
                    text-align: center;
                    color: {Colors.TEXT_PRIMARY};
                    font-weight: bold;
                    font-size: 11px;
                }}
                QProgressBar::chunk {{
                    background-color: {bar_color};
                    border-radius: 10px;
                }}
            """)
            self._threshold_marker.setText(
                f"▲ Threshold: {threshold:.1f}"
            )
            self._score_bar_frame.setVisible(True)
        else:
            self._score_bar_frame.setVisible(False)

    def _fill_score_details(self, best_score, threshold, rule_based_sufficient: bool) -> None:
        """Fill the score details card."""
        if best_score is not None:
            color = _score_color(best_score)
            self._best_score_label.setText(f"{best_score:.1f}")
            self._best_score_label.setStyleSheet(
                f"color: {color}; font-size: 24px; font-weight: bold;"
            )
        else:
            self._best_score_label.setText("—")
            self._best_score_label.setStyleSheet(
                f"color: {Colors.ACCENT}; font-size: 24px; font-weight: bold;"
            )

        if threshold is not None:
            self._threshold_label.setText(f"{threshold:.1f}")
        else:
            self._threshold_label.setText("—")

        if best_score is not None and threshold is not None:
            gap = best_score - threshold
            self._gap_label.setText(f"{gap:+.1f}")
            if gap >= 0:
                self._gap_label.setStyleSheet(
                    f"color: {Colors.SUCCESS}; font-size: 24px; font-weight: bold;"
                )
                self._score_interpretation.setText(
                    f"점수가 임계값을 {gap:.1f}점 초과하여 Rule-based 검사가 가능합니다."
                )
            else:
                self._gap_label.setStyleSheet(
                    f"color: {Colors.ERROR}; font-size: 24px; font-weight: bold;"
                )
                self._score_interpretation.setText(
                    f"점수가 임계값에 {abs(gap):.1f}점 미달하여 고급 기술이 필요합니다."
                )
        else:
            self._gap_label.setText("—")
            self._gap_label.setStyleSheet(
                f"color: {Colors.ACCENT}; font-size: 24px; font-weight: bold;"
            )
            if rule_based_sufficient:
                self._score_interpretation.setText(
                    "Rule-based 검사로 충분합니다."
                )
            else:
                self._score_interpretation.setText(
                    "점수 정보가 없습니다."
                )

        self._score_card.setVisible(True)

    def _fill_rationale(self, reasoning: str) -> None:
        """Fill the rationale card."""
        self._rationale_text.setText(reasoning or "판단 근거 정보 없음")

    def _fill_models(self, approach: str, model_suggestion) -> None:
        """Fill recommended models table. Hidden for Rule-based."""
        if approach == "Rule-based" or not model_suggestion:
            self._models_card.setVisible(False)
            return

        self._models_card.setVisible(True)

        # Split model_suggestion by commas for multiple suggestions
        models = [m.strip() for m in str(model_suggestion).split(",") if m.strip()]

        rows = [
            ("권장 기술 수준", approach),
        ]
        for i, model in enumerate(models):
            label = "추천 모델" if len(models) == 1 else f"추천 모델 {i + 1}"
            rows.append((label, model))

        self._models_table.setRowCount(len(rows))
        for row_idx, (key, val) in enumerate(rows):
            self._models_table.setItem(row_idx, 0, QTableWidgetItem(key))
            self._models_table.setItem(row_idx, 1, QTableWidgetItem(val))

    def _fill_features(self, feature_summary) -> None:
        """Fill feature summary card."""
        # Clear old rows
        for widget in self._feature_rows:
            widget.setParent(None)
            widget.deleteLater()
        self._feature_rows.clear()

        if not feature_summary or not isinstance(feature_summary, dict):
            self._feature_empty_label.setVisible(True)
            return

        self._feature_empty_label.setVisible(False)

        for key, value in feature_summary.items():
            row_widget = QFrame()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(4, 2, 4, 2)
            row_layout.setSpacing(8)

            # Label
            display_label = _FEATURE_LABELS.get(key, key)
            name_lbl = QLabel(display_label)
            name_lbl.setStyleSheet(
                f"color: {Colors.TEXT_SECONDARY}; font-size: 12px;"
            )
            name_lbl.setFixedWidth(120)
            row_layout.addWidget(name_lbl)

            # Color indicator dot
            str_val = str(value)
            dot_color = _FEATURE_COLORS.get(str_val, Colors.ACCENT)
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {dot_color}; font-size: 14px;")
            dot.setFixedWidth(20)
            row_layout.addWidget(dot)

            # Value
            val_lbl = QLabel(str_val)
            val_lbl.setStyleSheet(
                f"color: {Colors.TEXT_PRIMARY}; font-size: 13px; font-weight: bold;"
            )
            row_layout.addWidget(val_lbl)
            row_layout.addStretch()

            self._feature_container.addWidget(row_widget)
            self._feature_rows.append(row_widget)

    def _fill_flow(
        self,
        approach: str,
        rule_based_sufficient: bool,
        best_score,
        threshold,
    ) -> None:
        """Fill the decision flow diagram."""
        labels = self._flow_step_labels

        # Step 1: Score check
        if best_score is not None and threshold is not None:
            labels["step_score_check"].setText(
                f"① 점수 확인: Score {best_score:.1f} vs Threshold {threshold:.1f}"
            )
        else:
            labels["step_score_check"].setText("① 점수 확인: Score vs Threshold")

        # Highlight style
        active_style = (
            f"color: #FFFFFF; font-size: 12px; font-weight: bold;"
            f" padding: 8px 12px;"
            f" background-color: {{color}};"
            f" border-radius: 4px;"
        )
        inactive_style = (
            f"color: {Colors.TEXT_DISABLED}; font-size: 12px;"
            f" padding: 6px 12px;"
            f" background-color: {Colors.BG_PRIMARY};"
            f" border-radius: 4px;"
        )

        # Step 2: Rule-based path
        if rule_based_sufficient:
            labels["step_rule_based"].setText(
                "② → Score ≥ Threshold → Rule-based 충분 ✓"
            )
            labels["step_rule_based"].setStyleSheet(
                active_style.format(color=Colors.SUCCESS)
            )
            labels["step_ai_decision"].setText("③ AI 판단: 불필요")
            labels["step_ai_decision"].setStyleSheet(inactive_style)
            labels["step_el"].setText("④ Edge Learning")
            labels["step_el"].setStyleSheet(inactive_style)
            labels["step_dl"].setText("⑤ Deep Learning")
            labels["step_dl"].setStyleSheet(inactive_style)
        else:
            labels["step_rule_based"].setText(
                "② → Score < Threshold → 고급 기술 필요"
            )
            labels["step_rule_based"].setStyleSheet(inactive_style)

            labels["step_ai_decision"].setText(
                "③ AI 판단 실행 → 기술 수준 결정"
            )

            if approach == "Edge Learning":
                labels["step_ai_decision"].setStyleSheet(
                    active_style.format(color=Colors.ACCENT)
                )
                labels["step_el"].setText("④ → Edge Learning 선택 ✓")
                labels["step_el"].setStyleSheet(
                    active_style.format(color="#FFA726")
                )
                labels["step_dl"].setText("⑤ Deep Learning")
                labels["step_dl"].setStyleSheet(inactive_style)
            elif approach == "Deep Learning":
                labels["step_ai_decision"].setStyleSheet(
                    active_style.format(color=Colors.ACCENT)
                )
                labels["step_el"].setText("④ Edge Learning")
                labels["step_el"].setStyleSheet(inactive_style)
                labels["step_dl"].setText("⑤ → Deep Learning 선택 ✓")
                labels["step_dl"].setStyleSheet(
                    active_style.format(color="#EF5350")
                )
            else:
                labels["step_ai_decision"].setStyleSheet(inactive_style)
                labels["step_el"].setText("④ Edge Learning")
                labels["step_el"].setStyleSheet(inactive_style)
                labels["step_dl"].setText("⑤ Deep Learning")
                labels["step_dl"].setStyleSheet(inactive_style)

        # Always show score check as neutral active
        labels["step_score_check"].setStyleSheet(
            active_style.format(color=Colors.ACCENT)
        )
