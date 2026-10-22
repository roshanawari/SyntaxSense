from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .models import Question, RetrievedChunk

@require_http_methods(["GET"])
def api_questions_list(request):
    if not request.user.is_authenticated:
        return JsonResponse(
            {"error": {"code": "UNAUTHORIZED", "message": "Authentication required"}},
            status=401
        )

    questions = Question.objects.filter(owner=request.user).order_by('-created_at')
    data = [
        {
            "id": q.id,
            "question_text": q.question_text,
            "language": q.language,
            "evidence_status": q.evidence_status,
            "created_at": q.created_at.isoformat(),
        }
        for q in questions
    ]
    return JsonResponse(data, safe=False, status=200)

@require_http_methods(["GET"])
def api_question_detail(request, question_id):
    if not request.user.is_authenticated:
        return JsonResponse(
            {"error": {"code": "UNAUTHORIZED", "message": "Authentication required"}},
            status=401
        )

    try:
        question = Question.objects.get(id=question_id)
    except Question.DoesNotExist:
        return JsonResponse(
            {"error": {"code": "NOT_FOUND", "message": "Question not found"}},
            status=404
        )

    if question.owner != request.user:
        return JsonResponse(
            {"error": {"code": "FORBIDDEN", "message": "Access denied"}},
            status=403
        )

    retrieved = question.retrieved_chunks.all().order_by('rank')
    retrieved_data = []
    for rc in retrieved:
        retrieved_data.append({
            "id": rc.id,
            "rank": rc.rank,
            "score": rc.score,
            "label": rc.saved_label,
            "text": rc.saved_text,
            "cited": rc.cited,
            "chunk_id": rc.chunk_id,
            "source_id": rc.chunk.source_id if rc.chunk else None,
            "source_file_id": rc.chunk.source_file_id if rc.chunk else None,
        })

    return JsonResponse({
        "id": question.id,
        "code": question.code,
        "language": question.language,
        "question_text": question.question_text,
        "source_ids": question.source_ids,
        "answer": question.answer,
        "evidence_status": question.evidence_status,
        "created_at": question.created_at.isoformat(),
        "retrieved_chunks": retrieved_data,
    }, status=200)
