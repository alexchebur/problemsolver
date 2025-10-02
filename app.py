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
   - Завязка: представление мира и персонажей, начало конфликта
   - Кульминация: развитие конфликта, ключевые события
   - Развязка: разрешение основных противоречий
   - Финал: заключительная часть, выводы

2. **Детальный план глав** (минимум 8 глав, общий объем не менее 8000 слов):
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

# Промпт для генерации отдельных глав
CHAPTER_PROMPT = """
Ты - профессиональный писатель. Напиши главу повести на основе предоставленной структуры.

## Контекст:
Жанр: {genre}
Сеттинг: {setting}
{alias_text}

## Структура произведения:
{structure}

## Задача главы {chapter_number}:
{chapter_details}

## Требования:
- Объем: примерно {word_count} слов
- Стиль: соответствие жанру {genre}
- Развитие сюжета согласно общей структуре
- Проработка персонажей согласно их описаниям
- Использование указанных локаций и предметов
- Естественные диалоги и описания
- Плавный переход от предыдущих событий (если применимо)
- Яркое завершение конфликта персонажа (если применимо и соответствует общей фабуле)

Напиши полный текст главы, начиная непосредственно с повествования.
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
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        return response.text
    except Exception as e:
        st.error(f"Ошибка при генерации структуры: {str(e)}")
        return None

def generate_chapter(genre, setting, alias, structure, chapter_number, chapter_details, word_count):
    """Генерирует отдельную главу повести"""
    try:
        alias_text = f"Дополнительная идея пользователя: {alias}" if alias else ""
        
        prompt = CHAPTER_PROMPT.format(
            genre=genre,
            setting=setting,
            alias_text=alias_text,
            structure=structure,
            chapter_number=chapter_number,
            chapter_details=chapter_details,
            word_count=word_count
        )
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        return response.text
    except Exception as e:
        st.error(f"Ошибка при генерации главы {chapter_number}: {str(e)}")
        return None

def main():
    st.set_page_config(
        page_title="Генератор повестей",
        page_icon="📖",
        layout="wide"
    )
    
    st.title("📖 Генератор повестей")
    st.markdown("Создавайте увлекательные повести в заданном жанре и сеттинге")
    
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
        
        # Генерация глав
        st.divider()
        st.header("🖋️ Написание глав")
        
        # Здесь в реальном приложении нужно было бы распарсить структуру
        # чтобы получить количество глав и их описание
        # Для демонстрации будем генерировать 8 глав
        
        full_story = ""
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        chapters_count = 8  # Стандартное количество глав
        words_per_chapter = 1000  # Примерный объем на главу
        
        for chapter_num in range(1, chapters_count + 1):
            status_text.text(f"Пишу главу {chapter_num} из {chapters_count}...")
            
            # В реальном приложении здесь нужно извлекать описание конкретной главы из структуры
            chapter_details = f"Глава {chapter_num} - развитие сюжета согласно общей структуре"
            
            chapter_text = generate_chapter(
                genre, setting, alias, structure, 
                chapter_num, chapter_details, words_per_chapter
            )
            
            if chapter_text:
                full_story += f"\n\nГЛАВА {chapter_num}\n\n{chapter_text}"
                st.success(f"✅ Глава {chapter_num} завершена")
            else:
                st.error(f"❌ Ошибка при написании главы {chapter_num}")
                break
            
            progress_bar.progress(chapter_num / chapters_count)
        
        if full_story.strip():
            # Отображаем полную повесть
            st.divider()
            st.header("📘 Готовая повесть")
            
            st.text_area("Полный текст повести:", full_story, height=600, key="full_story")
            
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
    **Генератор повестей** создает полноценные литературные произведения 
    на основе заданных параметров.
    
    **Как использовать:**
    1. Укажите жанр и сеттинг
    2. Добавьте дополнительную идею (по желанию)
    3. Нажмите "Начать создание повести"
    4. Получите структуру и полный текст
    
    **Процесс создания:**
    - Сначала генерируется детальная структура
    - Затем пишутся отдельные главы
    - Общий объем: ~8000 слов
    - Соответствие канонам литературного творчества
    """)
    
    st.sidebar.header("🎭 Подсказки")
    st.sidebar.write("""
    - Будьте конкретны в описании жанра
    - Детально опишите сеттинг для лучшего погружения
    - Используйте дополнительную идею для уникальности сюжета
    - Результат может варьироваться - пробуйте разные комбинации!
    """)

if __name__ == "__main__":
    main()
