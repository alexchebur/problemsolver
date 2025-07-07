# report.py
import re
import html
from datetime import datetime
import markdown
import base64
import logging

# Настройка логирования
logger = logging.getLogger(__name__) 

# report.py
import re
import html
from datetime import datetime
import markdown
import os
import logging

# Настройка логирования
logger = logging.getLogger(__name__) 

def load_template():
    """Загружает HTML шаблон из файла"""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(current_dir, 'template.html')
        
        with open(template_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        logger.error(f"Ошибка загрузки шаблона: {str(e)}")
        # Возвращаем резервный шаблон
        return """<!DOCTYPE html>
        <html>
        <head><title>Отчет</title></head>
        <body>
            <h1>__TITLE__</h1>
            <p>Сгенерировано: __GENERATION_DATE__</p>
            <div class="content">__HTML_CONTENT__</div>
        </body>
        </html>"""

def create_html_report(content: str, title: str = "Отчет") -> bytes:
    """Создает HTML отчет с полной поддержкой Markdown и Mermaid.js"""
    try:
        # Загружаем шаблон
        html_template = load_template()
        
        # Генерируем HTML контент
        html_content = convert_md_to_html(content)
        generation_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # Заменяем плейсхолдеры
        html_template = html_template \
            .replace("__TITLE__", html.escape(title)) \
            .replace("__GENERATION_DATE__", html.escape(generation_date)) \
            .replace("__HTML_CONTENT__", html_content)
        
        return html_template.encode('utf-8')
    
    except Exception as e:
        logging.error(f"Ошибка при создании HTML: {str(e)}")
        # Возвращаем минимальный работающий HTML
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Отчет</title>
        </head>
        <body>
            <h1>{html.escape(title)}</h1>
            <p>Ошибка при генерации отчета: {html.escape(str(e))}</p>
            <pre>{html.escape(content[:5000])}</pre>
        </body>
        </html>
        """.encode('utf-8')
def convert_md_to_html(md_text: str) -> str:
    """Конвертирует Markdown в HTML с сохранением блоков Mermaid"""
    # Обрабатываем блоки Mermaid отдельно
    def process_mermaid(match):
        mermaid_code = match.group(1).strip()
        fixed_code = fix_mermaid_syntax(mermaid_code)
        
        # Возвращаем чистый HTML для диаграммы
        return f"""
<div class="diagram-wrapper">
    <div class="mermaid-container">
        <div class="mermaid">
{fixed_code}
        </div>
        <div class="mermaid-error-container"></div>
    </div>
</div>
        """
    
    # Обрабатываем блоки Mermaid ДО конвертации Markdown
    processed_content = re.sub(
        r'```mermaid\s*(.*?)```',
        process_mermaid,
        md_text,
        flags=re.DOTALL
    )
    
    # Конвертируем оставшийся Markdown в HTML
    html_content = markdown.markdown(
        processed_content,
        extensions=[
            'extra', 'codehilite', 'fenced_code', 
            'tables', 'attr_list', 'md_in_html',
            'nl2br', 'sane_lists', 'toc'
        ],
        output_format='html5'
    )
    
    # Исправляем возможные проблемы с экранированием
    html_content = html_content.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    
    return html_content

def fix_mermaid_syntax(mermaid_code: str) -> str:
    """Исправляет синтаксические ошибки в диаграммах Mermaid"""
    # Удаляем все HTML-теги и лишние символы
    code = re.sub(r'<[^>]+>', '', mermaid_code)
    code = re.sub(r'[^\w\s\-\+\*\/\(\)\[\]\{\}\<\>\=\|\:;,"\.#]', '', code)
    code = code.strip()
    
    # Декодируем HTML-сущности
    code = html.unescape(code)
    code = code.replace("&quot;", '"')
    code = code.replace("&amp;", "&")

    # Заменяем точки на пробелы ТОЛЬКО в текстовых метках узлов
    # Обрабатываем все типы нотаций: ["..."], ("..."), {...}
    code = re.sub(r'(\[|\(|\{)"([^"]*)\.([^"]*)"(\\|$)', 
                 lambda m: f'{m.group(1)}"{m.group(2)} {m.group(3)}"{m.group(4)}', 
                 code)
    
    # Упрощаем сложные диаграммы
    if len(code.split('\n')) > 35:
        return "graph TD\nA[Слишком сложная диаграмма]\nB[Упростите количество элементов]"
    
    # Исправляем основные синтаксические ошибки
    code = re.sub(r'(\w+)\s*\["([^"]*)"\]', r'\1["\2"]', code)  # Квадратные скобки
    code = re.sub(r'(\w+)\s*\("([^"]*)"\)', r'\1("\2")', code)  # Круглые скобки
    code = re.sub(r'(\w+)\s*\{"([^"]*)"\}', r'\1{"\2"}', code)  # Фигурные скобки
    code = re.sub(r'(\w+)\s+&\s+(\w+)', r'\1 & \2', code) # сохраняем символ &

    # Добавляем базовую ориентацию если отсутствует
    if not re.search(r'^\s*(graph|flowchart)\s+[A-Z]{2}', code, re.IGNORECASE):
        if re.search(r'(graph|flowchart)', code, re.IGNORECASE):
            code = re.sub(r'(graph|flowchart)\s+', r'\1 TD\n', code, flags=re.IGNORECASE)
        else:
            code = "graph TD\n" + code
    
    # Форматируем диаграмму: каждый элемент на новой строке
    if '\n' not in code:
        # Если вся диаграмма в одной строке, разбиваем на элементы
        code = code.replace(';', ';\n')
        code = code.replace('{', '{\n')
        code = code.replace('}', '}\n')
        code = code.replace('-->', '\n-->')
        code = re.sub(r'(\w+)\[', r'\n\1[', code)
        code = re.sub(r'(\w+)\(', r'\n\1(', code)
        code = re.sub(r'(\w+)\{', r'\n\1{', code)
        code = re.sub(r'([^\]\)\}])\s+([A-Z])', r'\1\n\2', code)
    
    # Завершаем все команды точкой с запятой
    lines = []
    for line in code.split('\n'):
        line = line.strip()
        if line and not line.endswith(';') and '-->' in line:
            line += ';'
        lines.append(line)
    code = '\n'.join(lines)
    
    # Удаляем пустые строки
    code = '\n'.join([line for line in code.split('\n') if line.strip()])
    
    # Добавляем отступы для улучшения читаемости
    formatted_code = []
    indent = 0
    for line in code.split('\n'):
        line = line.strip()
        if line.endswith('{'):
            formatted_code.append('  ' * indent + line)
            indent += 1
        elif line.startswith('}'):
            indent = max(0, indent - 1)
            formatted_code.append('  ' * indent + line)
        else:
            formatted_code.append('  ' * indent + line)
    
    return '\n'.join(formatted_code)
