import time
import random
import logging
from typing import List, Dict
from duckduckgo_search import DDGS

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebSearcher:
    def __init__(self):
        # Простая инициализация без параметров
        self.ddgs = None
        self._init_ddgs()
        
    def _init_ddgs(self):
        """Инициализация экземпляра DDGS"""
        try:
            # Простая инициализация как в рабочем скрипте
            self.ddgs = DDGS()
            logger.info("Инициализирован экземпляр DDGS")
        except Exception as e:
            logger.error(f"Ошибка инициализации DDGS: {str(e)}")
            self.ddgs = None

    def perform_search(self, query: str, max_results: int = 3) -> List[Dict]:
        """Основной метод поиска как в рабочем скрипте"""
        try:
            logger.info(f"Ищу: {query}")
            
            # ТОЧНО ТАКОЙ ЖЕ ВЫЗОВ КАК В РАБОЧЕМ СКРИПТЕ
            results = self.ddgs.text(query, max_results=max_results, backend="auto")
            
            logger.info(f"Успешно найдено для: {query}")
            
            # Форматируем результаты в простую структуру
            formatted_results = []
            for r in results:
                formatted_results.append({
                    'title': r.get('title', 'Без названия'),
                    'url': r.get('href', ''),
                    'snippet': r.get('body', '')[:500]  # Ограничиваем длину
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Ошибка поиска для '{query}': {str(e)}")
            # Переинициализация после ошибки
            self._init_ddgs()
            return [{
                "error": str(e),
                "message": "Не удалось выполнить поиск"
            }]
        finally:
            # Точная задержка как в рабочем скрипте
            delay = random.uniform(3.0, 6.0)
            logger.info(f"Задержка {delay:.2f} сек")
            time.sleep(delay)

    def batch_search(self, queries: List[str], max_results: int = 3) -> Dict[str, List[Dict]]:
        """Пакетный поиск как в рабочем скрипте"""
        results = {}
        for query in queries:
            results[query] = self.perform_search(query, max_results)
        return results
