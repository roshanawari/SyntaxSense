document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('register-form');
  const errorBox = document.getElementById('register-error');
  const btn = document.getElementById('btn-register');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    errorBox.style.display = 'none';
    errorBox.textContent = '';
    btn.disabled = true;
    btn.textContent = 'Creating account…';

    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;

    try {
      const response = await fetch('/api/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ email, password })
      });

      const data = await response.json().catch(() => ({}));

      if (response.ok) {
        window.location.href = '/';
      } else {
        const msg = data.error?.message || 'Failed to create account. Please try again.';
        errorBox.textContent = msg;
        errorBox.style.display = 'block';
        btn.disabled = false;
        btn.textContent = 'Create account';
      }
    } catch (err) {
      errorBox.textContent = 'A network error occurred. Please try again.';
      errorBox.style.display = 'block';
      btn.disabled = false;
      btn.textContent = 'Create account';
    }
  });
});
