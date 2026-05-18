"""政府文书（.docx）解析服务"""
import os
from docx import Document as DocxDocument


def extract_text_from_docx(file_path: str) -> str:
    """从 .docx 文件提取全部文本"""
    if not os.path.exists(file_path):
        return ""
    doc = DocxDocument(file_path)
    paragraphs = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            paragraphs.append(text)
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text.strip() for cell in row.cells)
            if row_text.replace("|", "").strip():
                paragraphs.append(row_text)
    return "\n".join(paragraphs)
