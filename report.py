# report.py
import re
import os
import tempfile
import base64
import logging
from io import BytesIO
from fpdf import FPDF
from PIL import Image
from mermaid import process_mermaid_diagrams

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация шрифтов
FONT_DIR = "fonts/"
FONT_MAPPING = {
    'normal': {
        'builtin': 'Helvetica',
        'custom': {'path': FONT_DIR+'DejaVuSansCondensed.ttf', 'name': 'DejaVu'}
    },
    'bold': {
        'builtin': 'Helvetica-B',
        'custom': {'path': FONT_DIR+'DejaVuSansCondensed-Bold.ttf', 'name': 'DejaVuB'}
    }
}

def create_pdf(content, title="Отчет"):
    try:
        logger.info("Начало создания PDF...")
        original_content = content
        
        pdf = FPDF()
        pdf.add_page()
        
        logger.info("Пытаемся загрузить шрифты...")
        custom_fonts_available = True
        for font_type in FONT_MAPPING.values():
            try:
                if os.path.exists(font_type['custom']['path']):
                    pdf.add_font(
                        font_type['custom']['name'],
                        '',
                        font_type['custom']['path'],
                        uni=True
                    )
                else:
                    logger.warning(f"Файл шрифта не найден: {font_type['custom']['path']}")
                    custom_fonts_available = False
            except Exception as e:
                logger.error(f"Ошибка загрузки шрифта: {str(e)}")
                custom_fonts_available = False
        
        def set_font(style='normal', size=12):
            if custom_fonts_available:
                font_name = FONT_MAPPING[style]['custom']['name']
            else:
                font_name = FONT_MAPPING[style]['builtin']
            pdf.set_font(font_name, '', size)
        
        pdf.set_auto_page_break(auto=True, margin=15)
        effective_width = pdf.w - 2*pdf.l_margin
        
        def clean_markdown(text):
            text = re.sub(r'```mermaid.*?```', '', text, flags=re.DOTALL)
            replacements = [
                (r'#{1,3}\s*', ''),
                (r'\*{2}(.*?)\*{2}', r'\1'),
                (r'_{2}(.*?)_{2}', r'\1'),
                (r'`{1,3}(.*?)`{1,3}', r'\1'),
                (r'\[(.*?)\]\(.*?\)', r'\1'),
                (r'\s+', ' ')
            ]
            for pattern, repl in replacements:
                text = re.sub(pattern, repl, text)
            return text.strip()
        
        set_font('bold', 16)
        pdf.cell(0, 10, txt=title, ln=1, align='C')
        pdf.ln(8)
        
        logger.info("Очистка Markdown...")
        cleaned_content = clean_markdown(content)
        paragraphs = re.split(r'\n\s*\n', cleaned_content)

        logger.info("Добавление текста в PDF...")
        for para in paragraphs:
            para = para.strip()
            if not para:
                pdf.ln(5)
                continue
            
            if para.upper() == para and len(para) < 100:
                set_font('bold', 14)
                pdf.cell(0, 8, txt=para, ln=1)
                pdf.ln(4)
                continue
            elif para.endswith(':'):
                set_font('bold', 12)
                pdf.cell(0, 7, txt=para, ln=1)
                pdf.ln(3)
                continue
            else:
                set_font('normal', 12)
                
            lines = pdf.multi_cell(
                w=effective_width,
                h=6,
                txt=para,
                split_only=True
            )
            
            for line in lines:
                pdf.cell(0, 6, txt=line, ln=1)
            
            pdf.ln(3)
        
        logger.info("Обработка диаграмм Mermaid...")
        mermaid_images = process_mermaid_diagrams(original_content)
        logger.info(f"Обработано {len(mermaid_images)} диаграмм Mermaid")
        
        if mermaid_images:
            logger.info("Добавление диаграмм Mermaid в PDF...")
            pdf.add_page()
            set_font('bold', 14)
            pdf.cell(0, 10, txt="Диаграммы Mermaid", ln=1, align='C')
            pdf.ln(8)
            
            for key, value in mermaid_images.items():
                img_data = value["image"]
                img_size = value["size"]
                
                max_width = pdf.w - 20
                max_height = pdf.h - 50
                
                width_ratio = max_width / img_size[0] if img_size[0] > 0 else 1
                height_ratio = max_height / img_size[1] if img_size[1] > 0 else 1
                ratio = min(width_ratio, height_ratio)
                
                if ratio < 0.1:
                    ratio = 0.1
                
                new_width = img_size[0] * ratio
                new_height = img_size[1] * ratio
                
                x = (pdf.w - new_width) / 2
                y = (pdf.h - new_height) / 2
                
                with tempfile.NamedTemporaryFile(delete=True, suffix=".png") as tmp_file:
                    tmp_file.write(base64.b64decode(img_data))
                    tmp_file.flush()
                    pdf.image(tmp_file.name, x=x, y=y, w=new_width)
                
                set_font('normal', 10)
                pdf.ln(new_height + 5)
                pdf.cell(0, 6, txt=f"Диаграмма {key}", ln=1)
                pdf.ln(5)
        else:
            logger.info("Диаграммы Mermaid не обнаружены")
        
        buffer = BytesIO()
        pdf.output(buffer)
        logger.info("PDF успешно создан")
        return buffer.getvalue()
    
    except Exception as e:
        logger.exception("Ошибка при создании PDF")
        return None
