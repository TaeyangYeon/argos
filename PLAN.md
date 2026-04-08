# 🧠 AI Vision Engineer Agent 개발 계획서 (v6)

---

## 🎯 1. 프로젝트 정의

### 목표

사용자가:

- Align 이미지 (OK)
- Inspection OK 이미지
- Inspection NG 이미지
- ROI 직접 지정
- **검사 목적 입력** ← 필수 입력

을 제공하면,

👉 **Align + ROI + 전처리 + Inspection 전체 알고리즘 자동 설계**
👉 **최적 결과 + 실패 케이스 + 원인 + 기술 수준 판단까지 제공**

### 최종 한 줄 정의

> **"비전 알고리즘을 설계하고, 한계를 판단하며, 필요한 기술 수준까지 결정하는 AI Vision Engineer Agent"**

### 대상 사용자

**비전 엔지니어 보조 도구.** 비전 지식이 있는 엔지니어가 자신의 환경(Keyence, Cognex, MIL, Halcon 등)에서 바로 구현할 수 있는 수준의 알고리즘과 파라미터를 제공한다. 기초 개념 설명은 생략하고 알고리즘 근거와 파라미터 선택 이유에 집중한다.

---

## 🔥 2. 핵심 설계 철학

| 원칙 | 설명 |
|------|------|
| 단순 추천 금지 | 결과 = 설계된 알고리즘 전체 |
| Multi-Candidate 구조 | 다양한 방법 생성 → 평가 → 선택 |
| 데이터 기반 검증 | OK / NG 기반 실제 성능 판단 |
| 실패까지 제공 | 실패 이미지 + 원인 + 개선 방향 |
| 기술 수준 판단 | Rule-based / Edge Learning / Deep Learning |
| AI 최소 사용 | 비용 절감 + 보안 (이미지 외부 전송 최소화) |
| CPU 기반 실행 | GPU 없이 동작 (DL/EL은 추천만, 모델 제공 아님) |
| 매 Step 직접 검증 | 테스트 통과 + 사용자 직접 UI 실행 확인 |

### 2.1 SOLID 기반 설계

| 원칙 | 적용 |
|------|------|
| S - Single Responsibility | AlignEngine / InspectionEngine / EvaluationEngine 분리 |
| O - Open/Closed | 새로운 검사 방법 추가 시 기존 코드 수정 없이 확장 |
| L - Liskov Substitution | 모든 알고리즘은 동일 인터페이스 사용 |
| I - Interface Segregation | 작은 인터페이스로 분리 |
| D - Dependency Inversion | 구현이 아닌 추상에 의존 |

---

## 🖥️ 3. 배포 전략

- **서버 없음 — 로컬 단독 실행** 확정
- Python 기반 단일 코드베이스, Windows / macOS / Linux 모두 동작
- UI: **PyQt6** (데스크톱 네이티브, 모던 스타일시트 적용)
- 배포 형태:
  - `pip install` 방식
  - PyInstaller 단일 실행 파일 (.exe / .app / 바이너리)
- 외부 네트워크: AI API 호출 시에만 사용, 이미지는 로컬에서만 처리

---

## 🎨 4. UI 설계 원칙

운영 수준의 모던 UI를 목표로 한다.

### 4.1 디자인 방향

- **다크 테마 기반** 모던 디자인 (산업용 비전 툴 레퍼런스)
- 좌측 사이드바 네비게이션 (워크플로우 단계별 이동)
- 상단 툴바: 프로젝트명 / AI 상태 표시 / API 입력 버튼
- 컬러 시스템: 주조색 `#1E88E5` (파랑), 배경 `#1A1A2E`, 카드 `#16213E`
- 폰트: Pretendard 또는 Noto Sans KR

### 4.2 주요 화면 구성

| 화면 | 설명 |
|------|------|
| 대시보드 | 프로젝트 현황, 최근 분석 결과 요약 |
| 이미지 업로드 | Drag & Drop, 썸네일 그리드, 분류 태그 (OK/NG/Align) |
| ROI 설정 | 이미지 위에서 마우스로 직접 드래그, 좌표 수동 입력 병행 |
| **검사 목적 입력** | 검사 유형 선택, 상세 설명, OK/NG 판정 기준 입력 |
| 분석 실행 | 진행 상태 바, 단계별 로그 실시간 출력 |
| 결과 뷰어 | 알고리즘 결과 카드, 파라미터 테이블, 시각화 오버레이 |
| 설정 | AI Provider 선택, 임계값 조정, FP/FN 가중치 |

### 4.3 AI API 입력 방식

- 상단 툴바 우측 **"🔑 API 입력"** 버튼
- 클릭 시 모달 다이얼로그 출현
- Provider 선택 (OpenAI / Claude / Gemini) → API Key 입력 → 연결 테스트 버튼
- 입력된 키는 로컬 암호화 저장 (AES/Fernet 암호화)
- 연결 상태: 상단 툴바에 `● 연결됨 / ● 미연결` 표시
- API Key는 절대 평문으로 로그에 출력하지 않음

---

## ✅ 5. 개발 검증 원칙 (매 Step 적용)

이전 프로젝트의 실패 교훈을 반영하여, **모든 Step은 반드시 아래 3단계를 완료해야 다음 Step으로 진행한다.**

```
① TDD — pytest 테스트 통과
② Human Review — 핵심 로직 코드 직접 확인
③ 직접 실행 — UI를 실제로 실행하여 해당 Step 기능 눈으로 확인
```

> ⚠️ 테스트만 통과하고 직접 실행을 생략하는 것은 허용하지 않는다.
> AI가 테스트와 코드를 동시에 잘못 생성하는 경우(둘 다 통과하지만 실제로는 틀린 로직)를
> 직접 실행 확인으로만 잡을 수 있다.

### Step 완료 체크리스트 (매 Step 공통)

```
□ pytest 전체 통과
□ 해당 Step 신규 기능 코드 Human Review 완료
□ UI 실행하여 해당 기능 직접 동작 확인
□ 이전 Step 기능 regression 없음 확인
□ git commit 완료
```

---

## 🧩 6. AI 기반 개발 방식

```
기획자 (Taeyang)
 ↓
생성형 AI (Claude) — PLAN.md 기반 PCRO 프롬프트 생성
 ↓
Claude Code — 실제 코드 + 테스트 코드 구현
 ↓
TDD 검증 (pytest)
 ↓
Human Review + 직접 UI 실행 확인
 ↓
git commit (메시지는 Claude가 제공)
```

---

## 📋 7. Step 진행 출력 규칙

**"step N 시작해줘"** 라고 하면 Claude는 항상 아래 3개 섹션을 순서대로 출력한다.

