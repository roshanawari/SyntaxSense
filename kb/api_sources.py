import json
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from .models import Source, SourceFile, Chunk
from .ingest.pipeline import process_text_source, process_file_source, process_github_source
from .ingest.github import inspect_github_zip

@require_http_methods(["GET"])
def api_sources_list(request):
    if not request.user.is_authenticated:
        return JsonResponse(
            {"error": {"code": "UNAUTHORIZED", "message": "Authentication required"}},
            status=401
        )

    sources = Source.objects.filter(owner=request.user).order_by('-created_at')
    data = [
        {
            "id": s.id,
            "name": s.name,
            "kind": s.kind,
            "status": s.status,
            "origin_url": s.origin_url,
            "error_message": s.error_message,
            "file_count": s.file_count,
            "chunk_count": s.chunk_count,
            "created_at": s.created_at.isoformat(),
        }
        for s in sources
    ]
    return JsonResponse(data, safe=False, status=200)

@require_http_methods(["POST"])
def api_source_add_text(request):
    if not request.user.is_authenticated:
        return JsonResponse(
            {"error": {"code": "UNAUTHORIZED", "message": "Authentication required"}},
            status=401
        )

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse(
            {"error": {"code": "BAD_REQUEST", "message": "Invalid JSON body"}},
            status=400
        )

    name = data.get('name', '').strip()
    text = data.get('text', '').strip()

    if not name or not text:
        return JsonResponse(
            {"error": {"code": "VALIDATION_ERROR", "message": "Name and text content are required"}},
            status=400
        )

    try:
        source = process_text_source(request.user, name, text)
        return JsonResponse({
            "id": source.id,
            "name": source.name,
            "kind": source.kind,
            "status": source.status,
            "file_count": source.file_count,
            "chunk_count": source.chunk_count,
        }, status=201)
    except ValueError as e:
        return JsonResponse(
            {"error": {"code": "VALIDATION_ERROR", "message": str(e)}},
            status=400
        )
    except Exception as e:
        return JsonResponse(
            {"error": {"code": "PROCESSING_ERROR", "message": f"Failed to process text: {str(e)}"}},
            status=502
        )

@require_http_methods(["POST"])
def api_source_add_upload(request):
    if not request.user.is_authenticated:
        return JsonResponse(
            {"error": {"code": "UNAUTHORIZED", "message": "Authentication required"}},
            status=401
        )

    uploaded_file = request.FILES.get('file')
    if not uploaded_file:
        return JsonResponse(
            {"error": {"code": "VALIDATION_ERROR", "message": "No file uploaded"}},
            status=400
        )

    if uploaded_file.size > 5 * 1024 * 1024:
        return JsonResponse(
            {"error": {"code": "PAYLOAD_TOO_LARGE", "message": "Uploaded file exceeds the 5 MB limit"}},
            status=413
        )

    try:
        source = process_file_source(request.user, uploaded_file)
        return JsonResponse({
            "id": source.id,
            "name": source.name,
            "kind": source.kind,
            "status": source.status,
            "file_count": source.file_count,
            "chunk_count": source.chunk_count,
        }, status=201)
    except ValueError as e:
        err_msg = str(e)
        code = "PAYLOAD_TOO_LARGE" if "limit" in err_msg else "VALIDATION_ERROR"
        status_code = 413 if "5 MB" in err_msg else 400
        return JsonResponse(
            {"error": {"code": code, "message": err_msg}},
            status=status_code
        )
    except Exception as e:
        return JsonResponse(
            {"error": {"code": "PROCESSING_ERROR", "message": f"Failed to process document: {str(e)}"}},
            status=502
        )

