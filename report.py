# report.py
import re
import base64
from datetime import datetime
from mermaid import extract_mermaid_code

def create_html_report(content: str, title: str = "Отчет") -> bytes:
    """Создает HTML отчет с поддержкой Mermaid.js"""
    # Извлекаем все диаграммы Mermaid
    mermaid_blocks = extract_mermaid_code(content)
    
    # Генерируем HTML
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{title}</title>
        <script src="https://cdn.jsdelivr.net/npm/mermaid@10.6.1/dist/mermaid.min.js"></script>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                max-width: 800px;
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
            }}
            .footer {{
                text-align: center;
                margin-top: 30px;
                font-size: 0.9em;
                color: #7f8c8d;
            }}
            h1, h2, h3 {{
                color: #2c3e50;
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
        
        <script>
            // Инициализация Mermaid
            mermaid.initialize({{
                startOnLoad: true,
                theme: 'default',
                securityLevel: 'loose'
            }});
            
            // Перерисовка диаграмм при изменении размера окна
            window.addEventListener('resize', function() {{
                mermaid.init(undefined, '.mermaid');
            }});
        </script>
        
        <div class="footer">
            Отчет сгенерирован с помощью Troubleshooter
        </div>
    </body>
    </html>
    """
    
    return html_template.encode('utf-8')

def convert_md_to_html(md_text: str) -> str:
    """Конвертирует Markdown в HTML с сохранением блоков Mermaid"""
    # Обрабатываем блоки Mermaid
    md_text = re.sub(
        r'```mermaid(.*?)```', 
        r'<div class="mermaid-container"><div class="mermaid">\1</div></div>', 
        md_text, 
        flags=re.DOTALL
    )
    
    # Конвертируем базовый Markdown в HTML
    replacements = [
        (r'### (.*)', r'<h3>\1</h3>'),
        (r'## (.*)', r'<h2>\1</h2>'),
        (r'# (.*)', r'<h1>\1</h1>'),
        (r'\*\*(.*?)\*\*', r'<strong>\1</strong>'),
        (r'\*(.*?)\*', r'<em>\1</em>'),
        (r'`(.*?)`', r'<code>\1</code>'),
        (r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>'),
        (r'\n\s*\n', r'</p><p>'),
        (r'!\[(.*?)\]\((.*?)\)', r'<img src="\2" alt="\1" style="max-width:100%;">')
    ]
    
    for pattern, repl in replacements:
        md_text = re.sub(pattern, repl, md_text)
    
    return f'<p>{md_text}</p>'
