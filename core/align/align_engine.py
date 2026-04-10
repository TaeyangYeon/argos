"""
Align Fallback Chain Orchestrator — Step 30.

Executes the five Argos align engines in sequence:
  Stage 1: PatternAlignEngine
  Stage 2: CaliperAlignEngine
  Stage 3: FeatureAlignEngine / ContourAlignEngine / BlobAlignEngine
            (order may be re-ranked by an optional AI provider)

Stops on the first successful result and accumulates failure reasons for all
preceding stages.  If all stages fail, returns a synthetic failure AlignResult.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from core.interfaces import IAlignEngine
from core.image_store import ImageStore
from core.logger import get_logger
from core.models import AlignResult, ROIConfig
from core.align.pattern_align import PatternAlignEngine
from core.align.caliper_align import CaliperAlignEngine
from core.align.feature_align import FeatureAlignEngine
from core.align.contour_align import ContourAlignEngine
from core.align.blob_align import BlobAlignEngine


_logger = get_logger("align_fallback")

# ---------------------------------------------------------------------------
# Extended result
# ---------------------------------------------------------------------------

@dataclass
class FallbackAlignResult(AlignResult):
    """AlignResult extended with fallback-chain metadata."""
    design_doc: dict = field(default_factory=dict)
    overlay_image: Optional[np.ndarray] = field(default=None)
    reference_point: Optional[tuple] = field(default=None)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class AlignFallbackChain(IAlignEngine):
    """
    Fallback chain orchestrator that executes up to five align engines in order.

    Execution order
    ---------------
    Stage 1: PatternAlignEngine   (always first)
    Stage 2: CaliperAlignEngine   (always second)
    Stage 3: FeatureAlignEngine, ContourAlignEngine, BlobAlignEngine
              — default order: feature → contour → blob
              — if *ai_provider* is supplied and stages 1+2 both fail,
                the provider is queried once to re-rank these three engines.

    Args:
        image_store:        Repository that provides the reference image.
        roi_config:         Optional ROI passed to engines that support it.
        inspection_purpose: Optional inspection-purpose context (unused internally).
        ai_provider:        Optional object with a ``complete(prompt: str) -> str``
                            method.  When supplied and the first two stages fail,
                            the provider is called to decide the stage-3 order.
    """

    _STAGE3_DEFAULT = ("feature", "contour", "blob")

    def __init__(
        self,
        image_store: ImageStore,
        roi_config: ROIConfig | None,
        inspection_purpose=None,
        ai_provider=None,
    ) -> None:
        self._image_store = image_store
        self._roi_config = roi_config
        self._inspection_purpose = inspection_purpose
        self._ai_provider = ai_provider

    # ------------------------------------------------------------------
    # IAlignEngine interface
    # ------------------------------------------------------------------

    def get_strategy_name(self) -> str:
        return "AlignFallbackChain"

    def get_strategy(self) -> str:
        return "AlignFallbackChain"

    def run(self, image: np.ndarray, reference: np.ndarray | None = None) -> FallbackAlignResult:
        """
        Run the fallback chain against *image*.

        Args:
            image:     Input image to align.
            reference: Optional reference image.  When ``None``, the chain
                       tries to obtain a reference from ``image_store``.

        Returns:
            :class:`FallbackAlignResult` from the first successful engine,
            or a synthetic failure result if all engines fail.
        """
        stages_tried: list[str] = []
        failure_reasons: dict[str, str] = {}
        ai_decision_used = False

        # ── Stage 1: Pattern ────────────────────────────────────────────
        pattern_engine = PatternAlignEngine()
        s1_result = self._run_stage(
            engine=pattern_engine,
            stage_num=1,
            stage_name="pattern",
            image=image,
            reference=reference,
            stages_tried=stages_tried,
            failure_reasons=failure_reasons,
        )
        if s1_result is not None:
            return self._wrap(s1_result, stages_tried, "pattern", failure_reasons, ai_decision_used)

        # ── Stage 2: Caliper ────────────────────────────────────────────
        caliper_engine = CaliperAlignEngine()
        s2_result = self._run_stage(
            engine=caliper_engine,
            stage_num=2,
            stage_name="caliper",
            image=image,
            reference=reference,
            stages_tried=stages_tried,
            failure_reasons=failure_reasons,
        )
        if s2_result is not None:
            return self._wrap(s2_result, stages_tried, "caliper", failure_reasons, ai_decision_used)

        # ── Stage 3: AI strategy decision (optional) ────────────────────
        stage3_order = list(self._STAGE3_DEFAULT)
        if self._ai_provider is not None:
            ai_decision_used = True
            try:
                prompt = self._build_ai_prompt(image, failure_reasons)
                reply = self._ai_provider.complete(prompt)
                stage3_order = self._parse_ai_order(reply)
            except Exception as exc:
                _logger.warning(
                    "[AlignFallback] AI provider call failed (%s); using default order.", exc
                )
                stage3_order = list(self._STAGE3_DEFAULT)

        # ── Stage 3 engines ─────────────────────────────────────────────
        import core.align.align_engine as _self_module  # resolve at runtime so patches work
        _name_to_cls = {
            "feature": _self_module.FeatureAlignEngine,
            "contour": _self_module.ContourAlignEngine,
            "blob": _self_module.BlobAlignEngine,
        }
        for stage_num, name in enumerate(stage3_order, start=3):
            engine_cls = _name_to_cls.get(name)
            if engine_cls is None:
                continue
            engine = engine_cls()
            result = self._run_stage(
                engine=engine,
                stage_num=stage_num,
                stage_name=name,
                image=image,
                reference=reference,
                stages_tried=stages_tried,
                failure_reasons=failure_reasons,
            )
            if result is not None:
                return self._wrap(result, stages_tried, name, failure_reasons, ai_decision_used)

        # ── All failed ──────────────────────────────────────────────────
        combined_reason = "\n".join(
            f"{s}: {r}" for s, r in failure_reasons.items()
        )
        _logger.error("[AlignFallback] Result: all_failed / score=0.000")
        return FallbackAlignResult(
            success=False,
            strategy_name="all_failed",
            score=0.0,
            failure_reason=combined_reason,
            design_doc={
                "chain_stages_tried": stages_tried,
                "winning_strategy": "all_failed",
                "failure_reasons": failure_reasons,
                "ai_strategy_decision": ai_decision_used,
            },
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run_stage(
        self,
        engine: IAlignEngine,
        stage_num: int,
        stage_name: str,
        image: np.ndarray,
        reference: np.ndarray | None,
        stages_tried: list[str],
        failure_reasons: dict[str, str],
    ) -> AlignResult | None:
        """
        Execute a single engine stage.  Returns the result on success,
        ``None`` on failure, and updates *stages_tried* / *failure_reasons*.
        """
        stages_tried.append(stage_name)
        ref = reference if reference is not None else self._get_reference(image)

        try:
            result = engine.run(image, ref)
        except Exception as exc:
            reason = f"exception: {exc}"
            failure_reasons[stage_name] = reason
            _logger.warning(
                "[AlignFallback] Stage %d (%s): FAIL — %s", stage_num, stage_name, reason
            )
            return None

        if result.success:
            _logger.info(
                "[AlignFallback] Stage %d (%s): PASS — score=%.4f",
                stage_num, stage_name, result.score,
            )
            return result

        reason = result.failure_reason or "unknown failure"
        failure_reasons[stage_name] = reason
        _logger.warning(
            "[AlignFallback] Stage %d (%s): FAIL — %s", stage_num, stage_name, reason
        )
        return None

    def _wrap(
        self,
        result: AlignResult,
        stages_tried: list[str],
        winning_strategy: str,
        failure_reasons: dict[str, str],
        ai_decision_used: bool,
    ) -> FallbackAlignResult:
        """Wrap a successful engine result into a FallbackAlignResult."""
        design_doc = {
            "chain_stages_tried": stages_tried,
            "winning_strategy": winning_strategy,
            "failure_reasons": failure_reasons,
            "ai_strategy_decision": ai_decision_used,
        }
        _logger.info(
            "[AlignFallback] Result: %s / score=%.3f", winning_strategy, result.score
        )
        wrapped = FallbackAlignResult(
            success=result.success,
            strategy_name=result.strategy_name,
            score=result.score,
            transform_matrix=result.transform_matrix,
            failure_reason=result.failure_reason,
            design_doc=design_doc,
        )
        # Propagate optional fields if present on the source result
        if hasattr(result, "overlay_image"):
            wrapped.overlay_image = result.overlay_image  # type: ignore[attr-defined]
        return wrapped

    def _get_reference(self, image: np.ndarray) -> np.ndarray:
        """
        Return a reference image.  Attempts to load the first ALIGN_OK image
        from the store; falls back to a blank image of the same shape.
        """
        from core.image_store import ImageType
        try:
            align_ok_list = self._image_store.get_all(ImageType.ALIGN_OK)
            if align_ok_list:
                return self._image_store.load_image(align_ok_list[0].id)
        except Exception:
            pass
        return np.zeros_like(image)

    @staticmethod
    def _build_ai_prompt(image: np.ndarray, failure_reasons: dict[str, str]) -> str:
        h, w = image.shape[:2]
        mean_val = float(np.mean(image))
        std_val = float(np.std(image))
        reasons_text = "; ".join(f"{k}={v}" for k, v in failure_reasons.items())
        return (
            f"Align image size: {w}x{h}, mean={mean_val:.1f}, std={std_val:.1f}.\n"
            f"Failed stages: {reasons_text}.\n"
            "Suggest execution order for: feature, contour, blob. "
            "Reply with a comma-separated list of those three words only."
        )

    @staticmethod
    def _parse_ai_order(reply: str) -> list[str]:
        """
        Extract an ordered list of ['feature','contour','blob'] from *reply*.
        Falls back to the default order if parsing fails or a name is missing.
        """
        valid = {"feature", "contour", "blob"}
        found: list[str] = []
        for token in re.split(r"[\s,;|]+", reply.lower()):
            token = token.strip()
            if token in valid and token not in found:
                found.append(token)
        # Append any missing names in default order
        for name in AlignFallbackChain._STAGE3_DEFAULT:
            if name not in found:
                found.append(name)
        return found
