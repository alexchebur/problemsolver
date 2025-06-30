import streamlit as st
import requests
import time
import random

# Список популярных User-Agent строк
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0"
]

def get_random_user_agent():
    """Возвращает случайный User-Agent"""
    return random.choice(USER_AGENTS)

def duckduckgo_search(query, region='ru-ru', max_results=5, max_snippet_length=500):
    """Поиск через DuckDuckGo с улучшенной обработкой ошибок"""
    try:
        headers = {'User-Agent': get_random_user_agent()}
        params = {
            'q': query,
            'kl': region,
        }
        
        response = requests.get(
            'https://html.duckduckgo.com/html/',
            headers=headers,
            params=params,
            timeout=10
        )
        response.raise_for_status()
        
        from bs4 import BeautifulSoup
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
            snippet = snippet_elem.text.strip()[:max_snippet_length]
            url = url_elem['href'] if url_elem and 'href' in url_elem.attrs else '#'
            
            # Отображаем в сайдбаре
            with st.sidebar.expander(f"🦆 {title}"):
                st.write(snippet)
                st.caption(f"URL: {url}")
            
            formatted.append(f"Результат {count+1} (DuckDuckGo): {title}\n{snippet}\nURL: {url}\n")
            count += 1
            
        return "\n\n".join(formatted) if formatted else "DuckDuckGo: результаты не найдены"
    
    except Exception as e:
        return f"Ошибка DuckDuckGo: {str(e)}"

def mojeek_search(query, max_results=5):
    """Поиск через Mojeek"""
    try:
        headers = {'User-Agent': get_random_user_agent()}
        params = {
            "q": query,
            "format": "json",
            "t": "web",
            "s": max_results
        }
        
        response = requests.get(
            "https://www.mojeek.com/search",
            headers=headers,
            params=params,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        formatted = []
        for i, result in enumerate(data.get('results', [])[:max_results], 1):
            title = result.get('title', '')
            url = result.get('url', '')
            snippet = (result.get('desc', '')[:500] + "...") if result.get('desc') else ''
            
            with st.sidebar.expander(f"🌐 {title}"):
                st.write(snippet)
                st.caption(f"URL: {url}")
            
            formatted.append(f"Результат {i} (Mojeek): {title}\n{snippet}\nURL: {url}\n")
        
        return "\n\n".join(formatted) if formatted else "Mojeek: результаты не найдены"
    
    except Exception as e:
        return f"Ошибка Mojeek: {str(e)}"

SEARXNG_INSTANCES = [
    "https://searx.work",
    "https://search.us.projectsegfau.lt",
    "https://searx.be",
    "https://searx.nixnet.services",
    "https://searx.tiekoetter.com"
]

def searxng_search(query, max_results=5):
    """Поиск через случайный инстанс SearXNG"""
    headers = {'User-Agent': get_random_user_agent()}
    
    for instance in random.sample(SEARXNG_INSTANCES, len(SEARXNG_INSTANCES)):
        try:
            url = f"{instance}/search"
            params = {
                "q": query,
                "format": "json",
                "language": "ru-RU"
            }
            
            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=8
            )
            response.raise_for_status()
            data = response.json()
            
            formatted = []
            for i, result in enumerate(data.get('results', [])[:max_results], 1):
                title = result.get('title', '')
                url = result.get('url', '')
                snippet = (result.get('content', '')[:500] + "...") if result.get('content') else ''
                
                with st.sidebar.expander(f"🔍 {title}"):
                    st.write(snippet)
                    st.caption(f"URL: {url}")
                
                formatted.append(f"Результат {i} (SearXNG): {title}\n{snippet}\nURL: {url}\n")
            
            return "\n\n".join(formatted) if formatted else "SearXNG: результаты не найдены"
        
        except Exception as e:
            st.sidebar.warning(f"Инстанс {instance} недоступен: {str(e)}")
            continue
    
    return "Все SearXNG-инстансы недоступны"

def perform_search(query, region='ru-ru', max_results=5):
    """Выполняет поиск с многоуровневым fallback"""
    st.sidebar.subheader("🔍 Результаты поиска")
    start_time = time.time()
    
    # Пробуем DuckDuckGo
    result = duckduckgo_search(query, region, max_results)
    if "Ошибка" not in result and "не найдены" not in result:
        st.sidebar.success(f"DuckDuckGo: найдено за {time.time()-start_time:.1f} сек")
        return result
    
    # Fallback 1: Mojeek
    st.sidebar.warning("⚠️ DuckDuckGo недоступен, пробуем Mojeek...")
    result = mojeek_search(query, max_results)
    if "Ошибка" not in result and "не найдены" not in result:
        st.sidebar.success(f"Mojeek: найдено за {time.time()-start_time:.1f} сек")
        return result
    
    # Fallback 2: SearXNG
    st.sidebar.warning("⚠️ Mojeek недоступен, пробуем SearXNG...")
    result = searxng_search(query, max_results)
    if "Ошибка" not in result and "не найдены" not in result and "недоступны" not in result:
        st.sidebar.success(f"SearXNG: найдено за {time.time()-start_time:.1f} сек")
        return result
    
    # Все методы не сработали
    st.sidebar.error("❌ Все поисковые системы недоступны")
    return "Поиск не дал результатов. Пожалуйста, попробуйте позже."
