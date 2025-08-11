import os
import json
import logging
import time
import hashlib
from typing import List, Optional, Dict, Any
from pathlib import Path

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logging.warning("OpenAI not available. Install: pip install openai")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SentenceGenerator:
    """OpenAI를 사용하여 수어 단어들을 자연스러운 문장으로 변환하는 클래스"""
    
    def __init__(self, api_key: Optional[str] = None, cache_dir: str = "cache"):
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI를 사용하려면 'pip install openai'를 설치하세요.")
        
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key가 필요합니다.")
        
        self.client = openai.OpenAI(api_key=self.api_key)
        
        # 캐시 설정
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_file = self.cache_dir / "sentence_cache.json"
        
        self.cache = self._load_cache()
        self.cache_hits = 0
        self.total_requests = 0
        
        logger.info("SentenceGenerator 초기화 완료")
    
    def _load_cache(self) -> Dict[str, Any]:
        """캐시 파일 로드"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                return cache_data
            except Exception as e:
                logger.warning(f"캐시 로드 실패: {e}")
                return {}
        return {}
    
    def _save_cache(self):
        """캐시 파일 저장"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"캐시 저장 실패: {e}")
    
    def _get_cache_key(self, words: List[str], context: Optional[str] = None) -> str:
        """캐시 키 생성"""
        key_data = {
            'words': sorted(words),
            'context': context or ""
        }
        key_string = json.dumps(key_data, ensure_ascii=False, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def generate_sentence(self, words: List[str], context: Optional[str] = None, 
                         use_cache: bool = True) -> Optional[str]:
        """수어 단어들을 자연스러운 문장으로 변환"""
        if not words:
            return None
        
        self.total_requests += 1
        
        # 캐시 확인
        cache_key = self._get_cache_key(words, context)
        if use_cache and cache_key in self.cache:
            self.cache_hits += 1
            return self.cache[cache_key]['sentence']
        
        # 프롬프트 생성
        prompt = self._create_prompt(words, context)
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "당신은 한국어 수어를 자연스러운 문장으로 변환하는 전문가입니다."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.7
            )
            
            sentence = response.choices[0].message.content.strip()
            sentence = self._post_process_sentence(sentence)
            
            # 캐시에 저장
            if use_cache and sentence:
                self.cache[cache_key] = {
                    'words': words,
                    'context': context,
                    'sentence': sentence,
                    'timestamp': time.time()
                }
                self._save_cache()
            
            return sentence
            
        except Exception as e:
            logger.error(f"문장 생성 실패: {e}")
            return None
    
    def _create_prompt(self, words: List[str], context: Optional[str] = None) -> str:
        """OpenAI용 프롬프트 생성"""
        prompt = f"""다음 한국어 수어 단어들을 자연스럽고 문법적으로 올바른 한국어 문장으로 변환해주세요.

수어 단어: {' + '.join(words)}"""
        
        if context:
            prompt += f"\n추가 맥락: {context}"
        
        prompt += """

규칙:
1. 자연스러운 한국어 문장으로 변환
2. 문법적으로 올바르게 작성
3. 조사와 어미를 적절히 추가
4. 한 문장으로 완성
5. 마침표 포함
6. 가능한 주어진 단어로만 자연스럽게 만들 것
7. 자연스러움을 위해 억지로 길게 만들지 말 것
8. 가능한 존댓말로 변환

예시:
수어 단어: 구급차 → 구급차입니다.
수어 단어: 나 → 저입니다.
수어 단어: 나, 아프다 → 저는 아픕니다.
수어 단어: 나, 학교, 가다 → 저는 학교에 갑니다.
수어 단어: 엄마, 밥, 먹다 → 엄마가 밥을 드신다.

변환된 문장:"""
        
        return prompt
    
    def _post_process_sentence(self, sentence: str) -> str:
        """생성된 문장 후처리"""
        if not sentence:
            return ""
        
        sentence = sentence.strip('"\'')
        
        if not sentence.endswith(('.', '!', '?')):
            sentence += '.'
        
        sentence = ' '.join(sentence.split())
        
        return sentence
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계 반환"""
        cache_size = 0
        if self.cache_file.exists():
            cache_size = self.cache_file.stat().st_size
        
        return {
            'total_entries': len(self.cache),
            'total_hits': self.cache_hits,
            'total_requests': self.total_requests,
            'hit_rate': (self.cache_hits / max(self.total_requests, 1)) * 100,
            'cache_size_kb': cache_size / 1024
        }
    
    def clear_cache(self):
        """캐시 초기화"""
        self.cache = {}
        if self.cache_file.exists():
            self.cache_file.unlink()
        self.cache_hits = 0
        self.total_requests = 0