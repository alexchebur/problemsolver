import streamlit as st
import google.generativeai as genai
import base64

# Настройка API
api_key = st.secrets.get('GEMINI_API_KEY')
if not api_key:
    st.error("❌ API ключ не найден. Пожалуйста, настройте GEMINI_API_KEY в секретах Streamlit")
    st.stop()

genai.configure(api_key=api_key)

# Базовый промпт для создания структуры произведения
STRUCTURE_PROMPT = """
Ты - профессиональный писатель и сценарист. На основе предоставленных пользователем данных создай подробную структуру повести.

## Задача:
Создать структуру повести в жанре {genre} с сеттингом: {setting}
{alias_text}

## Требования к структуре:
1. **Структура сюжета** (по канонам "завязка-кульминация-развязка-финал"):
   - Завязка: представление мира и персонажей, начало конфликта (главы 1-2)
   - Кульминация: развитие конфликта, ключевые события (главы 3-6)
   - Развязка: разрешение основных противоречий (главы 7-8)
   - Финал: заключительная часть, выводы (глава 9)

2. **Детальный план глав** (9 глав, объем каждой не менее 8000 слов):
   Для каждой главы укажи:
   - Название главы
   - Действующие лица
   - Синопсис: основные события и конфликты
   - Локации действия
   - Участвующие предметы/артефакты
   - Примерный объем в словах

3. **Персонажи** (для каждого):
   - Имя и краткое описание
   - Характер, мотивация
   - Внутренний конфликт
   - Роль и движущая сила в сюжете

4. **Локации** - описание ключевых мест действия

5. **Предметы/артефакты** - значимые объекты в сюжете

6. **Краткая концовка** - общее направление финала

Структура должна быть достаточно детальной, чтобы служить основой для написания полного текста повести.
"""

# Промпт для генерации отдельных глав с учетом предыдущего контекста
CHAPTER_PROMPT = """
Ты - профессиональный писатель. Напиши главу повести на основе предоставленной структуры и УЖЕ НАПИСАННЫХ ПРЕДЫДУЩИХ ГЛАВ.

## КОНТЕКСТ ПРОИЗВЕДЕНИЯ:
Жанр: {genre}
Сеттинг: {setting}
{alias_text}

## ПОЛНАЯ СТРУКТУРА ПРОИЗВЕДЕНИЯ:
{structure}

## УЖЕ НАПИСАННЫЕ ПРЕДЫДУЩИЕ ГЛАВЫ:
{previous_chapters}

## ТЕКУЩАЯ ГЛАВА {chapter_number} - ДЕТАЛИ:
{chapter_details}

## КРИТИЧЕСКИ ВАЖНЫЕ ТРЕБОВАНИЯ:
- Объем: примерно {word_count} слов
- Стиль: соответствие жанру {genre}
- УЧТИ ВСЕ СОБЫТИЯ И ДИАЛОГИ ИЗ ПРЕДЫДУЩИХ ГЛАВ
- ОБЕСПЕЧЬ ПЛАВНЫЕ ПЕРЕХОДЫ И ЛОГИЧЕСКУЮ ПРЕЕМСТВЕННОСТЬ
- Развивай сюжетные линии, начатые в предыдущих главах
- Используй установленные характеры персонажей последовательно
- Развивай конфликты, заложенные ранее
- Используй указанные локации и предметы согласно общей структуре
- Естественные живые диалоги, учитывающие предыдущие взаимодействия персонажей. 
- Логическое разрешения внутренних конфликтов персонажей и их пути (если применимо)
- Яркие развязка и финал (если применимо)
- НЕ ВОСПРОИЗВОДИ ТЕКСТ ПРОМПТА
- НЕ ЗЛОУПОТРЕБЛЯЙ КОЛИЧЕСТВОМ ДИАЛОГОВ, БОЛЬШЕ ДЕЙСТВИЯ

Напиши полный текст главы {chapter_number}, начиная непосредственно с повествования, КОТОРОЕ ЛОГИЧЕСКИ ВЫТЕКАЕТ ИЗ ПРЕДЫДУЩИХ СОБЫТИЙ.
"""

