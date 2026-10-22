import re

def chunk_document_text(text, target_size=1200, overlap=150):
    """
    Split document text into chunks of ~1,200 chars with ~150 char overlap,
    preferring paragraph breaks (\n\n) then line breaks (\n) then spaces.
    Returns list of dicts: [{'text': str, 'page_number': None, 'start_line': None, 'end_line': None}]
    """
    if not text or not text.strip():
        return []

    text = text.strip()
    if len(text) <= target_size:
        return [{'text': text, 'page_number': None, 'start_line': 1, 'end_line': text.count('\n') + 1}]

    paragraphs = re.split(r'(\n\s*\n)', text)
    chunks = []
    current_chunk = []
    current_length = 0

    for part in paragraphs:
        if not part:
            continue
        part_len = len(part)

        if current_length + part_len <= target_size:
            current_chunk.append(part)
            current_length += part_len
        else:
            if current_chunk:
                chunk_str = "".join(current_chunk).strip()
                if chunk_str:
                    chunks.append({'text': chunk_str, 'page_number': None, 'start_line': None, 'end_line': None})

                # Handle overlap from tail of current_chunk
                overlap_text = chunk_str[-overlap:] if len(chunk_str) > overlap else ""
                current_chunk = [overlap_text, part] if overlap_text else [part]
                current_length = len("".join(current_chunk))
            else:
                # Single paragraph larger than target_size, split by sentences or lines
                sub_lines = part.splitlines(keepends=True)
                for line in sub_lines:
                    if current_length + len(line) <= target_size:
                        current_chunk.append(line)
                        current_length += len(line)
                    else:
                        chunk_str = "".join(current_chunk).strip()
                        if chunk_str:
                            chunks.append({'text': chunk_str, 'page_number': None, 'start_line': None, 'end_line': None})
                        current_chunk = [line]
                        current_length = len(line)

    if current_chunk:
        chunk_str = "".join(current_chunk).strip()
        if chunk_str:
            chunks.append({'text': chunk_str, 'page_number': None, 'start_line': None, 'end_line': None})

    return chunks

def chunk_pdf_pages(pages):
    """
    pages is a list of tuples: [(page_number, page_text), ...]
    Chunks each page's text while preserving page_number.
    """
    all_chunks = []
    for page_num, page_text in pages:
        if not page_text or not page_text.strip():
            continue
        page_chunks = chunk_document_text(page_text, target_size=1200, overlap=150)
        for c in page_chunks:
            c['page_number'] = page_num
            all_chunks.append(c)
    return all_chunks

def chunk_code_text(code_text, max_lines=40, max_chars=1500):
    """
    Split code ~40 lines or 1,500 characters per chunk, whichever is smaller.
    Splits on blank lines when possible, recording 1-indexed start_line and end_line.
    """
    if not code_text or not code_text.strip():
        return []

    lines = code_text.splitlines()
    total_lines = len(lines)
    if total_lines == 0:
        return []

    chunks = []
    current_lines = []
    chunk_start_line = 1
    current_chars = 0

    for idx, line in enumerate(lines, start=1):
        line_len = len(line) + 1  # include newline char
        should_split = (len(current_lines) >= max_lines) or (current_chars + line_len > max_chars)

        if should_split and current_lines:
            chunk_str = "\n".join(current_lines).strip()
            if chunk_str:
                chunks.append({
                    'text': chunk_str,
                    'page_number': None,
                    'start_line': chunk_start_line,
                    'end_line': idx - 1,
                })
            current_lines = [line]
            current_chars = line_len
            chunk_start_line = idx
        else:
            current_lines.append(line)
            current_chars += line_len

    if current_lines:
        chunk_str = "\n".join(current_lines).strip()
        if chunk_str:
            chunks.append({
                'text': chunk_str,
                'page_number': None,
                'start_line': chunk_start_line,
                'end_line': total_lines,
            })

    return chunks
