"""
Settings page for the Argos vision algorithm design application.

This module provides the interface for configuring application
settings and algorithm parameters.
"""

import os
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QScrollArea, QWidget, QSlider,
    QSpinBox, QLabel, QPushButton, QLineEdit, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from .base_page import BasePage, PageHeader
from ui.components.sidebar import PageID
from ui.components.section_card import SectionCard
from ui.components.toast import ToastMessage
from config.settings import Settings
from config.paths import SETTINGS_FILE
from config.constants import DEFAULT_SCORE_THRESHOLD


class SettingsPage(BasePage):
    """
    Settings page for application configuration.
    
    Provides controls for adjusting application settings,
    algorithm thresholds, and system preferences with validation
    and persistent storage.
    """
    
    settings_saved = pyqtSignal(object)  # Settings instance
    
    def __init__(self, parent=None):
        """Initialize the settings page."""
        super().__init__(PageID.SETTINGS, "설정", parent)
        
        self._settings = None
        self._is_dirty = False
        self._toast = None
        
    def setup_ui(self) -> None:
        """Setup the settings page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Page header
        self._header = PageHeader("설정", "분석 기준 및 시스템 설정을 관리합니다.")
        layout.addWidget(self._header)
        
        # Scrollable content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(24, 16, 24, 16)
        content_layout.setSpacing(16)
        
        # Analysis criteria section
        self._create_analysis_section(content_layout)
        
        # Sample criteria section
        self._create_sample_section(content_layout)
        
        # AI connection section
        self._create_ai_section(content_layout)
        
        # Save paths section
        self._create_paths_section(content_layout)
        
        # Action buttons
        self._create_action_buttons(content_layout)
        
        content_layout.addStretch()
        
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
        
        # Toast notifications
        self._toast = ToastMessage(self)
        
    def _create_analysis_section(self, parent_layout: QVBoxLayout) -> None:
        """Create analysis criteria section."""
        card = SectionCard("분석 기준")
        
        # Threshold slider with spinbox
        threshold_widget = QWidget()
        threshold_layout = QHBoxLayout(threshold_widget)
        threshold_layout.setContentsMargins(0, 0, 0, 0)
        threshold_layout.setSpacing(8)
        
        self._threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self._threshold_slider.setRange(50, 95)
        self._threshold_slider.setValue(int(DEFAULT_SCORE_THRESHOLD))
        self._threshold_slider.valueChanged.connect(self._on_threshold_changed)
        threshold_layout.addWidget(self._threshold_slider, 1)
        
        self._threshold_spinbox = QSpinBox()
        self._threshold_spinbox.setRange(50, 95)
        self._threshold_spinbox.setValue(int(DEFAULT_SCORE_THRESHOLD))
        self._threshold_spinbox.valueChanged.connect(self._on_threshold_spinbox_changed)
        threshold_layout.addWidget(self._threshold_spinbox)
        
        self._threshold_status_label = QLabel()
        threshold_layout.addWidget(self._threshold_status_label)
        self._update_threshold_status()
        
        card.add_row("임계값", threshold_widget)
        
        # OK weight slider
        ok_weight_widget = QWidget()
        ok_weight_layout = QHBoxLayout(ok_weight_widget)
        ok_weight_layout.setContentsMargins(0, 0, 0, 0)
        ok_weight_layout.setSpacing(8)
        
        self._ok_weight_slider = QSlider(Qt.Orientation.Horizontal)
        self._ok_weight_slider.setRange(0, 100)
        self._ok_weight_slider.setValue(50)
        self._ok_weight_slider.valueChanged.connect(self._on_ok_weight_changed)
        ok_weight_layout.addWidget(self._ok_weight_slider, 1)
        
        self._ok_weight_label = QLabel("0.5")
        ok_weight_layout.addWidget(self._ok_weight_label)
        
        card.add_row("OK 가중치", ok_weight_widget)
        
        # NG weight slider
        ng_weight_widget = QWidget()
        ng_weight_layout = QHBoxLayout(ng_weight_widget)
        ng_weight_layout.setContentsMargins(0, 0, 0, 0)
        ng_weight_layout.setSpacing(8)
        
        self._ng_weight_slider = QSlider(Qt.Orientation.Horizontal)
        self._ng_weight_slider.setRange(0, 100)
        self._ng_weight_slider.setValue(50)
        self._ng_weight_slider.valueChanged.connect(self._on_ng_weight_changed)
        ng_weight_layout.addWidget(self._ng_weight_slider, 1)
        
        self._ng_weight_label = QLabel("0.5")
        ng_weight_layout.addWidget(self._ng_weight_label)
        
        card.add_row("NG 가중치", ng_weight_widget)
        
        # Weight formula preview
        self._formula_label = QLabel()
        self._formula_label.setStyleSheet("color: #9E9E9E; font-style: italic;")
        self._update_formula_preview()
        card.add_widget(self._formula_label)
        
        # Margin slider with spinbox
        margin_widget = QWidget()
        margin_layout = QHBoxLayout(margin_widget)
        margin_layout.setContentsMargins(0, 0, 0, 0)
        margin_layout.setSpacing(8)
        
        self._margin_slider = QSlider(Qt.Orientation.Horizontal)
        self._margin_slider.setRange(5, 30)
        self._margin_slider.setValue(15)
        self._margin_slider.valueChanged.connect(self._on_margin_changed)
        margin_layout.addWidget(self._margin_slider, 1)
        
        self._margin_spinbox = QSpinBox()
        self._margin_spinbox.setRange(5, 30)
        self._margin_spinbox.setValue(15)
        self._margin_spinbox.valueChanged.connect(self._on_margin_spinbox_changed)
        margin_layout.addWidget(self._margin_spinbox)
        
        card.add_row("분리 마진", margin_widget)
        
        parent_layout.addWidget(card)
        
    def _create_sample_section(self, parent_layout: QVBoxLayout) -> None:
        """Create sample criteria section."""
        card = SectionCard("샘플 기준")
        
        # NG minimum recommended
        self._ng_min_recommended_spinbox = QSpinBox()
        self._ng_min_recommended_spinbox.setRange(1, 100)
        self._ng_min_recommended_spinbox.setValue(3)
        self._ng_min_recommended_spinbox.valueChanged.connect(self._on_value_changed)
        card.add_row("NG 최소 권장", self._ng_min_recommended_spinbox)
        
        # NG absolute minimum
        self._ng_absolute_min_spinbox = QSpinBox()
        self._ng_absolute_min_spinbox.setRange(1, 100)
        self._ng_absolute_min_spinbox.setValue(1)
        self._ng_absolute_min_spinbox.valueChanged.connect(self._on_value_changed)
        card.add_row("NG 절대 최소", self._ng_absolute_min_spinbox)
        
        parent_layout.addWidget(card)
        
    def _create_ai_section(self, parent_layout: QVBoxLayout) -> None:
        """Create AI connection section."""
        card = SectionCard("AI 연결")
        
        # AI timeout
        self._ai_timeout_spinbox = QSpinBox()
        self._ai_timeout_spinbox.setRange(1, 300)
        self._ai_timeout_spinbox.setValue(30)
        self._ai_timeout_spinbox.valueChanged.connect(self._on_value_changed)
        card.add_row("타임아웃(초)", self._ai_timeout_spinbox)
        
        # AI retry count
        self._ai_retry_spinbox = QSpinBox()
        self._ai_retry_spinbox.setRange(0, 10)
        self._ai_retry_spinbox.setValue(2)
        self._ai_retry_spinbox.valueChanged.connect(self._on_value_changed)
        card.add_row("재시도 횟수", self._ai_retry_spinbox)
        
        parent_layout.addWidget(card)
        
    def _create_paths_section(self, parent_layout: QVBoxLayout) -> None:
        """Create save paths section."""
        card = SectionCard("저장 경로")
        
        # Log directory
        log_dir_widget = QWidget()
        log_dir_layout = QHBoxLayout(log_dir_widget)
        log_dir_layout.setContentsMargins(0, 0, 0, 0)
        log_dir_layout.setSpacing(8)
        
        self._log_dir_edit = QLineEdit("logs/")
        self._log_dir_edit.setReadOnly(True)
        self._log_dir_edit.textChanged.connect(self._on_value_changed)
        log_dir_layout.addWidget(self._log_dir_edit, 1)
        
        log_dir_button = QPushButton("📁 변경")
        log_dir_button.clicked.connect(self._select_log_directory)
        log_dir_layout.addWidget(log_dir_button)
        
        card.add_row("로그 폴더", log_dir_widget)
        
        # Output directory
        output_dir_widget = QWidget()
        output_dir_layout = QHBoxLayout(output_dir_widget)
        output_dir_layout.setContentsMargins(0, 0, 0, 0)
        output_dir_layout.setSpacing(8)
        
        self._output_dir_edit = QLineEdit("output/")
        self._output_dir_edit.setReadOnly(True)
        self._output_dir_edit.textChanged.connect(self._on_value_changed)
        output_dir_layout.addWidget(self._output_dir_edit, 1)
        
        output_dir_button = QPushButton("📁 변경")
        output_dir_button.clicked.connect(self._select_output_directory)
        output_dir_layout.addWidget(output_dir_button)
        
        card.add_row("출력 폴더", output_dir_widget)
        
        parent_layout.addWidget(card)
        
    def _create_action_buttons(self, parent_layout: QVBoxLayout) -> None:
        """Create action buttons."""
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # Save button
        self._save_button = QPushButton("💾 저장")
        self._save_button.setObjectName("primaryBtn")
        self._save_button.clicked.connect(self._save_settings)
        button_layout.addWidget(self._save_button)
        
        # Reset button
        self._reset_button = QPushButton("🔄 기본값으로 초기화")
        self._reset_button.clicked.connect(self._reset_to_defaults)
        button_layout.addWidget(self._reset_button)
        
        parent_layout.addLayout(button_layout)
        
    def _on_threshold_changed(self, value: int) -> None:
        """Handle threshold slider change."""
        self._threshold_spinbox.blockSignals(True)
        self._threshold_spinbox.setValue(value)
        self._threshold_spinbox.blockSignals(False)
        self._update_threshold_status()
        self._on_value_changed()
        
    def _on_threshold_spinbox_changed(self, value: int) -> None:
        """Handle threshold spinbox change."""
        self._threshold_slider.blockSignals(True)
        self._threshold_slider.setValue(value)
        self._threshold_slider.blockSignals(False)
        self._update_threshold_status()
        self._on_value_changed()
        
    def _update_threshold_status(self) -> None:
        """Update threshold status label."""
        value = self._threshold_slider.value()
        if value < 60:
            text = "⚠️ 낮음"
            color = "#FFA726"  # amber
        elif value <= 80:
            text = "✅ 권장"
            color = "#66BB6A"  # green
        else:
            text = "🔒 엄격"
            color = "#42A5F5"  # blue
        
        self._threshold_status_label.setText(text)
        self._threshold_status_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        
    def _on_ok_weight_changed(self, value: int) -> None:
        """Handle OK weight slider change."""
        self._ng_weight_slider.blockSignals(True)
        self._ng_weight_slider.setValue(100 - value)
        self._ng_weight_slider.blockSignals(False)
        
        # Update labels
        self._ok_weight_label.setText(f"{value / 100:.1f}")
        self._ng_weight_label.setText(f"{(100 - value) / 100:.1f}")
        
        self._update_formula_preview()
        self._on_value_changed()
        
    def _on_ng_weight_changed(self, value: int) -> None:
        """Handle NG weight slider change."""
        self._ok_weight_slider.blockSignals(True)
        self._ok_weight_slider.setValue(100 - value)
        self._ok_weight_slider.blockSignals(False)
        
        # Update labels
        self._ng_weight_label.setText(f"{value / 100:.1f}")
        self._ok_weight_label.setText(f"{(100 - value) / 100:.1f}")
        
        self._update_formula_preview()
        self._on_value_changed()
        
    def _update_formula_preview(self) -> None:
        """Update weight formula preview."""
        w1 = self._ok_weight_slider.value() / 100.0
        w2 = self._ng_weight_slider.value() / 100.0
        self._formula_label.setText(f"score = (OK × {w1:.1f}) + (NG × {w2:.1f})")
        
    def _on_margin_changed(self, value: int) -> None:
        """Handle margin slider change."""
        self._margin_spinbox.blockSignals(True)
        self._margin_spinbox.setValue(value)
        self._margin_spinbox.blockSignals(False)
        self._on_value_changed()
        
    def _on_margin_spinbox_changed(self, value: int) -> None:
        """Handle margin spinbox change."""
        self._margin_slider.blockSignals(True)
        self._margin_slider.setValue(value)
        self._margin_slider.blockSignals(False)
        self._on_value_changed()
        
    def _select_log_directory(self) -> None:
        """Select log directory."""
        directory = QFileDialog.getExistingDirectory(
            self, 
            "로그 폴더 선택",
            self._log_dir_edit.text()
        )
        if directory:
            self._log_dir_edit.setText(directory)
            self._on_value_changed()
            
    def _select_output_directory(self) -> None:
        """Select output directory."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "출력 폴더 선택", 
            self._output_dir_edit.text()
        )
        if directory:
            self._output_dir_edit.setText(directory)
            self._on_value_changed()
            
    def _on_value_changed(self) -> None:
        """Handle any value change to mark as dirty."""
        self._is_dirty = True
        self._update_title()
        
    def _update_title(self) -> None:
        """Update page title to show dirty state."""
        base_title = "설정"
        if self._is_dirty:
            title = f"{base_title} *"
        else:
            title = base_title
        self._header.update_title(title)
        
    def _save_settings(self) -> None:
        """Save current settings."""
        try:
            current_settings = self.get_current_settings()
            current_settings.validate()
            current_settings.save(str(SETTINGS_FILE))
            
            self._is_dirty = False
            self._update_title()
            
            if self._toast:
                self._toast.show_success("설정이 저장되었습니다.")
            self.settings_saved.emit(current_settings)
            
        except ValueError as e:
            if self._toast:
                self._toast.show_error(f"설정 검증 실패: {str(e)}")
        except Exception as e:
            if self._toast:
                self._toast.show_error(f"저장 실패: {str(e)}")
            
    def _reset_to_defaults(self) -> None:
        """Reset all settings to defaults."""
        reply = QMessageBox.question(
            self,
            "기본값으로 초기화",
            "모든 설정을 기본값으로 초기화하시겠습니까?\n\n저장하려면 별도로 💾 저장을 클릭해야 합니다.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            default_settings = Settings.reset()
            self._load_settings_to_ui(default_settings)
            self._is_dirty = True
            self._update_title()
            
            if self._toast:
                self._toast.show_warning(
                    "기본값으로 초기화되었습니다. 저장하려면 💾 저장을 클릭하세요."
                )
            
    def load_settings(self) -> None:
        """Load settings from file and update UI."""
        try:
            if SETTINGS_FILE.exists():
                self._settings = Settings.load(str(SETTINGS_FILE))
            else:
                self._settings = Settings()
            
            self._load_settings_to_ui(self._settings)
            self._is_dirty = False
            self._update_title()
            
        except Exception as e:
            self._settings = Settings()
            self._load_settings_to_ui(self._settings)
            self._is_dirty = False
            self._update_title()
            if self._toast:
                self._toast.show_error(f"설정 로딩 실패, 기본값 사용: {str(e)}")
            
    def _load_settings_to_ui(self, settings: Settings) -> None:
        """Load settings values into UI widgets."""
        # Block all signals to prevent triggering dirty state
        widgets = [
            self._threshold_slider, self._threshold_spinbox,
            self._ok_weight_slider, self._ng_weight_slider,
            self._margin_slider, self._margin_spinbox,
            self._ng_min_recommended_spinbox, self._ng_absolute_min_spinbox,
            self._ai_timeout_spinbox, self._ai_retry_spinbox,
            self._log_dir_edit, self._output_dir_edit
        ]
        
        for widget in widgets:
            widget.blockSignals(True)
            
        try:
            # Load values
            threshold_value = int(settings.score_threshold)
            self._threshold_slider.setValue(threshold_value)
            self._threshold_spinbox.setValue(threshold_value)
            
            ok_weight_value = int(settings.w1 * 100)
            ng_weight_value = int(settings.w2 * 100)
            self._ok_weight_slider.setValue(ok_weight_value)
            self._ng_weight_slider.setValue(ng_weight_value)
            
            # Update weight labels
            self._ok_weight_label.setText(f"{settings.w1:.1f}")
            self._ng_weight_label.setText(f"{settings.w2:.1f}")
            
            margin_value = int(settings.margin_warning)
            self._margin_slider.setValue(margin_value)
            self._margin_spinbox.setValue(margin_value)
            
            self._ng_min_recommended_spinbox.setValue(settings.ng_minimum_recommended)
            self._ng_absolute_min_spinbox.setValue(settings.ng_absolute_minimum)
            
            self._ai_timeout_spinbox.setValue(settings.ai_timeout)
            self._ai_retry_spinbox.setValue(settings.ai_retry)
            
            self._log_dir_edit.setText(settings.log_dir)
            self._output_dir_edit.setText(settings.output_dir)
            
            # Update displays
            self._update_threshold_status()
            self._update_formula_preview()
            
        finally:
            # Re-enable signals
            for widget in widgets:
                widget.blockSignals(False)
                
    def get_current_settings(self) -> Settings:
        """Get current settings from UI widgets."""
        return Settings(
            score_threshold=float(self._threshold_slider.value()),
            margin_warning=float(self._margin_slider.value()),
            w1=float(self._ok_weight_slider.value()) / 100.0,
            w2=float(self._ng_weight_slider.value()) / 100.0,
            ng_minimum_recommended=self._ng_min_recommended_spinbox.value(),
            ng_absolute_minimum=self._ng_absolute_min_spinbox.value(),
            ai_timeout=self._ai_timeout_spinbox.value(),
            ai_retry=self._ai_retry_spinbox.value(),
            log_dir=self._log_dir_edit.text(),
            output_dir=self._output_dir_edit.text()
        )
        
    def showEvent(self, event) -> None:
        """Handle show event to load settings if not dirty."""
        super().showEvent(event)
        if not self._is_dirty:
            self.load_settings()