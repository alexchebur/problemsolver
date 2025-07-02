import time
import logging
import requests
from typing import List, Dict
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
        self.cse_id = "a4f17489c6a0a4414"  # Пример ID, замените на ваш
        
        # Резервные методы поиска (добавлен DuckDuckGo)
        self.fallback_searchers = [
            self._search_duckduckgo,  # Первый резерв - DuckDuckGo
            self._search_google_organic,
            self._search_bing_ru
        ]

    def perform_search(self, query: str, max_results: int = 3, full_text=True) -> List[Dict]:
        """Основной метод поиска через Google CSE с резервными вариантами"""
        try:
            # Попытка поиска через Google CSE API
            results = self._search_google_cse(query, max_results)
            if results:
                logger.info("Успешный поиск через Google CSE API")
                
                # Если запрошен полный текст, добавляем его
                if full_text:
                    for item in results:
                        item['full_content'] = self.get_full_page_content(item['url'])
                
                return results
                
            # Если CSE не вернул результатов, пробуем резервные методы
            for searcher in self.fallback_searchers:
                try:
                    results = searcher(query, max_results)
                    if results:
                        logger.info(f"Успешный поиск через {searcher.__name__}")
                        
                        # Добавляем полный текст для DuckDuckGo результатов
                        if full_text:
                            for item in results:
                                item['full_content'] = self.get_full_page_content(item['url'])
                        
                        return results
                except Exception as e:
                    logger.warning(f"Ошибка в резервном поиске: {str(e)}")
                    time.sleep(1)
            
            return [{"error": "Все методы поиска недоступны"}]
        except Exception as e:
            return [{"error": f"Ошибка поиска: {str(e)}"}]
        finally:
            time.sleep(random.uniform(*self.delay_range))

    def _search_duckduckgo(self, query: str, max_results: int) -> List[Dict]:
        """Поиск через DuckDuckGo API (резервный метод)"""
        try:
            from duckduckpy import query as dd_query
        except ImportError:
            logger.warning("Библиотека duckduckpy не установлена. Пропуск DuckDuckGo.")
            return []

        try:
            # Выполняем запрос в формате словаря
            response = dd_query(query, container='dict')
            results = []
            
            # Обрабатываем основные результаты
            for item in response.get('results', [])[:max_results]:
                if 'first_url' in item and 'text' in item:
                    results.append({
                        'title': item['text'][:100],
                        'url': item['first_url'],
                        'snippet': item['text'][:500]
                    })
            
            # Обрабатываем связанные темы (если не набрали достаточно результатов)
            if len(results) < max_results:
                for item in response.get('related_topics', []):
                    if 'first_url' in item and 'text' in item:
                        results.append({
                            'title': item['text'][:100],
                            'url': item['first_url'],
                            'snippet': item['text'][:500]
                        })
                        if len(results) >= max_results:
                            break
            
            return results[:max_results]
        
        except Exception as e:
            logger.error(f"Ошибка DuckDuckGo: {str(e)}")
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
                'title': item.get('title'),
                'url': item.get('link'),
                'snippet': item.get('snippet', '')[:500]
            })
        
        return results

    def _search_google_organic(self, query: str, max_results: int) -> List[Dict]:
        """Органический поиск через Google (резервный метод)"""
        url = "https://www.google.com/search"
        params = {
            'q': query + " site:.ru",
            'num': max_results,
            'hl': 'ru',
            'lr': 'lang_ru',
            'cr': 'countryRU'
        }
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        
        response = self.session.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Здесь должен быть парсинг результатов, но для примера заглушка
        return [{
            'title': 'Резервный результат Google',
            'url': 'https://www.google.com',
            'snippet': 'Это результат резервного поиска Google'
        }]

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
        
        # Здесь должен быть парсинг результатов, но для примера заглушка
        return [{
            'title': 'Резервный результат Bing',
            'url': 'https://www.bing.com',
            'snippet': 'Это результат резервного поиска Bing'
        }]

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
