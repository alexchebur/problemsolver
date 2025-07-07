import streamlit as st
import google.generativeai as genai
import time
import requests
import traceback
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import random
import base64
import os
from datetime import datetime
from bs4 import BeautifulSoup
from websearch import WebSearcher
from typing import List, Tuple
import re
from report import create_html_report
from prompts import (
    PROMPT_FORMULATE_PROBLEM_AND_QUERIES,
    PROMPT_APPLY_COGNITIVE_METHOD,
    PROMPT_GENERATE_REFINEMENT_QUERIES,
    PROMPT_GENERATE_FINAL_CONCLUSIONS
)
from converters import (
    convert_uploaded_file_to_markdown, 
    convert_excel_to_markdown_for_analysis  # Добавьте эту строку
)

# Настройка API
api_key = st.secrets['GEMINI_API_KEY']
if not api_key:
    st.warning("Пожалуйста, введите API-ключ")
    st.stop()

genai.configure(
    api_key=api_key,
    transport='rest',
    client_options={
        'api_endpoint': 'generativelanguage.googleapis.com/'
    }
)

# Создаем экземпляр поисковика
searcher = WebSearcher()

# Глобальные переменные состояния
if 'current_doc_text' not in st.session_state:
    st.session_state.current_doc_text = ""
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'report_content' not in st.session_state:
    st.session_state.report_content = None
if 'problem_formulation' not in st.session_state:
    st.session_state.problem_formulation = ""
if 'generated_queries' not in st.session_state:
    st.session_state.generated_queries = []
if 'search_results' not in st.session_state:
    st.session_state.search_results = ""
if 'internal_dialog' not in st.session_state:
    st.session_state.internal_dialog = ""
# Добавляем новое состояние для анализа временных рядов
if 'time_series_analysis' not in st.session_state:
    st.session_state.time_series_analysis = None

# Модель
model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-06-17')

# Когнитивные методики
CORE_METHODS = [
    "First Principles Thinking",
    "Pareto Principle (80/20 Rule)",
    "Occam's Razor",
    "System 1 vs System 2 Thinking",
    "Second-Order Thinking"
]

ADDITIONAL_METHODS = [
    "Inversion (thinking backwards)",
    "Opportunity Cost",
    "Margin of Diminishing Returns",
    "Hanlon's Razor",
    "Confirmation Bias",
    "Availability Heuristic",
    "Parkinson's Law",
    "Loss Aversion",
    "Switching Costs",
    "Circle of Competence",
    "Regret Minimization",
    "Leverage Points",
    "Lindy Effect",
    "Game Theory",
    "Antifragility",
    "Теории Решения Изобретательских задач"
]

# Конфигурация контекста для разных этапов
CONTEXT_CONFIG = {
    'problem_formulation': {
        'doc_text': True,
        'original_query': True,
        'search_results': False,
        'method_results': False,
        'time_series': False  # Новое поле
    },
    'cognitive_method': {
        'doc_text': True,
        'original_query': True,
        'search_results': True,
        'method_results': False,
        'time_series': True   # Новое поле
    },
    'refinement_queries': {
        'doc_text': False,
        'original_query': True,
        'search_results': True,
        'method_results': True,
        'time_series': True   # Новое поле
    },
    'final_conclusions': {
        'doc_text': False,
        'original_query': True,
        'search_results': True,
        'method_results': True,
        'time_series': True   # Новое поле
    }
}

def get_current_date():
    return datetime.now().strftime("%Y-%m-%d")

def build_context(context_type: str) -> str:
    """Собирает контекст для указанного типа запроса"""
    config = CONTEXT_CONFIG[context_type]
    context_parts = []
    
    if config['doc_text'] and st.session_state.current_doc_text:
        context_parts.append(f"Документ: {st.session_state.current_doc_text[:100000]}")
    
    if config['original_query'] and 'input_query' in st.session_state:
        context_parts.append(f"Исходный запрос: {st.session_state.input_query}")
    
    if config['search_results'] and st.session_state.search_results:
        context_parts.append(f"Результаты поиска: {st.session_state.search_results[:20000]}")
    
    if config['method_results'] and hasattr(st.session_state, 'method_results'):
        method_results = "\n\n".join(
            [f"{method}:\n{result}" for method, result in st.session_state.method_results.items()]
        )
        context_parts.append(f"Анализ методик: {method_results[:10000]}")
    
    # Добавляем анализ временных рядов в контекст
    if config['time_series'] and st.session_state.time_series_analysis:
        context_parts.append(f"Анализ временных рядов: {st.session_state.time_series_analysis}")
    
    return "\n\n".join(context_parts)

