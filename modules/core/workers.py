#!/usr/bin/env python3
"""
백그라운드 워커 모듈
문장 생성 및 음성 처리를 위한 워커 클래스
"""

import logging
from typing import List, Optional
from PyQt5.QtCore import QObject, QThread, pyqtSignal

logger = logging.getLogger(__name__)


class SentenceWorker(QObject):
    """문장 생성을 위한 워커 클래스"""

    # 시그널 정의
    sentence_ready = pyqtSignal(str)  # 문장 생성 완료
    error_occurred = pyqtSignal(str)  # 오류 발생
    progress_update = pyqtSignal(str)  # 진행 상황 업데이트

    def __init__(self, translator=None):
        """
        Args:
            translator: SignLanguageTranslator 인스턴스
        """
        super().__init__()
        self.translator = translator

    def generate_sentence(self, words: List[str], context: Optional[str] = None):
        """
        백그라운드에서 문장 생성

        Args:
            words: 단어 리스트
            context: 추가 컨텍스트
        """
        try:
            if not self.translator:
                self.error_occurred.emit("번역기가 초기화되지 않았습니다.")
                return

            if not words:
                self.error_occurred.emit("단어가 없습니다.")
                return

            self.progress_update.emit("문장 생성 중...")

            # 문장 생성
            sentence = self.translator.sentence_generator.generate_sentence(
                words=words,
                context=context,
                use_cache=True
            )

            if sentence:
                self.sentence_ready.emit(sentence)
                self.progress_update.emit("TTS 실행 중...")

                # TTS 실행
                self.translator.tts_module.text_to_speech(
                    text=sentence,
                    play_audio=True,
                    use_cache=True
                )

                self.progress_update.emit("완료")
            else:
                self.error_occurred.emit("문장 생성에 실패했습니다.")

        except Exception as e:
            logger.error(f"문장 생성 오류: {e}")
            self.error_occurred.emit(f"오류: {str(e)}")


class STTWorker(QObject):
    """음성 인식을 위한 워커 클래스"""

    # 시그널 정의
    text_recognized = pyqtSignal(str)  # 텍스트 인식 완료
    error_occurred = pyqtSignal(str)  # 오류 발생
    recording_started = pyqtSignal()  # 녹음 시작
    recording_stopped = pyqtSignal()  # 녹음 중지

    def __init__(self, translator=None):
        """
        Args:
            translator: SignLanguageTranslator 인스턴스
        """
        super().__init__()
        self.translator = translator

    def start_recording(self):
        """녹음 시작"""
        try:
            if not self.translator or not self.translator.stt_module:
                self.error_occurred.emit("STT 모듈이 초기화되지 않았습니다.")
                return

            if self.translator.start_stt_recording():
                self.recording_started.emit()
            else:
                self.error_occurred.emit("녹음을 시작할 수 없습니다.")

        except Exception as e:
            logger.error(f"녹음 시작 오류: {e}")
            self.error_occurred.emit(f"오류: {str(e)}")

    def stop_recording(self):
        """녹음 중지 및 텍스트 변환"""
        try:
            if not self.translator:
                self.error_occurred.emit("번역기가 초기화되지 않았습니다.")
                return

            recognized_text = self.translator.stop_stt_recording()
            self.recording_stopped.emit()

            if recognized_text:
                self.text_recognized.emit(recognized_text)
            else:
                self.error_occurred.emit("음성을 인식하지 못했습니다.")

        except Exception as e:
            logger.error(f"녹음 중지 오류: {e}")
            self.error_occurred.emit(f"오류: {str(e)}")


class WorkerManager:
    """워커 스레드 관리자"""

    def __init__(self):
        self.active_threads = []
        logger.info("워커 매니저 초기화")

    def create_sentence_worker(self, translator, words: List[str],
                               on_ready=None, on_error=None, on_progress=None):
        """
        문장 생성 워커 생성 및 실행

        Args:
            translator: 번역기 인스턴스
            words: 단어 리스트
            on_ready: 완료 콜백
            on_error: 오류 콜백
            on_progress: 진행 콜백
        """
        # 스레드와 워커 생성
        thread = QThread()
        worker = SentenceWorker(translator)
        worker.moveToThread(thread)

        # 시그널 연결
        if on_ready:
            worker.sentence_ready.connect(on_ready)
        if on_error:
            worker.error_occurred.connect(on_error)
        if on_progress:
            worker.progress_update.connect(on_progress)

        # 스레드 시작 시 작업 실행
        thread.started.connect(lambda: worker.generate_sentence(words))

        # 정리 작업
        worker.sentence_ready.connect(thread.quit)
        worker.error_occurred.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self.remove_thread(thread))

        # 스레드 추가 및 시작
        self.active_threads.append(thread)
        thread.start()

        return worker

    def create_stt_worker(self, translator, on_recognized=None, on_error=None):
        """
        STT 워커 생성

        Args:
            translator: 번역기 인스턴스
            on_recognized: 인식 완료 콜백
            on_error: 오류 콜백
        """
        worker = STTWorker(translator)

        if on_recognized:
            worker.text_recognized.connect(on_recognized)
        if on_error:
            worker.error_occurred.connect(on_error)

        return worker

    def remove_thread(self, thread):
        """스레드 제거"""
        if thread in self.active_threads:
            self.active_threads.remove(thread)

    def cleanup_all(self):
        """모든 활성 스레드 정리"""
        for thread in self.active_threads:
            if thread.isRunning():
                thread.quit()
                thread.wait()
        self.active_threads.clear()
        logger.info("모든 워커 스레드 정리 완료")