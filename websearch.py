import time
import logging
import requests
import json
import urllib.parse
from typing import List, Dict, Union
import random
from bs4 import BeautifulSoup

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.78 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0"
]

class GoogleCSESearcher:
    def __init__(self, delay_range=(1.0, 3.0)):
        self.delay_range = delay_range
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': random.choice(USER_AGENTS)})
        
        # Ваш API ключ и настройки
        self.api_key = "AIzaSyCNVeNmUgrt-kL5ZI4EkHFoTjTzRSWATX4"
        self.cse_id = "a4f17489c6a0a4414"
        
        # Резервные методы поиска
        self.fallback_searchers = [
            self._search_duckduckgo,
            self._search_google_organic,
            self._search_bing_ru
        ]

    def perform_search(self, queries: Union[str, List[str]], max_results: int = 3, full_text=True) -> List[Dict]:
        """Поддерживает поиск по одному запросу или списку запросов"""
        if isinstance(queries, str):
            queries = [queries]
            
        all_results = []
        
        for query in queries:
            try:
                # Всегда выполняем поиск по оригинальному запросу пользователя
                results = self._search_with_fallbacks(query, max_results, full_text)
                all_results.extend(results)
            except Exception as e:
                logger.error(f"Ошибка поиска для '{query}': {str(e)}")
                all_results.append({
                    'title': f"Ошибка поиска: {query}",
                    'url': "#",
                    'snippet': str(e),
                    'query': query
                })
            finally:
                time.sleep(random.uniform(*self.delay_range))
        
        return all_results

    def _search_with_fallbacks(self, query: str, max_results: int, full_text: bool) -> List[Dict]:
        """Основная логика поиска с резервными методами"""
        try:
            # Сначала пробуем Google CSE API
            results = self._search_google_cse(query, max_results)
            if results:
                logger.info(f"Успешный поиск через Google CSE: {query}")
                if full_text:
                    self._add_full_content(results)
                return results
        except Exception as e:
            logger.warning(f"Google CSE недоступен для '{query}': {str(e)}")
        
        # Если CSE не сработал, пробуем резервные методы
        for searcher in self.fallback_searchers:
            try:
                results = searcher(query, max_results)
                if results:
                    logger.info(f"Успешный поиск через {searcher.__name__}: {query}")
                    if full_text:
                        self._add_full_content(results)
                    return results
            except Exception as e:
                logger.warning(f"Ошибка в {searcher.__name__} для '{query}': {str(e)}")
                time.sleep(1)
        
        return [{
            'title': f"Не найдено: {query}",
            'url': "#",
            'snippet': "Все методы поиска недоступны",
            'query': query
        }]

    def _add_full_content(self, results: List[Dict]):
        """Добавляет полный контент к результатам"""
        for item in results:
            item['full_content'] = self.get_full_page_content(item['url'])

    def _search_duckduckgo(self, query: str, max_results: int) -> List[Dict]:
        """Надежный поиск через DuckDuckGo с прямым доступом к API"""
        try:
            # Прямой вызов DuckDuckGo API
            url = "https://api.duckduckgo.com/"
            params = {
                'q': query,
                'format': 'json',
                'no_redirect': 1,
                'no_html': 1,
                'skip_disambig': 1,
                'kl': 'ru-ru'
            }
            
            headers = {'User-Agent': random.choice(USER_AGENTS)}
            response = self.session.get(url, params=params, headers=headers, timeout=15)
            response.raise_for_status()
            
            # Проверяем корректность JSON
            try:
                data = response.json()
            except json.JSONDecodeError:
                logger.error("DuckDuckGo вернул невалидный JSON")
                return []
            
            results = []
            
            # Обрабатываем основной результат
            if data.get('AbstractText'):
                results.append({
                    'title': data.get('Heading', 'Без названия')[:100],
                    'url': data.get('AbstractURL', '#'),
                    'snippet': data.get('AbstractText', 'Без описания')[:500],
                    'query': query
                })
            
            # Обрабатываем связанные темы
            for topic in data.get('RelatedTopics', [])[:max_results]:
                if 'FirstURL' in topic and 'Text' in topic:
                    results.append({
                        'title': topic['Text'][:100] if topic.get('Text') else 'Без названия',
                        'url': topic['FirstURL'],
                        'snippet': topic['Text'][:500] if topic.get('Text') else 'Без описания',
                        'query': query
                    })
                elif 'Topics' in topic:
                    for subtopic in topic['Topics'][:max_results - len(results)]:
                        if 'FirstURL' in subtopic and 'Text' in subtopic:
                            results.append({
                                'title': subtopic['Text'][:100] if subtopic.get('Text') else 'Без названия',
                                'url': subtopic['FirstURL'],
                                'snippet': subtopic['Text'][:500] if subtopic.get('Text') else 'Без описания',
                                'query': query
                            })
            
            return results[:max_results]
        
        except Exception as e:
            logger.error(f"Ошибка DuckDuckGo: {str(e)}")
            # В случае ошибки пробуем HTML-версию как запасной вариант
            return self._search_duckduckgo_html(query, max_results)

    def _search_duckduckgo_html(self, query: str, max_results: int) -> List[Dict]:
        """Резервный метод поиска через парсинг HTML DuckDuckGo"""
        try:
            url = "https://html.duckduckgo.com/html/"
            headers = {
                'User-Agent': random.choice(USER_AGENTS),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
                'Referer': 'https://duckduckgo.com/',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': 'https://duckduckgo.com',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            data = {'q': query}
            response = self.session.post(url, headers=headers, data=data, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # Ищем все результаты
            for result in soup.select('.result__body')[:max_results]:
                title_elem = result.select_one('.result__a')
                snippet_elem = result.select_one('.result__snippet')
                
                if title_elem:
                    title = title_elem.get_text(strip=True)[:100]
                    url = title_elem.get('href', '#')
                    
                    # Обработка относительных URL
                    if url.startswith('//'):
                        url = 'https:' + url
                    elif url.startswith('/'):
                        url = 'https://duckduckgo.com' + url
                    
                    snippet = snippet_elem.get_text(strip=True)[:500] if snippet_elem else 'Без описания'
                    
                    results.append({
                        'title': title,
                        'url': url,
                        'snippet': snippet,
                        'query': query
                    })
            
            return results[:max_results]
        
        except Exception as e:
            logger.error(f"Ошибка DuckDuckGo HTML: {str(e)}")
            return []

    def _search_google_cse(self, query: str, max_results: int) -> List[Dict]:
        """Поиск через Google Custom Search API"""
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': self.api_key,
            'cx': self.cse_id,
            'q': query,
            'num': max_results,
            'lr': 'lang_ru',
            'cr': 'countryRU',
            'hl': 'ru'
        }
        
        response = self.session.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for item in data.get('items', [])[:max_results]:
            results.append({
                'title': item.get('title', 'Без названия'),
                'url': item.get('link', '#'),
                'snippet': item.get('snippet', 'Без описания')[:500],
                'query': query
            })
        
        return results

    def _search_google_organic(self, query: str, max_results: int) -> List[Dict]:
        """Органический поиск через Google (резервный метод)"""
        url = "https://www.google.com/search"
        params = {
            'q': query,
            'num': max_results,
            'hl': 'ru',
            'lr': 'lang_ru',
            'cr': 'countryRU'
        }
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        
        response = self.session.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        # Парсинг органических результатов
        for g in soup.select('.g')[:max_results]:
            anchor = g.select_one('a')
            if anchor:
                title = anchor.get_text(strip=True)
                url = anchor.get('href')
                snippet = g.select_one('.IsZvec, .VwiC3b').get_text(strip=True)[:500] if g.select_one('.IsZvec, .VwiC3b') else ''
                
                # Проверяем, что это не рекламный результат
                if url and not url.startswith('/search?') and 'google.com' not in url:
                    results.append({
                        'title': title[:100],
                        'url': url,
                        'snippet': snippet,
                        'query': query
                    })
        
        return results[:max_results]

    def _search_bing_ru(self, query: str, max_results: int) -> List[Dict]:
        """Поиск через Bing (резервный метод)"""
        url = "https://www.bing.com/search"
        params = {
            'q': query,
            'count': max_results,
            'setmkt': 'ru-RU',
            'setlang': 'ru'
        }
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        
        response = self.session.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        # Парсинг результатов Bing
        for li in soup.select('.b_algo')[:max_results]:
            anchor = li.select_one('h2 a')
            if anchor:
                title = anchor.get_text(strip=True)
                url = anchor.get('href')
                snippet = li.select_one('.b_caption p').get_text(strip=True)[:500] if li.select_one('.b_caption p') else ''
                
                results.append({
                    'title': title[:100],
                    'url': url,
                    'snippet': snippet,
                    'query': query
                })
        
        return results[:max_results]

    def get_full_page_content(self, url: str) -> str:
        """Получение полного текста страницы"""
        try:
            headers = {'User-Agent': random.choice(USER_AGENTS)}
            response = self.session.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            # Упрощенный парсинг основного контента
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Удаляем ненужные элементы
            for tag in soup(['script', 'style', 'footer', 'nav', 'aside']):
                tag.decompose()
            
            # Извлекаем текст
            text = ' '.join(soup.stripped_strings)
            return text[:10000]  # Ограничение до 10k символов
            
        except Exception as e:
            logger.error(f"Ошибка получения контента: {str(e)}")
            return ""
