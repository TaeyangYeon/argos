"""
Step 30 — AlignFallbackChain 유닛 테스트

All 12 tests must pass with:
    pytest tests/unit/test_step30_align_fallback.py -v
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch, call

import numpy as np
import pytest

from core.align.align_engine import AlignFallbackChain
from core.image_store import ImageStore
from core.models import AlignResult, ROIConfig


# ─── Helpers ─────────────────────────────────────────────────────────────────

def make_image() -> np.ndarray:
    return np.zeros((100, 100, 3), dtype=np.uint8)


def _ok_result(strategy: str = "pattern_matching", score: float = 0.9) -> AlignResult:
    return AlignResult(success=True, strategy_name=strategy, score=score)


def _fail_result(strategy: str, reason: str = "low score") -> AlignResult:
    return AlignResult(success=False, strategy_name=strategy, score=0.0, failure_reason=reason)


def _make_chain(ai_provider=None) -> AlignFallbackChain:
    store = MagicMock(spec=ImageStore)
    store.get_all.return_value = []          # no reference images → zeros fallback
    return AlignFallbackChain(
        image_store=store,
        roi_config=None,
        ai_provider=ai_provider,
    )


# ─── Tests ───────────────────────────────────────────────────────────────────

class TestAlignFallbackChain:

    # 1. Pattern succeeds — no fallback
    @patch("core.align.align_engine.PatternAlignEngine")
    def test_pattern_success_no_fallback(self, MockPattern):
        MockPattern.return_value.run.return_value = _ok_result("Pattern Matching")
        MockPattern.return_value.get_strategy_name.return_value = "Pattern Matching"

        chain = _make_chain()
        result = chain.run(make_image())

        assert result.success is True
        assert result.design_doc["winning_strategy"] == "pattern"
        assert result.design_doc["chain_stages_tried"] == ["pattern"]

    # 2. Pattern fails → Caliper succeeds
    @patch("core.align.align_engine.CaliperAlignEngine")
    @patch("core.align.align_engine.PatternAlignEngine")
    def test_caliper_fallback_on_pattern_fail(self, MockPattern, MockCaliper):
        MockPattern.return_value.run.return_value = _fail_result("Pattern Matching", "score low")
        MockPattern.return_value.get_strategy_name.return_value = "Pattern Matching"
        MockCaliper.return_value.run.return_value = _ok_result("Caliper", 0.85)
        MockCaliper.return_value.get_strategy_name.return_value = "Caliper"

        chain = _make_chain()
        result = chain.run(make_image())

        assert result.success is True
        assert result.design_doc["winning_strategy"] == "caliper"
        assert result.design_doc["chain_stages_tried"] == ["pattern", "caliper"]

    # 3. Pattern + Caliper fail → Feature succeeds
    @patch("core.align.align_engine.FeatureAlignEngine")
    @patch("core.align.align_engine.CaliperAlignEngine")
    @patch("core.align.align_engine.PatternAlignEngine")
    def test_feature_fallback_stage3(self, MockPattern, MockCaliper, MockFeature):
        MockPattern.return_value.run.return_value = _fail_result("Pattern Matching")
        MockCaliper.return_value.run.return_value = _fail_result("Caliper")
        MockFeature.return_value.run.return_value = _ok_result("Feature", 0.8)
        MockFeature.return_value.get_strategy_name.return_value = "Feature"

        chain = _make_chain()
        result = chain.run(make_image())

        assert result.success is True
        assert result.design_doc["winning_strategy"] == "feature"
        assert "feature" in result.design_doc["chain_stages_tried"]

    # 4. Pattern + Caliper + Feature fail → Contour succeeds
    @patch("core.align.align_engine.ContourAlignEngine")
    @patch("core.align.align_engine.FeatureAlignEngine")
    @patch("core.align.align_engine.CaliperAlignEngine")
    @patch("core.align.align_engine.PatternAlignEngine")
    def test_contour_fallback(self, MockPattern, MockCaliper, MockFeature, MockContour):
        MockPattern.return_value.run.return_value = _fail_result("Pattern Matching")
        MockCaliper.return_value.run.return_value = _fail_result("Caliper")
        MockFeature.return_value.run.return_value = _fail_result("Feature")
        MockContour.return_value.run.return_value = _ok_result("Contour", 0.7)
        MockContour.return_value.get_strategy_name.return_value = "Contour"

        chain = _make_chain()
        result = chain.run(make_image())

        assert result.success is True
        assert result.design_doc["winning_strategy"] == "contour"

    # 5. All except Blob fail → Blob succeeds
    @patch("core.align.align_engine.BlobAlignEngine")
    @patch("core.align.align_engine.ContourAlignEngine")
    @patch("core.align.align_engine.FeatureAlignEngine")
    @patch("core.align.align_engine.CaliperAlignEngine")
    @patch("core.align.align_engine.PatternAlignEngine")
    def test_blob_fallback(self, MockPattern, MockCaliper, MockFeature, MockContour, MockBlob):
        MockPattern.return_value.run.return_value = _fail_result("Pattern Matching")
        MockCaliper.return_value.run.return_value = _fail_result("Caliper")
        MockFeature.return_value.run.return_value = _fail_result("Feature")
        MockContour.return_value.run.return_value = _fail_result("Contour")
        MockBlob.return_value.run.return_value = _ok_result("Blob", 0.6)
        MockBlob.return_value.get_strategy_name.return_value = "Blob"

        chain = _make_chain()
        result = chain.run(make_image())

        assert result.success is True
        assert result.design_doc["winning_strategy"] == "blob"

    # 6. All 5 fail → success == False, strategy == "all_failed"
    @patch("core.align.align_engine.BlobAlignEngine")
    @patch("core.align.align_engine.ContourAlignEngine")
    @patch("core.align.align_engine.FeatureAlignEngine")
    @patch("core.align.align_engine.CaliperAlignEngine")
    @patch("core.align.align_engine.PatternAlignEngine")
    def test_all_fail_returns_failure(self, MockP, MockC, MockF, MockCo, MockB):
        for mock, name in [
            (MockP, "Pattern Matching"), (MockC, "Caliper"),
            (MockF, "Feature"), (MockCo, "Contour"), (MockB, "Blob"),
        ]:
            mock.return_value.run.return_value = _fail_result(name, "fail")

        chain = _make_chain()
        result = chain.run(make_image())

        assert result.success is False
        assert result.strategy_name == "all_failed"

    # 7. All fail → failure_reason contains all 5 stage names
    @patch("core.align.align_engine.BlobAlignEngine")
    @patch("core.align.align_engine.ContourAlignEngine")
    @patch("core.align.align_engine.FeatureAlignEngine")
    @patch("core.align.align_engine.CaliperAlignEngine")
    @patch("core.align.align_engine.PatternAlignEngine")
    def test_all_fail_accumulates_reasons(self, MockP, MockC, MockF, MockCo, MockB):
        for mock, name, reason in [
            (MockP, "Pattern Matching", "p fail"),
            (MockC, "Caliper", "c fail"),
            (MockF, "Feature", "f fail"),
            (MockCo, "Contour", "co fail"),
            (MockB, "Blob", "b fail"),
        ]:
            mock.return_value.run.return_value = _fail_result(name, reason)

        chain = _make_chain()
        result = chain.run(make_image())

        assert result.failure_reason is not None
        for stage_name in ("pattern", "caliper", "feature", "contour", "blob"):
            assert stage_name in result.failure_reason

    # 8. Winning at stage 2 → stages_tried has exactly 2 entries
    @patch("core.align.align_engine.CaliperAlignEngine")
    @patch("core.align.align_engine.PatternAlignEngine")
    def test_design_doc_chain_stages_tried(self, MockPattern, MockCaliper):
        MockPattern.return_value.run.return_value = _fail_result("Pattern Matching")
        MockCaliper.return_value.run.return_value = _ok_result("Caliper")

        chain = _make_chain()
        result = chain.run(make_image())

        assert len(result.design_doc["chain_stages_tried"]) == 2

    # 9. failure_reasons dict has correct stage keys
    @patch("core.align.align_engine.FeatureAlignEngine")
    @patch("core.align.align_engine.CaliperAlignEngine")
    @patch("core.align.align_engine.PatternAlignEngine")
    def test_design_doc_failure_reasons_dict(self, MockPattern, MockCaliper, MockFeature):
        MockPattern.return_value.run.return_value = _fail_result("Pattern Matching", "pf")
        MockCaliper.return_value.run.return_value = _fail_result("Caliper", "cf")
        MockFeature.return_value.run.return_value = _ok_result("Feature")

        chain = _make_chain()
        result = chain.run(make_image())

        reasons = result.design_doc["failure_reasons"]
        assert isinstance(reasons, dict)
        assert "pattern" in reasons
        assert "caliper" in reasons
        assert "feature" not in reasons  # feature succeeded

    # 10. ai_provider.complete never called if Pattern succeeds
    @patch("core.align.align_engine.PatternAlignEngine")
    def test_ai_decision_not_called_if_pattern_succeeds(self, MockPattern):
        MockPattern.return_value.run.return_value = _ok_result("Pattern Matching")

        ai = MagicMock()
        chain = _make_chain(ai_provider=ai)
        chain.run(make_image())

        ai.complete.assert_not_called()

    # 11. ai_provider.complete called exactly once when stages 1+2 fail
    @patch("core.align.align_engine.FeatureAlignEngine")
    @patch("core.align.align_engine.CaliperAlignEngine")
    @patch("core.align.align_engine.PatternAlignEngine")
    def test_ai_decision_called_after_2_failures(self, MockPattern, MockCaliper, MockFeature):
        MockPattern.return_value.run.return_value = _fail_result("Pattern Matching")
        MockCaliper.return_value.run.return_value = _fail_result("Caliper")
        MockFeature.return_value.run.return_value = _ok_result("Feature")

        ai = MagicMock()
        ai.complete.return_value = "feature, contour, blob"

        chain = _make_chain(ai_provider=ai)
        chain.run(make_image())

        ai.complete.assert_called_once()

    # 12. No ai_provider → stages 3-5 run in default order
    @patch("core.align.align_engine.BlobAlignEngine")
    @patch("core.align.align_engine.ContourAlignEngine")
    @patch("core.align.align_engine.FeatureAlignEngine")
    @patch("core.align.align_engine.CaliperAlignEngine")
    @patch("core.align.align_engine.PatternAlignEngine")
    def test_ai_provider_none_uses_default_order(self, MockP, MockC, MockF, MockCo, MockB):
        MockP.return_value.run.return_value = _fail_result("Pattern Matching")
        MockC.return_value.run.return_value = _fail_result("Caliper")
        MockF.return_value.run.return_value = _fail_result("Feature")
        MockCo.return_value.run.return_value = _fail_result("Contour")
        MockB.return_value.run.return_value = _ok_result("Blob")

        chain = _make_chain(ai_provider=None)   # no AI
        result = chain.run(make_image())

        tried = result.design_doc["chain_stages_tried"]
        # Default stage-3 order: feature → contour → blob
        assert tried.index("feature") < tried.index("contour") < tried.index("blob")
        assert result.design_doc["ai_strategy_decision"] is False
