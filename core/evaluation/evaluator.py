"""
Inspection Evaluation Engine (Argos Step 39).

Scores each EngineCandidate against real OK/NG image samples using
a weighted pass-rate formula.  No AI provider is called here — pure
rule-based scoring only.

Scoring formula (PLAN.md §9):
    final_score = (ok_pass_rate × w1 + ng_detect_rate × w2) × 100
    margin      = (ok_pass_rate + ng_detect_rate - 1.0) × 100
    is_margin_warning = margin < settings.margin_warning  (default 15.0)

ok_pass_rate  : fraction of OK images for which the engine classifies
                the image as OK  (is_ok=True or ok_pass_rate ≥ 0.5).
ng_detect_rate: fraction of NG images for which the engine classifies
                the image as NG  (is_ok=False or ng_detect_rate ≥ 0.5).
"""

from __future__ import annotations

import logging
import warnings
from typing import Optional

import numpy as np

from core.interfaces import IEvaluationEngine
from core.models import EvaluationResult

logger = logging.getLogger("argos.evaluation.evaluator")

# Threshold used to decide pass / fail from a batch candidate's rate field.
_RATE_PASS_THRESHOLD = 0.5


class InspectionEvaluator(IEvaluationEngine):
    """
    Scores an EngineCandidate against OK/NG image sets.

    Each image is processed individually so that a single failing image
    cannot abort the entire batch.  FP (false-positive) and FN
    (false-negative) image indices are collected for downstream reporting.
    """

    def __init__(self) -> None:
        self._last_score: float = 0.0

    # ------------------------------------------------------------------ #
    #  Public API — IEvaluationEngine                                      #
    # ------------------------------------------------------------------ #

    def evaluate(
        self,
        candidate: object,
        ok_images: list[np.ndarray],
        ng_images: list[np.ndarray],
        settings: object,
    ) -> EvaluationResult:
        """
        Evaluate a single engine candidate against OK and NG image sets.

        Args:
            candidate:  EngineCandidate (engine_class, engine_name fields).
            ok_images:  List of numpy arrays — OK (pass) images.
            ng_images:  List of numpy arrays — NG (fail) images.
            settings:   Settings instance with w1, w2, margin_warning.

        Returns:
            EvaluationResult with ok_pass_rate, ng_detect_rate, final_score,
            margin, is_margin_warning, fp_images, fn_images.
        """
        engine_name: str = getattr(candidate, "engine_name", "Unknown")
        engine_cls = getattr(candidate, "engine_class", None)

        try:
            engine = engine_cls() if engine_cls is not None else None
        except Exception as exc:
            logger.error("엔진 인스턴스화 실패 (%s): %s", engine_name, exc)
            engine = None

        # Reference OK image used when evaluating NG images
        ref_ok: Optional[np.ndarray] = ok_images[0] if ok_images else None

        ok_pass_rate, fp_images = self._evaluate_ok_images(engine, ok_images)
        ng_detect_rate, fn_images = self._evaluate_ng_images(engine, ng_images, ref_ok)

        w1: float = float(getattr(settings, "w1", 0.5))
        w2: float = float(getattr(settings, "w2", 0.5))
        margin_warning: float = float(getattr(settings, "margin_warning", 15.0))

        final_score = (ok_pass_rate * w1 + ng_detect_rate * w2) * 100.0
        margin = (ok_pass_rate + ng_detect_rate - 1.0) * 100.0
        is_margin_warning = margin < margin_warning

        if is_margin_warning:
            logger.warning(
                "경계선 위험 구간: 분리 마진 %.1f < %.1f (엔진: %s)",
                margin,
                margin_warning,
                engine_name,
            )

        self._last_score = final_score

        return EvaluationResult(
            best_strategy=engine_name,
            ok_pass_rate=ok_pass_rate,
            ng_detect_rate=ng_detect_rate,
            final_score=final_score,
            margin=margin,
            is_margin_warning=is_margin_warning,
            fp_images=fp_images,
            fn_images=fn_images,
        )

    def get_score(self) -> float:
        """Return the final_score from the most recent evaluate() call."""
        return self._last_score

    # ------------------------------------------------------------------ #
    #  Per-image evaluation helpers                                        #
    # ------------------------------------------------------------------ #

    def _evaluate_ok_images(
        self,
        engine,
        ok_images: list[np.ndarray],
    ) -> tuple[float, list[str]]:
        """
        Run the engine on each OK image individually.

        An OK image *passes* when the engine's best candidate reports
        ok_pass_rate ≥ _RATE_PASS_THRESHOLD (≥ 0.5).

        Images that raise an exception are treated as failed (conservative).

        Returns:
            (ok_pass_rate, fp_image_ids)
        """
        if not ok_images:
            warnings.warn(
                "OK 이미지가 제공되지 않았습니다. ok_pass_rate를 1.0으로 처리합니다.",
                UserWarning,
                stacklevel=4,
            )
            logger.warning("OK 이미지 없음 — ok_pass_rate=1.0 (부분 점수)")
            return 1.0, []

        passes: list[bool] = []
        fp_images: list[str] = []

        for i, img in enumerate(ok_images):
            passed = self._run_single_ok(engine, img, index=i)
            passes.append(passed)
            if not passed:
                fp_images.append(f"ok_{i}")

        rate = sum(passes) / len(passes)
        return rate, fp_images

    def _evaluate_ng_images(
        self,
        engine,
        ng_images: list[np.ndarray],
        ref_ok: Optional[np.ndarray],
    ) -> tuple[float, list[str]]:
        """
        Run the engine on each NG image individually (paired with ref_ok).

        An NG image is *detected* when the engine's best candidate reports
        ng_detect_rate ≥ _RATE_PASS_THRESHOLD (≥ 0.5).

        Returns:
            (ng_detect_rate, fn_image_ids)
        """
        if not ng_images:
            warnings.warn(
                "NG 이미지가 제공되지 않았습니다. ng_detect_rate를 1.0으로 처리합니다.",
                UserWarning,
                stacklevel=4,
            )
            logger.warning("NG 이미지 없음 — ng_detect_rate=1.0 (부분 점수)")
            return 1.0, []

        if ref_ok is None:
            warnings.warn(
                "참조 OK 이미지가 없어 NG 평가를 수행할 수 없습니다. "
                "ng_detect_rate를 0.0으로 처리합니다.",
                UserWarning,
                stacklevel=4,
            )
            logger.warning("참조 OK 없음 — ng_detect_rate=0.0 (부분 점수)")
            fn_images = [f"ng_{j}" for j in range(len(ng_images))]
            return 0.0, fn_images

        detects: list[bool] = []
        fn_images: list[str] = []

        for j, ng_img in enumerate(ng_images):
            detected = self._run_single_ng(engine, ref_ok, ng_img, index=j)
            detects.append(detected)
            if not detected:
                fn_images.append(f"ng_{j}")

        rate = sum(detects) / len(detects)
        return rate, fn_images

    # ------------------------------------------------------------------ #
    #  Single-image engine calls (exception-isolated)                      #
    # ------------------------------------------------------------------ #

    def _run_single_ok(
        self,
        engine,
        img: np.ndarray,
        index: int,
    ) -> bool:
        """
        Invoke the engine on a single OK image.

        Returns True if the engine classifies the image as OK.
        Returns False on any exception (isolated, does not re-raise).
        """
        if engine is None:
            logger.warning("OK 이미지 %d: 엔진 없음 → 실패 처리", index)
            return False

        try:
            result_candidates = engine.run(ok_images=[img], ng_images=[])
            if not result_candidates:
                return False
            best = max(result_candidates, key=lambda c: c.score)
            return float(best.ok_pass_rate) >= _RATE_PASS_THRESHOLD
        except Exception as exc:
            logger.warning("OK 이미지 %d 처리 중 오류 (격리됨): %s", index, exc)
            return False

    def _run_single_ng(
        self,
        engine,
        ref_ok: np.ndarray,
        ng_img: np.ndarray,
        index: int,
    ) -> bool:
        """
        Invoke the engine on a single NG image (with ref_ok as reference).

        Returns True if the engine detects the NG (defect found).
        Returns False on any exception (isolated, does not re-raise).
        """
        if engine is None:
            logger.warning("NG 이미지 %d: 엔진 없음 → 미검출 처리", index)
            return False

        try:
            result_candidates = engine.run(ok_images=[ref_ok], ng_images=[ng_img])
            if not result_candidates:
                return False
            best = max(result_candidates, key=lambda c: c.score)
            return float(best.ng_detect_rate) >= _RATE_PASS_THRESHOLD
        except Exception as exc:
            logger.warning("NG 이미지 %d 처리 중 오류 (격리됨): %s", index, exc)
            return False
