"""
Inspection 결과 탭 — Step 45 (PROGRESS.md) / Step 46 (PLAN.md).

Best candidate 요약 카드, 4섹션 파라미터 테이블, 라이브러리 매핑,
오버레이 이미지 뷰어, Candidate 비교 테이블.
"""

from __future__ import annotations

import os
from typing import Optional

import numpy as np

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QSizePolicy,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap, QColor, QBrush

from ui.style import Colors

# ── Style constants ───────────────────────────────────────────────────────────

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
    min-width: 150px;
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

_DETAIL_TAB_STYLE = f"""
QTabWidget::pane {{
    border: 1px solid {Colors.BORDER};
    background-color: {Colors.BG_PRIMARY};
}}
QTabBar::tab {{
    background-color: {Colors.CARD_BG};
    color: {Colors.TEXT_SECONDARY};
    padding: 10px 16px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}}
QTabBar::tab:selected {{
    background-color: {Colors.ACCENT};
    color: #FFFFFF;
}}
QTabBar::tab:hover {{
    background-color: #424242;
    color: {Colors.TEXT_PRIMARY};
}}
"""

_EMPTY_MSG = (
    "Inspection 결과 없음 — NG 이미지가 없어 Inspection 단계를 건너뛰었습니다."
)

_HIGHLIGHT_BG = QColor("#1A3A6E")

# ── Section label mapping for design_doc ──────────────────────────────────────

_SECTION_LABELS: dict[str, str] = {
    "layout": "① 배치 구조",
    "placement_structure": "① 배치 구조",
    "placement": "① 배치 구조",
    "배치구조": "① 배치 구조",
    "parameters": "② 개별 파라미터",
    "individual_caliper_params": "② 개별 Caliper 파라미터",
    "caliper_params": "② 개별 Caliper 파라미터",
    "개별파라미터": "② 개별 파라미터",
    "result_calculation": "③ 결과 계산 방식",
    "결과계산": "③ 결과 계산 방식",
    "rationale": "④ 선택 근거",
    "selection_rationale": "④ 선택 근거",
    "선택근거": "④ 선택 근거",
    "library_mapping": "라이브러리 매핑",
    "warnings": "경고",
}


# ── Helper functions ──────────────────────────────────────────────────────────

def _score_color(score: float) -> str:
    """Return hex color for score: green >=70, yellow >=50, red <50."""
    if score >= 70:
        return Colors.SUCCESS
    if score >= 50:
        return Colors.WARNING
    return Colors.ERROR


def _ndarray_to_qpixmap(arr: np.ndarray) -> Optional[QPixmap]:
    """Safely convert numpy ndarray (BGR or grayscale) to QPixmap."""
    if arr is None or not isinstance(arr, np.ndarray) or arr.size == 0:
        return None
    try:
        if arr.ndim == 2:
            h, w = arr.shape
            img = np.ascontiguousarray(arr, dtype=np.uint8)
            qimg = QImage(img.data, w, h, w, QImage.Format.Format_Grayscale8)
        elif arr.ndim == 3 and arr.shape[2] == 3:
            rgb = np.ascontiguousarray(arr[:, :, ::-1], dtype=np.uint8)
            h, w, _ = rgb.shape
            qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888)
        elif arr.ndim == 3 and arr.shape[2] == 4:
            rgba = np.ascontiguousarray(arr[:, :, [2, 1, 0, 3]], dtype=np.uint8)
            h, w, _ = rgba.shape
            qimg = QImage(rgba.data, w, h, 4 * w, QImage.Format.Format_RGBA8888)
        else:
            return None
        return QPixmap.fromImage(qimg.copy())
    except Exception:
        return None


def _load_overlay_from_path(path: str) -> Optional[QPixmap]:
    """Load overlay image from file path."""
    if not path or not os.path.isfile(str(path)):
        return None
    pm = QPixmap(str(path))
    return pm if not pm.isNull() else None


# ── Main widget ───────────────────────────────────────────────────────────────

