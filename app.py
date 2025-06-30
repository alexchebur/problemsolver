import streamlit as st
import google.generativeai as genai
import time
import traceback
from docx import Document
from io import BytesIO
from fpdf import FPDF
import base64
import os
from duckduckgo_search import DDGS
from datetime import datetime

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
    "Occam’s Razor",
    "System 1 vs System 2 Thinking",
    "Second-Order Thinking"
]

ADDITIONAL_METHODS = [
    "Inversion (thinking backwards)",
    "Opportunity Cost",
    "Margin of Diminishing Returns",
    "Hanlon’s Razor",
    "Confirmation Bias",
    "Availability Heuristic",
    "Parkinson’s Law",
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

def perform_search(query, region='ru-ru', max_results=8, max_snippet_length=3000):
    """Выполняет поиск и отображает результаты в сайдбаре"""
    try:
        with DDGS() as ddgs:
            results = []
            st.sidebar.subheader("Результаты поиска")
            
            for r in ddgs.text(
                query,
                region=region,
                max_results=max_results,
                backend="lite"
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

def create_pdf(content, title="Отчет"):
    try:
        pdf = FPDF()
        pdf.add_page()
        font_path = "fonts/DejaVuSansCondensed.ttf"
        
        if not os.path.exists(font_path):
            st.error(f"🚫 Файл шрифта не найден: {font_path}")
            return None
        
        pdf.add_font('DejaVu', '', font_path, uni=True)
        pdf.set_font('DejaVu', '', 12)
        effective_width = 190
        
        paragraphs = content.split('\n')
        
        for para in paragraphs:
            if not para.strip():
                pdf.ln(6)
                continue
                
            words = para.split()
            current_line = ""
            
            for word in words:
                test_line = current_line + " " + word if current_line else word
                if pdf.get_string_width(test_line) <= effective_width:
                    current_line = test_line
                else:
                    pdf.cell(0, 10, txt=current_line, ln=1)
                    current_line = word
            
            if current_line:
                pdf.cell(0, 10, txt=current_line, ln=1)
            
            pdf.ln(4)
        
        buffer = BytesIO()
        pdf.output(buffer)
        return buffer.getvalue()
    
    except Exception as e:
        st.error(f"🚨 Ошибка при создании PDF: {str(e)}")
        return None

def formulate_problem_and_queries():
    """Этап 1: Формулирование проблемы и генерация поисковых запросов"""
    query = st.session_state.input_query.strip()
    doc_text = st.session_state.current_doc_text[:300000]
    
    # Инструкция для LLM
    prompt = f"""
    Вы - эксперт по решению проблем. Проанализируйте запрос пользователя и документ (если есть):
    
    Запрос: {query}
    Документ: {doc_text if doc_text else "Нет документа"}
    
    Ваши задачи:
    1. Сформулируйте ключевую проблему
    2. Проведите рассуждения, внутренний диалог (вопросы, возражения, сомнения самому себе и ответы)
    3. Создайте список из 5 поисковых запросов для сбора информации
    4. Примените First Principles Thinking и System 2 Thinking
    
    Требования:
    - Вывод структурировать: 
        ПРОБЛЕМА: ... 
        ВНУТРЕННИЙ ДИАЛОГ: ...
        ЗАПРОСЫ:
        1. ...
        2. ...
        ...
    - Каждый запрос должен быть самодостаточным для поиска
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
        
        # Парсинг результатов
        problem = ""
        internal_dialog = ""
        queries = []
        
        # Пытаемся распарсить структурированный ответ
        if "ПРОБЛЕМА:" in result:
            problem_part = result.split("ПРОБЛЕМА:")[1]
            if "ВНУТРЕННИЙ ДИАЛОГ:" in problem_part:
                problem = problem_part.split("ВНУТРЕННИЙ ДИАЛОГ:")[0].strip()
                internal_dialog_part = problem_part.split("ВНУТРЕННИЙ ДИАЛОГ:")[1]
                if "ЗАПРОСЫ:" in internal_dialog_part:
                    internal_dialog = internal_dialog_part.split("ЗАПРОСЫ:")[0].strip()
                    queries_part = internal_dialog_part.split("ЗАПРОСЫ:")[1]
                    # Извлекаем запросы по нумерованному списку
                    for line in queries_part.split('\n'):
                        if line.strip() and line.strip()[0].isdigit():
                            # Убираем номер и точку
                            query_text = line.split('.', 1)[1].strip() if '. ' in line else line.strip()
                            queries.append(query_text)
            else:
                # Пытаемся извлечь только проблему и запросы
                if "ЗАПРОСЫ:" in problem_part:
                    problem = problem_part.split("ЗАПРОСЫ:")[0].strip()
                    queries_part = problem_part.split("ЗАПРОСЫ:")[1]
                    for line in queries_part.split('\n'):
                        if line.strip() and line.strip()[0].isdigit():
                            query_text = line.split('.', 1)[1].strip() if '. ' in line else line.strip()
                            queries.append(query_text)
        
        # Если не удалось распарсить, возвращаем как есть
        if not problem:
            problem = result
        if not queries:
            # Попробуем найти запросы в последних строках
            last_lines = result.split('\n')[-10:]
            for line in last_lines:
                if line.strip() and line.strip()[0].isdigit() and '.' in line:
                    query_text = line.split('.', 1)[1].strip()
                    queries.append(query_text)
            if len(queries) > 5:
                queries = queries[:5]
        
        st.session_state.problem_formulation = problem
        st.session_state.internal_dialog = internal_dialog
        st.session_state.generated_queries = queries[:5]  # ограничиваем 5 запросами
        
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

def generate_final_conclusions(context):
    """Генерирует итоговые выводы"""
    prompt = f"""
    На основе анализа сформулируйте итоговые выводы по проблеме:
    
    {st.session_state.problem_formulation}
    
    Контекст анализа:
    {context}
    
    Требования:
    - Сравните решения от разных методик
    - Выделите оптимальные решения
    - Предложите план реализации
    - Ответ должен быть не менее 5000 символов
    """
    
    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": st.session_state.temperature * 0.7,
                "max_output_tokens": 8000
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
        query = st.session_state.input_query.strip()
        if not query:
            status_area.warning("⚠️ Введите запрос")
            return

        # Этап 1: Формулирование проблемы и генерация запросов
        status_area.info("🔍 Формулирую проблему и генерирую поисковые запросы...")
        problem_result, queries = formulate_problem_and_queries()
        
        with st.expander("✅ Этап 1: Формулировка проблемы", expanded=True):
            st.subheader("Сформулированная проблема")
            st.write(st.session_state.problem_formulation)
            if hasattr(st.session_state, 'internal_dialog'):
                st.subheader("Внутренний диалог")
                st.write(st.session_state.internal_dialog)
            st.subheader("Сгенерированные поисковые запросы")
            st.write(queries)
            st.subheader("Полный вывод LLM")
            st.code(problem_result, language='text')
        
        # Сохраняем для отчета
        full_report = f"### Этап 1: Формулировка проблемы ###\n\n{problem_result}\n\n"
        full_report += f"Сформулированная проблема: {st.session_state.problem_formulation}\n\n"
        if hasattr(st.session_state, 'internal_dialog'):
            full_report += f"Внутренний диалог:\n{st.session_state.internal_dialog}\n\n"
        full_report += f"Поисковые запросы:\n" + "\n".join([f"{i+1}. {q}" for i, q in enumerate(queries)]) + "\n\n"
        
        # Этап 2: Поиск информации
        status_area.info("🔍 Выполняю поиск информации...")
        all_search_results = ""
        
        for i, search_query in enumerate(queries):
            search_result = perform_search(search_query)
            all_search_results += f"### Результаты по запросу '{search_query}':\n\n{search_result}\n\n"
        
        st.session_state.search_results = all_search_results
        
        with st.expander("🔍 Результаты поиска", expanded=False):
            st.text(all_search_results[:10000] + ("..." if len(all_search_results) > 10000 else ""))
        
        full_report += f"### Результаты поиска ###\n\n{all_search_results}\n\n"
        
        # Контекст для следующих этапов
        context = (
            f"Проблема: {st.session_state.problem_formulation}\n"
            f"Исходный запрос: {query}\n"
            f"Документ: {st.session_state.current_doc_text[:100000]}\n"
            f"Результаты поиска: {all_search_results[:20000]}"
        )
        
        # Этап 3: Применение когнитивных методик
        status_area.info("⚙️ Применяю когнитивные методики...")
        
        # Всегда применяем основные методики
        all_methods = CORE_METHODS.copy()
        
        # Добавляем выбранные дополнительные методики
        if st.session_state.selected_methods:
            all_methods += [m for m in st.session_state.selected_methods if m not in CORE_METHODS]
        
        method_results = {}
        
        for i, method in enumerate(all_methods):
            progress = int((i + 1) / (len(all_methods) + 1) * 100)
            progress_bar.progress(progress)
            
            status_area.info(f"⚙️ Применяю {method}...")
            result = apply_cognitive_method(method, context)
            
            method_results[method] = result
            
            with st.expander(f"✅ {method}", expanded=False):
                st.code(result, language='text')
            
            full_report += f"### Методика: {method} ###\n\n{result}\n\n"
            
            time.sleep(1)
        
        # Этап 4: Итоговые выводы
        status_area.info("📝 Формирую итоговые выводы...")
        progress_bar.progress(95)
        conclusions = generate_final_conclusions(full_report)
        
        with st.expander("📝 Итоговые выводы", expanded=True):
            st.write(conclusions)
        
        full_report += f"### Итоговые выводы ###\n\n{conclusions}\n\n"
        
        # Сохраняем полный отчет
        st.session_state.report_content = full_report
        progress_bar.progress(100)
        status_area.success("✅ Обработка завершена!")
        
        # Показываем полный отчет
        st.divider()
        st.subheader("Полный отчет")
        st.text(full_report[:20000] + ("..." if len(full_report) > 20000 else ""))

    except Exception as e:
        st.error(f"💥 Критическая ошибка: {str(e)}")
        traceback.print_exc()
    finally:
        st.session_state.processing = False

# Интерфейс Streamlit
# --- Боковая панель ---
with st.sidebar:
    st.title("Troubleshooter")
    st.subheader("Решатель проблем")
    
    st.markdown("### Выберите дополнительные методы:")
    selected_methods = st.multiselect(
        "Дополнительные когнитивные методики:",
        ADDITIONAL_METHODS,
        key="selected_methods"
    )

# --- Основная область ---
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
    "Загрузите DOCX файл с дополнительным контекстом (все что имеет значение, не более 300 тыс. символов):",
    type=["docx"],
    key="uploaded_file"
)

if uploaded_file:
    parse_docx(uploaded_file)

if st.button("Сгенерировать отчет", disabled=st.session_state.processing):
    generate_response()

# --- Экспорт результатов ---
if st.session_state.report_content and not st.session_state.processing:
    st.divider()
    st.subheader("Экспорт результатов")
    
    # Текстовый экспорт
    b64_txt = base64.b64encode(st.session_state.report_content.encode()).decode()
    txt_href = f'<a href="data:file/txt;base64,{b64_txt}" download="report.txt">📥 Скачать TXT отчет</a>'
    st.markdown(txt_href, unsafe_allow_html=True)
    
    # PDF экспорт
    try:
        pdf_bytes = create_pdf(st.session_state.report_content)
        if pdf_bytes:
            b64_pdf = base64.b64encode(pdf_bytes).decode()
            pdf_href = f'<a href="data:application/pdf;base64,{b64_pdf}" download="report.pdf">📥 Скачать PDF отчет</a>'
            st.markdown(pdf_href, unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"Не удалось создать PDF: {str(e)}")

if st.session_state.processing:
    st.info("⏳ Обработка запроса...")