### 섹션 1 — Claude Code 프롬프트 (PCRO 형식, 영문)

```
## Step N Claude Code Prompt (PCRO)

[P - Persona]
...

[C - Context]
...

[R - Restriction]
...

[O - Output Format]
...
```

### 섹션 2 — 실행 및 확인 방법

```
## 실행 및 확인 방법

1. 테스트 실행
   pytest tests/... -v
   □ 전체 PASSED 확인

2. 앱 실행 (UI가 있는 Step의 경우)
   python main.py

3. 순서별 확인 내용
   □ 확인 항목 1
   □ 확인 항목 2
   ...
```

확인 방법은 **간결하게** 작성한다. 단계별 번호, 클릭할 버튼, 확인할 내용을 명확히 명시.

### 섹션 3 — Git Commit Message

```
## Git Commit Message

feat: 한글로 작성된 커밋 메시지

- 변경 파일 및 내용 요약
```

커밋 메시지 규칙:
- prefix (`feat:`, `fix:`, `chore:` 등) 는 영문
- 그 이후 내용은 모두 한글

---

## ⚠️ 8. 에러 처리 전략

### Layer 1: 입력 검증 (Input Validation)

| 검증 항목 | 기준 | 처리 |
|----------|------|------|
| 이미지 포맷 | BMP, PNG, TIFF, JPEG | 즉시 오류 반환 |
| 해상도 | 64×64 이하 거부 | 오류 메시지 |
| 파일 손상 | 열기 실패 | 오류 메시지 |
| ROI 범위 | 경계 초과 / 크기 0 / 전체 대비 1% 미만 | 오류 메시지 |
| NG 이미지 0장 | Inspection 설계 진입 불가 | 알람 모달 출력 |
| 검사 목적 미입력 | 분석 실행 불가 | 알람 표시 |

### Layer 2: 처리 중 예외 (Runtime Exception)

- 알고리즘 실행 예외는 try-except로 격리, 해당 candidate만 실패 처리
- 전체 candidate 실패 시에만 상위 에러 전파
- AI API 타임아웃: 30초, retry 2회 후 → graceful degradation (로컬 룰베이스 결과만 제공)

### Layer 3: 결과 검증 (Output Validation)

- 알고리즘 생성 후 OK 샘플 적용 스코어 < 기준 → "알고리즘 생성 실패" + 사유 출력

### 데이터 부족 알람

```
⚠️  NG 이미지가 필요합니다.
    Inspection 알고리즘 설계를 위해 NG 이미지를 1장 이상 업로드해주세요.
    현재 등록: OK {n}장 / NG 0장
```

- NG 1~2장: "샘플 부족 — 정확도 신뢰도 낮음" 경고 병기
- NG 3장 이상: 정상 진행

---

## 📊 9. 성능 목표치 (SLA)

검사 속도 제외. **분류 품질 기준만** 정의.

| 지표 | 기준 |
|------|------|
| OK 샘플 스코어 | ≥ 사용자 설정 임계값 (기본: 70) |
| NG 샘플 스코어 | < 사용자 설정 임계값 |
| OK ↔ NG 분리 마진 | ≥ 15점 (권장) |

- 마진 15점 미만: "경계선 위험 구간" 경고 병기
- 임계값 미달 candidate 없을 경우: EL/DL 추천 자동 전환

### Multi-Candidate 평가 공식

```
score = (OK 샘플 통과율 × w1) + (NG 샘플 검출율 × w2)
기본값: w1 = 0.5, w2 = 0.5
```

사용자가 FP/FN 가중치 조정 가능 (FN이 더 치명적인 경우 w2 상향).

---

## 🔧 10. Align 설계

### Fallback 체인

```
1단계: Pattern Matching (템플릿 매칭, 정규화 상관)
    ↓ 실패 (매칭 점수 < 기준)
2단계: Caliper (에지 기반 기준점 탐색)
    ↓ 실패 (유효 에지 미검출)
3단계: AI 판단 추가 전략 (이미지 특성 기반 순서 결정)
    - Feature-based (ORB, SIFT 기반 키포인트)
    - Contour-based (윤곽선 형상 매칭)
    - Blob Detection (특정 영역 중심점)
    ↓ 모두 실패
최종: "Align 처리 실패" + 실패 원인 + 권장 조치
```

각 단계 실패 시 원인(낮은 대비 / 반복 패턴 / 텍스처 부족 등)을 로그로 남김.

---

## 🔍 11. Inspection 설계

### 기술 수준 판단 로직

```
Rule-based 후보 평가
    ↓
best_candidate_score ≥ threshold
    → Rule-based 알고리즘 출력

best_candidate_score < threshold
    → AI가 이미지 상태 + 검사 난이도 판단
       → EL 또는 DL 추천 + 판단 근거 텍스트 출력
```

EL/DL 판단 시 AI 고려 요소: 노이즈 수준, 결함 형태 복잡도, 배경 변동성, OK/NG 경계 모호함.

> DL/EL 추천은 "룰베이스로 불가능하므로 학습 기반이 필요하다"는 결론 제공. 모델 자체 미제공 → GPU 불필요.

---

## 📤 12. 출력 형식 (라이브러리 독립적)

### 핵심 원칙

Library-Agnostic 출력. OpenCV, Keyence, Cognex, Halcon, MIL 어디서도 적용 가능.
파라미터는 항상 `파라미터명 | 설정값 | 선택 근거` 세트로 출력.

### Caliper 출력 4섹션 구조 (필수)

```
① 배치 구조
   배치 방식 (Circular / Linear / Arc / Grid)
   개수 / 각도 간격 또는 위치 간격 / 시작 위치 / 기준점
   탐색 방향 (Inward / Outward / Leftward / Rightward / CW / CCW)

② 개별 Caliper 파라미터
   Projection Length / Search Length
   Condition (First / Best / Last / All)
   Threshold / Polarity / Edge Filter

③ 결과 계산 방식
   검출점 → 최종 측정값 환산 방법
   이상치 처리 기준 / 신뢰도 판정 조건

④ 선택 근거
   이미지 분석 수치 기반 (그레이값, 대비, 크기)
   Condition / 방향 / 개수 선택 이유
```

### 라이브러리 대응 명칭 병기

| 개념 | Keyence | Cognex | Halcon | MIL |
|------|---------|--------|--------|-----|
| Search Length | 탐색 폭 | Search Length | SearchExtent | M_SEARCH_LENGTH |
| Condition: Best | 최적 에지 | Best | 'best' | M_BEST_CONTRAST |
| Inward | 내측 방향 | Inward | 'inner' | M_INWARD |
| Projection Length | 투영 길이 | Projection Length | ProfileLength | M_PROJECTION_LENGTH |

