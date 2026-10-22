import json
import time
from django.conf import settings
from google import genai
from google.genai import types
from .prompt import SYSTEM_INSTRUCTION, build_rag_prompt

def call_gemini_rag(question_text, code_text="", retrieved_chunks=None, evidence_status="SUFFICIENT"):
    """
    Sends prompt to Gemini gemini-3.8-flash, requesting structured JSON.
    Validates and cleans chunk citations.
    """
    api_key = settings.GEMINI_API_KEY
    if not api_key or api_key == "your-gemini-api-key" or api_key == "your-key-here":
        raise ValueError("GEMINI_API_KEY is not configured in .env. Please add a valid Gemini API key.")

    client = genai.Client(api_key=api_key)
    prompt_text = build_rag_prompt(question_text, code_text, retrieved_chunks, evidence_status)

    valid_chunk_ranks = set(c['rank'] for c in (retrieved_chunks or []))

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        system_instruction=SYSTEM_INSTRUCTION,
        temperature=0.2,
    )

    max_retries = 3
    delay = 2.0
    last_error = None

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt_text,
                config=config,
            )
            raw_text = response.text.strip()
            return parse_and_validate_answer(raw_text, valid_chunk_ranks)
        except Exception as e:
            err_msg = str(e).lower()
            last_error = e
            if ("429" in err_msg or "rate limit" in err_msg or "resource_exhausted" in err_msg or
                "503" in err_msg or "unavailable" in err_msg or "high demand" in err_msg):
                if attempt < max_retries - 1:
                    time.sleep(delay)
                    delay *= 2
                    continue
                else:
                    raise ValueError("AI rate limit reached or model busy, please try again in a moment") from e
            elif "did not respond" in err_msg or "timeout" in err_msg:
                raise ValueError("The AI service did not respond. Try again.") from e
            else:
                raise e

    raise last_error

def parse_and_validate_answer(raw_json_str, valid_chunk_ranks):
    """
    Parses JSON and filters chunk citations that do not match a retrieved chunk.
    """
    # Remove any markdown wrapping if present
    cleaned = raw_json_str.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as err:
        raise ValueError(f"AI returned invalid JSON: {err}")

    # Ensure top-level structure
    explanation = data.get("explanation", [])
    if isinstance(explanation, str):
        explanation = [{"text": explanation, "chunk_numbers": []}]
    elif not isinstance(explanation, list):
        explanation = []

    bugs = data.get("bugs", [])
    if not isinstance(bugs, list):
        bugs = []

    fixes = data.get("fixes", [])
    if not isinstance(fixes, list):
        fixes = []

    # Sanitize citations
    sanitized_explanation = []
    for item in explanation:
        if isinstance(item, str):
            item = {"text": item, "chunk_numbers": []}
        raw_nums = item.get("chunk_numbers", [])
        clean_nums = [n for n in raw_nums if isinstance(n, int) and n in valid_chunk_ranks]
        sanitized_explanation.append({
            "text": item.get("text", ""),
            "chunk_numbers": clean_nums,
            "from_code_only": len(clean_nums) == 0,
        })

    sanitized_bugs = []
    for b in bugs:
        raw_nums = b.get("chunk_numbers", [])
        clean_nums = [n for n in raw_nums if isinstance(n, int) and n in valid_chunk_ranks]
        sanitized_bugs.append({
            "title": b.get("title", "Bug"),
            "detail": b.get("detail", ""),
            "line": b.get("line"),
            "chunk_numbers": clean_nums,
            "from_code_only": len(clean_nums) == 0,
        })

    sanitized_fixes = []
    for f in fixes:
        raw_nums = f.get("chunk_numbers", [])
        clean_nums = [n for n in raw_nums if isinstance(n, int) and n in valid_chunk_ranks]
        sanitized_fixes.append({
            "description": f.get("description", "Fix"),
            "code": f.get("code", ""),
            "chunk_numbers": clean_nums,
            "from_code_only": len(clean_nums) == 0,
        })

    return {
        "explanation": sanitized_explanation,
        "bugs": sanitized_bugs,
        "fixes": sanitized_fixes,
    }
