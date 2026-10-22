# Decisions Log

- 2026-10-22: Added `django.contrib.postgres` to `INSTALLED_APPS` to support Django ORM's native `HnswIndex` requirement.
- 2026-10-22: Included `VectorExtension()` in initial migration `kb/migrations/0001_initial.py` and enabled PostgreSQL Row Level Security (RLS) on all kb tables.
- 2026-10-22: Verified that Django's Supabase connection role performs read/write operations with RLS enabled without errors.
- 2026-10-22: Used `bge-small-en-v1.5` SentenceTransformer locally with singleton lazy-loading in `kb/rag/retrieval.py` for M0 seed embeddings.
- 2026-10-22: Built full in-memory ZIP ingestion for GitHub repositories (`kb/ingest/github.py`) enforcing size limits, symlink skipping, and path traversal guards.
- 2026-10-22: Implemented document extraction (PDF per page with page numbers via pypdf, DOCX via python-docx, TXT via utf-8) and code chunking with line number tracking.
- 2026-10-22: Integrated pgvector cosine distance retrieval with threshold filtering and Gemini 3.8 Flash structured JSON generation with server-side citation validation.
- 2026-10-22: Ensured user-submitted code and repository code are treated strictly as inert data without evaluation or subprocess execution.
- 2026-10-22: Enhanced mobile responsiveness down to 360px viewport widths with responsive navbar wrapping, horizontally scrollable tabs/tables, and full empty state illustrations across sources and history.

