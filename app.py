import streamlit as st
import google.generativeai as genai
import base64
import time

# Настройка API
api_key = st.secrets.get('GEMINI_API_KEY')
if not api_key:
    st.error("❌ API ключ не найден. Пожалуйста, настройте GEMINI_API_KEY в секретах Streamlit")
    st.stop()

genai.configure(api_key=api_key)

# Фрагменты произведений авторов для стилизации
AUTHOR_STYLES = {
    "tolstoy": {
        "name": "Л.Н. Толстой",
        "fragment": """
Фрагмент из "Войны и мира":
«Что ж, пора? — сказала Элен, оглянувшись на Наташу с тем, что Наташа сочла за значительную улыбку. — Пойдем в гостиную. — Граф Безухов вышел вперед, и все трое пошли в гостиную. 
Они вошли в небольшую комнату, с голубыми обоями, с красным и зеленым ковром и с несколькими портретами. На столах стояли дорогие безделушки. Берг сидел у бюро и писал что-то. 
Княжна Марья сидела на турецком диване и перебирала четки. Она была бледна, худа, с черными глазами. Она была одета в простое темное платье. 
Когда вошли, она медленно поднялась и оперлась рукой о стол. В движениях ее была какая-то особенная, не женская, а скорее кошачья мягкость и грация. 
Глаза ее, большие, глубокие, лучистые, остановились на Пьере с выражением вопросительным и вместе с тем ласковым. 
"Я рада, что вы пришли", — сказала она тем грудным голосом, который так шел к ее глубоким глазам.»
        """,
        "description": "Психологическая глубина, детальные описания внутреннего мира персонажей, эпический размах"
    },
    "pelevin": {
        "name": "В.О. Пелевин", 
        "fragment": """
Фрагмент из "Generation П":
«Вся наша жизнь есть текст. Или, точнее, гипертекст. Каждое утро, просыпаясь, мы открываем новую вкладку в браузере сознания. 
А вечером, закрывая глаза, мы просто сворачиваем все окна. Татарин сидел перед монитором и чувствовал, как реальность медленно, но верно превращается в набор пикселей. 
Каждый человек на улице был не более чем аватаркой, несущей в себе определенный пакет смыслов. Даже эта сигарета в его руках — не просто сигарета, а символ целой эпохи. 
Дым, поднимающийся к потолку, был похож на вопросительный знак, который он ставил перед всем миром.»
        """,
        "description": "Постмодернизм, ирония, философские размышления, игра с реальностью"
    },
    "nabokov": {
        "name": "В.В. Набоков",
        "fragment": """
Фрагмент из "Лолиты":
«Лолита, свет моей жизни, огонь моих чресел. Грех мой, душа моя. Ло-ли-та: кончик языка совершает путь в три шажка вниз по нёбу, чтобы на третьем толкнуться о зубы. Ло. Ли. Та. 
Она была Ло утром, стоя во весь свой рост в четыре фута десять дюймов, в одном носке. Она была Лола в штанах. Она была Долли в школе. Она была Долорес на пунктире официальных документов. 
Но в моих объятиях она всегда была Лолитой. Разве не случалось тебе, в летний час, услышать где-то вдали гул невидимой машины и, прислушавшись, понять, 
что это всего лишь кровь, гудевшая в твоих ушах? Разве не случалось тебе касаться чего-либо — скажем, подушки — и ощущать, будто твоя рука спит?»
        """,
        "description": "Лирическая проза, виртуозное владение языком, сложные метафоры, психологическая тонкость"
    }
}

