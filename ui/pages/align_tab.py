"""
Align 결과 탭 — Step 31.

AlignResult / FallbackAlignResult 데이터를 시각화하는 QWidget.
ResultPage의 QTabWidget에 "Align 결과" 탭으로 삽입된다.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView,
    QPlainTextEdit, QSizePolicy,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QImage, QPixmap, QColor

# ── Shared style constants ──────────────────────────────────────────────────

_CARD_STYLE = """
QFrame {
    background-color: #16213E;
    border: 1px solid #2A2A4A;
    border-radius: 8px;
}
"""

_TITLE_STYLE = "color: #E0E0E0; font-size: 15px; font-weight: bold; margin-bottom: 6px;"

_TABLE_STYLE = """
QTableWidget {
    background-color: #1A1A2E;
    border: 1px solid #2A2A4A;
    border-radius: 6px;
    color: #E0E0E0;
    gridline-color: #2A2A4A;
    font-size: 13px;
}
QHeaderView::section {
    background-color: #16213E;
    color: #9E9E9E;
    padding: 6px;
    border: none;
    font-weight: bold;
}
QTableWidget::item {
    padding: 4px 8px;
}
"""

_SECTION_HEADER_BG = QColor("#1E3A5F")
_SECTION_HEADER_FG = QColor("#90CAF9")


# ── Helper: BGR numpy → QPixmap ────────────────────────────────────────────

def _bgr_to_pixmap(bgr: np.ndarray) -> QPixmap:
    """Convert a BGR numpy array to QPixmap via QImage.Format_RGB888."""
    import cv2  # local import to avoid hard dependency at module load
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb.shape
    bytes_per_line = ch * w
    qimage = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(qimage)


# ── Main widget ─────────────────────────────────────────────────────────────

class AlignTab(QWidget):
    """
    Align 결과를 표시하는 탭 위젯.

    포함 내용:
    1. 전략 요약 카드 (strategy_name, score %, success badge)
    2. 기준점 카드 (reference_point 또는 "검출 실패")
    3. 오버레이 이미지 뷰어
    4. 4섹션 파라미터 테이블 (design_doc 기반)
    5. 라이브러리 대응 명칭 테이블 (정적)
    6. 폴백 체인 로그 (chain_stages_tried 포함 시)
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    # ── UI setup ────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #1A1A2E; }")

        content = QWidget()
        self._main_layout = QVBoxLayout(content)
        self._main_layout.setContentsMargins(24, 24, 24, 24)
        self._main_layout.setSpacing(16)

        # ── Placeholder ──
        self._placeholder_label = QLabel("분석 결과 없음")
        self._placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder_label.setStyleSheet(
            "color: #9E9E9E; font-size: 16px; padding: 40px;"
        )
        self._main_layout.addWidget(self._placeholder_label)

        # ── Strategy summary card ──
        self._strategy_frame = self._make_card("전략 요약")
        strategy_body = QHBoxLayout()

        self._strategy_name_label = QLabel("—")
        self._strategy_name_label.setStyleSheet(
            "color: #1E88E5; font-size: 18px; font-weight: bold;"
        )
        strategy_body.addWidget(self._strategy_name_label)

        self._score_label = QLabel("—%")
        self._score_label.setStyleSheet("color: #E0E0E0; font-size: 16px; padding-left: 12px;")
        strategy_body.addWidget(self._score_label)

        self._success_badge = QLabel("—")
        self._success_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._success_badge.setFixedWidth(80)
        self._success_badge.setStyleSheet(
            "background-color: #424242; color: #E0E0E0; border-radius: 12px;"
            " padding: 4px 10px; font-weight: bold; margin-left: 12px;"
        )
        strategy_body.addWidget(self._success_badge)
        strategy_body.addStretch()
        self._strategy_frame.layout().addLayout(strategy_body)

        self._failure_reason_label = QLabel("")
        self._failure_reason_label.setStyleSheet("color: #EF9A9A; font-size: 12px;")
        self._failure_reason_label.setWordWrap(True)
        self._failure_reason_label.setVisible(False)
        self._strategy_frame.layout().addWidget(self._failure_reason_label)

        self._main_layout.addWidget(self._strategy_frame)
        self._strategy_frame.setVisible(False)

        # ── Reference point card ──
        self._ref_frame = self._make_card("기준점 (Reference Point)")
        self._ref_point_label = QLabel("—")
        self._ref_point_label.setStyleSheet(
            "color: #E0E0E0; font-size: 15px; padding: 4px 0;"
        )
        self._ref_frame.layout().addWidget(self._ref_point_label)
        self._main_layout.addWidget(self._ref_frame)
        self._ref_frame.setVisible(False)

        # ── Overlay image viewer ──
        self._overlay_frame = self._make_card("오버레이 이미지")
        overlay_scroll = QScrollArea()
        overlay_scroll.setWidgetResizable(True)
        overlay_scroll.setMinimumHeight(220)
        overlay_scroll.setStyleSheet("QScrollArea { border: none; background-color: #0D0D1A; }")

        overlay_inner = QWidget()
        overlay_inner.setStyleSheet("background-color: #0D0D1A;")
        overlay_inner_layout = QVBoxLayout(overlay_inner)
        overlay_inner_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._overlay_image_label = QLabel()
        self._overlay_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._overlay_image_label.setVisible(False)
        overlay_inner_layout.addWidget(self._overlay_image_label)

        self._overlay_placeholder_label = QLabel("오버레이 이미지 없음")
        self._overlay_placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._overlay_placeholder_label.setStyleSheet(
            "color: #616161; font-size: 14px; padding: 40px;"
        )
        overlay_inner_layout.addWidget(self._overlay_placeholder_label)

        overlay_scroll.setWidget(overlay_inner)
        self._overlay_frame.layout().addWidget(overlay_scroll)
        self._main_layout.addWidget(self._overlay_frame)
        self._overlay_frame.setVisible(False)

        # ── 4-section parameter table ──
        self._param_section_frame = self._make_card("파라미터 섹션 상세")
        self._param_table_holder = QVBoxLayout()
        self._param_section_frame.layout().addLayout(self._param_table_holder)
        self._main_layout.addWidget(self._param_section_frame)
        self._param_section_frame.setVisible(False)

        # ── Library mapping table (static) ──
        self._lib_section_frame = self._make_card("라이브러리 대응 명칭 (캘리퍼 파라미터)")
        self._lib_table = self._build_library_table()
        self._lib_section_frame.layout().addWidget(self._lib_table)
        self._main_layout.addWidget(self._lib_section_frame)
        self._lib_section_frame.setVisible(False)

        # ── Fallback chain log ──
        self._fallback_section_frame = self._make_card("폴백 체인 로그")
        self._fallback_log_holder = QVBoxLayout()
        self._fallback_section_frame.layout().addLayout(self._fallback_log_holder)
        self._main_layout.addWidget(self._fallback_section_frame)
        self._fallback_section_frame.setVisible(False)

        self._main_layout.addStretch()

        scroll.setWidget(content)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    # ── Helper: create styled card frame ────────────────────────────────────

    def _make_card(self, title: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(_CARD_STYLE)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        title_label = QLabel(title)
        title_label.setStyleSheet(_TITLE_STYLE)
        layout.addWidget(title_label)
        return frame

    # ── Public API ───────────────────────────────────────────────────────────

    def load_result(self, result) -> None:
        """
        AlignResult / FallbackAlignResult 데이터를 탭에 표시한다.

        Args:
            result: AlignResult 또는 그 서브클래스 인스턴스, 또는 None.
        """
        if result is None:
            self._show_placeholder(True)
            return

        self._show_placeholder(False)

        # ── 1. Strategy summary ──
        strategy_name = getattr(result, "strategy_name", "알 수 없음") or "알 수 없음"
        score = float(getattr(result, "score", 0.0) or 0.0)
        success = bool(getattr(result, "success", False))
        failure_reason = getattr(result, "failure_reason", None)

        self._strategy_name_label.setText(strategy_name)
        self._score_label.setText(f"{score * 100:.1f}%")

        if success:
            self._success_badge.setText("성공")
            self._success_badge.setStyleSheet(
                "background-color: #2E7D32; color: #FFFFFF; border-radius: 12px;"
                " padding: 4px 10px; font-weight: bold; margin-left: 12px;"
            )
        else:
            self._success_badge.setText("실패")
            self._success_badge.setStyleSheet(
                "background-color: #C62828; color: #FFFFFF; border-radius: 12px;"
                " padding: 4px 10px; font-weight: bold; margin-left: 12px;"
            )

        if failure_reason:
            self._failure_reason_label.setText(f"실패 원인: {failure_reason}")
            self._failure_reason_label.setVisible(True)
        else:
            self._failure_reason_label.setVisible(False)

        self._strategy_frame.setVisible(True)

        # ── 2. Reference point ──
        ref_point = getattr(result, "reference_point", None)
        if ref_point is not None:
            self._ref_point_label.setText(f"({ref_point[0]}, {ref_point[1]})")
        else:
            self._ref_point_label.setText("검출 실패")
        self._ref_frame.setVisible(True)

        # ── 3. Overlay image ──
        overlay = getattr(result, "overlay_image", None)
        if overlay is not None and isinstance(overlay, np.ndarray) and overlay.size > 0:
            try:
                pixmap = _bgr_to_pixmap(overlay)
                self._overlay_image_label.setPixmap(pixmap)
                self._overlay_image_label.setVisible(True)
                self._overlay_placeholder_label.setVisible(False)
            except Exception:
                self._overlay_image_label.setVisible(False)
                self._overlay_placeholder_label.setVisible(True)
        else:
            self._overlay_image_label.setVisible(False)
            self._overlay_placeholder_label.setVisible(True)
        self._overlay_frame.setVisible(True)

        # ── 4. 4-section parameter table ──
        design_doc = getattr(result, "design_doc", {}) or {}
        self._refresh_layout(self._param_table_holder)
        param_table = self._build_4section_table(design_doc)
        self._param_table_holder.addWidget(param_table)
        self._param_section_frame.setVisible(True)

        # ── 5. Library table (always visible when result loaded) ──
        self._lib_section_frame.setVisible(True)

        # ── 6. Fallback chain log ──
        self._refresh_layout(self._fallback_log_holder)
        if isinstance(design_doc, dict) and "chain_stages_tried" in design_doc:
            fallback_log = self._build_fallback_log(design_doc)
            self._fallback_log_holder.addWidget(fallback_log)
            self._fallback_section_frame.setVisible(True)
        else:
            self._fallback_section_frame.setVisible(False)

    # ── Internal table builders ──────────────────────────────────────────────

    def _build_4section_table(self, design_doc: dict) -> QTableWidget:
        """
        design_doc 딕셔너리를 섹션별 QTableWidget으로 렌더링한다.

        - dict 값이 dict이면 섹션 헤더 행(강조) + 서브키 행으로 표시
        - dict 값이 단순 타입이면 키|값 행으로 직접 표시
        - 빈 dict이면 단일 "데이터 없음" 행 표시
        - design_doc가 str이면 단일 행으로 처리
        """
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["파라미터", "값"])
        table.setStyleSheet(_TABLE_STYLE)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        table.setMinimumHeight(150)

        rows: list[tuple[str, str, bool]] = []  # (key, value, is_header)

        if isinstance(design_doc, str):
            # Pattern align returns a plain string
            for line in design_doc.splitlines():
                line = line.strip()
                if not line:
                    continue
                if line.startswith("[") and line.endswith("]"):
                    rows.append((line, "", True))
                elif ":" in line:
                    k, _, v = line.partition(":")
                    rows.append((k.strip(), v.strip(), False))
                else:
                    rows.append((line, "", False))
        elif not design_doc:
            rows.append(("(데이터 없음)", "", False))
        else:
            for section_key, section_val in design_doc.items():
                if isinstance(section_val, dict):
                    rows.append((str(section_key), "", True))
                    for sub_key, sub_val in section_val.items():
                        rows.append((f"  {sub_key}", str(sub_val), False))
                elif isinstance(section_val, (list, tuple)):
                    rows.append((str(section_key), "", True))
                    for item in section_val:
                        rows.append(("  •", str(item), False))
                else:
                    rows.append((str(section_key), str(section_val), False))

        table.setRowCount(len(rows))
        bold_font = QFont()
        bold_font.setBold(True)

        for row_idx, (key, val, is_header) in enumerate(rows):
            key_item = QTableWidgetItem(key)
            val_item = QTableWidgetItem(val)

            if is_header:
                key_item.setFont(bold_font)
                key_item.setForeground(_SECTION_HEADER_FG)
                val_item.setForeground(_SECTION_HEADER_FG)
                key_item.setBackground(_SECTION_HEADER_BG)
                val_item.setBackground(_SECTION_HEADER_BG)
                # span is not available easily in QTableWidget without merging;
                # keep two cells but make them visually identical
                table.setItem(row_idx, 0, key_item)
                table.setItem(row_idx, 1, val_item)
            else:
                key_item.setForeground(QColor("#B0BEC5"))
                val_item.setForeground(QColor("#E0E0E0"))
                table.setItem(row_idx, 0, key_item)
                table.setItem(row_idx, 1, val_item)

        return table

    def _build_library_table(self) -> QTableWidget:
        """
        캘리퍼 파라미터의 라이브러리별 대응 명칭을 보여주는 정적 QTableWidget.

        열: 개념 | Keyence | Cognex | Halcon | MIL
        행: Search Length / Condition:Best / Inward / Projection Length
        """
        headers = ["개념", "Keyence", "Cognex", "Halcon", "MIL"]
        data = [
            [
                "Search Length",
                "Search Width\n(검색 폭)",
                "CaliperSearchLength\n(캘리퍼 검색 범위)",
                "SearchLength\n(탐색 길이)",
                "MeasSearchLength\n(측정 탐색 길이)",
            ],
            [
                "Condition:Best",
                "Edge Strength\n(에지 강도 최적)",
                "CalibrationFilter\n(에지 선택 조건)",
                "Transition (edge type)\n(전환 타입)",
                "M_EDGE_STRENGTH\n(에지 강도 조건)",
            ],
            [
                "Inward",
                "Inward (내측)\n방향 설정",
                "Polarity: Pos→Neg\n(극성: 양→음)",
                "'positive'\n(양의 전환)",
                "M_POSITIVE\n(양의 방향)",
            ],
            [
                "Projection Length",
                "Caliper Size (Width)\n(캘리퍼 폭)",
                "CaliperProjectionLength\n(투영 길이)",
                "Length1\n(측정 길이 1)",
                "MeasLength1\n(측정 길이 1)",
            ],
        ]

        table = QTableWidget(len(data), len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setStyleSheet(_TABLE_STYLE)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setMinimumHeight(160)

        bold_font = QFont()
        bold_font.setBold(True)

        for row_idx, row_data in enumerate(data):
            for col_idx, cell in enumerate(row_data):
                item = QTableWidgetItem(cell)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                )
                if col_idx == 0:
                    item.setFont(bold_font)
                    item.setForeground(_SECTION_HEADER_FG)
                    item.setBackground(_SECTION_HEADER_BG)
                else:
                    item.setForeground(QColor("#E0E0E0"))
                table.setItem(row_idx, col_idx, item)

        table.resizeRowsToContents()
        return table

    def _build_fallback_log(self, design_doc: dict) -> QPlainTextEdit:
        """
        chain_stages_tried 키가 있는 design_doc에서 폴백 체인 로그를 생성한다.
        """
        log = QPlainTextEdit()
        log.setReadOnly(True)
        log.setMinimumHeight(120)
        log.setStyleSheet("""
            QPlainTextEdit {
                background-color: #0D0D1A;
                border: 1px solid #2A2A4A;
                border-radius: 6px;
                color: #B0BEC5;
                font-family: monospace;
                font-size: 12px;
                padding: 8px;
            }
        """)

        lines: list[str] = []

        stages = design_doc.get("chain_stages_tried", [])
        if stages:
            lines.append(f"시도한 단계: {', '.join(str(s) for s in stages)}")
        else:
            lines.append("시도한 단계: (없음)")

        winning = design_doc.get("winning_strategy")
        if winning:
            lines.append(f"성공 전략: {winning}")

        failure_reasons = design_doc.get("failure_reasons", {})
        if failure_reasons:
            lines.append("실패 원인:")
            if isinstance(failure_reasons, dict):
                for stage, reason in failure_reasons.items():
                    lines.append(f"  [{stage}] {reason}")
            else:
                lines.append(f"  {failure_reasons}")

        ai_used = design_doc.get("ai_strategy_decision")
        if ai_used is not None:
            lines.append(f"AI 전략 판단 사용: {'예' if ai_used else '아니오'}")

        log.setPlainText("\n".join(lines))
        return log

    # ── Private helpers ──────────────────────────────────────────────────────

    def _show_placeholder(self, visible: bool) -> None:
        self._placeholder_label.setVisible(visible)
        self._strategy_frame.setVisible(not visible)
        self._ref_frame.setVisible(not visible)
        self._overlay_frame.setVisible(not visible)
        self._param_section_frame.setVisible(not visible)
        self._lib_section_frame.setVisible(not visible)
        self._fallback_section_frame.setVisible(not visible)

    @staticmethod
    def _refresh_layout(layout: QVBoxLayout) -> None:
        """Remove all widgets from a QVBoxLayout without deleting them permanently."""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
