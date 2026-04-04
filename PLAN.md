# 🧠 AI Vision Engineer Agent 개발 계획서 (v5)

---

## 🎯 1. 프로젝트 정의

### 목표

사용자가:

- Align 이미지 (OK)
- Inspection OK 이미지
- Inspection NG 이미지
- ROI 직접 지정
- 검사 목적 입력

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
| 분석 실행 | 진행 상태 바, 단계별 로그 실시간 출력 |
| 결과 뷰어 | 알고리즘 결과 카드, 파라미터 테이블, 시각화 오버레이 |
| 설정 | AI Provider 선택, 임계값 조정, FP/FN 가중치 |

### 4.3 AI API 입력 방식

- 상단 툴바 우측 **"🔑 API 입력"** 버튼
- 클릭 시 모달 다이얼로그 출현
- Provider 선택 (OpenAI / Claude / Gemini) → API Key 입력 → 연결 테스트 버튼
- 입력된 키는 로컬 암호화 저장 (keyring 또는 AES 암호화)
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
생성형 AI — 설계 해석 + Claude Code 프롬프트 생성 (PCRO 포맷)
 ↓
Claude Code — 실제 코드 + 테스트 코드 구현
 ↓
TDD 검증 (pytest)
 ↓
Human Review + 직접 UI 실행 확인
 ↓
