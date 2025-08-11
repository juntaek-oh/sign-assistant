#!/usr/bin/env python3
"""
시퀀스 관리 모듈
수어 단어의 시퀀스를 관리하고 완성된 단어를 반환
"""

import time
import logging
from typing import Optional, Dict, Tuple

logger = logging.getLogger(__name__)


class SequenceManager:
    """수어 시퀀스 관리 클래스"""

    def __init__(self, sequence_timeout: float = 10.0):
        """
        Args:
            sequence_timeout: 시퀀스 타임아웃 시간 (초)
        """
        # 시퀀스 정의: {단어_기본명: {총_단계수, 완성된_단어명}}
        self.sequence_definitions = {
            '구급차': {'total_steps': 3, 'completed_word': '구급차'},
            '쓰러지다': {'total_steps': 2, 'completed_word': '쓰러지다'},
            '사람': {'total_steps': 2, 'completed_word': '사람'}
        }

        # 현재 진행 중인 시퀀스 상태
        self.current_sequence = None  # 현재 진행 중인 시퀀스의 기본명
        self.current_step = 0  # 현재 단계 (1부터 시작)
        self.sequence_timeout = sequence_timeout  # 시퀀스 타임아웃
        self.last_sequence_time = 0  # 마지막 시퀀스 업데이트 시간

        logger.info(f"시퀀스 관리자 초기화 완료 (타임아웃: {sequence_timeout}초)")

    def parse_word(self, word: str) -> Tuple[str, int, bool]:
        """
        단어를 파싱하여 기본명, 단계, 시퀀스 여부 반환

        Args:
            word: 입력 단어 (예: "구급차1/3", "학교")

        Returns:
            (기본명, 단계, 시퀀스_여부)
            예: ("구급차", 1, True) 또는 ("학교", 0, False)
        """
        # 시퀀스 패턴 확인 (예: "구급차1/3")
        if '/' in word:
            try:
                # "구급차1/3" → "구급차", "1", "3"
                base_with_step = word.split('/')[0]  # "구급차1"
                total_steps = int(word.split('/')[1])  # "3"

                # 숫자 제거하여 기본명 추출
                base_name = ''.join([c for c in base_with_step if not c.isdigit()])  # "구급차"
                step_num = int(''.join([c for c in base_with_step if c.isdigit()]))  # 1

                return base_name, step_num, True

            except (ValueError, IndexError):
                # 파싱 실패 시 단일 단어로 처리
                return word, 0, False
        else:
            # 단일 단어 (예: "학교", "아프다")
            return word, 0, False

    def process_word(self, word: str) -> Optional[str]:
        """
        단어를 처리하고 완성된 단어 반환

        Args:
            word: 감지된 수어 단어

        Returns:
            완성된 단어 (시퀀스 완성 시) 또는 단일 단어 또는 None
        """
        current_time = time.time()

        # 시퀀스 타임아웃 체크
        if (self.current_sequence and
                current_time - self.last_sequence_time > self.sequence_timeout):
            logger.info(f"시퀀스 타임아웃: {self.current_sequence} (단계: {self.current_step})")
            self.reset_sequence()

        # 단어 파싱
        base_name, step_num, is_sequence = self.parse_word(word)

        # 단일 단어인 경우
        if not is_sequence:
            if self.current_sequence:
                logger.info(f"시퀀스 중단: {self.current_sequence} → 단일 단어: {word}")
                self.reset_sequence()
            return word

        # 시퀀스 단어인 경우
        if base_name not in self.sequence_definitions:
            logger.warning(f"알 수 없는 시퀀스: {base_name}")
            return None

        sequence_def = self.sequence_definitions[base_name]

        # 새로운 시퀀스 시작인지 확인
        if self.current_sequence != base_name:
            if step_num == 1:
                # 새 시퀀스 시작
                logger.info(f"새 시퀀스 시작: {base_name} (1/{sequence_def['total_steps']})")
                self.current_sequence = base_name
                self.current_step = 1
                self.last_sequence_time = current_time
                return None  # 아직 완성되지 않음
            else:
                # 중간부터 시작하는 경우 무시
                logger.info(f"시퀀스 중간 단계 무시: {word}")
                return None

        # 기존 시퀀스 진행 중
        expected_step = self.current_step + 1

        if step_num == expected_step:
            # 올바른 다음 단계
            self.current_step = step_num
            self.last_sequence_time = current_time

            logger.info(f"시퀀스 진행: {base_name} ({step_num}/{sequence_def['total_steps']})")

            # 시퀀스 완성 체크
            if step_num == sequence_def['total_steps']:
                completed_word = sequence_def['completed_word']
                logger.info(f"시퀀스 완성: {base_name} → {completed_word}")
                self.reset_sequence()
                return completed_word

            return None  # 아직 완성되지 않음

        elif step_num == self.current_step:
            # 같은 단계 반복 (무시)
            logger.debug(f"같은 단계 반복 무시: {word}")
            return None

        else:
            # 잘못된 순서
            logger.warning(f"잘못된 시퀀스 순서: {word} (예상: {base_name}{expected_step})")
            self.reset_sequence()

            # 1단계인 경우 새 시퀀스로 시작
            if step_num == 1:
                self.current_sequence = base_name
                self.current_step = 1
                self.last_sequence_time = current_time
                logger.info(f"새 시퀀스 재시작: {base_name}")

            return None

    def reset_sequence(self):
        """현재 시퀀스 초기화"""
        if self.current_sequence:
            logger.info(f"시퀀스 리셋: {self.current_sequence}")
        self.current_sequence = None
        self.current_step = 0
        self.last_sequence_time = 0

    def get_current_status(self) -> Dict:
        """현재 시퀀스 상태 반환"""
        if not self.current_sequence:
            return {"status": "대기 중"}

        sequence_def = self.sequence_definitions[self.current_sequence]
        return {
            "status": "진행 중",
            "sequence": self.current_sequence,
            "current_step": self.current_step,
            "total_steps": sequence_def['total_steps'],
            "progress": f"{self.current_step}/{sequence_def['total_steps']}"
        }

    def add_sequence_definition(self, base_name: str, total_steps: int, completed_word: str):
        """새로운 시퀀스 정의 추가"""
        self.sequence_definitions[base_name] = {
            'total_steps': total_steps,
            'completed_word': completed_word
        }
        logger.info(f"새 시퀀스 정의 추가: {base_name} ({total_steps}단계) → {completed_word}")

    def remove_sequence_definition(self, base_name: str):
        """시퀀스 정의 제거"""
        if base_name in self.sequence_definitions:
            del self.sequence_definitions[base_name]
            logger.info(f"시퀀스 정의 제거: {base_name}")