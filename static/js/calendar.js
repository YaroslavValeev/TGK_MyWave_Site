// static/js/calendar.js
// Клиент для получения доступных слотов с Flask backend

function fetchSlots(selectedDate) {
  fetch('/api/calendar/slots?date=' + selectedDate)
    .then(res => res.json())
    .then(renderSlots)
    .catch(console.error);
}

// Функция для рендера слотов (пример)
function renderSlots(slots) {
  // Здесь ваш код для отображения слотов на странице
  console.log('Доступные слоты:', slots);
}

// Пример использования:
// fetchSlots('2024-06-01'); 