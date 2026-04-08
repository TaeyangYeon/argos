"""
Unit tests for the PurposePage component.

Tests all functionality including type selection, form validation,
signal emission, and purpose confirmation.
"""

import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from ui.pages.purpose_page import PurposePage
from core.models import InspectionPurpose


class TestPurposePage:
    """Test suite for PurposePage component."""
    
    def test_purpose_page_created(self, qtbot):
        """Test that PurposePage can be created and shown without exceptions."""
        page = PurposePage()
        qtbot.addWidget(page)
        page.show()
        
        # Check that the page is visible and has expected components
        assert page.isVisible()
        assert page.page_id.value == "purpose"
        assert page.title == "검사 목적 입력"
        
        # Check that main components exist
        assert page._type_buttons is not None
        assert len(page._type_buttons) == 5
        assert page._description_input is not None
        assert page._confirm_btn is not None
        
    def test_type_buttons_exclusive(self, qtbot):
        """Test that type buttons work exclusively - only one active at a time."""
        page = PurposePage()
        qtbot.addWidget(page)
        
        # Click "치수 측정" button
        page._set_type_button("치수측정")
        assert page._get_selected_type() == "치수측정"
        
        # Verify only one button has accent background
        accent_count = 0
        for btn, type_value in page._type_buttons:
            if "#1E88E5" in btn.styleSheet():
                accent_count += 1
                assert type_value == "치수측정"
        assert accent_count == 1
        
        # Click "결함 검출" button 
        page._set_type_button("결함검출")
        assert page._get_selected_type() == "결함검출"
        
        # Verify only the new button has accent background
        accent_count = 0
        for btn, type_value in page._type_buttons:
            if "#1E88E5" in btn.styleSheet():
                accent_count += 1
                assert type_value == "결함검출"
        assert accent_count == 1
        
    def test_example_text_changes_by_type(self, qtbot):
        """Test that example text updates when type buttons are clicked."""
        page = PurposePage()
        qtbot.addWidget(page)
        
        # Test each type and its corresponding example text
        test_cases = [
            ("치수측정", "예) 홀 지름 0.5mm ± 0.05mm 범위 이탈 시 NG"),
            ("결함검출", "예) 표면 스크래치 길이 1mm 이상 시 NG"),
            ("형상검사", "예) 부품 외곽 형상이 기준과 5% 이상 차이 시 NG"),
            ("위치정렬", "예) 부품 중심 위치 오차 ±0.1mm 초과 시 NG"),
            ("기타", "검사 목적을 직접 입력해주세요.")
        ]
        
        for type_value, expected_text in test_cases:
            page._set_type_button(type_value)
            actual_text = page._example_label.text()
            assert actual_text == expected_text, f"Type {type_value} should show: {expected_text}, but got: {actual_text}"
            
    def test_confirm_empty_description_shows_error(self, qtbot):
        """Test that confirming with empty description shows error and doesn't save purpose."""
        page = PurposePage()
        qtbot.addWidget(page)
        
        # Leave description field empty 
        page._description_input.clear()
        
        # Call confirm (this should trigger validation error)
        page._on_confirm_clicked()
        
        # Should not have confirmed purpose stored
        assert page.get_confirmed_purpose() is None
        
    def test_confirm_valid_emits_signal(self, qtbot):
        """Test that confirming with valid data emits purpose_confirmed signal."""
        page = PurposePage()
        qtbot.addWidget(page)
        
        # Set valid description
        page._description_input.setPlainText("PCB 솔더볼 직경 검사 목적 테스트")
        
        # Setup signal monitoring
        with qtbot.waitSignal(page.purpose_confirmed, timeout=1000) as blocker:
            page._on_confirm_clicked()
            
        # Verify signal was emitted
        assert blocker.signal_triggered
        assert blocker.args[0] is not None  # Should contain InspectionPurpose object
        
    def test_get_confirmed_purpose_after_confirm(self, qtbot):
        """Test that get_confirmed_purpose returns valid purpose after confirmation."""
        page = PurposePage()
        qtbot.addWidget(page)
        
        # Fill in valid description
        page._description_input.setPlainText("PCB 솔더볼 직경 검사 목적 테스트")
        
        # Confirm purpose
        page._on_confirm_clicked()
        
        # Get result
        result = page.get_confirmed_purpose()
        
        # Verify result
        assert result is not None
        assert isinstance(result, InspectionPurpose)
        assert result.inspection_type == "결함검출"  # default selected type
        assert result.description == "PCB 솔더볼 직경 검사 목적 테스트"
        assert result.measurement_unit == "mm"  # default unit
        
    def test_load_purpose_restores_fields(self, qtbot):
        """Test that load_purpose correctly restores all field values."""
        page = PurposePage()
        qtbot.addWidget(page)
        
        # Create test purpose
        test_purpose = InspectionPurpose(
            inspection_type="치수측정",
            description="홀 지름 치수 검사 테스트 입력",
            ok_ng_criteria="지름 0.5mm ± 0.05mm",
            target_feature="홀 지름",
            measurement_unit="mm",
            tolerance="±0.05"
        )
        
        # Load the purpose
        page.load_purpose(test_purpose)
        
        # Verify all fields are restored
        assert page._description_input.toPlainText() == test_purpose.description
        assert page._get_selected_type() == "치수측정"
        assert page._target_input.text() == "홀 지름"
        assert page._criteria_input.text() == "지름 0.5mm ± 0.05mm"
        assert page._tolerance_input.text() == "±0.05"
        assert page._unit_combo.currentText() == "mm"
        
        # Verify example text also updated
        expected_example = "예) 홀 지름 0.5mm ± 0.05mm 범위 이탈 시 NG"
        assert page._example_label.text() == expected_example
        
    def test_confirm_button_size(self, qtbot):
        """Test that confirm button has proper size and is not squished."""
        page = PurposePage()
        qtbot.addWidget(page)
        page.show()
        btn = page._confirm_btn
        print(f"sizeHint: {btn.sizeHint()}")
        print(f"minimumSizeHint: {btn.minimumSizeHint()}")
        print(f"geometry: {btn.geometry()}")
        print(f"fixedHeight: {btn.height()}")
        assert btn.height() >= 48