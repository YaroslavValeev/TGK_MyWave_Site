// reco.js — module that fetches recommendations and renders them into .reco-grid

const MW = (() => {
  const analyticsEndpoint = '/analytics/log';
  const recoEndpoint = '/api/reco';

  function sessionId() {
    let s = localStorage.getItem('mw_session');
    if (!s) {
      s = 's_' + Math.random().toString(36).slice(2, 10);
      localStorage.setItem('mw_session', s);
    }
    return s;
  }

  async function postAnalytics(payload) {
    try {
      await fetch(analyticsEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        credentials: 'same-origin'
      });
    } catch (e) {
      // ignore
      console.debug('analytics post failed', e);
    }
  }

  function renderCard(item) {
    const el = document.createElement('div');
    el.className = 'reco-card';
    el.dataset.itemId = item.id;
    el.innerHTML = `
      ${item.image ? `<img src="${item.image}" alt="${item.title||''}">` : ''}
      <div class="title">${item.title || ''}</div>
    `;
    el.addEventListener('click', () => {
      postAnalytics({ event: 'reco_click', item_id: item.id, type: item.type, user_key: sessionId(), context: 'client' });
    });
    return el;
  }

  async function loadForGrid(grid) {
    const context = grid.dataset.context || 'index';
    const url = `${recoEndpoint}?context=${encodeURIComponent(context)}`;
    try {
      const res = await fetch(url, { credentials: 'same-origin' });
      if (res.status === 204) return;
      const items = await res.json();
      if (!Array.isArray(items) || items.length === 0) return;
      // render
      items.forEach(it => {
        grid.appendChild(renderCard(it));
      });
      // log show event
      postAnalytics({ event: 'reco_show', item_count: items.length, user_key: sessionId(), context });
    } catch (e) {
      console.debug('Failed to load recommendations', e);
    }
  }

  function init() {
    document.querySelectorAll('.reco-grid').forEach(grid => {
      loadForGrid(grid);
    });
  }

  return { init };
})();

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', MW.init);
} else {
  MW.init();
}
