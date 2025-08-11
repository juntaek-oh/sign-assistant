#!/usr/bin/env python3
"""
수어 인식 모듈
YOLO 모델을 사용한 수어 감지 기능
"""

import os
import cv2
import logging
import time
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)


class SignDetector:
    """YOLO 기반 수어 인식 클래스"""

    def __init__(self, model_path: str = "models/best_1.pt",
                 confidence_threshold: float = 0.5,
                 word_cooldown: float = 3.0):
        """
        Args:
            model_path: YOLO 모델 파일 경로
            confidence_threshold: 인식 신뢰도 임계값
            word_cooldown: 같은 단어 재감지 방지 시간
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.word_cooldown = word_cooldown
        self.model_input_size = (640, 480)

        # 단어 누적 관련 변수
        self.last_detected_word = ""
        self.last_detection_time = 0

        # 모델 클래스 매핑
        self.word_mapping = {
            0: {'korean': '구급차1/3', 'english': 'ambulance'},
            1: {'korean': '구급차2/3', 'english': 'ambulance'},
            2: {'korean': '구급차3/3', 'english': 'ambulance'},
            3: {'korean': '학교', 'english': 'school'},
            4: {'korean': '쓰러지다1/2', 'english': 'collapse'},
            5: {'korean': '쓰러지다2/2', 'english': 'collapse'},
            6: {'korean': '아프다', 'english': 'hurt'},
            7: {'korean': '가다', 'english': 'go'},
            8: {'korean': '나', 'english': 'me'},
            9: {'korean': '사람1/2', 'english': 'person'},
            10: {'korean': '사람2/2', 'english': 'person'},
            11: {'korean': '빨리', 'english': 'quickly'},
            12: {'korean': '병원', 'english': 'hospital'},
            13: {'korean': '구조', 'english': 'rescue'},
            14: {'korean': '리셋', 'english': 'reset'}
        }

        # YOLO 모델
        self.model = None
        self.load_model()

    def load_model(self):
        """YOLO 모델 로드"""
        try:
            from ultralytics import YOLO

            if not os.path.exists(self.model_path):
                logger.error(f"모델 파일이 없습니다: {self.model_path}")
                self.model = None
                return False

            self.model = YOLO(self.model_path)
            logger.info(f"YOLO 모델 로드 완료: {self.model_path}")
            logger.info(f"클래스 개수: {len(self.word_mapping)}개")
            return True

        except ImportError:
            logger.error("ultralytics 패키지가 설치되지 않았습니다. pip install ultralytics")
            self.model = None
            return False
        except Exception as e:
            logger.error(f"YOLO 모델 로드 실패: {e}")
            self.model = None
            return False

    def detect_signs(self, frame) -> List[str]:
        """
        프레임에서 수어 인식

        Args:
            frame: 비디오 프레임

        Returns:
            감지된 수어 단어 리스트
        """
        if self.model is None:
            return []

        try:
            # 모델 입력 크기로 리사이즈
            model_input = cv2.resize(frame, self.model_input_size)

            # YOLO 추론
            results = self.model(model_input, conf=self.confidence_threshold, verbose=False)

            detected_words = []
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        class_id = int(box.cls[0])
                        confidence_score = float(box.conf[0])

                        if class_id in self.word_mapping:
                            korean_word = self.word_mapping[class_id]['korean']
                            detected_words.append(korean_word)

                            logger.debug(f"수어 인식: {korean_word} (신뢰도: {confidence_score:.3f})")

            return detected_words

        except Exception as e:
            logger.error(f"수어 인식 오류: {e}")
            return []

    def filter_duplicate_detections(self, detected_words: List[str]) -> List[str]:
        """
        중복 감지 필터링

        Args:
            detected_words: 감지된 단어 리스트

        Returns:
            필터링된 단어 리스트
        """
        current_time = time.time()
        filtered_words = []

        for word in detected_words:
            # 중복 방지: 같은 단어가 cooldown 시간 내에 연속으로 감지되는 것 방지
            if (word == self.last_detected_word and
                    current_time - self.last_detection_time < self.word_cooldown):
                continue

            filtered_words.append(word)
            self.last_detected_word = word
            self.last_detection_time = current_time

        return filtered_words

    def reset_detection_state(self):
        """감지 상태 초기화"""
        self.last_detected_word = ""
        self.last_detection_time = 0
        logger.info("감지 상태 초기화")

    def update_confidence_threshold(self, threshold: float):
        """신뢰도 임계값 업데이트"""
        if 0.0 <= threshold <= 1.0:
            self.confidence_threshold = threshold
            logger.info(f"신뢰도 임계값 업데이트: {threshold}")

    def update_word_cooldown(self, cooldown: float):
        """중복 방지 시간 업데이트"""
        if cooldown > 0:
            self.word_cooldown = cooldown
            logger.info(f"중복 방지 시간 업데이트: {cooldown}초")

    def get_word_mapping(self) -> Dict:
        """단어 매핑 정보 반환"""
        return self.word_mapping.copy()

    def add_word_mapping(self, class_id: int, korean: str, english: str):
        """새로운 단어 매핑 추가"""
        self.word_mapping[class_id] = {
            'korean': korean,
            'english': english
        }
        logger.info(f"새 단어 매핑 추가: {class_id} → {korean}/{english}")