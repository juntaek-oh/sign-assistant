import speech_recognition as sr
import logging
import time
from typing import Optional, Dict, Any
import threading
import os
import io

try:
    from google.cloud import speech
    GOOGLE_CLOUD_AVAILABLE = True
except ImportError:
    GOOGLE_CLOUD_AVAILABLE = False
    logging.warning("Google Cloud Speech not available")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class STTModule:
    """Google Cloud Speech-to-Text 전용 음성 인식 모듈 (토글 방식)"""
    
    def __init__(self, credentials_path: Optional[str] = None, language: str = 'ko-KR'):
        if not GOOGLE_CLOUD_AVAILABLE:
            raise ImportError("Google Cloud STT를 사용하려면 'pip install google-cloud-speech'를 설치하세요.")
        
        self.language = language
        
        # Google Cloud 인증 설정
        if credentials_path:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
        elif not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
            logger.warning("Google Cloud 인증 정보가 없습니다.")
        
        try:
            self.google_client = speech.SpeechClient()
            
            self.google_config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code=language,
                enable_automatic_punctuation=True,
                model='latest_long',
                use_enhanced=True
            )
            logger.info("Google Cloud STT 초기화 완료")
        except Exception as e:
            logger.error(f"Google Cloud STT 초기화 실패: {e}")
            raise
        
        # Speech Recognition 설정 (마이크 입력용)
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        self.recognizer.energy_threshold = 2000
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        self.recognizer.phrase_threshold = 0.3
        
        # 토글 모드 상태
        self.is_recording = False
        self.recording_thread = None
        self.accumulated_audio = []
        self.recording_lock = threading.Lock()
        
        # 통계
        self.recognition_count = 0
        self.successful_recognitions = 0
        
        self._check_microphone()
        
        logger.info("STT 모듈 초기화 완료 (토글 방식)")
    
    def _check_microphone(self):
        """마이크 연결 확인"""
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
        except Exception as e:
            logger.error(f"마이크 연결 오류: {e}")
            raise Exception("마이크를 찾을 수 없습니다.")
    
    def start_recording(self):
        """음성 녹음 시작 (토글 ON)"""
        if self.is_recording:
            return False
        
        logger.info("음성 녹음 시작")
        self.is_recording = True
        self.accumulated_audio = []
        
        self.recording_thread = threading.Thread(target=self._recording_worker)
        self.recording_thread.daemon = True
        self.recording_thread.start()
        
        return True
    
    def stop_recording(self) -> Optional[str]:
        """음성 녹음 중지 및 텍스트 변환 (토글 OFF)"""
        if not self.is_recording:
            return None
        
        logger.info("음성 녹음 중지 및 변환 시작")
        self.is_recording = False
        
        if self.recording_thread:
            self.recording_thread.join(timeout=5)
        
        # 녹음된 오디오가 있으면 변환
        if self.accumulated_audio:
            return self._convert_audio_to_text()
        
        return None
    
    def _recording_worker(self):
        """백그라운드 녹음 작업자"""
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                while self.is_recording:
                    try:
                        # 짧은 오디오 청크를 연속으로 녹음
                        audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=2)
                        
                        with self.recording_lock:
                            self.accumulated_audio.append(audio)
                        
                    except sr.WaitTimeoutError:
                        # 타임아웃은 정상적인 상황 (계속 녹음)
                        continue
                    except Exception as e:
                        logger.error(f"녹음 중 오류: {e}")
                        break
                        
        except Exception as e:
            logger.error(f"녹음 스레드 오류: {e}")
    
    def _convert_audio_to_text(self) -> Optional[str]:
        """누적된 오디오를 텍스트로 변환"""
        if not self.accumulated_audio:
            return None
        
        self.recognition_count += 1
        
        try:
            # 모든 오디오 청크를 하나로 합치기
            combined_audio_data = b''
            for audio in self.accumulated_audio:
                audio_data = audio.get_raw_data(convert_rate=16000, convert_width=2)
                combined_audio_data += audio_data
            
            if not combined_audio_data:
                return None
            
            # Google Cloud STT 요청
            audio_proto = speech.RecognitionAudio(content=combined_audio_data)
            response = self.google_client.recognize(
                config=self.google_config,
                audio=audio_proto
            )
            
            # 결과 처리
            if response.results:
                result = response.results[0]
                alternative = result.alternatives[0]
                transcript = alternative.transcript
                
                self.successful_recognitions += 1
                logger.info(f"STT 변환 성공: {transcript}")
                
                return transcript
            else:
                logger.warning("STT 변환 결과 없음")
                return None
                
        except Exception as e:
            logger.error(f"STT 변환 실패: {e}")
            return None
    
    def is_recording_active(self) -> bool:
        """현재 녹음 중인지 확인"""
        return self.is_recording
    
    def get_stats(self) -> Dict[str, Any]:
        """STT 사용 통계 반환"""
        success_rate = (self.successful_recognitions / max(self.recognition_count, 1)) * 100
        
        return {
            'total_recognitions': self.recognition_count,
            'successful_recognitions': self.successful_recognitions,
            'success_rate': success_rate,
            'language': self.language,
            'is_recording': self.is_recording
        }