class InspectionTab(QWidget):
    """Inspection 결과 전체 탭."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scale_factor = 1.0
        self._overlay_pixmap: Optional[QPixmap] = None
        self._setup_ui()

    # ── UI Setup ─────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # A. Summary card
        self._summary_card = self._build_summary_card()
        layout.addWidget(self._summary_card)

        # Empty state label (kept as _content_label for backward compatibility)
        self._content_label = QLabel(_EMPTY_MSG)
        self._content_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 13px;"
        )
        self._content_label.setWordWrap(True)
        layout.addWidget(self._content_label)

        # Detail tabs
        self._detail_tabs = QTabWidget()
        self._detail_tabs.setStyleSheet(_DETAIL_TAB_STYLE)

        self._param_tab = self._build_param_tab()
        self._detail_tabs.addTab(self._param_tab, "파라미터")

        self._lib_tab = self._build_library_tab()
        self._detail_tabs.addTab(self._lib_tab, "라이브러리 매핑")

        self._overlay_tab = self._build_overlay_tab()
        self._detail_tabs.addTab(self._overlay_tab, "오버레이")

        self._comparison_tab = self._build_comparison_tab()
        self._detail_tabs.addTab(self._comparison_tab, "Candidate 비교")

        layout.addWidget(self._detail_tabs)
        layout.addStretch()

        scroll.setWidget(content)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

        # Initial state
        self._summary_card.setVisible(False)
        self._detail_tabs.setVisible(False)
        self._content_label.setVisible(True)

    # ── Summary Card ─────────────────────────────────────────────────────────

    def _build_summary_card(self) -> QFrame:
        card = QFrame()
        card.setFrameShape(QFrame.Shape.Box)
        card.setStyleSheet(_CARD_STYLE)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(12)

        title = QLabel("Inspection 결과")
        title.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: 16px; font-weight: bold;"
        )
        card_layout.addWidget(title)

        self._algo_name_label = QLabel("")
        self._algo_name_label.setStyleSheet(
            f"color: {Colors.ACCENT}; font-size: 18px; font-weight: bold;"
        )
        card_layout.addWidget(self._algo_name_label)

        # Stats row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)

        self._score_label = QLabel("—")
        stats_row.addWidget(self._build_stat_box("최종 점수", self._score_label))

        self._ok_rate_label = QLabel("—")
        stats_row.addWidget(self._build_stat_box("OK 통과율", self._ok_rate_label))

        self._ng_rate_label = QLabel("—")
        stats_row.addWidget(self._build_stat_box("NG 검출률", self._ng_rate_label))

        self._margin_label = QLabel("—")
        stats_row.addWidget(self._build_stat_box("분리 마진", self._margin_label))

        stats_row.addStretch()
        card_layout.addLayout(stats_row)

        self._margin_warning = QLabel("")
        self._margin_warning.setStyleSheet(
            f"color: {Colors.WARNING}; font-size: 12px;"
        )
        self._margin_warning.setVisible(False)
        card_layout.addWidget(self._margin_warning)

        return card

    def _build_stat_box(self, title: str, value_label: QLabel) -> QFrame:
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

    # ── Parameter Table Tab ──────────────────────────────────────────────────

    def _build_param_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)

        self._param_placeholder = QLabel("파라미터 데이터 없음")
        self._param_placeholder.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY};"
        )
        self._param_placeholder.setWordWrap(True)
        layout.addWidget(self._param_placeholder)

        self._param_table = QTableWidget()
        self._param_table.setColumnCount(2)
        self._param_table.setHorizontalHeaderLabels(["항목", "값"])
        self._param_table.horizontalHeader().setStretchLastSection(True)
        self._param_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self._param_table.setAlternatingRowColors(True)
        self._param_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self._param_table.setStyleSheet(_TABLE_STYLE)
        self._param_table.setVisible(False)
        layout.addWidget(self._param_table)

        layout.addStretch()
        return w

    # ── Library Mapping Tab ──────────────────────────────────────────────────

    def _build_library_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)

        self._lib_placeholder = QLabel("라이브러리 매핑 데이터 없음")
        self._lib_placeholder.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY};"
        )
        layout.addWidget(self._lib_placeholder)

        self._lib_table = QTableWidget()
        self._lib_table.setAlternatingRowColors(True)
        self._lib_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self._lib_table.setStyleSheet(_TABLE_STYLE)
        self._lib_table.setVisible(False)
        layout.addWidget(self._lib_table)

        layout.addStretch()
        return w

    # ── Overlay Image Tab ────────────────────────────────────────────────────

    def _build_overlay_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)

        btn_row = QHBoxLayout()
        zoom_in = QPushButton("+")
        zoom_in.setFixedSize(32, 32)
        zoom_in.clicked.connect(self._zoom_in)
        zoom_out = QPushButton("−")
        zoom_out.setFixedSize(32, 32)
        zoom_out.clicked.connect(self._zoom_out)
        zoom_reset = QPushButton("1:1")
        zoom_reset.setFixedSize(48, 32)
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
        layout.addLayout(btn_row)

        img_scroll = QScrollArea()
        img_scroll.setWidgetResizable(False)
        img_scroll.setStyleSheet(
            f"background-color: {Colors.BG_PRIMARY}; "
            f"border: 1px solid {Colors.BORDER};"
        )

        self._overlay_label = QLabel("오버레이 없음")
        self._overlay_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._overlay_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; padding: 40px;"
        )
        self._overlay_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        img_scroll.setWidget(self._overlay_label)
        layout.addWidget(img_scroll, 1)
        return w

    def _zoom_in(self) -> None:
        self._scale_factor = min(5.0, self._scale_factor * 1.25)
        self._apply_overlay_zoom()

    def _zoom_out(self) -> None:
        self._scale_factor = max(0.1, self._scale_factor / 1.25)
        self._apply_overlay_zoom()

    def _zoom_reset(self) -> None:
        self._scale_factor = 1.0
        self._apply_overlay_zoom()

    def _apply_overlay_zoom(self) -> None:
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

    # ── Comparison Tab ───────────────────────────────────────────────────────

    def _build_comparison_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)

        self._comp_placeholder = QLabel("비교 데이터 없음")
        self._comp_placeholder.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY};"
        )
        layout.addWidget(self._comp_placeholder)

        self._comp_table = QTableWidget()
        self._comp_table.setColumnCount(6)
        self._comp_table.setHorizontalHeaderLabels(
            ["Engine", "Score", "OK Pass", "NG Detect", "Margin", "Source"]
        )
        self._comp_table.horizontalHeader().setStretchLastSection(True)
        self._comp_table.setAlternatingRowColors(True)
        self._comp_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self._comp_table.setStyleSheet(_TABLE_STYLE)
        self._comp_table.setVisible(False)
        layout.addWidget(self._comp_table)

        layout.addStretch()
        return w

    # ── Data Loading ─────────────────────────────────────────────────────────

    def load_data(self, result) -> None:
        """Load OptimizationResult or None."""
        if result is None:
            self._show_empty()
            return

        best = getattr(result, "best_candidate", None)
        best_eval = getattr(result, "best_evaluation", None)
        all_results = getattr(result, "all_results", [])

        if best is None and best_eval is None:
            self._show_empty()
            return

        self._content_label.setVisible(False)
        self._summary_card.setVisible(True)
        self._detail_tabs.setVisible(True)

        self._fill_summary(best, best_eval)
        self._fill_param_table(best)
        self._fill_library_table(best)
        self._fill_overlay(best)
        self._fill_comparison_table(all_results, best)

    def _show_empty(self) -> None:
        self._content_label.setText(_EMPTY_MSG)
        self._content_label.setVisible(True)
        self._summary_card.setVisible(False)
        self._detail_tabs.setVisible(False)

    # ── Fill Summary Card ────────────────────────────────────────────────────

    def _fill_summary(self, best, best_eval) -> None:
        name = getattr(best, "engine_name", "Unknown") if best else "Unknown"
        self._algo_name_label.setText(f"Best: {name}")

        score = getattr(best_eval, "final_score", 0.0) if best_eval else 0.0
        ok_rate = getattr(best_eval, "ok_pass_rate", 0.0) if best_eval else 0.0
        ng_rate = getattr(best_eval, "ng_detect_rate", 0.0) if best_eval else 0.0
        margin = getattr(best_eval, "margin", 0.0) if best_eval else 0.0
        is_warning = (
            getattr(best_eval, "is_margin_warning", False)
            if best_eval
            else False
        )

        color = _score_color(score)
        self._score_label.setText(f"{score:.1f}")
        self._score_label.setStyleSheet(
            f"color: {color}; font-size: 24px; font-weight: bold;"
        )

        self._ok_rate_label.setText(f"{ok_rate * 100:.1f}%")
        self._ng_rate_label.setText(f"{ng_rate * 100:.1f}%")
        self._margin_label.setText(f"{margin:.1f}")

        if is_warning:
            self._margin_warning.setText(
                f"분리 마진이 낮습니다 (margin={margin:.1f} < 15)"
            )
            self._margin_warning.setVisible(True)
            self._margin_label.setStyleSheet(
                f"color: {Colors.WARNING}; font-size: 24px; font-weight: bold;"
            )
        else:
            self._margin_warning.setVisible(False)
            self._margin_label.setStyleSheet(
                f"color: {Colors.ACCENT}; font-size: 24px; font-weight: bold;"
            )

    # ── Fill Parameter Table ─────────────────────────────────────────────────

    def _fill_param_table(self, best) -> None:
        design_doc = getattr(best, "design_doc", None) if best else None

        if design_doc is None or not isinstance(design_doc, dict) or not design_doc:
            rationale = getattr(best, "rationale", "") if best else ""
            if rationale:
                self._param_placeholder.setText(f"선택 근거: {rationale}")
            else:
                self._param_placeholder.setText("설계 문서 데이터 없음")
            self._param_placeholder.setVisible(True)
            self._param_table.setVisible(False)
            return

        rows = self._flatten_design_doc(design_doc)

        self._param_table.setRowCount(len(rows))
        accent_brush = QBrush(QColor(Colors.ACCENT))
        for row_idx, (key, val, is_header) in enumerate(rows):
            key_item = QTableWidgetItem(key)
            val_item = QTableWidgetItem(val)
            if is_header:
                key_item.setForeground(accent_brush)
            self._param_table.setItem(row_idx, 0, key_item)
            self._param_table.setItem(row_idx, 1, val_item)

        self._param_placeholder.setVisible(False)
        self._param_table.setVisible(True)

    @staticmethod
    def _flatten_design_doc(doc: dict) -> list[tuple[str, str, bool]]:
        """Flatten nested design_doc to (key, value, is_header) rows."""
        rows: list[tuple[str, str, bool]] = []
        for section_key, section_val in doc.items():
            label = _SECTION_LABELS.get(section_key, section_key)
            rows.append((label, "", True))
            if isinstance(section_val, dict):
                for k, v in section_val.items():
                    if isinstance(v, list):
                        rows.append(
                            (str(k), " | ".join(str(x) for x in v), False)
                        )
                    else:
                        rows.append((str(k), str(v), False))
            elif isinstance(section_val, list):
                for i, item in enumerate(section_val):
                    rows.append((f"[{i}]", str(item), False))
            else:
                rows.append(("값", str(section_val), False))
        return rows

    # ── Fill Library Table ───────────────────────────────────────────────────

    def _fill_library_table(self, best) -> None:
        lib_map = getattr(best, "library_mapping", None) if best else None
        if not lib_map or not isinstance(lib_map, dict):
            self._lib_placeholder.setVisible(True)
            self._lib_table.setVisible(False)
            return

        vendor_names = {"keyence", "cognex", "halcon", "mil"}
        top_keys_lower = {k.lower() for k in lib_map.keys()}

        # Detect library_mapping format
        concept_table = lib_map.get("concept_table")
        if concept_table and isinstance(concept_table, dict):
            self._fill_concept_table(concept_table)
        elif top_keys_lower.issubset(vendor_names) and top_keys_lower:
            self._fill_vendor_keyed_table(lib_map)
        else:
            self._fill_concept_table(lib_map)

        self._lib_table.horizontalHeader().setStretchLastSection(True)
        self._lib_placeholder.setVisible(False)
        self._lib_table.setVisible(True)

    def _fill_concept_table(self, concept_data: dict) -> None:
        """Fill table from concept-keyed format (rows=concepts, cols=vendors)."""
        vendors = ["Keyence", "Cognex", "Halcon", "MIL"]
        self._lib_table.setColumnCount(len(vendors) + 1)
        self._lib_table.setHorizontalHeaderLabels(["개념"] + vendors)

        concepts = list(concept_data.keys())
        self._lib_table.setRowCount(len(concepts))
        for row_idx, concept in enumerate(concepts):
            self._lib_table.setItem(
                row_idx, 0, QTableWidgetItem(str(concept))
            )
            vendor_vals = concept_data[concept]
            if isinstance(vendor_vals, dict):
                for col_idx, vendor in enumerate(vendors):
                    val = vendor_vals.get(vendor, "—")
                    self._lib_table.setItem(
                        row_idx, col_idx + 1, QTableWidgetItem(str(val))
                    )

    def _fill_vendor_keyed_table(self, lib_map: dict) -> None:
        """Fill table from vendor-keyed format (rows=params, cols=vendors)."""
        vendors = [
            k for k in ["keyence", "cognex", "halcon", "mil"] if k in lib_map
        ]
        all_keys: list[str] = []
        seen: set[str] = set()
        for v in vendors:
            v_data = lib_map.get(v, {})
            if isinstance(v_data, dict):
                for k in v_data:
                    if k != "description" and k not in seen:
                        all_keys.append(k)
                        seen.add(k)

        self._lib_table.setColumnCount(len(vendors) + 1)
        self._lib_table.setHorizontalHeaderLabels(
            ["개념"] + [v.title() for v in vendors]
        )
        self._lib_table.setRowCount(len(all_keys))

        for row_idx, key in enumerate(all_keys):
            self._lib_table.setItem(row_idx, 0, QTableWidgetItem(key))
            for col_idx, vendor in enumerate(vendors):
                v_data = lib_map.get(vendor, {})
                val = v_data.get(key, "—") if isinstance(v_data, dict) else "—"
                self._lib_table.setItem(
                    row_idx, col_idx + 1, QTableWidgetItem(str(val))
                )

    # ── Fill Overlay ─────────────────────────────────────────────────────────

    def _fill_overlay(self, best) -> None:
        self._overlay_pixmap = None
        self._scale_factor = 1.0

        overlay_arr = getattr(best, "overlay_image", None) if best else None
        if isinstance(overlay_arr, np.ndarray) and overlay_arr.size > 0:
            self._overlay_pixmap = _ndarray_to_qpixmap(overlay_arr)

        if self._overlay_pixmap is None:
            overlay_path = getattr(best, "overlay_image_path", None)
            if overlay_path:
                self._overlay_pixmap = _load_overlay_from_path(str(overlay_path))

        if self._overlay_pixmap is not None:
            self._overlay_label.setPixmap(self._overlay_pixmap)
            self._overlay_label.setText("")
            self._overlay_label.adjustSize()
            self._zoom_label.setText("100%")
        else:
            self._overlay_label.clear()
            self._overlay_label.setText("오버레이 없음")
            self._zoom_label.setText("—")

    # ── Fill Comparison Table ────────────────────────────────────────────────

    def _fill_comparison_table(self, all_results, best) -> None:
        if not all_results:
            self._comp_placeholder.setVisible(True)
            self._comp_table.setVisible(False)
            return

        self._comp_table.setRowCount(len(all_results))
        highlight = QBrush(_HIGHLIGHT_BG)

        for row_idx, item in enumerate(all_results):
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                cand, ev = item[0], item[1]
            else:
                cand, ev = item, None

            eng_name = getattr(cand, "engine_name", "Unknown")
            score = getattr(ev, "final_score", getattr(ev, "score", 0.0)) if ev else 0.0
            ok_pass = getattr(ev, "ok_pass_rate", 0.0) if ev else 0.0
            ng_det = getattr(ev, "ng_detect_rate", 0.0) if ev else 0.0
            margin = getattr(ev, "margin", 0.0) if ev else 0.0
            source = getattr(cand, "source", "—")

            is_best = cand is best

            cells = [
                QTableWidgetItem(eng_name),
                QTableWidgetItem(f"{score:.1f}"),
                QTableWidgetItem(f"{ok_pass * 100:.1f}%"),
                QTableWidgetItem(f"{ng_det * 100:.1f}%"),
                QTableWidgetItem(f"{margin:.1f}"),
                QTableWidgetItem(source),
            ]
            for col_idx, cell in enumerate(cells):
                if is_best:
                    cell.setBackground(highlight)
                self._comp_table.setItem(row_idx, col_idx, cell)

        self._comp_placeholder.setVisible(False)
        self._comp_table.setVisible(True)
