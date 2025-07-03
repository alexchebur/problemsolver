import streamlit as st
import google.generativeai as genai
import time
import requests
import traceback
import random
from docx import Document
from io import BytesIO
from fpdf import FPDF
import base64
import os
from datetime import datetime
from bs4 import BeautifulSoup
from websearch import GoogleCSESearcher
from typing import List, Tuple
import re
from report import create_html_report
#from mermaid import add_mermaid_diagrams_to_pdf 

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
searcher = GoogleCSESearcher()

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

# Модель
model = genai.GenerativeModel('gemini-2.0-flash')

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

def get_current_date():
    return datetime.now().strftime("%Y-%m-%d")

def parse_docx(uploaded_file):
    try:
        if uploaded_file is None:
            return False

        doc = Document(BytesIO(uploaded_file.getvalue()))
        full_text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        st.session_state.current_doc_text = full_text[:300000]
        st.success(f"📂 Документ загружен: {len(st.session_state.current_doc_text)} символов")
        return True
    except Exception as e:
        st.error(f"🚨 Ошибка загрузки: {str(e)}")
        st.session_state.current_doc_text = ""
        return False

def formulate_problem_and_queries():
    """Этап 1: Формулирование проблемы и генерация поисковых запросов"""
    query = st.session_state.input_query.strip()
    doc_text = st.session_state.current_doc_text[:300000]
    
    prompt = f"""
    Вы - эксперт по решению проблем. Проанализируйте запрос пользователя и документ (если есть):

    Запрос: {query}
    Документ: {doc_text if doc_text else "Нет документа"}

    Ваши задачи:
    1. Сформулируйте ключевую проблему
    2. Проведите рассуждения (внутренний диалог из 10 шагов вопрос-ответы СТРОГО в формате каждого шага:
       [вопрос на уточнение проблемы]
       [ответ на вопрос]
       [сомнения в правильности ответа]
       [возражение на сомнения]
       ...
    3. Создайте список из 5 поисковых запросов
    4. Примените First Principles Thinking и System 2 Thinking

    Требования к формату:
    - Начните вывод строго с "ПРОБЛЕМА:"
    - Затем строго "РАССУЖДЕНИЯ:" с диалогом
    - Завершите строго "ЗАПРОСЫ:"
    - Каждый запрос должен начинаться с цифры и точки (1. ...)
    - Никаких дополнительных пояснений после заголовков
    - Пример:
    ПРОБЛЕМА: [формулировка проблемы]
    РАССУЖДЕНИЯ:
    [Вопрос 1]
    [Ответ 1]
    [Сомнение 1]
    [Возражение на сомнение 1]

    [Вопрос 2]
    [Ответ 2]
    ...
    ЗАПРОСЫ:
    1. [Запрос 1]
    2. [Запрос 2]
    ...
    """
    
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

def apply_cognitive_method(method_name, context):
    """Применяет когнитивную методику к проблеме"""
    prompt = f"""
    Примените методику {method_name} к проблеме:
    
    {st.session_state.problem_formulation}
    
    Контекст:
    {context}
    
    Требования:
    - Детально опишите процесс применения методики
    - Сформулируйте выводы и решения
    - Ответ должен быть не менее 9000 символов
    - Используйте строгий анализ, избегайте общих фраз
    - Для процессов и потоков пишите код визуализаций в формате Mermaid, СТРОГО код, начинающийся с пометки вида [```mermaid], СТРОГО вертикальной ориентации direction TD - top-down, без LR или RL
    """
    
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

def generate_refinement_queries(context: str) -> List[str]:
    """Генерирует уточняющие поисковые запросы на основе контекста"""
    prompt = f"""
    На основе проведенного анализа сформулируйте 5 уточняющих поисковых запросов, 
    которые помогут проверить гипотезы и углубить понимание решения:
    
    {context[:100000]}
    
    Требования:
    - Запросы должны быть конкретными и направленными на проверку гипотез и углубленное понимание проблемы
    - Выведите только нумерованный список
    - Формат:
        1. [Запрос 1]
        2. [Запрос 2]
        3. [Запрос 3]
        4. [Запрос 4]
        5. [Запрос 5]
    """
    
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