---

## 🔐 13. AI 연결 구조

- Provider 추상화 레이어 (OpenAI / Claude / Gemini 교체 가능)
- API Key: UI 상단 "🔑 API 입력" 버튼 → 모달 입력 → 로컬 암호화 저장
- 모델 버전 고정 (재현성 보장)
- AI 호출 시점: Feature Analysis / Candidate 생성 / Feasibility 판단 / Fallback 전략 결정에만 사용
- 이미지 원본 외부 전송 금지 (텍스트 분석 결과만 API 전달)

---

## 🚀 14. 개발 단계 (51 Steps)

### 현재 진행 상황

- ✅ **Step 1~22 완료** (Phase 1~3 Feature 분석 엔진까지)
- 🔄 **Step 23부터 진행 예정**

### Step 완료 현황

| Phase | 범위 | 상태 |
|-------|------|------|
| Phase 1 | Step 1~8 — 프로젝트 기반 구축 | ✅ 완료 |
| Phase 2 | Step 9~16 — UI 기본 골격 | ✅ 완료 |
| Phase 3 | Step 17~22 — Feature 분석 엔진 | ✅ 완료 |
| Phase 4 | Step 23~24 — 검사 목적 입력 UI | 🔲 대기 |
| Phase 5 | Step 25~26 — 분석 실행 UI | 🔲 대기 |
| Phase 6 | Step 27~34 — Align 엔진 | 🔲 대기 |
| Phase 7 | Step 35~44 — Inspection 엔진 | 🔲 대기 |
| Phase 8 | Step 45~49 — 결과 뷰어 및 출력 | 🔲 대기 |
| Phase 9 | Step 50~51 — 통합 완성 및 운영 품질 | 🔲 대기 |

---

## Phase 1: 프로젝트 기반 구축 (Step 1~8) ✅ 완료

---

### Step 1 — 프로젝트 구조 및 개발 환경 초기화 ✅

**완료 내용:**
- 디렉토리 구조 생성, requirements.txt, pyproject.toml, pytest.ini, .gitignore, README.md, main.py 골격

---

### Step 2 — SOLID 인터페이스 정의 ✅

**완료 내용:**
- core/interfaces.py (IAlignEngine, IInspectionEngine, IEvaluationEngine, IFeatureAnalyzer)
- core/models.py (ROIConfig, AlignResult, InspectionResult, EvaluationResult, FeatureAnalysisSummary, FeasibilityResult)
- core/exceptions.py (InputValidationError, RuntimeProcessingError, OutputValidationError, AIProviderError)

---

### Step 3 — 설정 및 상수 관리 모듈 ✅

**완료 내용:**
- config/constants.py, config/settings.py (save/load/validate/reset), config/paths.py

---

### Step 4 — 로깅 및 에러 핸들링 기반 ✅

**완료 내용:**
- core/logger.py (싱글톤 ArgosLogger, TimedRotatingFileHandler)
- core/exceptions.py 업데이트 (raise_with_log)
- core/error_handler.py (데코레이터, safe_execute)

---

### Step 5 — AI Provider Layer 기반 ✅

**완료 내용:**
- core/providers/base_provider.py (IAIProvider, retry/safe, ProviderStatus)
- core/providers/openai_provider.py, claude_provider.py, gemini_provider.py (raw requests)
- core/providers/provider_factory.py

---

### Step 6 — API Key 암호화 저장 모듈 ✅

**완료 내용:**
- core/key_manager.py (Fernet 암호화, 파일 권한 0o600, 보안 처리)

---

### Step 7 — 입력 검증 레이어 구현 ✅

**완료 내용:**
- core/validators.py (ImageValidator, ROIValidator, SampleValidator)
- tests/fixtures/sample_ok.png

---

### Step 8 — 이미지 데이터 모델 및 저장소 ✅

**완료 내용:**
- core/image_store.py (ImageType enum, ImageMeta, ImageStore)
- 썸네일 생성, CRUD, 요약 반환

---

## Phase 2: UI 기본 골격 (Step 9~16) ✅ 완료

---

### Step 9 — PyQt6 메인 윈도우 및 레이아웃 ✅

**완료 내용:**
- ui/style.py (DARK_THEME_QSS, 컬러 시스템)
- ui/main_window.py (MainWindow, 사이드바 220px, QStackedWidget)
- main.py 진입점

---

### Step 10 — 상단 툴바 및 API 입력 버튼 ✅

**완료 내용:**
- ui/components/status_indicator.py
- ui/dialogs/api_key_dialog.py (Provider 선택, 마스킹, QThread 연결 테스트)
- ui/components/toolbar.py

---

### Step 11 — 좌측 사이드바 네비게이션 ✅

**완료 내용:**
- ui/components/sidebar.py (ArgosSidebar, SidebarMenuItem, PageID enum)
- ui/pages/base_page.py (BasePage, PageHeader)
- 6개 페이지 플레이스홀더, QPropertyAnimation 접기/펼치기

---

### Step 12 — 대시보드 화면 ✅

**완료 내용:**
- ui/components/stat_card.py, workflow_indicator.py
- ui/pages/dashboard_page.py (StatCard 4종, AI 연결 상태, 워크플로우, 초기화)

---

### Step 13 — 이미지 업로드 화면 ✅

**완료 내용:**
- ui/components/drop_zone.py (Drag & Drop, 에러 플래시)
- ui/components/toast.py (슬라이드인/페이드아웃)
- ui/pages/upload_page.py (3구역 DropZone, NG 경고 배너)

---

### Step 14 — 이미지 썸네일 그리드 및 관리 ✅

**완료 내용:**
- ui/components/flow_layout.py (커스텀 QLayout)
- ui/components/thumbnail_card.py (타입 배지, 우클릭 메뉴)
- ui/components/thumbnail_grid.py, image_viewer_dialog.py
- tests/conftest.py (make_image_meta 픽스처)

---

### Step 15 — ROI 설정 화면 ✅

**완료 내용:**
- ui/components/roi_canvas.py (QPainter ROI 드래그, 줌, 좌표 변환)
- ui/components/roi_controls.py (스핀박스 양방향 동기화)
- ui/pages/roi_page.py (이미지 선택, 빈 상태, ROI 확정)

---

### Step 16 — 설정 화면 ✅

**완료 내용:**
- ui/components/section_card.py
- ui/pages/settings_page.py (슬라이더, w1+w2 동기화, dirty 상태, 저장/초기화)

---

## Phase 3: Feature 분석 엔진 (Step 17~22) ✅ 완료

---

### Step 17 — 이미지 로드 및 전처리 유틸리티 ✅

**완료 내용:**
- core/image_processor.py (ImageLoader, ImagePreprocessor 메서드 체이닝)

