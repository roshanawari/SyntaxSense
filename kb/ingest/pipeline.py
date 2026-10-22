from django.db import transaction
from kb.models import Source, SourceFile, Chunk
from kb.rag.retrieval import embed_texts
from .chunking import chunk_document_text, chunk_pdf_pages, chunk_code_text
from .extract import extract_pdf, extract_docx, extract_txt
from .github import parse_github_url, download_github_zip, inspect_github_zip

MAX_CHUNKS_PER_SOURCE = 500

def process_text_source(user, name, text_content):
    name = name.strip()
    text = text_content.strip()

    if not name or len(name) > 100:
        raise ValueError("Source name must be between 1 and 100 characters")
    if not text:
        raise ValueError("Pasted text cannot be empty")
    if len(text) > 100000:
        raise ValueError("Pasted text exceeds the 100,000 character limit")

    source = Source.objects.create(
        owner=user,
        name=name,
        kind='TEXT',
        status='PROCESSING',
    )

    try:
        raw_chunks = chunk_document_text(text)
        if len(raw_chunks) > MAX_CHUNKS_PER_SOURCE:
            raw_chunks = raw_chunks[:MAX_CHUNKS_PER_SOURCE]

        first_heading = text.splitlines()[0][:100] if text else name

        source_file = SourceFile.objects.create(
            source=source,
            path=f"{name[:30].strip()}.txt",
            kind='DOCUMENT',
            topic=first_heading,
            size_bytes=len(text.encode('utf-8')),
            extracted_text=text,
            status='READY',
            chunk_count=len(raw_chunks),
        )

        texts_to_embed = [c['text'] for c in raw_chunks]
        embeddings = embed_texts(texts_to_embed)

        chunks_to_create = []
        for idx, (c, emb) in enumerate(zip(raw_chunks, embeddings), start=1):
            chunks_to_create.append(
                Chunk(
                    source=source,
                    source_file=source_file,
                    position=idx,
                    text=c['text'],
                    page_number=c.get('page_number'),
                    start_line=c.get('start_line'),
                    end_line=c.get('end_line'),
                    embedding=emb,
                )
            )

        with transaction.atomic():
            Chunk.objects.bulk_create(chunks_to_create)
            source.file_count = 1
            source.chunk_count = len(chunks_to_create)
            source.status = 'READY'
            source.save()

        return source
    except Exception as e:
        source.status = 'FAILED'
        source.error_message = str(e)
        source.save()
        raise e


def process_file_source(user, uploaded_file):
    name = uploaded_file.name
    lower_name = name.lower()

    if lower_name.endswith('.doc'):
        raise ValueError("Legacy .doc format is not supported. Please convert your file to .docx or .pdf.")

    ext = lower_name.rsplit('.', 1)[-1] if '.' in lower_name else ''
    if ext not in ('pdf', 'docx', 'txt'):
        raise ValueError("Unsupported file type. Please upload a PDF, DOCX, or TXT file.")

    if uploaded_file.size > 5 * 1024 * 1024:
        raise ValueError("Uploaded file exceeds 5 MB limit")
    if uploaded_file.size == 0:
        raise ValueError("Uploaded file is empty")

    file_bytes = uploaded_file.read()
    if not file_bytes:
        raise ValueError("Uploaded file is empty")

    source = Source.objects.create(
        owner=user,
        name=name,
        kind='FILE',
        status='PROCESSING',
    )

    try:
        raw_chunks = []
        page_count = None
        topic = None
        extracted_text = ""

        if ext == 'pdf':
            pdf_data = extract_pdf(file_bytes)
            topic = pdf_data['topic']
            page_count = pdf_data['page_count']
            extracted_text = pdf_data['full_text']
            raw_chunks = chunk_pdf_pages(pdf_data['pages'])
        elif ext == 'docx':
            docx_data = extract_docx(file_bytes)
            topic = docx_data['topic']
            extracted_text = docx_data['full_text']
            raw_chunks = chunk_document_text(extracted_text)
        elif ext == 'txt':
            txt_data = extract_txt(file_bytes)
            topic = txt_data['topic']
            extracted_text = txt_data['full_text']
            raw_chunks = chunk_document_text(extracted_text)

        if not extracted_text or not extracted_text.strip():
            raise ValueError("No text could be extracted from the uploaded document")

        if len(raw_chunks) > MAX_CHUNKS_PER_SOURCE:
            raw_chunks = raw_chunks[:MAX_CHUNKS_PER_SOURCE]

        source_file = SourceFile.objects.create(
            source=source,
            path=name,
            kind='DOCUMENT',
            language='Text' if ext == 'txt' else ext.upper(),
            topic=topic,
            page_count=page_count,
            extracted_text=extracted_text,
            size_bytes=len(file_bytes),
            status='READY',
            chunk_count=len(raw_chunks),
        )

        texts_to_embed = [c['text'] for c in raw_chunks]
        embeddings = embed_texts(texts_to_embed)

        chunks_to_create = []
        for idx, (c, emb) in enumerate(zip(raw_chunks, embeddings), start=1):
            chunks_to_create.append(
                Chunk(
                    source=source,
                    source_file=source_file,
                    position=idx,
                    text=c['text'],
                    page_number=c.get('page_number'),
                    start_line=c.get('start_line'),
                    end_line=c.get('end_line'),
                    embedding=emb,
                )
            )

        with transaction.atomic():
            Chunk.objects.bulk_create(chunks_to_create)
            source.file_count = 1
            source.chunk_count = len(chunks_to_create)
            source.status = 'READY'
            source.save()

        return source
    except Exception as e:
        source.status = 'FAILED'
        source.error_message = str(e)
        source.save()
        raise e


