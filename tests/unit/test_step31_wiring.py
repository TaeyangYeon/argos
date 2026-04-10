"""
Tests for Step 31 wiring fix.

Verifies that:
- AnalysisWorker.align_complete signal fires after run()
- The emitted payload is an AlignResult with a non-empty strategy_name
- AnalysisPage._on_align_complete stores the result and re-emits align_completed
- When no ALIGN_OK images are present, worker emits success=False result (no crash)
"""

from __future__ import annotations

import os
import tempfile

import numpy as np
import pytest
import cv2

from PyQt6.QtCore import QCoreApplication, Qt

from core.image_store import ImageStore, ImageType, ImageMeta
from core.models import AlignResult, ROIConfig
from ui.workers.analysis_worker import AnalysisWorker
from ui.pages.analysis_page import AnalysisPage


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _write_temp_image(path: str, size: tuple[int, int] = (60, 60)) -> None:
    """Write a small BGR PNG to *path*."""
    img = np.full((*size, 3), 128, dtype=np.uint8)
    cv2.imwrite(path, img)


def _make_image_meta(image_id: str, path: str, image_type: ImageType) -> ImageMeta:
    """Build an ImageMeta with all required fields."""
    from datetime import datetime
    return ImageMeta(
        id=image_id,
        file_path=path,
        image_type=image_type,
        width=60,
        height=60,
        file_size_bytes=os.path.getsize(path),
        added_at=datetime.now().isoformat(),
    )


def _make_image_store_with_align_ok() -> tuple[ImageStore, str]:
    """Return an ImageStore loaded with one ALIGN_OK image and its temp file path."""
    store = ImageStore()
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp.close()
    _write_temp_image(tmp.name)

    meta = _make_image_meta("align_ok_1", tmp.name, ImageType.ALIGN_OK)
    store._images["align_ok_1"] = meta  # inject directly for test isolation
    return store, tmp.name


def _make_image_store_no_align_ok() -> tuple[ImageStore, str]:
    """Return an ImageStore with a generic image but NO ALIGN_OK images."""
    store = ImageStore()
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp.close()
    _write_temp_image(tmp.name)

    meta = _make_image_meta("insp_ok_1", tmp.name, ImageType.INSPECTION_OK)
    store._images["insp_ok_1"] = meta
    return store, tmp.name


# ── 1. Worker emits align_complete after run() ────────────────────────────────

class TestAnalysisWorkerAlignSignal:
    def test_align_complete_emitted(self, qtbot):
        """align_complete must fire at least once after worker.run()."""
        store, tmp = _make_image_store_with_align_ok()
        try:
            worker = AnalysisWorker(store, roi_config=None, inspection_purpose=None)
            received = []
            worker.align_complete.connect(lambda r: received.append(r))

            with qtbot.waitSignal(worker.align_complete, timeout=10_000):
                worker.run()

            assert len(received) == 1
        finally:
            os.unlink(tmp)

    def test_align_complete_carries_align_result(self, qtbot):
        """Emitted payload must be an AlignResult instance."""
        store, tmp = _make_image_store_with_align_ok()
        try:
            worker = AnalysisWorker(store, roi_config=None, inspection_purpose=None)
            received = []
            worker.align_complete.connect(lambda r: received.append(r))

            with qtbot.waitSignal(worker.align_complete, timeout=10_000):
                worker.run()

            result = received[0]
            assert isinstance(result, AlignResult)
        finally:
            os.unlink(tmp)

    def test_align_result_strategy_name_non_empty(self, qtbot):
        """Emitted AlignResult must have a non-empty strategy_name."""
        store, tmp = _make_image_store_with_align_ok()
        try:
            worker = AnalysisWorker(store, roi_config=None, inspection_purpose=None)
            received = []
            worker.align_complete.connect(lambda r: received.append(r))

            with qtbot.waitSignal(worker.align_complete, timeout=10_000):
                worker.run()

            result = received[0]
            assert isinstance(getattr(result, "strategy_name", None), str)
            assert result.strategy_name != ""
        finally:
            os.unlink(tmp)


# ── 2. No ALIGN_OK images → failed result emitted (no crash) ─────────────────

class TestWorkerNoAlignImages:
    def test_emits_failed_result_when_no_align_ok(self, qtbot):
        """When there are no ALIGN_OK images, worker must emit align_complete
        with success=False instead of crashing."""
        store, tmp = _make_image_store_no_align_ok()
        try:
            worker = AnalysisWorker(store, roi_config=None, inspection_purpose=None)
            received = []
            worker.align_complete.connect(lambda r: received.append(r))

            with qtbot.waitSignal(worker.align_complete, timeout=10_000):
                worker.run()

            result = received[0]
            assert isinstance(result, AlignResult)
            assert result.success is False
        finally:
            os.unlink(tmp)

    def test_no_crash_when_no_align_ok(self, qtbot):
        """run() must complete without raising when no ALIGN_OK images exist."""
        store, tmp = _make_image_store_no_align_ok()
        try:
            worker = AnalysisWorker(store, roi_config=None, inspection_purpose=None)

            # Should complete without exception — analysis_complete or failed fires
            with qtbot.waitSignals(
                [worker.analysis_complete, worker.analysis_failed],
                timeout=10_000,
                raising=False,
            ):
                worker.run()
        finally:
            os.unlink(tmp)


# ── 3. AnalysisPage._on_align_complete stores result ─────────────────────────

class TestAnalysisPageAlignHandler:
    def test_on_align_complete_stores_result(self, qtbot):
        """_on_align_complete must save the result to _last_align_result."""
        store = ImageStore()
        page = AnalysisPage(image_store=store)
        qtbot.addWidget(page)

        dummy = AlignResult(
            success=True,
            strategy_name="pattern",
            score=0.9,
        )
        page._on_align_complete(dummy)

        assert page._last_align_result is dummy

    def test_on_align_complete_emits_align_completed(self, qtbot):
        """_on_align_complete must emit align_completed with the result."""
        store = ImageStore()
        page = AnalysisPage(image_store=store)
        qtbot.addWidget(page)

        dummy = AlignResult(
            success=True,
            strategy_name="caliper",
            score=0.75,
        )
        received = []
        page.align_completed.connect(lambda r: received.append(r))

        page._on_align_complete(dummy)

        assert len(received) == 1
        assert received[0] is dummy

    def test_align_completed_signal_exists_on_page(self, qtbot):
        """AnalysisPage must expose align_completed as a pyqtSignal."""
        store = ImageStore()
        page = AnalysisPage(image_store=store)
        qtbot.addWidget(page)
        # Signal must be connectable (no AttributeError)
        received = []
        page.align_completed.connect(lambda r: received.append(r))
        page.align_completed.emit(None)
        assert received == [None]
