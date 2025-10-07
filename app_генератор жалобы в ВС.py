import streamlit as st
import google.generativeai as genai
import base64
import time
from docx import Document
import io
import os

# Настройка API
api_key = st.secrets.get('GEMINI_API_KEY')
if not api_key:
    st.error("❌ API ключ не найден. Пожалуйста, настройте GEMINI_API_KEY в секретах Streamlit")
    st.stop()

genai.configure(api_key=api_key)

# Промпты для генерации жалобы
FACTUAL_CIRCUMSTANCES_PROMPT = """
Ты - опытный юрист, специализирующийся на административном праве. На основе предоставленных документов подготовь раздел надзорной жалобы "Фактические обстоятельства дела".

## ИСПОЛЬЗУЙ ТОЛЬКО ПРЕДОСТАВЛЕННЫЕ ДОКУМЕНТЫ:
{context}

## ТРЕБОВАНИЯ К РАЗДЕЛУ:
1. Кратко и объективно изложи фактические обстоятельства дела
2. Укажите даты, участников, существенные события
3. Опишите процессуальную историю дела (какие суды рассматривали, какие решения приняли)
4. Укажите на какие именно судебные акты подается жалоба
5. Избегай оценок и правовых выводов в этом разделе
6. Соблюдай официально-деловой стиль
7. Используй юридическую терминологию

Верни только текст раздела без дополнительных комментариев.
"""

LEGAL_ISSUES_PROMPT = """
Ты - опытный юрист, специализирующийся на административном праве. На основе предоставленных документов подготовь раздел надзорной жалобы "Правовая проблематика дела".

## ИСПОЛЬЗУЙ ТОЛЬКО ПРЕДОСТАВЛЕННЫЕ ДОКУМЕНТЫ:
{context}

## УЖЕ СГЕНЕРИРОВАННЫЕ РАЗДЕЛЫ:
{generated_parts}

## ТРЕБОВАНИЯ К РАЗДЕЛУ:
1. Проанализируй правовые основания обжалования
2. Выяви нарушения норм материального и процессуального права
3. Укажи на неправильное толкование и применение закона
4. Проанализируй состав административного правонарушения
5. Используй позиции ВС РФ и правовую доктрину
6. Ссылайся на экспертные заключения (если предоставлены)
7. Выяви противоречия в судебных актах

Верни только текст раздела без дополнительных комментариев.
"""

APPLICANT_POSITION_PROMPT = """
Ты - опытный юрист, специализирующийся на административном праве. На основе предоставленных документов подготовь раздел надзорной жалобы "Правовая позиция заявителя".

## ИСПОЛЬЗУЙ ТОЛЬКО ПРЕДОСТАВЛЕННЫЕ ДОКУМЕНТЫ:
{context}

## УЖЕ СГЕНЕРИРОВАННЫЕ РАЗДЕЛЫ:
{generated_parts}

## ТРЕБОВАНИЯ К РАЗДЕЛУ:
1. Изложи правовую позицию заявителя
2. Оцени неправомерность доводов судебных актов
3. Обоснуй почему судебные акты подлежат отмене
4. Используй процессуальные позиции заявителя (если предоставлены)
5. Ссылайся на судебную практику ВС РФ
6. Покажи существенность допущенных нарушений
7. Обоснуй почему нарушения повлияли на исход дела

Верни только текст раздела без дополнительных комментариев.
"""

PETITIONARY_PART_PROMPT = """
Ты - опытный юрист, специализирующийся на административном праве. На основе предоставленных документов подготовь просительную часть надзорной жалобы.

## ИСПОЛЬЗУЙ ТОЛЬКО ПРЕДОСТАВЛЕННЫЕ ДОКУМЕНТЫ:
{context}

## УЖЕ СГЕНЕРИРОВАННЫЕ РАЗДЕЛЫ:
{generated_parts}

## ТРЕБОВАНИЯ К ПРОСИТЕЛЬНОЙ ЧАСТИ:
1. Четко сформулируй требования к Верховному суду РФ
2. Укажи какие именно судебные акты подлежат отмене
3. Предложи варианты разрешения дела (прекращение производства, направление на новое рассмотрение и т.д.)
4. Соблюди формальные требования к надзорной жалобе
5. Укажи основания для отмены в соответствии с КАС РФ/АПК РФ

Верни только текст просительной части без дополнительных комментариев.
"""