git commit
```

---

## ⚠️ 7. 에러 처리 전략

### Layer 1: 입력 검증 (Input Validation)

| 검증 항목 | 기준 | 처리 |
|----------|------|------|
| 이미지 포맷 | BMP, PNG, TIFF, JPEG | 즉시 오류 반환 |
| 해상도 | 64×64 이하 거부 | 오류 메시지 |
| 파일 손상 | 열기 실패 | 오류 메시지 |
| ROI 범위 | 경계 초과 / 크기 0 / 전체 대비 1% 미만 | 오류 메시지 |
| NG 이미지 0장 | Inspection 설계 진입 불가 | 알람 모달 출력 |

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

## 📊 8. 성능 목표치 (SLA)

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

## 🔧 9. Align 설계

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

## 🔍 10. Inspection 설계

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

## 📤 11. 출력 형식 (라이브러리 독립적)

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

## 🔐 12. AI 연결 구조

- Provider 추상화 레이어 (OpenAI / Claude / Gemini 교체 가능)
- API Key: UI 상단 "🔑 API 입력" 버튼 → 모달 입력 → 로컬 암호화 저장
- 모델 버전 고정 (재현성 보장)
- AI 호출 시점: Feature Analysis / Candidate 생성 / Feasibility 판단 / Fallback 전략 결정에만 사용
- 이미지 원본 외부 전송 금지 (텍스트 분석 결과만 API 전달)

---

## 🚀 13. 개발 단계 (50 Steps)

### Step 표기 규칙

각 Step은 아래 형식으로 기술한다.

```
### Step N — [제목]
목표: 이 Step에서 완성해야 하는 것
구현 내용: 실제 구현 항목
테스트: pytest 테스트 항목
직접 실행 확인: UI에서 눈으로 확인할 내용
완료 조건: 체크리스트
```

---

## Phase 1: 프로젝트 기반 구축 (Step 1~8)

---

### Step 1 — 프로젝트 구조 및 개발 환경 초기화

**목표:** 전체 프로젝트 골격 생성, 개발 환경 세팅 완료

**구현 내용:**
- 디렉토리 구조 생성 (`core/`, `ui/`, `tests/`, `assets/`, `config/`)
- `pyproject.toml` / `requirements.txt` 작성
- pytest 설정 (`pytest.ini`)
- `.gitignore`, `README.md` 초안 작성
- Python 가상환경 구성 확인

**테스트:**
- `pytest --collect-only` 실행 시 오류 없음 확인
- import 경로 정상 동작 확인

**직접 실행 확인:**
- `python -m pytest` 실행 → 0 errors
- 디렉토리 구조 눈으로 확인

**완료 조건:**
```
□ pytest 수집 오류 없음
□ 디렉토리 구조 확인
□ git init + 첫 commit 완료
```

---

### Step 2 — SOLID 인터페이스 정의

**목표:** 핵심 엔진 추상 인터페이스 정의

**구현 내용:**
- `IAlignEngine` 추상 클래스
- `IInspectionEngine` 추상 클래스
- `IEvaluationEngine` 추상 클래스
- `IFeatureAnalyzer` 추상 클래스
- 공통 데이터 클래스 (`AlignResult`, `InspectionResult`, `EvaluationResult`)

**테스트:**
- 각 인터페이스 인스턴스 생성 불가 (추상 클래스) 확인
- 데이터 클래스 필드 타입 검증

**직접 실행 확인:**
- Python REPL에서 인터페이스 import 후 구조 확인

**완료 조건:**
```
□ 추상 클래스 4개 정의 완료
□ 데이터 클래스 정의 완료
□ pytest 통과
□ Human Review: 인터페이스 설계 확인
□ git commit
```

---

### Step 3 — 설정 및 상수 관리 모듈

**목표:** 전역 설정, 상수, 경로 관리 체계 구축

**구현 내용:**
- `config/settings.py` — 기본 임계값, SLA 기준, 지원 포맷 등
- `config/constants.py` — 상수 정의
- 설정 로드/저장 유틸리티 (JSON 기반)
- 설정 검증 로직

**테스트:**
- 기본값 로드 정상 확인
- 잘못된 설정값 입력 시 예외 발생 확인

**직접 실행 확인:**
- 설정 파일 생성 후 값 확인

**완료 조건:**
```
□ pytest 통과
□ 설정 파일 생성/로드 확인
□ git commit
```

---

### Step 4 — 로깅 및 에러 핸들링 기반

**목표:** 전체 시스템 로깅 체계 구축

**구현 내용:**
- `core/logger.py` — 구조화 로깅 (파일 + 콘솔)
- 에러 레이어 3종 Exception 클래스 정의
  - `InputValidationError`
  - `RuntimeProcessingError`
  - `OutputValidationError`
- 에러 발생 시 로그 자동 기록

**테스트:**
- 각 Exception 발생 및 로그 기록 확인
- 로그 파일 생성 확인

**직접 실행 확인:**
- 의도적 에러 발생 → 로그 파일 내용 눈으로 확인

**완료 조건:**
```
□ pytest 통과
□ 로그 파일 생성 확인
□ git commit
```

---

### Step 5 — AI Provider Layer 기반

**목표:** AI API 추상화 레이어 구축

**구현 내용:**
- `IAIProvider` 추상 인터페이스
- `OpenAIProvider` 구현체 (stub)
- `ClaudeProvider` 구현체 (stub)
- `GeminiProvider` 구현체 (stub)
- Provider 팩토리 패턴
- 타임아웃 / retry 로직 (30초, 2회)

**테스트:**
- Provider 팩토리 정상 생성 확인
- Stub 응답 정상 반환 확인
- 타임아웃 시뮬레이션 → graceful degradation 확인

**직접 실행 확인:**
- Python REPL에서 Provider 생성 → stub 호출 확인

**완료 조건:**
```
□ pytest 통과
□ Provider 팩토리 동작 확인
□ git commit
```

---

### Step 6 — API Key 암호화 저장 모듈

**목표:** API Key 안전한 로컬 저장/로드 구현

**구현 내용:**
- `core/key_manager.py`
- AES 암호화 기반 저장 (cryptography 라이브러리)
- OS keyring 연동 (keyring 라이브러리)
- 저장 / 로드 / 삭제 / 존재 여부 확인 API
- API Key 평문 로그 출력 방지 처리

**테스트:**
- 저장 후 로드 값 일치 확인
- 로그에 키 값 미출력 확인
- 잘못된 키 포맷 입력 시 예외 확인

**직접 실행 확인:**
- 키 저장 후 파일 확인 (암호화 여부)
- 로드 후 복호화 정상 확인

**완료 조건:**
```
□ pytest 통과
□ 암호화 파일 생성 확인
□ 복호화 정상 확인
□ git commit
```

---

### Step 7 — 입력 검증 레이어 구현

**목표:** 이미지 / ROI 입력 검증 로직 완성

**구현 내용:**
- `core/validators.py`
- 이미지 포맷 검증 (BMP, PNG, TIFF, JPEG)
- 해상도 검증 (64×64 이하 거부)
- 파일 손상 검증
- ROI 유효성 검증 (경계 초과 / 크기 0 / 1% 미만)
- NG 이미지 수량 검증

**테스트:**
- 지원 포맷 정상 통과
- 비지원 포맷 → `InputValidationError`
- 손상 파일 → 에러
- ROI 경계 초과 → 에러
- NG 0장 → 알람 트리거 확인

**직접 실행 확인:**
- 의도적으로 잘못된 이미지/ROI 입력 → 에러 메시지 확인

**완료 조건:**
```
□ pytest 통과
□ 검증 시나리오 6종 직접 확인
□ git commit
```

---

### Step 8 — 이미지 데이터 모델 및 저장소

**목표:** 이미지 세션 데이터 관리 구조 완성

**구현 내용:**
- `core/image_store.py`
- 이미지 메타데이터 모델 (`ImageMeta`: 경로, 타입, 크기, 태그)
- 세션 단위 이미지 저장소 (Align OK / Inspection OK / Inspection NG 분류)
- 이미지 추가 / 삭제 / 조회 / 전체 초기화 API
- 썸네일 생성 유틸리티

**테스트:**
- 이미지 추가/삭제/조회 정상 동작
- 분류별 카운트 정상 반환
- 썸네일 생성 확인

**직접 실행 확인:**
- 이미지 추가 후 저장소 상태 출력 확인

**완료 조건:**
```
□ pytest 통과
□ 저장소 CRUD 동작 확인
□ git commit
```

---

## Phase 2: UI 기본 골격 (Step 9~16)

---

### Step 9 — PyQt6 메인 윈도우 및 레이아웃

**목표:** 앱 실행 가능한 메인 윈도우 골격 완성

**구현 내용:**
- `ui/main_window.py` — 메인 윈도우 클래스
- 전체 레이아웃: 좌측 사이드바 + 중앙 콘텐츠 영역 + 상단 툴바
- 다크 테마 QSS 스타일시트 적용 (배경 `#1A1A2E`, 카드 `#16213E`)
- 앱 진입점 `main.py`
- 최소 창 크기 설정 (1280×800)

**테스트:**
- 윈도우 생성 후 종료 정상 확인 (headless)
- 레이아웃 구성요소 존재 확인

**직접 실행 확인:**
- `python main.py` 실행 → 윈도우 출현 및 다크 테마 확인

**완료 조건:**
```
□ pytest 통과
□ 앱 실행 후 창 출현 직접 확인
□ 다크 테마 시각 확인
□ git commit
```

---

### Step 10 — 상단 툴바 및 API 입력 버튼

**목표:** 상단 툴바 완성, API 입력 모달 동작

**구현 내용:**
- 상단 툴바: 로고 / 프로젝트명 / AI 연결 상태 표시 / "🔑 API 입력" 버튼
- `ui/dialogs/api_key_dialog.py` — API Key 입력 모달
  - Provider 선택 드롭다운 (OpenAI / Claude / Gemini)
  - API Key 입력 필드 (비밀번호 마스킹)
  - "연결 테스트" 버튼
  - 연결 성공/실패 결과 표시
  - 저장/취소 버튼