def process_github_source(user, github_url):
    owner, repo = parse_github_url(github_url)
    if not owner or not repo:
        raise ValueError("Invalid GitHub URL. Must be in the format https://github.com/owner/repo")

    # Download in memory
    zip_bytes = download_github_zip(owner, repo)
    supported_files, skipped_files, _ = inspect_github_zip(zip_bytes)

    source = Source.objects.create(
        owner=user,
        name=f"{owner}/{repo}",
        kind='GITHUB',
        origin_url=github_url,
        status='PROCESSING',
    )

    try:
        source_files_records = []
        all_chunks_data = []  # tuples of (file_idx, chunk_dict)

        # Create records for skipped files
        for sf in skipped_files:
            source_files_records.append(
                SourceFile(
                    source=source,
                    path=sf['path'],
                    kind='CODE',
                    size_bytes=sf['size'],
                    status='SKIPPED',
                    skip_reason=sf['reason'],
                    chunk_count=0,
                )
            )

        # Process supported files
        total_chunks = 0
        for f in supported_files:
            chunks = chunk_code_text(f['content'])
            if total_chunks + len(chunks) > MAX_CHUNKS_PER_SOURCE:
                allowed = max(0, MAX_CHUNKS_PER_SOURCE - total_chunks)
                chunks = chunks[:allowed]

            total_chunks += len(chunks)

            sf_record = SourceFile(
                source=source,
                path=f['path'],
                kind='CODE',
                language=f['language'],
                topic=f['path'].split('/')[-1],
                extracted_text=f['content'],
                size_bytes=f['size'],
                status='READY',
                chunk_count=len(chunks),
            )
            source_files_records.append((sf_record, chunks))

        with transaction.atomic():
            # Save files
            ready_files = []
            for item in source_files_records:
                if isinstance(item, tuple):
                    sf, chunks = item
                    sf.save()
                    ready_files.append((sf, chunks))
                else:
                    item.save()

            # Collect texts for embedding
            flat_texts = []
            flat_refs = []  # (sf, chunk_dict, position_in_file)
            for sf, chunks in ready_files:
                for pos, c in enumerate(chunks, start=1):
                    flat_texts.append(c['text'])
                    flat_refs.append((sf, c, pos))

            # Batch embed in Python locally
            embeddings = embed_texts(flat_texts) if flat_texts else []

            chunks_to_create = []
            for (sf, c, pos), emb in zip(flat_refs, embeddings):
                chunks_to_create.append(
                    Chunk(
                        source=source,
                        source_file=sf,
                        position=pos,
                        text=c['text'],
                        page_number=None,
                        start_line=c.get('start_line'),
                        end_line=c.get('end_line'),
                        embedding=emb,
                    )
                )

            Chunk.objects.bulk_create(chunks_to_create)

            source.file_count = len(supported_files) + len(skipped_files)
            source.chunk_count = len(chunks_to_create)
            source.status = 'READY'
            source.save()

        return source
    except Exception as e:
        source.status = 'FAILED'
        source.error_message = str(e)
        source.save()
        raise e
