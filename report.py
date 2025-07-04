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
        <script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs"></script>
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
        
            // Перерисовка диаграмм при изменении размера окна
            window.addEventListener('resize', function() {{
                mermaid.run({{ querySelector: '.mermaid' }});
            }});
        </script>
        <style>
            /* Стили для диаграмм */
            .diagram-wrapper {{
                margin: 20px 0;
                padding: 10px;
                border: 1px solid #eee;
                border-radius: 5px;
                background-color: #f9f9f9;
            }}
        
            .mermaid-container {{
                overflow-x: auto;
            }}
        
            .mermaid-error-container {{
                color: #d32f2f;
                background-color: #ffebee;
                padding: 10px;
                border-radius: 4px;
                margin-top: 10px;
                font-family: monospace;
                white-space: pre-wrap;
            }}
        
            /* Остальные стили остаются без изменений */
            .report-header {{ /* ... */ }}
            .content {{ /* ... */ }}
            .footer {{ /* ... */ }}
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
        placeholder = f"%%%MERMAID_BLOCK_{block_id}%%%"
        mermaid_blocks[placeholder] = fixed_code
        block_id += 1
        return f"\n\n{placeholder}\n\n"

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
        # Извлекаем цифровой ID из плейсхолдера
        mermaid_id = placeholder.split('_')[-1].strip('%%%')
        
        mermaid_html = f"""
<div class="diagram-wrapper">
    <div class="mermaid-container">
        <div class="mermaid" id="mermaid-{mermaid_id}">
            {html.escape(fixed_code)}
        </div>
        <div id="mermaid-error-{mermaid_id}" class="mermaid-error-container"></div>
    </div>
</div>
        """
        html_content = html_content.replace(placeholder, mermaid_html)
    
    # Удаляем возможные обертки параграфов вокруг диаграмм
    html_content = re.sub(
        r'<p>\s*(<div class="diagram-wrapper".*?</div>)\s*</p>',
        r'\1',
        html_content,
        flags=re.DOTALL
    )
    
    # Удаляем пустые параграфы, которые могли образоваться
    html_content = re.sub(r'<p>\s*</p>', '', html_content)
    
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
    code = code.replace("&lt;", "<")
    code = code.replace("&gt;", ">")
    
    # Упрощаем сложные диаграммы
    if len(code.split('\n')) > 15:
        return "graph TD\nA[Слишком сложная диаграмма]\nB[Упростите количество узлов]"
    
    # Добавляем базовую ориентацию если отсутствует
    if not re.search(r'^\s*(graph|flowchart)\s+[A-Z]{2}', code):
        if "graph" in code or "flowchart" in code:
            code = re.sub(r'(graph|flowchart)\s+', r'\1 TD\n', code)
        else:
            code = "graph TD\n" + code
    
    return code
