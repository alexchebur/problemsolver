import time
import random
import logging
from typing import List, Dict
from duckduckgo_search import DDGS
from duckduckgo_search.exceptions import DuckDuckGoSearchException
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, RetryError

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Обновленные User-Agent для 2024-2025
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.78 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0"
]

class WebSearcher:
    def __init__(self, max_retries=5, delay_range=(5.0, 15.0)):
        self.max_retries = max_retries
        self.delay_range = delay_range
        self.ddgs = None
        self._init_ddgs()
        
    def _init_ddgs(self):
        """Инициализация или переинициализация экземпляра DDGS"""
        user_agent = random.choice(USER_AGENTS)
        try:
            self.ddgs = DDGS(
                headers={'User-Agent': user_agent},
                timeout=30  # Увеличенный таймаут
            )
            logger.info(f"Инициализирован DDGS с User-Agent: {user_agent[:50]}...")
        except Exception as e:
            logger.error(f"Ошибка инициализации DDGS: {str(e)}")
            self.ddgs = None

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1.5, min=4, max=60),
        retry=retry_if_exception_type((DuckDuckGoSearchException, ConnectionError, TimeoutError)),
        reraise=False
    )
    def perform_search(self, query: str, max_results: int = 5) -> List[Dict]:
        try:
            if not self.ddgs:
                self._init_ddgs()
                if not self.ddgs:
                    raise DuckDuckGoSearchException("Не удалось инициализировать DDGS")
            
            logger.info(f"Выполняю поиск: {query}")
            
            # Пробуем разные бэкенды последовательно
            backends = ["api", "html", "lite"]
            results = []
            
            for backend in backends:
                try:
                    results = self.ddgs.text(
                        keywords=query, 
                        max_results=max_results, 
                        backend=backend
                    )
                    if results:
                        logger.info(f"Успешный поиск через {backend} бэкенд")
                        break
                except Exception as e:
                    logger.warning(f"Бэкенд {backend} не сработал: {str(e)}")
                    time.sleep(random.uniform(2, 5))
            
            if not results:
                logger.warning(f"Нет результатов для: {query}")
                return []
            
            # Форматируем результаты
            formatted_results = []
            for r in results:
                # Проверяем наличие минимально необходимых данных
                if r.get('title') and r.get('href'):
                    formatted_results.append({
                        'title': r.get('title', ''),
                        'url': r.get('href', ''),
                        'snippet': r.get('body', '')[:300]  # Ограничение длины сниппета
                    })
            
            return formatted_results

        except DuckDuckGoSearchException as e:
            logger.error(f"DuckDuckGoSearchException: {str(e)}")
            self._init_ddgs()  # Переинициализация при специфической ошибке
            raise
        except Exception as e:
            logger.error(f"Общая ошибка при поиске: {str(e)}")
            raise
        finally:
            # Задержка между запросами
            delay = random.uniform(*self.delay_range)
            logger.info(f"Задержка {delay:.2f} сек")
            time.sleep(delay)

    def batch_search(self, queries: List[str], max_results: int = 5) -> Dict[str, List[Dict]]:
        results = {}
        for i, query in enumerate(queries):
            try:
                results[query] = self.perform_search(query, max_results)
            except Exception as e:
                logger.exception(f"Ошибка для запроса '{query}'")
                results[query] = [{
                    "error": str(e),
                    "message": "Не удалось получить результаты поиска"
                }]
                
                # Дополнительная задержка после ошибки
                time.sleep(random.uniform(10, 20))
        return results
