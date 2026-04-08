"""
Purpose input page for the Argos vision algorithm design application.

This module provides the inspection purpose input interface where users
define inspection type, target features, criteria, and measurement units.
"""

from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLineEdit, QTextEdit, 
                           QComboBox, QPushButton, QLabel, QSizePolicy, QWidget, QScrollArea)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont

from ui.pages.base_page import BasePage, PageHeader
from ui.components.sidebar import PageID
from ui.components.section_card import SectionCard
from ui.components.toast import ToastMessage
from core.models import InspectionPurpose
from core.validators import PurposeValidator
from core.exceptions import InputValidationError


class PurposePage(BasePage):
    """
    Page for defining inspection purpose and criteria.
    
    Provides interface for selecting inspection type, entering descriptions,
    defining criteria, and confirming the inspection purpose.
    """
    
    purpose_confirmed = pyqtSignal(object)  # emits InspectionPurpose
    navigate_requested = pyqtSignal(str)
    
    def __init__(self, parent=None):
        """Initialize the purpose page."""
        self._confirmed_purpose = None
        self._type_buttons = []
        self._example_label = None
        
        # Type mappings
        self._type_map = {
            "치수 측정": "치수측정",
            "결함 검출": "결함검출", 
            "형상 검사": "형상검사",
            "위치 정렬": "위치정렬",
            "기타": "기타"
        }
        
        self._example_texts = {
            "치수측정": "예) 홀 지름 0.5mm ± 0.05mm 범위 이탈 시 NG",
            "결함검출": "예) 표면 스크래치 길이 1mm 이상 시 NG",
            "형상검사": "예) 부품 외곽 형상이 기준과 5% 이상 차이 시 NG",
            "위치정렬": "예) 부품 중심 위치 오차 ±0.1mm 초과 시 NG",
            "기타": "검사 목적을 직접 입력해주세요."
        }
        
        super().__init__(PageID.PURPOSE, "검사 목적 입력", parent)
        
    def setup_ui(self) -> None:
        """Setup the page UI components."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Page header
        header = PageHeader(
            "검사 목적 입력",
            "검사 유형과 목적을 입력하면 AI가 최적 알고리즘을 설계합니다."
        )
        main_layout.addWidget(header)
        
        # Scrollable content area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(20, 20, 20, 20)
        scroll_layout.setSpacing(24)
        
        # Type selection card
        self._setup_type_card(scroll_layout)
        
        # Details card
        self._setup_details_card(scroll_layout)
        
        # Example card
        self._setup_example_card(scroll_layout)
        
        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area, 1)  # stretch=1
        
        # Confirm button (fixed at bottom)
        self._setup_confirm_button(main_layout)
        
        # Set default selection
        self._set_type_button("결함검출")
        
    def _setup_type_card(self, layout: QVBoxLayout) -> None:
        """Setup the inspection type selection card."""
        card = SectionCard("검사 유형")
        card.setMinimumWidth(600)
        
        # Button layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        
        # Create type buttons
        for button_text, type_value in self._type_map.items():
            btn = QPushButton(button_text)
            btn.setCheckable(False)
            btn.setObjectName(f"typeBtn_{type_value}")
            btn.setMinimumHeight(40)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self._apply_button_style(btn, False)
            btn.clicked.connect(lambda checked, t=type_value: self._set_type_button(t))
            
            self._type_buttons.append((btn, type_value))
            button_layout.addWidget(btn)
        
        card.add_widget(self._create_layout_widget(button_layout))
        layout.addWidget(card)
        
    def _setup_details_card(self, layout: QVBoxLayout) -> None:
        """Setup the inspection details input card."""
        card = SectionCard("검사 대상 및 기준")
        card.setMinimumWidth(600)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        # Custom add_row to set stretch
        def add_row_with_stretch(label: str, widget):
            row_layout = QHBoxLayout()
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(12)
            
            # Label (fixed width)
            label_widget = QLabel(label)
            label_font = QFont()
            label_font.setPointSize(12)
            label_widget.setFont(label_font)
            label_widget.setStyleSheet("color: #E0E0E0;")
            label_widget.setFixedWidth(140)
            label_widget.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            row_layout.addWidget(label_widget)
            
            # Widget (expanding)
            row_layout.addWidget(widget, 1)
            
            # Set stretch factors
            row_layout.setStretch(0, 0)
            row_layout.setStretch(1, 1)
            
            # Add row to content layout
            card._content_layout.addLayout(row_layout)
        
        # Target feature input
        self._target_input = QLineEdit()
        self._target_input.setPlaceholderText("예) 홀 지름, 스크래치, 부품 위치")
        self._target_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._style_input(self._target_input)
        add_row_with_stretch("검사 대상", self._target_input)
        
        # Description input
        self._description_input = QTextEdit()
        self._description_input.setPlaceholderText("검사 목적을 10자 이상 상세히 설명해주세요.")
        self._description_input.setMinimumHeight(80)
        self._description_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._description_input.setStyleSheet("""
            QTextEdit {
                background-color: #2A2A4A;
                color: #E0E0E0;
                border: 1px solid #3A3A5A;
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
            }
            QTextEdit:focus {
                border-color: #1E88E5;
            }
        """)
        add_row_with_stretch("상세 설명", self._description_input)
        
        # Criteria input
        self._criteria_input = QLineEdit()
        self._criteria_input.setPlaceholderText("예) 지름 0.5mm ± 0.05mm 범위 이탈 시 NG")
        self._criteria_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._style_input(self._criteria_input)
        add_row_with_stretch("판정 기준", self._criteria_input)
        
        # Measurement unit
        self._unit_combo = QComboBox()
        self._unit_combo.addItems(["mm", "px", "%", "기타"])
        self._unit_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._unit_combo.setStyleSheet("""
            QComboBox {
                background-color: #2A2A4A;
                color: #E0E0E0;
                border: 1px solid #3A3A5A;
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
                min-width: 80px;
            }
            QComboBox:focus {
                border-color: #1E88E5;
            }
            QComboBox::drop-down {
                border: none;
                background: #3A3A5A;
                border-radius: 4px;
            }
            QComboBox::down-arrow {
                border: none;
                background: none;
            }
            QComboBox QAbstractItemView {
                background-color: #2A2A4A;
                color: #E0E0E0;
                selection-background-color: #1E88E5;
                border: 1px solid #3A3A5A;
            }
        """)
        add_row_with_stretch("측정 단위", self._unit_combo)
        
        # Tolerance input
        self._tolerance_input = QLineEdit()
        self._tolerance_input.setPlaceholderText("예) ±0.05")
        self._tolerance_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._style_input(self._tolerance_input)
        add_row_with_stretch("허용 공차", self._tolerance_input)
        
        layout.addWidget(card)
        
    def _setup_example_card(self, layout: QVBoxLayout) -> None:
        """Setup the example text card."""
        card = SectionCard("입력 예시")
        card.setMinimumWidth(600)
        
        self._example_label = QLabel()
        self._example_label.setWordWrap(True)
        self._example_label.setStyleSheet("""
            color: #7A8BA0;
            font-style: italic;
            font-size: 12px;
            padding: 8px;
            background-color: #1A1A2E;
            border-radius: 4px;
        """)
        
        card.add_widget(self._example_label)
        layout.addWidget(card)
        
    def _setup_confirm_button(self, layout: QVBoxLayout) -> None:
        """Setup the confirm button."""
        self._confirm_btn = QPushButton("✅  목적 확정")
        self._confirm_btn.setFixedHeight(52)
        self._confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #1E88E5;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """)
        self._confirm_btn.clicked.connect(self._on_confirm_clicked)
        
        # Add button with proper spacing via layout margins
        layout.setContentsMargins(20, 16, 20, 16)
        layout.addWidget(self._confirm_btn, 0)  # stretch=0 for fixed height
        
    def _style_input(self, input_widget: QLineEdit) -> None:
        """Apply standard styling to input widgets."""
        input_widget.setStyleSheet("""
            QLineEdit {
                background-color: #2A2A4A;
                color: #E0E0E0;
                border: 1px solid #3A3A5A;
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #1E88E5;
            }
        """)
        
    def _create_layout_widget(self, layout) -> QWidget:
        """Create a widget to hold a layout."""
        widget = QWidget()
        widget.setLayout(layout)
        return widget
        
    def _get_selected_type(self) -> str:
        """Return the inspection_type string of the currently active toggle button."""
        for btn, type_value in self._type_buttons:
            if "#1E88E5" in btn.styleSheet():
                return type_value
        return "결함검출"  # default fallback
        
    def _apply_button_style(self, btn: QPushButton, selected: bool) -> None:
        """Apply consistent styling to inspection type buttons."""
        if selected:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #1E88E5;
                    color: #FFFFFF;
                    font-size: 13px;
                    font-weight: bold;
                    min-height: 40px;
                    padding: 6px 16px;
                    border-radius: 6px;
                    border: none;
                }
                QPushButton:hover { background-color: #1976D2; }
            """)
        else:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2A2A4A;
                    color: #E0E0E0;
                    font-size: 13px;
                    font-weight: bold;
                    min-height: 40px;
                    padding: 6px 16px;
                    border-radius: 6px;
                    border: 1px solid #3A3A5A;
                }
                QPushButton:hover { background-color: #3A3A5A; }
            """)
        
    def _set_type_button(self, inspection_type: str) -> None:
        """Activate the button matching inspection_type; deactivate others."""
        for btn, type_value in self._type_buttons:
            selected = (type_value == inspection_type)
            self._apply_button_style(btn, selected)
            # Force redraw
            btn.update()
            btn.repaint()
        
        # Update example text
        if self._example_label:
            example_text = self._example_texts.get(inspection_type, "")
            self._example_label.setText(example_text)
            
    def _on_confirm_clicked(self) -> None:
        """Handle confirm button click."""
        try:
            # Build InspectionPurpose from current field values
            purpose = InspectionPurpose(
                inspection_type=self._get_selected_type(),
                description=self._description_input.toPlainText().strip(),
                ok_ng_criteria=self._criteria_input.text().strip(),
                target_feature=self._target_input.text().strip(),
                measurement_unit=self._unit_combo.currentText(),
                tolerance=self._tolerance_input.text().strip()
            )
            
            # Validate the purpose
            PurposeValidator().validate_purpose(purpose)
            
            # Store confirmed purpose
            self._confirmed_purpose = purpose
            
            # Show success message
            toast = ToastMessage(self)
            toast.show_success("검사 목적이 확정되었습니다.")
            
            # Emit signal
            self.purpose_confirmed.emit(purpose)
            
        except InputValidationError as e:
            # Show error message
            toast = ToastMessage(self)
            toast.show_error(str(e))
            
    def get_confirmed_purpose(self) -> InspectionPurpose | None:
        """Return the confirmed purpose object, None until confirmed."""
        return self._confirmed_purpose
        
    def load_purpose(self, purpose: InspectionPurpose) -> None:
        """Restore all field values from purpose object."""
        # Set type button
        self._set_type_button(purpose.inspection_type)
        
        # Set field values
        self._target_input.setText(purpose.target_feature)
        self._description_input.setPlainText(purpose.description)
        self._criteria_input.setText(purpose.ok_ng_criteria)
        self._tolerance_input.setText(purpose.tolerance)
        
        # Set unit combo
        unit_index = self._unit_combo.findText(purpose.measurement_unit)
        if unit_index >= 0:
            self._unit_combo.setCurrentIndex(unit_index)
