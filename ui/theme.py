"""
디자인 토큰 중앙 관리 모듈.

색상, 폰트, 간격 등 모든 디자인 상수를 한 곳에서 관리한다.
ui/style.py 의 Colors, Fonts 클래스를 재수출하면서
추가 토큰(간격, 폰트 크기, 반지름 등)을 정의한다.
"""

# 기존 Colors, Fonts 재수출 (style.py 가 canonical source)
from ui.style import Colors, Fonts  # noqa: F401


class Spacing:
    """간격(padding/margin) 상수."""
    XS = 4
    SM = 8
    MD = 16
    LG = 24
    XL = 32

    CARD_PADDING = 16
    SECTION_GAP = 16
    PAGE_MARGIN = 24


class FontSize:
    """폰트 크기 상수 (px 기준)."""
    SMALL = 11
    BODY = 13
    LABEL = 12
    SUBTITLE = 14
    TITLE = 16
    PAGE_TITLE = 20
    HERO = 28


class Radius:
    """border-radius 상수."""
    SM = 4
    MD = 6
    LG = 8
    PILL = 20


class Size:
    """위젯 크기 상수."""
    BUTTON_MIN_HEIGHT = 36
    BUTTON_PADDING_H = 16
    BUTTON_PADDING_V = 8
    ICON_SM = 16
    ICON_MD = 24
    ICON_LG = 32


# 빈 상태 메시지
class EmptyStateMessages:
    """각 페이지의 빈 상태 메시지."""
    DASHBOARD = "프로젝트를 시작하려면 이미지를 업로드하세요"
    ROI = "이미지를 먼저 업로드하세요"
    RESULTS = "분석을 실행하면 결과가 표시됩니다"
    UPLOAD = "이미지를 드래그하거나 클릭하여 업로드하세요"


# 툴팁 텍스트
class Tooltips:
    """주요 UI 요소 툴팁 텍스트."""
    # Settings page
    THRESHOLD = "분석 결과의 합격 기준점입니다. 높을수록 엄격한 판정을 합니다."
    OK_WEIGHT = "OK 이미지 통과율에 부여할 가중치 (0.0~1.0)"
    NG_WEIGHT = "NG 이미지 검출율에 부여할 가중치 (0.0~1.0)"
    MARGIN = "합격/불합격 경계 근처 경고를 표시할 마진 범위 (점수 단위)"
    NG_MIN_RECOMMENDED = "권장 최소 NG 이미지 수 — 이보다 적으면 경고 표시"
    NG_ABSOLUTE_MIN = "분석 가능한 절대 최소 NG 이미지 수"
    AI_TIMEOUT = "AI Provider 요청 타임아웃 (초 단위)"
    AI_RETRY = "AI Provider 요청 실패 시 재시도 횟수"

    # Toolbar
    API_STATUS = "현재 AI Provider 연결 상태"
    API_BUTTON = "API 키를 입력하여 AI 분석 기능을 활성화합니다"

    # Result tabs
    TAB_SUMMARY = "전체 분석 결과를 한눈에 요약합니다"
    TAB_FEATURE = "히스토그램, 노이즈, 에지, 형상 분석 상세 결과"
    TAB_ALIGN = "정렬 전략 및 변환 결과"
    TAB_INSPECTION = "검사 알고리즘 파라미터 및 평가 결과"
    TAB_FEASIBILITY = "기술 수준 판단 (Rule-based / EL / DL)"
    TAB_FAILURE = "FP/FN 실패 케이스 분석"

    # Workflow steps
    STEP_UPLOAD = "분석에 사용할 이미지를 업로드합니다 (Align OK, Inspection OK/NG)"
    STEP_ROI = "분석할 관심 영역(ROI)을 설정합니다"
    STEP_PURPOSE = "검사 유형과 목적을 입력합니다"
    STEP_ANALYSIS = "이미지 분석을 실행합니다"
    STEP_RESULTS = "분석 결과를 확인하고 내보냅니다"

    # Export dialog
    EXPORT_JSON = "분석 결과를 JSON 형식으로 저장합니다 (재사용 가능)"
    EXPORT_PDF = "분석 결과를 PDF 리포트로 저장합니다"
    EXPORT_IMAGES = "오버레이 이미지를 개별 파일로 저장합니다"