def generate_final_conclusions(problem_formulation: str, analysis_context: str) -> str:
    """Генерирует итоговые выводы на основе проблемы и контекста анализа"""
    prompt = f"""
    На основе анализа сформулируйте итоговые выводы по проблеме:
    
    {problem_formulation}
    
    Контекст анализа:
    {analysis_context[:100000]}  # Ограничиваем длину контекста
    
    Требования:
    - Выделите оптимальные решения и максимально детализированно их опишите (подробное описание решения, необходимые ресурсы, план, планируемый результат)
    - Ответ должен быть структурированным и содержательным
    - Не включайте технические детали поисковых запросов
    - Ваша задача - решить проблему пользователя, а не просто описать абстрактные пути
    - Выводы должны соответствовать предполагаемому результату выполнения запроса пользователя
    """
    
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
        # Проверка сетевой доступности
        try:
            test_response = requests.get("https://www.google.com", timeout=10)
            st.info(f"Сетевая доступность: {'OK' if test_response.status_code == 200 else 'Проблемы'}")
        except Exception as e:
            st.error(f"Сетевая ошибка: {str(e)}")

        query = st.session_state.input_query.strip()
        if not query:
            status_area.warning("⚠️ Введите запрос")
            return

        # Этап 1: Формулирование проблемы и генерация запросов
        status_area.info("🔍 Формулирую проблему и генерирую поисковые запросы...")
        problem_result, queries = formulate_problem_and_queries()
        # Проверка и резервный исходный запрос
        if not queries:
            queries = [query]  # query - исходный запрос пользователя
            st.warning("⚠️ Использован исходный запрос для поиска (LLM не сгенерировал запросы)")
        
        # Вывод рассуждений в боковую панель
        if hasattr(st.session_state, 'internal_dialog') and st.session_state.internal_dialog:
            st.sidebar.subheader("🧠 Рассуждения ИИ")
            st.sidebar.text_area(
                "",
                value=st.session_state.internal_dialog,
                height=300,
                label_visibility="collapsed"
            )
        else:
            st.sidebar.warning("Рассуждения не были сгенерированы")
        
        # Основной контейнер для этапа 1
        with st.expander("✅ Этап 1: Формулировка проблемы", expanded=False):
            st.subheader("Сформулированная проблема")
            st.write(st.session_state.problem_formulation)
            
            st.subheader("Сгенерированные поисковые запросы")
            st.write(queries)
            
            # Полный вывод LLM (без вложенного expander)
            st.subheader("Полный вывод LLM")
            st.code(problem_result, language='text')
        
        # Формирование отчета
        full_report = f"### Этап 1: Формулировка проблемы ###\n\n{problem_result}\n\n"
        full_report += f"Сформулированная проблема: {st.session_state.problem_formulation}\n\n"
        if hasattr(st.session_state, 'internal_dialog') and st.session_state.internal_dialog:
            full_report += f"Рассуждения:\n{st.session_state.internal_dialog}\n\n"
        full_report += f"Поисковые запросы:\n" + "\n".join([f"{i+1}. {q}" for i, q in enumerate(queries)]) + "\n\n"

        # Этап 2: Поиск информации
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
                
                # Показ результатов в боковой панели (без вложенных expanders)
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
        
        # Контекст для следующих этапов
        context = (
            f"Проблема: {st.session_state.problem_formulation}\n"
            f"Исходный запрос: {query}\n"
            f"Документ: {st.session_state.current_doc_text[:100000]}\n"
            f"Результаты поиска: {all_search_results[:20000]}"
        )
        
        # Этап 3: Применение когнитивных методик
        status_area.info("⚙️ Применяю когнитивные методики...")
        
        all_methods = CORE_METHODS.copy()
        if st.session_state.selected_methods:
            all_methods += [m for m in st.session_state.selected_methods if m not in CORE_METHODS]
        
        method_results = {}
        
        for i, method in enumerate(all_methods):
            progress = int((i + 1) / (len(all_methods) + 1) * 100)
            progress_bar.progress(progress)
            
            status_area.info(f"⚙️ Применяю {method}...")
            try:
                result = apply_cognitive_method(method, context)
                method_results[method] = result
                
                # Отображаем результат метода без вложенного expander
                st.subheader(f"✅ {method}")
                st.text_area("", value=result, height=300, label_visibility="collapsed")
                
                full_report += f"### Методика: {method} ###\n\n{result}\n\n"
            except Exception as e:
                st.error(f"Ошибка при применении {method}: {str(e)}")
                full_report += f"### Ошибка при применении {method}: {str(e)}\n\n"
            
            time.sleep(1)
        
        # Этап 4: Уточняющий поиск
        status_area.info("🔍 Выполняю уточняющий поиск...")
        refinement_search_results = ""
    
        refinement_context = (
            f"Проблема: {st.session_state.problem_formulation}\n"
            f"Анализ методик: {' '.join(method_results.values())[:10000]}\n"
        )
    
        refinement_queries = generate_refinement_queries(refinement_context)
    
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
    
        # Обновляем контекст для финальных выводов
        final_context = f"{context}\n\nРезультаты уточняющего поиска:\n{refinement_search_results}"
    
        # Этап 5: Итоговые выводы
        status_area.info("📝 Формирую итоговые выводы...")
        progress_bar.progress(95)
        try:
            # Формируем контекст только из анализа методик
            analysis_context = (
                f"Проблема: {st.session_state.problem_formulation}\n"
                f"Анализ методик:\n"
                + "\n\n".join([f"{method}:\n{result}" for method, result in method_results.items()])
            )
            
            conclusions = generate_final_conclusions(
                problem_formulation=st.session_state.problem_formulation,
                analysis_context=analysis_context
            )
            
            st.subheader("📝 Итоговые выводы")
            st.text_area("", value=conclusions, height=400, label_visibility="collapsed")
            
            full_report += f"### Итоговые выводы ###\n\n{conclusions}\n\n"
        except Exception as e:
            st.error(f"Ошибка при генерации выводов: {str(e)}")
            full_report += f"### Ошибка при генерации выводов: {str(e)}\n\n"
        
        # Сохраняем полный отчет (без результатов поиска)
        st.session_state.report_content = full_report
        progress_bar.progress(100)
        status_area.success("✅ Обработка завершена!")
        
        # Показываем полный отчет (без результатов поиска)
        #st.divider()
        #st.subheader("Полный отчет")
        #st.text(full_report[:30000] + ("..." if len(full_report) > 30000 else ""))

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

