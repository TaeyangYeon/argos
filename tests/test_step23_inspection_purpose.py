"""
Tests for InspectionPurpose dataclass and PurposeValidator.
"""

import pytest
from core.models import InspectionPurpose
from core.validators import PurposeValidator
from core.exceptions import InputValidationError


def test_inspection_purpose_dataclass():
    """Test InspectionPurpose dataclass instantiation and created_at field."""
    purpose = InspectionPurpose(
        inspection_type="치수측정",
        description="홀의 지름을 정확하게 측정하여 규격 내 치수인지 검증",
        ok_ng_criteria="지름 오차 ±0.1mm 이내",
        target_feature="홀 지름",
        measurement_unit="mm",
        tolerance="±0.1"
    )
    
    assert purpose.inspection_type == "치수측정"
    assert purpose.description == "홀의 지름을 정확하게 측정하여 규격 내 치수인지 검증"
    assert purpose.ok_ng_criteria == "지름 오차 ±0.1mm 이내"
    assert purpose.target_feature == "홀 지름"
    assert purpose.measurement_unit == "mm"
    assert purpose.tolerance == "±0.1"
    assert isinstance(purpose.created_at, str)
    assert purpose.created_at != ""


def test_validate_empty_description_raises():
    """Test that empty description raises InputValidationError."""
    purpose = InspectionPurpose(
        inspection_type="치수측정",
        description=""
    )
    
    with pytest.raises(InputValidationError, match="검사 설명이 비어있습니다."):
        PurposeValidator.validate_purpose(purpose)


def test_validate_short_description_raises():
    """Test that description shorter than 10 characters raises InputValidationError."""
    purpose = InspectionPurpose(
        inspection_type="치수측정",
        description="123456789"  # 9 characters
    )
    
    with pytest.raises(InputValidationError, match="검사 설명을 10자 이상 입력해주세요."):
        PurposeValidator.validate_purpose(purpose)


def test_validate_valid_purpose():
    """Test that valid purpose with 10+ character description and non-empty type passes validation."""
    purpose = InspectionPurpose(
        inspection_type="치수측정",
        description="1234567890"  # exactly 10 characters
    )
    
    # Should not raise any exception
    PurposeValidator.validate_purpose(purpose)


def test_validate_empty_type_raises():
    """Test that empty inspection_type raises InputValidationError."""
    purpose = InspectionPurpose(
        inspection_type="",
        description="Valid description with more than 10 characters"
    )
    
    with pytest.raises(InputValidationError, match="검사 유형이 비어있습니다."):
        PurposeValidator.validate_purpose(purpose)