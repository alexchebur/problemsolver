import streamlit as st
import google.generativeai as genai
import time
import traceback
from docx import Document
from io import BytesIO
from fpdf import FPDF
import base64
import os

# Настройка API
api_key = "AIzaSyCGC2JB3BgfBMycbt4us1eq6D5exNOvKT8"
#st.secrets.get('GEMINI_API_KEY') or st.text_input("Введите API-ключ:", type="password")
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
    "Анализ контекста и запроса пользователя (не менее 5000 знаков, НЕ УПОМИНАЙ количество знаков)",
    "Применение когнитивных подходов и методов решения проблем",
    "Формулирование итогового вывода и оптимальных решений"
]

def parse_docx(uploaded_file):
    try:
        if uploaded_file is None:
            return False

        doc = Document(BytesIO(uploaded_file.getvalue()))
        full_text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        st.session_state.current_doc_text = full_text[:400000]
        st.success(f"📂 Документ загружен: {len(st.session_state.current_doc_text)} символов")
        return True
    except Exception as e:
        st.error(f"🚨 Ошибка загрузки: {str(e)}")
        st.session_state.current_doc_text = ""
        return False

def process_step(step_num, step_name, context, temperature):
    try:
        step_text = st.empty()
        step_text.markdown(f"**🔹 Шаг {step_num+1}/{len(REASONING_STEPS)}: {step_name}**")
        
        response = model.generate_content(
            f"Выполните шаг {step_num+1}: {step_name}\nКонтекст: {context}",
            generation_config={
                "temperature": temperature,
                "max_output_tokens": 9000
            },
            request_options={'timeout': 60}
        )

        result = response.text
        step_text.markdown(f"**✅ Шаг {step_num+1} завершен**")
        st.markdown(f"---\n{result}\n---")
        return result

    except Exception as e:
        error_msg = f"🚨 Ошибка на шаге {step_num+1}: {str(e)}"
        st.error(error_msg)
        return error_msg

def create_pdf(content, title="Отчет о решении проблемы"):
    """Создает PDF файл из текстового содержимого"""
    pdf = FPDF()
    pdf.add_page()
    
    # Путь к шрифту в папке fonts репозитория
    font_path = "fonts/DejaVuSansCondensed.ttf"
    
    # Проверяем существование файла шрифта
    if not os.path.exists(font_path):
        st.error(f"🚨 Файл шрифта не найден: {font_path}")
        st.error("Убедитесь, что файл шрифта находится в папке fonts вашего репозитория")
        return None
    
    try:
        # Добавляем шрифт
        pdf.add_font('DejaVu', '', font_path, uni=True)
        pdf.set_font('DejaVu', '', 12)
    except Exception as e:
        st.error(f"🚨 Ошибка загрузки шрифта: {str(e)}")
        return None
    
    # Заголовок
    pdf.set_font_size(16)
    pdf.cell(0, 10, title, 0, 1, 'C')
    pdf.ln(10)
    
    # Основной текст
    pdf.set_font_size(12)
    for line in content.split('\n'):
        # Обработка заголовков Markdown
        if line.startswith('## '):
            pdf.set_font_size(14)
            pdf.cell(0, 10, line[3:], 0, 1)
            pdf.ln(5)
            pdf.set_font_size(12)
        elif line.startswith('# '):
            pdf.set_font_size(16)
            pdf.cell(0, 10, line[2:], 0, 1, 'C')
            pdf.ln(10)
            pdf.set_font_size(12)
        else:
            # Удаляем лишние пробелы в начале строк
            cleaned_line = line.lstrip()
            # Пропускаем пустые строки
            if cleaned_line:
                pdf.multi_cell(0, 8, cleaned_line)
            pdf.ln(5)
    
    return pdf.output(dest='S').encode('latin1')