---

### Step 18 — 히스토그램 및 밝기 분석 ✅

**완료 내용:**
- core/analyzers/histogram_analyzer.py (HistogramAnalyzer, 분리도 계산, 전처리 추천)

---

### Step 19 — 노이즈 수준 분석 ✅

**완료 내용:**
- core/analyzers/noise_analyzer.py (Laplacian variance, MAD, SNR, 노이즈 레벨 분류)

---

### Step 20 — 에지 강도 분석 ✅

**완료 내용:**
- core/analyzers/edge_analyzer.py (Sobel, Canny, 방향성, Caliper 적합성)

---

### Step 21 — 형상 및 Blob 특성 분석 ✅

**완료 내용:**
- core/analyzers/shape_analyzer.py (Blob 검출, Hough Circle, 반복 패턴, 검사 방법 추천)

---

### Step 22 — Feature 분석 통합 및 AI 요약 ✅

**완료 내용:**
- core/analyzers/feature_analyzer.py (FullFeatureAnalysis, FeatureAnalyzer, AI 프롬프트 생성, JSON 저장)

---

## Phase 4: 검사 목적 입력 UI (Step 23~24)

---

### Step 23 — 검사 목적 데이터 모델 및 검증 ✅

**완료 내용:**
- core/models.py: InspectionPurpose 데이터클래스 추가
- core/validators.py: PurposeValidator 추가 (validate_not_empty, validate_description_length, validate_purpose)
- tests/test_step23_inspection_purpose.py: 5개 테스트 추가

**목표:** 검사 목적 입력 데이터 구조 및 검증 로직 구현

**구현 내용:**

- `core/models.py` 에 InspectionPurpose 데이터클래스 추가:
  - `inspection_type: str` — 검사 유형 (치수측정 / 결함검출 / 형상검사 / 위치정렬 / 기타)
  - `description: str` — 검사 상세 설명 (자유 텍스트)
  - `ok_ng_criteria: str` — OK/NG 판정 기준
  - `target_feature: str` — 검사 대상 특징 (홀 지름, 폭, 스크래치 등)
  - `measurement_unit: str` — 측정 단위 (mm, px, %)
  - `tolerance: str` — 허용 공차
  - `created_at: str` — ISO datetime

- `core/validators.py` 에 PurposeValidator 클래스 추가:
  - `validate_not_empty(purpose: InspectionPurpose) -> None`
    description과 inspection_type이 비어있으면 InputValidationError
  - `validate_description_length(description: str) -> None`
    10자 미만이면 InputValidationError ("검사 설명을 10자 이상 입력해주세요.")
  - `validate_purpose(purpose: InspectionPurpose) -> None`
    두 검증을 순서대로 실행

**테스트:**
- test_inspection_purpose_dataclass: 정상 생성 확인
- test_validate_empty_description_raises: 빈 description → InputValidationError
- test_validate_short_description_raises: 9자 → InputValidationError
- test_validate_valid_purpose: 정상 purpose → 예외 없음
- test_validate_empty_type_raises: 빈 inspection_type → InputValidationError

**직접 실행 확인:**
- Python REPL에서 InspectionPurpose 생성 및 검증 확인

**완료 조건:**
```
□ pytest 통과
□ REPL 동작 확인
□ git commit
```

---

### Step 24 — 검사 목적 입력 페이지 UI

**목표:** 검사 목적 입력 전용 페이지 완성 및 워크플로우 통합

**구현 내용:**

- `ui/pages/purpose_page.py` — PurposePage(BasePage):
  - page_id: PageID.PURPOSE
  - title: "검사 목적 입력"

  전체 레이아웃:
  ```
  ┌──────────────────────────────────────────────┐
  │ PageHeader("검사 목적 입력",                   │
  │   "검사 유형과 목적을 입력하면               │
  │    AI가 최적 알고리즘을 설계합니다.")         │
  ├──────────────────────────────────────────────┤
  │ SectionCard: 검사 유형                        │
  │  [ 치수 측정  ] [ 결함 검출  ] (토글 버튼)   │
  │  [ 형상 검사  ] [ 위치 정렬  ]               │
  │  [ 기타       ]                              │
  ├──────────────────────────────────────────────┤
  │ SectionCard: 검사 대상 및 기준                │
  │  검사 대상  [ 홀 지름              ] (입력)  │
  │  상세 설명  [ 멀티라인 텍스트 입력 ]         │
  │  판정 기준  [ OK/NG 기준 입력      ]         │
  │  측정 단위  [ mm ▼ ]  공차 [ ±0.05 ]        │
  ├──────────────────────────────────────────────┤
  │ SectionCard: 예시 (선택한 유형에 따라 변경)   │
  │  💡 예시: "PCB 솔더볼 직경 0.5mm ± 0.05mm   │
  │           범위 이탈 시 NG"                   │
  ├──────────────────────────────────────────────┤
  │ [ ✅ 목적 확정 ]  (primaryBtn)              │
  └──────────────────────────────────────────────┘
  ```

  검사 유형 토글 버튼:
  - 5개 버튼 (치수 측정 / 결함 검출 / 형상 검사 / 위치 정렬 / 기타)
  - 하나만 선택 가능 (exclusive toggle)
  - 선택 시 accent color 배경
  - 선택에 따라 예시 텍스트 자동 변경:
    - 치수 측정: "예) 홀 지름 0.5mm ± 0.05mm 범위 이탈 시 NG"
    - 결함 검출: "예) 표면 스크래치 길이 1mm 이상 시 NG"
    - 형상 검사: "예) 부품 외곽 형상이 기준과 5% 이상 차이 시 NG"
    - 위치 정렬: "예) 부품 중심 위치 오차 ±0.1mm 초과 시 NG"
    - 기타: "검사 목적을 직접 입력해주세요."

  ✅ 목적 확정 버튼:
  - PurposeValidator.validate_purpose() 실행
  - 실패 시 ToastMessage.show_error() 출력
  - 성공 시 InspectionPurpose 저장
  - ToastMessage.show_success("검사 목적이 확정되었습니다.")
  - purpose_confirmed 시그널 발행

  Methods:
  - get_confirmed_purpose() -> InspectionPurpose | None
  - load_purpose(purpose: InspectionPurpose) -> None
    이전에 저장된 목적 로드하여 필드 복원

  Signals:
  - purpose_confirmed = pyqtSignal(object)  # InspectionPurpose
  - navigate_requested = pyqtSignal(str)

- `ui/components/sidebar.py` 업데이트:
  PageID enum에 PURPOSE = "purpose" 추가
  메뉴 아이템 추가: "🎯  검사 목적" (ROI 설정 다음 위치)

