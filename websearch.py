import time
import random
import logging
from typing import List, Dict
from duckduckgo_search import DDGS
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

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
    def __init__(self, max_retries=3, delay_range=(3.0, 6.0)):
        self.max_retries = max_retries
        self.delay_range = delay_range
        # Создаем единственный экземпляр DDGS
        self.ddgs = DDGS(headers={'User-Agent': random.choice(USER_AGENTS)})
        logger.info("Инициализирован экземпляр DDGS")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=10),
        retry=retry_if_exception_type((Exception,))
    )
    def perform_search(self, query: str, max_results: int = 5) -> List[Dict]:
        try:
            logger.info(f"Выполняю поиск: {query}")
            
            # Используем единый экземпляр DDGS
            results = self.ddgs.text(
                keywords=query, 
                max_results=max_results, 
                backend="auto"
            )
            
            if not results:
                logger.warning(f"Нет результатов для: {query}")
                return []
            
            # Форматируем результаты в единую структуру
            formatted_results = []
            for r in results:
                formatted_results.append({
                    'title': r.get('title', ''),
                    'url': r.get('href', ''),
                    'snippet': r.get('body', '')
                })
            
            return formatted_results

        except Exception as e:
            logger.error(f"Ошибка при поиске '{query}': {str(e)}")
            # Обновляем User-Agent и пересоздаем DDGS после ошибки
            self._refresh_ddgs_instance()
            raise
        finally:
            # Задержка между запросами
            delay = random.uniform(*self.delay_range)
            logger.info(f"Задержка {delay:.2f} сек")
            time.sleep(delay)

    def _refresh_ddgs_instance(self):
        """Обновляет экземпляр DDGS с новым User-Agent"""
        logger.warning("Обновление экземпляра DDGS")
        self.ddgs = DDGS(headers={'User-Agent': random.choice(USER_AGENTS)})

    def batch_search(self, queries: List[str], max_results: int = 5) -> Dict[str, List[Dict]]:
        results = {}
        for query in queries:
            try:
                results[query] = self.perform_search(query, max_results)
            except Exception as e:
                logger.exception(f"Неустранимая ошибка для запроса '{query}'")
                results[query] = [{"error": str(e)}]
        return results