CHAT_PROMPT = """
Ты - опытный юрист-консультант по административному праву. Отвечай на вопросы пользователя на основе предоставленных документов по делу об административном правонарушении.

## ДОКУМЕНТЫ ПО ДЕЛУ:
{context}

## СГЕНЕРИРОВАННАЯ ЖАЛОБА:
{complaint_text}

## ИСТОРИЯ ЧАТА:
{chat_history}

## ТЕКУЩИЙ ВОПРОС ПОЛЬЗОВАТЕЛЯ:
{user_question}

## ТРЕБОВАНИЯ К ОТВЕТУ:
1. Отвечай строго на основе предоставленных документов
2. Используй юридическую терминологию
3. Будь точным и конкретным
4. При необходимости ссылайся на конкретные документы или части жалобы
5. Объясняй сложные правовые концепции доступным языком
6. Помогай с доработкой жалобы, если пользователь об этом просит

Отвечай как профессиональный юрист-консультант.
"""

def read_docx(file):
    """Читает текст из файла DOCX"""
    try:
        doc = Document(file)
        text = []
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text.append(paragraph.text)
        return '\n'.join(text)
    except Exception as e:
        st.error(f"Ошибка при чтении файла {file.name}: {str(e)}")
        return ""

def extract_text_from_uploaded_files(uploaded_files):
    """Извлекает текст из загруженных файлов"""
    context_parts = []
    
    for uploaded_file in uploaded_files:
        if uploaded_file.name.endswith('.docx'):
            text = read_docx(uploaded_file)
            context_parts.append(f"--- ДОКУМЕНТ: {uploaded_file.name} ---\n{text}")
        else:
            st.warning(f"Формат файла {uploaded_file.name} не поддерживается. Поддерживаются только .docx файлы.")
    
    return "\n\n".join(context_parts)

def generate_complaint_part(prompt_template, context, generated_parts, temperature=0.3):
    """Генерирует часть жалобы с помощью Gemini API"""
    try:
        # Формируем полный промпт
        prompt = prompt_template.format(
            context=context,
            generated_parts=generated_parts
        )
        
        model = genai.GenerativeModel('gemini-2.0-flash-lite')
        
        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            top_p=0.8,
            top_k=40
        )
        
        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )
        
        return response.text
    except Exception as e:
        st.error(f"Ошибка при генерации части жалобы: {str(e)}")
        return None

def chat_with_context(user_question, context, complaint_text, chat_history):
    """Функция для чата с учетом контекста"""
    try:
        prompt = CHAT_PROMPT.format(
            context=context,
            complaint_text=complaint_text,
            chat_history=chat_history,
            user_question=user_question
        )
        
        model = genai.GenerativeModel('gemini-2.0-flash-lite')
        
        generation_config = genai.types.GenerationConfig(
            temperature=0.7,
            top_p=0.9,
            top_k=40
        )
        
        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )
        
        return response.text
    except Exception as e:
        st.error(f"Ошибка в чате: {str(e)}")
        return None

