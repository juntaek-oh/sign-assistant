#!/usr/bin/env python3
"""
수어 번역기 메인 윈도우
UI 클래스 정의
"""

import cv2
import numpy as np
import logging
from typing import List, Optional
from PyQt5.QtWidgets import QMainWindow, QWidget, QHBoxLayout
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QPixmap, QImage

# 내부 모듈
from modules.ui.components import StyleSheet, LeftPanel, RightPanel
from modules.core import CameraHandler, WorkerManager

logger = logging.getLogger(__name__)


class SignLanguageMainWindow(QMainWindow):
    """수어 번역 메인 윈도우"""

    def __init__(self, translator=None, config=None):
        """
        Args:
            translator: SignLanguageTranslator 인스턴스
            config: 설정 딕셔너리
        """
        super().__init__()

        # 외부 주입
        self.translator = translator
        self.config = config or {}

        # 컴포넌트 초기화
        self.camera_handler = None
        self.worker_manager = WorkerManager()

        # 상태 변수
        self.is_sign_mode = False
        self.is_speech_mode = False
        self.accumulated_words = []

        # UI 초기화
        self.init_ui()
        self.init_camera()
        self.connect_signals()

        logger.info("메인 윈도우 초기화 완료")

    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("수어 번역기")
        self.setFixedSize(800, 480)

        # 메인 위젯
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        # 레이아웃
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # 패널 추가
        self.left_panel = LeftPanel()
        self.right_panel = RightPanel()

        main_layout.addWidget(self.left_panel, 3)
        main_layout.addWidget(self.right_panel, 1)

        # 스타일 적용
        self.apply_styles()

    def apply_styles(self):
        """스타일 적용"""
        self.setStyleSheet(StyleSheet.get_main_style())

    def init_camera(self):
        """카메라 초기화"""
        self.camera_handler = CameraHandler()

        # 카메라 시그널 연결
        self.camera_handler.frame_ready.connect(self.update_camera_frame)
        self.camera_handler.sign_detected.connect(self.handle_sign_detection)
        self.camera_handler.sequence_status.connect(self.update_sequence_status)

    def connect_signals(self):
        """시그널 연결"""
        # 수어 버튼
        self.right_panel.sign_button.mode_toggled.connect(self.on_sign_mode_toggled)

        # 말하기 버튼
        self.right_panel.speech_button.mode_toggled.connect(self.on_speech_mode_toggled)

    @pyqtSlot(bool)
    def on_sign_mode_toggled(self, active: bool):
        """수어 모드 토글"""
        if active:
            self.start_sign_mode()
        else:
            self.stop_sign_mode()

    @pyqtSlot(bool)
    def on_speech_mode_toggled(self, active: bool):
        """말하기 모드 토글"""
        if active:
            self.start_speech_mode()
        else:
            self.stop_speech_mode()

    def start_sign_mode(self):
        """수어 모드 시작"""
        # 말하기 모드 중지
        if self.is_speech_mode:
            self.right_panel.speech_button.set_active(False)
            self.stop_speech_mode()

        # 카메라 시작
        if self.camera_handler and self.camera_handler.start_camera():
            self.is_sign_mode = True
            self.accumulated_words = []
            self.left_panel.text_area.update_text("시퀀스 단어 누적 중입니다...")
            logger.info("수어 모드 시작")
        else:
            self.left_panel.text_area.update_text("카메라를 시작할 수 없습니다.")
            self.right_panel.sign_button.set_active(False)

    def stop_sign_mode(self):
        """수어 모드 중지"""
        if self.camera_handler:
            self.camera_handler.stop_camera()

        self.is_sign_mode = False
        self.left_panel.camera_display.clear_display()

        # 누적된 단어로 문장 생성
        if self.accumulated_words:
            self.generate_sentence()
        else:
            self.left_panel.text_area.update_text("완성된 단어가 없습니다.")

        logger.info("수어 모드 중지")

    def start_speech_mode(self):
        """말하기 모드 시작"""
        # 수어 모드 중지
        if self.is_sign_mode:
            self.right_panel.sign_button.set_active(False)
            self.stop_sign_mode()

        # STT 시작
        if self.translator and self.translator.stt_module:
            if self.translator.start_stt_recording():
                self.is_speech_mode = True
                self.left_panel.text_area.update_text("음성 인식 중입니다...")
                logger.info("말하기 모드 시작")
            else:
                self.left_panel.text_area.update_text("음성 인식을 시작할 수 없습니다.")
                self.right_panel.speech_button.set_active(False)
        else:
            self.left_panel.text_area.update_text("음성 인식 모듈을 사용할 수 없습니다.")
            self.right_panel.speech_button.set_active(False)

    def stop_speech_mode(self):
        """말하기 모드 중지"""
        if self.translator:
            recognized_text = self.translator.stop_stt_recording()

            self.is_speech_mode = False

            if recognized_text:
                self.left_panel.text_area.update_text(f"음성 인식 결과: {recognized_text}")
            else:
                self.left_panel.text_area.update_text("음성을 인식하지 못했습니다.")

        logger.info("말하기 모드 중지")

    @pyqtSlot(np.ndarray)
    def update_camera_frame(self, frame):
        """카메라 프레임 업데이트"""
        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)

            pixmap = QPixmap.fromImage(qt_image)
            scaled_pixmap = pixmap.scaled(600, 320, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.left_panel.camera_display.setPixmap(scaled_pixmap)
        except Exception as e:
            logger.error(f"프레임 업데이트 오류: {e}")

    @pyqtSlot(str)
    def handle_sign_detection(self, detected_word: str):
        """수어 감지 처리"""
        if not self.is_sign_mode:
            return

        if detected_word == "RESET":
            # 리셋: 마지막 단어 삭제
            if self.accumulated_words:
                removed_word = self.accumulated_words.pop()
                logger.info(f"단어 삭제: {removed_word}")
                self.update_accumulated_text()
        else:
            # 완성된 단어 추가
            self.accumulated_words.append(detected_word)
            logger.info(f"완성된 단어 추가: {detected_word}")
            self.update_accumulated_text()

    @pyqtSlot(dict)
    def update_sequence_status(self, status: dict):
        """시퀀스 상태 업데이트"""
        if not self.is_sign_mode:
            return

        if status["status"] == "진행 중":
            sequence_info = f"시퀀스 진행 중: {status['sequence']} ({status['progress']})"
            current_text = self.left_panel.text_area.toPlainText()

            # 시퀀스 정보 업데이트
            lines = current_text.split('\n')
            if lines and "시퀀스 진행 중:" in lines[-1]:
                lines[-1] = sequence_info
            else:
                lines.append(sequence_info)

            self.left_panel.text_area.update_text('\n'.join(lines))

    def update_accumulated_text(self):
        """누적된 단어 텍스트 업데이트"""
        if self.accumulated_words:
            accumulated_text = ", ".join(self.accumulated_words)
            self.left_panel.text_area.update_text(f"완성 단어: {accumulated_text}")
        else:
            self.left_panel.text_area.update_text("완성된 단어가 누적되면 여기에 표시됩니다...")

    def generate_sentence(self):
        """누적된 단어로 문장 생성"""
        if not self.translator or not self.accumulated_words:
            return

        self.left_panel.text_area.update_text("문장 생성 중...")

        # 워커를 통한 문장 생성
        worker = self.worker_manager.create_sentence_worker(
            translator=self.translator,
            words=self.accumulated_words.copy(),
            on_ready=self.on_sentence_ready,
            on_error=self.on_sentence_error,
            on_progress=self.on_sentence_progress
        )

    @pyqtSlot(str)
    def on_sentence_ready(self, sentence: str):
        """문장 생성 완료"""
        accumulated_text = ", ".join(self.accumulated_words)
        final_text = f"완성 단어: {accumulated_text}\n\n완성 문장: {sentence}"
        self.left_panel.text_area.update_text(final_text)

        # 누적 단어 초기화
        self.accumulated_words = []
        logger.info(f"문장 생성 완료: {sentence}")

    @pyqtSlot(str)
    def on_sentence_error(self, error_msg: str):
        """문장 생성 오류"""
        self.left_panel.text_area.update_text(f"오류: {error_msg}")
        self.accumulated_words = []
        logger.error(f"문장 생성 오류: {error_msg}")

    @pyqtSlot(str)
    def on_sentence_progress(self, progress_msg: str):
        """문장 생성 진행 상황"""
        logger.debug(f"진행 상황: {progress_msg}")

    def closeEvent(self, event):
        """앱 종료 시 정리"""
        # 모드 중지
        if self.is_sign_mode:
            self.stop_sign_mode()

        if self.is_speech_mode:
            self.stop_speech_mode()

        # 워커 정리
        self.worker_manager.cleanup_all()

        logger.info("애플리케이션 종료")
        event.accept()