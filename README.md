# Argos — AI Vision Engineer Agent

> 비전 알고리즘을 설계하고, 한계를 판단하며, 필요한 기술 수준까지 결정하는 AI Vision Engineer Agent

**Argos**는 비전 엔지니어를 위한 AI 기반 알고리즘 자동 설계 데스크톱 애플리케이션입니다.
OK/NG 샘플 이미지, ROI, 검사 목적을 입력하면 Align부터 Inspection까지 전체 비전 알고리즘을 자동으로 설계하고,
최적 파라미터와 라이브러리별 매핑(Keyence, Cognex, Halcon, MIL)을 제공합니다.

---

## 주요 기능

- **Feature 분석** — 히스토그램, 노이즈, 에지, 형상/Blob 특성 자동 분석 및 AI 요약
- **Align 엔진 (5종 폴백 체인)** — Pattern Matching, Caliper, Feature-based(ORB/SIFT), Contour, Blob
- **Inspection 엔진 (4종)** — Blob, Circular Caliper, Linear Caliper, Pattern 기반 검사
- **Multi-Candidate 평가** — 다중 후보 생성 → 자동 평가 → 최적 알고리즘 선택
- **Failure 분석** — FP/FN 오버레이 시각화 및 AI 기반 원인 분석
- **Feasibility 판단** — Rule-based / Edge Learning / Deep Learning 기술 수준 자동 판정
- **결과 내보내기** — JSON, PDF, 이미지(오버레이) 형식 지원
- **대시보드 워크플로우** — 5단계 진행 상황 시각화 및 상태 추적
- **모던 다크 테마 UI** — PyQt6 기반 데스크톱 네이티브 인터페이스

### 프로그램 실행 동작 확인

- https://rebel-pyramid-645.notion.site/Argos-AI-Vision-Engineer-Agent-3486a9e71bde80f58ec1c33a08f97b19?source=copy_link

**위의 링크로 접속하여 프로그램의 동작 내용을 보실 수 있습니다.**

---

## 기술 스택

| 구분 | 기술 |
|------|------|
| 언어 | Python 3.11+ |
| UI 프레임워크 | PyQt6 |
| 영상 처리 | OpenCV (opencv-python-headless) |
| 수치 연산 | NumPy |
| AI Provider | OpenAI / Claude / Gemini (API 기반) |
| 암호화 | cryptography (Fernet), keyring |
| PDF 생성 | ReportLab |
| 테스트 | pytest, pytest-qt, pytest-cov |
| 빌드/배포 | PyInstaller |

---

## 설치 방법

### 요구 사항

- Python 3.11 이상
- pip 패키지 매니저

### pip 설치

```bash
git clone <repository-url>
cd argos
pip install -r requirements.txt
```

### 개발 환경 설정

```bash
# 가상 환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# 의존성 설치
pip install -r requirements.txt

# 테스트 실행
python -m pytest
```

---

## 사용법

### 애플리케이션 실행

```bash
python main.py
```

### 워크플로우 (5단계)

1. **이미지 업로드** — OK/NG/Align 이미지를 드래그 앤 드롭 또는 파일 선택으로 업로드
2. **ROI 설정** — 이미지 위에서 마우스 드래그로 관심 영역(ROI) 지정
3. **검사 목적 입력** — 검사 유형 선택, 대상 설명, OK/NG 판정 기준 및 허용 공차 입력
4. **분석 실행** — AI 기반 자동 분석 (Feature → Align → Inspection → Evaluation → Feasibility)
5. **결과 확인** — 6개 탭(요약, Feature 분석, Align, Inspection, Failure, Feasibility)에서 결과 확인 및 내보내기

### API 키 설정

상단 툴바의 "API 입력" 버튼 클릭 → Provider 선택 (OpenAI / Claude / Gemini) → API Key 입력 → 연결 테스트

- API Key는 로컬에 Fernet 암호화 저장됩니다
- AI API는 Feature 요약, 전략 판단, Failure 원인 분석, Feasibility 판정에 사용됩니다
- 이미지는 외부로 전송되지 않으며, 로컬에서만 처리됩니다

---

## 빌드 (PyInstaller)

### macOS / Linux

```bash
bash scripts/build.sh
```

### Windows

```bat
scripts\build.bat
```

빌드 결과물은 `dist/` 디렉토리에 생성됩니다. `argos.spec` 파일로 빌드 설정을 커스터마이징할 수 있습니다.

---

## 프로젝트 구조