- 연결 상태 실시간 반영 (`● 연결됨 (Claude)` / `● 미연결`)

**테스트:**
- 모달 열기/닫기 동작
- Key 저장 후 상태 표시 변경 확인
- 빈 Key 저장 시도 → 검증 에러

**직접 실행 확인:**
- "🔑 API 입력" 클릭 → 모달 출현 확인
- Key 입력 → 저장 → 상태 표시 변경 직접 확인

**완료 조건:**
```
□ pytest 통과
□ API 모달 동작 직접 확인
□ 연결 상태 표시 변경 확인
□ git commit
```

---

### Step 11 — 좌측 사이드바 네비게이션

**목표:** 워크플로우 단계 네비게이션 완성

**구현 내용:**
- 사이드바 메뉴: 대시보드 / 이미지 업로드 / ROI 설정 / 분석 실행 / 결과 뷰어 / 설정
- 활성 메뉴 하이라이트 (주조색 `#1E88E5`)
- 메뉴 클릭 시 중앙 콘텐츠 전환 (스택 위젯)
- 사이드바 접기/펼치기 토글 버튼

**테스트:**
- 메뉴 클릭 시 콘텐츠 전환 확인
- 접기/펼치기 동작 확인

**직접 실행 확인:**
- 각 메뉴 클릭 → 화면 전환 직접 확인

**완료 조건:**
```
□ pytest 통과
□ 메뉴 전환 6개 모두 직접 확인
□ git commit
```

---

### Step 12 — 대시보드 화면

**목표:** 프로젝트 현황 대시보드 완성

**구현 내용:**
- 현재 세션 이미지 현황 카드 (Align OK / Inspection OK / NG 수량)
- AI 연결 상태 카드
- 최근 분석 결과 요약 카드 (미분석 시 안내 메시지)
- "새 프로젝트 시작" 버튼 (세션 초기화)
- 단계별 진행 상태 인디케이터

**테스트:**
- 세션 데이터 변경 시 카드 수량 업데이트 확인

**직접 실행 확인:**
- 대시보드 화면 출현 및 카드 레이아웃 확인

**완료 조건:**
```
□ pytest 통과
□ 대시보드 시각 확인
□ git commit
```

---

### Step 13 — 이미지 업로드 화면 (기본)

**목표:** 이미지 업로드 UI 기본 동작 완성

**구현 내용:**
- `ui/pages/upload_page.py`
- Drag & Drop 업로드 영역 3구역 (Align OK / Inspection OK / Inspection NG)
- 파일 선택 버튼 병행
- 업로드 즉시 입력 검증 실행
- 검증 실패 시 에러 토스트 메시지

**테스트:**
- 지원 포맷 업로드 정상 처리
- 비지원 포맷 업로드 → 에러 메시지 출력

**직접 실행 확인:**
- 이미지 파일 드래그 앤 드롭 → 각 구역에 업로드 확인
- 잘못된 파일 업로드 → 에러 메시지 확인

**완료 조건:**
```
□ pytest 통과
□ Drag & Drop 동작 직접 확인
□ 에러 메시지 출현 직접 확인
□ git commit
```

---

### Step 14 — 이미지 썸네일 그리드 및 관리

**목표:** 업로드된 이미지 썸네일 표시 및 관리 완성

**구현 내용:**
- 이미지 업로드 후 썸네일 그리드 자동 갱신
- 썸네일 위에 분류 태그 표시 (OK / NG / Align)
- 썸네일 우클릭 → 삭제 컨텍스트 메뉴
- 이미지 수량 실시간 카운터 표시
- NG 0장 상태 시 경고 배너 표시

**테스트:**
- 이미지 추가/삭제 후 썸네일 갱신 확인
- NG 0장 경고 배너 조건 트리거 확인

**직접 실행 확인:**
- 이미지 여러 장 업로드 → 썸네일 그리드 출현 확인
- 삭제 후 그리드 갱신 확인

**완료 조건:**
```
□ pytest 통과
□ 썸네일 그리드 동작 직접 확인
□ git commit
```

---

### Step 15 — ROI 설정 화면 (마우스 드래그)

**목표:** 이미지 위에서 마우스로 ROI 직접 지정 완성

**구현 내용:**
- `ui/pages/roi_page.py`
- 선택된 이미지 표시 (스크롤 줌 지원)
- 마우스 드래그로 ROI 사각형 그리기
- ROI 좌표 수동 입력 필드 병행 (X, Y, W, H)
- 드래그 ↔ 수동 입력 실시간 동기화
- ROI 초기화 버튼
- ROI 유효성 검증 실시간 표시

**테스트:**
- ROI 좌표 설정 후 데이터 모델 반영 확인
- 경계 초과 좌표 입력 → 에러 표시
- 수동 입력 → 화면 ROI 박스 갱신 확인

**직접 실행 확인:**
- 이미지 위에서 마우스 드래그 → ROI 박스 출현 확인
- 좌표 수동 입력 → ROI 박스 변경 확인

**완료 조건:**
```
□ pytest 통과
□ 드래그 ROI 동작 직접 확인
□ 수동 입력 동기화 직접 확인
□ git commit
```

---

### Step 16 — 설정 화면

**목표:** 전체 시스템 설정 화면 완성

**구현 내용:**
- `ui/pages/settings_page.py`
- 임계값 슬라이더 (기본 70, 범위 50~95)
- FP/FN 가중치 조정 (w1 / w2 슬라이더)
- 분리 마진 경고 기준 설정
- NG 샘플 최소 수량 경고 기준 설정
- 설정 저장/초기화 버튼
- 변경사항 저장 전 확인 다이얼로그

**테스트:**
- 설정 변경 후 저장 → 재로드 시 값 유지 확인
- 초기화 후 기본값 복원 확인