@require_http_methods(["POST"])
def api_source_add_github(request):
    if not request.user.is_authenticated:
        return JsonResponse(
            {"error": {"code": "UNAUTHORIZED", "message": "Authentication required"}},
            status=401
        )

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse(
            {"error": {"code": "BAD_REQUEST", "message": "Invalid JSON body"}},
            status=400
        )

    url = data.get('url', '').strip()
    if not url:
        return JsonResponse(
            {"error": {"code": "VALIDATION_ERROR", "message": "GitHub repository URL is required"}},
            status=400
        )

    try:
        source = process_github_source(request.user, url)
        return JsonResponse({
            "id": source.id,
            "name": source.name,
            "kind": source.kind,
            "origin_url": source.origin_url,
            "status": source.status,
            "file_count": source.file_count,
            "chunk_count": source.chunk_count,
        }, status=201)
    except ValueError as e:
        msg = str(e)
        if "not found or not public" in msg.lower():
            return JsonResponse({"error": {"code": "NOT_FOUND", "message": msg}}, status=404)
        elif "10 mb limit" in msg.lower():
            return JsonResponse({"error": {"code": "PAYLOAD_TOO_LARGE", "message": msg}}, status=413)
        else:
            return JsonResponse({"error": {"code": "VALIDATION_ERROR", "message": msg}}, status=400)
    except Exception as e:
        return JsonResponse(
            {"error": {"code": "PROCESSING_ERROR", "message": f"Failed to import GitHub repository: {str(e)}"}},
            status=502
        )

@require_http_methods(["GET", "DELETE"])
def api_source_detail(request, source_id):
    if not request.user.is_authenticated:
        return JsonResponse(
            {"error": {"code": "UNAUTHORIZED", "message": "Authentication required"}},
            status=401
        )

    try:
        source = Source.objects.get(id=source_id)
    except Source.DoesNotExist:
        return JsonResponse(
            {"error": {"code": "NOT_FOUND", "message": "Source not found"}},
            status=404
        )

    if source.owner != request.user:
        return JsonResponse(
            {"error": {"code": "FORBIDDEN", "message": "Access denied"}},
            status=403
        )

    if request.method == "DELETE":
        source.delete()
        return HttpResponse(status=204)

    # GET details
    files = SourceFile.objects.filter(source=source).order_by('path')
    files_data = [
        {
            "id": f.id,
            "path": f.path,
            "kind": f.kind,
            "language": f.language,
            "topic": f.topic,
            "page_count": f.page_count,
            "size_bytes": f.size_bytes,
            "status": f.status,
            "skip_reason": f.skip_reason,
            "chunk_count": f.chunk_count,
        }
        for f in files
    ]

    supported_count = sum(1 for f in files if f.status == 'READY')
    skipped_count = sum(1 for f in files if f.status != 'READY')

    return JsonResponse({
        "id": source.id,
        "name": source.name,
        "kind": source.kind,
        "status": source.status,
        "origin_url": source.origin_url,
        "error_message": source.error_message,
        "file_count": source.file_count,
        "chunk_count": source.chunk_count,
        "supported_count": supported_count,
        "skipped_count": skipped_count,
        "created_at": source.created_at.isoformat(),
        "files": files_data,
    }, status=200)

@require_http_methods(["GET"])
def api_source_file_detail(request, source_id, file_id):
    if not request.user.is_authenticated:
        return JsonResponse(
            {"error": {"code": "UNAUTHORIZED", "message": "Authentication required"}},
            status=401
        )

    try:
        source = Source.objects.get(id=source_id)
    except Source.DoesNotExist:
        return JsonResponse(
            {"error": {"code": "NOT_FOUND", "message": "Source not found"}},
            status=404
        )

    if source.owner != request.user:
        return JsonResponse(
            {"error": {"code": "FORBIDDEN", "message": "Access denied"}},
            status=403
        )

    try:
        source_file = SourceFile.objects.get(id=file_id, source=source)
    except SourceFile.DoesNotExist:
        return JsonResponse(
            {"error": {"code": "NOT_FOUND", "message": "Source file not found"}},
            status=404
        )

    chunks = Chunk.objects.filter(source_file=source_file).order_by('position')
    chunks_data = [
        {
            "id": c.id,
            "position": c.position,
            "text": c.text,
            "page_number": c.page_number,
            "start_line": c.start_line,
            "end_line": c.end_line,
        }
        for c in chunks
    ]

    return JsonResponse({
        "id": source_file.id,
        "source_id": source.id,
        "path": source_file.path,
        "kind": source_file.kind,
        "language": source_file.language,
        "topic": source_file.topic,
        "page_count": source_file.page_count,
        "size_bytes": source_file.size_bytes,
        "extracted_text": source_file.extracted_text,
        "status": source_file.status,
        "skip_reason": source_file.skip_reason,
        "chunk_count": source_file.chunk_count,
        "chunks": chunks_data,
    }, status=200)
