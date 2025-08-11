import os
import logging
import json
import time
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from modules.translation.sentence_generator import SentenceGenerator
from modules.translation.tts_module import TTSModule
from modules.translation.stt_module import STTModule

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SignLanguageTranslator:
    """통합 수어 번역 시스템"""
    
    def __init__(self, 
                 openai_api_key: Optional[str] = None,
                 google_credentials_path: Optional[str] = None,
                 cache_dir: str = "cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        self.history_file = self.cache_dir / "translation_history.json"
        self.translation_history = self._load_translation_history()
        
        # API 키 및 인증 설정
        self.openai_api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        self.google_credentials_path = google_credentials_path or os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        
        logger.info("수어 번역 시스템 초기화 중...")
        
        # 문장 생성기 초기화 (OpenAI)
        try:
            self.sentence_generator = SentenceGenerator(
                api_key=self.openai_api_key,
                cache_dir=cache_dir
            )
            logger.info("문장 생성기 초기화 완료")
        except Exception as e:
            logger.error(f"문장 생성기 초기화 실패: {e}")
            raise
        
        # TTS 모듈 초기화 (Google Cloud)
        try:
            self.tts_module = TTSModule(
                google_credentials_path=google_credentials_path,
                cache_dir=cache_dir
            )
            logger.info("TTS 모듈 초기화 완료")
        except Exception as e:
            logger.error(f"TTS 모듈 초기화 실패: {e}")
            raise
        
        # STT 모듈 초기화 (Google Cloud)
        self.stt_module = None
        try:
            self.stt_module = STTModule(
                credentials_path=google_credentials_path
            )
            logger.info("STT 모듈 초기화 완료")
        except Exception as e:
            logger.warning(f"STT 모듈 초기화 실패: {e}")
        
        # 기본 설정
        self.default_voice = "ko-KR-Wavenet-A"
        self.default_speed = 1.0
        self.default_pitch = 0.0
        
        # 통계
        self.session_translations = 0
        self.session_start_time = time.time()
        
        logger.info("수어 번역 시스템 초기화 완료")
    
    def _load_translation_history(self) -> List[Dict[str, Any]]:
        """번역 이력 로드"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"번역 이력 로드 실패: {e}")
                return []
        return []
    
    def _save_translation_history(self):
        """번역 이력 저장"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.translation_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"번역 이력 저장 실패: {e}")
    
    def translate_sign_to_speech(self, 
                                sign_words: List[str],
                                context: Optional[str] = None,
                                voice: Optional[str] = None,
                                speed: float = None,
                                pitch: float = None,
                                play_audio: bool = True,
                                use_cache: bool = True) -> Dict[str, Any]:
        """수어를 음성으로 번역"""
        self.session_translations += 1
        start_time = time.time()
        
        # 기본값 설정
        voice = voice or self.default_voice
        speed = speed if speed is not None else self.default_speed
        pitch = pitch if pitch is not None else self.default_pitch
        
        result = {
            'session_id': self.session_translations,
            'timestamp': datetime.now().isoformat(),
            'input': {
                'sign_words': sign_words,
                'context': context
            },
            'output': {
                'sentence': None,
                'audio_generated': False,
                'audio_played': False
            },
            'settings': {
                'voice': voice,
                'speed': speed,
                'pitch': pitch
            },
            'performance': {
                'sentence_generation_time': 0,
                'tts_generation_time': 0,
                'total_time': 0
            },
            'success': False,
            'error': None
        }
        
        try:
            # 1. 문장 생성
            sentence_start = time.time()
            sentence = self.sentence_generator.generate_sentence(
                words=sign_words,
                context=context,
                use_cache=use_cache
            )
            sentence_end = time.time()
            
            result['performance']['sentence_generation_time'] = sentence_end - sentence_start
            
            if not sentence:
                raise ValueError("문장 생성 실패")
            
            result['output']['sentence'] = sentence
            
            # 2. TTS 변환
            tts_start = time.time()
            audio_data = self.tts_module.text_to_speech(
                text=sentence,
                voice=voice,
                speed=speed,
                pitch=pitch,
                play_audio=play_audio,
                use_cache=use_cache
            )
            tts_end = time.time()
            
            result['performance']['tts_generation_time'] = tts_end - tts_start
            
            if audio_data:
                result['output']['audio_generated'] = True
                result['output']['audio_played'] = play_audio
            
            # 3. 성공 처리
            result['success'] = True
            result['performance']['total_time'] = time.time() - start_time
            
            # 4. 이력에 추가
            self.translation_history.append(result)
            self._save_translation_history()
            
            logger.info(f"번역 완료: {' + '.join(sign_words)} → {sentence}")
            
        except Exception as e:
            result['error'] = str(e)
            result['performance']['total_time'] = time.time() - start_time
            logger.error(f"번역 실패: {e}")
        
        return result
    
    def start_stt_recording(self) -> bool:
        """STT 녹음 시작 (토글 ON)"""
        if not self.stt_module:
            logger.error("STT 모듈이 초기화되지 않았습니다.")
            return False
        
        return self.stt_module.start_recording()
    
    def stop_stt_recording(self) -> Optional[str]:
        """STT 녹음 중지 및 텍스트 변환 (토글 OFF)"""
        if not self.stt_module:
            logger.error("STT 모듈이 초기화되지 않았습니다.")
            return None
        
        return self.stt_module.stop_recording()
    
    def is_stt_recording(self) -> bool:
        """STT 녹음 상태 확인"""
        if not self.stt_module:
            return False
        
        return self.stt_module.is_recording_active()
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """종합 통계 반환"""
        session_time = time.time() - self.session_start_time
        
        successful_translations = sum(1 for item in self.translation_history if item['success'])
        
        return {
            'session': {
                'duration_seconds': session_time,
                'total_translations': len(self.translation_history),
                'successful_translations': successful_translations,
                'success_rate': (successful_translations / max(len(self.translation_history), 1)) * 100,
                'session_translations': self.session_translations
            },
            'sentence_generator': self.sentence_generator.get_cache_stats(),
            'tts': self.tts_module.get_cache_stats(),
            'stt': self.stt_module.get_stats() if self.stt_module else None,
            'cache_directory': str(self.cache_dir)
        }
    
    def export_translation_history(self, output_file: Optional[str] = None) -> str:
        """번역 이력을 파일로 내보내기"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"translation_export_{timestamp}.json"
        
        output_path = self.cache_dir / output_file
        
        export_data = {
            'export_info': {
                'timestamp': datetime.now().isoformat(),
                'total_translations': len(self.translation_history),
                'session_info': self.get_comprehensive_stats()['session']
            },
            'translation_history': self.translation_history
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"번역 이력 내보내기 완료: {output_path}")
        return str(output_path)
    
    def clear_all_cache(self):
        """모든 캐시 초기화"""
        logger.info("모든 캐시 초기화 중...")
        
        self.sentence_generator.clear_cache()
        self.tts_module.clear_cache()
        
        self.translation_history = []
        self._save_translation_history()
        
        logger.info("모든 캐시 초기화 완료")