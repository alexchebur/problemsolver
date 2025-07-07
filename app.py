import streamlit as st
import google.generativeai as genai
import time
import requests
import traceback
import random
from docx import Document
from io import BytesIO
from fpdf import FPDF
import base64
import os
from datetime import datetime
from bs4 import BeautifulSoup
from websearch import WebSearcher
from typing import List, Tuple
import re
from report import create_html_report
from prompts import (
    PROMPT_FORMULATE_PROBLEM_AND_QUERIES,
    PROMPT_APPLY_COGNITIVE_METHOD,
    PROMPT_GENERATE_REFINEMENT_QUERIES,
    PROMPT_GENERATE_FINAL_CONCLUSIONS
)
import io
import pandas as pd
from pptx import Presentation
import PyPDF2
from openpyxl import load_workbook

# Настройка API
api_key = st.secrets['GEMINI_API_KEY']
if not api_key:
    st.warning("Пожалуйста, введите API-ключ")
    st.stop()

genai.configure(
    api_key=api_key,
    transport='rest',
    client_options={
        'api_endpoint': 'generativelanguage.googleapis.com/'
    }
)

# Создаем экземпляр поисковика
searcher = WebSearcher()

# Глобальные переменные состояния
if 'current_doc_text' not in st.session_state:
    st.session_state.current_doc_text = ""
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'report_content' not in st.session_state:
    st.session_state.report_content = None
if 'problem_formulation' not in st.session_state:
    st.session_state.problem_formulation = ""
if 'generated_queries' not in st.session_state:
    st.session_state.generated_queries = []
if 'search_results' not in st.session_state:
    st.session_state.search_results = ""
if 'internal_dialog' not in st.session_state:
    st.session_state.internal_dialog = ""

# Модель
model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-06-17')

# Когнитивные методики
CORE_METHODS = [
    "First Principles Thinking",
    "Pareto Principle (80/20 Rule)",
    "Occam's Razor",
    "System 1 vs System 2 Thinking",
    "Second-Order Thinking"
]

ADDITIONAL_METHODS = [
    "Inversion (thinking backwards)",
    "Opportunity Cost",
    "Margin of Diminishing Returns",
    "Hanlon's Razor",
    "Confirmation Bias",
    "Availability Heuristic",
    "Parkinson's Law",
    "Loss Aversion",
    "Switching Costs",
    "Circle of Competence",
    "Regret Minimization",
    "Leverage Points",
    "Lindy Effect",
    "Game Theory",
    "Antifragility",
    "Теории Решения Изобретательских задач"
]

# Конфигурация контекста для разных этапов
CONTEXT_CONFIG = {
    'problem_formulation': {
        'doc_text': True,
        'original_query': True,
        'search_results': False,
        'method_results': False
    },
    'cognitive_method': {
        'doc_text': True,
        'original_query': True,
        'search_results': True,
        'method_results': False
    },
    'refinement_queries': {
        'doc_text': False,
        'original_query': True,
        'search_results': True,
        'method_results': True
    },
    'final_conclusions': {
        'doc_text': False,
        'original_query': True,
        'search_results': True,
        'method_results': True
    }
}

class WordToMarkdown:
    """Converter for Word documents to Markdown"""
    
    def convert(self, file_content):
        """Convert Word document content to Markdown"""
        doc = Document(io.BytesIO(file_content))
        markdown_content = []
        
        for paragraph in doc.paragraphs:
            text = paragraph.text.strip()
            if not text:
                markdown_content.append("")
                continue
            
            style_name = paragraph.style.name.lower()
            if 'heading' in style_name:
                if 'heading 1' in style_name:
                    markdown_content.append(f"# {text}")
                elif 'heading 2' in style_name:
                    markdown_content.append(f"## {text}")
                elif 'heading 3' in style_name:
                    markdown_content.append(f"### {text}")
                elif 'heading 4' in style_name:
                    markdown_content.append(f"#### {text}")
                elif 'heading 5' in style_name:
                    markdown_content.append(f"##### {text}")
                else:
                    markdown_content.append(f"###### {text}")
            else:
                formatted_text = self._format_text_runs(paragraph)
                markdown_content.append(formatted_text)
        
        for table in doc.tables:
            table_md = self._convert_table(table)
            markdown_content.append(table_md)
        
        return "\n\n".join(markdown_content)
    
    def _format_text_runs(self, paragraph):
        formatted_text = ""
        for run in paragraph.runs:
            text = run.text
            if run.bold and run.italic:
                text = f"***{text}***"
            elif run.bold:
                text = f"**{text}**"
            elif run.italic:
                text = f"*{text}*"
            formatted_text += text
        return formatted_text
    
    def _convert_table(self, table):
        markdown_table = []
        table_data = []
        for row in table.rows:
            row_data = []
            for cell in row.cells:
                cell_text = cell.text.strip().replace('\n', ' ')
                row_data.append(cell_text)
            table_data.append(row_data)
        
        if not table_data:
            return ""
        
        header_row = "| " + " | ".join(table_data[0]) + " |"
        markdown_table.append(header_row)
        separator = "| " + " | ".join(["---"] * len(table_data[0])) + " |"
        markdown_table.append(separator)
        
        for row in table_data[1:]:
            data_row = "| " + " | ".join(row) + " |"
            markdown_table.append(data_row)
        
        return "\n".join(markdown_table)

