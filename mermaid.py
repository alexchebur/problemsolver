# mermaid.py
import re

def extract_mermaid_code(text: str) -> list:
    """Извлекает все блоки кода Mermaid из текста"""
    pattern = r'```mermaid(.*?)```'
    matches = re.findall(pattern, text, flags=re.DOTALL)
    return [match.strip() for match in matches]
