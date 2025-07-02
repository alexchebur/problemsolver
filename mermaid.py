# mermaid.py
import re
import os
import asyncio
from pyppeteer import launch
from PIL import Image
import tempfile
import logging
import base64

def extract_mermaid_code(text: str) -> list:
    """Извлекает все блоки кода Mermaid из текста"""
    pattern = r'```mermaid(.*?)```'
    matches = re.findall(pattern, text, flags=re.DOTALL)
    return [match.strip() for match in matches]

async def render_mermaid_to_image(mermaid_code: str, output_path: str, width: int = 800):
    """Рендерит код Mermaid в PNG изображение с использованием Pyppeteer"""
    browser = await launch(
        headless=True, 
        args=[
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage'
        ],
        handleSIGINT=False,
        handleSIGTERM=False,
        handleSIGHUP=False
    )
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
                padding: 10px;
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
    
    # Ждем завершения рендеринга
    await page.waitForFunction('''() => {
        return document.querySelector('.mermaid')?.getAttribute('data-processed') === 'true';
    }''', timeout=60000)
    
    # Дополнительная задержка для стабилизации
    await asyncio.sleep(1)
    
    # Получаем размеры контейнера
    dimensions = await page.evaluate('''() => {
        const element = document.querySelector('.mermaid-container');
        if (!element) return null;
        const rect = element.getBoundingClientRect();
        return {
            width: Math.ceil(rect.width),
            height: Math.ceil(rect.height)
        };
    }''')
    
    if not dimensions:
        logging.error("Не удалось получить размеры контейнера Mermaid")
        await browser.close()
        return False
    
    # Устанавливаем размеры viewport
    await page.setViewport({
        'width': dimensions['width'] + 20,  # + отступы
        'height': dimensions['height'] + 20
    })
    
    # Сделаем скриншот только контейнера с диаграммой
    await page.screenshot({
        'path': output_path,
        'clip': {
            'x': 0,
            'y': 0,
            'width': dimensions['width'],
            'height': dimensions['height']
        }
    })
    
    await browser.close()
    return True

def process_mermaid_diagrams(content: str) -> dict:
    """Обрабатывает все диаграммы Mermaid и возвращает словарь с изображениями"""
    mermaid_blocks = extract_mermaid_code(content)
    if not mermaid_blocks:
        return {}
    
    images = {}
    # Создаем временную директорию для изображений
    with tempfile.TemporaryDirectory() as tmp_dir:
        for i, code in enumerate(mermaid_blocks):
            try:
                img_path = os.path.join(tmp_dir, f"mermaid_{i}.png")
                
                # Создаем новый цикл событий для текущего потока
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Рендерим диаграмму в изображение
                success = loop.run_until_complete(
                    render_mermaid_to_image(code, img_path)
                )
                loop.close()
                
                if not success or not os.path.exists(img_path):
                    logging.error(f"Не удалось создать изображение для диаграммы {i}")
                    continue
                
                # Конвертируем в base64
                with open(img_path, "rb") as img_file:
                    img_data = img_file.read()
                    images[f"mermaid_{i}"] = {
                        "code": code,
                        "image": base64.b64encode(img_data).decode("utf-8"),
                        "size": Image.open(img_path).size
                    }
                
            except Exception as e:
                logging.error(f"Ошибка при генерации диаграммы Mermaid: {str(e)}")
    
    return images
