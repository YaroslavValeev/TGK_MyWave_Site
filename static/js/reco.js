document.addEventListener('DOMContentLoaded', () => {
  console.log('[reco.js] Блок рекомендаций активен');

  const blocks = document.querySelectorAll('.reco-block');
  if (!blocks.length) return;

  blocks.forEach(block => {
    const items = block.querySelectorAll('.reco-item a');
    items.forEach(link => {
      link.addEventListener('click', async () => {
        const tokenResp = await fetch('/api/csrf-token', { credentials: 'same-origin' });
        const tokenData = await tokenResp.json();
        await fetch('/analytics/log', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': tokenData.csrf_token },
          credentials: 'same-origin',
          body: JSON.stringify({
            event: 'reco_click',
            context: document.body.dataset.page || 'unknown',
            label: link.textContent.trim(),
            timestamp: new Date().toISOString()
          })
        });
      });
    });

    // Лог показа блока
    fetch('/api/csrf-token', { credentials: 'same-origin' })
      .then(r => r.json())
      .then(t => fetch('/analytics/log', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': t.csrf_token },
        credentials: 'same-origin',
        body: JSON.stringify({
          event: 'reco_show',
          context: document.body.dataset.page || 'unknown',
          timestamp: new Date().toISOString()
        })
      }));
  });
});