class ExcelToMarkdown:
    """Converter for Excel files to Markdown"""
    
    def convert(self, file_content):
        excel_io = io.BytesIO(file_content)
        workbook = load_workbook(excel_io, data_only=True)
        markdown_content = []
        
        for sheet_name in workbook.sheetnames:
            worksheet = workbook[sheet_name]
            markdown_content.append(f"# {sheet_name}")
            markdown_content.append("")
            
            data = []
            for row in worksheet.iter_rows(values_only=True):
                if any(cell is not None and str(cell).strip() for cell in row):
                    clean_row = []
                    for cell in row:
                        if cell is None:
                            clean_row.append("")
                        else:
                            cell_value = str(cell).strip()
                            clean_row.append(cell_value)
                    data.append(clean_row)
            
            if data:
                table_md = self._create_markdown_table(data)
                markdown_content.append(table_md)
            else:
                markdown_content.append("*No data in this worksheet*")
            
            markdown_content.append("")
        
        return "\n".join(markdown_content)
    
    def _create_markdown_table(self, data):
        if not data:
            return ""
        
        max_cols = max(len(row) for row in data)
        padded_data = []
        for row in data:
            padded_row = row + [""] * (max_cols - len(row))
            padded_data.append(padded_row)
        
        markdown_table = []
        
        if padded_data:
            header_row = "| " + " | ".join(padded_data[0]) + " |"
            markdown_table.append(header_row)
            separator = "| " + " | ".join(["---"] * max_cols) + " |"
            markdown_table.append(separator)
            
            for row in padded_data[1:]:
                data_row = "| " + " | ".join(row) + " |"
                markdown_table.append(data_row)
        
        return "\n".join(markdown_table)

class PowerPointToMarkdown:
    """Converter for PowerPoint presentations to Markdown"""
    
    def convert(self, file_content):
        ppt_io = io.BytesIO(file_content)
        presentation = Presentation(ppt_io)
        markdown_content = ["# PowerPoint Presentation", ""]
        
        for slide_num, slide in enumerate(presentation.slides, 1):
            markdown_content.append(f"## Slide {slide_num}")
            markdown_content.append("")
            
            slide_text = []
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    text_content = shape.text.strip()
                    if not slide_text and self._is_likely_title(shape):
                        slide_text.append(f"### {text_content}")
                    else:
                        paragraphs = text_content.split('\n')
                        for para in paragraphs:
                            para = para.strip()
                            if para:
                                if para.startswith(('•', '-', '*')) or para[0:2] in ['1.', '2.', '3.', '4.', '5.']:
                                    slide_text.append(f"- {para.lstrip('•-* ')}")
                                else:
                                    slide_text.append(para)
                
                elif hasattr(shape, "table"):
                    table_md = self._convert_ppt_table(shape.table)
                    if table_md:
                        slide_text.append(table_md)
            
            if slide_text:
                markdown_content.extend(slide_text)
            else:
                markdown_content.append("*No text content in this slide*")
            
            markdown_content.append("")
        
        return "\n".join(markdown_content)
    
    def _is_likely_title(self, shape):
        try:
            if hasattr(shape, 'top') and shape.top < 1000000:
                return True
        except:
            pass
        return False
    
    def _convert_ppt_table(self, table):
        markdown_table = []
        table_data = []
        
        for row in table.rows:
            row_data = []
            for cell in row.cells:
                cell_text = cell.text.strip().replace('\n', ' ')
                row_data.append(cell_text)
            table_data.append(row_data)
        
        if not table_data:
            return ""
        
        if table_data:
            header_row = "| " + " | ".join(table_data[0]) + " |"
            markdown_table.append(header_row)
            separator = "| " + " | ".join(["---"] * len(table_data[0])) + " |"
            markdown_table.append(separator)
            
            for row in table_data[1:]:
                data_row = "| " + " | ".join(row) + " |"
                markdown_table.append(data_row)
        
        return "\n".join(markdown_table)

