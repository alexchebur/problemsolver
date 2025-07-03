import time
import logging
import requests
import re
from typing import List, Dict, Union
import random
from bs4 import BeautifulSoup
from urllib.parse import unquote, urlparse, parse_qs

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.78 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0"
]

class WebSearcher:
    def __init__(self, delay_range=(1.0, 3.0)):
        self.delay_range = delay_range
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': random.choice(USER_AGENTS)})
        
        # Настройки Google CSE
        self.api_key = "AIzaSyCNVeNmUgrt-kL5ZI4EkHFoTjTzRSWATX4"
        self.cse_id = "a4f17489c6a0a4414"
        
        # Порядок поисковых систем
        self.search_engines = [
            self._search_google_cse,
            self._search_duckduckgo,
            self._search_google_organic,
            self._search_bing_ru
        ]

    def perform_search(self, queries: Union[str, List[str]], max_results: int = 3, full_text=True) -> List[Dict]:
        """Выполняет поиск по одному или нескольким запросам"""
        if isinstance(queries, str):
            queries = [queries]
            
        all_results = []
        
        for query in queries:
            try:
                # Пытаемся выполнить поиск по всем системам
                results = self._search_with_engines(query, max_results, full_text)
                all_results.extend(results)
            except Exception as e:
                logger.error(f"Ошибка поиска для '{query}': {str(e)}")
                all_results.append({
                    'title': f"Ошибка поиска: {query}",
                    'url': "#",
                    'snippet': str(e),
                    'query': query,
                    'engine': 'System'
                })
            finally:
                time.sleep(random.uniform(*self.delay_range))
        
        return all_results

    def _search_with_engines(self, query: str, max_results: int, full_text: bool) -> List[Dict]:
        """Поочередно пробует разные поисковые системы"""
        results = []
        
        for engine in self.search_engines:
            try:
                engine_results = engine(query, max_results - len(results))
                if engine_results:
                    logger.info(f"Найдено {len(engine_results)} результатов через {engine.__name__}")
                    
                    # Добавляем информацию о движке
                    for r in engine_results:
                        r['engine'] = engine.__name__.replace('_search_', '').title()
                    
                    results.extend(engine_results)
                    
                    if len(results) >= max_results:
                        break
            except Exception as e:
                logger.warning(f"Ошибка в {engine.__name__}: {str(e)}")
                time.sleep(1)
        
        # Добавляем полный текст если требуется
        if full_text and results:
            self._add_full_content(results)
        
        # Если результатов нет, возвращаем заглушку
        if not results:
            return [{
                'title': f"Не найдено: {query}",
                'url': "#",
                'snippet': "Все поисковые системы недоступны",
                'query': query,
                'engine': 'System'
            }]
        
        return results[:max_results]

    def _add_full_content(self, results: List[Dict]):
        """Добавляет полный контент к результатам"""
        for item in results:
            # Не загружаем контент для системных сообщений
            if not item['url'].startswith('#'):
                item['full_content'] = self.get_full_page_content(item['url'])

    def _search_duckduckgo(self, query: str, max_results: int) -> List[Dict]:
        """Поиск через DuckDuckGo с надежным HTML-парсингом"""
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
            for result in soup.select('.web-result')[:max_results]:
                try:
                    # Извлекаем заголовок и URL
                    title_elem = result.select_one('.result__a')
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    raw_url = title_elem.get('href', '')
                    
                    # Декодируем специальный URL DuckDuckGo
                    if raw_url.startswith('/l/?uddg='):
                        match = re.search(r'uddg=([^&]+)', raw_url)
                        if match:
                            decoded_url = unquote(match.group(1))
                            url = decoded_url
                        else:
                            url = f"https://duckduckgo.com{raw_url}"
                    else:
                        url = raw_url
                    
                    # Извлекаем сниппет
                    snippet_elem = result.select_one('.result__snippet')
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ''
                    
                    # Добавляем результат
                    results.append({
                        'title': title[:150],
                        'url': url,
                        'snippet': snippet[:500],
                        'query': query
                    })
                except Exception as e:
                    logger.warning(f"Ошибка парсинга результата DuckDuckGo: {str(e)}")
            
            return results[:max_results]
        
        except Exception as e:
            logger.error(f"Ошибка DuckDuckGo: {str(e)}")
            return []

    def _search_google_cse(self, query: str, max_results: int) -> List[Dict]:
        """Поиск через Google Custom Search API"""
        try:
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
                    'title': item.get('title', 'Без названия')[:150],
                    'url': item.get('link', '#'),
                    'snippet': item.get('snippet', 'Без описания')[:500],
                    'query': query
                })
            
            return results
        except Exception as e:
            logger.error(f"Ошибка Google CSE: {str(e)}")
            return []

    def _search_google_organic(self, query: str, max_results: int) -> List[Dict]:
        """Органический поиск через Google"""
        try:
            url = "https://www.google.com/search"
            params = {
                'q': query,
                'num': max_results + 2,  # Берем больше на случай рекламных результатов
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
            for g in soup.select('div.g')[:max_results * 2]:
                try:
                    # Пропускаем рекламные блоки
                    if g.find('span', text=re.compile(r'Реклама|Ad')):
                        continue
                    
                    # Извлекаем заголовок и URL
                    anchor = g.select_one('a')
                    if not anchor or not anchor.get('href'):
                        continue
                    
                    title = anchor.get_text(strip=True)
                    raw_url = anchor.get('href')
                    
                    # Обработка Google-ссылок
                    if raw_url.startswith('/url?q='):
                        decoded_url = unquote(raw_url.split('q=')[1].split('&')[0])
                        url = decoded_url
                    else:
                        url = raw_url
                    
                    # Извлекаем сниппет
                    snippet = ''
                    snippet_elem = g.select_one('div.IsZvec, div.VwiC3b, span.aCOpRe')
                    if snippet_elem:
                        snippet = snippet_elem.get_text(strip=True)
                    
                    # Добавляем результат
                    results.append({
                        'title': title[:150],
                        'url': url,
                        'snippet': snippet[:500],
                        'query': query
                    })
                    
                    if len(results) >= max_results:
                        break
                except Exception as e:
                    logger.warning(f"Ошибка парсинга результата Google: {str(e)}")
            
            return results[:max_results]
        except Exception as e:
            logger.error(f"Ошибка Google Organic: {str(e)}")
            return []

    def _search_bing_ru(self, query: str, max_results: int) -> List[Dict]:
        """Поиск через Bing"""
        try:
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
            for li in soup.select('li.b_algo')[:max_results]:
                try:
                    anchor = li.select_one('h2 a')
                    if not anchor or not anchor.get('href'):
                        continue
                    
                    title = anchor.get_text(strip=True)
                    url = anchor.get('href')
                    
                    # Извлекаем сниппет
                    snippet = ''
                    snippet_elem = li.select_one('div.b_caption p')
                    if not snippet_elem:
                        snippet_elem = li.select_one('p.b_algoSlug')
                    
                    if snippet_elem:
                        snippet = snippet_elem.get_text(strip=True)
                    
                    # Добавляем результат
                    results.append({
                        'title': title[:150],
                        'url': url,
                        'snippet': snippet[:500],
                        'query': query
                    })
                except Exception as e:
                    logger.warning(f"Ошибка парсинга результата Bing: {str(e)}")
            
            return results[:max_results]
        except Exception as e:
            logger.error(f"Ошибка Bing: {str(e)}")
            return []

    def get_full_page_content(self, url: str) -> str:
        """Получение полного текста страницы с улучшенным парсингом"""
        try:
            headers = {'User-Agent': random.choice(USER_AGENTS)}
            response = self.session.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            # Определяем кодировку
            if response.encoding == 'ISO-8859-1':
                response.encoding = 'utf-8'
            
            # Упрощенный парсинг основного контента
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Удаляем ненужные элементы
            for tag in soup(['script', 'style', 'footer', 'nav', 'aside', 'header']):
                tag.decompose()
            
            # Удаляем пустые элементы
            for tag in soup.find_all():
                if len(tag.get_text(strip=True)) == 0:
                    tag.decompose()
            
            # Извлекаем текст
            text = ' '.join(soup.stripped_strings)
            
            # Удаляем лишние пробелы
            text = re.sub(r'\s+', ' ', text)
            
            return text[:15000]  # Ограничение до 15k символов
            
        except Exception as e:
            logger.error(f"Ошибка получения контента для {url}: {str(e)}")
            return ""
