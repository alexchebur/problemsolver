import streamlit as st
import google.generativeai as genai
import base64
import time
import PyPDF2
import docx
import io
import json
from datetime import datetime

# Настройка API с ротацией моделей
API_KEYS = [
    st.secrets.get('GEMINI_API_KEY_1'),
    st.secrets.get('GEMINI_API_KEY_2'), 
    st.secrets.get('GEMINI_API_KEY_3')
]

# Доступные модели Gemini в порядке приоритета
GEMINI_MODELS = [
    'gemini-2.5-flash',
    'gemini-2.5-flash-lite',
    'gemini-2.0-flash',
    'gemini-2.0-flash-lite'
]

# Системный промпт по умолчанию
DEFAULT_SYSTEM_PROMPT = """Ты - опытный юрист-аналитик, специализирующийся на обработке судебных документов. 

Твоя роль:
- Анализировать юридические документы с максимальной точностью
- Выявлять правовые позиции, аргументы и доказательства
- Давать структурированные и обоснованные выводы
- Сохранять нейтральный профессиональный тон
- Работать строго в рамках предоставленных документов

Стиль работы:
- Ответы краткие и содержательные
- Используй четкую структуру: списки, нумерацию
- Выделяй ключевые моменты
- Избегай пространных вступлений и выводов
- Ссылайся на конкретные факты из документов

Формат ответов:
- Используй заголовки и подзаголовки
- Нумеруй пункты для удобства чтения
- Выделяй важные термины
- Сохраняй юридическую точность"""

def get_available_model(api_key_index=0):
    """Получает доступную модель с ротацией API ключей"""
    for model in GEMINI_MODELS:
        for i in range(len(API_KEYS)):
            current_key_index = (api_key_index + i) % len(API_KEYS)
            if API_KEYS[current_key_index]:
                try:
                    genai.configure(api_key=API_KEYS[current_key_index])
                    # Проверяем доступность модели
                    genai.GenerativeModel(model)
                    return model, current_key_index
                except Exception:
                    continue
    return None, None

# Инициализация состояния
if 'current_model_index' not in st.session_state:
    st.session_state.current_model_index = 0

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

if 'uploaded_files_content' not in st.session_state:
    st.session_state.uploaded_files_content = ""

if 'current_step' not in st.session_state:
    st.session_state.current_step = 1

if 'system_prompt' not in st.session_state:
    st.session_state.system_prompt = DEFAULT_SYSTEM_PROMPT

# Промпты для обработки судебных документов (редактируемые в сайдбаре)
DEFAULT_PROMPTS = {
    "1_analysis": """Проанализируй судебные документы. Выдели:
1. Ключевые факты
2. Правовые нормы  
3. Доказательства
Формат: списком, кратко.""",
    
    "2_relations": """Определи вид правоотношений из спора.
Укажи: вид + краткое обоснование.
На основе предыдущего анализа.""",
    
    "3_search_npa": """Сгенерируй 5 запросов для поиска НПА/НТД.
Только ключевые термины из дела.
Формат: нумерованный список.""",
    
    "6_evaluate_args": """Пронумеруй аргументы оппонента от сильного к слабому.
Для каждого оцени: соответствие фактам, обоснованность нормами.
Кратко, тезисами.""",
    
    "7_evaluate_evidence": """Оцени каждое доказательство оппонента:
- Относимость к делу
- Допустимость 
- Противоречия
Формат: название + оценка.""",
    
    "8_analyze_position": """Выяви в позиции оппонента:
- Пробелы в фактах/нормах
- Внутренние противоречия
- Логические ошибки
Списком.""",
    
    "9_reflective_dialogue": """Для 2 сильнейших аргументов оппонента:
Тезис → Контртезис → Опровержение → Сомнения.
Кратко, по пунктам.""",
    
    "10_search_practice": """Сгенерируй 10 обобщенных запросов для поиска практики.
Без конкретных фактов дела, только правовые проблемы.
Нумерованный список.""",
    
    "12_final_recommendations": """Дай рекомендации по защите:
- Аргументы для возражений (сильные→слабые)
- Дальнейшие действия
На основе всего анализа.""",
    
    "13_facts_objections": """Подготовь описание фактических обстоятельств для возражений.
Только факты, без аргументации.
Структурированно.""",
    
    "14_summary_position": """Суммаризируй правовую позицию. Пронумеруй аргументы оппонента.
Для каждого: почему не согласны (не доказан/не обоснован).""",
    
    "15_detailed_refutation": """Подготовь опровержение аргумента [N]:
- Контраргумент
- Нормы права
- Судебная практика
- Вывод
Кратко.""",
    
    "20_comparative_analysis": """Сравни позиции сторон по:
- Полноте обоснования
- Непротиворечивости
- Релевантности нормам
Рекомендации по усилению.""",
    
    "21_visualization": """Создай код Mermaid для визуализации позиций сторон.
Диаграмма: аргументы vs контраргументы.
Простая структура.""",
    
    "23_hearing_analysis": """Проанализируй выступления в заседании:
- Эффективность наших аргументов
- Новые обстоятельства
- Рекомендации по тактике
Кратко."""
}

