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
    "Первая часть отчета: постановка проблемы и расширение контекста. Проанализируй запрос пользователя {query} и на его основе сформулируей подразумеваемую пользователем проблему. Придумай пять сходных по смыслу концепций-тезисов из смежных запросу пользователя контекстов",
    "Вторая часть отчета: гипотезы о причинах и варианты решения разными методами. Сформулируй наиболее вероятные причины и предпосылки проблемы, сформулируй варианты решения проблемы с применением методов познания из {st.session_state.sys_prompt}",
    "Третья часть отчета: выбор оптимальных решений и выводы. Выбери оптимальные решения на основе {context}, подробно детализируй каждое из оптимальных решений."
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

        prompt = (
            f"{step_name}\n"
            f"Контекст: {context}\n\n"
            "Ваш ответ должен быть полным, не менее 5000 символов, но не должен содержать упоминаний о количестве символов и о шагах "
            "(например, не пишите 'На шаге 1...', 'В рамках первого этапа...')"
        )

        response = model.generate_content(
            prompt,
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

    # --- Совместимость с fpdf2 >= 2.0 ---
    return pdf.output(dest='S')  # Возвращает bytes

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

        # Начальный контекст — только системный промпт + документ + запрос
        context = (
            f"{st.session_state.sys_prompt}\n"
            f"Документ:\n{st.session_state.current_doc_text}\n"
            f"Запрос: {query}"
        )

        responses = []
        with results_container:
            for step_num, step_name in enumerate(REASONING_STEPS):
                progress = int((step_num + 1) / len(REASONING_STEPS) * 100)
                progress_bar.progress(progress)

                # Формируем prompt для текущего шага
                prompt = (
                    f"{step_name}\n"
                    f"Контекст: {context}\n\n"
                    "Ваш ответ должен быть полным, но не должен содержать упоминаний о шагах "
                    "(например, не пишите 'На шаге 1...', 'В рамках первого этапа...')"
                )

                step_text = st.empty()
                step_text.markdown(f"**🔹 Шаг {step_num+1}/{len(REASONING_STEPS)}: {step_name}**")

                try:
                    response = model.generate_content(
                        prompt,
                        generation_config={
                            "temperature": st.session_state.temperature,
                            "max_output_tokens": 9000
                        },
                        request_options={'timeout': 60}
                    )
                    result = response.text
                    step_text.markdown(f"**✅ Шаг {step_num+1} завершен**")
                    st.markdown(f"---\n{result}\n---")
                    responses.append(result)

                    # Добавляем результат текущего шага в контекст для следующих шагов
                    context += f"\n\nРезультат шага {step_num+1} ({step_name}): {result}"

                except Exception as e:
                    error_msg = f"🚨 Ошибка на шаге {step_num+1}: {str(e)}"
                    st.error(error_msg)
                    responses.append(error_msg)

                time.sleep(1)

        # Сохраняем объединенные результаты
        raw_report = ""
        for i, response in enumerate(responses):
            raw_report += f"### Шаг {i + 1}: {REASONING_STEPS[i]}\n\n{response}\n\n"

        st.session_state.report_content = raw_report

        # Выводим в интерфейс
        st.divider()
        st.subheader("Результаты по каждому шагу")
        st.markdown(raw_report)

    except Exception as e:
        st.error(f"💥 Критическая ошибка: {str(e)}")
        traceback.print_exception(e)
    finally:
        st.session_state.processing = False
        progress_bar.empty()

# Интерфейс Streamlit
# --- Боковая панель ---
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
              "System 1 vs System 2 Thinking, Antifragility, Теории решения изобретательских задач. Вы будете выполнять несколько шагов анализа. Ответы должны быть согласованы между собой. Следующие шаги будут опираться на выводы предыдущих. Числовые ряды и последовательности данных представляйте в формате ASCII-диаграмм. Отвечайте по-русски",
        height=300,
        key="sys_prompt"
    )

# --- Основная область ---
st.title("🧠 Troubleshooter - Решатель проблем")
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

# --- Экспорт PDF ---
if st.session_state.report_content:
    st.divider()
    st.subheader("Экспорт результатов")

    # Создаем PDF
    pdf_bytes = create_pdf(st.session_state.report_content)

    if pdf_bytes:
        # Формируем кнопку скачивания
        b64 = base64.b64encode(pdf_bytes).decode()
        filename = f"gemini_report_{time.strftime('%Y%m%d_%H%M%S')}.pdf"
        href = f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}">📥 Скачать PDF отчет</a>'
        st.markdown(href, unsafe_allow_html=True)
