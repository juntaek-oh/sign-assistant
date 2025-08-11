"""
수어 번역기 모듈 패키지
"""

# 버전 정보
__version__ = "1.0.0"

# 주요 클래스 노출
from .app_controller import ApplicationController, ApplicationFactory
from .ui.main_window import SignLanguageMainWindow

__all__ = [
    'ApplicationController',
    'ApplicationFactory',
    'SignLanguageMainWindow'
]