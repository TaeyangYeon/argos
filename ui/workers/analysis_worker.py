"""
분석 작업 워커
백그라운드에서 분석 작업을 수행하는 QThread 워커
"""

import time
from PyQt6.QtCore import QThread, pyqtSignal

import logging

from core.image_store import ImageStore, ImageType
from core.models import ROIConfig, InspectionPurpose, AlignResult
from core.analyzers.feature_analyzer import FeatureAnalyzer, FullFeatureAnalysis
from ui.components.progress_steps import AnalysisStep

worker_logger = logging.getLogger("argos.ui.analysis_worker")


class AnalysisWorker(QThread):
    """백그라운드에서 분석을 수행하는 워커 스레드"""

    # 시그널 정의
    step_started = pyqtSignal(str)          # AnalysisStep.value
    step_finished = pyqtSignal(str, float)  # step.value, elapsed_seconds
    step_failed = pyqtSignal(str, str)      # step.value, error_message
    log_message = pyqtSignal(str, str)      # level, message
    analysis_complete = pyqtSignal(object)  # FullFeatureAnalysis
    align_complete = pyqtSignal(object)     # AlignResult (or FallbackAlignResult)
    inspection_complete = pyqtSignal(object)  # OptimizationResult
    evaluation_complete = pyqtSignal(object)  # dict with failure_result + feasibility_result
    analysis_failed = pyqtSignal(str)       # error_message

    def __init__(
        self,
        image_store: ImageStore,
        roi_config=None,
        inspection_purpose: "InspectionPurpose | None" = None,
        ai_provider=None,
        parent=None,
    ):
        """
        분석 워커 초기화

        Args:
            image_store: 이미지 스토어
            roi_config: ROI 설정
            inspection_purpose: 검사 목적
            ai_provider: AI 프로바이더 (None 허용)
            parent: 부모 객체
        """
        super().__init__(parent)
        self.image_store = image_store
        self.roi_config = roi_config
        self.inspection_purpose = inspection_purpose
        self._ai_provider = ai_provider
        self._cancel_flag = False
        self.feature_result = None
        self._align_result = None
        self._results: dict = {}

    def cancel(self):
        """분석 작업 취소"""
        self._cancel_flag = True
        self.log_message.emit("WARNING", "분석 작업이 취소되었습니다")

    def is_cancelled(self) -> bool:
        """
        취소 상태 확인

        Returns:
            취소 여부
        """
        return self._cancel_flag

    def run(self):
        """
        메인 분석 실행 함수
        백그라운드에서 각 단계별로 분석을 수행
        """
        try:
            self.log_message.emit("INFO", "분석을 시작합니다")

            # Basic validation: ensure we have at least some images to work with
            all_images = self.image_store.get_all()
            if not all_images:
                error_msg = "분석할 이미지가 없습니다"
                self.log_message.emit("ERROR", error_msg)
                self.analysis_failed.emit(error_msg)
                return

            # Step 1: Feature Analysis
            if not self._execute_feature_analysis():
                return

            # Step 2: Align Design (real AlignFallbackChain)
            if not self._execute_align_design():
                return

            # Step 3: Inspection Design (placeholder)
            if not self._execute_inspection_design():
                return

            # Step 4: Evaluation (placeholder)
            if not self._execute_evaluation():
                return

            # 모든 단계 완료 — aggregate dict 생성
            self.log_message.emit("SUCCESS", "모든 분석 단계가 완료되었습니다")
            aggregate = {
                "feature": self.feature_result,
                "align": self._results.get("align"),
                "inspection": self._results.get("inspection"),
                "evaluation": self._results.get("evaluation"),
                "inspection_purpose": self.inspection_purpose,
            }
            self.analysis_complete.emit(aggregate)

        except Exception as e:
            error_msg = f"분석 중 예기치 않은 오류가 발생했습니다: {str(e)}"
            self.log_message.emit("ERROR", error_msg)
            self.analysis_failed.emit(error_msg)

    def _check_cancel(self) -> bool:
        """
        취소 여부 확인

        Returns:
            True if cancelled, False otherwise
        """
        if self._cancel_flag:
            self.log_message.emit("WARNING", "분석이 취소되었습니다")
            return True
        return False

    def _execute_feature_analysis(self) -> bool:
        """
        특성 분석 단계 실행

        Returns:
            성공 여부
        """
        if self._check_cancel():
            return False

        step_name = AnalysisStep.FEATURE_ANALYSIS.value
        self.step_started.emit(step_name)
        self.log_message.emit("INFO", "특성 분석을 시작합니다")

        start_time = time.time()

        try:
            # Get all images from ImageStore
            all_images = self.image_store.get_all()

            if not all_images:
                error_msg = "분석할 이미지가 없습니다"
                self.log_message.emit("ERROR", error_msg)
                self.step_failed.emit(step_name, error_msg)
                return False

            # Use the first available image for feature analysis
            first_image_meta = all_images[0]
            self.log_message.emit("INFO", f"이미지 분석 중: {first_image_meta.file_path}")

            # Load the actual image data
            image_array = self.image_store.load_image(first_image_meta.id)

            # FeatureAnalyzer를 사용하여 전체 특성 분석 수행
            analyzer = FeatureAnalyzer()
            self.feature_result = analyzer.analyze_full(image_array, first_image_meta.file_path)

            # OK/NG 분리도 분석 (OK와 NG 이미지가 모두 있는 경우)
            ok_images_meta = self.image_store.get_all(ImageType.INSPECTION_OK)
            ng_images_meta = self.image_store.get_all(ImageType.INSPECTION_NG)

            if ok_images_meta and ng_images_meta:
                self.log_message.emit("INFO", f"OK/NG 분리도 분석 중: OK {len(ok_images_meta)}장, NG {len(ng_images_meta)}장")

                # Load image arrays
                ok_arrays = [self.image_store.load_image(meta.id) for meta in ok_images_meta]
                ng_arrays = [self.image_store.load_image(meta.id) for meta in ng_images_meta]

                # Analyze separation
                separation = analyzer.analyze_ok_ng_separation(ok_arrays, ng_arrays)
                self.feature_result.histogram.separation_score = separation["separation_score"]

                print(f"[SEPARATION] score: {separation['separation_score']}", flush=True)
                self.log_message.emit("INFO", f"분리도 점수: {separation['separation_score']:.1f}%")
            else:
                self.log_message.emit("INFO", "OK 또는 NG 이미지가 없어 분리도 분석을 건너뜁니다")

            elapsed_time = time.time() - start_time
            self.step_finished.emit(step_name, elapsed_time)
            self.log_message.emit("SUCCESS", f"특성 분석 완료 ({elapsed_time:.1f}초)")

            return True

        except Exception as e:
            elapsed_time = time.time() - start_time
            error_msg = f"특성 분석 중 오류 발생: {str(e)}"
            self.log_message.emit("ERROR", error_msg)
            self.step_failed.emit(step_name, error_msg)
            return False

    def _execute_align_design(self) -> bool:
        """
        Align 설계 단계 실행 — AlignFallbackChain 사용

        Returns:
            성공 여부
        """
        if self._check_cancel():
            return False

        step_name = AnalysisStep.ALIGN_DESIGN.value
        self.step_started.emit(step_name)
        self.log_message.emit("INFO", "Align 설계 단계를 시작합니다")

        start_time = time.time()

        try:
            # ── Load ALIGN_OK images ──────────────────────────────────────
            align_ok_metas = self.image_store.get_all(ImageType.ALIGN_OK)

            if not align_ok_metas:
                self.log_message.emit("WARNING", "ALIGN_OK 이미지가 없습니다 — Align 설계를 건너뜁니다")
                failed_result = AlignResult(
                    success=False,
                    strategy_name="no_align_image",
                    score=0.0,
                    failure_reason="ALIGN_OK 이미지가 없어 Align을 실행할 수 없습니다",
                )
                self._align_result = failed_result
                self._results["align"] = failed_result
                self.align_complete.emit(failed_result)
                elapsed_time = time.time() - start_time
                self.step_finished.emit(step_name, elapsed_time)
                self.log_message.emit("SUCCESS", f"Align 설계 단계 완료 — 이미지 없음 ({elapsed_time:.1f}초)")
                return True

            # ── Use first ALIGN_OK image as the input (template = reference) ──
            first_meta = align_ok_metas[0]
            image = self.image_store.load_image(first_meta.id)
            self.log_message.emit("INFO", f"Align 이미지 로드: {first_meta.file_path}")

            # ── Instantiate AlignFallbackChain ─────────────────────────────
            from core.align.align_engine import AlignFallbackChain
            try:
                chain = AlignFallbackChain(
                    image_store=self.image_store,
                    roi_config=self.roi_config,
                    inspection_purpose=self.inspection_purpose,
                    ai_provider=self._ai_provider,
                )
            except TypeError:
                # Fallback: older signature without ai_provider
                self.log_message.emit("WARNING", "AlignFallbackChain: ai_provider 파라미터 없음 — 기본 생성자 사용")
                chain = AlignFallbackChain(
                    image_store=self.image_store,
                    roi_config=self.roi_config,
                    inspection_purpose=self.inspection_purpose,
                )

            # ── Run the chain ──────────────────────────────────────────────
            align_result = chain.run(image)
            self._align_result = align_result
            self._results["align"] = align_result

            self.log_message.emit(
                "INFO",
                f"Align 완료 — 전략: {align_result.strategy_name}, "
                f"점수: {align_result.score * 100:.1f}%"
            )

            # ── Emit result ────────────────────────────────────────────────
            self.align_complete.emit(align_result)

            elapsed_time = time.time() - start_time
            self.step_finished.emit(step_name, elapsed_time)
            self.log_message.emit("SUCCESS", f"Align 설계 완료 ({elapsed_time:.1f}초)")
            return True

        except Exception as e:
            elapsed_time = time.time() - start_time
            error_msg = f"Align 설계 중 오류 발생: {str(e)}"
            self.log_message.emit("ERROR", error_msg)

            # Emit a synthetic failed result so the UI shows failure gracefully
            failed_result = AlignResult(
                success=False,
                strategy_name="error",
                score=0.0,
                failure_reason=error_msg,
            )
            self._align_result = failed_result
            self._results["align"] = failed_result
            self.align_complete.emit(failed_result)

            self.step_failed.emit(step_name, error_msg)
            return False

    def _execute_inspection_design(self) -> bool:
        """
        검사 설계 단계 실행 — DynamicCandidateGenerator + InspectionOptimizer

        Returns:
            성공 여부
        """
        if self._check_cancel():
            return False

        step_name = AnalysisStep.INSPECTION_DESIGN.value
        self.step_started.emit(step_name)
        self.log_message.emit("INFO", "검사 설계 단계를 시작합니다")

        start_time = time.time()

        try:
            # ── Check for NG images ──────────────────────────────────────
            ok_images_meta = self.image_store.get_all(ImageType.INSPECTION_OK)
            ng_images_meta = self.image_store.get_all(ImageType.INSPECTION_NG)

            if not ng_images_meta:
                self.log_message.emit(
                    "WARNING",
                    "NG 이미지가 없습니다 — Inspection 설계를 건너뜁니다. "
                    "정확한 검사 알고리즘 평가를 위해 NG 이미지를 추가하세요."
                )
                self._results["inspection"] = None
                elapsed_time = time.time() - start_time
                self.step_finished.emit(step_name, elapsed_time)
                self.log_message.emit("SUCCESS", f"검사 설계 단계 완료 — NG 없음 ({elapsed_time:.1f}초)")
                return True

            # ── Check for feature analysis result ────────────────────────
            if self.feature_result is None:
                error_msg = "특성 분석 결과가 없어 검사 설계를 진행할 수 없습니다"
                self.log_message.emit("ERROR", error_msg)
                self.step_failed.emit(step_name, error_msg)
                return False

            # ── Load images ──────────────────────────────────────────────
            ok_arrays = [self.image_store.load_image(m.id) for m in ok_images_meta]
            ng_arrays = [self.image_store.load_image(m.id) for m in ng_images_meta]
            self.log_message.emit(
                "INFO",
                f"이미지 로드 완료: OK {len(ok_arrays)}장, NG {len(ng_arrays)}장"
            )

            # ── Ensure InspectionPurpose exists ──────────────────────────
            purpose = self.inspection_purpose or InspectionPurpose()

            # ── Step 3a: Generate candidates ─────────────────────────────
            from core.inspection.candidate_generator import DynamicCandidateGenerator

            self.log_message.emit("INFO", "후보 엔진 생성 중...")
            generator = DynamicCandidateGenerator(ai_provider=self._ai_provider)
            candidates = generator.generate(self.feature_result, purpose)
            self.log_message.emit(
                "INFO",
                f"후보 엔진 {len(candidates)}개 생성 완료: "
                + ", ".join(c.engine_name for c in candidates)
            )

            # ── Step 3b: Optimize (evaluate each candidate) ──────────────
            from core.inspection.optimizer import InspectionOptimizer
            from config.settings import Settings

            self.log_message.emit("INFO", "최적화 루프 실행 중...")
            optimizer = InspectionOptimizer()
            settings = Settings()
            opt_result = optimizer.run(candidates, ok_arrays, ng_arrays, settings)

            best_name = getattr(opt_result.best_candidate, "engine_name", "Unknown")
            best_score = getattr(opt_result.best_evaluation, "final_score", 0.0)
            self.log_message.emit(
                "INFO",
                f"최적화 완료 — 최적 엔진: {best_name}, 점수: {best_score:.1f}"
            )

            self._results["inspection"] = opt_result
            self.inspection_complete.emit(opt_result)

            elapsed_time = time.time() - start_time
            self.step_finished.emit(step_name, elapsed_time)
            self.log_message.emit("SUCCESS", f"검사 설계 완료 ({elapsed_time:.1f}초)")
            return True

        except Exception as e:
            elapsed_time = time.time() - start_time
            error_msg = f"검사 설계 중 오류 발생: {str(e)}"
            worker_logger.error(error_msg, exc_info=True)
            self.log_message.emit("ERROR", error_msg)
            self._results["inspection"] = None
            self.step_failed.emit(step_name, error_msg)
            return False

    def _execute_evaluation(self) -> bool:
        """
        평가 단계 실행 — FailureAnalyzer + FeasibilityAnalyzer

        Returns:
            성공 여부
        """
        if self._check_cancel():
            return False

        step_name = AnalysisStep.EVALUATION.value
        self.step_started.emit(step_name)
        self.log_message.emit("INFO", "평가 단계를 시작합니다")

        start_time = time.time()

        try:
            opt_result = self._results.get("inspection")

            if opt_result is None:
                self.log_message.emit(
                    "WARNING",
                    "Inspection 결과가 없습니다 — 평가 단계를 건너뜁니다"
                )
                self._results["evaluation"] = None
                elapsed_time = time.time() - start_time
                self.step_finished.emit(step_name, elapsed_time)
                self.log_message.emit("SUCCESS", f"평가 단계 완료 — Inspection 없음 ({elapsed_time:.1f}초)")
                return True

            purpose = self.inspection_purpose or InspectionPurpose()

            # ── Step 4a: Failure Analysis ────────────────────────────────
            from core.evaluation.failure_analyzer import FailureAnalyzer

            self.log_message.emit("INFO", "실패 분석 실행 중...")
            failure_analyzer = FailureAnalyzer(
                ai_provider=self._ai_provider,
            )
            failure_result = failure_analyzer.analyze(opt_result, purpose)
            self.log_message.emit(
                "INFO",
                f"실패 분석 완료 — FP: {failure_result.fp_count}건, "
                f"FN: {failure_result.fn_count}건"
            )

            # ── Step 4b: Feasibility Analysis ────────────────────────────
            from core.evaluation.feasibility_analyzer import FeasibilityAnalyzer
            from config.settings import Settings

            self.log_message.emit("INFO", "기술 수준 판단 실행 중...")
            feasibility_analyzer = FeasibilityAnalyzer(
                ai_provider=self._ai_provider,
            )
            settings = Settings()
            best_eval = opt_result.best_evaluation
            best_score = getattr(best_eval, "final_score", 0.0)

            feasibility_result = feasibility_analyzer.analyze(
                best_score=best_score,
                threshold=settings.score_threshold,
                evaluation_result=best_eval,
                inspection_purpose=purpose,
            )
            self.log_message.emit(
                "INFO",
                f"기술 수준 판단 완료 — 권장: {feasibility_result.recommended_approach}"
            )

            eval_results = {
                "failure_result": failure_result,
                "feasibility_result": feasibility_result,
            }
            self._results["evaluation"] = eval_results
            self.evaluation_complete.emit(eval_results)

            elapsed_time = time.time() - start_time
            self.step_finished.emit(step_name, elapsed_time)
            self.log_message.emit("SUCCESS", f"평가 단계 완료 ({elapsed_time:.1f}초)")
            return True

        except Exception as e:
            elapsed_time = time.time() - start_time
            error_msg = f"평가 중 오류 발생: {str(e)}"
            worker_logger.error(error_msg, exc_info=True)
            self.log_message.emit("ERROR", error_msg)
            self._results["evaluation"] = None
            self.step_failed.emit(step_name, error_msg)
            return False