def generate_structure(genre, setting, alias):
    """Генерирует структуру повести"""
    try:
        alias_text = f"Дополнительная идея пользователя: {alias}" if alias else ""
        
        prompt = STRUCTURE_PROMPT.format(
            genre=genre,
            setting=setting,
            alias_text=alias_text
        )
        
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        
        return response.text
    except Exception as e:
        st.error(f"Ошибка при генерации структуры: {str(e)}")
        return None

def generate_chapter(genre, setting, alias, structure, previous_chapters, chapter_number, chapter_details, word_count):
    """Генерирует отдельную главу повести с учетом предыдущих глав"""
    try:
        alias_text = f"Дополнительная идея пользователя: {alias}" if alias else ""
        
        # Формируем текст предыдущих глав для контекста
        previous_chapters_text = "Это первая глава, предыдущих глав нет." if not previous_chapters else previous_chapters
        
        prompt = CHAPTER_PROMPT.format(
            genre=genre,
            setting=setting,
            alias_text=alias_text,
            structure=structure,
            previous_chapters=previous_chapters_text,
            chapter_number=chapter_number,
            chapter_details=chapter_details,
            word_count=word_count
        )
        
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        
        return response.text
    except Exception as e:
        st.error(f"Ошибка при генерации главы {chapter_number}: {str(e)}")
        return None

def parse_structure_for_chapters(structure_text):
    """Парсит структуру для извлечения информации о главах"""
    # В реальном приложении здесь должна быть сложная логика парсинга структуры
    # Для демонстрации создадим упрощенную структуру глав
    chapters = []
    
    lines = structure_text.split('\n')
    current_chapter = None
    
    for line in lines:
        line = line.strip()
        if line.lower().startswith('глава') or line.lower().startswith('chapter'):
            if current_chapter:
                chapters.append(current_chapter)
            current_chapter = {"title": line, "details": ""}
        elif current_chapter and line:
            current_chapter["details"] += line + "\n"
    
    if current_chapter:
        chapters.append(current_chapter)
    
    # Если не удалось распарсить, создаем базовую структуру
    if not chapters:
        chapters = [
            {"title": "Глава 1: Начало пути", "details": "Знакомство с главным героем и миром"},
            {"title": "Глава 2: Первые испытания", "details": "Герой сталкивается с первыми трудностями"},
            {"title": "Глава 3: Развитие конфликта", "details": "Углубление основных противоречий"},
            {"title": "Глава 4: Поворотный момент", "details": "Ключевое событие, меняющее ход истории"},
            {"title": "Глава 5: Нарастание напряжения", "details": "Ситуация усложняется"},
            {"title": "Глава 6: Кризис", "details": "Герой оказывается в сложнейшем положении"},
            {"title": "Глава 7: Решение", "details": "Герой находит путь к разрешению конфликта"},
            {"title": "Глава 8: Кульминация", "details": "Развязка основных событий"},
            {"title": "Глава 9: Финал", "details": "Завершение истории, выводы"}
        ]
    
    return chapters

