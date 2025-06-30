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
    def __init__(self, max_retries=3, delay_range=(5.0, 10.0)):
        self.max_retries = max_retries
        self.delay_range = delay_range

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=10),
        retry=retry_if_exception_type((Exception,))
    )
    def perform_search(self, query: str, max_results: int = 5) -> List[Dict]:
        user_agent = random.choice(USER_AGENTS)
        try:
            logger.info(f"Выполняю поиск: {query}")
            
            # Создаем новый экземпляр DDGS для каждого запроса
            with DDGS(headers={'User-Agent': user_agent}, timeout=20) as ddgs:
                results = ddgs.text(
                    keywords=query,
                    max_results=max_results,
                    backend="api"  # Используем стабильный API-бэкенд
                )
            
            if not results:
                logger.warning(f"Нет результатов для: {query}")
                return []
                
            # Фильтруем некорректные результаты
            valid_results = []
            for r in results:
                if not r.get('href', '').startswith(('http://www.google.com', 'https://www.google.com')):
                    valid_results.append({
                        'title': r.get('title', ''),
                        'url': r.get('href', ''),
                        'snippet': r.get('body', '')
                    })
            
            return valid_results

        except Exception as e:
            logger.error(f"Ошибка при поиске '{query}': {str(e)}")
            raise

    def batch_search(self, queries: List[str], max_results: int = 5) -> Dict[str, List[Dict]]:
        results = {}
        for i, query in enumerate(queries):
            try:
                results[query] = self.perform_search(query, max_results)
            except Exception as e:
                logger.exception(f"Критическая ошибка для запроса '{query}'")
                results[query] = [{"error": str(e)}]
            
            # Задержка между запросами (кроме последнего)
            if i < len(queries) - 1:
                delay = random.uniform(*self.delay_range)
                logger.info(f"Задержка {delay:.2f} сек перед следующим запросом")
                time.sleep(delay)
                
        return results