- `ui/main_window.py` 업데이트:
  PurposePage 등록, purpose_confirmed 시그널 연결

**테스트:**
- test_purpose_page_created: PurposePage 생성 오류 없음
- test_type_buttons_exclusive: 하나 선택 시 나머지 비활성화
- test_example_text_changes_by_type: 유형 선택 → 예시 텍스트 변경
- test_confirm_empty_description_shows_error: 빈 입력 → 에러 토스트
- test_confirm_valid_emits_signal: 유효 입력 → purpose_confirmed 시그널
- test_get_confirmed_purpose_after_confirm: 확정 후 get_confirmed_purpose() 반환값 확인
- test_load_purpose_restores_fields: load_purpose() → 필드값 복원

**직접 실행 확인:**
1. `python main.py` 실행
2. 사이드바 "🎯 검사 목적" 클릭
3. 검사 유형 버튼 클릭 → 예시 텍스트 변경 확인
4. 상세 설명 입력 → 목적 확정 → 성공 토스트 확인
5. 빈 상태로 확정 → 에러 토스트 확인

**완료 조건:**
```
□ pytest 통과
□ 사이드바에 "🎯 검사 목적" 메뉴 추가 확인
□ 유형 토글 버튼 동작 확인
□ 예시 텍스트 자동 변경 확인
□ 목적 확정 → 성공 토스트 확인
□ 빈 입력 → 에러 토스트 확인
□ git commit
```

---

## Phase 5: 분석 실행 UI (Step 25~26)

---

### Step 25 — 분析 실행 화면 UI

**목표:** 분析 실행 페이지 완성 (검사 목적 포함 Pre-flight 체크)

**구현 내용:**

- `ui/components/progress_steps.py`:
  - AnalysisStep enum (FEATURE_ANALYSIS / ALIGN_DESIGN / INSPECTION_DESIGN / EVALUATION)
  - StepStatus enum (PENDING / RUNNING / DONE / FAILED / SKIPPED)
  - AnalysisStepWidget (48px, 상태 아이콘 + 라벨 + 소요시간)
  - AnalysisProgressPanel (4단계 패널, reset_all, get_overall_progress)
  - RUNNING 상태 QGraphicsOpacityEffect 펄싱 애니메이션 (0.4↔1.0, 800ms)

- `ui/components/log_viewer.py`:
  - LogViewer (레벨별 색상 로그, 자동 스크롤, 최대 500줄)
  - append_info / append_warning / append_error / clear_log

- `ui/workers/__init__.py` 생성

- `ui/workers/analysis_worker.py` — AnalysisWorker(QThread):
  - 시그널: step_started, step_finished, step_failed, log_message, analysis_complete, analysis_failed
  - cancel() 플래그 방식
  - FEATURE_ANALYSIS 단계: feature_analyzer.analyze_full() 실행
  - ALIGN_DESIGN / INSPECTION_DESIGN / EVALUATION: placeholder (Step 27~44에서 구현)

- `ui/pages/analysis_page.py` 전체 구현:
  - Pre-flight 체크: Align OK / Insp OK / Insp NG / ROI / **검사 목적** 5개 항목
  - 분析 시작 버튼: 5개 모두 ✅ 일 때만 활성화
  - 중단 / 결과 보기 버튼
  - set_roi_config(), set_inspection_purpose() 메서드
  - get_last_result() -> FullFeatureAnalysis | None

**테스트:**
- test_progress_panel_created / reset / one_done / all_done
- test_step_widget_status_change
- test_log_viewer_append / clear
- test_analysis_page_created
- test_start_button_disabled_no_images
- test_start_button_disabled_no_purpose: 목적 미설정 → 비활성화
- test_start_button_enabled_all_ready: 5개 조건 모두 충족 → 활성화
- test_cancel_button_disabled_initially
- test_result_button_disabled_initially

**직접 실행 확인:**
1. `python main.py` → 분析 실행 페이지 이동
2. Pre-flight 체크 5개 항목 확인 (검사 목적 미설정 시 ❌)
3. 검사 목적 입력 후 돌아오면 ✅ 로 변경 확인
4. 모두 ✅ → 분析 시작 활성화 확인
5. 분析 시작 → 단계별 진행 확인

**완료 조건:**
```
□ pytest 통과
□ Pre-flight 5개 항목 확인
□ 검사 목적 연동 확인
□ 분析 실행 → 단계 전환 시각 확인
□ git commit
```

---

### Step 26 — Feature 분析 결과 UI 표시

**목표:** Feature 분析 결과를 결과 뷰어에 표시

**구현 내용:**

- `ui/pages/result_page.py` 기본 골격:
  - 탭 구성: 요약 / Feature 분析 / Align 결과 / Inspection 결과 / Feasibility
  - 각 탭 플레이스홀더 (Step 45~49에서 완성)

- 결과 뷰어 내 "이미지 특성" 탭:
  - 히스토그램 통계 카드 (평균/표준편차/다이나믹레인지)
  - 노이즈 레벨 배지 (Low/Medium/High)
  - 에지 강도 / 밀도 수치
  - Blob 수량 / 원형 구조 유무
  - OK/NG 분리도 점수 및 시각화 바
  - AI 분析 요약 텍스트
  - 전처리 추천 목록

- `ui/main_window.py` 업데이트:
  - analysis_complete 시그널 → result_page에 결과 전달 연결

**테스트:**
- test_result_page_created
- test_feature_tab_renders_with_data
- test_ai_summary_displayed

**직접 실행 확인:**
1. 전체 워크플로우 진행 후 분析 완료
2. 결과 보기 버튼 클릭
3. Feature 분析 탭에서 각 수치 확인

**완료 조건:**
```
□ pytest 통과
□ Feature 분析 결과 탭 시각 확인
□ git commit
```

---

## Phase 6: Align 엔진 (Step 27~34)

---

### Step 27 — Pattern Matching Align 엔진

**목표:** 템플릿 매칭 기반 Align 엔진 구현

**구현 내용:**
- `core/align/pattern_align.py` — IAlignEngine 구현
- TM_CCOEFF_NORMED 정규화 상관 매칭
- 매칭 점수 계산 및 임계값 판정
- 4섹션 설계 문서 자동 생성

**테스트:**
- 알려진 이미지 쌍 → 정확한 위치 반환
- 매칭 불가 → 실패 결과 반환

**직접 실행 확인:**
- 매칭 결과 오버레이 이미지 저장 후 눈으로 확인

**완료 조건:**
```
□ pytest 통과
□ 결과 이미지 직접 확인
□ git commit
```

---

### Step 28 — Caliper Align 엔진

**목표:** Caliper 기반 Align 엔진 구현 (4섹션 설계 출력 포함)

