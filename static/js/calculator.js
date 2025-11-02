document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('#calc-form');
  const resultEl = document.querySelector('#calc-result');
  const historyBtn = document.querySelector('#load-my-history');
  const historyEl = document.querySelector('#calc-history');

  if (form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const fd = new FormData(form);
      const a = Number(fd.get('a') || 0);
      const b = Number(fd.get('b') || 0);
      const res = a + b; // заглушка — замените реальной формулой

      resultEl.textContent = `Результат: ${res}`;

      const phone = window.lastSubmittedPhone || ''; // подтяните откуда храните телефон
      fetch('/api/calculator/save', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ phone, inputs: {a,b}, result: {sum: res} })
      });
    });
  }

  if (historyBtn) {
    historyBtn.addEventListener('click', () => {
      const phone = window.lastSubmittedPhone || prompt('Введите телефон в формате +7XXXXXXXXXX') || '';
      fetch('/api/calculator/history?phone=' + encodeURIComponent(phone))
        .then(r => r.json())
        .then(data => {
          if (data.ok) {
            historyEl.innerHTML = '<pre>'+JSON.stringify(data.history, null, 2)+'</pre>';
          }
        });
    });
  }
});
