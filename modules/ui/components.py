#!/usr/bin/env python3
"""
UI 컴포넌트 모듈
재사용 가능한 UI 위젯 및 스타일
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont


class StyleSheet:
    """UI 스타일시트 관리"""

    @staticmethod
    def get_main_style():
        """메인 윈도우 스타일"""
        return """
            QMainWindow {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #667db6, stop: 1 #0082c8);
            }
        """

    @staticmethod
    def get_text_area_style():
        """텍스트 영역 스타일"""
        return """
            QTextEdit {
                border: 3px solid #34495e;
                border-radius: 12px;
                padding: 12px;
                background-color: #ecf0f1;
                font-family: 'Malgun Gothic', Arial, sans-serif;
                font-size: 18px;
                color: #2c3e50;
            }
        """

    @staticmethod
    def get_camera_label_style():
        """카메라 레이블 스타일"""
        return """
            QLabel {
                border: 3px solid #34495e;
                border-radius: 12px;
                background-color: #2c3e50;
                color: #ecf0f1;
                font-size: 16px;
                font-weight: bold;
                font-family: 'Malgun Gothic', Arial, sans-serif;
            }
        """

    @staticmethod
    def get_button_style(color_gradient: str):
        """버튼 스타일"""
        return f"""
            QPushButton {{
                background-color: qlineargradient({color_gradient});
                border: none;
                border-radius: 20px;
                font-family: 'Malgun Gothic', Arial, sans-serif;
                font-size: 18px;
                font-weight: bold;
                color: white;
            }}
            QPushButton:hover {{
                opacity: 0.9;
            }}
            QPushButton:pressed {{
                opacity: 0.8;
            }}
        """

    @staticmethod
    def get_sign_button_gradient(active: bool):
        """수어 버튼 그라디언트"""
        if active:
            return "x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #ff4757, stop: 1 #ff6b7a"
        else:
            return "x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #56ab2f, stop: 1 #a8e6cf"

    @staticmethod
    def get_speech_button_gradient(active: bool):
        """말하기 버튼 그라디언트"""
        if active:
            return "x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #ff4757, stop: 1 #ff6b7a"
        else:
            return "x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #ff6b6b, stop: 1 #ffa8a8"


class TranslationTextArea(QTextEdit):
    """번역 결과 표시용 텍스트 영역"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(600, 120)
        self.setReadOnly(True)
        self.setPlaceholderText("완성된 단어가 누적되면 여기에 표시됩니다...")
        self.setStyleSheet(StyleSheet.get_text_area_style())

    def update_text(self, text: str):
        """텍스트 업데이트"""
        self.setPlainText(text)

    def append_text(self, text: str):
        """텍스트 추가"""
        current = self.toPlainText()
        if current:
            self.setPlainText(f"{current}\n{text}")
        else:
            self.setPlainText(text)

    def clear_text(self):
        """텍스트 지우기"""
        self.clear()


class CameraDisplay(QLabel):
    """카메라 영상 표시용 레이블"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(600, 320)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(StyleSheet.get_camera_label_style())
        self.set_waiting_state()

    def set_waiting_state(self):
        """대기 상태 표시"""
        self.setText("카메라 대기 중\n\n수어하기 버튼을 눌러\n카메라를 시작하세요")

    def set_error_state(self, error_msg: str = "카메라 오류"):
        """오류 상태 표시"""
        self.setText(f"❌ {error_msg}")

    def clear_display(self):
        """디스플레이 초기화"""
        self.clear()
        self.set_waiting_state()


class ModeButton(QPushButton):
    """모드 전환 버튼"""

    mode_toggled = pyqtSignal(bool)  # 모드 변경 시그널

    def __init__(self, text: str, active_text: str, parent=None):
        super().__init__(text, parent)
        self.default_text = text
        self.active_text = active_text
        self.is_active = False
        self.setFixedSize(170, 210)

        # 클릭 이벤트 연결
        self.clicked.connect(self.toggle_mode)

    def toggle_mode(self):
        """모드 토글"""
        self.is_active = not self.is_active
        self.update_button_state()
        self.mode_toggled.emit(self.is_active)

    def set_active(self, active: bool):
        """활성 상태 설정"""
        self.is_active = active
        self.update_button_state()

    def update_button_state(self):
        """버튼 상태 업데이트"""
        if self.is_active:
            self.setText(self.active_text)
        else:
            self.setText(self.default_text)

    def reset(self):
        """버튼 초기화"""
        self.is_active = False
        self.update_button_state()


class SignModeButton(ModeButton):
    """수어 모드 버튼"""

    def __init__(self, parent=None):
        super().__init__("수어하기", "수어\n그만하기", parent)
        self.update_style()

    def update_button_state(self):
        """버튼 상태 업데이트"""
        super().update_button_state()
        self.update_style()

    def update_style(self):
        """스타일 업데이트"""
        gradient = StyleSheet.get_sign_button_gradient(self.is_active)
        self.setStyleSheet(StyleSheet.get_button_style(gradient))


class SpeechModeButton(ModeButton):
    """말하기 모드 버튼"""

    def __init__(self, parent=None):
        super().__init__("말하기", "말\n그만하기", parent)
        self.update_style()

    def update_button_state(self):
        """버튼 상태 업데이트"""
        super().update_button_state()
        self.update_style()

    def update_style(self):
        """스타일 업데이트"""
        gradient = StyleSheet.get_speech_button_gradient(self.is_active)
        self.setStyleSheet(StyleSheet.get_button_style(gradient))


class LeftPanel(QWidget):
    """왼쪽 패널 (텍스트 + 카메라)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        # 텍스트 영역
        self.text_area = TranslationTextArea()
        layout.addWidget(self.text_area)

        # 카메라 영역
        self.camera_display = CameraDisplay()
        layout.addWidget(self.camera_display)


class RightPanel(QWidget):
    """오른쪽 패널 (버튼들)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        # 수어하기 버튼
        self.sign_button = SignModeButton()
        layout.addWidget(self.sign_button)

        # 말하기 버튼
        self.speech_button = SpeechModeButton()
        layout.addWidget(self.speech_button)