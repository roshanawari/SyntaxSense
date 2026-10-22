document.addEventListener('DOMContentLoaded', async () => {
  const loadingEl = document.getElementById('answer-loading');
  const containerEl = document.getElementById('answer-container');
  const evidenceBanner = document.getElementById('evidence-banner');

  try {
    const res = await fetch(`/api/questions/${QUESTION_ID}`);
    if (!res.ok) {
      loadingEl.innerHTML = '<p class="text-muted" style="color:var(--error);">Failed to load answer details.</p>';
      return;
    }

    const data = await res.json();
    loadingEl.style.display = 'none';
    containerEl.style.display = 'block';

    // 1. Evidence Banner
    renderEvidenceBanner(data.evidence_status);

    // 2. Question & Code
    document.getElementById('q-text').textContent = data.question_text || '(No question specified)';
    const langBadge = document.getElementById('q-lang');
    if (data.language) {
      langBadge.textContent = data.language;
    } else {
      langBadge.style.display = 'none';
    }

    const codeContainer = document.getElementById('q-code-container');
    const codeEl = document.getElementById('q-code');
    if (data.code && data.code.trim()) {
      codeEl.textContent = data.code;
    } else {
      codeContainer.style.display = 'none';
    }

    // 3. Answer Content (Explanation, Bugs, Fixes)
    renderAnswerContent(data.answer, data.evidence_status);

    // 4. Retrieved Chunks Panel
    renderRetrievedChunks(data.retrieved_chunks || []);

    // 5. Setup Citation Clicking
    setupCitationInteractions();

  } catch (err) {
    loadingEl.innerHTML = '<p class="text-muted" style="color:var(--error);">Network error loading question.</p>';
  }

  function renderEvidenceBanner(status) {
    if (status === 'INSUFFICIENT') {
      evidenceBanner.innerHTML = `
        <div class="state-warning" style="display:flex; align-items:center; gap:0.75rem;">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
          <div>
            <strong>Not enough evidence in your sources:</strong> None of the retrieved passages met the similarity threshold. Statements below are labeled "From the code only, not from your documents".
          </div>
        </div>
      `;
    } else if (status === 'NO_SOURCES') {
      evidenceBanner.innerHTML = `
        <div class="state-warning" style="display:flex; align-items:center; gap:0.75rem;">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
          <div>
            <strong>No sources searched:</strong> The question was analyzed from code only without grounding documents.
          </div>
        </div>
      `;
    } else {
      evidenceBanner.innerHTML = `
        <div class="state-success" style="display:flex; align-items:center; gap:0.75rem;">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
            <polyline points="22 4 12 14.01 9 11.01"></polyline>
          </svg>
          <div>
            <strong>Evidence grounded:</strong> Answers are cross-referenced with your documentation sources. Click chunk badges to view supporting passages.
          </div>
        </div>
      `;
    }
  }

  function renderAnswerContent(answer, evidenceStatus) {
    const expList = document.getElementById('explanation-list');
    const bugsList = document.getElementById('bugs-list');
    const fixesList = document.getElementById('fixes-list');

    const explanations = answer.explanation || [];
    if (explanations.length === 0) {
      expList.innerHTML = '<p class="text-muted">No explanation provided.</p>';
    } else {
      expList.innerHTML = '';
      explanations.forEach(item => {
        const div = document.createElement('div');
        div.style.padding = '0.5rem 0';
        div.style.borderBottom = '1px solid #F1F5F9';
        const citationsHtml = renderCitations(item.chunk_numbers, evidenceStatus);
        div.innerHTML = `<p style="margin:0 0 0.35rem 0;">${escapeHtml(item.text)}</p>${citationsHtml}`;
        expList.appendChild(div);
      });
    }

    const bugs = answer.bugs || [];
    if (bugs.length === 0) {
      bugsList.innerHTML = '<p class="text-muted">No bugs detected in code.</p>';
    } else {
      bugsList.innerHTML = '';
      bugs.forEach(b => {
        const div = document.createElement('div');
        div.style.padding = '0.75rem';
        div.style.background = '#FFF5F5';
        div.style.border = '1px solid #FED7D7';
        div.style.borderRadius = 'var(--radius)';
        const lineText = b.line ? `<span class="badge badge-failed" style="margin-left:0.5rem;">Line ${b.line}</span>` : '';
        const citationsHtml = renderCitations(b.chunk_numbers, evidenceStatus);

        div.innerHTML = `
          <div style="font-weight:600; color:var(--error); margin-bottom:0.25rem; display:flex; align-items:center;">
            ${escapeHtml(b.title)} ${lineText}
          </div>
          <p class="text-sm" style="margin:0 0 0.35rem 0; color:#4A5568;">${escapeHtml(b.detail)}</p>
          ${citationsHtml}
        `;
        bugsList.appendChild(div);
      });
    }

    const fixes = answer.fixes || [];
    if (fixes.length === 0) {
      fixesList.innerHTML = '<p class="text-muted">No specific fixes suggested.</p>';
    } else {
      fixesList.innerHTML = '';
      fixes.forEach(f => {
        const div = document.createElement('div');
        div.style.padding = '0.85rem';
        div.style.background = '#F0FDF4';
        div.style.border = '1px solid #BBF7D0';
        div.style.borderRadius = 'var(--radius)';
        const citationsHtml = renderCitations(f.chunk_numbers, evidenceStatus);

        let codeHtml = '';
        if (f.code && f.code.trim()) {
          codeHtml = `
            <div class="code-container" style="margin: 0.5rem 0; background: #0F172A;">
              <pre style="margin:0; padding:0.65rem;"><code style="color:#86EFAC;">${escapeHtml(f.code)}</code></pre>
            </div>
          `;
        }

        div.innerHTML = `
          <div style="font-weight:600; color:var(--success); margin-bottom:0.25rem;">
            ${escapeHtml(f.description)}
          </div>
          ${codeHtml}
          ${citationsHtml}
        `;
        fixesList.appendChild(div);
      });
    }
  }

  function renderCitations(chunkNumbers, evidenceStatus) {
    if (!chunkNumbers || chunkNumbers.length === 0) {
      const label = (evidenceStatus === 'INSUFFICIENT')
        ? 'From the code only, not from your documents'
        : 'From the code only';
      return `<span class="badge" style="background:#F1F5F9; color:#64748B; font-size:0.7rem;">${label}</span>`;
    }

    const tags = chunkNumbers.map(n => `
      <button type="button" class="btn btn-secondary btn-sm citation-btn" data-rank="${n}" style="padding:0.15rem 0.45rem; font-size:0.75rem; border-color:#93C5FD; color:#1D4ED8; font-weight:600;">
        [Chunk ${n}]
      </button>
    `).join(' ');

    return `<div style="display:flex; align-items:center; gap:0.35rem; margin-top:0.25rem;"><span class="text-sm text-muted" style="font-size:0.75rem;">Evidence:</span> ${tags}</div>`;
  }

  function renderRetrievedChunks(chunks) {
    const list = document.getElementById('retrieved-chunks-list');
    const badge = document.getElementById('chunks-count-badge');
    badge.textContent = `${chunks.length} chunks`;

    if (chunks.length === 0) {
      list.innerHTML = '<p class="text-sm text-muted">No chunks retrieved for this question.</p>';
      return;
    }

    list.innerHTML = '';
    chunks.forEach(c => {
      const card = document.createElement('div');
      card.className = 'card chunk-card';
      card.id = `chunk-card-${c.rank}`;
      card.style.padding = '0.85rem';
      card.style.marginBottom = '0.5rem';
      card.style.border = '1px solid #CBD5E1';
      card.style.transition = 'all 0.3s ease';

      const usedBadge = c.cited
        ? '<span class="badge badge-ready" style="font-size:0.65rem;">Used in answer</span>'
        : '<span class="badge" style="background:#F1F5F9; color:#64748B; font-size:0.65rem;">Retrieved</span>';

      let fileLink = escapeHtml(c.label);
      if (c.source_id && c.source_file_id) {
        fileLink = `<a href="/sources/${c.source_id}/files/${c.source_file_id}" target="_blank" style="font-weight:600; color:var(--primary);">${escapeHtml(c.label)}</a>`;
      }

      card.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.35rem;">
          <span style="font-weight:700; font-size:0.85rem; color:var(--text);">[Chunk ${c.rank}]</span>
          <div style="display:flex; gap:0.35rem; align-items:center;">
            <span class="text-sm text-muted" style="font-size:0.75rem;">score: ${c.score}</span>
            ${usedBadge}
          </div>
        </div>
        <div class="text-sm text-muted" style="margin-bottom:0.4rem; font-size:0.8rem;">
          ${fileLink}
        </div>
        <div class="code-container" style="margin:0; background:#F8FAFC; border:1px solid #E2E8F0; max-height:160px; overflow-y:auto;">
          <pre style="margin:0; padding:0.5rem;"><code style="color:#1E293B; font-size:0.8rem; white-space:pre-wrap;">${escapeHtml(c.text)}</code></pre>
        </div>
      `;
      list.appendChild(card);
    });
  }

  function setupCitationInteractions() {
    document.querySelectorAll('.citation-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const rank = btn.getAttribute('data-rank');
        const targetCard = document.getElementById(`chunk-card-${rank}`);
        if (targetCard) {
          // Highlight
          document.querySelectorAll('.chunk-card').forEach(c => {
            c.style.borderColor = '#CBD5E1';
            c.style.backgroundColor = '#FFFFFF';
          });
          targetCard.style.borderColor = '#2563EB';
          targetCard.style.backgroundColor = '#EFF6FF';
          targetCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
      });
    });
  }

  function escapeHtml(str) {
    if (!str) return '';
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
  }
});
