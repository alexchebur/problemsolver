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
            // Инициализация Mermaid после загрузки страницы
            document.addEventListener('DOMContentLoaded', function() {{
                mermaid.initialize({{
                    startOnLoad: true,
                    theme: 'default',
                    securityLevel: 'loose',
                    errorRenderer: function(error) {{
                        const container = error.element.closest('.mermaid-container')
                                            .querySelector('.mermaid-error-container');
                        if (container) {{
                            container.innerHTML = `
                                <div class="mermaid-error">
                                    <strong>Ошибка в диаграмме:</strong> ${{error.message}}
                                    <pre>${{error.str}}</pre>
                                </div>
                            `;
                        }}
                    }}
                }});
            
                // Принудительная перерисовка при изменении размера
                window.addEventListener('resize', function() {{
                    mermaid.run({{ 
                        querySelector: '.mermaid',
                        suppressErrors: true 
                    }});
                }});
            }});
        </script>
        <style>
            /* Стили для диаграмм */
            .diagram-wrapper {{
                margin: 20px 0;
                padding: 10px;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background-color: #f8f9fa;
                overflow: hidden;
            }}
        
            .mermaid-container {{
                overflow-x: auto;
                min-height: 100px;
            }}
        
            .mermaid {{
                min-width: 100%;
                display: flex;
                justify-content: center;
            }}
        
            .mermaid-error-container {{
                color: #d32f2f;
                background-color: #ffebee;
                padding: 12px;
                border-radius: 6px;
                margin-top: 10px;
                font-family: 'Courier New', monospace;
                white-space: pre-wrap;
                font-size: 14px;
            }}
        
            /* Остальные стили */
            .report-header {{ 
                background-color: #1976d2;
                color: white;
                padding: 20px;
                border-radius: 8px 8px 0 0;
            }}
        
            .content {{ 
                padding: 20px;
                line-height: 1.6;
            }}
        
            .footer {{ 
                text-align: center;
                padding: 15px;
                color: #757575;
                font-size: 14px;
                border-top: 1px solid #e0e0e0;
                margin-top: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="report">
            <div class="report-header">
                <h1>{title}</h1>
                <p>Сгенерировано: {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>
            </div>
        
            <div class="content">
                {convert_md_to_html(content)}
            </div>
        
            <div class="footer">
                Отчет сгенерирован автоматически
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_template.encode('utf-8')

def convert_md_to_html(md_text: str) -> str:
    """Конвертирует Markdown в HTML с сохранением блоков Mermaid"""
    # Сначала обработаем все блоки Mermaid
    def process_mermaid(match):
        mermaid_code = match.group(1).strip()
        fixed_code = fix_mermaid_syntax(mermaid_code)
        
        # Генерируем безопасный HTML для диаграммы
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
    
    # Удаляем оборачивание в параграфы вокруг диаграмм
    html_content = re.sub(
        r'<p>\s*(<div class="diagram-wrapper".*?</div>)\s*</p>',
        r'\1',
        html_content,
        flags=re.DOTALL
    )
    
    # Убираем лишние пробелы и переносы
    html_content = re.sub(r'>\s+<', '><', html_content)
    
    return html_content

def fix_mermaid_syntax(mermaid_code: str) -> str:
    """Исправляет синтаксические ошибки в диаграммах Mermaid"""
    # Удаляем все HTML-теги
    code = re.sub(r'<[^>]+>', '', mermaid_code)
    code = code.strip()
    
    # Декодируем HTML-сущности
    code = html.unescape(code)
    code = code.replace("&quot;", '"')
    code = code.replace("&amp;", "&")
    code = code.replace("&lt;", "<")
    code = code.replace("&gt;", ">")
    
    # Убираем лишние пробелы
    code = re.sub(r'\s+', ' ', code)
    
    # Добавляем базовую ориентацию если отсутствует
    if not re.search(r'^\s*(graph|flowchart)\s+[A-Z]{2}', code, re.IGNORECASE):
        if "graph" in code.lower() or "flowchart" in code.lower():
            code = re.sub(r'(graph|flowchart)\s+', r'\1 TD\n', code, flags=re.IGNORECASE)
        else:
            code = "graph TD\n" + code
    
    # Упрощаем слишком сложные диаграммы
    node_count = len(re.findall(r'\w+\[".*?"\]|\w+\(.*?\)|\w+\{.*?\}|\w+-->\w+', code))
    if node_count > 25:
        return "graph TD\nA[Слишком сложная диаграмма]\nB[Упростите количество элементов]"
    
    return code
