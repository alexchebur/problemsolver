import streamlit as st
import google.generativeai as genai
import time
import traceback
from docx import Document
from io import BytesIO
from fpdf import FPDF
import base64
import os
from duckduckgo_search import DDGS  # Добавлен импорт для поиска

# Настройка API
#api_key = os.environ['GEMINI_API_KEY']
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

model = genai.GenerativeModel('gemini-2.0-flash')

# Глобальные переменные состояния
if 'current_doc_text' not in st.session_state:
    st.session_state.current_doc_text = ""
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'report_content' not in st.session_state:
    st.session_state.report_content = None

REASONING_STEPS = [
    "Первая часть отчета: постановка проблемы и расширение контекста. Проанализируй запрос пользователя {query} и на его основе сформулируй подразумеваемую пользователем проблему. Придумай пять сходных по смыслу концепций-тезисов из смежных запросу пользователя контекстов, используй метод Tree of Thoughts. Составь пошаговую цепочку рассуждений, направленную на решение проблемы. Опиши всю цепочку рассуждений, воспроизведя внутренний диалог размышляюшего человека c вопросами самому себе и ответами на них (НЕ УПОМИНАЙ про внутренний диалог, только воспроизводи его)",
    "Вторая часть отчета: гипотезы о причинах и варианты решения разными методами. Сформулируй наиболее вероятные причины и предпосылки проблемы на основе контекста и цепочки рассуждений из {context} (в том числе отвечая на заданные себе в режиме внутреннего диалога вопросы, не повторяя вопросов и НЕ упоминая внутренний диалог), сформулируй варианты решения проблемы с применением методов познания из {sys_prompt}",
    "Третья часть отчета: выбор оптимальных решений и выводы. Выбери оптимальные решения на основе {context}, подробно детализируй каждое из оптимальных решений."
]

#def duckduckgo_search(query, region='ru-ru', max_results=8, max_snippet_length=3000):
#    """Выполняет расширенный поиск в DuckDuckGo с увеличенными лимитами"""
#    try:
#        with DDGS() as ddgs:
#            results = []
#            for r in ddgs.text(
#                query,
#                region=region,
#                max_results=max_results,
#                backend="lite"  # Используем "lite" для получения полных описаний
#            ):
#                # Обрезаем слишком длинные фрагменты
#                if len(r['body']) > max_snippet_length:
#                    r['body'] = r['body'][:max_snippet_length] + "..."
#                results.append(r)

#            # Форматируем результаты
#            formatted = []
#            for i, r in enumerate(results, 1):
#                formatted.append(f"Результат {i}: {r['title']}\n{r['body']}\nURL: {r['href']}\n")

#            return "\n\n".join(formatted)
#    except Exception as e:
#        return f"Ошибка поиска: {str(e)}"

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
                # Обрезаем слишком длинные фрагменты
                snippet = r['body'][:500] + "..." if len(r['body']) > 500 else r['body']
                results.append(r)
                
                # Выводим в сайдбар
                with st.sidebar.expander(f"🔍 {r['title']}"):
                    st.write(snippet)
                    st.caption(f"URL: {r['href']}")

            # Форматируем результаты для контекста
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
        
        # Указываем путь к шрифту
        font_path = "fonts/DejaVuSansCondensed.ttf"
        
        # Проверяем существование файла шрифта
        if not os.path.exists(font_path):
            st.error(f"🚫 Файл шрифта не найден: {font_path}")
            return None
        
        # Добавляем шрифт
        pdf.add_font('DejaVu', '', font_path, uni=True)
        pdf.set_font('DejaVu', '', 12)
        
        # Устанавливаем эффективную ширину текста (190 мм - ширина A4 минус поля)
        effective_width = 190
        
        # Разбиваем контент на абзацы
        paragraphs = content.split('\n')
        
        for para in paragraphs:
            if not para.strip():
                pdf.ln(6)  # Добавляем отступ для пустых строк
                continue
                
            # Разбиваем абзац на слова
            words = para.split()
            current_line = ""
            
            for word in words:
                # Проверяем, помещается ли слово в текущую строку
                test_line = current_line + " " + word if current_line else word
                if pdf.get_string_width(test_line) <= effective_width:
                    current_line = test_line
                else:
                    # Выводим текущую строку
                    pdf.cell(0, 10, txt=current_line, ln=1)
                    current_line = word
            
            # Выводим оставшиеся слова в абзаце
            if current_line:
                pdf.cell(0, 10, txt=current_line, ln=1)
            
            # Добавляем отступ между абзацами
            pdf.ln(4)
        
        buffer = BytesIO()
        pdf.output(buffer)
        return buffer.getvalue()
    
    except Exception as e:
        st.error(f"🚨 Ошибка при создании PDF: {str(e)}")
        return None

