# mermaid.py
import re
import requests
import base64
import zlib
import json
from io import BytesIO
from PIL import Image

MERMAID_API_URL = "https://mermaid.ink/svg"

def extract_mermaid_code(text: str) -> list:
    """Извлекает все блоки кода Mermaid из текста"""
    pattern = r'```mermaid(.*?)```'
    matches = re.findall(pattern, text, flags=re.DOTALL)
    return [match.strip() for match in matches]

def process_mermaid_diagrams(content: str) -> dict:
    """Обрабатывает диаграммы Mermaid через публичный API с использованием POST"""
    mermaid_blocks = extract_mermaid_code(content)
    if not mermaid_blocks:
        return {}
    
    images = {}
    for i, code in enumerate(mermaid_blocks):
        try:
            # Сжимаем код для уменьшения размера
            compressed = base64.urlsafe_b64encode(
                zlib.compress(code.encode('utf-8'), level=9)
            ).decode('utf-8')
            
            # Формируем POST-запрос
            response = requests.post(
                MERMAID_API_URL,
                json={
                    'code': code,
                    'compressed': compressed
                },
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code != 200:
                # Если основной запрос не удался, пробуем через сжатие
                response = requests.get(
                    f"{MERMAID_API_URL}?compressed={compressed}",
                    timeout=30
                )
                
            response.raise_for_status()
            
            # Получаем SVG и конвертируем в PNG
            svg_content = response.text
            png_data = self.svg_to_png(svg_content)
            img = Image.open(BytesIO(png_data))
            
            images[f"mermaid_{i}"] = {
                "code": code,
                "image": base64.b64encode(png_data).decode("utf-8"),
                "size": img.size
            }
        except Exception as e:
            print(f"Ошибка при генерации диаграммы Mermaid: {str(e)}")
    
    return images

def svg_to_png(svg_content: str) -> bytes:
    try:
        import cairosvg
        return cairosvg.svg2png(bytestring=svg_content.encode('utf-8'))
    except ImportError:
        # Fallback если библиотека не установлена
        img = Image.new('RGB', (800, 200), color='white')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    except Exception as e:
        print(f"Ошибка конвертации SVG: {str(e)}")
        img = Image.new('RGB', (800, 200), color='white')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
