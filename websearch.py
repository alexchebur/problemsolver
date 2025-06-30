import streamlit as st
from duckduckgo_search import DDGS
import time
import random
from fake_useragent import UserAgent

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
    ua = UserAgent()
    attempts = 0
    
    while attempts < retries:
        try:
            # Генерируем случайный User-Agent для каждого запроса
            headers = {'User-Agent': ua.random}
            
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