# Базовый промпт для создания структуры произведения
STRUCTURE_PROMPT = """
Ты - профессиональный писатель и сценарист. На основе предоставленных пользователем данных создай подробную структуру повести.

## Задача:
Создать структуру повести в жанре {genre} с сеттингом: {setting}
{alias_text}
{style_instruction}

## Требования к структуре:
1. **Структура сюжета** (по канонам "завязка-кульминация-развязка-финал"):
   - Завязка: представление мира и персонажей, начало конфликта (главы 1-2)
   - Кульминация: развитие конфликта, ключевые события (главы 3-6)
   - Развязка: разрешение основных противоречий (главы 7-8)
   - Финал: заключительная часть, выводы (глава 9)

2. **Детальный план глав** (9 глав,  объем каждой главы не менее 8000 слов):
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
   - Как завершается путь персонажа в сюжете (если применимо)

4. **Локации** - описание ключевых мест действия

5. **Предметы/артефакты** - значимые объекты в сюжете

6. **Краткая концовка** - общее направление финала

Структура должна быть достаточно детальной, чтобы служить основой для написания полного текста повести.
"""

# Промпт для генерации отдельных глав с учетом предыдущего контекста
CHAPTER_PROMPT = """
Ты - профессиональный писатель. Напиши главу повести на основе предоставленной структуры и ПРЕДЫДУЩИХ ГЛАВ.
{style_instruction}

## КОНТЕКСТ ПРОИЗВЕДЕНИЯ:
Жанр: {genre}
Сеттинг: {setting}
{alias_text}

## ПОЛНАЯ СТРУКТУРА ПРОИЗВЕДЕНИЯ:
{structure}

## ПРЕДЫДУЩИЕ ГЛАВЫ (для контекста и преемственности):
{previous_chapters_context}

## ТЕКУЩАЯ ГЛАВА {chapter_number} - ДЕТАЛИ:
{chapter_details}

## КРИТИЧЕСКИ ВАЖНЫЕ ТРЕБОВАНИЯ:
- Объем: примерно {word_count} слов
- Стиль: соответствие жанру {genre}
- Сюжет: НЕ ОТКЛОНЯЙСЯ от полной структуры произведения, списка персонажей
- Локации, предметы: используй локации и предметы из сгенерированной структуры произведения {structure}
- УЧТИ ВСЕ СОБЫТИЯ, ДИАЛОГИ И РАЗВИТИЕ ПЕРСОНАЖЕЙ ИЗ ПРЕДЫДУЩИХ ГЛАВ
- ОБЕСПЕЧЬ ПЛАВНЫЕ ПЕРЕХОДЫ И ЛОГИЧЕСКУЮ ПРЕЕМСТВЕННОСТЬ С ПРЕДЫДУЩИМИ ГЛАВАМИ
- Развивай сюжетные линии, начатые в предыдущих главах
- Используй установленные характеры персонажей последовательно
- Развивай конфликты, заложенные ранее
- Используй указанные локации и предметы согласно общей структуре
- Естественные диалоги, учитывающие предыдущие взаимодействия персонажей
- НЕ ЗЛОУПОТРЕБЛЯЙ ДИАЛОГАМИ, БОЛЬШЕ ДЕЙСТВИЯ И ОПИСАНИЙ
- МЕНЬШЕ ШТАМПОВ И КЛИШЕ, БОЛЬШЕ ОРИГИНАЛЬНЫХ ИДЕЙ И НЕОЖИДАННЫХ СЮЖЕТНЫХ ПОВОРОТОВ
- НЕ ВОСПРОИЗВОДИ В ТЕКСТЕ ПРОМПТЫ И СОДЕРЖАНИЕ ПРЕДЫДУЩИХ ГЛАВ
- ИЗБЕГАЙ НЕНУЖНОГО ПАФОСА
- ИЗБЕГАЙ НЕРВОЗНЫХ ПОВТОРЯЮЩИХСЯ ФРАЗ ВРОДЕ 'ОНА СДЕЛАЛА ЭТО', 'ОНА БЫЛА ГОТОВА'

Напиши полный текст главы {chapter_number}, начиная непосредственно с повествования, КОТОРОЕ ЛОГИЧЕСКИ ВЫТЕКАЕТ ИЗ ПРЕДЫДУЩИХ ГЛАВ.
"""

