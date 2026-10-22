document.addEventListener('DOMContentLoaded', () => {
  // Format times in user's local timezone
  document.querySelectorAll('.question-time').forEach(el => {
    const utcStr = el.getAttribute('data-utc');
    if (utcStr) {
      try {
        const d = new Date(utcStr);
        el.textContent = d.toLocaleString();
      } catch (e) {}
    }
  });
});