# Новая функция для анализа временных рядов
def analyze_time_series(file_content: bytes) -> str:
    """Анализирует данные временных рядов из Excel файла и генерирует отчет"""
    try:
        # Конвертируем Excel в Markdown с сохранением структуры
        markdown_data = convert_excel_to_markdown_for_analysis(file_content)
        
        analytic_prompt = f"""
**Задача:** Проведи комплексный анализ временных рядов по следующей схеме: 
1. Дескриптивная статистика (среднее, медиана, стандартное отклонение)
2. Выявление аномалий и выбросов
3. Анализ корреляций (включая кросс-корреляции и запаздывающие)
4. Анализ трендов (линейные/нелинейные, точки изменения)
5. Сезонные компоненты
6. Прогноз на 3-5 периодов с доверительными интервалами
7. Интеграция с контекстом проблемы

**Требования:**
- Использовать профессиональные методы анализа временных рядов
- Интерпретировать результаты в контексте исходной проблемы
- Предложить рекомендации для принятия решений

**Контекст проблемы:**
{st.session_state.problem_formulation}

**Структура данных:**
{markdown_data}
"""
        
        response = model.generate_content(
            analytic_prompt,
            generation_config={
                "temperature": st.session_state.temperature * 0.7,
                "max_output_tokens": 10000
            },
            request_options={'timeout': 240}
        )
        return response.text
    except Exception as e:
        return f"Ошибка при анализе временных рядов: {str(e)}\n\n{traceback.format_exc()}"



def formulate_problem_and_queries():
    """Этап 1: Формулирование проблемы и генерация поисковых запросов"""
    context = build_context('problem_formulation')
    
    prompt = PROMPT_FORMULATE_PROBLEM_AND_QUERIES.format(
        query=st.session_state.input_query.strip(),
        doc_text=st.session_state.current_doc_text[:200000] if st.session_state.current_doc_text else "Нет документа"
    )
    
    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": st.session_state.temperature,
                "max_output_tokens": 4000
            },
            request_options={'timeout': 120}
        )
        
        result = response.text
        
        problem = ""
        internal_dialog = ""
        queries = []
        
        if "ПРОБЛЕМА:" in result:
            problem_part = result.split("ПРОБЛЕМА:")[1]
            if "РАССУЖДЕНИЯ:" in problem_part:
                problem = problem_part.split("РАССУЖДЕНИЯ:")[0].strip()
                internal_dialog_part = problem_part.split("РАССУЖДЕНИЯ:")[1]
                if "ЗАПРОСЫ:" in internal_dialog_part:
                    internal_dialog = internal_dialog_part.split("ЗАПРОСЫ:")[0].strip()
                    queries_part = internal_dialog_part.split("ЗАПРОСЫ:")[1]
                    for line in queries_part.split('\n'):
                        if line.strip() and line.strip()[0].isdigit():
                            query_text = line.split('.', 1)[1].strip() if '. ' in line else line.strip()
                            queries.append(query_text)
        
        if not problem:
            problem = result
        if not queries:
            last_lines = result.split('\n')[-10:]
            for line in last_lines:
                if line.strip() and line.strip()[0].isdigit() and '.' in line:
                    query_text = line.split('.', 1)[1].strip()
                    queries.append(query_text)
            if len(queries) > 5:
                queries = queries[:5]
        
        st.session_state.problem_formulation = problem
        st.session_state.internal_dialog = internal_dialog
        st.session_state.generated_queries = queries[:5]
        
        return result, queries
        
    except Exception as e:
        st.error(f"Ошибка при формулировании проблемы: {str(e)}")
        return f"Ошибка: {str(e)}", []

def apply_cognitive_method(method_name: str):
    """Применяет когнитивную методику к проблеме"""
    context = build_context('cognitive_method')
    
    prompt = PROMPT_APPLY_COGNITIVE_METHOD.format(
        method_name=method_name,
        problem_formulation=st.session_state.problem_formulation,
        context=context
    )
    
    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": st.session_state.temperature,
                "max_output_tokens": 12000
            },
            request_options={'timeout': 180}
        )
        return response.text
    except Exception as e:
        return f"Ошибка при применении {method_name}: {str(e)}"

def generate_refinement_queries() -> List[str]:
    """Генерирует уточняющие поисковые запросы на основе контекста"""
    context = build_context('refinement_queries')
    
    prompt = PROMPT_GENERATE_REFINEMENT_QUERIES.format(
        context=context[:100000]
    )
    
    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": st.session_state.temperature * 0.5,
                "max_output_tokens": 2000
            },
            request_options={'timeout': 90}
        )
        result = response.text
        
        queries = []
        for line in result.split('\n'):
            if line.strip() and line.strip()[0].isdigit():
                query_text = line.split('.', 1)[1].strip() if '. ' in line else line.strip()
                queries.append(query_text)
        
        return queries[:5]
        
    except Exception as e:
        st.error(f"Ошибка при генерации уточняющих запросов: {str(e)}")
        return []

