"""
Tests for FailureAnalyzer (Argos Step 41).

Coverage:
  □ FP/FN extraction from OptimizationResult
  □ Overlay image file creation on disk
  □ AI success path — cause_summary and improvement_directions populated
  □ AI failure path — graceful degradation ("AI 분석 불가")
  □ Zero FP / zero FN edge cases
  □ FailureAnalysisResult field completeness
"""

import os
import tempfile
import types
from unittest.mock import MagicMock, patch

import pytest

from core.evaluation.failure_analyzer import FailureAnalyzer, _parse_ai_response
from core.models import EvaluationResult, FailureAnalysisResult, OptimizationResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_eval_result(
    fp_images: list[str] | None = None,
    fn_images: list[str] | None = None,
    ok_pass_rate: float = 0.8,
    ng_detect_rate: float = 0.75,
    final_score: float = 77.5,
    margin: float = 55.0,
    is_margin_warning: bool = False,
) -> EvaluationResult:
    return EvaluationResult(
        best_strategy="Blob Inspection",
        ok_pass_rate=ok_pass_rate,
        ng_detect_rate=ng_detect_rate,
        final_score=final_score,
        margin=margin,
        is_margin_warning=is_margin_warning,
        fp_images=fp_images or [],
        fn_images=fn_images or [],
    )


def _make_candidate(engine_name: str = "Blob Inspection") -> MagicMock:
    c = MagicMock()
    c.engine_name = engine_name
    return c


def _make_opt_result(
    fp_images: list[str] | None = None,
    fn_images: list[str] | None = None,
    engine_name: str = "Blob Inspection",
) -> OptimizationResult:
    evaluation = _make_eval_result(fp_images=fp_images, fn_images=fn_images)
    candidate = _make_candidate(engine_name)
    return OptimizationResult(
        best_candidate=candidate,
        best_evaluation=evaluation,
    )


@pytest.fixture
def tmp_output(tmp_path) -> str:
    return str(tmp_path)


@pytest.fixture
def analyzer(tmp_output) -> FailureAnalyzer:
    return FailureAnalyzer(ai_provider=None, output_dir=tmp_output)


# ---------------------------------------------------------------------------
# 1 — Return type
# ---------------------------------------------------------------------------

class TestReturnType:
    def test_returns_failure_analysis_result_type(self, analyzer):
        opt = _make_opt_result()
        result = analyzer.analyze(opt)
        assert isinstance(result, FailureAnalysisResult)


# ---------------------------------------------------------------------------
# 2 — FP / FN extraction
# ---------------------------------------------------------------------------

class TestCountExtraction:
    def test_fp_count_matches_evaluation(self, analyzer):
        opt = _make_opt_result(fp_images=["ok_0", "ok_2"])
        result = analyzer.analyze(opt)
        assert result.fp_count == 2

    def test_fn_count_matches_evaluation(self, analyzer):
        opt = _make_opt_result(fn_images=["ng_0", "ng_1", "ng_3"])
        result = analyzer.analyze(opt)
        assert result.fn_count == 3

    def test_zero_fp_count(self, analyzer):
        opt = _make_opt_result(fp_images=[])
        result = analyzer.analyze(opt)
        assert result.fp_count == 0

    def test_zero_fn_count(self, analyzer):
        opt = _make_opt_result(fn_images=[])
        result = analyzer.analyze(opt)
        assert result.fn_count == 0

    def test_zero_fp_and_fn(self, analyzer):
        opt = _make_opt_result(fp_images=[], fn_images=[])
        result = analyzer.analyze(opt)
        assert result.fp_count == 0
        assert result.fn_count == 0


# ---------------------------------------------------------------------------
# 3 — Overlay image generation
# ---------------------------------------------------------------------------

class TestOverlayGeneration:
    def test_fp_overlay_files_created(self, analyzer):
        opt = _make_opt_result(fp_images=["ok_0", "ok_1"])
        result = analyzer.analyze(opt)
        assert len(result.fp_overlay_paths) == 2
        for p in result.fp_overlay_paths:
            assert os.path.isfile(p), f"overlay not found: {p}"

    def test_fn_overlay_files_created(self, analyzer):
        opt = _make_opt_result(fn_images=["ng_0"])
        result = analyzer.analyze(opt)
        assert len(result.fn_overlay_paths) == 1
        assert os.path.isfile(result.fn_overlay_paths[0])

    def test_zero_fp_no_overlays(self, analyzer):
        opt = _make_opt_result(fp_images=[])
        result = analyzer.analyze(opt)
        assert result.fp_overlay_paths == []

    def test_zero_fn_no_overlays(self, analyzer):
        opt = _make_opt_result(fn_images=[])
        result = analyzer.analyze(opt)
        assert result.fn_overlay_paths == []

    def test_overlay_has_png_extension(self, analyzer):
        opt = _make_opt_result(fp_images=["ok_0"])
        result = analyzer.analyze(opt)
        assert result.fp_overlay_paths[0].endswith(".png")

    def test_overlay_path_is_absolute(self, analyzer):
        opt = _make_opt_result(fp_images=["ok_0"])
        result = analyzer.analyze(opt)
        assert os.path.isabs(result.fp_overlay_paths[0])

    def test_fp_overlay_count_matches_fp_images(self, analyzer):
        opt = _make_opt_result(fp_images=["ok_0", "ok_1", "ok_2"])
        result = analyzer.analyze(opt)
        assert len(result.fp_overlay_paths) == 3

    def test_fn_overlay_count_matches_fn_images(self, analyzer):
        opt = _make_opt_result(fn_images=["ng_0", "ng_1"])
        result = analyzer.analyze(opt)
        assert len(result.fn_overlay_paths) == 2


