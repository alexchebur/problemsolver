import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from typing import List, Dict

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.78 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1"
]

class WebSearcher:
    def __init__(self, delay_range=(3.0, 6.0)):
        self.delay_range = delay_range

    def perform_search(self, query: str, max_results: int = 3) -> List[Dict]:
        """Надёжный метод поиска с прямым парсингом DuckDuckGo"""
        try:
            # Очищаем запрос
            clean_query = query.replace('"', '').strip()
            logger.info(f"Поиск: '{clean_query}'")
            
            # Выполняем поиск напрямую через DuckDuckGo HTML API
            results = self._duckduckgo_search(clean_query, max_results)
            
            if not results:
                logger.warning(f"Нет результатов для: '{clean_query}'")
                return [{"error": "Нет результатов"}]
            
            return results
        except Exception as e:
            logger.error(f"Ошибка поиска: {str(e)}")
            return [{"error": str(e)}]
        finally:
            delay = random.uniform(*self.delay_range)
            time.sleep(delay)

    def _duckduckgo_search(self, query: str, max_results: int) -> List[Dict]:
        """Прямой поиск через DuckDuckGo HTML API"""
        url = "https://html.duckduckgo.com/html/"
        params = {'q': query, 'kl': 'ru-ru'}
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
        
        response = requests.post(url, data=params, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        for result in soup.select('.result')[:max_results]:
            try:
                title_elem = result.select_one('.result__title a')
                url_elem = result.select_one('.result__url')
                snippet_elem = result.select_one('.result__snippet')
                
                if not title_elem or not url_elem:
                    continue
                
                title = title_elem.text.strip()
                url = url_elem['href'].strip() if 'href' in url_elem.attrs else ''
                snippet = snippet_elem.text.strip()[:500] if snippet_elem else ''
                
                # Исправляем относительные URL
                if url.startswith('//'):
                    url = 'https:' + url
                elif url.startswith('/'):
                    url = 'https://duckduckgo.com' + url
                
                results.append({
                    'title': title,
                    'url': url,
                    'snippet': snippet
                })
            except Exception as e:
                logger.warning(f"Ошибка парсинга результата: {str(e)}")
                continue
        
        return results
