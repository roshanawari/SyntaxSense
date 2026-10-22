import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.conf import settings
from .models import Source, Question, RetrievedChunk
from .rag.retrieval import search_relevant_chunks
from .rag.gemini import call_gemini_rag

@require_http_methods(["POST"])
def api_ask(request):
    if not request.user.is_authenticated:
        return JsonResponse(
            {"error": {"code": "UNAUTHORIZED", "message": "Authentication required"}},
            status=401
        )

    # In-flight rate limit protection: 1 request per user at a time
    if request.session.get('ask_in_flight'):
        return JsonResponse(
            {"error": {"code": "CONCURRENT_REQUEST", "message": "A request is already in progress. Please wait for it to complete."}},
            status=429
        )

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse(
            {"error": {"code": "BAD_REQUEST", "message": "Invalid JSON body"}},
            status=400
        )

    code = data.get('code', '') or ''
    question_text = data.get('question', '') or ''
    language = data.get('language') or None
    raw_source_ids = data.get('source_ids', [])

    if not code.strip() and not question_text.strip():
        return JsonResponse(
            {"error": {"code": "VALIDATION_ERROR", "message": "Please provide code, a question, or both"}},
            status=400
        )

    if len(code) > 20000:
        return JsonResponse(
            {"error": {"code": "VALIDATION_ERROR", "message": "Code exceeds 20,000 character limit"}},
            status=400
        )

    if len(question_text) > 2000:
        return JsonResponse(
            {"error": {"code": "VALIDATION_ERROR", "message": "Question exceeds 2,000 character limit"}},
            status=400
        )

    # Clean and validate source_ids
    source_ids = []
    if isinstance(raw_source_ids, list):
        for sid in raw_source_ids:
            try:
                source_ids.append(int(sid))
            except (ValueError, TypeError):
                continue

    # Ownership check on sources
    if source_ids:
        owned_count = Source.objects.filter(id__in=source_ids, owner=request.user).count()
        if owned_count != len(source_ids):
            return JsonResponse(
                {"error": {"code": "FORBIDDEN", "message": "Access denied to one or more selected sources"}},
                status=403
            )

    request.session['ask_in_flight'] = True
    request.session.modified = True

    try:
        # Step 1: Retrieval with pgvector
        retrieved_chunks, evidence_status = search_relevant_chunks(
            user=request.user,
            source_ids=source_ids,
            question_text=question_text,
            code_text=code,
            top_k=8,
            threshold=settings.SIMILARITY_THRESHOLD,
        )

        # Step 2: Generation with Gemini
        answer = call_gemini_rag(
            question_text=question_text,
            code_text=code,
            retrieved_chunks=retrieved_chunks,
            evidence_status=evidence_status,
        )

        # Step 3: Determine which chunks were cited
        cited_ranks = set()
        for item in answer.get('explanation', []):
            cited_ranks.update(item.get('chunk_numbers', []))
        for item in answer.get('bugs', []):
            cited_ranks.update(item.get('chunk_numbers', []))
        for item in answer.get('fixes', []):
            cited_ranks.update(item.get('chunk_numbers', []))

        # Step 4: Persist Question and RetrievedChunks in database
        with transaction.atomic():
            question = Question.objects.create(
                owner=request.user,
                code=code,
                language=language,
                question_text=question_text,
                source_ids=source_ids,
                answer=answer,
                evidence_status=evidence_status,
            )

            retrieved_chunk_objects = []
            for rc in retrieved_chunks:
                retrieved_chunk_objects.append(
                    RetrievedChunk(
                        question=question,
                        chunk=rc['chunk_obj'],
                        rank=rc['rank'],
                        score=rc['score'],
                        saved_label=rc['label'],
                        saved_text=rc['text'],
                        cited=rc['rank'] in cited_ranks,
                    )
                )

            if retrieved_chunk_objects:
                RetrievedChunk.objects.bulk_create(retrieved_chunk_objects)

        return JsonResponse({
            "id": question.id,
            "evidence_status": question.evidence_status,
            "created_at": question.created_at.isoformat(),
        }, status=201)

    except ValueError as e:
        return JsonResponse(
            {"error": {"code": "AI_ERROR", "message": str(e)}},
            status=502
        )
    except Exception as e:
        return JsonResponse(
            {"error": {"code": "SERVER_ERROR", "message": f"Failed to complete request: {str(e)}"}},
            status=502
        )
    finally:
        request.session['ask_in_flight'] = False
        request.session.modified = True
