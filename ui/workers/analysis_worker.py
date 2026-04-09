"""
분석 작업 워커
백그라운드에서 분석 작업을 수행하는 QThread 워커
"""

import time
from PyQt6.QtCore import QThread, pyqtSignal

from core.image_store import ImageStore, ImageType
from core.models import ROIConfig, InspectionPurpose
from core.analyzers.feature_analyzer import FeatureAnalyzer, FullFeatureAnalysis
from ui.components.progress_steps import AnalysisStep


class AnalysisWorker(QThread):
    """백그라운드에서 분석을 수행하는 워커 스레드"""
    
    # 시그널 정의
    step_started = pyqtSignal(str)          # AnalysisStep.value
    step_finished = pyqtSignal(str, float)  # step.value, elapsed_seconds
    step_failed = pyqtSignal(str, str)      # step.value, error_message
    log_message = pyqtSignal(str, str)      # level, message
    analysis_complete = pyqtSignal(object)  # FullFeatureAnalysis
    analysis_failed = pyqtSignal(str)       # error_message
    
    def __init__(self, image_store: ImageStore, roi_config=None, inspection_purpose=None, parent=None):
        """
        분석 워커 초기화
        
        Args:
            image_store: 이미지 스토어
            roi_config: ROI 설정
            inspection_purpose: 검사 목적
            parent: 부모 객체
        """
        super().__init__(parent)
        self.image_store = image_store
        self.roi_config = roi_config
        self.inspection_purpose = inspection_purpose
        self._cancel_flag = False
        self.feature_result = None
    
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
            
            # Step 2: Align Design (placeholder)
            if not self._execute_align_design():
                return
            
            # Step 3: Inspection Design (placeholder)
            if not self._execute_inspection_design():
                return
            
            # Step 4: Evaluation (placeholder)
            if not self._execute_evaluation():
                return
            
            # 모든 단계 완료
            self.log_message.emit("SUCCESS", "모든 분석 단계가 완료되었습니다")
            self.analysis_complete.emit(self.feature_result)
            
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
        Align 설계 단계 실행 (placeholder)
        
        Returns:
            성공 여부
        """
        if self._check_cancel():
            return False
        
        step_name = AnalysisStep.ALIGN_DESIGN.value
        self.step_started.emit(step_name)
        self.log_message.emit("INFO", "Align 설계 단계 (Step 27-28에서 구현 예정)")
        
        start_time = time.time()
        
        # Placeholder 실행
        time.sleep(0.1)
        
        elapsed_time = time.time() - start_time
        self.step_finished.emit(step_name, elapsed_time)
        self.log_message.emit("SUCCESS", "Align 설계 단계 완료 (placeholder)")
        
        return True
    
    def _execute_inspection_design(self) -> bool:
        """
        검사 설계 단계 실행 (placeholder)
        
        Returns:
            성공 여부
        """
        if self._check_cancel():
            return False
        
        step_name = AnalysisStep.INSPECTION_DESIGN.value
        self.step_started.emit(step_name)
        self.log_message.emit("INFO", "검사 설계 단계 (Step 27-28에서 구현 예정)")
        
        start_time = time.time()
        
        # Placeholder 실행
        time.sleep(0.1)
        
        elapsed_time = time.time() - start_time
        self.step_finished.emit(step_name, elapsed_time)
        self.log_message.emit("SUCCESS", "검사 설계 단계 완료 (placeholder)")
        
        return True
    
    def _execute_evaluation(self) -> bool:
        """
        평가 단계 실행 (placeholder)
        
        Returns:
            성공 여부
        """
        if self._check_cancel():
            return False
        
        step_name = AnalysisStep.EVALUATION.value
        self.step_started.emit(step_name)
        self.log_message.emit("INFO", "평가 단계 (Step 27-28에서 구현 예정)")
        
        start_time = time.time()
        
        # Placeholder 실행
        time.sleep(0.1)
        
        elapsed_time = time.time() - start_time
        self.step_finished.emit(step_name, elapsed_time)
        self.log_message.emit("SUCCESS", "평가 단계 완료 (placeholder)")
        
        return True