"""
Feature analysis integration and AI summary for the Argos vision algorithm design system.

This module provides comprehensive feature analysis by combining histogram, noise, edge, 
and shape analysis results into a unified summary suitable for AI provider input.
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np

from core.analyzers.edge_analyzer import EdgeAnalyzer, EdgeAnalysisResult
from core.analyzers.histogram_analyzer import HistogramAnalyzer, HistogramAnalysisResult
from core.analyzers.noise_analyzer import NoiseAnalyzer, NoiseAnalysisResult
from core.analyzers.shape_analyzer import ShapeAnalyzer, ShapeAnalysisResult
from core.exceptions import RuntimeProcessingError
from core.interfaces import IFeatureAnalyzer
from core.logger import get_logger
from core.models import FeatureAnalysisSummary
from config.paths import OUTPUT_DIR


@dataclass
class FullFeatureAnalysis:
    """Complete feature analysis result including all component analyses."""
    image_path: str
    image_width: int
    image_height: int
    histogram: HistogramAnalysisResult
    noise: NoiseAnalysisResult
    edge: EdgeAnalysisResult
    shape: ShapeAnalysisResult
    summary: FeatureAnalysisSummary
    ai_prompt: str
    analyzed_at: str   # ISO datetime string


class FeatureAnalyzer(IFeatureAnalyzer):
    """
    Integrated feature analyzer that combines all analysis types.
    
    Implements IFeatureAnalyzer interface by orchestrating histogram, noise, 
    edge, and shape analyzers to provide comprehensive feature analysis.
    """
    
    def __init__(self, ai_provider=None):
        """
        Initialize feature analyzer with optional AI provider.
        
        Args:
            ai_provider: IAIProvider instance or None to skip AI analysis
        """
        self._ai_provider = ai_provider
        self._logger = get_logger("feature_analyzer")
        self._last_summary: Optional[FeatureAnalysisSummary] = None
        
        # Initialize component analyzers
        self._histogram_analyzer = HistogramAnalyzer()
        self._noise_analyzer = NoiseAnalyzer()
        self._edge_analyzer = EdgeAnalyzer()
        self._shape_analyzer = ShapeAnalyzer()
    
    def analyze(self, image: np.ndarray) -> FeatureAnalysisSummary:
        """
        Analyze image features using all component analyzers.
        
        Args:
            image: Input image to analyze
            
        Returns:
            FeatureAnalysisSummary with extracted features
        """
        self._logger.debug("Starting comprehensive feature analysis")
        
        # Run all component analyzers
        histogram_result = self._histogram_analyzer.analyze_single(image)
        noise_result = self._noise_analyzer.analyze(image)
        edge_result = self._edge_analyzer.analyze(image)
        shape_result = self._shape_analyzer.analyze(image)
        
        # Build unified summary
        summary = FeatureAnalysisSummary(
            mean_gray=histogram_result.mean_gray,
            std_gray=histogram_result.std_gray,
            noise_level=noise_result.noise_level,
            edge_density=edge_result.edge_density,
            blob_count=shape_result.blob_count,
            has_circular_structure=shape_result.has_circular_structure,
            ai_summary=None  # Will be filled by analyze_full if AI provider is available
        )
        
        # Store for get_summary()
        self._last_summary = summary
        
        return summary
    
    def get_summary(self) -> str:
        """
        Get human-readable summary of the last analysis.
        
        Returns:
            Text summary suitable for display
            
        Raises:
            RuntimeProcessingError: If no analysis has been performed yet
        """
        self._logger.debug("Generating text summary of analysis results")
        
        if self._last_summary is None:
            RuntimeProcessingError.raise_with_log(
                "No analysis has been performed yet. Call analyze() first.",
                self._logger
            )
        
        summary = self._last_summary
        
        text = f"""이미지 특성 분석 결과:
