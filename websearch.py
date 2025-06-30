import streamlit as st
from duckduckgo_search import DDGS
import time
import random

def perform_search(query, region='ru-ru', max_results=8, max_snippet_length=3000, retries=3, delay=2):
    """
    Выполняет веб-поиск с обработкой ошибок и повторами
    
    Параметры:
    query - поисковый запрос
    region - регион для поиска
    max_results - максимальное количество результатов
    max_snippet_length - максимальная длина сниппета
    retries - количество попыток при ошибках
    delay - базовая задержка между попытками (секунды)
    
    Возвращает отформатированную строку с результатами
    """
    results_formatted = ""
    attempts = 0
    
    while attempts < retries:
        try:
            with DDGS() as ddgs:
                results = []
                st.sidebar.subheader("🔍 Результаты поиска")
                
                # Собираем результаты
                for r in ddgs.text(
                    query,
                    region=region,
                    max_results=max_results,
                    backend="lite"
                ):
                    # Ограничиваем длину сниппета для отображения
                    snippet = r['body'][:500] + "..." if len(r['body']) > 500 else r['body']
                    results.append(r)
                    
                    # Отображаем каждый результат в сайдбаре
                    with st.sidebar.expander(f"📄 {r['title']}"):
                        st.write(snippet)
                        st.caption(f"URL: {r['href']}")
                
                # Форматируем результаты для возврата
                for i, r in enumerate(results, 1):
                    body = r['body'][:max_snippet_length] + "..." if len(r['body']) > max_snippet_length else r['body']
                    results_formatted += f"### Результат {i}: {r['title']}\n\n{body}\n\nURL: {r['href']}\n\n\n"
                
                return results_formatted
        
        except Exception as e:
            attempts += 1
            error_msg = f"⚠️ Ошибка поиска (попытка {attempts}/{retries}): {str(e)}"
            st.sidebar.error(error_msg)
            
            if attempts < retries:
                # Экспоненциальная задержка с джиттером
                sleep_time = delay * (2 ** attempts) + random.uniform(0, 1)
                time.sleep(sleep_time)
    
    # Если все попытки закончились неудачей
    st.sidebar.error("❌ Поиск не удался после нескольких попыток")
    return "Ошибка поиска: не удалось получить результаты"