def generate_final_conclusions() -> str:
    """Генерирует итоговые выводы на основе проблемы и контекста анализа"""
    context = build_context('final_conclusions')
    
    prompt = PROMPT_GENERATE_FINAL_CONCLUSIONS.format(
        problem_formulation=st.session_state.problem_formulation,
        analysis_context=context[:100000]
    )
    
    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": st.session_state.temperature * 0.7,
                "max_output_tokens": 9000
            },
            request_options={'timeout': 120}
        )
        return response.text
    except Exception as e:
        return f"Ошибка при генерации выводов: {str(e)}"

def generate_response():
    st.session_state.processing = True
    st.session_state.report_content = None
    status_area = st.empty()
    progress_bar = st.progress(0)

    try:
        try:
            test_response = requests.get("https://www.google.com", timeout=10)
            st.info(f"Сетевая доступность: {'OK' if test_response.status_code == 200 else 'Проблемы'}")
        except Exception as e:
            st.error(f"Сетевая ошибка: {str(e)}")

        query = st.session_state.input_query.strip()
        if not query:
            status_area.warning("⚠️ Введите запрос")
            return

        status_area.info("🔍 Формулирую проблему и генерирую поисковые запросы...")
        problem_result, queries = formulate_problem_and_queries()
        if not queries:
            queries = [query]
            st.warning("⚠️ Использован исходный запрос для поиска (LLM не сгенерировал запросы)")
        
        if st.session_state.internal_dialog:
            st.sidebar.subheader("🧠 Рассуждения ИИ")
            st.sidebar.text_area(
                "",
                value=st.session_state.internal_dialog,
                height=300,
                label_visibility="collapsed"
            )
        else:
            st.sidebar.warning("Рассуждения не были сгенерированы")
        
        with st.expander("✅ Этап 1: Формулировка проблемы", expanded=False):
            st.subheader("Сформулированная проблема")
            st.write(st.session_state.problem_formulation)
            
            st.subheader("Сгенерированные поисковые запросы")
            st.write(queries)
            
            st.subheader("Полный вывод LLM")
            st.code(problem_result, language='text')
        
        full_report = f"### Этап 1: Формулировка проблемы ###\n\n{problem_result}\n\n"
        full_report += f"Сформулированная проблема: {st.session_state.problem_formulation}\n\n"
        full_report += f"Рассуждения:\n{st.session_state.internal_dialog}\n\n"
        full_report += f"Поисковые запросы:\n" + "\n".join([f"{i+1}. {q}" for i, q in enumerate(queries)]) + "\n\n"

        status_area.info("🔍 Выполняю поиск информации...")
        all_search_results = ""
        
        for i, search_query in enumerate(queries):
            try:
                clean_query = search_query.replace('"', '').strip()
                search_result_list = searcher.perform_search(clean_query, max_results=3, full_text=True)
                
                formatted_results = []
                for j, r in enumerate(search_result_list, 1):
                    content = r.get('full_content', r.get('snippet', ''))
                    formatted_results.append(
                        f"Результат {j}: {r.get('title', '')}\n"
                        f"Контент: {content[:5000]}{'...' if len(content) > 5000 else ''}\n"
                        f"URL: {r.get('url', '')}\n"
                    )

                search_result_str = "\n\n".join(formatted_results)
                all_search_results += f"### Результаты по запросу '{search_query}':\n\n{search_result_str}\n\n"
                
                st.sidebar.subheader(f"🔍 Результаты по запросу: '{search_query}'")
                for j, r in enumerate(search_result_list, 1):
                    title = r.get('title', 'Без названия')
                    url = r.get('url', '')
                    snippet = r.get('snippet', '')

                    if url and not url.startswith('http'):
                        url = 'https://' + url

                    st.sidebar.markdown(f"**{j}. {title}**")
                    if url:
                        st.sidebar.markdown(f"[{url}]({url})")
                    if snippet:
                        st.sidebar.caption(snippet[:300] + ('...' if len(snippet) > 300 else ''))
                    st.sidebar.write("---")
                
            except Exception as e:
                st.error(f"Ошибка поиска для запроса '{search_query}': {str(e)}")
                all_search_results += f"### Ошибка поиска для запроса '{search_query}': {str(e)}\n\n"
        
        st.session_state.search_results = all_search_results
        
        status_area.info("⚙️ Применяю когнитивные методики...")
        
        all_methods = CORE_METHODS.copy()
        if st.session_state.selected_methods:
            all_methods += [m for m in st.session_state.selected_methods if m not in CORE_METHODS]
        
        st.session_state.method_results = {}
        
        for i, method in enumerate(all_methods):
            progress = int((i + 1) / (len(all_methods) + 1) * 100)
            progress_bar.progress(progress)
            
            status_area.info(f"⚙️ Применяю {method}...")
            try:
                result = apply_cognitive_method(method)
                st.session_state.method_results[method] = result
                
                st.subheader(f"✅ {method}")
                st.text_area("", value=result, height=300, label_visibility="collapsed")
                
                full_report += f"### Методика: {method} ###\n\n{result}\n\n"
            except Exception as e:
                st.error(f"Ошибка при применении {method}: {str(e)}")
                full_report += f"### Ошибка при применении {method}: {str(e)}\n\n"
            
            time.sleep(1)
        
        status_area.info("🔍 Выполняю уточняющий поиск...")
        refinement_search_results = ""
    
        refinement_queries = generate_refinement_queries()
    
        if refinement_queries:
            st.sidebar.subheader("🔎 Уточняющие запросы")
            for i, query in enumerate(refinement_queries):
                st.sidebar.write(f"{i+1}. {query}")
            
            for i, query in enumerate(refinement_queries):
                try:
                    clean_query = query.replace('"', '').strip()
                    search_results = searcher.perform_search(clean_query, max_results=2, full_text=True)
                
                    formatted = []
                    for j, r in enumerate(search_results, 1):
                        content = r.get('full_content', r.get('snippet', ''))
                        formatted.append(
                            f"Результат {j}: {r.get('title', '')}\n"
                            f"Контент: {content[:3000]}{'...' if len(content) > 3000 else ''}\n"
                            f"URL: {r.get('url', '')}\n"
                        )
                
                    refinement_search_results += f"### Уточняющий запрос '{query}':\n\n"
                    refinement_search_results += "\n\n".join(formatted) + "\n\n"
                
                except Exception as e:
                    refinement_search_results += f"### Ошибка поиска для '{query}': {str(e)}\n\n"
    
        status_area.info("📝 Формирую итоговые выводы...")
        progress_bar.progress(95)
        try:
            conclusions = generate_final_conclusions()
            
            st.subheader("📝 Итоговые выводы")
            st.text_area("", value=conclusions, height=400, label_visibility="collapsed")
            
            full_report += f"### Итоговые выводы ###\n\n{conclusions}\n\n"
        except Exception as e:
            st.error(f"Ошибка при генерации выводов: {str(e)}")
            full_report += f"### Ошибка при генерации выводов: {str(e)}\n\n"
        
        st.session_state.report_content = full_report
        progress_bar.progress(100)
        status_area.success("✅ Обработка завершена!")
        
    except Exception as e:
        st.error(f"💥 Критическая ошибка: {str(e)}")
        traceback.print_exc()
    finally:
        st.session_state.processing = False

