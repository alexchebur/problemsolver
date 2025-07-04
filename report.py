# report.py
import re
import html
from datetime import datetime
import markdown
import base64
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

def create_html_report(content: str, title: str = "Отчет") -> bytes:
    """Создает HTML отчет с полной поддержкой Markdown и Mermaid.js"""
    # Генерируем HTML
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{title}</title>
        <script src="https://cdn.jsdelivr.net/npm/mermaid@10.6.1/dist/mermaid.min.js"></script>
        <script>
            // Конфигурация Mermaid с обработкой ошибок
            mermaid.initialize({{
                startOnLoad: true,
                theme: 'default',
                securityLevel: 'loose',
                errorRenderer: function(err, svg) {{
                    const container = document.getElementById('mermaid-error-' + err.strId);
                    if (container) {{
                        container.innerHTML = `
                            <div class="mermaid-error">
                                <strong>Ошибка в диаграмме:</strong> ${{err.message}}
                                <pre>${{err.str}}</pre>
                            </div>
                        `;
                    }}
                    return svg;
                }}
            }});
        </script>
        <style>
            /* ... (существующие стили остаются без изменений) ... */
        </style>
    </head>
    <body>
        <div class="report-header">
            <h1>{title}</h1>
            <p>Сгенерировано: {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>
        </div>
        
        <div class="content">
            {convert_md_to_html(content)}
        </div>
        
        <div class="footer">
            Отчет сгенерирован с помощью Troubleshooter
        </div>
    </body>
    </html>
    """
    
    return html_template.encode('utf-8')

def convert_md_to_html(md_text: str) -> str:
    """Конвертирует Markdown в HTML с сохранением блоков Mermaid"""
    mermaid_blocks = {}
    block_id = 0

    def replace_mermaid_with_placeholder(match):
        nonlocal block_id
        mermaid_code = match.group(1).strip()
        fixed_code = fix_mermaid_syntax(mermaid_code)
        placeholder = f"%%%MERMAID_PLACEHOLDER_{block_id}%%%"
        mermaid_blocks[placeholder] = fixed_code
        block_id += 1
        return f"\n\n{placeholder}\n\n"  # Отделяем пустыми строками

    # Заменяем блоки Mermaid на плейсхолдеры
    text_with_placeholders = re.sub(
        r'```mermaid\s*(.*?)```',
        replace_mermaid_with_placeholder,
        md_text,
        flags=re.DOTALL
    )
    
    # Конвертируем Markdown в HTML
    html_content = markdown.markdown(
        text_with_placeholders,
        extensions=[
            'extra', 'codehilite', 'fenced_code', 
            'tables', 'attr_list', 'md_in_html',
            'nl2br', 'sane_lists', 'toc'
        ],
        output_format='html5'
    )
    
    # Заменяем плейсхолдеры на финальные блоки Mermaid
    for placeholder, fixed_code in mermaid_blocks.items():
        mermaid_html = f"""
        <div class="diagram-wrapper">
            <div class="mermaid-container">
                <script type="text/mermaid" id="mermaid-{placeholder}">
                    {fixed_code}
                </script>
                <div id="mermaid-error-mermaid-{placeholder}"></div>
            </div>
        </div>
        """
        html_content = html_content.replace(placeholder, mermaid_html)
    
    return html_content

def fix_mermaid_syntax(mermaid_code: str) -> str:
    """Исправляет синтаксические ошибки в диаграммах Mermaid"""
    # Удаляем HTML-теги
    code = re.sub(r'<[^>]+>', '', mermaid_code)
    code = code.strip()
    
    # Декодируем HTML-сущности
    code = html.unescape(code)
    code = code.replace("&quot;", '"')
    code = code.replace("&amp;", "&")
    
    # 3. Удаление некорректных символов
    code = re.sub(r'[^a-zA-Z0-9\s_\-\[\]{}();"\'<>=]', '', code)
    
    # 4. Завершение незавершенных команд
    if not code.endswith(';') and not code.endswith(']') and not code.endswith('}'):
        code += ';'
    
    # 5. Добавление точек с запятой в конце команд
    lines = []
    for line in code.split('\n'):
        line = line.strip()
        if line:
            # Добавляем точку с запятой, если ее нет
            if not line.endswith(';') and '-->' in line:
                line += ';'
            lines.append(line)
    code = '\n'.join(lines)
    
    # 6. Завершение незакрытых узлов
    if '"' in code:
        open_quotes = code.count('"')
        if open_quotes % 2 != 0:
            code += '"'
    
    # 7. Проверка и завершение узлов
    def complete_nodes(match):
        node_text = match.group(1)
        return f'["{node_text.strip()}"]'
    
    code = re.sub(r'\["([^"]*)$', complete_nodes, code)
    
    # 8. Замена пустых узлов
    code = re.sub(r'\["\s*"\]', '["Не указано"]', code)
    code = re.sub(r'\(\s*\)', '("Не указано")', code)
    code = re.sub(r'\{\s*\}', '{"Не указано"}', code)
    
    # 9. Добавление ориентации по умолчанию
    if not re.search(r'^\s*(graph|flowchart)\s+[A-Z]{2}', code):
        if "graph" in code or "flowchart" in code:
            code = re.sub(r'(graph|flowchart)\s+', r'\1 TD\n', code)
        else:
            code = "graph TD\n" + code
    
    # 10. Упрощение диаграмм с большим количеством узлов
    #nodes = re.findall(r'\w+\[".*?"\]|\w+\(.*?\)|\w+\{.*?\}', code)
    #if len(nodes) > 10:
        #code = "graph TD\nA[Слишком сложная диаграмма]\nB[Упростите количество узлов]"
    
    return code
