# report.py
import re
import html
from datetime import datetime
import markdown
from markdown.extensions.tables import TableExtension
from markdown.extensions.fenced_code import FencedCodeExtension
from markdown.extensions.codehilite import CodeHiliteExtension
from markdown.extensions.attr_list import AttrListExtension
import base64

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
                }},
                flowchart: {{ 
                    useMaxWidth: true,
                    htmlLabels: true 
                }}
            }});
        </script>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                max-width: 1000px;
                margin: auto;
                padding: 20px;
                background-color: #f8f9fa;
            }}
            .report-header {{
                text-align: center;
                margin-bottom: 30px;
                border-bottom: 2px solid #3498db;
                padding-bottom: 10px;
            }}
            .content {{
                background-color: white;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            pre {{
                background-color: #f5f5f5;
                padding: 15px;
                border-radius: 5px;
                overflow-x: auto;
            }}
            code {{
                background-color: #f5f5f5;
                padding: 2px 4px;
                border-radius: 3px;
            }}
            .mermaid-container {{
                text-align: center;
                margin: 30px 0;
                padding: 20px;
                background-color: white;
                border-radius: 8px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.05);
                overflow: auto;
            }}
            .mermaid-error {{
                color: #721c24;
                background-color: #f8d7da;
                border: 1px solid #f5c6cb;
                border-radius: 5px;
                padding: 15px;
                margin: 15px 0;
                font-family: monospace;
                white-space: pre-wrap;
            }}
            .footer {{
                text-align: center;
                margin-top: 30px;
                font-size: 0.9em;
                color: #7f8c8d;
            }}
            h1, h2, h3, h4, h5, h6 {{
                color: #2c3e50;
                margin-top: 1.5em;
                margin-bottom: 0.5em;
            }}
            h1 {{ font-size: 2.2em; }}
            h2 {{ font-size: 1.8em; }}
            h3 {{ font-size: 1.5em; }}
            h4 {{ font-size: 1.3em; }}
            h5 {{ font-size: 1.1em; }}
            h6 {{ font-size: 1em; }}
            
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 25px 0;
                font-size: 0.9em;
                box-shadow: 0 0 20px rgba(0, 0, 0, 0.05);
            }}
            table thead tr {{
                background-color: #3498db;
                color: #ffffff;
                text-align: left;
            }}
            table th,
            table td {{
                padding: 12px 15px;
                border: 1px solid #dddddd;
            }}
            table tbody tr {{
                border-bottom: 1px solid #dddddd;
            }}
            table tbody tr:nth-of-type(even) {{
                background-color: #f3f3f3;
            }}
            table tbody tr:last-of-type {{
                border-bottom: 2px solid #3498db;
            }}
            blockquote {{
                background: #f9f9f9;
                border-left: 10px solid #ccc;
                margin: 1.5em 10px;
                padding: 0.5em 10px;
                quotes: "\\201C""\\201D""\\2018""\\2019";
            }}
            blockquote:before {{
                color: #ccc;
                content: open-quote;
                font-size: 4em;
                line-height: 0.1em;
                margin-right: 0.25em;
                vertical-align: -0.4em;
            }}
            blockquote p {{
                display: inline;
            }}
            img {{
                max-width: 100%;
                height: auto;
                display: block;
                margin: 20px auto;
            }}
            ul, ol {{
                padding-left: 30px;
                margin: 15px 0;
            }}
            li {{
                margin: 8px 0;
            }}
            hr {{
                border: 0;
                height: 1px;
                background: #3498db;
                background-image: linear-gradient(to right, #f8f9fa, #3498db, #f8f9fa);
                margin: 30px 0;
            }}
            .diagram-wrapper {{
                margin: 30px 0;
                text-align: center;
            }}
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

def is_valid_mermaid(code: str) -> bool:
    """Проверяет базовую валидность кода Mermaid"""
    # Должен содержать хотя бы одну стрелку и один узел
    has_arrow = re.search(r'-->|--|==>|~~>', code)
    has_node = re.search(r'\[".+"\]|\(".+"\)|{".+"}', code)
    return bool(has_arrow and has_node)

def convert_md_to_html(md_text: str) -> str:
    """Конвертирует Markdown в HTML с сохранением блоков Mermaid"""
    # Обработка блоков Mermaid
    mermaid_blocks = []
    placeholder_pattern = "@@@MERMAID_BLOCK_{}@@@"
    
    def mermaid_replacer(match):
        mermaid_code = match.group(1).strip()
        # Удаляем все HTML-теги
        mermaid_code = re.sub(r'<[^>]+>', '', mermaid_code)
        # Удаляем лишние пробелы
        mermaid_code = re.sub(r'\s+', ' ', mermaid_code)
        # Обрезаем слишком длинные диаграммы
        if len(mermaid_code) > 500:
            mermaid_code = mermaid_code[:500] + "..."
        mermaid_blocks.append(mermaid_code)
        # Возвращаем плейсхолдер с переносами
        return f"\n\n{placeholder_pattern.format(len(mermaid_blocks) - 1)}\n\n"
    
    # Временная замена блоков Mermaid
    md_text = re.sub(
        r'```mermaid\s*(.*?)```', 
        mermaid_replacer, 
        md_text, 
        flags=re.DOTALL
    )
    
    # Конвертация Markdown в HTML
    html_content = markdown.markdown(
        md_text,
        extensions=[
            'extra', 'codehilite', 'fenced_code', 
            'tables', 'attr_list', 'md_in_html',
            'nl2br', 'sane_lists', 'toc'
        ],
        output_format='html5'
    )
    
    # Восстановление блоков Mermaid
    for i, block in enumerate(mermaid_blocks):
        try:
            fixed_block = fix_mermaid_syntax(block)
            
            # Проверка на пустую диаграмму
            if not fixed_block.strip() or len(fixed_block.strip()) < 10:
                raise ValueError("Диаграмма слишком короткая или пустая")
                
            mermaid_div = f"""
            <div class="diagram-wrapper">
                <div class="mermaid-container">
                    <div class="mermaid" id="mermaid-{i}">
                        {html.escape(fixed_block)}
                    </div>
                    <div id="mermaid-error-mermaid-{i}"></div>
                </div>
            </div>
            """
        except Exception as e:
            mermaid_div = f"""
            <div class="mermaid-error">
                <strong>Ошибка обработки диаграммы:</strong> {str(e)}
                <pre>{html.escape(block)}</pre>
            </div>
            """
        
        html_content = html_content.replace(
            placeholder_pattern.format(i), 
            mermaid_div
        )

    if not is_valid_mermaid(fixed_block):
        raise ValueError("Диаграмма не соответствует базовым требованиям синтаксиса")
    
    return html_content
    
def fix_mermaid_syntax(mermaid_code: str) -> str:
    """Исправляет синтаксические ошибки в диаграммах Mermaid"""
    # 1. Удаление лишних символов в начале и конце
    code = mermaid_code.strip()
    
    # 2. Замена HTML-сущностей на нормальные символы
    code = html.unescape(code)
    
    # 3. Удаление некорректных символов в идентификаторах
    code = re.sub(r'[^a-zA-Z0-9\s_\-\[\]{}();"\'<>=]', '', code)
    
    # 4. Замена некорректных кавычек
    code = re.sub(r'&quot;', '"', code)
    
    # 5. Завершение незаконченных диаграмм
    if not re.search(r'\]\s*$', code):
        # Если диаграмма обрывается, удаляем последнюю незавершенную строку
        lines = code.split('\n')
        if lines:
            last_line = lines[-1]
            if not re.search(r'\]\s*$', last_line) and not re.search(r'[;}]$', last_line):
                code = '\n'.join(lines[:-1])
    
    # 6. Проверка и завершение узлов
    def complete_nodes(match):
        node_text = match.group(1)
        # Удаляем лишние символы и завершаем узел
        node_text = re.sub(r'[^a-zA-Z0-9\s_\-]', ' ', node_text)
        return f'["{node_text.strip()}"]'
    
    code = re.sub(r'\["([^"]*)$', complete_nodes, code)
    
    # 7. Удаление лишних символов в конце
    code = re.sub(r'[^\w\s]\s*$', '', code)
    
    # 8. Добавление ориентации по умолчанию
    if not re.search(r'^\s*(graph|flowchart)\s+[A-Z]{2}', code):
        if "graph" in code or "flowchart" in code:
            code = re.sub(r'(graph|flowchart)\s+', r'\1 TD\n', code)
        else:
            code = "graph TD\n" + code
    
    # 9. Упрощение длинных текстов
    def simplify_text(match):
        text = match.group(1)
        if len(text) > 100:
            return '["Слишком длинный текст"]'
        return f'["{text}"]'
    
    code = re.sub(r'\["([^"]+)"\]', simplify_text, code)
    
    # 10. Базовая проверка синтаксиса
    if not re.search(r'\w+\s*-->', code) or not re.search(r'\[".+"\]', code):
        return "graph TD\nA[Диаграмма содержит ошибки]\nB[Проверьте синтаксис]"
    
    return code
