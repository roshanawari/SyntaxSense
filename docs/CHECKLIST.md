# CHECKLIST.md: Manual Testing Checklist

## M0: Foundation
- [x] Database setup: all tables created in Supabase (`kb_source`, `kb_sourcefile`, `kb_chunk`, `kb_question`, `kb_retrievedchunk`, `auth_user`) with pgvector and HNSW index.
- [x] Seed data: `python manage.py seed` creates demo user (`demo@example.com`) and seeded TEXT source with real embeddings.
- [x] F1 Auth: Registration creates an account and logs in; invalid passwords (< 8 chars) show validation error; duplicate email shows "Email already in use".
- [x] F1 Auth: Login with wrong password shows "Wrong email or password"; valid login succeeds and redirects to `/`.
- [x] F1 Auth: Visiting `/sources` while logged out redirects to `/login`.
- [x] F1 Auth: Logging out invalidates session and redirects to `/login`.
- [x] F2 Sources: `/sources` displays the logged-in user's real sources from Supabase.
- [x] F2 Sources: `GET /api/sources` returns JSON list of sources for authenticated user; returns 401 when logged out.
- [x] Isolation: Another user's sources never appear in `/sources` or `/api/sources`.
- [x] `python manage.py check` passes without errors.

## M1: Features (F3 - F15)
- [x] F3: Add pasted text creates Ready source in Supabase and appears in `/sources`.
- [x] F4: Upload PDF / DOCX / TXT creates Ready source; rejected for `.doc`, oversized, or empty.
- [x] F5: Add GitHub repository downloads zipball in-memory, processes supported files, shows folder tree.
- [x] F6: Processing status transitions (Processing -> Ready or Failed) and persists across restart.
- [x] F7: Delete source removes source, files, and chunks from Supabase.
- [x] F8: Document explorer shows topic, extracted text, page references, and chunks.
- [x] F9: Repository explorer shows tree, file counts, and preview with line numbers.
- [x] F10: Ask question with code and selected sources saves Question record.
- [x] F11: Grounded answer shows explanation, possible bugs, suggested fixes with chunk citations.
- [x] F12: Insufficient evidence notice displayed when similarity < threshold.
- [x] F13: Retrieved chunks inspector shows rank, scores, and text sent to Gemini.
- [x] F14: Question history lists past questions and loads saved answers even if source deleted.
- [x] F15: Code submitted is strictly inert text; no subprocess, eval, or exec runs.

## M2: Polish & Edge Cases
- [x] Responsive layout verified at 360px and 1280px.
- [x] Empty states for sources and history screens.
- [x] Rate limit handling: Gemini 429 backoff / graceful error notice.

