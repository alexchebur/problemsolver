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
        <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&family=Fira+Code&display=swap" rel="stylesheet">
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
        
            /* Базовые стили */
            body {
                font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                background-color: #f8f9fa;
                margin: 0;
                padding: 0;
            }
    
            .report {{
                max-width: 900px;
                margin: 0 auto;
                padding: 30px;
                background-color: white;
                box-shadow: 0 0 30px rgba(0, 0, 0, 0.05);
                border-radius: 10px;
            }}

            /* Заголовки */
            h1 {{
                color: #2c3e50;
                font-weight: 700;
                border-bottom: 2px solid #3498db;
                padding-bottom: 10px;
                margin-top: 30px;
                margin-bottom: 20px;
            }}

            h2 {{
                color: #2980b9;
                font-weight: 600;
                margin-top: 25px;
                margin-bottom: 15px;
                padding-bottom: 8px;
                border-bottom: 1px solid #ecf0f1;
            }}

            h3 {{
                color: #3498db;
                font-weight: 600;
                margin-top: 20px;
                margin-bottom: 12px;
            }}

            h4, h5, h6 {{
                color: #3498db;
                font-weight: 500;
                margin-top: 18px;
                margin-bottom: 10px;
            }}

            /* Текст и абзацы */
            p {{
                margin-bottom: 15px;
                text-align: justify;
            }}

            strong {{
                color: #2c3e50;
                font-weight: 600;
            }}

            em {{
                color: #7f8c8d;
                font-style: italic;
            }}

            /* Списки */
            ul, ol {{
                margin-bottom: 20px;
                padding-left: 25px;
            }}

            li {{
                margin-bottom: 8px;
                position: relative;
            }}

            ul li::before {{
                content: "•";
                color: #3498db;
                font-weight: bold;
                display: inline-block;
                width: 1em;
                margin-left: -1em;
            }}

            ol {{
                counter-reset: list-counter;
            }}

            ol li {{
                counter-increment: list-counter;
            }}

            ol li::before {{
                content: counter(list-counter) ".";
                color: #3498db;
                font-weight: bold;
                display: inline-block;
                width: 1.5em;
                margin-left: -1.5em;
            }}

            /* Ссылки */
            a {{
                color: #3498db;
                text-decoration: none;
                transition: color 0.3s;
                border-bottom: 1px dotted rgba(52, 152, 219, 0.3);
            }}

            a:hover {{
                color: #2980b9;
                border-bottom: 1px solid #2980b9;
            }}

            /* Цитаты */
            blockquote {{
                border-left: 4px solid #3498db;
                background-color: #f8fafc;
                padding: 15px 20px;
                margin: 20px 0;
                border-radius: 0 8px 8px 0;
                color: #555;
            }}

            blockquote p {{
                margin-bottom: 0;
            }}

            /* Код */
            pre {{
                background-color: #2c3e50;
                color: #ecf0f1;
                padding: 15px;
                border-radius: 6px;
                overflow-x: auto;
                font-family: 'Fira Code', 'Consolas', monospace;
                line-height: 1.5;
                margin: 20px 0;
            }}

            code {{
                background-color: #f1f8ff;
                color: #d63200;
                padding: 2px 6px;
                border-radius: 4px;
                font-family: 'Fira Code', 'Consolas', monospace;
                font-size: 0.95em;
            }}

            /* Таблицы */
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
                box-shadow: 0 0 10px rgba(0, 0, 0, 0.03);
            }}

            th {{
                background-color: #3498db;
                color: white;
                font-weight: 600;
                text-align: left;
                padding: 12px 15px;
            }}

            td {{
                padding: 10px 15px;
                border-bottom: 1px solid #ecf0f1;
            }}

            tr:nth-child(even) {{
                background-color: #f8fafc;
            }}

            tr:hover {{
                background-color: #f0f7ff;
            }}

            /* Изображения */
            img {{
                max-width: 100%;
                height: auto;
                border-radius: 6px;
                margin: 15px 0;
                box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08);
            }}

            /* Разделители */
            hr {{
                border: 0;
                height: 1px;
                background: linear-gradient(to right, transparent, #3498db, transparent);
                margin: 30px 0;
            }}

            /* Подсветка важного */
            .highlight {{
                background: linear-gradient(120deg, rgba(52, 152, 219, 0.15), rgba(52, 152, 219, 0.05));
                padding: 15px 20px;
                border-radius: 8px;
                border-left: 3px solid #3498db;
                margin: 20px 0;
            }}

            /* Футер */
            .footer {{
                text-align: center;
                margin-top: 40px;
                padding-top: 20px;
                color: #7f8c8d;
                font-size: 0.9em;
                border-top: 1px solid #ecf0f1;
            }}

            /* Адаптивность */
            @media (max-width: 768px) {
                .report {{
                    padding: 20px;
                    border-radius: 0;
                    box-shadow: none;
                }}
        
                body {{
                    background-color: white;
                }}
        
                h1 {{
                    font-size: 1.8em;
                }}
            }
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