class PDFToMarkdown:
    """Converter for PDF documents to Markdown"""
    
    def convert(self, file_content):
        pdf_io = io.BytesIO(file_content)
        pdf_reader = PyPDF2.PdfReader(pdf_io)
        markdown_content = ["# PDF Document", ""]
        
        for page_num, page in enumerate(pdf_reader.pages, 1):
            markdown_content.append(f"## Page {page_num}")
            markdown_content.append("")
            
            try:
                page_text = page.extract_text()
                if page_text.strip():
                    cleaned_text = self._clean_pdf_text(page_text)
                    paragraphs = cleaned_text.split('\n\n')
                    
                    for paragraph in paragraphs:
                        paragraph = paragraph.strip()
                        if paragraph:
                            if self._is_likely_heading(paragraph):
                                markdown_content.append(f"### {paragraph}")
                            else:
                                markdown_content.append(paragraph)
                            markdown_content.append("")
                else:
                    markdown_content.append("*No text content found on this page*")
                    markdown_content.append("")
                    
            except Exception as e:
                markdown_content.append(f"*Error extracting text from page {page_num}: {str(e)}*")
                markdown_content.append("")
        
        return "\n".join(markdown_content)
    
    def _clean_pdf_text(self, text):
        if not text:
            return ""
        
        cleaned = ' '.join(text.split())
        cleaned = re.sub(r'([.!?])\s+([A-Z][a-z])', r'\1\n\n\2', cleaned)
        cleaned = re.sub(r'\s*([•·▪▫‣⁃])\s*', r'\n- ', cleaned)
        cleaned = re.sub(r'\s*(\d+\.)\s+', r'\n\1 ', cleaned)
        return cleaned
    
    def _is_likely_heading(self, text):
        if len(text) < 100 and (
            text.isupper() or
            (len(text.split()) <= 8 and text.count('.') == 0)
        ):
            return True
        return False

class ConverterFactory:
    @staticmethod
    def get_converter(file_type):
        converters = {
            'docx': WordToMarkdown(),
            'xlsx': ExcelToMarkdown(),
            'pptx': PowerPointToMarkdown(),
            'pdf': PDFToMarkdown()
        }
        return converters.get(file_type)

def get_current_date():
    return datetime.now().strftime("%Y-%m-%d")

def parse_uploaded_file(uploaded_file):
    """Parse uploaded file and convert to Markdown"""
    try:
        if uploaded_file is None:
            return False

        file_name = uploaded_file.name.lower()
        file_extension = file_name.split('.')[-1]
        
        converter = ConverterFactory.get_converter(file_extension)
        if not converter:
            st.error(f"🚨 Unsupported file type: {file_extension}")
            return False

        file_content = uploaded_file.getvalue()
        markdown_content = converter.convert(file_content)
        
        st.session_state.current_doc_text = markdown_content[:300000]
        st.success(f"📂 Document converted: {len(st.session_state.current_doc_text)} characters")
        return True

    except Exception as e:
        st.error(f"🚨 Conversion error: {str(e)}")
        st.session_state.current_doc_text = ""
        return False

def build_context(context_type: str) -> str:
    """Собирает контекст для указанного типа запроса"""
    config = CONTEXT_CONFIG[context_type]
    context_parts = []
    
    if config['doc_text'] and st.session_state.current_doc_text:
        context_parts.append(f"Документ: {st.session_state.current_doc_text[:100000]}")
    
    if config['original_query'] and 'input_query' in st.session_state:
        context_parts.append(f"Исходный запрос: {st.session_state.input_query}")
    
    if config['search_results'] and st.session_state.search_results:
        context_parts.append(f"Результаты поиска: {st.session_state.search_results[:20000]}")
    
    if config['method_results'] and hasattr(st.session_state, 'method_results'):
        method_results = "\n\n".join(
            [f"{method}:\n{result}" for method, result in st.session_state.method_results.items()]
        )
        context_parts.append(f"Анализ методик: {method_results[:10000]}")
    
    return "\n\n".join(context_parts)