**직접 실행 확인:**
- 슬라이더 조작 → 값 변경 확인
- 저장 후 앱 재시작 → 값 유지 확인

**완료 조건:**
```
□ pytest 통과
□ 설정 저장/복원 직접 확인
□ git commit
```

---

## Phase 3: Feature 분석 엔진 (Step 17~24)

---

### Step 17 — 이미지 로드 및 전처리 유틸리티

**목표:** 이미지 로드, 변환, 기본 전처리 파이프라인 구축

**구현 내용:**
- `core/image_processor.py`
- 이미지 로드 (OpenCV)
- 그레이스케일 변환
- 노이즈 제거 필터 (Gaussian, Median, Bilateral)
- 히스토그램 평활화
- 이미지 정규화
- 배치 처리 지원

**테스트:**
- 각 전처리 함수 입출력 형상 확인
- 손상 이미지 로드 → RuntimeProcessingError 발생 확인

**직접 실행 확인:**
- 테스트 이미지로 각 전처리 결과 이미지 파일 저장 후 눈으로 확인

**완료 조건:**
```
□ pytest 통과
□ 전처리 결과 이미지 직접 확인
□ git commit
```

---

### Step 18 — 히스토그램 및 밝기 분석

**목표:** 이미지 밝기 / 대비 특성 정량 분석 완성

**구현 내용:**
- `core/analyzers/histogram_analyzer.py`
- 평균 / 표준편차 / 최솟값 / 최댓값 그레이 레벨
- 히스토그램 분포 분석 (피크 수, 분포 형태)
- OK vs NG 히스토그램 분리도 계산
- 결과: `HistogramAnalysisResult` 데이터 클래스

**테스트:**
- 알려진 이미지에 대해 정확한 통계값 반환 확인
- OK/NG 히스토그램 분리도 수치 정상 계산 확인

**직접 실행 확인:**
- 분석 결과 출력값 수치 확인

**완료 조건:**
```
□ pytest 통과
□ 분석 수치 출력 직접 확인
□ git commit
```

---

### Step 19 — 노이즈 수준 분석

**목표:** 이미지 노이즈 정량화 완성

**구현 내용:**
- `core/analyzers/noise_analyzer.py`
- Laplacian variance 기반 노이즈 측정
- SNR (Signal-to-Noise Ratio) 계산
- 노이즈 레벨 분류 (Low / Medium / High)
- 권장 필터 자동 선택 로직

**테스트:**
- 고노이즈 / 저노이즈 이미지 분류 정확성 확인

**직접 실행 확인:**
- 여러 이미지에 대한 노이즈 레벨 분류 결과 확인

**완료 조건:**
```
□ pytest 통과
□ 노이즈 분류 결과 직접 확인
□ git commit
```

---

### Step 20 — 에지 강도 분석

**목표:** 이미지 에지 특성 분석 완성

**구현 내용:**
- `core/analyzers/edge_analyzer.py`
- Sobel / Canny 에지 강도 측정
- 에지 밀도 계산 (에지 픽셀 비율)
- 에지 방향성 분석 (수평 / 수직 / 대각)
- Caliper 적용 가능성 판단 지표 계산

**테스트:**
- 에지 강도 수치 정상 계산 확인
- 방향성 분류 정확성 확인

**직접 실행 확인:**
- 에지 검출 결과 이미지 저장 후 눈으로 확인

**완료 조건:**
```
□ pytest 통과
□ 에지 검출 결과 이미지 직접 확인
□ git commit
```

---

### Step 21 — 형상 및 Blob 특성 분석

**목표:** 이미지 내 형상/Blob 특성 정량 분석 완성

**구현 내용:**
- `core/analyzers/shape_analyzer.py`
- Blob 검출 및 속성 추출 (면적, 원형도, 종횡비)
- 윤곽선 복잡도 계산
- 반복 패턴 존재 여부 감지
- 원형 구조 검출 (Hough Circle)

**테스트:**
- 알려진 원형 이미지에서 Hough Circle 정상 검출 확인
- Blob 속성 수치 정상 확인

**직접 실행 확인:**
- Blob 검출 결과 오버레이 이미지 저장 후 눈으로 확인

**완료 조건:**
```
□ pytest 통과
□ Blob 오버레이 이미지 직접 확인
□ git commit
```

---

### Step 22 — Feature 분석 통합 및 AI 요약

**목표:** 분석 결과를 통합하여 AI에게 전달할 요약 텍스트 생성

**구현 내용:**
- `core/feature_analyzer.py` — 통합 분석 클래스
- 히스토그램 + 노이즈 + 에지 + 형상 분석 결과 통합
- `FeatureAnalysisSummary` 데이터 클래스 정의
- AI 프롬프트 생성용 텍스트 직렬화
- 분석 결과 JSON 저장

**테스트:**
- 전체 분석 파이프라인 정상 실행 확인
- 결과 JSON 직렬화/역직렬화 확인

**직접 실행 확인:**
- 분석 결과 JSON 파일 열어서 수치 확인

**완료 조건:**
```
□ pytest 통과
□ 결과 JSON 내용 직접 확인
□ git commit
```

---

### Step 23 — 분석 실행 화면 UI (진행 상태)

**목표:** 분석 실행 화면, 진행 상태 실시간 표시

**구현 내용:**
- `ui/pages/analysis_page.py`
- "분석 시작" 버튼
- 단계별 진행 상태 바 (Feature 분석 / Align 설계 / Inspection 설계 / 평가)
- 실시간 로그 출력 텍스트 박스 (스크롤 자동)
- 분석 중 취소 버튼
- 완료 시 "결과 보기" 버튼 활성화

**테스트:**
- 진행 상태 업데이트 시그널 정상 동작 확인
- 취소 시 프로세스 중단 확인

