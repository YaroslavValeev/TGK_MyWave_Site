document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('#calc-form');
  const resultEl = document.querySelector('#calc-result');
  const historyBtn = document.querySelector('#load-my-history');
  const historyEl = document.querySelector('#calc-history');

  // Базовые цены
  const PRICES = {
    packages: {
      Base: 15000,
      Pro: 25000,
      Elite: 35000
    },
    extra_set: 11000,
    pilot_hour: 3500,
    personal_clip: 7000,
    drone_session: 5000,
    merch: {
      tshirt: 4000,
      hoodie: 8000,
      poncho: 10000,
      cap: 3000,
      balance_board: 10000,
      smooth_trainer: 6000
    }
  };

  if (form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const fd = new FormData(form);
      
      // Собираем базовые параметры
      const inputs = {
        zone: fd.get('zone'),
        package: fd.get('package'),
        days: Number(fd.get('days')),
        participants: Number(fd.get('participants')),
        extra_sets: Number(fd.get('extra_sets')),
        pilot_hours: Number(fd.get('pilot_hours')),
        personal_clip: fd.has('personal_clip'),
        drone_session: fd.has('drone_session'),
        merch: fd.getAll('merch')
      };

      // Расчет стоимости
      const basePrice = PRICES.packages[inputs.package] * inputs.participants * inputs.days;
      const extraSetsPrice = inputs.extra_sets * PRICES.extra_set * inputs.participants;
      const pilotPrice = inputs.pilot_hours * PRICES.pilot_hour; // общая цена на группу
      const personalClipPrice = inputs.personal_clip ? PRICES.personal_clip * inputs.participants : 0;
      const dronePrice = inputs.drone_session ? PRICES.drone_session : 0;
      const merchPrice = inputs.merch.reduce((sum, item) => 
        sum + (PRICES.merch[item] || 0) * inputs.participants, 0);

      const total = basePrice + extraSetsPrice + pilotPrice + personalClipPrice + dronePrice + merchPrice;

      // Формируем детализацию для отображения
      const breakdown = {
        'Базовый пакет': `${basePrice.toLocaleString()} ₽`,
        'Доп. сеты': extraSetsPrice ? `${extraSetsPrice.toLocaleString()} ₽` : null,
        'Обучение пилотированию': pilotPrice ? `${pilotPrice.toLocaleString()} ₽` : null,
        'Персональный клип': personalClipPrice ? `${personalClipPrice.toLocaleString()} ₽` : null,
        'Съёмка дрона': dronePrice ? `${dronePrice.toLocaleString()} ₽` : null,
        'Мерч': merchPrice ? `${merchPrice.toLocaleString()} ₽` : null,
        'ИТОГО': `${total.toLocaleString()} ₽`
      };

      // Отображаем результат
      resultEl.innerHTML = `
        <h3>Расчет стоимости:</h3>
        <table>
          <tbody>
            ${Object.entries(breakdown)
              .filter(([_, value]) => value !== null)
              .map(([key, value]) => `
                <tr>
                  <td>${key}</td>
                  <td style="text-align: right">${value}</td>
                </tr>
              `).join('')}
          </tbody>
        </table>
      `;
      resultEl.classList.add('visible');

      // Сохраняем результат
      const phone = window.lastSubmittedPhone || '';
      fetch('/api/calculator/save', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ 
          phone,
          inputs,
          result: { total, breakdown }
        })
      });
    });
  }
  }

  if (historyBtn) {
    historyBtn.addEventListener('click', () => {
      const phone = window.lastSubmittedPhone || prompt('Введите телефон в формате +7XXXXXXXXXX') || '';
      fetch('/api/calculator/history?phone=' + encodeURIComponent(phone))
        .then(r => r.json())
        .then(data => {
          if (data.ok && data.history.length) {
            historyEl.innerHTML = `
              <h3>История расчетов:</h3>
              <div class="history-list">
                ${data.history.map(item => `
                  <div class="history-item">
                    <div class="history-date">${new Date(item.timestamp).toLocaleString()}</div>
                    <div class="history-details">
                      <strong>Пакет:</strong> ${item.inputs.package}, 
                      <strong>Дней:</strong> ${item.inputs.days}, 
                      <strong>Участников:</strong> ${item.inputs.participants}<br>
                      <strong>Итого:</strong> ${item.result.total.toLocaleString()} ₽
                    </div>
                  </div>
                `).join('')}
              </div>
            `;
          } else {
            historyEl.innerHTML = '<p>История расчетов пуста</p>';
          }
        });
    });
  }
});
});
