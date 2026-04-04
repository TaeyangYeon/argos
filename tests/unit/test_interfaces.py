"""
Unit tests for core interfaces, models, and exceptions.

Tests verify that abstract interfaces cannot be instantiated,
dataclasses work correctly, and exception hierarchy is proper.
"""

import pytest
import numpy as np

from core.interfaces import (
    IAlignEngine,
    IEvaluationEngine,
    IFeatureAnalyzer,
    IInspectionEngine
)
from core.models import (
    AlignResult,
    EvaluationResult,
    FeatureAnalysisSummary,
    FeasibilityResult,
    InspectionResult,
    ROIConfig
)
from core.exceptions import (
    AIProviderError,
    InputValidationError,
    OutputValidationError,
    RuntimeProcessingError
)


class TestAbstractInterfaces:
    """Test abstract interfaces cannot be instantiated."""
    
    def test_align_engine_cannot_be_instantiated(self):
        """Test IAlignEngine raises TypeError when instantiated directly."""
        with pytest.raises(TypeError):
            IAlignEngine()
    
    def test_inspection_engine_cannot_be_instantiated(self):
        """Test IInspectionEngine raises TypeError when instantiated directly."""
        with pytest.raises(TypeError):
            IInspectionEngine()
    
    def test_evaluation_engine_cannot_be_instantiated(self):
        """Test IEvaluationEngine raises TypeError when instantiated directly."""
        with pytest.raises(TypeError):
            IEvaluationEngine()
    
    def test_feature_analyzer_cannot_be_instantiated(self):
        """Test IFeatureAnalyzer raises TypeError when instantiated directly."""
        with pytest.raises(TypeError):
            IFeatureAnalyzer()


class TestDataclassModels:
    """Test dataclass models instantiation and field types."""
    
    def test_roi_config_creation(self):
        """Test ROIConfig can be instantiated with correct field types."""
        roi = ROIConfig(x=10, y=20, width=100, height=50)
        
        assert isinstance(roi.x, int)
        assert isinstance(roi.y, int) 
        assert isinstance(roi.width, int)
        assert isinstance(roi.height, int)
        assert roi.x == 10
        assert roi.y == 20
        assert roi.width == 100
        assert roi.height == 50
    
    def test_align_result_creation_with_defaults(self):
        """Test AlignResult with default None fields."""
        result = AlignResult(
            success=True,
            strategy_name="Pattern Matching",
            score=85.5
        )
        
        assert result.success is True
        assert result.strategy_name == "Pattern Matching"
        assert result.score == 85.5
        assert result.transform_matrix is None
        assert result.failure_reason is None
    
    def test_align_result_creation_with_matrix(self):
        """Test AlignResult with provided transform matrix."""
        matrix = np.array([[1, 0, 5], [0, 1, 10]])
        result = AlignResult(
            success=True,
            strategy_name="Caliper",
            score=90.0,
            transform_matrix=matrix
        )
        
        assert result.success is True
        assert result.transform_matrix is not None
        assert np.array_equal(result.transform_matrix, matrix)
    
    def test_inspection_result_creation(self):
        """Test InspectionResult instantiation."""
        result = InspectionResult(
            success=True,
            strategy_name="Blob Detection",
            score=75.0,
            is_ok=True
        )
        
        assert result.success is True
        assert result.strategy_name == "Blob Detection"
        assert result.score == 75.0
        assert result.is_ok is True
        assert result.failure_reason is None
        assert result.overlay_image is None
    
    def test_evaluation_result_creation(self):
        """Test EvaluationResult instantiation."""
        result = EvaluationResult(
            best_strategy="Caliper",
            ok_pass_rate=95.5,
            ng_detect_rate=88.2,
            final_score=91.8,
            margin=15.3,
            is_margin_warning=False
        )
        
        assert result.best_strategy == "Caliper"
        assert result.ok_pass_rate == 95.5
        assert result.ng_detect_rate == 88.2
        assert result.final_score == 91.8
        assert result.margin == 15.3
        assert result.is_margin_warning is False
        assert isinstance(result.fp_images, list)
        assert isinstance(result.fn_images, list)
        assert len(result.fp_images) == 0
        assert len(result.fn_images) == 0
    
    def test_feature_analysis_summary_creation(self):
        """Test FeatureAnalysisSummary instantiation."""
        summary = FeatureAnalysisSummary(
            mean_gray=128.5,
            std_gray=45.2,
            noise_level="Medium",
            edge_density=0.35,
            blob_count=12,
            has_circular_structure=True
        )
        
        assert summary.mean_gray == 128.5
        assert summary.std_gray == 45.2
        assert summary.noise_level == "Medium"
        assert summary.edge_density == 0.35
        assert summary.blob_count == 12
        assert summary.has_circular_structure is True
        assert summary.ai_summary is None
    
    def test_feasibility_result_creation(self):
        """Test FeasibilityResult instantiation."""
        result = FeasibilityResult(
            rule_based_sufficient=False,
            recommended_approach="Deep Learning",
            reasoning="Complex defect patterns require deep learning"
        )
        
        assert result.rule_based_sufficient is False
        assert result.recommended_approach == "Deep Learning"
        assert result.reasoning == "Complex defect patterns require deep learning"
        assert result.model_suggestion is None


class TestCustomExceptions:
    """Test custom exception classes."""
    
    def test_input_validation_error_is_exception_subclass(self):
        """Test InputValidationError is subclass of Exception."""
        assert issubclass(InputValidationError, Exception)
        
        error = InputValidationError("Invalid image format")
        assert isinstance(error, Exception)
        assert str(error) == "Invalid image format"
    
    def test_runtime_processing_error_is_exception_subclass(self):
        """Test RuntimeProcessingError is subclass of Exception."""
        assert issubclass(RuntimeProcessingError, Exception)
        
        error = RuntimeProcessingError("Algorithm execution failed")
        assert isinstance(error, Exception)
        assert str(error) == "Algorithm execution failed"
    
    def test_output_validation_error_is_exception_subclass(self):
        """Test OutputValidationError is subclass of Exception."""
        assert issubclass(OutputValidationError, Exception)
        
        error = OutputValidationError("Score below threshold")
        assert isinstance(error, Exception)
        assert str(error) == "Score below threshold"
    
    def test_ai_provider_error_is_exception_subclass(self):
        """Test AIProviderError is subclass of Exception."""
        assert issubclass(AIProviderError, Exception)
        
        error = AIProviderError("API timeout")
        assert isinstance(error, Exception)
        assert str(error) == "API timeout"