uploaded_file = st.file_uploader(
    "Загрузите DOCX файл с подобранным вручную дополнительным контекстом (все что имеет значение, не более 300 тыс. символов):",
    type=["docx"],
    key="uploaded_file"
)

if uploaded_file:
    parse_docx(uploaded_file)

if st.button("Сгенерировать решение", disabled=st.session_state.processing):
    generate_response()

if st.session_state.report_content and not st.session_state.processing:
    st.divider()
    st.subheader("Экспорт результатов")
    
    # Текстовый экспорт
    b64_txt = base64.b64encode(st.session_state.report_content.encode()).decode()
    txt_href = f'<a href="data:file/txt;base64,{b64_txt}" download="report.txt">📥 Скачать TXT отчет</a>'
    st.markdown(txt_href, unsafe_allow_html=True)
    
    # HTML экспорт
    try:
        html_bytes = create_html_report(st.session_state.report_content, "Отчет Troubleshooter")
        b64_html = base64.b64encode(html_bytes).decode()
        html_href = f'<a href="data:text/html;base64,{b64_html}" download="report.html">📥 Скачать HTML отчет</a>'
        st.markdown(html_href, unsafe_allow_html=True)
        
        # Превью отчета
        with st.expander("Предпросмотр отчета"):
            st.components.v1.html(html_bytes.decode('utf-8'), height=600, scrolling=True)
            
    except Exception as e:
        st.error(f"Ошибка при создании HTML отчета: {str(e)}")

if st.session_state.processing:
    st.info("⏳ Обработка запроса...")
