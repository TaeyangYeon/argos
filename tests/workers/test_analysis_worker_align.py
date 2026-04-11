"""
Step 34 — AnalysisWorker ALIGN_DESIGN 단계 연동 테스트

Tests:
  1.  ALIGN_OK 이미지가 있을 때 align_complete 시그널이 발행된다
  2.  발행된 payload가 AlignResult 인스턴스다
  3.  결과가 _align_result에 저장된다
  4.  결과가 _results["align"]에 저장된다
  5.  ALIGN_OK 이미지 없음 → align_complete(success=False) 발행
  6.  ALIGN_OK 이미지 없음 → _results["align"]가 실패 결과로 저장된다
  7.  ALIGN_OK 이미지 없음 → 워커가 중단 없이 계속 실행된다 (analysis_complete 발행)
  8.  AlignFallbackChain.run()이 예외 → align_complete(success=False) 발행
  9.  AlignFallbackChain.run()이 예외 → step_failed 시그널 발행
  10. AlignFallbackChain.run()이 예외 → _results["align"]가 에러 결과로 저장된다
  11. step_started("Align 설계") 발행 확인
  12. 성공 시 step_finished 발행 확인
  13. inspection_purpose가 AlignFallbackChain 생성자에 전달된다
  14. cancel 플래그가 설정되면 _execute_align_design이 즉시 False를 반환한다
"""

from __future__ import annotations

import os
import tempfile
from unittest.mock import MagicMock, patch, call

import cv2
import numpy as np
import pytest

from core.image_store import ImageStore, ImageType, ImageMeta
from core.models import AlignResult, ROIConfig, InspectionPurpose
from ui.workers.analysis_worker import AnalysisWorker


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _write_png(path: str, size: tuple[int, int] = (60, 60)) -> None:
    img = np.full((*size, 3), 128, dtype=np.uint8)
    cv2.imwrite(path, img)


def _make_meta(image_id: str, path: str, image_type: ImageType) -> ImageMeta:
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


def _store_with_align_ok() -> tuple[ImageStore, str]:
    """ImageStore with one ALIGN_OK image; also returns temp file path."""
    store = ImageStore()
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp.close()
    _write_png(tmp.name)
    store._images["align_ok_1"] = _make_meta("align_ok_1", tmp.name, ImageType.ALIGN_OK)
    return store, tmp.name


def _store_no_align_ok() -> tuple[ImageStore, str]:
    """ImageStore with an INSPECTION_OK image but no ALIGN_OK images."""
    store = ImageStore()
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp.close()
    _write_png(tmp.name)
    store._images["insp_ok_1"] = _make_meta("insp_ok_1", tmp.name, ImageType.INSPECTION_OK)
    return store, tmp.name


def _ok_align_result(strategy: str = "pattern_matching") -> AlignResult:
    return AlignResult(success=True, strategy_name=strategy, score=0.9)


# ─── Test class ──────────────────────────────────────────────────────────────

