import time
import random
import logging
from typing import List, Dict, Optional
from duckduckgo_search import DDGS
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Список User-Agent для анти-бан системы
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
]

def get_random_user_agent():
    return random.choice(USER_AGENTS)

class WebSearcher:
    def __init__(self, max_retries=3, delay_range=(2.0, 5.0)):
        self.user_agent = get_random_user_agent()
        self.max_retries = max_retries
        self.delay_range = delay_range
        self.ddgs = DDGS(headers={'User-Agent': self.user_agent})  # ✅ Создаем один раз

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=10),
        retry=retry_if_exception_type((Exception,))
    )
    def perform_search(self, query: str, max_results: int = 5) -> List[Dict]:
        """
        Выполняет поиск через DuckDuckGo и возвращает результаты.

        :param query: Поисковый запрос
        :param max_results: Максимальное количество результатов
        :return: Список результатов поиска
        """
        try:
            logger.info(f"Выполняю поиск: {query}")
            time.sleep(random.uniform(*self.delay_range))  # ✅ Случайная задержка

            results = self.ddgs.text(query, max_results=max_results, backend="auto")

            if not results:
                logger.warning(f"Нет результатов для: {query}")
                return []

            return results

        except Exception as e:
            logger.error(f"Ошибка при поиске '{query}': {str(e)}")
            raise

    def batch_search(self, queries: List[str], max_results: int = 5) -> Dict[str, List[Dict]]:
        """
        Выполняет несколько поисковых запросов.

        :param queries: Список поисковых запросов
        :param max_results: Максимальное количество результатов на каждый запрос
        :return: Словарь с результатами по каждому запросу
        """
        results = {}
        for query in queries:
            try:
                results[query] = self.perform_search(query, max_results)
            except Exception as e:
                results[query] = [{"error": str(e)}]
        return results
