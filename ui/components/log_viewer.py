"""
로그 뷰어 컴포넌트
- LogViewer: 분석 과정의 로그를 실시간으로 표시하는 위젯
"""

from datetime import datetime
from PyQt6.QtWidgets import QPlainTextEdit
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QTextCursor, QTextCharFormat, QColor

from ui.style import Colors, Fonts


class LogViewer(QPlainTextEdit):
    """분석 로그를 실시간으로 표시하는 뷰어"""
    
    # 로그 레벨별 색상
    LEVEL_COLORS = {
        "INFO": "#AAAAAA",
        "WARNING": "#FFA500",
        "ERROR": "#FF4444",
        "SUCCESS": "#44FF88"
    }
    
    MAX_LINES = 500  # 최대 보관 라인 수
    
    def __init__(self, parent=None):
        """
        로그 뷰어 초기화
        
        Args:
            parent: 부모 위젯
        """
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """UI 설정"""
        # 읽기 전용 설정
        self.setReadOnly(True)
        
        # 폰트 설정 (고정폭)
        font = QFont(Fonts.MONO_FONT, 11)
        self.setFont(font)
        
        # 스타일 설정
        self.setStyleSheet(f"""
            LogViewer {{
                background-color: {Colors.BG_DARK};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 8px;
                color: {Colors.TEXT_PRIMARY};
            }}
        """)
        
        # 줄바꿈 설정
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        
        # 초기 메시지
        self.append_info("로그 뷰어 준비됨")
    
    def append_log(self, level: str, message: str):
        """
        로그 메시지 추가
        
        Args:
            level: 로그 레벨 (INFO, WARNING, ERROR, SUCCESS)
            message: 로그 메시지
        """
        # 현재 시간 생성
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # 로그 엔트리 생성
        log_entry = f"[{timestamp}] [{level}] {message}"
        
        # 색상 설정
        color = self.LEVEL_COLORS.get(level, Colors.TEXT_PRIMARY)
        
        # 텍스트 커서 이동 (끝으로)
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)
        
        # 색상 포맷 설정
        char_format = QTextCharFormat()
        char_format.setForeground(QColor(color))
        
        # 텍스트 삽입
        cursor.insertText(log_entry + "\n", char_format)
        
        # 자동 스크롤
        self.ensureCursorVisible()
        
        # 최대 라인 수 제한
        self.limit_lines()
    
    def append_info(self, message: str):
        """
        INFO 레벨 로그 추가
        
        Args:
            message: 로그 메시지
        """
        self.append_log("INFO", message)
    
    def append_warning(self, message: str):
        """
        WARNING 레벨 로그 추가
        
        Args:
            message: 로그 메시지
        """
        self.append_log("WARNING", message)
    
    def append_error(self, message: str):
        """
        ERROR 레벨 로그 추가
        
        Args:
            message: 로그 메시지
        """
        self.append_log("ERROR", message)
    
    def append_success(self, message: str):
        """
        SUCCESS 레벨 로그 추가
        
        Args:
            message: 로그 메시지
        """
        self.append_log("SUCCESS", message)
    
    def clear_log(self):
        """로그 내용 지우기"""
        self.clear()
    
    def limit_lines(self):
        """최대 라인 수 제한"""
        document = self.document()
        
        # 현재 라인 수 확인
        if document.blockCount() > self.MAX_LINES:
            # 초과된 라인 수 계산
            excess_lines = document.blockCount() - self.MAX_LINES
            
            # 처음부터 초과된 라인 수만큼 삭제
            cursor = QTextCursor(document)
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            
            for _ in range(excess_lines):
                cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
                cursor.removeSelectedText()
                cursor.deleteChar()  # 개행 문자도 삭제
    
    def get_line_count(self) -> int:
        """
        현재 라인 수 반환
        
        Returns:
            현재 라인 수
        """
        return self.document().blockCount()