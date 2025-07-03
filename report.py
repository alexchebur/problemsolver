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
            // Ждем полной загрузки страницы
            document.addEventListener('DOMContentLoaded', function() {{
                try {{
                    // Конфигурация Mermaid с обработкой ошибок
                    mermaid.initialize({{
                        startOnLoad: true,
                        theme: 'default',
                        securityLevel: 'loose',
                        flowchart: {{
                            useMaxWidth: true,
                            htmlLabels: true
                        }},
                        errorRenderer: function(err) {{
                            try {{
                                const container = document.getElementById('mermaid-error-' + err.strId);
                                if (container) {{
                                    container.innerHTML = `
                                        <div class="mermaid-error">
                                            <strong>Ошибка в диаграмме:</strong> ${{err.message}}
                                            <pre>${{err.str}}</pre>
                                        </div>
                                    `;
                                }}
                            }} catch (e) {{
                                console.error('Ошибка в обработчике ошибок Mermaid:', e);
                            }}
                            return '';
                        }}
                    }});
                
                    // Явный запуск рендеринга
                    mermaid.init(undefined, '.mermaid');
                }} catch (e) {{
                    console.error('Ошибка инициализации Mermaid:', e);
                }}
            }});
        </script>
        <style>
            /* ... остальные стили ... */
        </style>
    </head>
    <body>
        <!-- ... тело отчета ... -->
    </body>
    </html>
    """    
    return html_template.encode('utf-8')

def convert_md_to_html(md_text: str) -> str:
    """Конвертирует Markdown в HTML с сохранением блоков Mermaid"""
    # Обработка блоков Mermaid
    mermaid_blocks = []
    mermaid_counter = 0
    
    def mermaid_replacer(match):
        nonlocal mermaid_counter
        mermaid_code = match.group(1).strip()
        
        # Удаляем все HTML-теги
        mermaid_code = re.sub(r'<[^>]+>', '', mermaid_code)
        
        # Удаляем лишние пробелы
        mermaid_code = re.sub(r'\s+', ' ', mermaid_code)
        
        # Очистка и фиксация синтаксиса
        fixed_code = fix_mermaid_syntax(mermaid_code)
        
        # Генерация уникального ID
        block_id = mermaid_counter
        mermaid_counter += 1
        
        # Создаем HTML для диаграммы
        mermaid_div = f"""
        <div class="diagram-wrapper">
            <div class="mermaid-container">
                <div class="mermaid" id="mermaid-{block_id}">
                    {html.escape(fixed_code)}
                </div>
                <div id="mermaid-error-mermaid-{block_id}"></div>
            </div>
        </div>
        """
        
        return mermaid_div
    
    # Замена блоков Mermaid на сгенерированный HTML
    html_content = re.sub(
        r'```mermaid\s*(.*?)```', 
        mermaid_replacer, 
        md_text, 
        flags=re.DOTALL
    )
    
    # Конвертация оставшегося Markdown в HTML
    html_content = markdown.markdown(
        html_content,
        extensions=[
            'extra', 'codehilite', 'fenced_code', 
            'tables', 'attr_list', 'md_in_html',
            'nl2br', 'sane_lists', 'toc'
        ],
        output_format='html5'
    )
    
    return html_content

def fix_mermaid_syntax(mermaid_code: str) -> str:
    """Исправляет синтаксические ошибки в диаграммах Mermaid"""
    # 1. Удаление лишних символов в начале и конце
    code = mermaid_code.strip()
    
    # 2. Замена HTML-сущностей
    code = html.unescape(code)
    code = code.replace("&quot;", '"')
    code = code.replace("&amp;", "&")
    code = code.replace("&lt;", "<")
    code = code.replace("&gt;", ">")
    
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
    nodes = re.findall(r'\w+\[".*?"\]|\w+\(.*?\)|\w+\{.*?\}', code)
    if len(nodes) > 10:
        code = "graph TD\nA[Слишком сложная диаграмма]\nB[Упростите количество узлов]"
    
    return code
