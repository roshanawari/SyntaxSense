document.addEventListener('DOMContentLoaded', () => {
  // Tab switching
  const tabs = document.querySelectorAll('.tab-btn');
  const panes = document.querySelectorAll('.tab-pane');
  const errorBox = document.getElementById('source-error');

  function clearError() {
    errorBox.style.display = 'none';
    errorBox.textContent = '';
  }

  function showError(msg) {
    errorBox.textContent = msg;
    errorBox.style.display = 'block';
  }

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      clearError();
      tabs.forEach(t => t.classList.remove('active'));
      panes.forEach(p => p.classList.remove('active'));

      tab.classList.add('active');
      const targetPane = document.getElementById(tab.getAttribute('data-tab'));
      if (targetPane) targetPane.classList.add('active');
    });
  });

  // 1. Paste Text form
  const formText = document.getElementById('form-add-text');
  const btnText = document.getElementById('btn-submit-text');
  formText.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearError();

    const name = document.getElementById('text-name').value.trim();
    const text = document.getElementById('text-content').value;

    if (!name || !text.trim()) {
      showError('Please provide both a name and text content.');
      return;
    }

    btnText.disabled = true;
    btnText.textContent = 'Processing…';

    try {
      const res = await fetch('/api/sources/text', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ name, text })
      });

      const data = await res.json().catch(() => ({}));
      if (res.ok) {
        window.location.href = `/sources/${data.id}`;
      } else {
        showError(data.error?.message || 'Failed to add text source');
        btnText.disabled = false;
        btnText.textContent = 'Add text source';
      }
    } catch (err) {
      showError('Network error while processing source');
      btnText.disabled = false;
      btnText.textContent = 'Add text source';
    }
  });

  // 2. Upload File form
  const formFile = document.getElementById('form-add-file');
  const btnFile = document.getElementById('btn-submit-file');
  formFile.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearError();

    const fileInput = document.getElementById('file-upload');
    const file = fileInput.files[0];

    if (!file) {
      showError('Please select a file to upload.');
      return;
    }

    const lowerName = file.name.toLowerCase();
    if (lowerName.endsWith('.doc')) {
      showError('Legacy .doc format is not supported. Please convert your file to .docx or .pdf.');
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      showError('Uploaded file exceeds 5 MB limit');
      return;
    }

    if (file.size === 0) {
      showError('Uploaded file is empty');
      return;
    }

    btnFile.disabled = true;
    btnFile.textContent = 'Processing… (Extracting & Chunking)';

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('/api/sources/upload', {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCsrfToken()
        },
        body: formData
      });

      const data = await res.json().catch(() => ({}));
      if (res.ok) {
        window.location.href = `/sources/${data.id}`;
      } else {
        showError(data.error?.message || 'Failed to process uploaded file');
        btnFile.disabled = false;
        btnFile.textContent = 'Upload and process';
      }
    } catch (err) {
      showError('Network error while uploading file');
      btnFile.disabled = false;
      btnFile.textContent = 'Upload and process';
    }
  });

  // 3. GitHub form
  const formGithub = document.getElementById('form-add-github');
  const btnGithub = document.getElementById('btn-submit-github');
  formGithub.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearError();

    const url = document.getElementById('github-url').value.trim();
    if (!url) {
      showError('Please enter a GitHub repository URL.');
      return;
    }

    btnGithub.disabled = true;
    btnGithub.textContent = 'Processing… (Downloading zip & embedding supported files)';

    try {
      const res = await fetch('/api/sources/github', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ url })
      });

      const data = await res.json().catch(() => ({}));
      if (res.ok) {
        window.location.href = `/sources/${data.id}`;
      } else {
        showError(data.error?.message || 'Failed to import GitHub repository');
        btnGithub.disabled = false;
        btnGithub.textContent = 'Import repository';
      }
    } catch (err) {
      showError('Network error while importing repository');
      btnGithub.disabled = false;
      btnGithub.textContent = 'Import repository';
    }
  });
});
