import streamlit as st
from duckduckgo_search import DDGS
import time
import random

# Список популярных User-Agent строк для разных браузеров и устройств
USER_AGENTS = [
    # Chrome - Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    # Chrome - macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    # Firefox - Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    # Firefox - macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:126.0) Gecko/20100101 Firefox/126.0",
    # Safari
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    # Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
    # Mobile - Android Chrome
    "Mozilla/5.0 (Linux; Android 13; SM-S901B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.147 Mobile Safari/537.36",
    # Mobile - iOS Safari
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1"
]

def get_random_user_agent():
    """Возвращает случайный User-Agent из предопределенного списка"""
    return random.choice(USER_AGENTS)

def perform_search(query, region='ru-ru', max_results=5, max_snippet_length=3000, retries=3, delay=1.5):
    """
    Выполняет веб-поиск с ротацией User-Agent, задержками и обработкой ошибок
    
    Параметры:
    query - поисковый запрос
    region - регион для поиска
    max_results - максимальное количество результатов
    max_snippet_length - максимальная длина сниппета
    retries - количество попыток при ошибках
    delay - базовая задержка между попытками (секунды)
    
    Возвращает отформатированную строку с результатами
    """
    attempts = 0
    
    while attempts < retries:
        try:
            # Генерируем случайный User-Agent для каждого запроса
            headers = {'User-Agent': get_random_user_agent()}
            
            with DDGS(headers=headers) as ddgs:
                results = []
                st.sidebar.subheader("🔍 Результаты поиска")
                
                # Добавляем случайную задержку (0.5-2.5 сек)
                sleep_time = delay + random.uniform(-0.5, 1.0)
                time.sleep(max(0.5, sleep_time))
                
                try:
                    search_results = ddgs.text(
                        query,
                        region=region,
                        max_results=max_results,
                        backend="lite"
                    )
                except Exception as e:
                    st.sidebar.warning(f"⚠️ Ошибка поиска: {str(e)}")
                    continue  # Попробуем еще раз
                
                if not search_results:
                    st.sidebar.info("🔍 Поиск не вернул результатов")
                    return "Поиск не вернул результатов"
                
                for i, r in enumerate(search_results, 1):
                    # Пропускаем неполные результаты
                    if 'body' not in r or not r['body']:
                        continue
                    
                    # Форматируем сниппет для отображения
                    snippet = r['body'][:500] + "..." if len(r['body']) > 500 else r['body']
                    results.append(r)
                    
                    # Выводим в сайдбар
                    with st.sidebar.expander(f"📄 {r.get('title', 'Без названия')}"):
                        st.write(snippet)
                        st.caption(f"URL: {r.get('href', '')}")
                
                # Форматируем результаты для возврата
                formatted = []
                for i, r in enumerate(results, 1):
                    body = r.get('body', '')[:max_snippet_length]
                    if len(body) > max_snippet_length:
                        body = body[:max_snippet_length] + "..."
                        
                    formatted.append(f"Результат {i}: {r.get('title', '')}\n{body}\nURL: {r.get('href', '')}\n")
                
                return "\n\n".join(formatted)
        
        except Exception as e:
            attempts += 1
            error_msg = f"⛔ Ошибка (попытка {attempts}/{retries}): {str(e)}"
            st.sidebar.error(error_msg)
            
            if attempts < retries:
                # Экспоненциальная задержка с рандомизацией
                sleep_time = delay * (2 ** attempts) + random.uniform(0, 2)
                time.sleep(sleep_time)
    
    # Если все попытки закончились неудачей
    st.sidebar.error("❌ Поиск не удался после нескольких попыток")
    return "Ошибка поиска: не удалось получить результаты"
