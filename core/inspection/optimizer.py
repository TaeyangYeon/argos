"""
Inspection Optimization Loop (Argos Step 40).

Iterates all EngineCandidate objects, evaluates each with InspectionEvaluator,
sorts by score descending, and selects the best candidate.
"""

from __future__ import annotations

import logging
import types

from core.evaluation.evaluator import InspectionEvaluator
from core.exceptions import RuntimeProcessingError
from core.inspection.blob_inspector import BlobInspectionEngine
from core.inspection.circular_caliper_inspector import CircularCaliperInspectionEngine
from core.inspection.linear_caliper_inspector import LinearCaliperInspectionEngine
from core.inspection.pattern_inspector import PatternInspectionEngine
from core.models import EvaluationResult, OptimizationResult

logger = logging.getLogger("argos.inspection.optimizer")

# Dispatch table: engine_type string → engine class.
# All engine-class validation goes through this dict — no if/elif chains.
ENGINE_REGISTRY: dict[str, type] = {
    "blob": BlobInspectionEngine,
    "circular_caliper": CircularCaliperInspectionEngine,
    "linear_caliper": LinearCaliperInspectionEngine,
    "pattern": PatternInspectionEngine,
}

# Reverse map: engine_class → engine_type key (for candidates that carry engine_class
# instead of an engine_type string, e.g. real EngineCandidate objects).
_CLASS_TO_TYPE: dict[type, str] = {cls: key for key, cls in ENGINE_REGISTRY.items()}


def _resolve_score(eval_result: object) -> float:
    """
    Extract a numeric score from an evaluation result.

    Tries ``final_score`` first (EvaluationResult), then ``score``
    (duck-typed / MagicMock-based results).  Returns 0.0 if neither
    attribute holds a real number.
    """
    for attr in ("final_score", "score"):
        val = getattr(eval_result, attr, None)
        if isinstance(val, (int, float)):
            return float(val)
    return 0.0


def _zero_evaluation(engine_name: str) -> types.SimpleNamespace:
    """
    Return a duck-typed zero evaluation object for a failed candidate.

    Uses SimpleNamespace instead of EvaluationResult so that callers
    can access both ``.score`` (duck-typed / smoke-test convention) and
    ``.final_score`` (EvaluationResult convention) without AttributeError.
    """
    return types.SimpleNamespace(
        score=0.0,
        final_score=0.0,
        ok_pass_rate=0.0,
        ng_detect_rate=0.0,
        boundary_warning=False,
        is_margin_warning=True,
        fp_indices=[],
        fn_indices=[],
        fp_images=[],
        fn_images=[],
        best_strategy=engine_name,
        margin=-100.0,
    )


class InspectionOptimizer:
    """
    Optimization loop that scores every EngineCandidate and selects the best.

    Each candidate is evaluated independently; exceptions in one candidate
    never abort the loop — they are logged and the candidate receives score 0.0.
    """

    def run(
        self,
        candidates: list,
        ok_images: list,
        ng_images: list,
        settings: object,
    ) -> OptimizationResult:
        """
        Evaluate all candidates and return the best result.

        Args:
            candidates: List of EngineCandidate (or duck-typed) objects to evaluate.
                        Each candidate must expose either an ``engine_type`` string
                        attribute (primary) or an ``engine_class`` type attribute
                        (fallback, resolved via _CLASS_TO_TYPE reverse map).
            ok_images:  List of numpy arrays (OK reference images).
            ng_images:  List of numpy arrays (NG defect images).
            settings:   Settings instance with w1, w2, margin_warning fields.

        Returns:
            OptimizationResult with best_candidate, best_evaluation, all_results,
            and optimization_log sorted by score descending.

        Raises:
            ValueError:              If candidates list is empty.
            RuntimeProcessingError:  If every valid candidate scores 0.0.
        """
        if not candidates:
            raise ValueError("candidates list must not be empty")

        evaluator = InspectionEvaluator()
        results: list[tuple] = []
        log: list[str] = []

        for candidate in candidates:
            # --- resolve engine_type string ---
            # Primary: explicit engine_type attribute (e.g. from MagicMock or future
            # EngineCandidate extensions).
            # Fallback: reverse-map engine_class → type key (current EngineCandidate).
            engine_type: str | None = getattr(candidate, "engine_type", None)
            if engine_type is None:
                engine_cls_attr = getattr(candidate, "engine_class", None)
                engine_type = _CLASS_TO_TYPE.get(engine_cls_attr)

            engine_name: str = (
                getattr(candidate, "engine_name", None) or engine_type or "Unknown"
            )

            engine_cls = ENGINE_REGISTRY.get(engine_type)
            if engine_cls is None:
                msg = (
                    f"[SKIP] {engine_name}: engine_type={engine_type!r} "
                    f"— not in ENGINE_REGISTRY, skipping"
                )
                log.append(msg)
                logger.warning(msg)
                continue

            try:
                eval_result = evaluator.evaluate(candidate, ok_images, ng_images, settings)
                score = _resolve_score(eval_result)
                log.append(
                    f"[OK] {engine_name}: score={score:.2f}, "
                    f"ok_pass_rate={getattr(eval_result, 'ok_pass_rate', 0.0):.4f}, "
                    f"ng_detect_rate={getattr(eval_result, 'ng_detect_rate', 0.0):.4f}"
                )
                results.append((candidate, eval_result))
            except Exception as exc:
                msg = f"[ERROR] {engine_name}: {exc} — score set to 0.0"
                log.append(msg)
                logger.error(msg)
                results.append((candidate, _zero_evaluation(engine_name)))

        if not results or all(_resolve_score(r[1]) == 0.0 for r in results):
            raise RuntimeProcessingError(
                "All candidates failed evaluation — no usable result available. "
                "Check engine implementations and image inputs."
            )

        # Stable sort preserves insertion order for equal scores (first wins on tie).
        results.sort(key=lambda x: _resolve_score(x[1]), reverse=True)

        return OptimizationResult(
            best_candidate=results[0][0],
            best_evaluation=results[0][1],
            all_results=results,
            optimization_log=log,
        )
