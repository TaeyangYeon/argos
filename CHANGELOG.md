# Changelog

이 문서는 Argos 프로젝트의 주요 변경 사항을 기록합니다.

---

## v1.0.0 (2026-04-20)

**최초 정식 릴리스** — 51개 Step, 1087개 테스트 통과

### Phase 1: 프로젝트 기반 구축 (Step 1~8) — 2026-04-04 ~ 2026-04-06

프로젝트 구조 초기화, SOLID 인터페이스 정의, 설정/상수 관리, 로깅/에러 핸들링,
AI Provider 레이어, API Key 암호화 저장, 입력 검증, 이미지 데이터 모델 구축.

- Step 1: 프로젝트 구조 및 개발 환경 초기화
- Step 2: SOLID 인터페이스 정의
- Step 3: 설정 및 상수 관리 모듈
- Step 4: 로깅 및 에러 핸들링 기반
- Step 5: AI Provider Layer 기반
- Step 6: API Key 암호화 저장 모듈
- Step 7: 입력 검증 레이어 구현
- Step 8: 이미지 데이터 모델 및 저장소

### Phase 2: UI 기본 골격 (Step 9~16) — 2026-04-06 ~ 2026-04-08

PyQt6 메인 윈도우, 상단 툴바, 좌측 사이드바, 대시보드, 이미지 업로드(드래그&드롭),
썸네일 그리드, ROI 설정(마우스 드래그), 설정 화면 구현.

- Step 9: PyQt6 메인 윈도우 및 레이아웃
- Step 10: 상단 툴바 및 API 입력 버튼
- Step 11: 좌측 사이드바 네비게이션
- Step 12: 대시보드 화면
- Step 13: 이미지 업로드 화면
- Step 14: 이미지 썸네일 그리드 및 관리
- Step 15: ROI 설정 화면
- Step 16: 설정 화면

### Phase 3: Feature 분석 엔진 (Step 17~24) — 2026-04-08

이미지 전처리 유틸리티, 히스토그램/밝기 분석, 노이즈 분석, 에지 강도 분석,
형상/Blob 분석, Feature 통합 및 AI 요약, 검사 목적 데이터 모델, 검사 목적 입력 UI.

- Step 17: 이미지 로드 및 전처리 유틸리티
- Step 18: 히스토그램 및 밝기 분석
- Step 19: 노이즈 수준 분석
- Step 20: 에지 강도 분석
- Step 21: 형상 및 Blob 특성 분석
- Step 22: Feature 분석 통합 및 AI 요약
- Step 23: 검사 목적 데이터 모델 및 검증 레이어
- Step 24: 검사 목적 입력 페이지 UI

### Phase 4: 분석 실행 UI + Align 통합 (Step 25~32) — 2026-04-09 ~ 2026-04-11

분석 실행 화면, Feature 결과 뷰어, Pattern/Caliper/Feature-based/Contour/Blob Align 엔진,
Align Fallback 체인, Align 결과 UI, 통합 테스트.

- Step 25: 분석 실행 화면 UI
- Step 26: Feature Analysis 결과 뷰어 UI
- Step 27: Pattern Matching Align 엔진
- Step 28: Caliper Align 엔진
- Step 29: Feature-based / Contour / Blob Align 엔진
- Step 30: Align Fallback 체인 통합
- Step 31: Align 결과 UI 표시
- Step 32: Align 통합 테스트 및 검증

### Phase 5: Inspection 엔진 (Step 33~41) — 2026-04-11 ~ 2026-04-14

Blob/Circular Caliper/Linear Caliper/Pattern Inspection 엔진, Dynamic Candidate 생성기,
평가 엔진(Evaluator), 최적화 루프(Optimizer), Failure 분석.

- Step 33: Blob 기반 Inspection 엔진
- Step 34: AnalysisWorker Align 단계 연동
- Step 35: Circular Caliper Inspection 엔진
- Step 36: Linear Caliper Inspection 엔진
- Step 37: Pattern 기반 Inspection 엔진
- Step 38: Dynamic Candidate 생성기
- Step 39: 평가 엔진 (Evaluation)
- Step 40: 최적화 루프 및 Best Candidate 선택
- Step 41: Failure 분석

### Phase 6: 결과 뷰어 및 출력 (Step 42~46) — 2026-04-15 ~ 2026-04-18

Feasibility 분석(Rule-based/EL/DL 판정), Inspection 통합 테스트, 결과 뷰어 레이아웃(6탭),
Inspection 결과 카드/파라미터 테이블, Failure 케이스 뷰어.

- Step 42: Feasibility Analysis 및 기술 수준 판단
- Step 43: Inspection 통합 테스트 및 AnalysisWorker 연동
- Step 44: 결과 뷰어 레이아웃
- Step 45: Inspection 결과 카드 및 파라미터 테이블
- Step 46: Failure 케이스 뷰어

### Phase 7: 통합 완성 및 운영 품질 (Step 47~51) — 2026-04-18 ~ 2026-04-20

Feasibility 결과 표시(기술 수준 배지/점수/AI 근거/추천 모델/흐름도),
결과 내보내기(JSON/PDF/이미지), 대시보드 워크플로우 연동,
UI 품질 개선(디자인 토큰/로딩 스피너/빈 상태/툴팁), E2E 테스트, PyInstaller 배포 패키징,
최종 문서화 및 릴리스 준비.

- Step 47: Feasibility 및 기술 수준 결과 표시
- Step 48: 결과 내보내기 (Export)
- Step 49: 대시보드 및 워크플로우 최종 연동
- Step 50: UI 품질 개선, E2E 테스트 및 PyInstaller 배포 패키징
- Step 51: 최종 검수 및 문서화, v1.0.0 릴리스

### 테스트 현황

- 전체 테스트: **1087개 통과**
- 테스트 범위: unit, e2e, integration, inspection, evaluation, workers
- 프레임워크: pytest + pytest-qt
