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
    def __init__(self, max_retries=3, delay_range=(8.0, 15.0)):
        self.max_retries = max_retries
        self.delay_range = delay_range
        self.ddgs = None
        self._init_ddgs()
        
    def _init_ddgs(self):
        """Инициализация экземпляра DDGS с новым User-Agent"""
        user_agent = random.choice(USER_AGENTS)
        try:
            self.ddgs = DDGS(
                headers={'User-Agent': user_agent},
                timeout=25  # Увеличенный таймаут
            )
            logger.info(f"Инициализирован DDGS с User-Agent: {user_agent[:50]}...")
        except Exception as e:
            logger.error(f"Ошибка инициализации DDGS: {str(e)}")
            self.ddgs = None

    def perform_search(self, query: str, max_results: int = 5) -> List[Dict]:
        """Основной метод поиска с обработкой ошибок"""
        try:
            return self._perform_search_retry(query, max_results)
        except RetryError as e:
            logger.error(f"Все попытки поиска провалились для '{query}': {str(e)}")
            return [{
                "error": "Поиск не удался после всех попыток",
                "message": "Попробуйте позже или измените запрос"
            }]
        except Exception as e:
            logger.exception(f"Необработанная ошибка для '{query}': {str(e)}")
            return [{
                "error": "Критическая ошибка поиска",
                "details": str(e)
            }]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1.5, min=4, max=30),
        retry=retry_if_exception_type((DuckDuckGoSearchException, ConnectionError, TimeoutError)),
        reraise=True
    )
    def _perform_search_retry(self, query: str, max_results: int = 5) -> List[Dict]:
        """Внутренний метод с повторными попытками"""
        if not self.ddgs:
            self._init_ddgs()
            if not self.ddgs:
                raise DuckDuckGoSearchException("Не удалось инициализировать DDGS")
        
        logger.info(f"Выполняю поиск: {query}")
        
        try:
            # Пробуем разные бэкенды
            for backend in ["auto", "api", "html", "lite"]:
                try:
                    results = self.ddgs.text(
                        keywords=query, 
                        max_results=max_results, 
                        backend=backend
                    )
                    if results:
                        logger.info(f"Успешный поиск через {backend} бэкенд")
                        return self._format_results(results)
                except DuckDuckGoSearchException as e:
                    logger.warning(f"Бэкенд {backend} не сработал: {str(e)}")
                    time.sleep(random.uniform(2, 4))
                    continue
            
            # Если все бэкенды не дали результатов
            logger.warning(f"Нет результатов для: {query}")
            return []
            
        except Exception as e:
            logger.error(f"Ошибка поиска: {str(e)}")
            self._init_ddgs()  # Переинициализация после ошибки
            raise

    def _format_results(self, results: List[Dict]) -> List[Dict]:
        """Форматирование результатов поиска"""
        formatted = []
        for r in results:
            # Проверяем минимальные требования к результату
            if not r.get('href') or not r.get('title'):
                continue
                
            formatted.append({
                'title': r.get('title', 'Без названия'),
                'url': r.get('href', ''),
                'snippet': r.get('body', 'Описание недоступно')[:500] + '...' if r.get('body') else 'Описание недоступно'
            })
        return formatted

    def batch_search(self, queries: List[str], max_results: int = 5) -> Dict[str, List[Dict]]:
        """Пакетный поиск с задержками между запросами"""
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
            
            # Задержка между запросами (кроме последнего)
            if i < len(queries) - 1:
                delay = random.uniform(*self.delay_range)
                logger.info(f"Задержка {delay:.2f} сек перед следующим запросом")
                time.sleep(delay)
                
        return results
