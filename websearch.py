import streamlit as st
from duckduckgo_search import DDGS
import time
import random  # ✅ Теперь random импортирован
import requests
from bs4 import BeautifulSoup
import urllib.parse

# Список популярных User-Agent строк
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15.7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36 Edg/125.0.0.0",
    "Mozilla/5.0 (Linux; Android 13; SM-S901B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.147 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1"
]

# ✅ Добавлена проверка и обработка ошибок для random
def get_random_user_agent():
    """Возвращает случайный User-Agent"""
    try:
        return random.choice(USER_AGENTS)
    except IndexError:
        return USER_AGENTS[0]  # Вернуть первый User-Agent, если возникла проблема

def get_random_delay(min_delay=2.0, max_delay=5.0):
    """Возвращает случайную задержку для анти-бан системы"""
    return random.uniform(min_delay, max_delay)

# ✅ Исправлены URL (удалены лишние пробелы)
def duckduckgo_html_search(query, region='ru-ru', max_results=5):
    """Альтернативный метод поиска через HTML DuckDuckGo"""
    try:
        headers = {'User-Agent': get_random_user_agent()}
        params = {
            'q': query,
            'kl': region,
        }
        
        response = requests.get(
            'https://html.duckduckgo.com/html/ ',
            headers=headers,
            params=params,
            timeout=15
        )
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = soup.find_all('div', class_='result')
        
        formatted = []
        count = 0
        
        for result in results:
            if count >= max_results:
                break
                
            title_elem = result.find('a', class_='result__a')
            snippet_elem = result.find('a', class_='result__snippet')
            url_elem = result.find('a', class_='result__url')
            
            if not title_elem or not snippet_elem:
                continue
                
            title = title_elem.text.strip()
            snippet = snippet_elem.text.strip()[:500]
            url = url_elem['href'] if url_elem and 'href' in url_elem.attrs else '#'
            
            # Исправляем относительные ссылки
            if url.startswith('/'):
                url = 'https://duckduckgo.com ' + url
            
            # Отображаем в сайдбаре
            with st.sidebar.expander(f"🦆 {title}"):
                st.write(snippet)
                st.caption(f"URL: {url}")
            
            formatted.append(f"Результат {count+1} (DuckDuckGo HTML): {title}\n{snippet}\nURL: {url}\n")
            count += 1
            
        return "\n\n".join(formatted) if formatted else "DuckDuckGo HTML: результаты не найдены"
    
    except Exception as e:
        return f"Ошибка DuckDuckGo HTML: {str(e)}"

# ✅ Добавлен новый метод поиска через Brave Search (без токена)
def brave_search(query, region='ru', max_results=5):
    """Поиск через Brave Search (требуется установка brave_search)"""
    try:
        from brave_search import search
        results = search(query, count=max_results, country=region)
        
        formatted = []
        for i, result in enumerate(results, 1):
            title = result.get('title', '')
            url = result.get('url', '')
            snippet = result.get('snippet', '')[:500] + "..." if result.get('snippet') else ''
            
            with st.sidebar.expander(f"🌐 {title}"):
                st.write(snippet)
                st.caption(f"URL: {url}")
            
            formatted.append(f"Результат {i} (Brave): {title}\n{snippet}\nURL: {url}\n")
        
        return "\n\n".join(formatted) if formatted else "Brave: результаты не найдены"
    
    except ImportError:
        return "Brave Search: библиотека не установлена"
    except Exception as e:
        return f"Ошибка Brave Search: {str(e)}"

# ✅ Добавлен новый метод поиска через Searx (публичный экземпляр)
def searx_search(query, max_results=5):
    """Поиск через публичный Searx (без токена)"""
    try:
        headers = {'User-Agent': get_random_user_agent()}
        params = {
            'q': query,
            'format': 'json',
            'limit': max_results
        }
        
        response = requests.get(
            'https://searx.be/search ',
            headers=headers,
            params=params,
            timeout=15
        )
        response.raise_for_status()
        data = response.json()
        
        formatted = []
        for i, result in enumerate(data.get('results', [])[:max_results], 1):
            title = result.get('title', '')
            url = result.get('url', '')
            snippet = result.get('content', '')[:500] + "..." if result.get('content') else ''
            
            with st.sidebar.expander(f"🔍 {title}"):
                st.write(snippet)
                st.caption(f"URL: {url}")
            
            formatted.append(f"Результат {i} (Searx): {title}\n{snippet}\nURL: {url}\n")
        
        return "\n\n".join(formatted) if formatted else "Searx: результаты не найдены"
    
    except Exception as e:
        return f"Ошибка Searx: {str(e)}"

