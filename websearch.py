import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from typing import List, Dict
import re

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.78 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0"
]

class WebSearcher:
    def __init__(self, delay_range=(5.0, 10.0)):
        self.delay_range = delay_range
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': random.choice(USER_AGENTS)})

    def perform_search(self, query: str, max_results: int = 3) -> List[Dict]:
        """Надёжный метод поиска для Streamlit"""
        try:
            # Очистка запроса
            clean_query = re.sub(r'[^\w\s]', '', query).strip()
            if not clean_query:
                return [{"error": "Пустой запрос"}]
                
            # Поиск через API
            return self._api_search(clean_query, max_results)
        except Exception as e:
            return [{"error": f"Ошибка поиска: {str(e)}"}]
        finally:
            time.sleep(random.uniform(*self.delay_range))

    def _api_search(self, query: str, max_results: int) -> List[Dict]:
        """Используем официальный API DuckDuckGo"""
        url = "https://api.duckduckgo.com/"
        params = {
            'q': query,
            'format': 'json',
            'no_redirect': 1,
            'no_html': 1,
            'kl': 'ru-ru'
        }
        
        response = self.session.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        results = []
        # Основной результат
        if data.get('AbstractText'):
            results.append({
                'title': data.get('Heading', query),
                'url': data.get('AbstractURL', ''),
                'snippet': data.get('AbstractText', '')[:500]
            })
        
        # Похожие результаты
        for i, topic in enumerate(data.get('RelatedTopics', [])[:max_results]):
            if 'Text' in topic:
                results.append({
                    'title': topic.get('FirstURL', '').split('//')[-1].split('/')[0],
                    'url': topic.get('FirstURL', ''),
                    'snippet': topic.get('Text', '')[:500]
                })
        
        return results[:max_results]