- 평균 밝기: {summary.mean_gray:.1f}
- 표준편차: {summary.std_gray:.1f}
- 노이즈 수준: {summary.noise_level}
- 에지 밀도: {summary.edge_density:.4f}
- 검출된 Blob 수: {summary.blob_count}
- 원형 구조: {'있음' if summary.has_circular_structure else '없음'}"""
        
        if summary.ai_summary:
            text += f"\n\nAI 분석: {summary.ai_summary}"
        
        return text
    
    def analyze_full(self, image: np.ndarray, image_path: str = "") -> FullFeatureAnalysis:
        """
        Perform full analysis including AI summary generation.
        
        Args:
            image: Input image to analyze
            image_path: Path to image file (optional)
            
        Returns:
            FullFeatureAnalysis with all component results and AI analysis
        """
        self._logger.debug("Starting full feature analysis with AI integration")
        
        # Get image dimensions
        image_height, image_width = image.shape[:2]
        
        # Run component analyzers
        histogram_result = self._histogram_analyzer.analyze_single(image)
        noise_result = self._noise_analyzer.analyze(image)
        edge_result = self._edge_analyzer.analyze(image)
        shape_result = self._shape_analyzer.analyze(image)
        
        # Build AI prompt
        ai_prompt = self._build_ai_prompt(
            histogram_result, noise_result, edge_result, shape_result,
            image_width, image_height
        )
        
        # Get AI analysis if provider available
        ai_summary = None
        if self._ai_provider is not None:
            try:
                ai_summary = self._ai_provider.analyze_safe(
                    ai_prompt,
                    fallback="AI 분석을 사용할 수 없습니다."
                )
            except Exception as e:
                self._logger.warning(f"AI analysis failed: {e}")
                ai_summary = "AI 분석을 사용할 수 없습니다."
        else:
            ai_summary = "AI 분석을 사용할 수 없습니다."
        
        # Build unified summary
        summary = FeatureAnalysisSummary(
            mean_gray=histogram_result.mean_gray,
            std_gray=histogram_result.std_gray,
            noise_level=noise_result.noise_level,
            edge_density=edge_result.edge_density,
            blob_count=shape_result.blob_count,
            has_circular_structure=shape_result.has_circular_structure,
            ai_summary=ai_summary
        )
        
        # Store for get_summary()
        self._last_summary = summary
        
        # Create full analysis result
        full_analysis = FullFeatureAnalysis(
            image_path=image_path,
            image_width=image_width,
            image_height=image_height,
            histogram=histogram_result,
            noise=noise_result,
            edge=edge_result,
            shape=shape_result,
            summary=summary,
            ai_prompt=ai_prompt,
            analyzed_at=datetime.utcnow().isoformat() + "Z"
        )
        
        return full_analysis
    
    def analyze_ok_ng_separation(self, ok_images: list[np.ndarray], 
                                ng_images: list[np.ndarray]) -> dict:
        """
        Analyze OK/NG separation using histogram and edge comparison.
        
        Args:
            ok_images: List of OK sample images
            ng_images: List of NG sample images
            
        Returns:
            Dictionary with separation analysis results
            
        Raises:
            RuntimeProcessingError: If either image list is empty
        """
        self._logger.debug("Analyzing OK/NG separation characteristics")
        
        if not ok_images:
            RuntimeProcessingError.raise_with_log(
                "OK images list is empty",
                self._logger
            )
        
        if not ng_images:
            RuntimeProcessingError.raise_with_log(
                "NG images list is empty", 
                self._logger
            )
        
        # Get histogram separation analysis
        histogram_separation = self._histogram_analyzer.analyze_separation(ok_images, ng_images)
        
        # Get edge comparison
        edge_comparison = self._edge_analyzer.compare_ok_ng(ok_images, ng_images)
        
        # Get separation score (default to 0.0 if None)
        separation_score = histogram_separation.separation_score or 0.0
        
        # Generate recommendation based on separation score
        if separation_score >= 40:
            recommendation = "히스토그램/밝기 기반 검사 적합"
        elif separation_score >= 20:
            recommendation = "에지 기반 검사 권장"
        else:
            recommendation = "딥러닝 또는 엣지러닝 검토 필요"
        
        return {
            "histogram_separation": histogram_separation,
            "edge_comparison": edge_comparison,
            "separation_score": separation_score,
            "recommendation": recommendation
        }
    
    def save_result(self, result: FullFeatureAnalysis, output_dir: Path = OUTPUT_DIR) -> Path:
        """
        Save analysis result to JSON file.
        
        Args:
            result: Full feature analysis result to save
            output_dir: Output directory (default: OUTPUT_DIR)
            
        Returns:
            Path to saved file
        """
        self._logger.debug("Saving feature analysis result to JSON")
        
        # Ensure output directory exists
        output_dir.mkdir(exist_ok=True, parents=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"feature_{timestamp}.json"
        file_path = output_dir / filename
        
        # Custom serialization function to handle numpy arrays and Path objects
        def json_default(obj):
            if isinstance(obj, np.ndarray):
                return None  # Not serializable, convert to None
            if isinstance(obj, Path):
                return str(obj)
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
        
        # Convert to dictionary and save
        try:
            result_dict = asdict(result)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(result_dict, f, ensure_ascii=False, indent=2, default=json_default)
            
            self._logger.debug(f"Analysis result saved to: {file_path}")
            return file_path
            
        except Exception as e:
            RuntimeProcessingError.raise_with_log(
                f"Failed to save analysis result: {e}",
                self._logger
            )
    
    def _build_ai_prompt(self, histogram: HistogramAnalysisResult,
                        noise: NoiseAnalysisResult,
                        edge: EdgeAnalysisResult,
                        shape: ShapeAnalysisResult,
                        image_width: int,
                        image_height: int) -> str:
        """
        Build structured prompt for AI provider analysis.
        
        Args:
            histogram: Histogram analysis result
            noise: Noise analysis result
            edge: Edge analysis result
            shape: Shape analysis result
            image_width: Image width in pixels
            image_height: Image height in pixels
            
        Returns:
            Formatted AI prompt string
        """
        prompt = f"""You are an expert vision algorithm engineer.
Analyze the following image features and provide a concise technical summary in Korean (2-3 sentences).
Focus on: image quality, dominant features, and recommended inspection approach.

Image Properties:
- Size: {image_width} x {image_height} px
- Mean Gray: {histogram.mean_gray:.1f}, Std: {histogram.std_gray:.1f}
- Dynamic Range: {histogram.dynamic_range}
- Distribution: {histogram.distribution_type}

Noise Analysis:
- Level: {noise.noise_level}
- Laplacian Variance: {noise.laplacian_variance:.2f}
- Recommended Filter: {noise.recommended_filter}

Edge Analysis:
- Mean Strength: {edge.mean_edge_strength:.2f}
- Edge Density: {edge.edge_density:.4f}
- Dominant Direction: {edge.dominant_direction}
- Suitable for Caliper: {edge.is_suitable_for_caliper}

Shape Analysis:
- Blob Count: {shape.blob_count}
- Has Circular Structure: {shape.has_circular_structure}
- Repeating Pattern: {shape.has_repeating_pattern}
- Suggested Methods: {', '.join(shape.suggest_inspection_method(shape)) if hasattr(shape, 'suggest_inspection_method') else 'N/A'}

Provide analysis summary in Korean:"""
        
        return prompt