def extract_text_from_pdf(file):
    """Извлекает текст из PDF файла"""
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        return f"Ошибка чтения PDF: {str(e)}"

def extract_text_from_docx(file):
    """Извлекает текст из DOCX файла"""
    try:
        doc = docx.Document(file)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    except Exception as e:
        return f"Ошибка чтения DOCX: {str(e)}"

def extract_text_from_txt(file):
    """Извлекает текст из TXT файла"""
    try:
        return file.read().decode('utf-8')
    except Exception as e:
        return f"Ошибка чтения TXT: {str(e)}"

def process_uploaded_files(uploaded_files):
    """Обрабатывает загруженные файлы и извлекает текст"""
    all_text = ""
    for file in uploaded_files:
        file_type = file.type
        if file_type == "application/pdf":
            text = extract_text_from_pdf(file)
        elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            text = extract_text_from_docx(file)
        elif file_type == "text/plain":
            text = extract_text_from_txt(file)
        else:
            text = f"Неподдерживаемый формат файла: {file_type}"
        
        all_text += f"\n\n--- ФАЙЛ: {file.name} ---\n{text}"
    
    return all_text

def call_gemini_api(prompt, context=""):
    """Вызывает API Gemini с ротацией моделей и ключей"""
    max_retries = 3
    for attempt in range(max_retries):
        model_name, key_index = get_available_model(st.session_state.current_model_index)
        if not model_name:
            return None, "Все модели и ключи недоступны"
        
        try:
            genai.configure(api_key=API_KEYS[key_index])
            model = genai.GenerativeModel(model_name)
            
            # Формируем полный промпт с системными настройками
            system_prompt = st.session_state.system_prompt
            full_prompt = f"{system_prompt}\n\nКОНТЕКСТ:\n{context}\n\nЗАДАЧА:\n{prompt}"
            
            response = model.generate_content(full_prompt)
            st.session_state.current_model_index = key_index
            
            # Добавляем в историю
            timestamp = datetime.now().strftime("%H:%M:%S")
            st.session_state.chat_history.append({
                "timestamp": timestamp,
                "model": model_name,
                "prompt": prompt,
                "response": response.text,
                "type": "processing",
                "system_prompt_used": system_prompt[:100] + "..." if len(system_prompt) > 100 else system_prompt
            })
            
            return response.text, None
            
        except Exception as e:
            error_msg = str(e)
            if "quota" in error_msg.lower() or "limit" in error_msg.lower():
                # Ротируем ключ при исчерпании лимита
                st.session_state.current_model_index = (key_index + 1) % len(API_KEYS)
                continue
            else:
                return None, f"Ошибка API: {error_msg}"
    
    return None, "Превышено количество попыток"

