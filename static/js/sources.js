document.addEventListener('DOMContentLoaded', () => {
  // Format dates in user's local time
  document.querySelectorAll('.source-created').forEach(el => {
    const utcString = el.getAttribute('data-utc');
    if (utcString) {
      try {
        const d = new Date(utcString);
        el.textContent = d.toLocaleString();
      } catch (e) {}
    }
  });

  const modal = document.getElementById('confirm-modal');
  const modalDesc = document.getElementById('modal-desc');
  const modalCancel = document.getElementById('modal-cancel');
  const modalConfirm = document.getElementById('modal-confirm');
  let targetSourceId = null;

  document.querySelectorAll('.btn-delete-source').forEach(btn => {
    btn.addEventListener('click', () => {
      targetSourceId = btn.getAttribute('data-id');
      const name = btn.getAttribute('data-name');
      modalDesc.textContent = `Are you sure you want to delete "${name}"? All files and chunks will be permanently removed.`;
      modal.style.display = 'flex';
    });
  });

  modalCancel.addEventListener('click', () => {
    modal.style.display = 'none';
    targetSourceId = null;
  });

  modalConfirm.addEventListener('click', async () => {
    if (!targetSourceId) return;

    modalConfirm.disabled = true;
    modalConfirm.textContent = 'Deleting…';

    try {
      const response = await fetch(`/api/sources/${targetSourceId}`, {
        method: 'DELETE',
        headers: {
          'X-CSRFToken': getCsrfToken()
        }
      });

      if (response.ok || response.status === 204) {
        showToast('Source deleted successfully', 'success');
        const row = document.getElementById(`source-row-${targetSourceId}`);
        if (row) row.remove();
        modal.style.display = 'none';
        // If no more rows, reload to show empty state
        const remaining = document.querySelectorAll('#sources-tbody tr');
        if (remaining.length === 0) {
          window.location.reload();
        }
      } else {
        const data = await response.json().catch(() => ({}));
        showToast(data.error?.message || 'Failed to delete source', 'error');
        modal.style.display = 'none';
      }
    } catch (err) {
      showToast('Network error while deleting source', 'error');
      modal.style.display = 'none';
    } finally {
      modalConfirm.disabled = false;
      modalConfirm.textContent = 'Delete';
      targetSourceId = null;
    }
  });
});
