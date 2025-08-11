import os
from dotenv import load_dotenv

load_dotenv()

# API 키 및 인증 설정
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'google-credentials.json')

# Google Cloud TTS 설정
GOOGLE_TTS_CONFIG = {
    'default_voice': "ko-KR-Wavenet-A",
    'default_speaking_rate': 1.0,
    'default_pitch': 0.0,
    'audio_encoding': 'MP3',
    
    'available_voices': {
        "ko-KR-Wavenet-A": {"gender": "female", "type": "wavenet"},
        "ko-KR-Wavenet-B": {"gender": "female", "type": "wavenet"},
        "ko-KR-Wavenet-C": {"gender": "male", "type": "wavenet"},
        "ko-KR-Wavenet-D": {"gender": "male", "type": "wavenet"},
        "ko-KR-Neural2-A": {"gender": "female", "type": "neural2"},
        "ko-KR-Neural2-B": {"gender": "female", "type": "neural2"},
        "ko-KR-Neural2-C": {"gender": "male", "type": "neural2"},
        "ko-KR-Standard-A": {"gender": "female", "type": "standard"},
        "ko-KR-Standard-B": {"gender": "female", "type": "standard"},
        "ko-KR-Standard-C": {"gender": "male", "type": "standard"},
        "ko-KR-Standard-D": {"gender": "male", "type": "standard"}
    }
}

# Google Cloud STT 설정
GOOGLE_STT_CONFIG = {
    'language_code': 'ko-KR',
    'model': 'latest_long',
    'use_enhanced': True,
    'enable_automatic_punctuation': True,
    'profanity_filter': False
}

# 파일 및 디렉토리 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, "cache")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

for directory in [CACHE_DIR, LOGS_DIR]:
    os.makedirs(directory, exist_ok=True)

# 설정 내보내기
CONFIG = {
    'api': {
        'openai_key': OPENAI_API_KEY,
        'google_credentials': GOOGLE_APPLICATION_CREDENTIALS
    },
    'tts': {
        'google_config': GOOGLE_TTS_CONFIG
    },
    'stt': {
        'google_config': GOOGLE_STT_CONFIG
    },
    'directories': {
        'base': BASE_DIR,
        'cache': CACHE_DIR,
        'logs': LOGS_DIR
    }
}

def validate_environment():
    """환경 설정 유효성 검사"""
    issues = []
    
    if not OPENAI_API_KEY:
        issues.append("OPENAI_API_KEY가 설정되지 않았습니다.")
    
    if not GOOGLE_APPLICATION_CREDENTIALS:
        issues.append("GOOGLE_APPLICATION_CREDENTIALS가 설정되지 않았습니다.")
    elif not os.path.exists(GOOGLE_APPLICATION_CREDENTIALS):
        issues.append(f"Google Cloud 인증 파일을 찾을 수 없습니다: {GOOGLE_APPLICATION_CREDENTIALS}")
    
    return issues