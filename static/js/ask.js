document.addEventListener('DOMContentLoaded', async () => {
  const container = document.getElementById('sources-checkboxes');
  const notice = document.getElementById('ask-sources-notice');
  const form = document.getElementById('ask-form');
  const submitBtn = document.getElementById('btn-submit-ask');
  const errorBox = document.getElementById('ask-error-box');

  // Load user's sources
  try {
    const res = await fetch('/api/sources');
    if (res.ok) {
      const sources = await res.json();
      const readySources = sources.filter(s => s.status === 'READY');

      if (readySources.length === 0) {
        if (notice) notice.style.display = 'block';
        if (container) {
          container.innerHTML = '<span class="text-sm text-muted">No ready sources available. You can still ask questions, and the assistant will analyze your code alone.</span>';
        }
      } else {
        if (notice) notice.style.display = 'none';
        if (container) {
          container.innerHTML = '';
          readySources.forEach(s => {
            const label = document.createElement('label');
            label.style.display = 'flex';
            label.style.alignItems = 'center';
            label.style.gap = '0.5rem';
            label.style.fontSize = '0.9rem';
            label.style.cursor = 'pointer';
            label.innerHTML = `
              <input type="checkbox" name="source_ids" value="${s.id}" checked>
              <span style="font-weight: 500;">${escapeHtml(s.name)}</span>
              <span class="badge badge-info" style="font-size:0.65rem;">${s.kind}</span>
              <span class="text-sm text-muted">(${s.chunk_count} chunks)</span>
            `;
            container.appendChild(label);
          });
        }
      }
    }
  } catch (err) {
    console.error('Failed to load sources', err);
  }

  // Handle Ask form submit
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (errorBox) {
      errorBox.style.display = 'none';
      errorBox.textContent = '';
    }

    const code = document.getElementById('code-input').value;
    const question = document.getElementById('question-input').value;
    const language = document.getElementById('language-select').value;

    if (!code.trim() && !question.trim()) {
      showError('Please provide code snippet, a question, or both.');
      return;
    }

    const checkedBoxes = document.querySelectorAll('input[name="source_ids"]:checked');
    const source_ids = Array.from(checkedBoxes).map(cb => parseInt(cb.value, 10));

    submitBtn.disabled = true;
    submitBtn.textContent = 'Analyzing with Gemini… (Retrieving chunks & generating answer)';

    try {
      const response = await fetch('/api/ask', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
          code,
          question,
          language: language || null,
          source_ids
        })
      });

      const data = await response.json().catch(() => ({}));

      if (response.ok) {
        window.location.href = `/questions/${data.id}`;
      } else {
        const msg = data.error?.message || 'Failed to analyze code. Please try again.';
        showError(msg);
        submitBtn.disabled = false;
        submitBtn.textContent = 'Ask Assistant';
      }
    } catch (err) {
      showError('Network error while communicating with server. Please try again.');
      submitBtn.disabled = false;
      submitBtn.textContent = 'Ask Assistant';
    }
  });

  function showError(msg) {
    if (errorBox) {
      errorBox.textContent = msg;
      errorBox.style.display = 'block';
    } else {
      showToast(msg, 'error');
    }
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }
});
