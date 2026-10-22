document.addEventListener('DOMContentLoaded', async () => {
  const loadingEl = document.getElementById('explorer-loading');
  const containerEl = document.getElementById('explorer-container');
  const tbody = document.getElementById('files-tbody');
  const repoCounts = document.getElementById('repo-counts');

  try {
    const res = await fetch(`/api/sources/${SOURCE_ID}`);
    if (!res.ok) {
      loadingEl.innerHTML = '<p class="text-muted" style="color:var(--error);">Failed to load source details.</p>';
      return;
    }

    const data = await res.json();
    loadingEl.style.display = 'none';
    containerEl.style.display = 'block';

    if (data.kind === 'GITHUB' && repoCounts) {
      repoCounts.style.display = 'block';
      repoCounts.innerHTML = `<strong>Total:</strong> ${data.file_count} files | <strong style="color:var(--success);">Supported:</strong> ${data.supported_count} | <strong style="color:var(--warning);">Skipped:</strong> ${data.skipped_count}`;
    }

    if (!data.files || data.files.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-muted text-center" style="padding: 2rem;">No files found in this source.</td></tr>';
      return;
    }

    tbody.innerHTML = '';
    data.files.forEach(f => {
      const tr = document.createElement('tr');
      const isReady = f.status === 'READY';
      const pathHtml = isReady
        ? `<a href="/sources/${SOURCE_ID}/files/${f.id}" style="font-weight: 500;">${escapeHtml(f.path)}</a>`
        : `<span class="text-muted">${escapeHtml(f.path)}</span>`;

      const statusBadge = `<span class="badge badge-${f.status.toLowerCase()}">${f.status}</span>`;
      const topicText = isReady ? escapeHtml(f.topic || 'Document') : `<span class="text-muted text-sm">${escapeHtml(f.skip_reason || 'Skipped')}</span>`;
      const formattedSize = formatBytes(f.size_bytes);

      tr.innerHTML = `
        <td>${pathHtml}</td>
        <td><span class="badge badge-info" style="font-size:0.7rem;">${f.language || f.kind}</span></td>
        <td>${topicText}</td>
        <td>${statusBadge}</td>
        <td>${f.chunk_count}</td>
        <td class="text-muted text-sm">${formattedSize}</td>
      `;
      tbody.appendChild(tr);
    });

  } catch (err) {
    loadingEl.innerHTML = '<p class="text-muted" style="color:var(--error);">Network error loading source.</p>';
  }

  // Delete modal
  const btnDelete = document.getElementById('btn-delete-current-source');
  const modal = document.getElementById('confirm-modal');
  const modalCancel = document.getElementById('modal-cancel');
  const modalConfirm = document.getElementById('modal-confirm');

  if (btnDelete) {
    btnDelete.addEventListener('click', () => {
      modal.style.display = 'flex';
    });
  }

  if (modalCancel) {
    modalCancel.addEventListener('click', () => {
      modal.style.display = 'none';
    });
  }

  if (modalConfirm) {
    modalConfirm.addEventListener('click', async () => {
      modalConfirm.disabled = true;
      modalConfirm.textContent = 'Deleting…';

      try {
        const res = await fetch(`/api/sources/${SOURCE_ID}`, {
          method: 'DELETE',
          headers: {
            'X-CSRFToken': getCsrfToken()
          }
        });

        if (res.ok || res.status === 204) {
          window.location.href = '/sources';
        } else {
          showToast('Failed to delete source', 'error');
          modal.style.display = 'none';
          modalConfirm.disabled = false;
          modalConfirm.textContent = 'Delete';
        }
      } catch (err) {
        showToast('Network error while deleting source', 'error');
        modal.style.display = 'none';
        modalConfirm.disabled = false;
        modalConfirm.textContent = 'Delete';
      }
    });
  }

  function escapeHtml(str) {
    if (!str) return '';
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
  }

  function formatBytes(bytes) {
    if (bytes === 0 || !bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }
});