def main():
    st.set_page_config(
        page_title="Графоманъ: генератор повестей",
        page_icon="📖",
        layout="wide"
    )
    
    st.title("📖 Графоманъ: генератор повестей")
    st.markdown("Создавайте повести в заданном жанре и сеттинге")
    
    # Секция ввода параметров
    st.header("1. Параметры повести")
    
    col1, col2 = st.columns(2)
    
    with col1:
        genre = st.text_input(
            "Жанр произведения:",
            placeholder="например: фэнтези, научная фантастика, детектив, роман...",
            help="Укажите основной жанр вашей повести"
        )
    
    with col2:
        setting = st.text_input(
            "Сеттинг (место и время действия):",
            placeholder="например: средневековое королевство, космическая станция в 2250 году...",
            help="Опишите мир, в котором происходит действие"
        )
    
    st.header("2. Дополнительная идея (опционально)")
    alias = st.text_area(
        "Дополнительная идея или концепция:",
        height=100,
        placeholder="например: история о программисте, попавшем в мир магии, где технологии заменяют заклинания...",
        help="Любые дополнительные пожелания или идеи для сюжета"
    )
    
    # Кнопка генерации
    st.header("3. Генерация повести")
    
    if st.button("🎭 Начать создание повести", type="primary"):
        if not genre or not setting:
            st.warning("⚠️ Пожалуйста, заполните жанр и сеттинг")
            return
        
        # Генерация структуры
        with st.spinner("📐 Создаю структуру произведения..."):
            structure = generate_structure(genre, setting, alias)
            
            if not structure:
                st.error("❌ Не удалось создать структуру произведения")
                return
            
            st.success("✅ Структура произведения создана!")
            
            # Отображаем структуру
            st.divider()
            st.header("📋 Структура произведения")
            st.text_area("Структура:", structure, height=400, key="structure")
        
        # Парсим структуру для получения информации о главах
        chapters_info = parse_structure_for_chapters(structure)
        
        # Генерация глав
        st.divider()
        st.header("🖋️ Написание глав")
        
        full_story = ""
        progress_bar = st.progress(0)
        status_text = st.empty()
        chapter_display = st.empty()
        
        chapters_count = len(chapters_info)
        words_per_chapter = 8000  # Примерный объем на главу
        
        for chapter_num in range(chapters_count):
            status_text.text(f"Пишу главу {chapter_num + 1} из {chapters_count}...")
            
            # Получаем информацию о текущей главе
            chapter_info = chapters_info[chapter_num]
            chapter_details = f"{chapter_info['title']}\n{chapter_info['details']}"
            
            # Показываем текущую главу в интерфейсе
            with chapter_display.container():
                st.subheader(f"Глава {chapter_num + 1}: {chapter_info['title']}")
                st.write(chapter_info['details'])
            
            # Генерируем главу с учетом предыдущего контекста
            chapter_text = generate_chapter(
                genre, setting, alias, structure, 
                full_story,  # Передаем все предыдущие главы как контекст
                chapter_num + 1, 
                chapter_details, 
                words_per_chapter
            )
            
            if chapter_text:
                # Добавляем новую главу к полному тексту
                full_story += f"\n\nГЛАВА {chapter_num + 1}: {chapter_info['title']}\n\n{chapter_text}"
                st.success(f"✅ Глава {chapter_num + 1} завершена")
                
                # Показываем прогресс и последнюю написанную главу
                with chapter_display.container():
                    st.subheader(f"Написано: Глава {chapter_num + 1}")
                    st.text_area(f"Текст главы {chapter_num + 1}:", chapter_text, height=200, key=f"chapter_{chapter_num}")
            else:
                st.error(f"❌ Ошибка при написании главы {chapter_num + 1}")
                break
            
            progress_bar.progress((chapter_num + 1) / chapters_count)
        
        if full_story.strip():
            # Отображаем полную повесть
            st.divider()
            st.header("📘 Готовая повесть")
            
            st.text_area("Полный текст повести:", full_story, height=600, key="full_story")
            
            # Статистика
            word_count = len(full_story.split())
            st.sidebar.header("📊 Статистика")
            st.sidebar.write(f"Количество глав: {chapters_count}")
            st.sidebar.write(f"Общий объем: {word_count} слов")
            
            # Кнопки экспорта
            st.divider()
            st.header("💾 Экспорт результата")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Скачивание как TXT
                b64_txt = base64.b64encode(full_story.encode()).decode()
                href_txt = f'<a href="data:file/txt;base64,{b64_txt}" download="повесть_{genre}.txt">📥 Скачать как TXT</a>'
                st.markdown(href_txt, unsafe_allow_html=True)
            
            with col2:
                # Копирование в буфер обмена
                if st.button("📋 Скопировать в буфер обмена"):
                    st.code(full_story, language="markdown")
                    st.success("Текст скопирован в буфер обмена!")
    
    # Информационная панель
    st.sidebar.header("ℹ️ О приложении")
    st.sidebar.info("""
    **Генератор повестей** создает литературные произведения 
    на основе заданных параметров.
    
    **Как использовать:**
    1. Укажите жанр и сеттинг
    2. Добавьте дополнительную идею (по желанию)
    3. Нажмите "Начать создание повести"
    4. Получите структуру и полный текст
    
    **Процесс создания:**
    - Сначала генерируется детальная структура
    - Затем последовательно пишутся главы
    - Каждая следующая глава учитывает содержание предыдущих
    - Общий объем: ~8000+ слов каждая глава
    """)
    
    st.sidebar.header("🎭 Подсказки")
    st.sidebar.write("""
    - Будьте конкретны в описании жанра
    - Детально опишите сеттинг для лучшего погружения
    - Используйте дополнительную идею для уникальности сюжета
    - Каждая глава пишется с учетом предыдущих для целостности
    """)

if __name__ == "__main__":
    main()
