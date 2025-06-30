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
        self.search_engines = [
            self._search_google,
            self._search_bing,
            self._search_yandex,
            self._search_duckduckgo_html
        ]

    def perform_search(self, query: str, max_results: int = 3) -> List[Dict]:
        """Универсальный метод поиска с резервными системами"""
        try:
            # Очистка запроса
            clean_query = re.sub(r'[^\w\s]', '', query).strip()
            if not clean_query:
                return [{"error": "Пустой запрос"}]
                
            # Пробуем разные поисковые системы
            for search_method in self.search_engines:
                try:
                    results = search_method(clean_query, max_results)
                    if results:
                        logger.info(f"Успешный поиск через {search_method.__name__}")
                        return results
                except Exception as e:
                    logger.warning(f"Ошибка в {search_method.__name__}: {str(e)}")
                    time.sleep(2)
            
            return [{"error": "Все поисковые системы недоступны"}]
        except Exception as e:
            return [{"error": f"Критическая ошибка: {str(e)}"}]
        finally:
            time.sleep(random.uniform(*self.delay_range))

    def _search_google(self, query: str, max_results: int) -> List[Dict]:
        """Поиск через Google"""
        url = "https://www.google.com/search"
        params = {'q': query, 'num': max_results, 'hl': 'ru'}
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        
        response = self.session.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        for g in soup.select('div.g')[:max_results]:
            title_elem = g.select_one('h3')
            link_elem = g.select_one('a[href]')
            snippet_elem = g.select_one('div.IsZvec')
            
            if not title_elem or not link_elem:
                continue
                
            title = title_elem.get_text()
            url = link_elem['href']
            snippet = snippet_elem.get_text()[:500] if snippet_elem else ''
            
            # Фильтрация URL Google
            if url.startswith('/search?') or url.startswith('/url?'):
                continue
                
            results.append({
                'title': title,
                'url': url,
                'snippet': snippet
            })
        
        return results

    def _search_bing(self, query: str, max_results: int) -> List[Dict]:
        """Поиск через Bing"""
        url = "https://www.bing.com/search"
        params = {'q': query, 'count': max_results}
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        
        response = self.session.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        for result in soup.select('li.b_algo')[:max_results]:
            title_elem = result.select_one('h2')
            link_elem = result.select_one('a')
            snippet_elem = result.select_one('p')
            
            if not title_elem or not link_elem:
                continue
                
            results.append({
                'title': title_elem.get_text(),
                'url': link_elem['href'],
                'snippet': snippet_elem.get_text()[:500] if snippet_elem else ''
            })
        
        return results

    def _search_yandex(self, query: str, max_results: int) -> List[Dict]:
        """Поиск через Yandex (для русскоязычных запросов)"""
        url = "https://yandex.ru/search/"
        params = {'text': query, 'numdoc': max_results}
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        
        response = self.session.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        for result in soup.select('li.serp-item')[:max_results]:
            title_elem = result.select_one('h2 a')
            snippet_elem = result.select_one('.organic__content-wrapper')
            
            if not title_elem:
                continue
                
            results.append({
                'title': title_elem.get_text(),
                'url': title_elem['href'],
                'snippet': snippet_elem.get_text()[:500] if snippet_elem else ''
            })
        
        return results

    def _search_duckduckgo_html(self, query: str, max_results: int) -> List[Dict]:
        """Резервный метод поиска через HTML DuckDuckGo"""
        url = "https://html.duckduckgo.com/html/"
        params = {'q': query, 'kl': 'ru-ru'}
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        
        response = self.session.post(url, data=params, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        for result in soup.select('.result')[:max_results]:
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
        
        return results
