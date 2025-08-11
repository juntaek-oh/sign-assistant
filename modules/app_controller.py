#!/usr/bin/env python3
"""
애플리케이션 컨트롤러
환경 설정, 초기화 및 의존성 주입 관리
"""

import logging
import sys
from typing import Dict
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont

# 환경 설정
from dotenv import load_dotenv

# 내부 모듈
from modules.config import CONFIG, validate_environment
from modules.translation import SignLanguageTranslator
from modules.ui import SignLanguageMainWindow

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ApplicationController:
    """애플리케이션 전체 제어 클래스"""

    def __init__(self):
        """컨트롤러 초기화"""
        self.app = None
        self.window = None
        self.translator = None
        self.config = None

        logger.info("애플리케이션 컨트롤러 초기화")

    def initialize_environment(self) -> bool:
        """환경 초기화 및 검증"""
        try:
            # .env 파일 로드
            load_dotenv()

            # 설정 로드
            self.config = CONFIG

            # 환경 검증
            issues = validate_environment()
            if issues:
                logger.warning("환경 설정 문제 발견:")
                for issue in issues:
                    logger.warning(f"  - {issue}")

                # 중요한 문제가 있는지 확인
                critical_issues = [i for i in issues if "API" in i or "인증" in i]
                if critical_issues:
                    logger.error("중요한 환경 설정 문제로 인해 일부 기능이 제한될 수 있습니다.")
                    return False

            logger.info("환경 초기화 완료")
            return True

        except Exception as e:
            logger.error(f"환경 초기화 실패: {e}")
            return False

    def initialize_translator(self) -> bool:
        """번역기 초기화"""
        try:
            if not self.config:
                logger.error("설정이 로드되지 않았습니다.")
                return False

            self.translator = SignLanguageTranslator(
                openai_api_key=self.config['api']['openai_key'],
                google_credentials_path=self.config['api']['google_credentials'],
                cache_dir=self.config['directories']['cache']
            )

            logger.info("번역기 초기화 성공")
            return True

        except Exception as e:
            logger.error(f"번역기 초기화 실패: {e}")
            self.translator = None
            return False

    def initialize_ui(self) -> bool:
        """UI 초기화"""
        try:
            # Qt 애플리케이션 생성
            self.app = QApplication(sys.argv)

            # 폰트 설정
            font = QFont("Arial", 12)
            self.app.setFont(font)

            # 메인 윈도우 생성 (의존성 주입)
            self.window = SignLanguageMainWindow(
                translator=self.translator,
                config=self.config
            )

            logger.info("UI 초기화 성공")
            return True

        except Exception as e:
            logger.error(f"UI 초기화 실패: {e}")
            return False

    def check_system_requirements(self) -> Dict[str, bool]:
        """시스템 요구사항 확인"""
        requirements = {
            'camera': False,
            'microphone': False,
            'openai_api': False,
            'google_cloud': False,
            'yolo_model': False
        }

        # 카메라 확인
        try:
            import cv2
            cap = cv2.VideoCapture(0)
            if cap.isOpened():
                requirements['camera'] = True
                cap.release()
        except:
            pass

        # 마이크 확인
        try:
            import speech_recognition as sr
            sr.Microphone()
            requirements['microphone'] = True
        except:
            pass

        # API 키 확인
        if self.config:
            if self.config['api'].get('openai_key'):
                requirements['openai_api'] = True
            if self.config['api'].get('google_credentials'):
                requirements['google_cloud'] = True

        # YOLO 모델 확인
        try:
            import os
            if os.path.exists("models/best_1.pt"):
                requirements['yolo_model'] = True
        except:
            pass

        return requirements

    def print_startup_info(self):
        """시작 정보 출력"""
        print("=" * 60)
        print("수어 번역기 시스템")
        print("=" * 60)

        # 시스템 요구사항 체크
        requirements = self.check_system_requirements()

        print("\n시스템 상태:")
        for component, status in requirements.items():
            status_symbol = "✓" if status else "✗"
            component_name = {
                'camera': "카메라",
                'microphone': "마이크",
                'openai_api': "OpenAI API",
                'google_cloud': "Google Cloud",
                'yolo_model': "YOLO 모델"
            }.get(component, component)
            print(f"  [{status_symbol}] {component_name}")

        # 사용 가능한 기능 안내
        print("\n사용 가능한 기능:")
        if requirements['camera'] and requirements['yolo_model']:
            print("  • 수어 인식 (카메라)")
        if requirements['microphone'] and requirements['google_cloud']:
            print("  • 음성 인식 (마이크)")
        if requirements['openai_api']:
            print("  • 문장 생성")
        if requirements['google_cloud']:
            print("  • 음성 합성 (TTS)")

        print("\n시스템 준비 완료!\n")

    def run(self) -> int:
        """애플리케이션 실행"""
        try:
            # 환경 초기화
            if not self.initialize_environment():
                logger.warning("환경 초기화 실패 - 제한된 모드로 실행")

            # 번역기 초기화
            if not self.initialize_translator():
                logger.warning("번역기 초기화 실패 - 일부 기능 제한")

            # UI 초기화
            if not self.initialize_ui():
                logger.error("UI 초기화 실패 - 프로그램 종료")
                return 1

            # 시작 정보 출력
            self.print_startup_info()

            # 윈도우 표시
            self.window.show()

            # 이벤트 루프 실행
            return self.app.exec_()

        except Exception as e:
            logger.error(f"애플리케이션 실행 중 오류: {e}")
            return 1

    def cleanup(self):
        """정리 작업"""
        try:
            if self.window:
                self.window.close()

            if self.app:
                self.app.quit()

            logger.info("정리 작업 완료")

        except Exception as e:
            logger.error(f"정리 작업 중 오류: {e}")


class ApplicationFactory:
    """애플리케이션 팩토리 패턴"""

    @staticmethod
    def create_controller() -> ApplicationController:
        """컨트롤러 생성"""
        return ApplicationController()

    @staticmethod
    def create_test_controller() -> ApplicationController:
        """테스트용 컨트롤러 생성"""
        controller = ApplicationController()
        # 테스트 설정 적용
        controller.config = {
            'api': {
                'openai_key': 'test_key',
                'google_credentials': 'test_credentials'
            },
            'directories': {
                'cache': 'test_cache'
            }
        }
        return controller