**구현 내용:**
- `core/align/caliper_align.py` — IAlignEngine 구현
- Projection Length / Search Length / Condition / Threshold / Polarity 파라미터
- Inward / Outward / Leftward / Rightward 방향 지원
- 4섹션 설계 문서 자동 생성

**테스트:**
- 에지 검출 정상 확인
- 4섹션 출력 구조 검증

**직접 실행 확인:**
- Caliper 결과 오버레이 이미지 및 4섹션 출력 텍스트 확인

**완료 조건:**
```
□ pytest 통과
□ 결과 이미지 + 4섹션 텍스트 직접 확인
□ git commit
```

---

### Step 29 — Feature-based / Contour / Blob Align 엔진

**목표:** Fallback 3단계용 추가 Align 엔진 구현

**구현 내용:**
- `core/align/feature_align.py` — ORB / SIFT 기반
- `core/align/contour_align.py` — 윤곽선 매칭
- `core/align/blob_align.py` — Blob 중심점

**테스트:**
- 각 엔진 정상 동작 및 실패 조건 확인

**직접 실행 확인:**
- 각 엔진 결과 이미지 저장 후 눈으로 확인

**완료 조건:**
```
□ pytest 통과 (3종)
□ 각 결과 이미지 직접 확인
□ git commit
```

---

### Step 30 — Align Fallback 체인 통합

**목표:** Pattern → Caliper → Feature/Contour/Blob → 실패 체인 완성

**구현 내용:**
- `core/align/align_engine.py` — Fallback 체인 오케스트레이터
- AI 판단: 3단계에서 시도 순서 결정
- 실패 원인 로그 기록
- InspectionPurpose를 Align 전략 결정에 활용

**테스트:**
- 각 단계 실패 시 체인 전환 확인
- 최종 실패 결과 반환 확인

**직접 실행 확인:**
- Fallback 체인 단계 전환 로그 직접 확인

**완료 조건:**
```
□ pytest 통과
□ Fallback 로그 직접 확인
□ git commit
```

---

### Step 31 — Align 결과 UI 표시

**목표:** Align 결과를 결과 뷰어에 표시

**구현 내용:**
- 결과 뷰어 "Align 결과" 탭 구현
- 전략명 / 매칭 점수 / 기준점 좌표 표시
- 4섹션 파라미터 테이블
- Align 오버레이 이미지
- 라이브러리 대응 명칭 테이블

**테스트:**
- Align 결과 데이터 → UI 렌더링 확인

**직접 실행 확인:**
- Align 결과 탭 출현 및 내용 확인

**완료 조건:**
```
□ pytest 통과
□ Align 결과 탭 시각 확인
□ git commit
```

---

### Step 32 — ROI 적용 및 전처리 파이프라인

**목표:** ROI 크롭 + 전처리 파이프라인 완성

**구현 내용:**
- `core/preprocessor.py`
- Align 결과 적용 후 ROI 크롭
- 노이즈 분析 결과 기반 자동 필터 선택
- InspectionPurpose 기반 전처리 조정
- 전처리 파이프라인 직렬화 (설계 문서 출력)

**테스트:**
- ROI 크롭 좌표 정확성 확인
- 파이프라인 직렬화 확인

**직접 실행 확인:**
- 전처리 전/후 이미지 파일 저장 후 눈으로 확인

**완료 조건:**
```
□ pytest 통과
□ 전처리 전/후 이미지 직접 확인
□ git commit
```

---

### Step 33 — Align 통합 테스트

**목표:** Align 전체 파이프라인 E2E 검증

**구현 내용:**
- Align 전체 흐름 통합 테스트
- 여러 이미지 타입에 대한 회귀 테스트
- InspectionPurpose 연동 테스트

**테스트:**
- E2E 테스트 3종 이상

**직접 실행 확인:**
- 실제 이미지로 전체 Align 흐름 UI에서 실행

**완료 조건:**
```
□ E2E 테스트 통과
□ 실제 이미지 Align 흐름 직접 확인
□ git commit
```

---

### Step 34 — AnalysisWorker Align 단계 연동

**목표:** AnalysisWorker의 ALIGN_DESIGN 단계를 실제 Align 엔진과 연결

**구현 내용:**
- `ui/workers/analysis_worker.py` 업데이트
- ALIGN_DESIGN 단계: AlignEngine.run() 실행
- InspectionPurpose를 Align 전략에 전달
- 단계별 시그널 정상 발행

**테스트:**
- Worker ALIGN_DESIGN 단계 실행 확인
- 시그널 정상 발행 확인

**직접 실행 확인:**
- 분析 실행 → ALIGN_DESIGN 단계 ✓ 확인

**완료 조건:**
```
□ pytest 통과
□ UI에서 Align 단계 완료 확인
□ git commit
```

---

## Phase 7: Inspection 엔진 (Step 35~44)

---

### Step 35 — Blob 기반 Inspection 엔진

**목표:** Blob 분析 기반 Inspection 엔진 구현

**구현 내용:**
- `core/inspection/blob_inspector.py` — IInspectionEngine 구현
- 면적 / 원형도 / 그레이 레벨 / 연결성 파라미터
- Polarity (Darker / Brighter than background)
- InspectionPurpose의 ok_ng_criteria를 파라미터 설정에 반영
- 4섹션 설계 문서 자동 생성

**테스트:**
- OK 이미지 → Blob 미검출 / NG → 검출 확인

**직접 실행 확인:**
- 검출 결과 오버레이 이미지 직접 확인

**완료 조건:**
```
□ pytest 통과
□ 오버레이 이미지 직접 확인
□ git commit
```

---

### Step 36 — Circular Caliper Inspection 엔진

**목표:** 원형 Caliper 배치 기반 검사 엔진 구현

**구현 내용:**
- `core/inspection/circular_caliper_inspector.py`
- 배치 수 / 각도 간격 / 시작 각도 / 탐색 반경
- Inward / Outward 방향
- LSQ Circle Fit, 이상치 처리 (3σ)
- 유효 Caliper < 8개 시 신뢰도 경고
- 4섹션 설계 문서 자동 생성

**테스트:**
- 원형 이미지 지름 정상 측정 / 이상치 처리 확인

**직접 실행 확인:**
- 원형 검사 결과 오버레이 직접 확인

**완료 조건:**
```
□ pytest 통과
□ 결과 이미지 직접 확인
□ git commit
```

---

### Step 37 — Linear Caliper Inspection 엔진

**목표:** 선형 Caliper 배치 기반 검사 엔진 구현

**구현 내용:**
- `core/inspection/linear_caliper_inspector.py`
- 좌우/상하 배치 수 / 간격 / 방향
- Leftward / Rightward / Upward / Downward
- 평균 에지선 계산, 폭/직진도
- 4섹션 설계 문서 자동 생성

