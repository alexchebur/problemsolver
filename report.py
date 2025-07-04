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
        <!-- Загрузка Mermaid в правильном формате -->
        <script src="https://cdn.jsdelivr.net/npm/mermaid@11.0.1/dist/mermaid.min.js"></script>
        <script>
            // Инициализация Mermaid после полной загрузки страницы
            document.addEventListener('DOMContentLoaded', function() {{
                // Проверка что Mermaid загрузился
                if (typeof mermaid === 'undefined') {{
                    console.error('Mermaid library not loaded!');
                    return;
               }}
            
                // Конфигурация Mermaid
                mermaid.initialize({{
                    startOnLoad: true,
                    theme: 'default',
                    securityLevel: 'loose',
                    fontFamily: 'Arial, sans-serif',
                    errorRenderer: function(error) {{
                        try {{
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
                        }} catch (e) {{
                            console.error('Mermaid error handling failed:', e);
                        }}
                    }}
                }});
            
                // Принудительная перерисовка всех диаграмм
                mermaid.run();
            
                // Логирование для отладки
                console.log('Mermaid initialized successfully. Diagrams:', document.querySelectorAll('.mermaid').length);
            }});
        </script>
        <style>
            /* Стили для диаграмм */
            .diagram-wrapper {{
                margin: 25px 0;
                padding: 15px;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background-color: #f8f9fa;
            }}
        
            .mermaid-container {{
                overflow-x: auto;
                min-height: 150px;
            }}
        
            .mermaid {{
                min-width: 100%;
                display: flex;
                justify-content: center;
                font-family: Arial, sans-serif;
                background-color: white;
                padding: 15px;
                border-radius: 6px;
                white-space: pre-wrap; /* Сохраняем форматирование */
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
            .report {{
                max-width: 1000px;
                margin: 0 auto;
                padding: 20px;
                font-family: Arial, sans-serif;
                line-height: 1.6;
            }}
        
            .report-header {{
                background-color: #1976d2;
                color: white;
                padding: 20px;
                border-radius: 8px 8px 0 0;
                margin-bottom: 20px;
            }}
        
            .content {{
                padding: 20px;
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
    
        <!-- Резервная загрузка Mermaid -->
        <script>
            if (typeof mermaid === 'undefined') {{
                console.warn('Mermaid not loaded, loading now...');
                const script = document.createElement('script');
                script.src = 'https://cdn.jsdelivr.net/npm/mermaid@11.0.1/dist/mermaid.min.js';
                script.onload = function() {{
                    mermaid.initialize({{startOnLoad: true}});
                    mermaid.run();
                }};
                document.head.appendChild(script);
            }}
        </script>
    </body>
    </html>
    """
    
    return html_template.encode('utf-8')

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
    
    # Упрощаем сложные диаграммы
    if len(code.split('\n')) > 35:
        return "graph TD\nA[Слишком сложная диаграмма]\nB[Упростите количество элементов]"
    
    # Исправляем основные синтаксические ошибки
    code = re.sub(r'(\w+)\s*\["([^"]*)"\]', r'\1["\2"]', code)  # Квадратные скобки
    code = re.sub(r'(\w+)\s*\("([^"]*)"\)', r'\1("\2")', code)  # Круглые скобки
    code = re.sub(r'(\w+)\s*\{"([^"]*)"\}', r'\1{"\2"}', code)  # Фигурные скобки
    
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