# Промпт для литературного редактора
EDITOR_PROMPT = """
Ты редактируешь художественный текст. Проанализируй представленную главу и перепиши ее, обогатив деталями описания событий, чувств и мыслей персонажей, исправив следующие ошибки:

1. Бредовые повторяющиеся по смыслу реплики персонажей и однотипные фразы
2. Тривиальные описания событий и поступков без деталей
3. Трюизмы, тавтологию.

{style_instruction}

## КОНТЕКСТ ПРОИЗВЕДЕНИЯ:
Жанр: {genre}
Сеттинг: {setting}
{alias_text}

## СТРУКТУРА ПРОИЗВЕДЕНИЯ:
{structure}

## ПРЕДЫДУЩИЕ ГЛАВЫ (для контекста):
{previous_chapters_context}

## ТЕКУЩАЯ ГЛАВА {chapter_number} ДЛЯ РЕДАКТУРЫ:
{chapter_text}

## ЗАДАЧА:
Перепиши главу, сохраняя сюжет и ключевые события, но улучшая литературное качество:
- Обогати описания деталями
- Углуби психологию персонажей через их мысли и чувства
- Убери повторяющиеся и шаблонные фразы
- Добавь оригинальности и выразительности
- Сохрани общий стиль и тон произведения
- ОБЕСПЕЧЬ ПРЕЕМСТВЕННОСТЬ С ПРЕДЫДУЩИМИ ГЛАВАМИ
- ПРИВЕДИ В СООТВЕТСТВИЕ СТРУКТУРЕ СЮЖЕТА
- УБЕРИ ЛОЖНЫЕ КУЛЬМИНАЦИИ И ЛОЖНЫЕ КОНЦОВКИ, НЕ СООТВЕТСТВУЮЩИЕ КРАТКОМУ ОПИСАНИЮ В СТРУКТУРЕ СЮЖЕТА

Верни только улучшенный текст главы без дополнительных комментариев.
"""

# Промпт для рецензии критика
CRITIQUE_PROMPT = """
Напиши рецензию на мой текст:

{full_story}

Твой тон — строгий, профессиональный, лишенный сентиментальности.
Твой анализ — точный и безжалостный к слабым местам.
Твоя критика всегда конструктивна. Ты не просто указываешь на ошибку, а объясняешь, почему это ошибка, и как её можно исправить.
Для анализа и вынесения вердиктов ты используешь медицинскую, хирургическую или юридическую метафорику (например: "Диагноз: ...", "Протокол вскрытия:", "Вердикт: ..."). 
Поставь тексту оценку от 10 - отлично до 0 - кошмарно.
"""

def get_style_instruction(selected_style):
    """Возвращает инструкцию по стилю в зависимости от выбранного автора"""
    if selected_style == "none":
        return "", ""
    
    author = AUTHOR_STYLES[selected_style]
    instruction = f"\n\n## СТИЛИСТИЧЕСКИЕ ТРЕБОВАНИЯ:\nИспользуй стиль автора согласно представленному фрагменту из {author['name']}:\n{author['fragment']}\n\nСтрого следуй стилистике, языковым особенностям и манере повествования данного автора."
    
    return instruction, author['description']

def generate_structure(genre, setting, alias, temperature, style_instruction):
    """Генерирует структуру повести с заданной температурой"""
    try:
        alias_text = f"Дополнительная идея пользователя: {alias}" if alias else ""
        
        prompt = STRUCTURE_PROMPT.format(
            genre=genre,
            setting=setting,
            alias_text=alias_text,
            style_instruction=style_instruction
        )
        
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
        
        # Используем настройки генерации с заданной температурой
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
        st.error(f"Ошибка при генерации структуры: {str(e)}")
        return None

