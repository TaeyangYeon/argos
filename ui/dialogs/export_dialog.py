"""
Export dialog for selecting export path and options.

Provides a dialog to configure which export types (JSON, PDF, images)
to generate and where to save them.
"""

from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)
from PyQt6.QtCore import Qt

from ui.style import Colors, Fonts


class ExportDialog(QDialog):
    """Dialog for selecting export path and export options."""

    def __init__(self, parent=None) -> None:
        """Initialize the export dialog."""
        super().__init__(parent)
        self._selected_path: str = ""
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the dialog UI."""
        self.setWindowTitle("결과 내보내기")
        self.setFixedSize(480, 320)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {Colors.BG_PRIMARY};
                color: {Colors.TEXT_PRIMARY};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Title
        title = QLabel("결과 내보내기")
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        # Path selection row
        path_layout = QHBoxLayout()
        self._path_label = QLabel("저장 경로를 선택하세요")
        self._path_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                background-color: {Colors.BG_SECONDARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 4px;
                padding: 8px;
            }}
        """)
        self._path_label.setMinimumHeight(36)
        path_layout.addWidget(self._path_label, 1)

        browse_btn = QPushButton("찾아보기")
        browse_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.ACCENT};
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Colors.ACCENT_HOVER};
            }}
        """)
        browse_btn.clicked.connect(self._browse_path)
        path_layout.addWidget(browse_btn)
        layout.addLayout(path_layout)

        # Checkboxes
        checkbox_style = f"color: {Colors.TEXT_PRIMARY}; font-size: 14px;"

        self._json_checkbox = QCheckBox("JSON (분석 결과 데이터)")
        self._json_checkbox.setChecked(True)
        self._json_checkbox.setStyleSheet(checkbox_style)
        layout.addWidget(self._json_checkbox)

        self._pdf_checkbox = QCheckBox("PDF (분석 리포트)")
        self._pdf_checkbox.setChecked(True)
        self._pdf_checkbox.setStyleSheet(checkbox_style)
        layout.addWidget(self._pdf_checkbox)

        self._image_checkbox = QCheckBox("이미지 (오버레이 이미지)")
        self._image_checkbox.setChecked(True)
        self._image_checkbox.setStyleSheet(checkbox_style)
        layout.addWidget(self._image_checkbox)

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("취소")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_SECONDARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 4px;
                padding: 8px 20px;
            }}
            QPushButton:hover {{
                border-color: {Colors.ACCENT};
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        self._export_btn = QPushButton("내보내기")
        self._export_btn.setEnabled(False)
        self._export_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.ACCENT};
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Colors.ACCENT_HOVER};
            }}
            QPushButton:disabled {{
                background-color: {Colors.BG_SECONDARY};
                color: {Colors.TEXT_DISABLED};
            }}
        """)
        self._export_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self._export_btn)

        layout.addLayout(btn_layout)

    def _browse_path(self) -> None:
        """Open directory selection dialog."""
        path = QFileDialog.getExistingDirectory(self, "내보내기 경로 선택")
        if path:
            self._selected_path = path
            self._path_label.setText(path)
            self._path_label.setStyleSheet(f"""
                QLabel {{
                    color: {Colors.TEXT_PRIMARY};
                    background-color: {Colors.BG_SECONDARY};
                    border: 1px solid {Colors.ACCENT};
                    border-radius: 4px;
                    padding: 8px;
                }}
            """)
            self._export_btn.setEnabled(True)

    @property
    def selected_path(self) -> str:
        """Return the selected export path."""
        return self._selected_path

    @property
    def export_json(self) -> bool:
        """Return whether JSON export is selected."""
        return self._json_checkbox.isChecked()

    @property
    def export_pdf(self) -> bool:
        """Return whether PDF export is selected."""
        return self._pdf_checkbox.isChecked()

    @property
    def export_images(self) -> bool:
        """Return whether image export is selected."""
        return self._image_checkbox.isChecked()