**테스트:**
- 직선 에지 이미지 폭 정상 측정 확인

**직접 실행 확인:**
- 결과 오버레이 이미지 직접 확인

**완료 조건:**
```
□ pytest 통과
□ 결과 이미지 직접 확인
□ git commit
```

---

### Step 38 — Pattern 기반 Inspection 엔진

**목표:** 패턴 매칭 기반 결함 검사 엔진 구현

**구현 내용:**
- `core/inspection/pattern_inspector.py`
- OK 기준 이미지 대비 차분 검사
- 차분 임계값 / 최소 면적 파라미터
- 4섹션 설계 문서 자동 생성

**테스트:**
- OK 대비 NG 차분 정상 검출 확인

**직접 실행 확인:**
- 차분 결과 이미지 직접 확인

**완료 조건:**
```
□ pytest 통과
□ 차분 결과 이미지 직접 확인
□ git commit
```

---

### Step 39 — Dynamic Candidate 생성기

**목표:** 이미지 특성 + 검사 목적 기반 Candidate 자동 생성

**구현 내용:**
- `core/inspection/candidate_generator.py`
- Feature 분析 결과 기반 후보 선택
- **InspectionPurpose를 AI 프롬프트에 포함** → 목적에 맞는 후보 생성
- AI Provider 호출 → 추가 후보 제안
- Candidate 우선순위 정렬

**테스트:**
- Feature 분析 결과 + InspectionPurpose 입력 → Candidate 목록 생성 확인
- AI 호출 실패 시 로컬 후보만으로 진행 확인

**직접 실행 확인:**
- InspectionPurpose 포함된 Candidate 목록 출력 확인

**완료 조건:**
```
□ pytest 통과
□ Candidate 목록 직접 확인
□ git commit
```

---

### Step 40 — 평가 엔진 (Evaluation)

**목표:** OK/NG 분류 품질 스코어 계산 엔진 완성

**구현 내용:**
- `core/evaluation/evaluator.py` — IEvaluationEngine 구현
- score = (OK 통과율 × w1) + (NG 검출율 × w2)
- 분리 마진 계산
- FP / FN 분류 및 목록 추출
- "경계선 위험 구간" 경고

**테스트:**
- 스코어 정확성 / 마진 < 15 시 경고 확인

**직접 실행 확인:**
- 스코어 계산 결과 수치 확인

**완료 조건:**
```
□ pytest 통과
□ 스코어 수치 직접 확인
□ git commit
```

---

### Step 41 — 최적화 루프 및 Best Candidate 선택

**목표:** Candidate 평가 → Best 선택 루프 완성

**구현 내용:**
- `core/inspection/optimizer.py`
- 모든 Candidate Evaluation 실행
- 스코어 기준 정렬 → Best 선택
- 최적화 루프 로그

**테스트:**
- Candidate 3종 → Best 정확히 선택 확인

**직접 실행 확인:**
- 최적화 루프 로그 출력 확인

**완료 조건:**
```
□ pytest 통과
□ Best 선택 로그 직접 확인
□ git commit
```

---

### Step 42 — Failure 분析

**목표:** 실패 케이스 分析 및 원인 제공

**구현 내용:**
- `core/evaluation/failure_analyzer.py`
- FP / FN 이미지 목록 추출
- AI 호출 기반 원인 분析
- 개선 방향 텍스트 생성
- 실패 케이스 시각화

**테스트:**
- FP / FN 목록 추출 / 원인 텍스트 생성 확인

**직접 실행 확인:**
- 실패 이미지 오버레이 결과 직접 확인

**완료 조건:**
```
□ pytest 통과
□ 실패 이미지 오버레이 직접 확인
□ git commit
```

---

### Step 43 — Feasibility Analysis 및 기술 수준 판단

**목표:** Rule-based 한계 판정 및 EL/DL 추천 완성

**구현 내용:**
- `core/evaluation/feasibility_analyzer.py`
- best_score < threshold 판정
- AI 호출: 이미지 상태 + 검사 난이도 + **InspectionPurpose** 분析 → EL/DL 결정
- 판단 근거 텍스트 생성
- 모델 추천 (EL: MobileNet / DL: CNN / Anomaly)

**테스트:**
- 스코어 < threshold → 추천 트리거 / AI 결과 파싱 확인

**직접 실행 확인:**
- EL/DL 추천 결과 텍스트 직접 확인

**완료 조건:**
```
□ pytest 통과
□ 추천 결과 텍스트 직접 확인
□ git commit
```

---

### Step 44 — Inspection 통합 테스트 및 AnalysisWorker 연동

**목표:** Inspection 전체 파이프라인 E2E 검증 + Worker 연동

**구현 내용:**
- Candidate 생성 → 평가 → 최적화 → Failure → Feasibility E2E 테스트
- `ui/workers/analysis_worker.py` INSPECTION_DESIGN / EVALUATION 단계 연결
- NG 0장 시나리오 → 알람 트리거 확인

**테스트:**
- E2E 테스트 3종 이상

**직접 실행 확인:**
- 실제 이미지로 전체 Inspection 흐름 UI에서 실행

**완료 조건:**
```
□ E2E 테스트 통과
□ 전체 Inspection UI 직접 확인
□ git commit
```

---

## Phase 8: 결과 뷰어 및 출력 (Step 45~49)

---

### Step 45 — 결과 뷰어 전체 완성

**목표:** 결과 뷰어 탭 전체 구현

**구현 내용:**
- `ui/pages/result_page.py` 전체 완성
- 탭: 요약 / Feature 분析 / Align 결과 / Inspection 결과 / Feasibility
- 요약 탭: 검사 목적 / 사용 전략 / 최종 스코어 / 권장 접근법

**테스트:**
- 탭별 렌더링 정상 확인

**직접 실행 확인:**
- 탭 전환 및 내용 직접 확인

**완료 조건:**
```
□ pytest 통과
□ 탭 전환 직접 확인
□ git commit
```

---

### Step 46 — Inspection 결과 카드 및 파라미터 테이블

**목표:** Inspection 알고리즘 결과 상세 표시

**구현 내용:**
- Best Candidate 알고리즘명 / 스코어 / 분리 마진
- 4섹션 파라미터 테이블
- 라이브러리 대응 명칭 테이블 (Keyence / Cognex / Halcon / MIL)
- 결과 이미지 오버레이 뷰어 (확대/축소)
- Candidate 비교 테이블

**테스트:**
- 결과 카드 렌더링 확인

**직접 실행 확인:**
- 파라미터 테이블 및 라이브러리 대응 명칭 직접 확인

