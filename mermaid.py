# mermaid.py
import re
import os
import asyncio
from pyppeteer import launch
from PIL import Image
from fpdf import FPDF
import tempfile
import logging

def extract_mermaid_code(text: str) -> list:
    """Извлекает все блоки кода Mermaid из текста"""
    pattern = r'```mermaid(.*?)```'
    matches = re.findall(pattern, text, flags=re.DOTALL)
    return [match.strip() for match in matches]

async def render_mermaid_to_image(mermaid_code: str, output_path: str, width: int = 800):
    """Рендерит код Mermaid в PNG изображение с использованием Pyppeteer"""
    browser = await launch(headless=True, args=['--no-sandbox'])
    page = await browser.newPage()
    
    # Генерация HTML с Mermaid
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdn.jsdelivr.net/npm/mermaid@10.6.1/dist/mermaid.min.js"></script>
        <style>
            body {{ margin: 0; padding: 0; }}
            .mermaid-container {{
                width: {width}px;
                margin: 0 auto;
                padding: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="mermaid-container">
            <div class="mermaid">{mermaid_code}</div>
        </div>
        <script>
            mermaid.initialize({{ 
                startOnLoad: true,
                theme: 'default',
                securityLevel: 'loose'
            }});
        </script>
    </body>
    </html>
    """
    
    await page.setContent(html_content)
    await page.waitForSelector('.mermaid', {'timeout': 30000})
    
    # Ждем завершения анимации
    await page.waitForFunction('''() => {
        return document.querySelector('.mermaid')?.getAttribute('data-processed') === 'true';
    }''', timeout=30000)
    
    # Сделаем скриншот только контейнера с диаграммой
    element = await page.querySelector('.mermaid-container')
    await element.screenshot({'path': output_path})
    await browser.close()

def add_mermaid_diagrams_to_pdf(pdf: FPDF, content: str):
    """Добавляет диаграммы Mermaid в PDF документ"""
    mermaid_blocks = extract_mermaid_code(content)
    if not mermaid_blocks:
        return
    
    # Создаем временную директорию для изображений
    with tempfile.TemporaryDirectory() as tmp_dir:
        for i, code in enumerate(mermaid_blocks):
            try:
                img_path = os.path.join(tmp_dir, f"mermaid_{i}.png")
                
                # Рендерим диаграмму в изображение
                asyncio.get_event_loop().run_until_complete(
                    render_mermaid_to_image(code, img_path)
                )
                
                # Добавляем изображение в PDF
                pdf.add_page()
                pdf.set_font("Arial", size=10)
                pdf.cell(0, 10, txt=f"Диаграмма {i+1}", ln=1, align='C')
                
                # Рассчитываем размеры для вписывания в страницу
                with Image.open(img_path) as img:
                    img_width, img_height = img.size
                    max_width = pdf.w - 20
                    max_height = pdf.h - 50
                    
                    # Сохраняем пропорции
                    ratio = min(max_width / img_width, max_height / img_height)
                    new_width = img_width * ratio
                    new_height = img_height * ratio
                    
                    # Позиционируем по центру
                    x = (pdf.w - new_width) / 2
                    y = (pdf.h - new_height) / 2
                    
                    pdf.image(img_path, x=x, y=y, w=new_width)
                
                # Добавляем исходный код диаграммы
                pdf.add_page()
                pdf.set_font("Courier", size=8)
                pdf.multi_cell(0, 5, txt=f"```mermaid\n{code}\n```")
                pdf.ln(5)
                
            except Exception as e:
                logging.error(f"Ошибка при генерации диаграммы Mermaid: {str(e)}")
                pdf.multi_cell(0, 10, txt=f"[Ошибка при генерации диаграммы Mermaid: {str(e)}]")