def generate_response():
    st.session_state.processing = True
    st.session_state.report_content = None
    status_area = st.empty()
    progress_bar = st.progress(0)
    results_container = st.container()
    
    try:
        query = st.session_state.input_query.strip()
        if not query:
            status_area.warning("⚠️ Введите запрос")
            return

        if not st.session_state.current_doc_text:
            status_area.warning("⚠️ Загрузите документ")
            return

        context = (
            f"{st.session_state.sys_prompt}\n"
            f"Документ:\n{st.session_state.current_doc_text}\n"
            f"Запрос: {query}"
        )

        responses = []
        with results_container:
            for step_num, step_name in enumerate(REASONING_STEPS):
                progress = int((step_num+1)/len(REASONING_STEPS)*100)
                progress_bar.progress(progress)
                
                result = process_step(
                    step_num, 
                    step_name, 
                    context, 
                    st.session_state.temperature
                )
                responses.append(result)
                time.sleep(1)

        try:
            status_area.info("📝 Формирование итогового отчета...")
            report_content = "Обобщите в формате MARKDOWN:\n" + "\n".join(responses)
            final_response = model.generate_content(
                report_content,
                request_options={'timeout': 40}
            )
            
            st.divider()
            st.subheader("Итоговый отчет")
            st.markdown(final_response.text)
            
            # Сохраняем отчет для экспорта
            st.session_state.report_content = final_response.text
            
        except Exception as e:
            st.error(f"🚨 Ошибка формирования отчета: {str(e)}")

    except Exception as e:
        st.error(f"💥 Критическая ошибка: {str(e)}")
        traceback.print_exception(e)
    finally:
        st.session_state.processing = False
        progress_bar.empty()

# Интерфейс Streamlit
st.title("🧠Troubleshooter - Решатель проблем")
st.subheader("Решение проблем с применением когнитивных методов")

# Основные элементы интерфейса
# Боковая панель
with st.sidebar:
    st.title("🧠 Troubleshooter")
    st.subheader("Решатель проблем")
    
    st.markdown("### Системный промпт:")
    st.text_area(
        "Системный промпт:",
        value="Вы - troubleshooter, специалист по решению проблем в различных отраслях знаний и жизнедеятельности. "
        "Помогайте пользователю исследовать проблему и предлагать пути ее решения. Руководствуйтесь методами First Principles Thinking, "
        "Inversion (thinking backwards), Opportunity Cost, Second-Order Thinking, Margin of Diminishing Returns, Occam’s Razor, "
        "Hanlon’s Razor, Confirmation Bias, Availability Heuristic, Parkinson’s Law, Loss Aversion, Switching Costs, "
        "Circle of Competence, Regret Minimization, Leverage Points, Pareto Principle (80/20 Rule), Lindy Effect, Game Theory, "
        "System 1 vs System 2 Thinking, Antifragility, Теории решения изобретательских задач. Отвечайте по-русски",
        height=300,
        key="sys_prompt"
    )
#st.text_area(
#    "Системный промпт:",
#    value="Вы - troubleshooter, специалист по решению проблем в различных отраслях знаний и жизнедеятельности. "
#    "Помогайте пользователю исследовать проблему и предлагать пути ее решения. Руководствуйтесь методами First Principles Thinking, "
#    "Inversion (thinking backwards), Opportunity Cost, Second-Order Thinking, Margin of Diminishing Returns, Occam’s Razor, "
#    "Hanlon’s Razor, Confirmation Bias, Availability Heuristic, Parkinson’s Law, Loss Aversion, Switching Costs, "
#    "Circle of Competence, Regret Minimization, Leverage Points, Pareto Principle (80/20 Rule), Lindy Effect, Game Theory, "
#    "System 1 vs System 2 Thinking, Antifragility, Теории решения изобретательских задач. Отвечайте по-русски",
#    height=100,
#    key="sys_prompt"
#)

col1, col2 = st.columns([3, 1])
with col1:
    st.text_input(
        "Ваш запрос:",
        placeholder="Опишите вашу проблему...",
        key="input_query"
    )
with col2:
    st.slider(
        "Температура (чем выше, тем больше отсебятины):",
        0.0, 1.0, 0.3, 0.1,
        key="temperature"
    )

st.file_uploader(
    "Загрузите DOCX файл с дополнительным контекстом (желательно не более 200 тыс. символов):",
    type=["docx"],
    key="uploaded_file",
    on_change=lambda: parse_docx(st.session_state.uploaded_file)
)

if st.session_state.uploaded_file and not st.session_state.current_doc_text:
    parse_docx(st.session_state.uploaded_file)

if st.button("Отправить", disabled=st.session_state.processing):
    generate_response()

if st.session_state.processing:
    st.info("Обработка запроса...")

# Кнопка скачивания PDF
if st.session_state.report_content:
    st.divider()
    st.subheader("Экспорт результатов")
    
    # Создаем PDF
    pdf_bytes = create_pdf(st.session_state.report_content)
    
    if pdf_bytes:
        # Формируем кнопку скачивания
        b64 = base64.b64encode(pdf_bytes).decode()
        filename = f"gemini_report_{time.strftime('%Y%m%d_%H%M%S')}.pdf"
        href = f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}">Скачать PDF отчет</a>'
        st.markdown(href, unsafe_allow_html=True)
