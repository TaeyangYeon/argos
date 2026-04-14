"""
Dynamic Candidate Generator for inspection engine selection (Argos Step 38).

Selects candidate inspection engines based on FullFeatureAnalysis characteristics
using deterministic rule-based logic, with optional AI-assisted augmentation.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Optional

from core.analyzers.feature_analyzer import FullFeatureAnalysis
from core.inspection.blob_inspector import BlobInspectionEngine
from core.inspection.circular_caliper_inspector import CircularCaliperInspectionEngine
from core.inspection.linear_caliper_inspector import LinearCaliperInspectionEngine
from core.inspection.pattern_inspector import PatternInspectionEngine
from core.models import InspectionPurpose

logger = logging.getLogger("argos.inspection.candidate_generator")

# Noise level constants (mirrors config/constants.py values)
_NOISE_LOW = "Low"

# Minimum priority for fallback candidates
_FALLBACK_PRIORITY = 0.3

# Minimum number of candidates to return
_MIN_CANDIDATES = 2


@dataclass
class EngineCandidate:
    """A ranked inspection engine candidate selected for a given image."""

    engine_class: type    # e.g. BlobInspectionEngine
    engine_name: str      # human-readable name
    priority: float       # 0.0–1.0 (higher = more suitable)
    rationale: str        # why this candidate was chosen
    source: str           # "rule_based" | "ai_suggested"


class DynamicCandidateGenerator:
    """
    Selects and ranks inspection engine candidates from image feature analysis.

    Rule-based selection is always performed; an optional AI provider can
    suggest additional candidates which are merged into the result.
    """

    def __init__(self, ai_provider=None):
        """
        Initialise the generator.

        Args:
            ai_provider: IAIProvider instance or None to skip AI augmentation.
        """
        self._ai_provider = ai_provider

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def generate(
        self,
        feature_analysis: FullFeatureAnalysis,
        inspection_purpose: InspectionPurpose,
    ) -> list[EngineCandidate]:
        """
        Generate a sorted list of inspection engine candidates.

        Args:
            feature_analysis: Full feature analysis result for the image set.
            inspection_purpose: Inspection purpose describing what to detect.

        Returns:
            List of EngineCandidate sorted by priority descending (≥2 items).
        """
        candidates: list[EngineCandidate] = []

        # --- Rule-based selection ---
        candidates.extend(self._apply_rules(feature_analysis))

        # --- AI augmentation (graceful degradation on failure) ---
        if self._ai_provider is not None:
            try:
                ai_candidates = self._query_ai(feature_analysis, inspection_purpose)
                candidates.extend(ai_candidates)
            except Exception as exc:
                logger.warning(
                    "AI candidate suggestion failed; using rule-based only. Error: %s",
                    exc,
                )

        # --- Deduplicate by engine_class (keep highest priority) ---
        candidates = self._deduplicate(candidates)

        # --- Ensure minimum 2 candidates ---
        candidates = self._ensure_minimum(candidates)

        # --- Sort by priority descending ---
        candidates.sort(key=lambda c: c.priority, reverse=True)

        return candidates

    # ------------------------------------------------------------------ #
    #  Rule-based selection                                                #
    # ------------------------------------------------------------------ #

    def _apply_rules(self, fa: FullFeatureAnalysis) -> list[EngineCandidate]:
        """Apply deterministic selection rules and return matching candidates."""
        results: list[EngineCandidate] = []

        edge = fa.edge
        shape = fa.shape
        noise = fa.noise
        histogram = fa.histogram

        # Rule 1: High edge density + caliper-suitable → LinearCaliperInspectionEngine
        if edge.edge_density >= 0.3 and edge.is_suitable_for_caliper:
            priority = min(1.0, edge.edge_density * 2.0)
            results.append(
                EngineCandidate(
                    engine_class=LinearCaliperInspectionEngine,
                    engine_name="Linear Caliper",
                    priority=round(priority, 4),
                    rationale=(
                        f"High edge density ({edge.edge_density:.3f}) with "
                        f"caliper-suitable edges."
                    ),
                    source="rule_based",
                )
            )

        # Rule 2: Circular blobs detected → CircularCaliperInspectionEngine
        if len(shape.detected_circles) > 0:
            circle_count = len(shape.detected_circles)
            priority = min(1.0, circle_count * 0.3 + 0.4)
            results.append(
                EngineCandidate(
                    engine_class=CircularCaliperInspectionEngine,
                    engine_name="Circular Caliper",
                    priority=round(priority, 4),
                    rationale=(
                        f"{circle_count} circular structure(s) detected by Hough transform."
                    ),
                    source="rule_based",
                )
            )

        # Rule 3: blob_count >= 2 → BlobInspectionEngine
        if shape.blob_count >= 2:
            priority = min(1.0, shape.blob_count * 0.08 + 0.2)
            results.append(
                EngineCandidate(
                    engine_class=BlobInspectionEngine,
                    engine_name="Blob Inspection",
                    priority=round(priority, 4),
                    rationale=(
                        f"{shape.blob_count} blobs detected — "
                        f"blob-based inspection is applicable."
                    ),
                    source="rule_based",
                )
            )

        # Rule 4: Low noise + sufficient contrast → PatternInspectionEngine
        if noise.noise_level == _NOISE_LOW and histogram.std_gray >= 30.0:
            priority = min(1.0, histogram.std_gray / 128.0 + 0.3)
            results.append(
                EngineCandidate(
                    engine_class=PatternInspectionEngine,
                    engine_name="Pattern Inspection",
                    priority=round(priority, 4),
                    rationale=(
                        f"Low noise (level={noise.noise_level}) and "
                        f"sufficient contrast (std_gray={histogram.std_gray:.1f})."
                    ),
                    source="rule_based",
                )
            )

        return results

    # ------------------------------------------------------------------ #
    #  AI augmentation                                                     #
    # ------------------------------------------------------------------ #

    def _build_ai_prompt(
        self,
        fa: FullFeatureAnalysis,
        purpose: InspectionPurpose,
    ) -> str:
        """Build a text-only prompt from feature statistics and inspection purpose."""
        return (
            "You are a vision inspection algorithm expert.\n"
            "Based on the following image feature analysis, suggest suitable inspection "
            "engine(s) from the list: BlobInspectionEngine, LinearCaliperInspectionEngine, "
            "CircularCaliperInspectionEngine, PatternInspectionEngine.\n\n"
            f"Inspection purpose: {purpose.description}\n"
            f"Inspection type: {purpose.inspection_type}\n"
            f"Target feature: {purpose.target_feature}\n\n"
            "Image statistics:\n"
            f"  edge_density: {fa.edge.edge_density:.4f}\n"
            f"  is_suitable_for_caliper: {fa.edge.is_suitable_for_caliper}\n"
            f"  blob_count: {fa.shape.blob_count}\n"
            f"  detected_circles: {len(fa.shape.detected_circles)}\n"
            f"  noise_level: {fa.noise.noise_level}\n"
            f"  std_gray (contrast): {fa.histogram.std_gray:.2f}\n"
            f"  mean_gray: {fa.histogram.mean_gray:.2f}\n\n"
            "Respond in JSON only, no extra text:\n"
            '{"candidates": [{"engine": "<EngineName>", "rationale": "<why>"}]}'
        )

    def _query_ai(
        self,
        fa: FullFeatureAnalysis,
        purpose: InspectionPurpose,
    ) -> list[EngineCandidate]:
        """Call AI provider and parse the response into EngineCandidate objects."""
        _ENGINE_MAP: dict[str, type] = {
            "BlobInspectionEngine": BlobInspectionEngine,
            "LinearCaliperInspectionEngine": LinearCaliperInspectionEngine,
            "CircularCaliperInspectionEngine": CircularCaliperInspectionEngine,
            "PatternInspectionEngine": PatternInspectionEngine,
        }

        prompt = self._build_ai_prompt(fa, purpose)
        raw_response = self._ai_provider.analyze(prompt)

        try:
            data = json.loads(raw_response)
        except json.JSONDecodeError:
            # Try to extract JSON block from response
            start = raw_response.find("{")
            end = raw_response.rfind("}") + 1
            data = json.loads(raw_response[start:end])

        ai_candidates: list[EngineCandidate] = []
        for item in data.get("candidates", []):
            engine_name_str = item.get("engine", "")
            rationale = item.get("rationale", "AI-suggested candidate.")
            engine_cls = _ENGINE_MAP.get(engine_name_str)
            if engine_cls is None:
                logger.warning("AI suggested unknown engine '%s'; skipping.", engine_name_str)
                continue
            ai_candidates.append(
                EngineCandidate(
                    engine_class=engine_cls,
                    engine_name=engine_name_str,
                    priority=0.5,  # Default priority for AI-suggested candidates
                    rationale=rationale,
                    source="ai_suggested",
                )
            )

        return ai_candidates

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _deduplicate(self, candidates: list[EngineCandidate]) -> list[EngineCandidate]:
        """Remove duplicates by engine_class, keeping the entry with highest priority."""
        seen: dict[type, EngineCandidate] = {}
        for candidate in candidates:
            existing = seen.get(candidate.engine_class)
            if existing is None or candidate.priority > existing.priority:
                seen[candidate.engine_class] = candidate
        return list(seen.values())

    def _ensure_minimum(self, candidates: list[EngineCandidate]) -> list[EngineCandidate]:
        """Add PatternInspectionEngine as fallback if fewer than _MIN_CANDIDATES present."""
        if len(candidates) < _MIN_CANDIDATES:
            engine_classes = {c.engine_class for c in candidates}
            if PatternInspectionEngine not in engine_classes:
                candidates.append(
                    EngineCandidate(
                        engine_class=PatternInspectionEngine,
                        engine_name="Pattern Inspection",
                        priority=_FALLBACK_PRIORITY,
                        rationale="Fallback candidate: minimum 2 candidates required.",
                        source="rule_based",
                    )
                )
            # If still < 2, add BlobInspectionEngine as secondary fallback
            if len(candidates) < _MIN_CANDIDATES:
                engine_classes = {c.engine_class for c in candidates}
                if BlobInspectionEngine not in engine_classes:
                    candidates.append(
                        EngineCandidate(
                            engine_class=BlobInspectionEngine,
                            engine_name="Blob Inspection",
                            priority=_FALLBACK_PRIORITY,
                            rationale="Fallback candidate: minimum 2 candidates required.",
                            source="rule_based",
                        )
                    )
        return candidates