def formulate_problem_and_queries():
    """Этап 1: Формулирование проблемы и генерация поисковых запросов"""
    context = build_context('problem_formulation')
    
    prompt = PROMPT_FORMULATE_PROBLEM_AND_QUERIES.format(
        query=st.session_state.input_query.strip(),
        doc_text=st.session_state.current_doc_text[:300000] if st.session_state.current_doc_text else "Нет документа"
    )
    
    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": st.session_state.temperature,
                "max_output_tokens": 4000
            },
            request_options={'timeout': 120}
        )
        
        result = response.text
        
        problem = ""
        internal_dialog = ""
        queries = []
        
        if "ПРОБЛЕМА:" in result:
            problem_part = result.split("ПРОБЛЕМА:")[1]
            if "РАССУЖДЕНИЯ:" in problem_part:
                problem = problem_part.split("РАССУЖДЕНИЯ:")[0].strip()
                internal_dialog_part = problem_part.split("РАССУЖДЕНИЯ:")[1]
                if "ЗАПРОСЫ:" in internal_dialog_part:
                    internal_dialog = internal_dialog_part.split("ЗАПРОСЫ:")[0].strip()
                    queries_part = internal_dialog_part.split("ЗАПРОСЫ:")[1]
                    for line in queries_part.split('\n'):
                        if line.strip() and line.strip()[0].isdigit():
                            query_text = line.split('.', 1)[1].strip() if '. ' in line else line.strip()
                            queries.append(query_text)
        
        if not problem:
            problem = result
        if not queries:
            last_lines = result.split('\n')[-10:]
            for line in last_lines:
                if line.strip() and line.strip()[0].isdigit() and '.' in line:
                    query_text = line.split('.', 1)[1].strip()
                    queries.append(query_text)
            if len(queries) > 5:
                queries = queries[:5]
        
        st.session_state.problem_formulation = problem
        st.session_state.internal_dialog = internal_dialog
        st.session_state.generated_queries = queries[:5]
        
        return result, queries
        
    except Exception as e:
        st.error(f"Ошибка при формулировании проблемы: {str(e)}")
        return f"Ошибка: {str(e)}", []

def apply_cognitive_method(method_name: str):
    """Применяет когнитивную методику к проблеме"""
    context = build_context('cognitive_method')
    
    prompt = PROMPT_APPLY_COGNITIVE_METHOD.format(
        method_name=method_name,
        problem_formulation=st.session_state.problem_formulation,
        context=context
    )
    
    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": st.session_state.temperature,
                "max_output_tokens": 12000
            },
            request_options={'timeout': 180}
        )
        return response.text
    except Exception as e:
        return f"Ошибка при применении {method_name}: {str(e)}"

def generate_refinement_queries() -> List[str]:
    """Генерирует уточняющие поисковые запросы на основе контекста"""
    context = build_context('refinement_queries')
    
    prompt = PROMPT_GENERATE_REFINEMENT_QUERIES.format(
        context=context[:100000]
    )
    
    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": st.session_state.temperature * 0.5,
                "max_output_tokens": 2000
            },
            request_options={'timeout': 90}
        )
        result = response.text
        
        queries = []
        for line in result.split('\n'):
            if line.strip() and line.strip()[0].isdigit():
                query_text = line.split('.', 1)[1].strip() if '. ' in line else line.strip()
                queries.append(query_text)
        
        return queries[:5]
        
    except Exception as e:
        st.error(f"Ошибка при генерации уточняющих запросов: {str(e)}")
        return []

def generate_final_conclusions() -> str:
    """Генерирует итоговые выводы на основе проблемы и контекста анализа"""
    context = build_context('final_conclusions')
    
    prompt = PROMPT_GENERATE_FINAL_CONCLUSIONS.format(
        problem_formulation=st.session_state.problem_formulation,
        analysis_context=context[:100000]
    )
    
    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": st.session_state.temperature * 0.7,
                "max_output_tokens": 9000
            },
            request_options={'timeout': 120}
        )
        return response.text
    except Exception as e:
        return f"Ошибка при генерации выводов: {str(e)}"

