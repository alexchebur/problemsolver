# mermaid.py (упрощенная версия)
import re
import requests
import base64
from io import BytesIO
from PIL import Image

MERMAID_API_URL = "https://mermaid.ink/img/"

def process_mermaid_diagrams(content: str) -> dict:
    """Обрабатывает диаграммы Mermaid через публичный API"""
    mermaid_blocks = extract_mermaid_code(content)
    if not mermaid_blocks:
        return {}
    
    images = {}
    for i, code in enumerate(mermaid_blocks):
        try:
            # Кодируем диаграмму в base64 URL
            encoded = base64.urlsafe_b64encode(code.encode()).decode()
            response = requests.post(
                f"{MERMAID_API_URL}{encoded}",
                headers={'Content-Type': 'text/plain'},
                timeout=30
            )
            response.raise_for_status()
            
            # Получаем изображение
            img_data = response.content
            img = Image.open(BytesIO(img_data))
            
            images[f"mermaid_{i}"] = {
                "code": code,
                "image": base64.b64encode(img_data).decode("utf-8"),
                "size": img.size
            }
        except Exception as e:
            print(f"Ошибка при генерации диаграммы Mermaid: {str(e)}")
    
    return images

def extract_mermaid_code(text: str) -> list:
    """Извлекает все блоки кода Mermaid из текста"""
    pattern = r'```mermaid(.*?)```'
    matches = re.findall(pattern, text, flags=re.DOTALL)
    return [match.strip() for match in matches]