**직접 실행 확인:**
- 분석 시작 → 진행 상태 바 실시간 변화 확인
- 로그 텍스트 실시간 출력 확인

**완료 조건:**
```
□ pytest 통과
□ 진행 상태 바 동작 직접 확인
□ 로그 실시간 출력 직접 확인
□ git commit
```

---

### Step 24 — Feature 분석 결과 UI 표시

**목표:** Feature 분석 결과를 UI 결과 뷰어에 표시

**구현 내용:**
- 결과 뷰어 내 "이미지 특성" 카드
- 히스토그램 차트 (PyQt6 또는 matplotlib 임베드)
- 노이즈 레벨 / 에지 강도 / Blob 수량 수치 표시
- OK vs NG 비교 통계 테이블
- AI 분석 요약 텍스트 표시 영역

**테스트:**
- 분석 결과 데이터 → UI 렌더링 정상 확인

**직접 실행 확인:**
- 분석 완료 후 결과 카드 출현 및 수치 확인

**완료 조건:**
```
□ pytest 통과
□ 결과 카드 시각 확인
□ 히스토그램 차트 출현 확인
□ git commit
```

---

## Phase 4: Align 엔진 (Step 25~31)

---

### Step 25 — Pattern Matching Align 엔진

**목표:** 템플릿 매칭 기반 Align 엔진 구현

**구현 내용:**
- `core/align/pattern_align.py` — `IAlignEngine` 구현
- 정규화 상관 계수 매칭 (TM_CCOEFF_NORMED)
- 매칭 점수 계산 및 임계값 판정
- 매칭 위치 → 변환 행렬 계산
- 매칭 실패 조건 정의 (점수 < 기준)

**테스트:**
- 알려진 이미지 쌍에 대해 정확한 위치 반환 확인
- 매칭 불가 이미지 → 실패 결과 반환 확인

**직접 실행 확인:**
- 매칭 결과 오버레이 이미지 저장 후 눈으로 확인

**완료 조건:**
```
□ pytest 통과
□ 매칭 결과 이미지 직접 확인
□ git commit
```

---

### Step 26 — Caliper Align 엔진

**목표:** Caliper 기반 Align 엔진 구현 (4섹션 설계 출력 포함)

**구현 내용:**
- `core/align/caliper_align.py` — `IAlignEngine` 구현
- 에지 기반 기준점 탐색
- Projection Length / Search Length / Condition / Threshold / Polarity 파라미터 지원
- 탐색 방향 (Inward / Outward / Leftward / Rightward) 지원
- 4섹션 설계 문서 자동 생성

**테스트:**
- 에지 검출 정상 확인
- 4섹션 출력 구조 검증

**직접 실행 확인:**
- Caliper 결과 오버레이 이미지 저장 후 눈으로 확인
- 4섹션 출력 텍스트 확인

**완료 조건:**
```
□ pytest 통과
□ 결과 이미지 직접 확인
□ 4섹션 출력 텍스트 확인
□ git commit
```

---

### Step 27 — Feature-based / Contour / Blob Align 엔진

**목표:** Fallback 3단계용 추가 Align 엔진 구현

**구현 내용:**
- `core/align/feature_align.py` — ORB / SIFT 기반
- `core/align/contour_align.py` — 윤곽선 매칭 기반
- `core/align/blob_align.py` — Blob 중심점 기반

**테스트:**
- 각 엔진 정상 동작 확인
- 실패 조건 정상 반환 확인

**직접 실행 확인:**
- 각 엔진 결과 이미지 저장 후 눈으로 확인

**완료 조건:**
```
□ pytest 통과 (3종)
□ 각 결과 이미지 직접 확인
□ git commit
```

---

### Step 28 — Align Fallback 체인 통합

**목표:** Pattern → Caliper → Feature/Contour/Blob → 실패 체인 완성

**구현 내용:**
- `core/align/align_engine.py` — Fallback 체인 오케스트레이터
- 각 단계 실패 시 자동 다음 단계 시도
- AI 판단: 3단계에서 시도 순서 결정 (AI Provider 호출)
- 실패 원인 로그 기록
- 최종 실패 시 원인 + 권장 조치 출력

**테스트:**
- Pattern 성공 시 체인 1단계에서 종료 확인
- Pattern 실패 → Caliper 시도 확인
- 모두 실패 → 최종 실패 결과 반환 확인

**직접 실행 확인:**
- 각 실패 시나리오 트리거 → 체인 동작 로그 확인

**완료 조건:**
```
□ pytest 통과
□ Fallback 체인 단계 전환 로그 직접 확인
□ 최종 실패 출력 확인
□ git commit
```

---

### Step 29 — Align 결과 UI 표시

**목표:** Align 결과를 결과 뷰어에 표시

**구현 내용:**
- 결과 뷰어 내 "Align 전략" 카드
- 사용된 전략명 / 매칭 점수 / 기준점 좌표 표시
- 4섹션 파라미터 테이블 (Caliper 사용 시)
- Align 오버레이 이미지 표시
- 라이브러리 대응 명칭 테이블

**테스트:**
- Align 결과 데이터 → UI 렌더링 정상 확인

**직접 실행 확인:**
- 결과 뷰어에서 Align 카드 출현 및 내용 확인

**완료 조건:**
```
□ pytest 통과
□ Align 결과 카드 시각 확인
□ git commit
```

---

### Step 30 — Align 통합 테스트 및 검증

**목표:** Align 전체 파이프라인 End-to-End 검증

**구현 내용:**
- Align 전체 흐름 통합 테스트 작성
- 여러 이미지 타입에 대한 회귀 테스트
- 성능 측정 (처리 시간 로깅)
- 엣지 케이스 시나리오 테스트

**테스트:**
- E2E 테스트 3종 이상 통과
- 회귀 테스트 전체 통과