**완료 조건:**
```
□ pytest 통과
□ 결과 카드 전체 직접 확인
□ git commit
```

---

### Step 47 — Failure 케이스 뷰어 및 Feasibility 표시

**목표:** 실패 케이스 + Feasibility 결과 표시

**구현 내용:**
- FP / FN 이미지 썸네일 그리드
- 이미지 클릭 → 원인 분析 팝업
- Rule-based / EL / DL 상태 배지
- AI 판단 근거 텍스트
- 추천 모델 정보

**테스트:**
- 실패 케이스 그리드 / 배지 렌더링 확인

**직접 실행 확인:**
- 실패 이미지 클릭 → 팝업 / Feasibility 배지 직접 확인

**완료 조건:**
```
□ pytest 통과
□ 팝업 / 배지 직접 확인
□ git commit
```

---

### Step 48 — 결과 내보내기 (Export)

**목표:** 분析 결과 파일 저장 기능 완성

**구현 내용:**
- 결과 JSON 저장 (전체 파라미터 + InspectionPurpose 포함)
- PDF 리포트 생성 (reportlab)
- 결과 이미지 일괄 저장
- 내보내기 경로 선택 다이얼로그

**테스트:**
- JSON 정합성 / PDF 생성 확인

**직접 실행 확인:**
- JSON / PDF 파일 저장 및 내용 직접 확인

**완료 조건:**
```
□ pytest 통과
□ JSON / PDF 직접 확인
□ git commit
```

---

### Step 49 — 대시보드 및 워크플로우 최종 연동

**목표:** 대시보드에 검사 목적 현황 반영 및 전체 워크플로우 연동

**구현 내용:**
- 대시보드 StatCard에 "검사 목적" 상태 카드 추가
- 워크플로우 인디케이터 5단계로 업데이트:
  이미지 업로드 → ROI 설정 → 검사 목적 → 분析 실행 → 결과 확인
- MainWindow에서 모든 페이지 간 데이터 전달 최종 확인
- InspectionPurpose가 전체 파이프라인에 올바르게 전달되는지 검증

**테스트:**
- 대시보드 워크플로우 5단계 확인
- 데이터 전달 E2E 확인

**직접 실행 확인:**
- 대시보드 워크플로우 5단계 시각 확인
- 처음부터 끝까지 전체 흐름 1회 실행

**완료 조건:**
```
□ pytest 통과
□ 워크플로우 5단계 직접 확인
□ 전체 흐름 1회 완주 직접 확인
□ git commit
```

---

## Phase 9: 통합 완성 및 운영 품질 (Step 50~51)

---

### Step 50 — UI 품질 개선, E2E 테스트 및 배포 패키징

**목표:** 운영 수준 완성도 확보 및 패키징

**구현 내용:**
- 전체 화면 폰트 / 색상 / 간격 일관성 검토
- 로딩 스피너 / 빈 상태 메시지 전체 적용
- 툴팁 추가 (파라미터 설명)
- 전체 워크플로우 E2E 자동화 테스트
- PyInstaller 스펙 파일 및 플랫폼별 빌드 스크립트
- 아이콘 / 스플래시 이미지 적용

**테스트:**
- E2E 시나리오 4종 이상
- UI 렌더링 오류 없음

**직접 실행 확인:**
- 실행 파일 생성 후 Python 없는 환경에서 실행 확인

**완료 조건:**
```
□ E2E 테스트 통과
□ 실행 파일 직접 확인
□ git commit + 버전 태그
```

---

### Step 51 — 최종 검수 및 문서화

**목표:** 운영 릴리스 준비 완료

**구현 내용:**
- 전체 회귀 테스트 최종 실행
- README.md 최종 업데이트 (설치 방법 / 사용법 / 스크린샷)
- CHANGELOG.md 작성
- 알려진 이슈 정리
- 향후 로드맵 (EL/DL 모듈 연동)

**테스트:**
- 전체 pytest 스위트 최종 통과

**직접 실행 확인:**
- README 따라 설치 → 실제 비전 이미지로 분析 사이클 1회 완주

**완료 조건:**
```
□ 전체 pytest 통과
□ 분析 완주 직접 확인
□ CHANGELOG 작성
□ 최종 git tag 및 release
```

---

## 📋 15. 최종 출력 형식

```
═══════════════════════════════════════════════
  AI Vision Engineer Agent — 분析 결과
═══════════════════════════════════════════════

[검사 목적]
  유형 / 대상 / 판정 기준 / 허용 공차

[Align Strategy]
  방식 / 배치 구조 / 파라미터 / 선택 근거

[ROI]
  좌표 / 크기

[Preprocessing]
  전처리 단계 및 파라미터

[Inspection Algorithm]
  배치 구조 (Caliper 수 / 간격 / 방향 포함)
  개별 파라미터 (4섹션 구조)
  라이브러리 대응 명칭 (Keyence / Cognex / Halcon / MIL)

[Parameters]
  전체 설정값 요약

[Accuracy]
  OK 통과율 / NG 검출율 / 분리 마진

[Failure Cases]
  FP / FN 이미지 목록 + 원인 + 개선 방향

─────────────────────────────────────────────
[Feasibility Analysis]
  Rule-based 충분 여부 판정

[Recommended Approach]
  Rule-based 유지 또는 EL / DL 추천
  추천 근거 (AI 판단 포함)
═══════════════════════════════════════════════
```

---

## 🔥 16. 최종 결론

이 시스템은:

- ✅ 비전 엔지니어 역할 수행
- ✅ **검사 목적 입력 기반 알고리즘 설계** (치수측정 / 결함검출 / 형상검사 / 위치정렬)
- ✅ 라이브러리 독립적 알고리즘 설계 출력 (Keyence / Cognex / Halcon / MIL)
- ✅ Caliper 배치 구조 전체 설계 (개수 / 각도 / 방향 / 4섹션)
- ✅ 에러 처리 3레이어 구조
- ✅ 데이터 부족 시 명확한 알람 체계
- ✅ 분류 품질 기준 SLA 정의
- ✅ 기술 수준 자동 판단 (스코어 기반 → EL/DL 추천)
- ✅ 로컬 전용 실행 (Windows / macOS / Linux)
- ✅ 운영 수준 모던 UI (다크 테마, 사이드바, API 모달)
- ✅ API Key UI 입력 + 로컬 암호화 저장
- ✅ **51 Step 단계별 TDD + Human Review + 직접 실행 검증**
- ✅ 유지보수 가능한 SOLID 구조

---

> **"AI가 코드를 만들고, 테스트가 검증하고, 사람이 직접 눈으로 확인하며, 시스템이 비전 엔지니어 역할을 수행하는 자동화 플랫폼"**
