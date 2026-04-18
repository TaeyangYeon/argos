"""
Image exporter for the Argos vision algorithm design system.

Batch-saves overlay images (align, inspection, failure) from analysis results.
"""

import shutil
from pathlib import Path
from typing import Any, Optional

import cv2
import numpy as np

from core.logger import get_logger
from core.models import FailureAnalysisResult, OptimizationResult


class ArgosImageExporter:
    """Batch exports overlay images from analysis results."""

    def __init__(self) -> None:
        self._logger = get_logger("image_exporter")

    def export(self, results: dict, output_dir: Path) -> list[Path]:
        """
        Export all overlay images from results.

        Args:
            results: Aggregate result dict from AnalysisWorker.
            output_dir: Directory to save images into.

        Returns:
            List of paths to saved image files.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        saved: list[Path] = []

        # Align overlay
        saved.extend(self._save_align_overlay(results, output_dir))

        # Inspection overlay (best candidate)
        saved.extend(self._save_inspection_overlay(results, output_dir))

        # Failure overlays
        saved.extend(self._save_failure_overlays(results, output_dir))

        self._logger.info("Image export complete: %d files saved", len(saved))
        return saved

    def _save_align_overlay(self, results: dict, output_dir: Path) -> list[Path]:
        """Save align overlay image if available."""
        align = results.get("align")
        if align is None:
            return []

        overlay = getattr(align, "overlay_image", None)
        if overlay is None:
            return []

        path = output_dir / "argos_align_overlay.png"
        return self._save_image(overlay, path)

    def _save_inspection_overlay(self, results: dict, output_dir: Path) -> list[Path]:
        """Save best candidate inspection overlay image."""
        inspection = results.get("inspection")
        if inspection is None:
            return []

        # Try OptimizationResult.best_candidate
        best = getattr(inspection, "best_candidate", None)
        if best is not None:
            overlay_path = getattr(best, "overlay_image_path", None)
            if overlay_path is not None:
                path = output_dir / "argos_inspection_overlay.png"
                return self._save_image(overlay_path, path)

        # Try dict format
        if isinstance(inspection, dict):
            best = inspection.get("best_candidate")
            if best is not None:
                overlay_path = getattr(best, "overlay_image_path", None)
                if overlay_path is not None:
                    path = output_dir / "argos_inspection_overlay.png"
                    return self._save_image(overlay_path, path)

        return []

    def _save_failure_overlays(self, results: dict, output_dir: Path) -> list[Path]:
        """Save failure (FP/FN) overlay images."""
        eval_dict = results.get("evaluation")
        if not isinstance(eval_dict, dict):
            return []

        failure = eval_dict.get("failure_result")
        if not isinstance(failure, FailureAnalysisResult):
            return []

        saved: list[Path] = []

        # FP overlays
        for i, fp_path in enumerate(failure.fp_overlay_paths):
            dest = output_dir / f"argos_failure_fp_{i + 1:03d}.png"
            saved.extend(self._save_image(fp_path, dest))

        # FN overlays
        for i, fn_path in enumerate(failure.fn_overlay_paths):
            dest = output_dir / f"argos_failure_fn_{i + 1:03d}.png"
            saved.extend(self._save_image(fn_path, dest))

        return saved

    def _save_image(self, source: Any, dest: Path) -> list[Path]:
        """
        Save an image from ndarray or file path string.

        Args:
            source: numpy ndarray or file path string.
            dest: Destination path.

        Returns:
            List containing dest path on success, empty list on failure.
        """
        try:
            if isinstance(source, np.ndarray):
                cv2.imwrite(str(dest), source)
                return [dest]
            if isinstance(source, (str, Path)):
                src_path = Path(source)
                if src_path.is_file():
                    shutil.copy2(str(src_path), str(dest))
                    return [dest]
                self._logger.warning("Source file not found: %s", source)
                return []
        except Exception as e:
            self._logger.error("Failed to save image %s: %s", dest, e)
            return []
        return []