def main():
    st.set_page_config(
        page_title="Юридический Ассистент - Обработка Документов",
        page_icon="⚖️",
        layout="wide"
    )
    
    st.title("⚖️ Юридический Ассистент - Обработка Судебных Документов")
    
    # Сайдбар с настройками и промптами
    with st.sidebar:
        st.header("⚙️ Настройки обработки")
        
        # Выбор модели
        st.subheader("Модель по умолчанию")
        st.info("Gemini 2.0 Flash Lite → другие Gemini при лимитах")
        
        # Системный промпт
        st.header("🎯 Системный промпт")
        st.info("Определяет поведение и стиль ответов LLM")
        
        system_prompt = st.text_area(
            "Системные инструкции для LLM:",
            value=st.session_state.system_prompt,
            height=300,
            key="system_prompt_input",
            help="Эти инструкции будут добавляться к каждому запросу к LLM"
        )
        
        # Сохраняем системный промпт
        if system_prompt != st.session_state.system_prompt:
            st.session_state.system_prompt = system_prompt
            st.success("✅ Системный промпт обновлен")
        
        # Кнопки управления системным промптом
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Сбросить", key="reset_system_prompt"):
                st.session_state.system_prompt = DEFAULT_SYSTEM_PROMPT
                st.rerun()
        with col2:
            if st.button("💾 Сохранить", key="save_system_prompt"):
                st.success("Системный промпт сохранен")
        
        # Редактируемые промпты для этапов обработки
        st.header("📝 Промпты обработки")
        st.info("Редактируйте промпты для каждого этапа обработки")
        
        edited_prompts = {}
        for key, default_prompt in DEFAULT_PROMPTS.items():
            step_name = key.split("_")[1]
            edited_prompts[key] = st.text_area(
                f"Промпт {step_name}:",
                value=default_prompt,
                height=150,
                key=f"prompt_{key}"
            )
        
        # Кнопка сброса промптов
        if st.button("🔄 Сбросить все промпты", key="reset_all_prompts"):
            for key in DEFAULT_PROMPTS.keys():
                if f"prompt_{key}" in st.session_state:
                    del st.session_state[f"prompt_{key}"]
            st.session_state.system_prompt = DEFAULT_SYSTEM_PROMPT
            st.rerun()
    
    # Основная область - загрузка файлов
    st.header("1. Загрузка документов")
    
    uploaded_files = st.file_uploader(
        "Загрузите судебные документы (PDF, DOCX, TXT)",
        type=['pdf', 'docx', 'txt'],
        accept_multiple_files=True,
        key="file_uploader"
    )
    
    if uploaded_files:
        with st.spinner("Обрабатываю загруженные файлы..."):
            files_content = process_uploaded_files(uploaded_files)
            st.session_state.uploaded_files_content = files_content
            
        st.success(f"✅ Обработано {len(uploaded_files)} файлов")
        
        # Превью содержимого
        with st.expander("📄 Просмотр содержимого файлов"):
            st.text_area("Текст документов:", files_content, height=300)
    
    # Область чата
    st.header("2. Чат с ассистентом")
    
    # Отображение истории чата
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.chat_history:
            if message["type"] == "chat":
                col1, col2 = st.columns([1, 4])
                with col1:
                    st.text(f"👤 {message['timestamp']}")
                with col2:
                    st.text_area("", message["prompt"], height=100, key=f"q_{message['timestamp']}", label_visibility="collapsed")
                
                col1, col2 = st.columns([1, 4])
                with col1:
                    st.text(f"🤖 {message['timestamp']}")
                with col2:
                    st.text_area("", message["response"], height=150, key=f"a_{message['timestamp']}", label_visibility="collapsed")
            else:
                with st.expander(f"⚖️ Обработка ({message['timestamp']}) - {message['model']}"):
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        st.text("Системный промпт:")
                        st.info(message.get("system_prompt_used", "Не указан"))
                    with col2:
                        st.text("Модель:")
                        st.info(message['model'])
                    
                    st.text_area("Промпт:", message["prompt"], height=100)
                    st.text_area("Результат:", message["response"], height=200)
    
    # Ввод сообщения
    col1, col2 = st.columns([4, 1])
    with col1:
        user_input = st.text_area("Ваш вопрос:", height=100, key="user_input")
    with col2:
        send_chat = st.button("📤 Отправить", use_container_width=True, key="send_chat")
    
    if send_chat and user_input:
        with st.spinner("Ассистент думает..."):
            # Формируем контекст из файлов и истории
            context = f"ЗАГРУЖЕННЫЕ ДОКУМЕНТЫ:\n{st.session_state.uploaded_files_content}\n\nИСТОРИЯ ДИАЛОГА:\n"
            for msg in st.session_state.chat_history[-5:]:  # Последние 5 сообщений
                context += f"\n{msg['prompt']}\n{msg['response']}\n"
            
            response, error = call_gemini_api(user_input, context)
            
            if error:
                st.error(f"Ошибка: {error}")
            else:
                timestamp = datetime.now().strftime("%H:%M:%S")
                st.session_state.chat_history.append({
                    "timestamp": timestamp,
                    "model": "chat",
                    "prompt": user_input,
                    "response": response,
                    "type": "chat"
                })
                st.rerun()
    
    # Область обработки документов
    st.header("3. Обработка документов")
    st.info("Запускайте этапы обработки последовательно")
    
    # Контекст для обработки
    processing_context = f"ДОКУМЕНТЫ ДЛЯ АНАЛИЗА:\n{st.session_state.uploaded_files_content}"
    
    # Кнопки обработки с уникальными ключами
    processing_steps = [
        ("1_analysis", "📋 Анализ документов"),
        ("2_relations", "⚖️ Определение правоотношений"), 
        ("3_search_npa", "🔍 Поиск НПА/НТД"),
        ("6_evaluate_args", "📊 Оценка аргументов"),
        ("7_evaluate_evidence", "🔎 Оценка доказательств"),
        ("8_analyze_position", "🎯 Анализ позиции оппонента"),
        ("9_reflective_dialogue", "💭 Рефлексивный диалог"),
        ("10_search_practice", "⚔️ Поиск судебной практики"),
        ("12_final_recommendations", "🛡️ Рекомендации по защите"),
        ("13_facts_objections", "📝 Факты для возражений"),
        ("14_summary_position", "📄 Сводная позиция"),
        ("15_detailed_refutation", "🎯 Детальное опровержение"),
        ("20_comparative_analysis", "⚖️ Сравнительный анализ"),
        ("21_visualization", "📊 Визуализация"),
        ("23_hearing_analysis", "🏛️ Анализ заседания")
    ]
    
    # Создаем кнопки обработки
    for step_key, step_name in processing_steps:
        if st.button(step_name, key=f"btn_{step_key}", use_container_width=True):
            if not st.session_state.uploaded_files_content:
                st.warning("⚠️ Сначала загрузите документы")
                continue
                
            with st.spinner(f"Выполняю {step_name.lower()}..."):
                current_prompt = edited_prompts.get(step_key, DEFAULT_PROMPTS[step_key])
                response, error = call_gemini_api(current_prompt, processing_context)
                
                if error:
                    st.error(f"Ошибка при выполнении {step_name}: {error}")
                else:
                    st.success(f"✅ {step_name} завершен")
                    
                    # Показываем результат
                    with st.expander(f"Результат: {step_name}"):
                        st.text_area("", response, height=300, key=f"result_{step_key}")
    
    # Кнопки управления
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💾 Скачать историю диалога", use_container_width=True):
            if st.session_state.chat_history:
                history_text = "ИСТОРИЯ ДИАЛОГА С ЮРИДИЧЕСКИМ АССИСТЕНТОМ\n"
                history_text += "=" * 50 + "\n\n"
                history_text += f"СИСТЕМНЫЙ ПРОМПТ:\n{st.session_state.system_prompt}\n\n"
                history_text += "=" * 50 + "\n\n"
                
                for msg in st.session_state.chat_history:
                    history_text += f"[{msg['timestamp']}] {msg['type'].upper()} - {msg['model']}\n"
                    if msg.get('system_prompt_used'):
                        history_text += f"СИСТЕМНЫЕ НАСТРОЙКИ: {msg['system_prompt_used']}\n"
                    history_text += f"ВОПРОС/ЗАДАЧА:\n{msg['prompt']}\n\n"
                    history_text += f"ОТВЕТ/РЕЗУЛЬТАТ:\n{msg['response']}\n"
                    history_text += "=" * 50 + "\n\n"
                
                # Создаем файл для скачивания
                b64 = base64.b64encode(history_text.encode()).decode()
                href = f'<a href="data:file/txt;base64,{b64}" download="юридический_ассистент_история.txt">📥 Скачать историю диалога</a>'
                st.markdown(href, unsafe_allow_html=True)
            else:
                st.warning("История диалога пуста")
    
    with col2:
        if st.button("🔄 Очистить историю", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()
    
    with col3:
        if st.button("🗂️ Новые документы", use_container_width=True):
            st.session_state.uploaded_files_content = ""
            st.session_state.chat_history = []
            st.rerun()
    
    # Информационная панель
    st.sidebar.header("ℹ️ Информация")
    st.sidebar.info("""
    **Как использовать:**
    1. Настройте системный промпт (определяет поведение LLM)
    2. Загрузите судебные документы
    3. Используйте чат для вопросов
    4. Запускайте этапы обработки последовательно
    5. Скачайте историю работы
    
    **Особенности:**
    - Системный промпт влияет на все запросы к LLM
    - Автоматическая ротация моделей при лимитах
    - Сохранение контекста файлов и истории
    - Редактируемые промпты для каждого этапа
    """)
    
    # Статус текущей модели
    current_model, _ = get_available_model(st.session_state.current_model_index)
    if current_model:
        st.sidebar.success(f"Текущая модель: {current_model}")
    else:
        st.sidebar.error("Модели недоступны")
        
    # Показываем текущий системный промпт
    with st.sidebar.expander("📋 Текущий системный промпт"):
        st.text(st.session_state.system_prompt)

if __name__ == "__main__":
    main()
