#!/usr/bin/env python3
"""
카메라 처리 모듈
카메라 스레드 및 프레임 처리 기능
"""

import cv2
import numpy as np
import time
import logging
from typing import Optional
from PyQt5.QtCore import QThread, pyqtSignal

from modules.core.sequence_manager import SequenceManager
from modules.core.sign_detector import SignDetector

logger = logging.getLogger(__name__)


class CameraHandler(QThread):
    """카메라 처리 스레드"""

    # 시그널 정의
    frame_ready = pyqtSignal(np.ndarray)  # 프레임 준비 완료
    sign_detected = pyqtSignal(str)  # 완성된 단어 감지
    sequence_status = pyqtSignal(dict)  # 시퀀스 상태 업데이트

    def __init__(self, model_path: str = "models/best_1.pt",
                 detection_interval: int = 30,
                 status_update_interval: int = 10):
        """
        Args:
            model_path: YOLO 모델 경로
            detection_interval: 수어 인식 프레임 간격
            status_update_interval: 상태 업데이트 프레임 간격
        """
        super().__init__()

        self.cap = None
        self.camera_id = -1
        self.is_running = False

        # 프레임 처리 간격
        self.detection_interval = detection_interval
        self.status_update_interval = status_update_interval

        # 모듈 초기화
        self.sequence_manager = SequenceManager()
        self.sign_detector = SignDetector(model_path=model_path)

        logger.info("카메라 핸들러 초기화 완료")

    def find_available_camera(self) -> int:
        """사용 가능한 카메라 자동 감지"""
        for camera_id in range(11):
            try:
                cap = cv2.VideoCapture(camera_id)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        cap.release()
                        logger.info(f"카메라 발견: ID {camera_id}")
                        return camera_id
                cap.release()
            except Exception as e:
                logger.debug(f"카메라 {camera_id} 확인 중 오류: {e}")
                continue

        logger.warning("사용 가능한 카메라를 찾을 수 없습니다")
        return -1

    def start_camera(self) -> bool:
        """카메라 시작"""
        try:
            self.camera_id = self.find_available_camera()
            if self.camera_id == -1:
                return False

            self.cap = cv2.VideoCapture(self.camera_id)
            if not self.cap.isOpened():
                return False

            # 카메라 설정
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(cv2.CAP_PROP_FPS, 15)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            self.is_running = True
            self.start()  # QThread 시작

            logger.info(f"카메라 시작 성공: ID {self.camera_id}")
            return True

        except Exception as e:
            logger.error(f"카메라 시작 실패: {e}")
            return False

    def stop_camera(self):
        """카메라 중지"""
        self.is_running = False

        # 상태 초기화
        self.sign_detector.reset_detection_state()
        self.sequence_manager.reset_sequence()

        if self.cap:
            self.cap.release()
            self.cap = None

        self.quit()
        self.wait()

        logger.info("카메라 중지")

    def run(self):
        """카메라 실행 루프"""
        frame_count = 0

        while self.is_running and self.cap:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.1)
                continue

            # 프레임 리사이즈
            frame = cv2.resize(frame, (640, 480))

            # 가이드 박스 추가
            self.add_guide_overlay(frame)

            # 수어 인식 (주기적으로)
            if frame_count % self.detection_interval == 0:
                self.process_sign_detection(frame)

            # 시퀀스 상태 업데이트 (주기적으로)
            if frame_count % self.status_update_interval == 0:
                status = self.sequence_manager.get_current_status()
                self.sequence_status.emit(status)

            # 프레임 전송
            self.frame_ready.emit(frame)

            frame_count += 1

            # FPS 조절
            time.sleep(1 / 15)

    def process_sign_detection(self, frame):
        """수어 감지 처리"""
        # 수어 감지
        detected_words = self.sign_detector.detect_signs(frame)

        if not detected_words:
            return

        # 중복 필터링
        filtered_words = self.sign_detector.filter_duplicate_detections(detected_words)

        # 각 단어 처리
        for raw_word in filtered_words:
            # 리셋 처리
            if raw_word == "리셋":
                self.sequence_manager.reset_sequence()
                self.sign_detected.emit("RESET")
                continue

            # 시퀀스 매니저를 통해 단어 처리
            completed_word = self.sequence_manager.process_word(raw_word)

            # 완성된 단어가 있으면 전송
            if completed_word:
                logger.info(f"완성된 단어 전송: {completed_word}")
                self.sign_detected.emit(completed_word)
                break  # 한 번에 하나의 완성된 단어만 처리

    def add_guide_overlay(self, frame):
        """프레임에 가이드 오버레이 추가"""
        h, w = frame.shape[:2]

        # 가이드 박스
        box_width = int(w * 0.8)
        box_height = int(h * 0.8)
        x1 = (w - box_width) // 2
        y1 = (h - box_height) // 2
        x2 = x1 + box_width
        y2 = y1 + box_height

        # 박스 그리기
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # 제목
        cv2.putText(frame, "Sign Language Recognition Area",
                    (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # 시퀀스 상태 표시
        status = self.sequence_manager.get_current_status()
        if status["status"] == "진행 중":
            status_text = f"Sequence: {status['sequence']} ({status['progress']})"
            cv2.putText(frame, status_text,
                        (x1, y2 + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

    def update_detection_settings(self, confidence_threshold: Optional[float] = None,
                                  word_cooldown: Optional[float] = None,
                                  detection_interval: Optional[int] = None):
        """감지 설정 업데이트"""
        if confidence_threshold is not None:
            self.sign_detector.update_confidence_threshold(confidence_threshold)

        if word_cooldown is not None:
            self.sign_detector.update_word_cooldown(word_cooldown)

        if detection_interval is not None and detection_interval > 0:
            self.detection_interval = detection_interval
            logger.info(f"감지 간격 업데이트: {detection_interval}프레임")