def generate_response():
    st.session_state.processing = True
    st.session_state.report_content = None
    status_area = st.empty()
    progress_bar = st.progress(0)

    try:
        try:
            test_response = requests.get("https://www.google.com", timeout=10)
            st.info(f"Сетевая доступность: {'OK' if test_response.status_code == 200 else 'Проблемы'}")
        except Exception as e:
            st.error(f"Сетевая ошибка: {str(e)}")

        query = st.session_state.input_query.strip()
        if not query:
            status_area.warning("⚠️ Введите запрос")
            return

        status_area.info("🔍 Формулирую проблему и генерирую поисковые запросы...")
        problem_result, queries = formulate_problem_and_queries()
        if not queries:
            queries = [query]
            st.warning("⚠️ Использован исходный запрос для поиска (LLM не сгенерировал запросы)")
        
        if st.session_state.internal_dialog:
            st.sidebar.subheader("🧠 Рассуждения ИИ")
            st.sidebar.text_area(
                "",
                value=st.session_state.internal_dialog,
                height=300,
                label_visibility="collapsed"
            )
        else:
            st.sidebar.warning("Рассуждения не были сгенерированы")
        
        with st.expander("✅ Этап 1: Формулировка проблемы", expanded=False):
            st.subheader("Сформулированная проблема")
            st.write(st.session_state.problem_formulation)
            
            st.subheader("Сгенерированные поисковые запросы")
            st.write(queries)
            
            st.subheader("Полный вывод LLM")
            st.code(problem_result, language='text')
        
        full_report = f"### Этап 1: Формулировка проблемы ###\n\n{problem_result}\n\n"
        full_report += f"Сформулированная проблема: {st.session_state.problem_formulation}\n\n"
        full_report += f"Рассуждения:\n{st.session_state.internal_dialog}\n\n"
        full_report += f"Поисковые запросы:\n" + "\n".join([f"{i+1}. {q}" for i, q in enumerate(queries)]) + "\n\n"

        status_area.info("🔍 Выполняю поиск информации...")
        all_search_results = ""
        
        for i, search_query in enumerate(queries):
            try:
                clean_query = search_query.replace('"', '').strip()
                search_result_list = searcher.perform_search(clean_query, max_results=3, full_text=True)
                
                formatted_results = []
                for j, r in enumerate(search_result_list, 1):
                    content = r.get('full_content', r.get('snippet', ''))
                    formatted_results.append(
                        f"Результат {j}: {r.get('title', '')}\n"
                        f"Контент: {content[:5000]}{'...' if len(content) > 5000 else ''}\n"
                        f"URL: {r.get('url', '')}\n"
                    )

                search_result_str = "\n\n".join(formatted_results)
                all_search_results += f"### Результаты по запросу '{search_query}':\n\n{search_result_str}\n\n"
                
                st.sidebar.subheader(f"🔍 Результаты по запросу: '{search_query}'")
                for j, r in enumerate(search_result_list, 1):
                    title = r.get('title', 'Без названия')
                    url = r.get('url', '')
                    snippet = r.get('snippet', '')

                    if url and not url.startswith('http'):
                        url = 'https://' + url

                    st.sidebar.markdown(f"**{j}. {title}**")
                    if url:
                        st.sidebar.markdown(f"[{url}]({url})")
                    if snippet:
                        st.sidebar.caption(snippet[:300] + ('...' if len(snippet) > 300 else ''))
                    st.sidebar.write("---")
                
            except Exception as e:
                st.error(f"Ошибка поиска для запроса '{search_query}': {str(e)}")
                all_search_results += f"### Ошибка поиска для запроса '{search_query}': {str(e)}\n\n"
        
        st.session_state.search_results = all_search_results
        
        status_area.info("⚙️ Применяю когнитивные методики...")
        
        all_methods = CORE_METHODS.copy()
        if st.session_state.selected_methods:
            all_methods += [m for m in st.session_state.selected_methods if m not in CORE_METHODS]
        
        st.session_state.method_results = {}
        
        for i, method in enumerate(all_methods):
            progress = int((i + 1) / (len(all_methods) + 1) * 100)
            progress_bar.progress(progress)
            
            status_area.info(f"⚙️ Применяю {method}...")
            try:
                result = apply_cognitive_method(method)
                st.session_state.method_results[method] = result
                
                st.subheader(f"✅ {method}")
                st.text_area("", value=result, height=300, label_visibility="collapsed")
                
                full_report += f"### Методика: {method} ###\n\n{result}\n\n"
            except Exception as e:
                st.error(f"Ошибка при применении {method}: {str(e)}")
                full_report += f"### Ошибка при применении {method}: {str(e)}\n\n"
            
            time.sleep(1)
        
        status_area.info("🔍 Выполняю уточняющий поиск...")
        refinement_search_results = ""
    
        refinement_queries = generate_refinement_queries()
    
        if refinement_queries:
            st.sidebar.subheader("🔎 Уточняющие запросы")
            for i, query in enumerate(refinement_queries):
                st.sidebar.write(f"{i+1}. {query}")
            
            for i, query in enumerate(refinement_queries):
                try:
                    clean_query = query.replace('"', '').strip()
                    search_results = searcher.perform_search(clean_query, max_results=2, full_text=True)
                
                    formatted = []
                    for j, r in enumerate(search_results, 1):
                        content = r.get('full_content', r.get('snippet', ''))
                        formatted.append(
                            f"Результат {j}: {r.get('title', '')}\n"
                            f"Контент: {content[:3000]}{'...' if len(content) > 3000 else ''}\n"
                            f"URL: {r.get('url', '')}\n"
                        )
                
                    refinement_search_results += f"### Уточняющий запрос '{query}':\n\n"
                    refinement_search_results += "\n\n".join(formatted) + "\n\n"
                
                except Exception as e:
                    refinement_search_results += f"### Ошибка поиска для '{query}': {str(e)}\n\n"
    
        status_area.info("📝 Формирую итоговые выводы...")
        progress_bar.progress(95)
        try:
            conclusions = generate_final_conclusions()
            
            st.subheader("📝 Итоговые выводы")
            st.text_area("", value=conclusions, height=400, label_visibility="collapsed")
            
            full_report += f"### Итоговые выводы ###\n\n{conclusions}\n\n"
        except Exception as e:
            st.error(f"Ошибка при генерации выводов: {str(e)}")
            full_report += f"### Ошибка при генерации выводов: {str(e)}\n\n"
        
        st.session_state.report_content = full_report
        progress_bar.progress(100)
        status_area.success("✅ Обработка завершена!")
        
    except Exception as e:
        st.error(f"💥 Критическая ошибка: {str(e)}")
        traceback.print_exc()
    finally:
        st.session_state.processing = False

