#!/usr/bin/env python3
"""
수어 번역기 메인 엔트리 포인트
"""

import sys
import argparse
import logging
from modules import ApplicationFactory  # 경로 변경!

# 로깅 설정
logger = logging.getLogger(__name__)


def parse_arguments():
    """명령줄 인자 파싱"""
    parser = argparse.ArgumentParser(
        description="수어 번역기 시스템",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python main.py                    # 일반 실행
  python main.py --debug            # 디버그 모드
  python main.py --no-camera        # 카메라 없이 실행
  python main.py --config custom.env # 커스텀 설정 파일
        """
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='디버그 모드 활성화'
    )

    parser.add_argument(
        '--no-camera',
        action='store_true',
        help='카메라 없이 실행 (음성 인식만)'
    )

    parser.add_argument(
        '--no-speech',
        action='store_true',
        help='음성 인식 없이 실행 (수어 인식만)'
    )

    parser.add_argument(
        '--config',
        type=str,
        default='.env',
        help='환경 설정 파일 경로 (기본값: .env)'
    )

    parser.add_argument(
        '--test',
        action='store_true',
        help='테스트 모드로 실행'
    )

    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO',
        help='로그 레벨 설정'
    )

    return parser.parse_args()


def setup_logging(level: str):
    """로깅 설정"""
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO

    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('sign_language_translator.log', encoding='utf-8')
        ]
    )

    logger.info(f"로깅 레벨: {level}")


def main():
    """메인 함수"""
    # 명령줄 인자 파싱
    args = parse_arguments()

    # 로깅 설정
    setup_logging(args.log_level)

    try:
        # 시작 배너
        print("\n")
        print("╔" + "═" * 58 + "╗")
        print("║" + " " * 18 + "수어 번역기 시스템" + " " * 18 + "║")
        print("╚" + "═" * 58 + "╝")
        print()

        # 컨트롤러 생성
        if args.test:
            logger.info("테스트 모드로 실행")
            controller = ApplicationFactory.create_test_controller()
        else:
            controller = ApplicationFactory.create_controller()

        # 옵션 적용
        if args.debug:
            logger.info("디버그 모드 활성화")
            # 디버그 설정 적용

        if args.no_camera:
            logger.info("카메라 비활성화")
            # 카메라 설정 비활성화

        if args.no_speech:
            logger.info("음성 인식 비활성화")
            # 음성 인식 설정 비활성화

        # 애플리케이션 실행
        exit_code = controller.run()

        # 정리
        controller.cleanup()

        # 종료 메시지
        if exit_code == 0:
            print("\n프로그램이 정상적으로 종료되었습니다.")
        else:
            print(f"\n프로그램이 오류 코드 {exit_code}로 종료되었습니다.")

        return exit_code

    except KeyboardInterrupt:
        print("\n\n사용자에 의해 프로그램이 중단되었습니다.")
        return 130  # 표준 KeyboardInterrupt 종료 코드

    except Exception as e:
        logger.error(f"예상치 못한 오류 발생: {e}", exc_info=True)
        print(f"\n오류가 발생했습니다: {e}")
        print("자세한 내용은 로그 파일을 확인하세요.")
        return 1


if __name__ == "__main__":
    sys.exit(main())