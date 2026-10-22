from sentence_transformers import SentenceTransformer
from django.conf import settings

_embedding_model = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _embedding_model

def embed_texts(texts):
    """Embed chunks locally in batches of 32 without query prefix, normalized."""
    if not texts:
        return []
    model = get_embedding_model()
    embeddings = model.encode(texts, batch_size=32, normalize_embeddings=True)
    return embeddings.tolist()

def embed_query(query_text):
    """Embed question (+ code snippet) locally with bge prefix, normalized."""
    prefix = "Represent this sentence for searching relevant passages: "
    model = get_embedding_model()
    embedding = model.encode([prefix + query_text], normalize_embeddings=True)
    return embedding[0].tolist()

def search_relevant_chunks(user, source_ids, question_text, code_text="", top_k=8, threshold=0.60):
    """
    Retrieves the top_k most similar chunks for the given user's sources.
    Filters out chunks with similarity < threshold.
    Returns:
      chunks: list of dicts:
        {
          'chunk_obj': Chunk,
          'rank': int (1-based),
          'score': float,
          'label': str,
          'text': str,
        }
      evidence_status: 'SUFFICIENT' | 'INSUFFICIENT' | 'NO_SOURCES'
    """
    from pgvector.django import CosineDistance
    from kb.models import Chunk

    if not source_ids:
        return [], 'NO_SOURCES'

    # Combine question + first 500 chars of code as per TECH.md
    snippet = code_text[:500] if code_text else ""
    combined_query = f"{question_text}\n{snippet}".strip()
    if not combined_query:
        return [], 'NO_SOURCES'

    query_vec = embed_query(combined_query)

    # Search in Supabase PostgreSQL pgvector
    queryset = (
        Chunk.objects.filter(source__owner=user, source_id__in=source_ids)
        .annotate(distance=CosineDistance('embedding', query_vec))
        .select_related('source', 'source_file')
        .order_by('distance')[:top_k]
    )

    retrieved = []
    rank = 1
    for chunk in queryset:
        score = 1.0 - float(chunk.distance)
        if score >= threshold:
            label = f"{chunk.source.name} - {chunk.source_file.path}"
            if chunk.page_number:
                label += f" (p. {chunk.page_number})"
            elif chunk.start_line and chunk.end_line:
                label += f" (lines {chunk.start_line}-{chunk.end_line})"

            retrieved.append({
                'chunk_obj': chunk,
                'rank': rank,
                'score': round(score, 4),
                'label': label,
                'text': chunk.text,
            })
            rank += 1

    if not retrieved:
        return [], 'INSUFFICIENT'

    return retrieved, 'SUFFICIENT'

