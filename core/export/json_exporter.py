"""
JSON exporter for the Argos vision algorithm design system.

Serializes analysis results to a structured JSON file, handling
dataclasses, numpy arrays, datetime, and enum types.
"""

import json
from dataclasses import asdict, fields, is_dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np

from core.logger import get_logger


class _ArgosEncoder(json.JSONEncoder):
    """Custom JSON encoder handling Argos-specific types."""

    def default(self, obj: Any) -> Any:
        """Encode non-standard types."""
        if isinstance(obj, np.ndarray):
            return {"__ndarray__": True, "shape": list(obj.shape), "dtype": str(obj.dtype)}
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, Path):
            return str(obj)
        if is_dataclass(obj) and not isinstance(obj, type):
            return self._dataclass_to_dict(obj)
        return super().default(obj)

    @staticmethod
    def _dataclass_to_dict(obj: Any) -> dict:
        """Convert a dataclass to dict, preserving nested types for the encoder."""
        result = {}
        for f in fields(obj):
            result[f.name] = getattr(obj, f.name)
        return result


class ArgosJSONExporter:
    """Exports full analysis results to a structured JSON file."""

    def __init__(self) -> None:
        self._logger = get_logger("json_exporter")

    def export(self, results: dict, output_path: Path) -> Path:
        """
        Export analysis results to JSON.

        Args:
            results: Aggregate result dict from AnalysisWorker.
            output_path: Directory to write the JSON file into.

        Returns:
            Path to the created JSON file.
        """
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)
        file_path = output_path / "argos_results.json"

        serializable = self._serialize(results)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(serializable, f, cls=_ArgosEncoder, ensure_ascii=False, indent=2)

        self._logger.info("JSON export complete: %s", file_path)
        return file_path

    def _serialize(self, obj: Any) -> Any:
        """
        Recursively convert an object tree to JSON-safe primitives.

        ndarray values are replaced with shape/dtype metadata.
        Dataclasses are converted to dicts.
        """
        if obj is None or isinstance(obj, (bool, int, float, str)):
            return obj
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return {"__ndarray__": True, "shape": list(obj.shape), "dtype": str(obj.dtype)}
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, Path):
            return str(obj)
        if is_dataclass(obj) and not isinstance(obj, type):
            return {f.name: self._serialize(getattr(obj, f.name)) for f in fields(obj)}
        if isinstance(obj, dict):
            return {str(k): self._serialize(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [self._serialize(item) for item in obj]
        # Fallback: try str
        try:
            json.dumps(obj)
            return obj
        except (TypeError, ValueError):
            return str(obj)