def generate_chapter(genre, setting, alias, structure, previous_chapters_context, chapter_number, chapter_details, word_count, style_instruction):
    """Генерирует отдельную главу повести с учетом всех предыдущих глав"""
    try:
        alias_text = f"Дополнительная идея пользователя: {alias}" if alias else ""
        
        # Формируем контекст предыдущих глав
        if not previous_chapters_context:
            previous_chapters_context = "Это первая глава, предыдущих глав нет."
        
        prompt = CHAPTER_PROMPT.format(
            genre=genre,
            setting=setting,
            alias_text=alias_text,
            structure=structure,
            previous_chapters_context=previous_chapters_context,
            chapter_number=chapter_number,
            chapter_details=chapter_details,
            word_count=word_count,
            style_instruction=style_instruction
        )
        
        model = genai.GenerativeModel('gemini-2.0-flash-lite')
        
        # Фиксированные настройки для генерации глав - низкая температура для консистентности
        generation_config = genai.types.GenerationConfig(
            temperature=0.3,  # Низкая температура для последовательности
            top_p=0.7,
            top_k=20
        )
        
        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )
        
        return response.text
    except Exception as e:
        st.error(f"Ошибка при генерации главы {chapter_number}: {str(e)}")
        return None

def literary_edit_chapter(genre, setting, alias, structure, previous_chapters_context, chapter_number, chapter_text, style_instruction):
    """Редактирует главу с помощью литературного редактора"""
    try:
        alias_text = f"Дополнительная идея пользователя: {alias}" if alias else ""
        
        # Формируем контекст предыдущих глав
        if not previous_chapters_context:
            previous_chapters_context = "Это первая глава, предыдущих глав нет."
        
        prompt = EDITOR_PROMPT.format(
            genre=genre,
            setting=setting,
            alias_text=alias_text,
            structure=structure,
            previous_chapters_context=previous_chapters_context,
            chapter_number=chapter_number,
            chapter_text=chapter_text,
            style_instruction=style_instruction
        )
        
        model = genai.GenerativeModel('gemini-2.0-flash-lite')
        
        # Настройки для редактор - средняя температура для баланса креативности и сохранения сюжета
        generation_config = genai.types.GenerationConfig(
            temperature=0.5,
            top_p=0.8,
            top_k=30
        )
        
        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )
        
        return response.text
    except Exception as e:
        st.error(f"Ошибка при редактировании главы {chapter_number}: {str(e)}")
        return chapter_text  # Возвращаем оригинальный текст в случае ошибки

def parse_structure_for_chapters(structure_text):
    """Парсит структуру для извлечения информации о главах"""
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

def generate_critique(full_story):
    """Генерирует рецензию от беспощадного критика"""
    try:
        # Ограничиваем длину текста для избежания переполнения контекста
        if len(full_story) > 100000:  # Примерное ограничение
            full_story = full_story[:100000] + "\n\n[Текст сокращен для рецензии...]"
        
        prompt = CRITIQUE_PROMPT.format(full_story=full_story)
        
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        generation_config = genai.types.GenerationConfig(
            temperature=0.7,  # Средняя температура для баланса строгости и креативности
            top_p=0.8,
            top_k=40,
            max_output_tokens=2000  # Ограничиваем длину ответа
        )
        
        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )
        
        return response.text
    except Exception as e:
        st.error(f"Ошибка при генерации рецензии: {str(e)}")
        return None

