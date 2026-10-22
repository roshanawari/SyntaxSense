document.addEventListener('DOMContentLoaded', async () => {
  // Tab switching
  const tabs = document.querySelectorAll('.tab-btn');
  const panes = document.querySelectorAll('.tab-pane');

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      panes.forEach(p => p.classList.remove('active'));

      tab.classList.add('active');
      const targetPane = document.getElementById(tab.getAttribute('data-tab'));
      if (targetPane) targetPane.classList.add('active');
    });
  });

  // Line numbering for code block
  const codeBlock = document.getElementById('file-code-block');
  if (codeBlock && codeBlock.textContent) {
    const lines = codeBlock.textContent.split('\n');
    const numbered = lines.map((line, idx) => {
      const lineNum = String(idx + 1).padStart(4, ' ');
      return `<span style="color: #64748B; user-select: none;">${lineNum} | </span>${escapeHtml(line)}`;
    }).join('\n');
    codeBlock.innerHTML = numbered;
  }

  // Fetch chunks
  const chunksLoading = document.getElementById('chunks-loading');
  const chunksList = document.getElementById('chunks-list');

  try {
    const res = await fetch(`/api/sources/${SOURCE_ID}/files/${FILE_ID}`);
    if (!res.ok) {
      chunksLoading.innerHTML = '<p class="text-muted" style="color:var(--error);">Failed to load chunks.</p>';
      return;
    }

    const data = await res.json();
    chunksLoading.style.display = 'none';

    if (!data.chunks || data.chunks.length === 0) {
      chunksList.innerHTML = '<div class="state-box state-empty"><p class="text-muted">No chunks found for this file.</p></div>';
      return;
    }

    chunksList.innerHTML = '';
    data.chunks.forEach(c => {
      const card = document.createElement('div');
      card.className = 'card';
      card.style.marginBottom = '0.75rem';

      let rangeLabel = '';
      if (c.page_number) {
        rangeLabel = `Page ${c.page_number}`;
      } else if (c.start_line && c.end_line) {
        rangeLabel = `Lines ${c.start_line} - ${c.end_line}`;
      } else {
        rangeLabel = `Chunk #${c.position}`;
      }

      card.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
          <span style="font-weight: 600; font-size: 0.9rem;">Chunk #${c.position}</span>
          <span class="badge badge-info" style="font-size: 0.7rem;">${rangeLabel}</span>
        </div>
        <div class="code-container" style="margin: 0; background: #1E293B; max-height: 250px; overflow-y: auto;">
          <pre style="margin: 0; padding: 0.75rem;"><code style="color: #E2E8F0;">${escapeHtml(c.text)}</code></pre>
        </div>
      `;
      chunksList.appendChild(card);
    });

  } catch (err) {
    chunksLoading.innerHTML = '<p class="text-muted" style="color:var(--error);">Network error loading chunks.</p>';
  }

  function escapeHtml(str) {
    if (!str) return '';
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
  }
});