class TestAnalysisWorkerAlignDesign:

    # ── 1. align_complete 시그널 발행 ─────────────────────────────────────────
    def test_align_complete_emitted_on_success(self, qtbot):
        """ALIGN_OK 이미지가 있을 때 align_complete 시그널이 발행된다."""
        store, tmp = _store_with_align_ok()
        try:
            worker = AnalysisWorker(store, roi_config=None)
            received = []
            worker.align_complete.connect(lambda r: received.append(r))

            with qtbot.waitSignal(worker.align_complete, timeout=15_000):
                worker.run()

            assert len(received) >= 1
        finally:
            os.unlink(tmp)

    # ── 2. payload가 AlignResult 인스턴스 ────────────────────────────────────
    def test_align_complete_payload_is_align_result(self, qtbot):
        """발행된 payload가 AlignResult 인스턴스여야 한다."""
        store, tmp = _store_with_align_ok()
        try:
            worker = AnalysisWorker(store, roi_config=None)
            received = []
            worker.align_complete.connect(lambda r: received.append(r))

            with qtbot.waitSignal(worker.align_complete, timeout=15_000):
                worker.run()

            assert isinstance(received[0], AlignResult)
        finally:
            os.unlink(tmp)

    # ── 3. _align_result에 저장 ───────────────────────────────────────────────
    def test_align_result_stored_in_private_attr(self, qtbot):
        """결과가 worker._align_result에 저장된다."""
        store, tmp = _store_with_align_ok()
        try:
            worker = AnalysisWorker(store, roi_config=None)

            with qtbot.waitSignal(worker.align_complete, timeout=15_000):
                worker.run()

            assert isinstance(worker._align_result, AlignResult)
        finally:
            os.unlink(tmp)

    # ── 4. _results["align"]에 저장 ──────────────────────────────────────────
    def test_align_result_stored_in_results_dict(self, qtbot):
        """결과가 worker._results['align']에 저장된다."""
        store, tmp = _store_with_align_ok()
        try:
            worker = AnalysisWorker(store, roi_config=None)

            with qtbot.waitSignal(worker.align_complete, timeout=15_000):
                worker.run()

            assert "align" in worker._results
            assert isinstance(worker._results["align"], AlignResult)
        finally:
            os.unlink(tmp)

    # ── 5. ALIGN_OK 없음 → align_complete(success=False) ─────────────────────
    def test_no_align_ok_emits_failed_result(self, qtbot):
        """ALIGN_OK 이미지 없음 → align_complete(success=False)가 발행된다."""
        store, tmp = _store_no_align_ok()
        try:
            worker = AnalysisWorker(store, roi_config=None)
            received = []
            worker.align_complete.connect(lambda r: received.append(r))

            with qtbot.waitSignal(worker.align_complete, timeout=15_000):
                worker.run()

            assert received[0].success is False
        finally:
            os.unlink(tmp)

    # ── 6. ALIGN_OK 없음 → _results["align"] 실패 결과 저장 ─────────────────
    def test_no_align_ok_stores_failure_in_results_dict(self, qtbot):
        """ALIGN_OK 이미지 없음 → _results['align']가 실패 결과로 저장된다."""
        store, tmp = _store_no_align_ok()
        try:
            worker = AnalysisWorker(store, roi_config=None)

            with qtbot.waitSignal(worker.align_complete, timeout=15_000):
                worker.run()

            assert "align" in worker._results
            assert worker._results["align"].success is False
        finally:
            os.unlink(tmp)

    # ── 7. ALIGN_OK 없음 → 워커가 중단 없이 계속 실행 ────────────────────────
    def test_no_align_ok_continues_without_crash(self, qtbot):
        """ALIGN_OK 이미지 없음에도 워커가 analysis_complete까지 실행된다."""
        store, tmp = _store_no_align_ok()
        try:
            worker = AnalysisWorker(store, roi_config=None)

            # 워커가 마지막까지 완료돼야 하므로 analysis_complete 또는 analysis_failed 중 하나 대기
            with qtbot.waitSignals(
                [worker.analysis_complete, worker.analysis_failed],
                timeout=15_000,
                raising=False,
            ):
                worker.run()
            # 예외가 발생하지 않으면 통과
        finally:
            os.unlink(tmp)

    # ── 8. chain.run() 예외 → align_complete(success=False) ──────────────────
    @patch("core.align.align_engine.AlignFallbackChain")
    def test_chain_exception_emits_failed_align_complete(self, MockChain, qtbot):
        """AlignFallbackChain.run()이 예외를 던지면 align_complete(success=False)가 발행된다."""
        store, tmp = _store_with_align_ok()
        try:
            mock_instance = MagicMock()
            mock_instance.run.side_effect = RuntimeError("simulated engine crash")
            MockChain.return_value = mock_instance

            worker = AnalysisWorker(store, roi_config=None)
            received = []
            worker.align_complete.connect(lambda r: received.append(r))

            with qtbot.waitSignal(worker.align_complete, timeout=15_000):
                worker.run()

            assert received[0].success is False
        finally:
            os.unlink(tmp)

    # ── 9. chain.run() 예외 → step_failed 시그널 발행 ───────────────────────
    @patch("core.align.align_engine.AlignFallbackChain")
    def test_chain_exception_emits_step_failed(self, MockChain, qtbot):
        """AlignFallbackChain.run()이 예외를 던지면 step_failed 시그널이 발행된다."""
        store, tmp = _store_with_align_ok()
        try:
            mock_instance = MagicMock()
            mock_instance.run.side_effect = RuntimeError("simulated engine crash")
            MockChain.return_value = mock_instance

            worker = AnalysisWorker(store, roi_config=None)
            failed_signals = []
            worker.step_failed.connect(lambda s, m: failed_signals.append((s, m)))

            with qtbot.waitSignal(worker.step_failed, timeout=15_000):
                worker.run()

            assert len(failed_signals) >= 1
        finally:
            os.unlink(tmp)

    # ── 10. chain.run() 예외 → _results["align"] 에러 결과 저장 ─────────────
    @patch("core.align.align_engine.AlignFallbackChain")
    def test_chain_exception_stores_error_in_results_dict(self, MockChain, qtbot):
        """AlignFallbackChain.run()이 예외를 던지면 _results['align']에 에러 결과가 저장된다."""
        store, tmp = _store_with_align_ok()
        try:
            mock_instance = MagicMock()
            mock_instance.run.side_effect = RuntimeError("simulated engine crash")
            MockChain.return_value = mock_instance

            worker = AnalysisWorker(store, roi_config=None)

            with qtbot.waitSignal(worker.align_complete, timeout=15_000):
                worker.run()

            assert "align" in worker._results
            assert worker._results["align"].success is False
        finally:
            os.unlink(tmp)

    # ── 11. step_started 발행 확인 ───────────────────────────────────────────
    def test_step_started_emitted(self, qtbot):
        """ALIGN_DESIGN 단계 시작 시 step_started 시그널이 발행된다."""
        store, tmp = _store_with_align_ok()
        try:
            worker = AnalysisWorker(store, roi_config=None)
            started_steps = []
            worker.step_started.connect(lambda s: started_steps.append(s))

            with qtbot.waitSignal(worker.align_complete, timeout=15_000):
                worker.run()

            from ui.components.progress_steps import AnalysisStep
            align_step_value = AnalysisStep.ALIGN_DESIGN.value
            assert align_step_value in started_steps
        finally:
            os.unlink(tmp)

    # ── 12. 성공 시 step_finished 발행 확인 ──────────────────────────────────
    @patch("core.align.align_engine.AlignFallbackChain")
    def test_step_finished_emitted_on_success(self, MockChain, qtbot):
        """체인이 성공하면 step_finished 시그널이 발행된다."""
        store, tmp = _store_with_align_ok()
        try:
            mock_instance = MagicMock()
            mock_instance.run.return_value = _ok_align_result()
            MockChain.return_value = mock_instance

            worker = AnalysisWorker(store, roi_config=None)
            finished_steps = []
            worker.step_finished.connect(lambda s, t: finished_steps.append(s))

            with qtbot.waitSignal(worker.step_finished, timeout=15_000):
                worker.run()

            from ui.components.progress_steps import AnalysisStep
            align_step_value = AnalysisStep.ALIGN_DESIGN.value
            assert align_step_value in finished_steps
        finally:
            os.unlink(tmp)

    # ── 13. inspection_purpose가 AlignFallbackChain 생성자에 전달된다 ─────────
    @patch("core.align.align_engine.AlignFallbackChain")
    def test_inspection_purpose_passed_to_chain(self, MockChain, qtbot):
        """inspection_purpose가 AlignFallbackChain 생성자에 전달돼야 한다."""
        store, tmp = _store_with_align_ok()
        try:
            mock_instance = MagicMock()
            mock_instance.run.return_value = _ok_align_result()
            MockChain.return_value = mock_instance

            purpose = InspectionPurpose(inspection_type="치수측정", description="테스트")
            worker = AnalysisWorker(store, roi_config=None, inspection_purpose=purpose)

            with qtbot.waitSignal(worker.align_complete, timeout=15_000):
                worker.run()

            # AlignFallbackChain이 inspection_purpose 인자와 함께 생성되었는지 확인
            call_kwargs = MockChain.call_args
            passed_purpose = (
                call_kwargs.kwargs.get("inspection_purpose")
                if call_kwargs.kwargs
                else None
            )
            if passed_purpose is None and call_kwargs.args:
                # positional args: (image_store, roi_config, inspection_purpose, ...)
                args = call_kwargs.args
                passed_purpose = args[2] if len(args) > 2 else None
            assert passed_purpose is purpose
        finally:
            os.unlink(tmp)

    # ── 14. cancel 플래그 → _execute_align_design이 False 반환 ──────────────
    def test_cancel_before_align_design_returns_false(self):
        """cancel 플래그가 설정되면 _execute_align_design이 즉시 False를 반환한다."""
        store, tmp = _store_with_align_ok()
        try:
            worker = AnalysisWorker(store, roi_config=None)
            worker._cancel_flag = True
            result = worker._execute_align_design()
            assert result is False
        finally:
            os.unlink(tmp)
