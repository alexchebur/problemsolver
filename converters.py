import io
import re
from docx import Document
from openpyxl import load_workbook
from pptx import Presentation
import PyPDF2
import pandas as pd
from typing import Optional

class WordToMarkdown:
    """Converter for Word documents to Markdown"""
    
    def convert(self, file_content: bytes) -> str:
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
    
    def _format_text_runs(self, paragraph) -> str:
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
    
    def _convert_table(self, table) -> str:
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
    
    def convert(self, file_content: bytes) -> str:
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
    
    def _create_markdown_table(self, data: list) -> str:
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
    
    def convert(self, file_content: bytes) -> str:
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
    
    def _is_likely_title(self, shape) -> bool:
        try:
            if hasattr(shape, 'top') and shape.top < 1000000:
                return True
        except:
            pass
        return False
    
    def _convert_ppt_table(self, table) -> str:
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
    
    def convert(self, file_content: bytes) -> str:
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
    
    def _clean_pdf_text(self, text: str) -> str:
        if not text:
            return ""
        
        cleaned = ' '.join(text.split())
        cleaned = re.sub(r'([.!?])\s+([A-Z][a-z])', r'\1\n\n\2', cleaned)
        cleaned = re.sub(r'\s*([•·▪▫‣⁃])\s*', r'\n- ', cleaned)
        cleaned = re.sub(r'\s*(\d+\.)\s+', r'\n\1 ', cleaned)
        return cleaned
    
    def _is_likely_heading(self, text: str) -> bool:
        if len(text) < 100 and (
            text.isupper() or
            (len(text.split()) <= 8 and text.count('.') == 0)
        ):
            return True
        return False

class ConverterFactory:
    """Factory for file converters"""
    
    @staticmethod
    def get_converter(file_type: str):
        converters = {
            'docx': WordToMarkdown(),
            'xlsx': ExcelToMarkdown(),
            'pptx': PowerPointToMarkdown(),
            'pdf': PDFToMarkdown()
        }
        return converters.get(file_type)

def convert_uploaded_file_to_markdown(uploaded_file) -> Optional[str]:
    """Parse uploaded file and convert to Markdown"""
    try:
        if uploaded_file is None:
            return None

        file_name = uploaded_file.name.lower()
        file_extension = file_name.split('.')[-1]
        
        converter = ConverterFactory.get_converter(file_extension)
        if not converter:
            return None

        file_content = uploaded_file.getvalue()
        return converter.convert(file_content)[:300000]  # Limit to 300k characters

    except Exception as e:
        return None