def generate_response():
    st.session_state.processing = True
    st.session_state.report_content = None
    status_area = st.empty()
    progress_bar = st.progress(0)
    results_container = st.empty()

    try:
        query = st.session_state.input_query.strip()
        if not query:
            status_area.warning("⚠️ Введите запрос")
            return

        if not st.session_state.current_doc_text:
            status_area.warning("⚠️ Загрузите документ")
            return

        # Выполняем поиск в DuckDuckGo
        status_area.info("🔍 Выполняю поиск в интернете...")
        #search_results = duckduckgo_search(query)
        search_results = perform_search(query)
        status_area.success("✅ Поиск завершен!")

        # Формируем контекст с результатами поиска
        context = (
            f"Системный промпт: {st.session_state.sys_prompt}\n"
            f"Документ: {st.session_state.current_doc_text[:300000]}...\n"
            f"Запрос: {query}\n"
            f"Результаты веб-поиска:\n{search_results}"
        )

        responses = []
        full_report = ""
        
        with st.spinner("Обработка запроса..."):
            for step_num, step_template in enumerate(REASONING_STEPS):
                progress = int((step_num + 1) / len(REASONING_STEPS) * 100)
                progress_bar.progress(progress)
                
                # Формируем промпт для шага
                step_name = step_template.format(
                    query=query,
                    context=context,
                    sys_prompt=st.session_state.sys_prompt
                )
                
                st.markdown(f"**🔹 Шаг {step_num+1}/{len(REASONING_STEPS)}**")
                
                try:
                    response = model.generate_content(
                        step_name,
                        generation_config={
                            "temperature": st.session_state.temperature,
                            "max_output_tokens": 10000
                        },
                        request_options={'timeout': 120}
                    )
                    
                    result = response.text
                    responses.append(result)
                    
                    # Добавляем результат в контекст
                    context += f"\n\nРезультат шага {step_num+1}: {result[:9000]}..."
                    
                    # Отображаем результат
                    with st.expander(f"✅ Шаг {step_num+1} завершен", expanded=True):
                        st.code(result, language='text')
                    
                    full_report += f"### Шаг {step_num+1} ###\n\n{result}\n\n{'='*50}\n\n"
                    
                except Exception as e:
                    error_msg = f"🚨 Ошибка на шаге {step_num+1}: {str(e)}"
                    st.error(error_msg)
                    responses.append(error_msg)
                    full_report += f"### Ошибка на шаге {step_num+1} ###\n\n{error_msg}\n\n"

                time.sleep(1)

        st.session_state.report_content = full_report
        progress_bar.empty()
        st.success("✅ Обработка завершена!")
        
        # Показываем полный отчет
        st.divider()
        st.subheader("Полный отчет")
        st.code(full_report, language='text')

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

    st.markdown("### Системный промпт:")
    st.session_state.sys_prompt = st.text_area(
        "",
        value="Вы - troubleshooter, специалист по решению проблем. "
              "Помогайте пользователю исследовать проблему и предлагать пути ее решения. "
              "Руководствуйтесь методами First Principles Thinking, Inversion (thinking backwards), Opportunity Cost, Second-Order Thinking, Margin of Diminishing Returns, Occam’s Razor, Hanlon’s Razor, Confirmation Bias, Availability Heuristic, Parkinson’s Law, Loss Aversion, Switching Costs, Circle of Competence, Regret Minimization, Leverage Points, Pareto Principle (80/20 Rule), Lindy Effect, Game Theory, System 1 vs System 2 Thinking, Antifragility, Теории Решения Изобретательских задач. "
              "Ответы должны быть согласованы между собой, составлять не менее 9000 символов (БЕЗ указания количества символов в ответе). "
              "Если в контексте присутствуют последовательности конкретных числовых показателей, то представляйте их в формате ASCII-диаграмм (если последовательностей чисел нет в контексте, диаграммы НЕ НУЖНЫ). Отвечайте по-русски.",
        height=250,
        label_visibility="collapsed"
    )

# --- Основная область ---
st.title("Troubleshooter - Решатель проблем")
st.subheader("Решение проблем с применением когнитивных методов на основе контекста в документе Word")

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
    txt_href = f'<a href="data:file/txt;base64,{b64_txt}" download="report.txt">📥 Скачать TXT отчет (MarkDown)</a>'
    st.markdown(txt_href, unsafe_allow_html=True)
    
    # PDF экспорт (упрощенный)
    try:
        pdf_bytes = create_pdf(st.session_state.report_content)
        b64_pdf = base64.b64encode(pdf_bytes).decode()
        pdf_href = f'<a href="data:application/pdf;base64,{b64_pdf}" download="report.pdf">📥 Скачать PDF отчет</a>'
        st.markdown(pdf_href, unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"Не удалось создать PDF: {str(e)}")

if st.session_state.processing:
    st.info("⏳ Обработка запроса...")
