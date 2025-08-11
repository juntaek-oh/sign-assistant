import os
import json
import logging
from typing import Optional, Dict, Any
import pygame
import io
import time
import hashlib
from pathlib import Path

try:
    from google.cloud import texttospeech
    GOOGLE_TTS_AVAILABLE = True
except ImportError:
    GOOGLE_TTS_AVAILABLE = False
    logging.warning("Google Cloud TTS not available")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TTSModule:
    """Google Cloud TTS 전용 텍스트 음성 변환 클래스"""
    
    def __init__(self, google_credentials_path: Optional[str] = None, cache_dir: str = "cache"):
        if not GOOGLE_TTS_AVAILABLE:
            raise ImportError("Google Cloud TTS를 사용하려면 'pip install google-cloud-texttospeech'를 설치하세요.")
        
        # 캐시 설정
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.audio_cache_dir = self.cache_dir / "tts_audio"
        self.audio_cache_dir.mkdir(exist_ok=True)
        self.cache_file = self.cache_dir / "tts_cache.json"
        
        self.cache = self._load_cache()
        self.cache_hits = 0
        self.total_requests = 0
        
        # pygame 초기화
        try:
            pygame.mixer.init()
        except Exception as e:
            logger.error(f"pygame 초기화 실패: {e}")
            raise
        
        # Google Cloud 인증 설정
        if google_credentials_path:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = google_credentials_path
        elif not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
            logger.warning("Google Cloud 인증 정보가 없습니다.")
        
        try:
            self.google_client = texttospeech.TextToSpeechClient()
            logger.info("Google Cloud TTS 초기화 완료")
        except Exception as e:
            logger.error(f"Google Cloud TTS 초기화 실패: {e}")
            raise
    
    def _load_cache(self) -> Dict[str, Any]:
        """캐시 파일 로드"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"TTS 캐시 로드 실패: {e}")
                return {}
        return {}
    
    def _save_cache(self):
        """캐시 파일 저장"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"TTS 캐시 저장 실패: {e}")
    
    def _get_cache_key(self, text: str, voice: str, speed: float, pitch: float) -> str:
        """캐시 키 생성"""
        key_data = {
            'text': text,
            'voice': voice,
            'speed': speed,
            'pitch': pitch
        }
        key_string = json.dumps(key_data, ensure_ascii=False, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def text_to_speech(self, text: str, voice: str = "ko-KR-Wavenet-A",
                      speed: float = 1.0, pitch: float = 0.0,
                      play_audio: bool = True, use_cache: bool = True) -> Optional[bytes]:
        """텍스트를 음성으로 변환"""
        if not text.strip():
            return None
        
        self.total_requests += 1
        
        # 캐시 확인
        cache_key = self._get_cache_key(text, voice, speed, pitch)
        if use_cache and cache_key in self.cache:
            cached_file = self.audio_cache_dir / f"{cache_key}.mp3"
            if cached_file.exists():
                self.cache_hits += 1
                with open(cached_file, 'rb') as f:
                    audio_data = f.read()
                
                if play_audio:
                    self._play_audio(audio_data)
                
                return audio_data
        
        # TTS 변환 실행
        try:
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            voice_params = texttospeech.VoiceSelectionParams(
                language_code="ko-KR",
                name=voice
            )
            
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=speed,
                pitch=pitch
            )
            
            response = self.google_client.synthesize_speech(
                input=synthesis_input,
                voice=voice_params,
                audio_config=audio_config
            )
            
            audio_data = response.audio_content
            
            # 캐시에 저장
            if use_cache and audio_data:
                cached_file = self.audio_cache_dir / f"{cache_key}.mp3"
                with open(cached_file, 'wb') as f:
                    f.write(audio_data)
                
                self.cache[cache_key] = {
                    'text': text,
                    'voice': voice,
                    'speed': speed,
                    'pitch': pitch,
                    'timestamp': time.time(),
                    'file_path': str(cached_file)
                }
                self._save_cache()
            
            if play_audio and audio_data:
                self._play_audio(audio_data)
            
            return audio_data
            
        except Exception as e:
            logger.error(f"TTS 변환 실패: {e}")
            return None
    
    def _play_audio(self, audio_data: bytes):
        """음성 데이터 재생"""
        try:
            audio_stream = io.BytesIO(audio_data)
            pygame.mixer.music.load(audio_stream)
            pygame.mixer.music.play()
            
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            
        except Exception as e:
            logger.error(f"오디오 재생 오류: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계 반환"""
        total_cache_size = 0
        
        for entry in self.cache.values():
            file_path = entry.get('file_path')
            if file_path and os.path.exists(file_path):
                total_cache_size += os.path.getsize(file_path)
        
        return {
            'total_entries': len(self.cache),
            'total_hits': self.cache_hits,
            'total_requests': self.total_requests,
            'hit_rate': (self.cache_hits / max(self.total_requests, 1)) * 100,
            'total_cache_size_mb': total_cache_size / (1024 * 1024)
        }
    
    def clear_cache(self):
        """캐시 초기화"""
        for cache_file in self.audio_cache_dir.glob("*.mp3"):
            try:
                cache_file.unlink()
            except Exception as e:
                logger.warning(f"캐시 파일 삭제 실패: {cache_file} - {e}")
        
        self.cache = {}
        self._save_cache()