def main():
    st.set_page_config(
        page_title="Юрист AI: Надзорная жалоба в ВС РФ",
        page_icon="⚖️",
        layout="wide"
    )
    
    st.title("⚖️ Юрист AI: Подготовка надзорной жалобы в Верховный суд РФ")
    st.markdown("Подготовьте надзорную жалобу по делу об административном правонарушении с помощью AI")
    
    # Инициализация session_state
    if 'current_step' not in st.session_state:
        st.session_state.current_step = 1  # 1: загрузка, 2: генерация, 3: результат, 4: чат
    
    if 'context' not in st.session_state:
        st.session_state.context = ""
    
    if 'complaint_parts' not in st.session_state:
        st.session_state.complaint_parts = {}
    
    if 'full_complaint' not in st.session_state:
        st.session_state.full_complaint = ""
    
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = ""
    
    if 'uploaded_files' not in st.session_state:
        st.session_state.uploaded_files = []
    
    # Шаг 1: Загрузка документов
    if st.session_state.current_step == 1:
        st.header("1. Загрузка документов по делу")
        
        st.info("""
        **Загрузите следующие документы (в формате DOCX):**
        - Все судебные акты по делу
        - Процессуальные позиции заявителя  
        - Экспертные заключения правоведов
        - Дополнительный контекст
        - Шаблон надзорной жалобы (опционально)
        """)
        
        # Загрузка файлов
        uploaded_files = st.file_uploader(
            "Выберите DOCX файлы",
            type=['docx'],
            accept_multiple_files=True,
            help="Можно загрузить несколько файлов одновременно"
        )
        
        if uploaded_files:
            st.session_state.uploaded_files = uploaded_files
            
            # Показываем загруженные файлы
            st.subheader("Загруженные файлы:")
            for file in uploaded_files:
                st.write(f"📄 {file.name} ({file.size} байт)")
            
            # Извлекаем текст из файлов
            if st.button("📂 Обработать загруженные документы", type="primary"):
                with st.spinner("Читаю документы..."):
                    context = extract_text_from_uploaded_files(uploaded_files)
                    
                    if context:
                        st.session_state.context = context
                        st.success(f"✅ Обработано {len(uploaded_files)} файлов")
                        
                        # Показываем превью контекста
                        with st.expander("📋 Предварительный просмотр извлеченного текста"):
                            st.text_area("Текст документов:", context[:5000] + "..." if len(context) > 5000 else context, height=300)
                        
                        st.session_state.current_step = 2
                        st.rerun()
                    else:
                        st.error("Не удалось извлечь текст из документов")
        
        # Пропуск загрузки для тестирования
        if st.button("🚀 Пропустить загрузку (для тестирования)"):
            st.session_state.context = "Тестовый контекст для демонстрации работы приложения"
            st.session_state.current_step = 2
            st.rerun()
    
    # Шаг 2: Генерация жалобы
    elif st.session_state.current_step == 2:
        st.header("2. Генерация надзорной жалобы")
        
        if not st.session_state.context:
            st.error("Контекст не загружен. Вернитесь к шагу 1.")
            if st.button("⬅️ Вернуться к загрузке документов"):
                st.session_state.current_step = 1
                st.rerun()
            return
        
        st.info("Жалоба будет сгенерирована по частям с последовательным использованием контекста")
        
        # Определяем части жалобы и их порядок
        complaint_parts = [
            ("factual", "Фактические обстоятельства дела", FACTUAL_CIRCUMSTANCES_PROMPT),
            ("legal_issues", "Правовая проблематика", LEGAL_ISSUES_PROMPT),
            ("applicant_position", "Правовая позиция заявителя", APPLICANT_POSITION_PROMPT),
            ("petition", "Просительная часть", PETITIONARY_PART_PROMPT)
        ]
        
        # Прогресс генерации
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        generated_count = sum(1 for part_id, _, _ in complaint_parts if part_id in st.session_state.complaint_parts)
        total_parts = len(complaint_parts)
        
        # Если все части уже сгенерированы, переходим к результату
        if generated_count >= total_parts:
            st.session_state.current_step = 3
            st.rerun()
        
        # Генерация очередной части
        current_part_index = generated_count
        if current_part_index < total_parts:
            part_id, part_name, prompt_template = complaint_parts[current_part_index]
            
            status_text.text(f"Генерирую: {part_name}...")
            progress_bar.progress(current_part_index / total_parts)
            
            # Формируем уже сгенерированные части для контекста
            generated_parts_text = "\n\n".join([
                f"=== {name} ===\n{text}" 
                for (pid, name, _), text in zip(
                    complaint_parts[:current_part_index], 
                    [st.session_state.complaint_parts.get(pid, "") for pid, _, _ in complaint_parts[:current_part_index]]
                )
            ])
            
            # Генерируем текущую часть
            with st.spinner(f"Генерирую {part_name}..."):
                part_text = generate_complaint_part(
                    prompt_template,
                    st.session_state.context,
                    generated_parts_text
                )
                
                if part_text:
                    st.session_state.complaint_parts[part_id] = part_text
                    st.success(f"✅ {part_name} сгенерирован")
                    
                    # Показываем сгенерированную часть
                    with st.expander(f"📄 Просмотр: {part_name}"):
                        st.text_area("", part_text, height=300, key=f"view_{part_id}")
                    
                    # Автоматически переходим к следующей части
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"❌ Ошибка при генерации {part_name}")
        
        # Ручное управление генерацией
        st.divider()
        st.subheader("Ручное управление генерацией")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Перегенерировать все части"):
                st.session_state.complaint_parts = {}
                st.rerun()
        
        with col2:
            if st.button("⏩ Перейти к результату"):
                st.session_state.current_step = 3
                st.rerun()
        
        with col3:
            if st.button("💬 Перейти к чату"):
                st.session_state.current_step = 4
                st.rerun()
    
    # Шаг 3: Результат - полная жалоба
    elif st.session_state.current_step == 3:
        st.header("3. Готовая надзорная жалоба")
        
        # Собираем полную жалобу
        full_complaint_parts = []
        
        complaint_structure = [
            ("factual", "ФАКТИЧЕСКИЕ ОБСТОЯТЕЛЬСТВА ДЕЛА"),
            ("legal_issues", "ПРАВОВАЯ ПРОБЛЕМАТИКА ДЕЛА"),
            ("applicant_position", "ПРАВОВАЯ ПОЗИЦИЯ ЗАЯВИТЕЛЯ"),
            ("petition", "ПРОСИТЕЛЬНАЯ ЧАСТЬ")
        ]
        
        for part_id, part_title in complaint_structure:
            if part_id in st.session_state.complaint_parts:
                full_complaint_parts.append(f"{part_title}\n\n{st.session_state.complaint_parts[part_id]}")
        
        st.session_state.full_complaint = "\n\n" + "\n\n" + "="*50 + "\n\n".join(full_complaint_parts)
        
        # Отображаем полную жалобу
        st.text_area("Полный текст надзорной жалобы:", st.session_state.full_complaint, height=600)
        
        # Статистика
        word_count = len(st.session_state.full_complaint.split())
        st.sidebar.header("📊 Статистика")
        st.sidebar.write(f"Общий объем: {word_count} слов")
        st.sidebar.write(f"Загружено файлов: {len(st.session_state.uploaded_files)}")
        st.sidebar.write(f"Разделов жалобы: {len(st.session_state.complaint_parts)}")
        
        # Кнопки экспорта
        st.divider()
        st.header("💾 Экспорт жалобы")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Скачивание как TXT
            b64_txt = base64.b64encode(st.session_state.full_complaint.encode()).decode()
            href_txt = f'<a href="data:file/txt;base64,{b64_txt}" download="надзорная_жалоба_ВС_РФ.txt">📥 Скачать как TXT</a>'
            st.markdown(href_txt, unsafe_allow_html=True)
        
        with col2:
            # Копирование в буфер обмена
            if st.button("📋 Скопировать в буфер обмена"):
                st.code(st.session_state.full_complaint, language="markdown")
                st.success("Текст скопирован в буфер обмена!")
        
        # Навигация
        st.divider()
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("⬅️ Вернуться к генерации"):
                st.session_state.current_step = 2
                st.rerun()
        
        with col2:
            if st.button("🔄 Создать новую жалобу"):
                for key in list(st.session_state.keys()):
                    if key != 'current_step':
                        del st.session_state[key]
                st.session_state.current_step = 1
                st.rerun()
        
        with col3:
            if st.button("💬 Обсудить в чате →"):
                st.session_state.current_step = 4
                st.rerun()
    
    # Шаг 4: Чат с AI
    elif st.session_state.current_step == 4:
        st.header("4. Чат с AI-юристом")
        
        st.info("""
        **Обсуждайте сгенерированную жалобу и загруженные документы с AI-юристом.**
        Можете задавать вопросы по:
        - Правовым аспектам дела
        - Доработке жалобы
        - Судебной практике
        - Процессуальным вопросам
        """)
        
        # Отображаем историю чата
        chat_container = st.container()
        
        with chat_container:
            if st.session_state.chat_history:
                st.markdown("### История обсуждения")
                st.text_area("", st.session_state.chat_history, height=400, key="chat_history_display")
        
        # Ввод сообщения
        st.divider()
        user_question = st.text_area(
            "Ваш вопрос к AI-юристу:",
            placeholder="Например: Какие еще правовые позиции можно использовать в жалобе? Или: Проанализируй судебную практику по подобным делам...",
            height=100
        )
        
        col1, col2 = st.columns([1, 4])
        
        with col1:
            if st.button("📤 Отправить вопрос", type="primary"):
                if user_question.strip():
                    # Добавляем вопрос в историю
                    st.session_state.chat_history += f"\n\n👤 ПОЛЬЗОВАТЕЛЬ:\n{user_question}\n\n"
                    
                    # Генерируем ответ
                    with st.spinner("AI-юрист формулирует ответ..."):
                        response = chat_with_context(
                            user_question,
                            st.session_state.context,
                            st.session_state.full_complaint,
                            st.session_state.chat_history
                        )
                        
                        if response:
                            st.session_state.chat_history += f"⚖️ AI-ЮРИСТ:\n{response}\n"
                            st.rerun()
                        else:
                            st.error("Не удалось получить ответ от AI-юриста")
                else:
                    st.warning("Пожалуйста, введите вопрос")
        
        with col2:
            if st.button("🧹 Очистить историю чата"):
                st.session_state.chat_history = ""
                st.rerun()
        
        # Навигация
        st.divider()
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("⬅️ Вернуться к жалобе"):
                st.session_state.current_step = 3
                st.rerun()
        
        with col2:
            if st.button("🔄 Новый анализ"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.session_state.current_step = 1
                st.rerun()

    # Боковая панель с информацией
    st.sidebar.header("ℹ️ О приложении")
    st.sidebar.info("""
    **Юрист AI** помогает подготовить надзорную жалобу в Верховный суд РФ по делам об административных правонарушениях.
    
    **Возможности:**
    - Анализ судебных актов и процессуальных документов
    - Генерация структурированной жалобы
    - Учет правовых позиций и экспертных заключений
    - Чат с AI-юристом для консультаций
    
    **Поддерживаемые форматы:** DOCX
    """)
    
    st.sidebar.header("🎯 Советы")
    st.sidebar.info("""
    - Загружайте все имеющиеся документы по делу
    - Используйте чат для уточнения правовых вопросов
    - Проверяйте сгенерированную жалобу перед подачей
    - Сохраняйте промежуточные результаты
    """)

if __name__ == "__main__":
    main()