def perform_search(query, region='ru-ru', max_results=5, max_snippet_length=800):
    """Ультра-надежная функция поиска с множественными fallback'ами"""
    st.sidebar.subheader("🔍 Результаты поиска")
    start_time = time.time()
    
    # Попытка 1: DuckDuckGo API
    try:
        headers = {'User-Agent': get_random_user_agent()}
        
        # Большая задержка перед запросом
        time.sleep(get_random_delay(3.0, 6.0))
        
        with DDGS(headers=headers, timeout=25) as ddgs:
            search_results = ddgs.text(
                query,
                region=region,
                max_results=max_results,
                backend="api"
            )
            
            if search_results:
                formatted = []
                for i, r in enumerate(search_results, 1):
                    if 'body' not in r or not r['body'] or 'title' not in r or 'href' not in r:
                        continue
                    
                    snippet = r['body'][:500] + "..." if len(r['body']) > 500 else r['body']
                    
                    with st.sidebar.expander(f"🔍 {r['title']}"):
                        st.write(snippet)
                        st.caption(f"URL: {r['href']}")
                    
                    body = r['body'][:max_snippet_length] + "..." if len(r['body']) > max_snippet_length else r['body']
                    formatted.append(f"Результат {i} (DDG API): {r['title']}\n{body}\nURL: {r['href']}\n")
                
                if formatted:
                    st.sidebar.success(f"Найдено {len(formatted)} результатов за {time.time()-start_time:.1f} сек")
                    return "\n\n".join(formatted)
    except Exception as e:
        st.sidebar.warning(f"⚠️ Ошибка DuckDuckGo API: {str(e)}")
    
    # Попытка 2: DuckDuckGo HTML
    try:
        time.sleep(get_random_delay(2.0, 4.0))
        html_result = duckduckgo_html_search(query, region, max_results)
        if "Ошибка" not in html_result and "не найдены" not in html_result:
            st.sidebar.success(f"DuckDuckGo HTML: найдено за {time.time()-start_time:.1f} сек")
            return html_result
    except Exception as e:
        st.sidebar.warning(f"⚠️ Ошибка DuckDuckGo HTML: {str(e)}")
    
    # Попытка 3: Brave Search
    try:
        st.sidebar.warning("⚠️ Пробуем Brave Search...")
        time.sleep(get_random_delay(1.0, 3.0))
        brave_result = brave_search(query, region[:2], max_results)
        if "Ошибка" not in brave_result and "не найдены" not in brave_result:
            st.sidebar.success(f"Brave: найдено за {time.time()-start_time:.1f} сек")
            return brave_result
    except Exception as e:
        st.sidebar.warning(f"⚠️ Ошибка Brave Search: {str(e)}")
    
    # Попытка 4: Searx
    try:
        st.sidebar.warning("⚠️ Пробуем Searx...")
        time.sleep(get_random_delay(1.0, 3.0))
        searx_result = searx_search(query, max_results)
        if "Ошибка" not in searx_result and "не найдены" not in searx_result:
            st.sidebar.success(f"Searx: найдено за {time.time()-start_time:.1f} сек")
            return searx_result
    except Exception as e:
        st.sidebar.warning(f"⚠️ Ошибка Searx: {str(e)}")
    
    # Попытка 5: Резервный поиск через Mojeek
    try:
        st.sidebar.warning("⚠️ Пробуем резервный поисковик...")
        time.sleep(get_random_delay(1.0, 3.0))
        headers = {'User-Agent': get_random_user_agent()}
        params = {
            "q": query,
            "s": max_results
        }
        
        response = requests.get(
            "https://www.mojeek.com/search ",
            headers=headers,
            params=params,
            timeout=15
        )
        response.raise_for_status()
        data = response.text
        soup = BeautifulSoup(data, 'html.parser')
        results = soup.find_all('li', class_='res')
        
        formatted = []
        count = 0
        
        for result in results:
            if count >= max_results:
                break
                
            title_elem = result.find('h2', class_='title')
            snippet_elem = result.find('div', class_='s')
            url_elem = title_elem.find('a') if title_elem else None
            
            if not title_elem or not snippet_elem or not url_elem:
                continue
                
            title = title_elem.text.strip()
            snippet = snippet_elem.text.strip()[:500]
            url = url_elem['href'] if 'href' in url_elem.attrs else '#'
            
            with st.sidebar.expander(f"🌐 {title}"):
                st.write(snippet)
                st.caption(f"URL: {url}")
            
            formatted.append(f"Результат {count+1} (Mojeek): {title}\n{snippet}\nURL: {url}\n")
            count += 1
        
        if formatted:
            st.sidebar.success(f"Mojeek: найдено за {time.time()-start_time:.1f} сек")
            return "\n\n".join(formatted)
    except Exception as e:
        st.sidebar.warning(f"⚠️ Ошибка Mojeek: {str(e)}")
    
    # Если все методы не сработали
    st.sidebar.error("❌ Все поисковые системы недоступны")
    return "Поиск не дал результатов. Пожалуйста, попробуйте позже."
