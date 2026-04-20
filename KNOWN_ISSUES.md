# 알려진 이슈 및 제한 사항

이 문서는 Argos v1.0.0의 알려진 제한 사항과 이슈를 정리합니다.

---

## CPU 전용 실행

Argos는 CPU 환경에서만 동작합니다. GPU 가속은 지원하지 않습니다.

- 모든 영상 처리(OpenCV)는 CPU에서 실행됩니다
- Feasibility 분석에서 Edge Learning(EL) 또는 Deep Learning(DL)을 **추천**할 수 있으나, 실제 EL/DL 모델을 학습하거나 실행하지는 않습니다
- EL/DL이 필요하다고 판정된 경우, 사용자가 별도 환경에서 직접 구현해야 합니다

---

## AI API 의존성

전체 기능을 사용하려면 AI API Key(OpenAI / Claude / Gemini 중 하나)가 필요합니다.

- API Key 없이도 Feature 분석, Align, Inspection, Evaluation은 정상 동작합니다
- 다음 기능은 AI API가 있어야 동작합니다:
  - Feature 분석 AI 요약
  - Align 전략 판단 (AI 폴백)
  - Failure 원인 분석 (AI 기반)
  - Feasibility EL/DL 판정 (AI 기반, 없으면 휴리스틱 폴백)
- API 호출 시 텍스트 데이터만 전송되며, 이미지는 외부로 전송되지 않습니다

---

## UI 관련

### StatCard에서 QLabel로의 마이그레이션 (Step 26)

Step 26 개발 중 커스텀 `StatCard` 위젯의 `paintEvent` 렌더링 문제가 발생했습니다.
`QTimer.singleShot`, `repaint()`, `update()` 등 다양한 방법을 시도했으나 근본적으로 해결되지 않아,
`StatCard`를 plain `QLabel`로 교체하여 해결했습니다. 현재 `ui/components/stat_card.py`는
대시보드 전용으로만 사용됩니다.

### QSS 글로벌 오버라이드 패턴 (Step 24)

PyQt6의 QSS(Qt Style Sheet)는 글로벌로 적용되어 특정 위젯에만 스타일을 적용하기 어려운 경우가 있습니다.
`objectName` 기반 선택자를 사용하여 우회했으나, 복잡한 위젯 트리에서는 예기치 않은 스타일 상속이
발생할 수 있습니다.

---

## 검사 제한 사항

- Inspection 엔진은 2D 이미지만 지원합니다 (3D 포인트 클라우드 미지원)
- ROI는 직사각형만 지원합니다 (원형, 다각형 ROI 미지원)
- 한 번에 하나의 검사 목적만 설정할 수 있습니다 (복합 검사 미지원)
- 실시간 카메라 입력은 지원하지 않습니다 (파일 기반 이미지만 지원)

---

## 내보내기 제한 사항

- PDF 내보내기 시 한글 폰트는 시스템에 설치된 폰트에 의존합니다
- 대용량 이미지(10,000x10,000 이상) 내보내기 시 메모리 사용량이 증가할 수 있습니다

---

## 플랫폼별 참고 사항

- macOS: PyInstaller 빌드 시 코드 서명이 필요할 수 있습니다
- Windows: 고DPI 디스플레이에서 UI 스케일링이 완벽하지 않을 수 있습니다
- Linux: Qt6 런타임 라이브러리가 시스템에 설치되어 있어야 합니다