def main():
    st.set_page_config(
        page_title="Графоманъ: Генератор повестей",
        page_icon="📖",
        layout="wide"
    )
    
    st.title("📖 Графоманъ: Генератор повестей")
    st.markdown("Создавайте увлекательные повести в заданном жанре и сеттинге")
    
    # Инициализация session_state
    if 'current_step' not in st.session_state:
        st.session_state.current_step = 1  # 1: параметры, 2: генерация, 3: результат
    
    if 'full_story' not in st.session_state:
        st.session_state.full_story = ""
    
    if 'edited_story' not in st.session_state:
        st.session_state.edited_story = ""  # Для хранения отредактированной версии
    
    if 'critique' not in st.session_state:
        st.session_state.critique = None
    
    if 'is_generating_critique' not in st.session_state:
        st.session_state.is_generating_critique = False
        
    if 'structure' not in st.session_state:
        st.session_state.structure = None
        
    if 'chapters_info' not in st.session_state:
        st.session_state.chapters_info = []
        
    if 'current_chapter' not in st.session_state:
        st.session_state.current_chapter = 0
        
    if 'previous_chapters_context' not in st.session_state:
        st.session_state.previous_chapters_context = ""  # Контекст всех предыдущих глав
        
    if 'selected_style' not in st.session_state:
        st.session_state.selected_style = "none"
    
    # Шаг 1: Параметры повести
    if st.session_state.current_step == 1:
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
        
        # Выбор стиля автора
        st.header("🎭 Стиль автора")
        st.info("Выберите стиль известного писателя для вашей повести")
        
        # Инициализация selected_style если не существует
        if 'selected_style' not in st.session_state:
            st.session_state.selected_style = "none"
        
        # Создаем колонки для кнопок стилей
        style_col1, style_col2, style_col3, style_col4 = st.columns(4)
        
        with style_col1:
            if st.button("📚 Без стиля", use_container_width=True, key="style_none"):
                st.session_state.selected_style = "none"
                st.rerun()
        with style_col2:
            if st.button("⚜️ Толстой", use_container_width=True, key="style_tolstoy"):
                st.session_state.selected_style = "tolstoy"
                st.rerun()
        with style_col3:
            if st.button("🌀 Пелевин", use_container_width=True, key="style_pelevin"):
                st.session_state.selected_style = "pelevin"
                st.rerun()
        with style_col4:
            if st.button("🦋 Набоков", use_container_width=True, key="style_nabokov"):
                st.session_state.selected_style = "nabokov"
                st.rerun()
        
        # Визуальное отображение выбранного стиля
        st.markdown("---")
        
        # Показываем выбранный стиль
        if st.session_state.selected_style != "none":
            author = AUTHOR_STYLES[st.session_state.selected_style]
            st.success(f"**Выбран стиль:** {author['name']}")
            st.info(f"**Описание стиля:** {author['description']}")
            
            with st.expander("📖 Посмотреть фрагмент стиля"):
                st.text_area("Фрагмент произведения:", author['fragment'], height=200, key=f"fragment_{st.session_state.selected_style}")
        else:
            st.info("⚪ Стиль не выбран - будет использован нейтральный литературный стиль")
        
        # Ползунок фантазии
        st.header("2. Настройки творчества")
        
        creativity = st.slider(
            "Уровень фантазии писателя:",
            min_value=0.1,
            max_value=1.0,
            value=0.7,
            step=0.1,
            help=(
                "Низкое значение = более предсказуемый сюжет, строгое следование жанру\n"
                "Высокое значение = более креативный и неожиданный сюжет, возможны смешения жанров"
            )
        )
        
        # Отображаем пояснение к уровню фантазии
        creativity_descriptions = {
            0.1: "🤖 Максимальная предсказуемость - строгое следование канонам жанра",
            0.2: "📚 Консервативный подход - минимальные отклонения от стандартов",
            0.3: "📝 Умеренный реализм - баланс между традиционностью и творчеством", 
            0.4: "🎭 Сбалансированный - классический подход с элементами новизны",
            0.5: "✨ Стандартная креативность - хороший баланс предсказуемости и неожиданностей",
            0.6: "🌟 Творческий - заметные элементы оригинальности в сюжете",
            0.7: "🚀 Высокая фантазия - значительные творческие отклонения от шаблонов",
            0.8: "🎨 Очень креативный - смелые сюжетные повороты и нестандартные решения",
            0.9: "🔥 Экспериментальный - высокий уровень неожиданных событий",
            1.0: "⚡ Максимальная креативность - полностью оригинальный и непредсказуемый сюжет"
        }
        
        # Показываем описание для текущего значения
        current_description = creativity_descriptions.get(creativity, "Сбалансированный подход")
        st.info(f"**Текущий уровень:** {current_description}")
        
        st.header("3. Дополнительная идея (опционально)")
        alias = st.text_area(
            "Дополнительная идея или концепция:",
            height=100,
            placeholder="например: история о программисте, попавшем в мир магии, где технологии заменяют заклинания...",
            help="Любые дополнительные пожелания или идеи для сюжета"
        )
        
        # Сохраняем параметры в session_state
        st.session_state.genre = genre
        st.session_state.setting = setting
        st.session_state.creativity = creativity
        st.session_state.alias = alias
        
        # Кнопка перехода к генерации
        if st.button("🎭 Начать создание повести", type="primary", key="start_creation"):
            if not genre or not setting:
                st.warning("⚠️ Пожалуйста, заполните жанр и сеттинг")
            else:
                st.session_state.current_step = 2
                st.rerun()
    
    # Шаг 2: Генерация повести
    elif st.session_state.current_step == 2:
        genre = st.session_state.genre
        setting = st.session_state.setting
        creativity = st.session_state.creativity
        alias = st.session_state.alias
        selected_style = st.session_state.selected_style
        
        st.header("🔄 Генерация повести")
        st.info(f"**Параметры:** Жанр: {genre}, Сеттинг: {setting}, Фантазия: {creativity}")
        
        if selected_style != "none":
            author_name = AUTHOR_STYLES[selected_style]['name']
            st.info(f"🎨 **Стиль автора:** {author_name}")
        
        # Получаем инструкцию по стилю
        style_instruction, style_description = get_style_instruction(selected_style)
        
        # Генерация структуры (только если еще не сгенерирована)
        if st.session_state.structure is None:
            with st.spinner("📐 Создаю структуру произведения..."):
                structure = generate_structure(genre, setting, alias, creativity, style_instruction)
                
                if not structure:
                    st.error("❌ Не удалось создать структуру произведения")
                    if st.button("🔄 Попробовать снова"):
                        st.rerun()
                    return
                
                st.session_state.structure = structure
                st.success("✅ Структура произведения создана!")
        
        # Отображаем структуру
        st.divider()
        st.header("📋 Структура произведения")
        st.text_area("Структура:", st.session_state.structure, height=400, key="structure_display")
        
        # Парсим структуру для получения информации о главах (только если еще не распарсена)
        if not st.session_state.chapters_info:
            st.session_state.chapters_info = parse_structure_for_chapters(st.session_state.structure)
        
        # Генерация глав
        st.divider()
        st.header("🖋️ Написание глав")
        st.info("📝 Каждая глава генерируется с учетом текста ВСЕХ предыдущих глав для обеспечения последовательности сюжета")
        
        chapters_count = len(st.session_state.chapters_info)
        words_per_chapter = 8000  # Примерный объем на главу
        
        # Показываем прогресс
        progress_bar = st.progress(st.session_state.current_chapter / chapters_count)
        status_text = st.empty()
        
        # Если все главы уже сгенерированы, переходим к шагу 3
        if st.session_state.current_chapter >= chapters_count:
            st.session_state.current_step = 3
            st.success("🎉 Повесть успешно создана и отредактирована!")
            st.rerun()
            return
        
        # Генерируем текущую главу
        chapter_num = st.session_state.current_chapter
        chapter_info = st.session_state.chapters_info[chapter_num]
        chapter_details = f"{chapter_info['title']}\n{chapter_info['details']}"
        
        # Показываем текущую главу в интерфейсе
        st.subheader(f"Глава {chapter_num + 1}: {chapter_info['title']}")
        st.write(chapter_info['details'])
        
        status_text.text(f"Пишу главу {chapter_num + 1} из {chapters_count}...")
        
        # Генерируем главу с учетом ВСЕХ предыдущих глав
        chapter_text = generate_chapter(
            genre, setting, alias, st.session_state.structure,
            st.session_state.previous_chapters_context,  # Передаем контекст всех предыдущих глав
            chapter_num + 1, 
            chapter_details, 
            words_per_chapter,
            style_instruction
        )
        
        if chapter_text:
            # Отправляем главу на литературное редактирование
            with st.spinner(f"✏️ Редактирую главу {chapter_num + 1}..."):
                edited_chapter_text = literary_edit_chapter(
                    genre, setting, alias, st.session_state.structure,
                    st.session_state.previous_chapters_context,  # Контекст всех предыдущих глав
                    chapter_num + 1,
                    chapter_text,
                    style_instruction
                )
            
            # Добавляем оригинальную главу к полному тексту
            st.session_state.full_story += f"\n\nГЛАВА {chapter_num + 1}: {chapter_info['title']}\n\n{chapter_text}"
            
            # Добавляем отредактированную главу к финальному тексту
            st.session_state.edited_story += f"\n\nГЛАВА {chapter_num + 1}: {chapter_info['title']}\n\n{edited_chapter_text}"
            
            # ОБНОВЛЯЕМ КОНТЕКСТ ПРЕДЫДУЩИХ ГЛАВ - добавляем текущую отредактированную главу
            if st.session_state.previous_chapters_context:
                st.session_state.previous_chapters_context += f"\n\n--- ГЛАВА {chapter_num + 1} ---\n{edited_chapter_text}"
            else:
                st.session_state.previous_chapters_context = f"--- ГЛАВА {chapter_num + 1} ---\n{edited_chapter_text}"
            
            st.success(f"✅ Глава {chapter_num + 1} завершена и отредактирована")
            
            # Переходим к следующей главе
            st.session_state.current_chapter += 1
            
            # Обновляем прогресс
            progress_bar.progress(st.session_state.current_chapter / chapters_count)
            
            # Автоматически перезагружаем страницу для генерации следующей главы
            st.rerun()
            
        else:
            st.error(f"❌ Ошибка при написании главы {chapter_num + 1}")
            if st.button("🔄 Попробовать снова"):
                st.rerun()
    
    # Шаг 3: Результат и рецензия
    elif st.session_state.current_step == 3:
        st.header("📘 Готовая повесть")
        
        # Показываем выбранный стиль
        if st.session_state.selected_style != "none":
            author_name = AUTHOR_STYLES[st.session_state.selected_style]['name']
            st.success(f"🎨 **Стиль автора:** {author_name}")
        
        # Переключатель между оригинальной и отредактированной версией
        version = st.radio(
            "Выберите версию для просмотра:",
            ["📝 Отредактированная версия (рекомендуется)", "⚪ Оригинальная версия"],
            index=0
        )
        
        # Выбираем какую версию показывать
        display_story = st.session_state.edited_story if version.startswith("📝") else st.session_state.full_story
        
        # Отображаем полную повесть
        st.text_area("Полный текст повести:", display_story, height=600, key="full_story_display")
        
        # Статистика
        word_count = len(display_story.split())
        st.sidebar.header("📊 Статистика")
        st.sidebar.write(f"Общий объем: {word_count} слов")
        st.sidebar.write(f"Уровень фантазии: {st.session_state.creativity}")
        st.sidebar.write(f"Версия: {'Отредактированная' if version.startswith('📝') else 'Оригинальная'}")
        if st.session_state.selected_style != "none":
            st.sidebar.write(f"Стиль: {AUTHOR_STYLES[st.session_state.selected_style]['name']}")
        
        # Кнопки экспорта
        st.divider()
        st.header("💾 Экспорт результата")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Скачивание как TXT
            b64_txt = base64.b64encode(display_story.encode()).decode()
            version_suffix = "_отредактированная" if version.startswith("📝") else "_оригинальная"
            style_suffix = f"_{st.session_state.selected_style}" if st.session_state.selected_style != "none" else ""
            href_txt = f'<a href="data:file/txt;base64,{b64_txt}" download="повесть_{st.session_state.genre}{style_suffix}{version_suffix}.txt">📥 Скачать как TXT</a>'
            st.markdown(href_txt, unsafe_allow_html=True)
        
        with col2:
            # Копирование в буфер обмена
            if st.button("📋 Скопировать в буфер обмена", key="copy_full"):
                st.code(display_story, language="markdown")
                st.success("Текст скопирован в буфер обмена!")

        # Рецензия от критика
        st.divider()
        st.header("🎯 Рецензия от Беспощадного Критика")
        
        # Если рецензия уже сгенерирована, показываем ее
        if st.session_state.critique:
            st.subheader("Рецензия от Беспощадного Критика")
            st.text_area("", st.session_state.critique, height=400, key="critique_display")
            
            # Кнопка для копирования рецензии
            if st.button("📋 Скопировать рецензию", key="copy_critique"):
                st.code(st.session_state.critique, language="markdown")
                st.success("Рецензия скопирована в буфер обмена!")
            
            # Кнопка для обновления рецензии
            if st.button("🔄 Обновить рецензию", key="refresh_critique"):
                st.session_state.critique = None
                st.session_state.is_generating_critique = False
                st.rerun()
        
        # Если рецензия генерируется - показываем спиннер и запускаем генерацию
        elif st.session_state.is_generating_critique:
            with st.spinner("🔍 Критик анализирует произведение... Это может занять несколько минут"):
                # Используем отредактированную версию для рецензии
                critique = generate_critique(st.session_state.edited_story)
                if critique:
                    st.session_state.critique = critique
                    st.session_state.is_generating_critique = False
                    st.rerun()  # Перезагружаем для отображения результата
                else:
                    st.error("❌ Не удалось получить рецензию")
                    st.session_state.is_generating_critique = False
                    st.rerun()
        
        # Если рецензия еще не запрашивалась
        else:
            st.info("""
            **Получите профессиональную рецензию на вашу повесть:**
            - Строгий анализ сильных и слабых сторон
            - Конструктивные рекомендации по улучшению
            - Оценка по 10-балльной шкале
            - Профессиональная критика с медицинской/юридической метафорикой
            """)
            
            if st.button("📝 Получить рецензию от Беспощадного Критика", type="secondary"):
                st.session_state.is_generating_critique = True
                st.rerun()
        
        # Кнопка для создания новой повести
        st.divider()
        if st.button("🔄 Создать новую повесть", type="primary"):
            # Полностью сбрасываем состояние
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # Информационная панель
    st.sidebar.header("🎛️ Настройки генерации")
    st.sidebar.info("""
    **Температура генерации:**
    - **Структура:** регулируется ползунком (0.1-1.0)
    - **Главы:** фиксированная 0.3 для консистентности
    - **Редактор:** фиксированная 0.5 для баланса
    
    🔥 Высокая температура = больше креативности
    ❄️ Низкая температура = больше предсказуемости
    """)
    
    st.sidebar.header("🎭 Стили авторов")
    st.sidebar.info("""
    **Доступные стили:**
    - **Толстой:** Психологическая глубина, эпический размах
    - **Пелевин:** Постмодернизм, ирония, философские размышления  
    - **Набоков:** Лирическая проза, виртуозное владение языком
    
    Стиль влияет на все этапы генерации: структуру, главы и редактуру.
    """)
    
    st.sidebar.header("ℹ️ О приложении")
    st.sidebar.info("""
    **Генератор повестей** создает литературные произведения 
    на основе заданных параметров.
    
    **Как использовать:**
    1. Укажите жанр и сеттинг
    2. Выберите стиль автора (опционально)
    3. Настройте уровень фантазии
    4. Добавьте дополнительную идею (по желанию)
    5. Нажмите "Начать создание повести"
    6. Получите структуру и полный текст
    """)

if __name__ == "__main__":
    main()