**직접 실행 확인:**
- 실제 테스트 이미지로 전체 흐름 UI에서 실행
- 각 단계 결과 눈으로 확인

**완료 조건:**
```
□ E2E 테스트 통과
□ 실제 이미지로 전체 Align 흐름 직접 확인
□ git commit
```

---

### Step 31 — ROI 적용 및 전처리 파이프라인

**목표:** ROI 크롭 + 전처리 파이프라인 완성

**구현 내용:**
- `core/preprocessor.py`
- Align 결과 적용 후 ROI 크롭
- 노이즈 분석 결과 기반 자동 필터 선택
- 전처리 파이프라인 직렬화 (설계 문서 출력용)
- 전처리 전/후 이미지 비교 저장

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

## Phase 5: Inspection 엔진 (Step 32~41)

---

### Step 32 — Blob 기반 Inspection 엔진

**목표:** Blob 분석 기반 Inspection 엔진 구현

**구현 내용:**
- `core/inspection/blob_inspector.py` — `IInspectionEngine` 구현
- 면적 / 원형도 / 그레이 레벨 / 연결성 파라미터 지원
- Polarity (Darker / Brighter than background) 지원
- 4섹션 설계 문서 자동 생성

**테스트:**
- OK 이미지 → Blob 미검출 확인
- NG 이미지 → Blob 검출 확인

**직접 실행 확인:**
- 검출 결과 오버레이 이미지 저장 후 눈으로 확인

**완료 조건:**
```
□ pytest 통과
□ 검출 결과 이미지 직접 확인
□ git commit
```

---

### Step 33 — Circular Caliper Inspection 엔진

**목표:** 원형 Caliper 배치 기반 검사 엔진 구현 (홀 지름 등)

**구현 내용:**
- `core/inspection/circular_caliper_inspector.py`
- 배치 수 / 각도 간격 / 시작 각도 / 탐색 반경 파라미터
- Inward / Outward 방향 지원
- 최소자승 원 피팅 (LSQ Circle Fit)
- 이상치 처리 (3σ 초과 제외)
- 유효 Caliper < 8개 시 신뢰도 경고
- 4섹션 설계 문서 자동 생성

**테스트:**
- 원형 이미지에서 지름 정상 측정 확인
- 이상치 처리 정상 동작 확인

**직접 실행 확인:**
- 원형 검사 결과 오버레이 이미지 저장 후 눈으로 확인

**완료 조건:**
```
□ pytest 통과
□ 결과 이미지 직접 확인
□ git commit
```

---

### Step 34 — Linear Caliper Inspection 엔진

**목표:** 선형 Caliper 배치 기반 검사 엔진 구현 (폭 측정 등)

**구현 내용:**
- `core/inspection/linear_caliper_inspector.py`
- 좌우/상하 배치 수 / 간격 / 탐색 방향 파라미터
- Leftward / Rightward / Upward / Downward 방향 지원
- 평균 에지선 계산 및 폭/직진도 계산
- 4섹션 설계 문서 자동 생성

**테스트:**
- 직선 에지 이미지에서 폭 정상 측정 확인

**직접 실행 확인:**
- 결과 오버레이 이미지 저장 후 눈으로 확인

**완료 조건:**
```
□ pytest 통과
□ 결과 이미지 직접 확인
□ git commit
```

---

### Step 35 — Pattern 기반 Inspection 엔진

**목표:** 패턴 매칭 기반 결함 검사 엔진 구현

**구현 내용:**
- `core/inspection/pattern_inspector.py`
- OK 기준 이미지 대비 차분 검사
- 차분 임계값 / 최소 면적 파라미터
- 4섹션 설계 문서 자동 생성

**테스트:**
- OK 대비 NG 차분 정상 검출 확인

**직접 실행 확인:**
- 차분 결과 이미지 저장 후 눈으로 확인

**완료 조건:**
```
□ pytest 통과
□ 차분 결과 이미지 직접 확인
□ git commit
```

---

### Step 36 — Dynamic Candidate 생성기

**목표:** 이미지 특성 기반 Candidate 자동 생성

**구현 내용:**
- `core/inspection/candidate_generator.py`
- Feature 분석 결과 기반 적합한 Inspection 방법 후보 선택
- AI Provider 호출 → 추가 후보 제안
- Candidate 우선순위 정렬
- 최대 Candidate 수 제한 설정

**테스트:**
- Feature 분석 결과 입력 → Candidate 목록 생성 확인
- AI 호출 실패 시 로컬 후보만으로 진행 확인

**직접 실행 확인:**
- 생성된 Candidate 목록 출력 확인

**완료 조건:**
```
□ pytest 통과
□ Candidate 목록 직접 확인
□ git commit
```

---

### Step 37 — 평가 엔진 (Evaluation)

**목표:** OK/NG 분류 품질 스코어 계산 엔진 완성

**구현 내용:**
- `core/evaluation/evaluator.py` — `IEvaluationEngine` 구현
- OK 샘플 통과율 / NG 샘플 검출율 계산
- 스코어 공식: `score = (OK 통과율 × w1) + (NG 검출율 × w2)`
- 분리 마진 계산
- FP / FN 분류 및 목록 추출
- "경계선 위험 구간" 경고 로직

**테스트:**
- 알려진 OK/NG 이미지 세트에 대한 스코어 정확성 확인
- 마진 < 15 시 경고 트리거 확인

**직접 실행 확인:**
- 스코어 계산 결과 수치 확인

**완료 조건:**
```
□ pytest 통과
□ 스코어 수치 직접 확인
□ git commit
```

---

### Step 38 — 최적화 루프 및 Best Candidate 선택

**목표:** Candidate 평가 → Best 선택 루프 완성