# Интерфейс Streamlit
with st.sidebar:
    st.title("Troubleshooter")
    st.subheader("Решатель проблем")
    
    st.markdown("### Выберите дополнительные методы:")
    selected_methods = st.multiselect(
        "Дополнительные когнитивные методики:",
        ADDITIONAL_METHODS,
        key="selected_methods"
    )

# Основная область
st.title("Troubleshooter - Решатель проблем")
st.subheader("Решение проблем с применением когнитивных методов")

col1, col2 = st.columns([3, 1])
with col1:
    st.text_input(
        "Ваш запрос:",
        placeholder="Опишите вашу проблему...",
        key="input_query"
    )
with col2:
    st.slider(
        "Температура:",
        0.0, 1.0, 0.3, 0.1,
        key="temperature"
    )

uploaded_file = st.file_uploader(
    "Загрузите файл с дополнительным контекстом (DOCX, XLSX, PPTX, PDF):",
    type=["docx", "xlsx", "pptx", "pdf"],
    key="uploaded_file"
)

if uploaded_file:
    parse_uploaded_file(uploaded_file)

if st.button("Сгенерировать решение", disabled=st.session_state.processing):
    generate_response()

if st.session_state.report_content and not st.session_state.processing:
    st.divider()
    st.subheader("Экспорт результатов")
    
    b64_txt = base64.b64encode(st.session_state.report_content.encode()).decode()
    txt_href = f'<a href="data:file/txt;base64,{b64_txt}" download="report.txt">📥 Скачать TXT Markdown отчет</a>'
    st.markdown(txt_href, unsafe_allow_html=True)
    
    try:
        html_bytes = create_html_report(st.session_state.report_content, "Отчет Troubleshooter")
        b64_html = base64.b64encode(html_bytes).decode()
        html_href = f'<a href="data:text/html;base64,{b64_html}" download="report.html">📥 Скачать HTML отчет</a>'
        st.markdown(html_href, unsafe_allow_html=True)
        
        with st.expander("Предпросмотр отчета"):
            st.components.v1.html(html_bytes.decode('utf-8'), height=600, scrolling=True)
            
    except Exception as e:
        st.error(f"Ошибка при создании HTML отчета: {str(e)}")

if st.session_state.processing:
    st.info("⏳ Обработка запроса...")
