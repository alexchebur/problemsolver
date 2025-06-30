import streamlit as st
from duckduckgo_search import DDGS
import time
import random
import requests
from bs4 import BeautifulSoup
import tenacity  # Для повторных попыток

# Список User-Agent
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
]

def get_random_user_agent():
    return random.choice(USER_AGENTS)

@tenacity.retry(
    stop=tenacity.stop_after_attempt(3),
    wait=tenacity.wait_exponential(multiplier=1, max=10),
    retry=tenacity.retry_if_exception_type((requests.exceptions.ConnectionError, requests.exceptions.Timeout))
)
def safe_request(url, headers, params=None):
    return requests.get(url, headers=headers, params=params, timeout=15)

def duckduckgo_html_search(query, region='ru-ru', max_results=5):
    try:
        headers = {'User-Agent': get_random_user_agent()}
        params = {'q': query, 'kl': region}
        response = safe_request("https://html.duckduckgo.com/html/ ", headers=headers, params=params)
        response.raise_for_status()
        # Парсинг HTML...
        return results
    except Exception as e:
        return f"Ошибка DuckDuckGo: {str(e)}"

def mojeek_search(query, max_results=5):
    try:
        headers = {'User-Agent': get_random_user_agent()}
        params = {'q': query, 's': max_results}
        response = safe_request("https://www.mojeek.com/search ", headers=headers, params=params)
        response.raise_for_status()
        # Парсинг HTML...
        return results
    except Exception as e:
        return f"Ошибка Mojeek: {str(e)}"

def perform_search(query, region='ru-ru', max_results=8, max_snippet_length=3000):
    try:
        headers = {'User-Agent': get_random_user_agent()}
        with DDGS(headers=headers) as ddgs:  # Укажите заголовки
            results = []
            st.sidebar.subheader("Результаты поиска")
            
            # Используйте параметр backend="api" вместо "lite"
            for r in ddgs.text(
                query,
                region=region,
                max_results=max_results,
                backend="api"  # Изменено на актуальный backend
            ):
                snippet = r['body'][:500] + "..." if len(r['body']) > 500 else r['body']
                results.append(r)
                
                with st.sidebar.expander(f"🔍 {r['title']}"):
                    st.write(snippet)
                    st.caption(f"URL: {r['href']}")

            formatted = []
            for i, r in enumerate(results, 1):
                body = r['body'][:max_snippet_length] + "..." if len(r['body']) > max_snippet_length else r['body']
                formatted.append(f"Результат {i}: {r['title']}\n{body}\nURL: {r['href']}\n")
            
            return "\n\n".join(formatted)
    except Exception as e:
        st.sidebar.error(f"Ошибка поиска: {str(e)}")
        return f"Ошибка поиска: {str(e)}"
    if "Ошибка" in result:
        result = "Все поисковики недоступны. Попробуйте позже."
    return result