# Интерфейс Streamlit
with st.sidebar:
    st.title("Troubleshooter")
    st.subheader("Решатель проблем")
    
    st.markdown("### Выберите дополнительные методы:")
    selected_methods = st.multiselect(
        "Дополнительные когнитивные методики:",
        ADDITIONAL_METHODS,
        key="selected_methods"
    )

# Основная область
st.title("Troubleshooter - Решатель проблем")
st.subheader("Решение проблем с применением когнитивных методов")

col1, col2 = st.columns([3, 1])
with col1:
    st.text_input(
        "Ваш запрос:",
        placeholder="Опишите вашу проблему...",
        key="input_query"
    )
with col2:
    st.slider(
        "Температура:",
        0.0, 1.0, 0.3, 0.1,
        key="temperature"
    )



# Основной загрузчик файлов
uploaded_file = st.file_uploader(
    "Загрузите файл с дополнительным контекстом (DOCX, XLSX, PPTX, PDF):",
    type=["docx", "xlsx", "pptx", "pdf"],
    key="uploaded_file"
)

if uploaded_file:
    markdown_content = convert_uploaded_file_to_markdown(uploaded_file)
    if markdown_content is not None:
        st.session_state.current_doc_text = markdown_content
        st.success(f"📂 Document converted: {len(st.session_state.current_doc_text)} characters")
    else:
        st.error("🚨 Unsupported file type or conversion error")
        st.session_state.current_doc_text = ""

if st.button("Сгенерировать решение", disabled=st.session_state.processing):
    generate_response()