# ---------------------------------------------------------------------------
# 4 — AI success path
# ---------------------------------------------------------------------------

class TestAISuccess:
    def test_ai_cause_summary_populated(self, tmp_output):
        ai = MagicMock()
        ai.analyze_safe.return_value = (
            "파라미터 임계값이 너무 낮아 정상 이미지에서 오탐이 발생합니다.\n"
            "- 임계값을 높이세요.\n"
            "- 추가 학습 데이터를 확보하세요.\n"
        )
        analyzer = FailureAnalyzer(ai_provider=ai, output_dir=tmp_output)
        opt = _make_opt_result(fp_images=["ok_0"])
        result = analyzer.analyze(opt)
        assert result.cause_summary != "AI 분석 불가"
        assert len(result.cause_summary) > 0

    def test_ai_improvement_directions_populated(self, tmp_output):
        ai = MagicMock()
        ai.analyze_safe.return_value = (
            "엔진 설정 문제로 인한 성능 저하.\n"
            "- 임계값 조정\n"
            "- 전처리 필터 추가\n"
            "- 샘플 데이터 보강\n"
        )
        analyzer = FailureAnalyzer(ai_provider=ai, output_dir=tmp_output)
        opt = _make_opt_result(fn_images=["ng_0"])
        result = analyzer.analyze(opt)
        assert isinstance(result.improvement_directions, list)
        assert len(result.improvement_directions) >= 1

    def test_ai_prompt_contains_engine_name(self, tmp_output):
        ai = MagicMock()
        ai.analyze_safe.return_value = "원인 요약.\n- 개선 방향.\n"
        analyzer = FailureAnalyzer(ai_provider=ai, output_dir=tmp_output)
        opt = _make_opt_result(engine_name="Pattern Inspection")
        analyzer.analyze(opt)
        prompt_arg = ai.analyze_safe.call_args[0][0]
        assert "Pattern Inspection" in prompt_arg


# ---------------------------------------------------------------------------
# 5 — AI failure / None provider path
# ---------------------------------------------------------------------------

class TestAIFailure:
    def test_ai_none_provider_graceful(self, analyzer):
        # analyzer fixture uses ai_provider=None
        opt = _make_opt_result()
        result = analyzer.analyze(opt)
        assert result.cause_summary == "AI 분석 불가"
        assert result.improvement_directions == []

    def test_ai_exception_graceful_degradation(self, tmp_output):
        ai = MagicMock()
        ai.analyze_safe.side_effect = RuntimeError("network error")
        analyzer = FailureAnalyzer(ai_provider=ai, output_dir=tmp_output)
        opt = _make_opt_result(fp_images=["ok_0"])
        result = analyzer.analyze(opt)
        assert result.cause_summary == "AI 분석 불가"
        assert result.improvement_directions == []


# ---------------------------------------------------------------------------
# 6 — FailureAnalysisResult field completeness
# ---------------------------------------------------------------------------

class TestResultFields:
    def test_improvement_directions_is_list(self, analyzer):
        opt = _make_opt_result()
        result = analyzer.analyze(opt)
        assert isinstance(result.improvement_directions, list)

    def test_fp_overlay_paths_is_list(self, analyzer):
        opt = _make_opt_result()
        result = analyzer.analyze(opt)
        assert isinstance(result.fp_overlay_paths, list)

    def test_fn_overlay_paths_is_list(self, analyzer):
        opt = _make_opt_result()
        result = analyzer.analyze(opt)
        assert isinstance(result.fn_overlay_paths, list)


# ---------------------------------------------------------------------------
# 7 — _parse_ai_response unit tests
# ---------------------------------------------------------------------------

class TestParseAIResponse:
    def test_empty_response_returns_fallback(self):
        summary, directions = _parse_ai_response("")
        assert summary == "AI 분석 불가"
        assert directions == []

    def test_bullet_lines_become_directions(self):
        response = "원인 요약입니다.\n- 방향 1\n- 방향 2\n"
        summary, directions = _parse_ai_response(response)
        assert "방향 1" in directions
        assert "방향 2" in directions

    def test_numbered_lines_become_directions(self):
        response = "원인 요약.\n1. 방향 A\n2. 방향 B\n"
        _, directions = _parse_ai_response(response)
        assert "방향 A" in directions

    def test_non_bullet_lines_become_summary(self):
        response = "이것은 원인 요약입니다.\n추가 설명입니다.\n"
        summary, _ = _parse_ai_response(response)
        assert "이것은 원인 요약입니다." in summary