```
argos/
├── main.py                          # 애플리케이션 진입점
├── requirements.txt                 # Python 의존성
├── pyproject.toml                   # 프로젝트 메타데이터
├── argos.spec                       # PyInstaller 빌드 스펙
├── assets/                          # 애플리케이션 리소스
│   ├── icon.png
│   └── splash.png
├── config/                          # 설정 및 상수
│   ├── constants.py
│   ├── paths.py
│   └── settings.py
├── core/                            # 핵심 엔진 및 알고리즘
│   ├── __init__.py                  # __version__ = "1.0.0"
│   ├── image_processor.py           # 이미지 로드 및 전처리
│   ├── image_store.py               # 이미지 데이터 저장소
│   ├── interfaces.py                # SOLID 인터페이스 정의
│   ├── models.py                    # 데이터 모델
│   ├── validators.py                # 입력 검증
│   ├── key_manager.py               # API Key 암호화 관리
│   ├── logger.py                    # 로깅
│   ├── error_handler.py             # 에러 핸들링
│   ├── exceptions.py                # 커스텀 예외
│   ├── providers/                   # AI Provider 레이어
│   │   ├── base_provider.py
│   │   ├── openai_provider.py
│   │   ├── claude_provider.py
│   │   ├── gemini_provider.py
│   │   └── provider_factory.py
│   ├── analyzers/                   # Feature 분석기
│   │   ├── histogram_analyzer.py
│   │   ├── noise_analyzer.py
│   │   ├── edge_analyzer.py
│   │   ├── shape_analyzer.py
│   │   └── feature_analyzer.py
│   ├── align/                       # Align 엔진 (5종)
│   │   ├── align_engine.py          # AlignFallbackChain
│   │   ├── pattern_align.py
│   │   ├── caliper_align.py
│   │   ├── feature_align.py
│   │   ├── contour_align.py
│   │   └── blob_align.py
│   ├── inspection/                  # Inspection 엔진 (4종)
│   │   ├── blob_inspector.py
│   │   ├── circular_caliper_inspector.py
│   │   ├── linear_caliper_inspector.py
│   │   ├── pattern_inspector.py
│   │   ├── candidate_generator.py   # Dynamic Candidate 생성
│   │   └── optimizer.py             # 최적화 루프
│   ├── evaluation/                  # 평가 및 판정
│   │   ├── evaluator.py             # Inspection 평가 엔진
│   │   ├── failure_analyzer.py      # FP/FN 원인 분석
│   │   └── feasibility_analyzer.py  # 기술 수준 판정
│   └── export/                      # 결과 내보내기
│       ├── json_exporter.py
│       ├── pdf_exporter.py
│       └── image_exporter.py
├── ui/                              # PyQt6 사용자 인터페이스
│   ├── main_window.py               # 메인 윈도우
│   ├── theme.py                     # 디자인 토큰 및 테마
│   ├── style.py                     # QSS 스타일시트
│   ├── pages/                       # 페이지 (화면)
│   │   ├── base_page.py
│   │   ├── dashboard_page.py
│   │   ├── upload_page.py
│   │   ├── roi_page.py
│   │   ├── purpose_page.py
│   │   ├── analysis_page.py
│   │   ├── result_page.py
│   │   ├── settings_page.py
│   │   ├── summary_tab.py
│   │   ├── align_tab.py
│   │   ├── inspection_tab.py
│   │   ├── failure_tab.py
│   │   └── feasibility_tab.py
│   ├── components/                  # 재사용 UI 컴포넌트
│   │   ├── sidebar.py
│   │   ├── toolbar.py
│   │   ├── drop_zone.py
│   │   ├── flow_layout.py
│   │   ├── thumbnail_card.py
│   │   ├── thumbnail_grid.py
│   │   ├── roi_canvas.py
│   │   ├── roi_controls.py
│   │   ├── section_card.py
│   │   ├── stat_card.py
│   │   ├── status_indicator.py
│   │   ├── workflow_indicator.py
│   │   ├── progress_steps.py
│   │   ├── log_viewer.py
│   │   ├── toast.py
│   │   └── image_viewer_dialog.py
│   ├── dialogs/                     # 다이얼로그
│   │   ├── api_key_dialog.py
│   │   ├── export_dialog.py
│   │   └── failure_detail_dialog.py
│   ├── widgets/                     # 커스텀 위젯
│   │   ├── empty_state.py
│   │   └── loading_spinner.py
│   └── workers/                     # 백그라운드 워커
│       └── analysis_worker.py
├── scripts/                         # 빌드 스크립트
│   ├── build.sh
│   ├── build.bat
│   └── generate_assets.py
└── tests/                           # 테스트 스위트 (1087개)
    ├── conftest.py
    ├── fixtures/
    ├── unit/
    ├── e2e/
    ├── integration/
    ├── inspection/
    ├── evaluation/
    └── workers/
```

---

## 테스트

```bash
# 전체 테스트 실행
python -m pytest

# 간략 출력
python -m pytest --tb=short -q

# 커버리지 포함
python -m pytest --cov=core --cov=ui
```

현재 **1087개** 테스트가 모두 통과합니다.

---

## 개발 현황

- 버전: **v1.0.0**
- 전체 진행률: **51/51 Steps 완료**
- 상세 현황: [PROGRESS.md](PROGRESS.md) 참조
- 변경 이력: [CHANGELOG.md](CHANGELOG.md) 참조
- 알려진 이슈: [KNOWN_ISSUES.md](KNOWN_ISSUES.md) 참조
- 향후 로드맵: [ROADMAP.md](ROADMAP.md) 참조

---

## 라이선스

MIT License — 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.
