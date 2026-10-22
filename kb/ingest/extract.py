import io
from pypdf import PdfReader
from docx import Document

def extract_pdf(file_bytes):
    """
    Extracts text from PDF bytes in memory.
    Returns dict:
      'topic': str or None
      'page_count': int
      'pages': [(page_num, text), ...]
      'full_text': str
    """
    reader = PdfReader(io.BytesIO(file_bytes))
    page_count = len(reader.pages)
    pages = []
    full_text_parts = []

    for idx, page in enumerate(reader.pages, start=1):
        txt = page.extract_text() or ''
        pages.append((idx, txt))
        full_text_parts.append(f"--- Page {idx} ---\n{txt}")

    # Determine topic: from PDF metadata title or first non-empty line
    topic = None
    if reader.metadata and reader.metadata.title:
        topic = str(reader.metadata.title).strip()
    if not topic and pages:
        first_lines = [line.strip() for line in pages[0][1].splitlines() if line.strip()]
        if first_lines:
            topic = first_lines[0][:100]

    return {
        'topic': topic or 'PDF Document',
        'page_count': page_count,
        'pages': pages,
        'full_text': "\n\n".join(full_text_parts),
    }

def extract_docx(file_bytes):
    """
    Extracts text from DOCX bytes in memory.
    Returns dict:
      'topic': str or None
      'full_text': str
    """
    doc = Document(io.BytesIO(file_bytes))
    topic = None
    paragraphs = []

    for p in doc.paragraphs:
        txt = p.text.strip()
        if txt:
            paragraphs.append(txt)
            if not topic:
                # First non-empty paragraph or heading is used as topic
                topic = txt[:100]

    for table in doc.tables:
        for row in table.rows:
            row_txt = " | ".join(c.text.strip() for c in row.cells if c.text.strip())
            if row_txt:
                paragraphs.append(row_txt)

    full_text = "\n\n".join(paragraphs)
    return {
        'topic': topic or 'DOCX Document',
        'full_text': full_text,
    }

def extract_txt(file_bytes):
    """
    Extracts plain text in memory.
    Returns dict:
      'topic': str or None
      'full_text': str
    """
    full_text = file_bytes.decode('utf-8', errors='replace')
    topic = None
    for line in full_text.splitlines():
        trimmed = line.strip().lstrip('#').strip()
        if trimmed:
            topic = trimmed[:100]
            break

    return {
        'topic': topic or 'Text Document',
        'full_text': full_text,
    }
