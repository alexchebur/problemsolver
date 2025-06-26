import streamlit as st
import google.generativeai as genai
import time
import traceback
import re
from docx import Document
from io import BytesIO
from fpdf import FPDF
import base64
import html

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
    "Первая часть отчета: постановка проблемы и расширение контекста. Проанализируй запрос пользователя {query} и на его основе сформулируй подразумеваемую пользователем проблему. Придумай пять сходных по смыслу концепций-тезисов из смежных запросу пользователя контекстов, используй метод Tree of Thoughts",
    "Вторая часть отчета: гипотезы о причинах и варианты решения разными методами. Сформулируй наиболее вероятные причины и предпосылки проблемы на основе {context}, сформулируй варианты решения проблемы с применением методов познания из {sys_prompt}",
    "Третья часть отчета: выбор оптимальных решений и выводы. Выбери оптимальные решения на основе {context}, подробно детализируй каждое из оптимальных решений."
]

# Функция для очистки текста от проблемных символов
def clean_text(text):
    if not text:
        return ""
    
    # Удаляем проблемные последовательности символов
    text = re.sub(r'(?<!\\)([\{\}])', r'\\\1', text)  # Экранируем фигурные скобки
    text = re.sub(r'([\[\]])', r'\\\1', text)  # Экранируем квадратные скобки
    text = re.sub(r'([\(\)])', r'\\\1', text)  # Экранируем круглые скобки
    text = re.sub(r'(\$)', r'\\\1', text)  # Экранируем знаки доллара
    text = re.sub(r'(\^)', r'\\\1', text)  # Экранируем каретки
    
    # Заменяем HTML-сущности
    text = html.unescape(text)
    
    # Удаляем непечатаемые символы
    text = re.sub(r'[\x00-\x1F\x7F-\x9F]', ' ', text)
    
    # Заменяем последовательности пробелов на один пробел
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def parse_docx(uploaded_file):
    try:
        if uploaded_file is None:
            return False

        doc = Document(BytesIO(uploaded_file.getvalue()))
        full_text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        st.session_state.current_doc_text = clean_text(full_text)[:400000]
        st.success(f"📂 Документ загружен: {len(st.session_state.current_doc_text)} символов")
        return True
    except Exception as e:
        st.error(f"🚨 Ошибка загрузки: {str(e)}")
        st.session_state.current_doc_text = ""
        return False

def create_pdf(content, title="Отчет"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Добавляем контент с переносами строк
    for line in content.split('\n'):
        pdf.multi_cell(0, 8, txt=line, align='L')
        pdf.ln(2)
    
    return pdf.output(dest='S').encode('latin-1')

def generate_response():
    st.session_state.processing = True
    st.session_state.report_content = None
    progress_bar = st.progress(0)
    results_container = st.container()

    try:
        query = clean_text(st.session_state.input_query.strip())
        if not query:
            st.warning("⚠️ Введите запрос")
            return

        if not st.session_state.current_doc_text:
            st.warning("⚠️ Загрузите документ")
            return

        # Начальный контекст
        context = (
            f"Системный промпт: {st.session_state.sys_prompt}\n"
            f"Документ: {st.session_state.current_doc_text[:1000]}...\n"
            f"Запрос: {query}"
        )

        responses = []
        full_report = ""
        
        with results_container:
            for step_num, step_template in enumerate(REASONING_STEPS):
                progress = int((step_num + 1) / len(REASONING_STEPS) * 100)
                progress_bar.progress(progress)
                
                # Формируем промпт для шага
                step_prompt = step_template.format(
                    query=query,
                    context=context,
                    sys_prompt=st.session_state.sys_prompt
                )
                
                st.markdown(f"**🔹 Шаг {step_num+1}/{len(REASONING_STEPS)}**")
                
                try:
                    response = model.generate_content(
                        step_prompt,
                        generation_config={
                            "temperature": st.session_state.temperature,
                            "max_output_tokens": 9000
                        },
                        request_options={'timeout': 120}
                    )
                    
                    result = clean_text(response.text)
                    responses.append(result)
                    
                    # Добавляем результат в контекст
                    context += f"\n\nРезультат шага {step_num+1}: {result[:500]}..."
                    
                    # Отображаем результат с безопасным Markdown
                    st.markdown(f"**✅ Шаг {step_num+1} завершен**")
                    st.markdown(f"```\n{result}\n```")
                    
                    full_report += f"### Шаг {step_num+1} ###\n\n{result}\n\n{'='*50}\n\n"
                    
                except Exception as e:
                    error_msg = f"🚨 Ошибка на шаге {step_num+1}: {str(e)}"
                    st.error(error_msg)
                    responses.append(error_msg)
                    full_report += f"### Ошибка на шаге {step_num+1} ###\n\n{error_msg}\n\n"

                time.sleep(1)

        st.session_state.report_content = clean_text(full_report)
        progress_bar.empty()
        st.success("✅ Обработка завершена!")
        
        # Показываем полный отчет
        st.divider()
        st.subheader("Полный отчет")
        st.markdown(f"```\n{st.session_state.report_content}\n```")

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
    sys_prompt_default = clean_text(
        "Вы - troubleshooter, специалист по решению проблем. "
        "Помогайте пользователю исследовать проблему и предлагать пути ее решения. "
        "Руководствуйтесь методами First Principles Thinking, Inversion, Pareto Principle. "
        "Ответы должны быть согласованы между собой. "
        "Числовые ряды представляйте в формате ASCII-диаграмм. Отвечайте по-русски."
    )
    st.session_state.sys_prompt = st.text_area(
        label="Системный промпт:",
        value=sys_prompt_default,
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
    "Загрузите DOCX файл с дополнительным контекстом:",
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
    
    # PDF экспорт
    try:
        pdf_bytes = create_pdf(st.session_state.report_content)
        if pdf_bytes:
            b64 = base64.b64encode(pdf_bytes).decode()
            filename = f"gemini_report_{time.strftime('%Y%m%d_%H%M%S')}.pdf"
            href = f'<a href="data:application/pdf;base64,{b64}" download="{filename}">📥 Скачать PDF отчет</a>'
            st.markdown(href, unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"Не удалось создать PDF: {str(e)}")

if st.session_state.processing:
    st.info("⏳ Обработка запроса...")