**구현 내용:**
- `core/inspection/optimizer.py`
- 모든 Candidate에 대해 Evaluation 실행
- 스코어 기준 정렬 → Best 선택
- 각 Candidate 결과 저장
- 최적화 루프 로그 기록

**테스트:**
- Candidate 3종 입력 → Best 정확히 선택 확인
- 동점 시 처리 방법 확인

**직접 실행 확인:**
- 최적화 루프 로그 출력 확인

**완료 조건:**
```
□ pytest 통과
□ Best 선택 로그 직접 확인
□ git commit
```

---

### Step 39 — Failure 분석

**목표:** 실패 케이스 분석 및 원인 제공

**구현 내용:**
- `core/evaluation/failure_analyzer.py`
- FP / FN 이미지 목록 추출
- 실패 이미지별 원인 분석 (AI 호출 기반)
- 개선 방향 텍스트 생성
- 실패 케이스 시각화 (오버레이)

**테스트:**
- FP / FN 목록 정상 추출 확인
- 원인 분석 텍스트 생성 확인

**직접 실행 확인:**
- 실패 이미지 오버레이 결과 직접 확인

**완료 조건:**
```
□ pytest 통과
□ 실패 이미지 오버레이 직접 확인
□ git commit
```

---

### Step 40 — Feasibility Analysis 및 기술 수준 판단

**목표:** Rule-based 한계 판정 및 EL/DL 추천 완성

**구현 내용:**
- `core/evaluation/feasibility_analyzer.py`
- `best_score < threshold` 조건 판정
- AI 호출: 이미지 상태 + 검사 난이도 분석 → EL 또는 DL 결정
- 판단 근거 텍스트 생성
- 모델 추천 (EL: MobileNet 계열 / DL: CNN / Anomaly)
- `FeasibilityResult` 데이터 클래스

**테스트:**
- 스코어 < threshold → EL/DL 추천 트리거 확인
- AI 판단 결과 정상 파싱 확인

**직접 실행 확인:**
- EL/DL 추천 결과 텍스트 출력 확인

**완료 조건:**
```
□ pytest 통과
□ 추천 결과 텍스트 직접 확인
□ git commit
```

---

### Step 41 — Inspection 통합 테스트

**목표:** Inspection 전체 파이프라인 E2E 검증

**구현 내용:**
- Candidate 생성 → 평가 → 최적화 → Failure 분석 → Feasibility E2E 테스트
- 다양한 이미지 시나리오 회귀 테스트
- NG 0장 시나리오 → 알람 트리거 확인

**테스트:**
- E2E 테스트 3종 이상 통과

**직접 실행 확인:**
- 실제 이미지로 전체 Inspection 흐름 UI에서 실행 확인

**완료 조건:**
```
□ E2E 테스트 통과
□ 전체 Inspection 흐름 UI 직접 확인
□ git commit
```

---

## Phase 6: 결과 뷰어 및 출력 (Step 42~46)

---

### Step 42 — 결과 뷰어 레이아웃

**목표:** 결과 뷰어 전체 레이아웃 완성

**구현 내용:**
- `ui/pages/result_page.py`
- 탭 구성: 요약 / Align 결과 / Inspection 결과 / Feasibility
- 각 탭별 카드 레이아웃
- 결과 데이터 바인딩 구조

**테스트:**
- 결과 데이터 → 탭별 렌더링 정상 확인

**직접 실행 확인:**
- 결과 뷰어 탭 전환 직접 확인

**완료 조건:**
```
□ pytest 통과
□ 탭 전환 직접 확인
□ git commit
```

---

### Step 43 — Inspection 결과 카드 및 파라미터 테이블

**목표:** Inspection 알고리즘 결과 상세 표시

**구현 내용:**
- Best Candidate 알고리즘명 / 스코어 / 분리 마진 표시
- 4섹션 파라미터 테이블 (Caliper 배치 구조 / 개별 파라미터 / 계산 방식 / 근거)
- 라이브러리 대응 명칭 테이블 (Keyence / Cognex / Halcon / MIL)
- 결과 이미지 오버레이 뷰어 (확대/축소 지원)
- Candidate 비교 테이블 (전체 후보 스코어)

**테스트:**
- 결과 데이터 → 카드 렌더링 정상 확인

**직접 실행 확인:**
- 파라미터 테이블 출현 및 내용 직접 확인
- 라이브러리 대응 명칭 테이블 확인

**완료 조건:**
```
□ pytest 통과
□ 결과 카드 전체 직접 확인
□ git commit
```

---

### Step 44 — Failure 케이스 뷰어

**목표:** 실패 케이스 시각적 표시

**구현 내용:**
- FP / FN 이미지 썸네일 그리드
- 이미지 클릭 시 원인 분석 텍스트 팝업
- 개선 방향 텍스트 표시
- 실패 케이스 수량 요약

**테스트:**
- 실패 케이스 데이터 → 그리드 렌더링 확인

**직접 실행 확인:**
- 실패 이미지 클릭 → 원인 팝업 직접 확인

**완료 조건:**
```
□ pytest 통과
□ 실패 케이스 팝업 직접 확인
□ git commit
```

---

### Step 45 — Feasibility 및 기술 수준 결과 표시

**목표:** Feasibility 판정 결과 표시 완성

**구현 내용:**
- Rule-based 충분 / EL 추천 / DL 추천 상태 배지 표시
- AI 판단 근거 텍스트 표시
- 추천 모델 정보 (EL: MobileNet / DL: CNN / Anomaly)
- 다음 단계 안내 텍스트

**테스트:**
- 각 판정 상태별 배지 색상 정상 출력 확인

**직접 실행 확인:**
- Feasibility 결과 카드 출현 및 배지 확인

**완료 조건:**
```
□ pytest 통과
□ 결과 카드 직접 확인
□ git commit
```

---

### Step 46 — 결과 내보내기 (Export)

