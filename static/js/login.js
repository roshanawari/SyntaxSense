document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('login-form');
  const errorBox = document.getElementById('login-error');
  const btn = document.getElementById('btn-login');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    errorBox.style.display = 'none';
    errorBox.textContent = '';
    btn.disabled = true;
    btn.textContent = 'Logging in…';

    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;

    try {
      const response = await fetch('/api/auth/login', {
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
        const msg = data.error?.message || 'Wrong email or password';
        errorBox.textContent = msg;
        errorBox.style.display = 'block';
        btn.disabled = false;
        btn.textContent = 'Log in';
      }
    } catch (err) {
      errorBox.textContent = 'A network error occurred. Please try again.';
      errorBox.style.display = 'block';
      btn.disabled = false;
      btn.textContent = 'Log in';
    }
  });
});
