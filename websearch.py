import streamlit as st
from duckduckgo_search import DDGS
import time
import random
import requests
from bs4 import BeautifulSoup

# Список популярных User-Agent строк
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
    "Mozilla/5.0 (Linux; Android 13; SM-S901B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.147 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1"
]

def get_random_user_agent():
    """Возвращает случайный User-Agent"""
    return random.choice(USER_AGENTS)

def get_full_snippet(url):
    """Получает полный текст страницы для сниппета"""
    try:
        headers = {'User-Agent': get_random_user_agent()}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Удаляем ненужные элементы
        for tag in soup(['script', 'style', 'header', 'footer', 'nav', 'aside']):
            tag.decompose()
        
        # Извлекаем основной контент
        main_content = soup.find('main') or soup.find('article') or soup.body
        
        # Очищаем текст
        text = main_content.get_text(separator=' ', strip=True)
        return text[:1000] + "..." if len(text) > 1000 else text
    
    except:
        return None

def perform_search(query, region='ru-ru', max_results=5, max_snippet_length=1000):
    """Выполняет поиск с улучшенной обработкой ошибок и обходом блокировок"""
    st.sidebar.subheader("🔍 Результаты поиска")
    start_time = time.time()
    
    # Пробуем разные бэкенды
    backends = ["lite", "api"]
    results = []
    
    for backend in backends:
        try:
            headers = {'User-Agent': get_random_user_agent()}
            
            # Случайная задержка перед запросом
            time.sleep(random.uniform(1.0, 3.0))
            
            with DDGS(headers=headers) as ddgs:
                search_results = ddgs.text(
                    query,
                    region=region,
                    max_results=max_results,
                    backend=backend
                )
                
                if not search_results:
                    continue
                    
                # Обрабатываем результаты
                for r in search_results:
                    # Получаем полный сниппет при необходимости
                    snippet = r.get('body', '')[:500] + "..." if len(r.get('body', '')) > 500 else r.get('body', '')
                    full_snippet = get_full_snippet(r.get('href', ''))
                    display_snippet = full_snippet if full_snippet else snippet
                    
                    # Добавляем результат
                    results.append({
                        'title': r.get('title', 'Без названия'),
                        'snippet': display_snippet,
                        'url': r.get('href', '')
                    })
                    
                    # Отображаем в сайдбаре
                    with st.sidebar.expander(f"🔍 {r.get('title', 'Без названия')}"):
                        st.write(display_snippet)
                        st.caption(f"URL: {r.get('href', '')}")
                
                # Форматируем результаты для возврата
                formatted = []
                for i, r in enumerate(results, 1):
                    body = r['snippet'][:max_snippet_length] + "..." if len(r['snippet']) > max_snippet_length else r['snippet']
                    formatted.append(f"Результат {i}: {r['title']}\n{body}\nURL: {r['url']}\n")
                
                st.sidebar.success(f"Найдено {len(results)} результатов за {time.time()-start_time:.1f} сек")
                return "\n\n".join(formatted)
                
        except Exception as e:
            st.sidebar.warning(f"⚠️ Ошибка в бэкенде {backend}: {str(e)}")
            time.sleep(2)  # Задержка перед следующей попыткой
    
    # Если все бэкенды не сработали
    st.sidebar.error("❌ Не удалось выполнить поиск")
    return "Ошибка поиска: все методы недоступны"