# Новый загрузчик для временных рядов
st.markdown("---")
st.subheader("Анализ рядов данных (опциональное дополнение к рассуждениям)")
time_series_file = st.file_uploader(
    "Загрузите файл XLSX с рядами данных для анализа (не забудьте сформулировать основную проблему в строке запроса выше):",
    type=["xlsx"],
    key="time_series_file"
)

# Добавляем сюда блок визуализации
if time_series_file is not None:
    with st.expander("🔍 Предпросмотр данных (первые 10 строк)", expanded=True):
        try:
            df = pd.read_excel(time_series_file)
            st.dataframe(df.head(10))
            st.write("Доступные столбцы:", df.dtypes)
            
            # Преобразуем все возможные числовые столбцы
            for col in df.columns:
                try:
                    df[col] = pd.to_numeric(df[col], errors='ignore')
                except:
                    pass
            
            # Визуализация
            st.markdown("### 📊 Визуализация данных")
            
            # Выбор столбцов для оси X и Y
            col1, col2 = st.columns(2)
            with col1:
                x_col = st.selectbox(
                    "Столбец для оси X (дата/категория):",
                    df.columns,
                    index=min(0, len(df.columns)-1)
                )
            with col2:
                y_col = st.selectbox(
                    "Столбец для оси Y (числовые значения):",
                    [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])],
                    index=min(1, len(df.columns)-1)
                )
            
            # Выбор типа графика
            plot_type = st.radio(
                "Тип графика:",
                ["Линейный", "Столбчатый", "Точечный"],
                horizontal=True
            )
            
            # Построение графика
            fig, ax = plt.subplots(figsize=(10, 5))
            
            if plot_type == "Линейный":
                ax.plot(df[x_col], df[y_col], marker='o')
            elif plot_type == "Столбчатый":
                ax.bar(df[x_col], df[y_col])
            else:
                ax.scatter(df[x_col], df[y_col])
            
            ax.set_title(f"{plot_type} график: {y_col} по {x_col}")
            ax.set_xlabel(x_col)
            ax.set_ylabel(y_col)
            plt.xticks(rotation=45)
            st.pyplot(fig)
            
        except Exception as e:
            st.warning(f"Ошибка визуализации: {str(e)}")

if st.button("Анализировать числовые данные", key="analyze_ts_button"):
    if time_series_file is not None:
        # Сохраняем сырые данные для возможного отображения
        st.session_state.time_series_raw = time_series_file.getvalue()
        
        # Запускаем анализ
        with st.spinner("🔢 Анализирую ряды данных..."):
            analysis_result = analyze_time_series(st.session_state.time_series_raw)
            st.session_state.time_series_analysis = analysis_result
        
        st.success("✅ Анализ временных рядов завершен!")
        
        # Показываем результаты анализа
        st.subheader("Результат анализа рядов данных")
        st.write(analysis_result)
    else:
        st.warning("Пожалуйста, загрузите файл XLSX.")

# Показываем сырые данные по запросу
if st.session_state.get('time_series_raw') and st.checkbox("Показать исходные данные рядов данных"):
    st.subheader("Исходные данные временных рядов")
    
    try:
        # Используем новую функцию конвертации для отображения
        markdown_data = convert_excel_to_markdown_for_analysis(st.session_state.time_series_raw)
        st.markdown(markdown_data)
    except Exception as e:
        st.error(f"Ошибка при отображении данных: {str(e)}")

#if st.button("Сгенерировать решение", disabled=st.session_state.processing):
#    generate_response()

if st.session_state.report_content and not st.session_state.processing:
    st.divider()
    st.subheader("Экспорт результатов")
    
    b64_txt = base64.b64encode(st.session_state.report_content.encode()).decode()
    txt_href = f'<a href="data:file/txt;base64,{b64_txt}" download="report.txt">📥 Скачать TXT Markdown отчет</a>'
    st.markdown(txt_href, unsafe_allow_html=True)
    
    try:
        html_bytes = create_html_report(st.session_state.report_content, "Отчет Troubleshooter")
        b64_html = base64.b64encode(html_bytes).decode()
        html_href = f'<a href="data:text/html;base64,{b64_html}" download="report.html">📥 Скачать HTML отчет</a>'
        st.markdown(html_href, unsafe_allow_html=True)
        
        with st.expander("Предпросмотр отчета"):
            st.components.v1.html(html_bytes.decode('utf-8'), height=600, scrolling=True)
            
    except Exception as e:
        st.error(f"Ошибка при создании HTML отчета: {str(e)}")

if st.session_state.processing:
    st.info("⏳ Обработка запроса...")