**목표:** 분석 결과 파일 저장 기능 완성

**구현 내용:**
- 결과 JSON 저장 (전체 파라미터 포함)
- 결과 PDF 리포트 생성 (reportlab 또는 weasyprint)
- 결과 이미지 일괄 저장
- 내보내기 경로 선택 다이얼로그

**테스트:**
- JSON 저장 후 내용 정합성 확인
- PDF 생성 정상 확인

**직접 실행 확인:**
- 내보내기 실행 → 파일 저장 확인
- PDF 파일 열어서 내용 확인

**완료 조건:**
```
□ pytest 통과
□ JSON / PDF 파일 직접 확인
□ git commit
```

---

## Phase 7: 통합 완성 및 운영 품질 (Step 47~50)

---

### Step 47 — 전체 워크플로우 E2E 통합 테스트

**목표:** 이미지 업로드 → 결과 출력 전체 흐름 완전 검증

**구현 내용:**
- 전체 워크플로우 E2E 자동화 테스트 (pytest + 테스트 이미지 세트)
- 시나리오: OK만 있을 때 / NG 부족 / 정상 세트 / Align 실패 시나리오
- 회귀 테스트 스위트 구축
- 성능 프로파일링 (각 단계 처리 시간 측정)

**테스트:**
- E2E 시나리오 4종 이상 통과

**직접 실행 확인:**
- 테스트 이미지 세트로 전체 워크플로우 UI에서 처음부터 끝까지 실행
- 각 화면 전환, 결과 출력 전부 눈으로 확인

**완료 조건:**
```
□ E2E 테스트 4종 통과
□ 전체 워크플로우 UI 직접 실행 완료
□ git commit
```

---

### Step 48 — UI 품질 개선 및 UX 다듬기

**목표:** 운영 수준 UI 완성도 확보

**구현 내용:**
- 전체 화면 폰트 / 색상 / 간격 일관성 검토 및 수정
- 로딩 스피너 / 스켈레톤 UI 적용
- 빈 상태(Empty State) 안내 메시지 전체 화면 적용
- 툴팁 추가 (파라미터 설명 등)
- 키보드 단축키 설정 (분석 시작 / 초기화 등)
- 창 크기 조절 시 레이아웃 반응형 검토

**테스트:**
- UI 컴포넌트 렌더링 오류 없음 확인

**직접 실행 확인:**
- 전체 화면 순서대로 직접 조작하며 UX 이슈 확인 및 수정
- 창 크기 변경 → 레이아웃 깨짐 없음 확인

**완료 조건:**
```
□ pytest 통과
□ 전체 화면 UX 직접 점검 완료
□ git commit
```

---

### Step 49 — 배포 패키징

**목표:** Windows / macOS / Linux 실행 파일 생성

**구현 내용:**
- PyInstaller 스펙 파일 작성 (`vision_agent.spec`)
- 플랫폼별 빌드 스크립트 (`build_windows.bat`, `build_mac.sh`, `build_linux.sh`)
- 아이콘 / 스플래시 이미지 적용
- 빌드 후 실행 테스트 (Python 없는 환경에서)
- `pip install` 패키지 구성 (`setup.py` / `pyproject.toml`)

**테스트:**
- 빌드 후 생성된 실행 파일 실행 확인

**직접 실행 확인:**
- 생성된 .exe (또는 바이너리) 실행 → 전체 기능 동작 확인

**완료 조건:**
```
□ 실행 파일 생성 완료
□ Python 없는 환경에서 실행 직접 확인
□ git commit + 버전 태그
```

---

### Step 50 — 최종 검수 및 문서화

**목표:** 운영 릴리스 준비 완료

**구현 내용:**
- 전체 회귀 테스트 최종 실행
- `README.md` 최종 업데이트 (설치 방법 / 사용법 / 스크린샷)
- `CHANGELOG.md` 작성
- 알려진 이슈 정리
- 향후 개발 로드맵 정리 (EL/DL 모듈 연동 등)

**테스트:**
- 전체 pytest 스위트 최종 통과

**직접 실행 확인:**
- 처음 설치하는 것처럼 README 따라서 설치 후 전체 기능 직접 실행
- 실제 비전 이미지로 완전한 분석 사이클 1회 완주

**완료 조건:**
```
□ 전체 pytest 통과
□ README 따라 설치 → 분석 완주 직접 확인
□ CHANGELOG 작성
□ 최종 git tag 및 release
```

---

## 📋 14. 최종 출력 형식

```
═══════════════════════════════════════════════
  AI Vision Engineer Agent — 분석 결과
═══════════════════════════════════════════════

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

## 🔥 15. 최종 결론

이 시스템은:

- ✅ 비전 엔지니어 역할 수행
- ✅ 라이브러리 독립적 알고리즘 설계 출력 (Keyence / Cognex / Halcon / MIL)
- ✅ Caliper 배치 구조 전체 설계 (개수 / 각도 / 방향 / 4섹션)
- ✅ 에러 처리 3레이어 구조
- ✅ 데이터 부족 시 명확한 알람 체계
- ✅ 분류 품질 기준 SLA 정의
- ✅ 기술 수준 자동 판단 (스코어 기반 → EL/DL 추천)
- ✅ 로컬 전용 실행 (Windows / macOS / Linux)
- ✅ 운영 수준 모던 UI (다크 테마, 사이드바, API 모달)
- ✅ API Key UI 입력 + 로컬 암호화 저장
- ✅ **50 Step 단계별 TDD + Human Review + 직접 실행 검증**
- ✅ 유지보수 가능한 SOLID 구조

---

> **"AI가 코드를 만들고, 테스트가 검증하고, 사람이 직접 눈으로 확인하며, 시스템이 비전 엔지니어 역할을 수행하는 자동화 플랫폼"**
