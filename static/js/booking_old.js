// Оборачиваем в try-catch для отладки
console.log("[booking.js] Script loaded (before DOMContentLoaded)");
window.bookingStatus = { loaded: true, initialized: false, error: null };

// Function to initialize booking system
async function initializeBooking() {
  window.bookingStatus.initStarted = true;

try {

// Получение свежего CSRF-токена с сервера
async function getFreshCsrfToken() {
  const resp = await fetch('/api/csrf-token', { credentials: 'same-origin' });
  const data = await resp.json();
  return data.csrf_token;
}
  console.log("[booking.js] DOMContentLoaded");
  console.log("📦 booking.js начинает инициализацию...");

  // ==============================
  // 🔧 DOM-элементы
  // ==============================
  const UI = {
    bookingDateInput: document.getElementById("bookingDateInput"),
    dateIcon: document.getElementById("dateIcon"),
    slotButtonsContainer: document.getElementById("slotButtonsContainer"),
    confirmDateBtn: document.getElementById("confirmDateBtn"),
    confirmSlotBtn: document.getElementById("confirmSlotBtn"),
    confirmContactBtn: document.getElementById("confirmContactBtn"),
    finalConfirmBtn: document.getElementById("finalConfirmBtn"),
    bookingName: document.getElementById("bookingName"),
    bookingPhone: document.getElementById("bookingPhone"),
    confirmDetails: document.getElementById("confirmDetails"),
    homeLink: document.getElementById("home-link"),
    slotSelectHidden: document.getElementById("slotSelect"),
    calendarModal: document.getElementById("modalCalendar"),
    slotsModal: document.getElementById("modalSlots"),
    contactModal: document.getElementById("modalContact"),
    confirmModal: document.getElementById("modalConfirm"),
    modalCloseButtons: document.querySelectorAll(".close-modal"),
    openBookingButtons: document.querySelectorAll("#openBookingBtn, .book-now, .btn-book"),
    toast: document.getElementById("toast"),
    stepIndicator: document.getElementById("step-indicator")
  };

  let currentStep = 1;
  let currentService = 'boat'; // По умолчанию используем лодку

  // Логируем инициализацию UI элементов
  console.log('[booking.js] UI элементы:', {
    calendarModal: Boolean(UI.calendarModal),
    bookingDateInput: Boolean(UI.bookingDateInput),
    openBookingButtons: UI.openBookingButtons?.length || 0,
    slotButtonsContainer: Boolean(UI.slotButtonsContainer)
  });

  if (!UI.bookingDateInput || !UI.slotButtonsContainer) {
    console.warn("⚠️ Предупреждение: отсутствуют некоторые модальные элементы (это нормально, если они подгружаются позже).");
    // NOTE: We do NOT return here anymore - this allows booking buttons to work even if modals aren't ready yet
  }

  // Проверяем инициализацию кнопок бронирования
  if (!UI.openBookingButtons || UI.openBookingButtons.length === 0) {
    console.warn("⚠️ Не найдены кнопки для бронирования - попытаемся продолжить");
    // NOTE: We do NOT return here - let booking initialization continue
  }

  // ==============================
  // 🔄 WebSocket для бронирования
  // ==============================
  let wsToken = '';
  let socket = null;

  // Асинхронная инициализация WebSocket (опционально, не критично для UI)
  async function initWebSocket(forcePolling = false) {
    try {
      // ВРЕМЕННО: Отключаем WebSocket чтобы не блокировать UI
      console.warn('[booking.js] WebSocket инициализация отключена');
      return;
      // Получаем свежий CSRF токен
      const token = await getFreshCsrfToken();
      wsToken = token;

      // Закрываем существующее соединение если есть
      if (socket) {
        try { socket.close(); } catch (e) { /* ignore */ }
      }

      // Создаем новое соединение с обновленным токеном
      socket = io({
        auth: { csrf_token: token },
        path: '/socket.io',
        timeout: 20000, // увеличить таймаут соединения
        transports: forcePolling ? ['polling'] : ['websocket', 'polling'],
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 5000,
        reconnectionAttempts: 5
      });

      // Обработчики событий сокета
      socket.on('connect', () => {
        console.log('WebSocket подключен');
      });

      socket.on('connect_error', async (error) => {
        try {
          console.error('Ошибка подключения WebSocket:', error && (error.message || error));
          const msg = (error && (error.message || '')).toString().toLowerCase();
          // При ошибке авторизации пробуем получить новый токен и переподключиться
          if (msg.includes('invalid csrf token')) {
            await initWebSocket(); // Рекурсивный вызов для переподключения с новым токеном
            return;
          }
          // Если это таймаут webSocket транспорта — попробуем принудительно использовать polling
          if (msg.includes('timeout')) {
            console.warn('WebSocket timeout — переключаемся на polling и переподключаемся');
            await initWebSocket(true);
            return;
          }
        } catch (e) {
          console.error('Ошибка в обработчике connect_error:', e);
        }
      });

      socket.on('disconnect', (reason) => {
        console.log('WebSocket отключен:', reason);
        if (reason === 'io server disconnect') {
          // Сервер разорвал соединение, пробуем переподключиться с новым токеном
          initWebSocket();
        }
      });

      socket.on('booking_update', (data) => {
        if (data && data.success) {
          showToast('✅ Бронирование подтверждено');
          hideAllModals();
        } else {
          showToast(`❌ Ошибка: ${data && data.error ? data.error : 'неизвестная'}`);
        }
      });

    } catch (err) {
      console.error('Ошибка при инициализации WebSocket:', err);
    }
  }

  // Запускаем инициализацию WebSocket (опционально)
  try {
    initWebSocket();
  } catch (err) {
    console.warn('[booking.js] WebSocket ошибка (не критично):', err);
  }

  // Инициализация flatpickr для выбора даты
  if (UI.bookingDateInput) {
    flatpickr(UI.bookingDateInput, {
      locale: "ru",
      minDate: "today",
      dateFormat: "Y-m-d",
      disableMobile: true,
      onChange: function(selectedDates) {
        if (selectedDates.length > 0) {
          const dateObj = selectedDates[0];
          const dateStr = dateObj.getFullYear() + '-' + String(dateObj.getMonth()+1).padStart(2, '0') + '-' + String(dateObj.getDate()).padStart(2, '0');
          console.log("Selected (local):", dateStr);
          updateSlotOptions(dateStr);
          showModal(UI.slotsModal);
        }
      }
    });
  }

  // Обработчик для иконки календаря
  if (UI.dateIcon) {
    UI.dateIcon.addEventListener("click", () => {
      if (UI.bookingDateInput._flatpickr) {
        UI.bookingDateInput._flatpickr.open();
      }
    });
  }

  // Закрытие модального окна по клику вне его
  document.addEventListener("click", (e) => {
    if (e.target.classList.contains("modal")) {
      hideAllModals();
    }
  });

  // ==============================
  // 🔧 Служебные функции
  // ==============================
  // Utility to clear a container safely
  function clearContainer(container) {
    while (container && container.firstChild) container.removeChild(container.firstChild);
  }

  function createLoadingSlots() {
    const wrap = document.createElement('div');
    wrap.className = 'loading-slots';
    const spinner = document.createElement('div');
    spinner.className = 'spinner';
    const text = document.createElement('div');
    text.className = 'text-gray-500';
    text.textContent = 'Загрузка доступных слотов...';
    wrap.appendChild(spinner);
    wrap.appendChild(text);
    return wrap;
  }

  function createErrorMessageNode(userMessage, dateStr) {
    const container = document.createElement('div');
    container.className = 'error-message';

    const icon = document.createElement('div');
    icon.className = 'error-icon';
    icon.textContent = '❌';

    const text = document.createElement('div');
    text.className = 'error-text';
    text.textContent = userMessage;

    const retry = document.createElement('button');
    retry.className = 'retry-button';
    retry.type = 'button';
    retry.textContent = 'Попробовать снова';
    retry.addEventListener('click', () => updateSlotOptions(dateStr));

    container.appendChild(icon);
    container.appendChild(text);
    container.appendChild(retry);
    return container;
  }

  function createNoSlotsNode() {
    const wrap = document.createElement('div');
    wrap.className = 'no-slots-message';
    const info = document.createElement('div');
    info.className = 'info-icon';
    info.textContent = 'ℹ️';
    const text = document.createElement('div');
    text.className = 'text-gray-500';
    text.appendChild(document.createTextNode('На выбранную дату нет доступных слотов.'));
    text.appendChild(document.createElement('br'));
    text.appendChild(document.createTextNode('Пожалуйста, выберите другую дату.'));
    wrap.appendChild(info);
    wrap.appendChild(text);
    return wrap;
  }
  let hideAllModals = () => {
    [UI.calendarModal, UI.slotsModal, UI.contactModal, UI.confirmModal].forEach((m) => {
      if (m) {
        m.classList.remove("show");
        m.style.display = "none";
      }
    });
    document.body.style.overflow = "auto";
  };

  let showModal = (modal) => {
    if (!modal) return;
    hideAllModals();
    modal.classList.remove("hidden");
    modal.classList.add("show");
    modal.style.setProperty('display', 'flex', 'important');
    document.body.style.overflow = "hidden";
    // Сбрасываем скролл модального окна
    const modalContent = modal.querySelector('.modal-content');
    if (modalContent) {
      modalContent.scrollTop = 0;
    }
    // Логгирование для отладки
    console.log(`[booking.js] modalCalendar классы:`, modal.className);
    console.log(`[booking.js] modalCalendar display:`, getComputedStyle(modal).display);
  };

  const showToast = (message) => {
    const toast = document.createElement("div");
    toast.className = "toast-success";
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
  };

  const validatePhone = (phone) => {
    // Очищаем телефон от всего кроме цифр и +
    let cleanPhone = phone.replace(/[^\d+]/g, '');
    // Преобразуем формат если нужно
    if (cleanPhone.startsWith('8')) {
        cleanPhone = '+7' + cleanPhone.substring(1);
    } else if (cleanPhone.startsWith('7')) {
        cleanPhone = '+' + cleanPhone;
    } else if (!cleanPhone.startsWith('+')) {
        cleanPhone = '+7' + cleanPhone;
    }
    // Проверяем конечный формат
    return /^\+7\d{10}$/.test(cleanPhone);
  };

  // ==============================
  // 📅 Получение слотов
  // ==============================
  async function updateSlotOptions(dateStr) {
    if (!dateStr) {
      clearContainer(UI.slotButtonsContainer);
      const div = document.createElement('div');
      div.className = 'text-gray-500';
      div.textContent = 'Пожалуйста, выберите дату';
      UI.slotButtonsContainer.appendChild(div);
      return;
    }

    try {
      clearContainer(UI.slotButtonsContainer);
      UI.slotButtonsContainer.appendChild(createLoadingSlots());
      
      // Получаем свежий CSRF токен для запроса
      const token = await getFreshCsrfToken();
      const response = await fetch(`/api/calendar/slots/${dateStr}`, {
        headers: {
          'X-CSRFToken': token
        },
        credentials: 'same-origin'
      });
      const data = await response.json();
      
      if (!response.ok) {
        const errorMessage = data.error || 'Произошла ошибка при загрузке слотов';
        console.error('Ошибка при загрузке слотов:', errorMessage);
        
  let userMessage = 'Извините, произошла ошибка при загрузке слотов. ';
        if (response.status === 400) {
          userMessage += 'Пожалуйста, проверьте выбранную дату.';
        } else if (response.status === 503 || response.status === 502) {
          userMessage += 'Сервер временно недоступен. Пожалуйста, попробуйте позже.';
        } else {
          userMessage += 'Пожалуйста, попробуйте позже или обратитесь в поддержку.';
        }
        
        clearContainer(UI.slotButtonsContainer);
        UI.slotButtonsContainer.appendChild(createErrorMessageNode(userMessage, dateStr));
        return;
      }
      
      clearContainer(UI.slotButtonsContainer);
      
      if (!Array.isArray(data) || data.length === 0) {
        UI.slotButtonsContainer.appendChild(createNoSlotsNode());
        return;
      }
      
      let hasAvailableSlots = false;
      
      data.forEach(slot => {
        if (slot.available && slot.remaining > 0) {
          hasAvailableSlots = true;
        }
        
        const button = document.createElement('button');
        button.className = `slot-btn ${slot.available ? 'available' : 'booked'}`;
        button.textContent = `${slot.time} ${slot.available ? `(Свободно: ${slot.remaining})` : '(Занято)'}`;
        button.disabled = !slot.available;
        
        if (slot.available) {
          button.addEventListener('click', () => {
            document.getElementById('selectedSlot').value = slot.time;
            goToStep(3); // Переходим к шагу 3 после выбора слота
          });
        }
        
        UI.slotButtonsContainer.appendChild(button);
      });
      
      if (!hasAvailableSlots) {
        clearContainer(UI.slotButtonsContainer);
        const div = document.createElement('div');
        div.className = 'text-gray-500';
        div.textContent = 'Нет свободных слотов на эту дату';
        UI.slotButtonsContainer.appendChild(div);
        return;
      }
      
      // Показываем модальное окно со слотами только если есть доступные слоты
      showModal(UI.slotsModal);
      setTimeout(() => {
        UI.slotsModal.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 100);
    } catch (error) {
      console.error('Ошибка загрузки слотов:', error);
      clearContainer(UI.slotButtonsContainer);
      const div = document.createElement('div');
      div.className = 'text-red-500';
      div.textContent = `Ошибка: ${error.message}`;
      UI.slotButtonsContainer.appendChild(div);
      showToast('❌ Ошибка загрузки слотов');
    }
  }

  // ==============================
  // ✅ Отправка заявки
  // ==============================
  async function submitBooking() {
    const selectedSlotInput = document.getElementById("selectedSlot");
    if (!selectedSlotInput) {
        console.error("❌ Элемент selectedSlot не найден в DOM.");
        return;
    }

    // Проверяем и форматируем дату
    const dateValue = UI.bookingDateInput.value;
    const formattedDate = dateValue ? new Date(dateValue).toISOString().split('T')[0] : '';
    
    // Проверяем и форматируем время
    const timeValue = selectedSlotInput.value;
    // Убеждаемся что время в правильном формате HH:MM
    let formattedTime = '';
    if (timeValue) {
      const timeParts = timeValue.trim().split(':');
      if (timeParts.length === 2) {
        const hours = timeParts[0].padStart(2, '0');
        const minutes = timeParts[1].padStart(2, '0');
        formattedTime = `${hours}:${minutes}`;
      }
    }

    // Валидация и форматирование телефона
    let phone = UI.bookingPhone.value.trim().replace(/[^\d+]/g, '');
    if (phone.startsWith('8')) {
        phone = '+7' + phone.substring(1);
    } else if (phone.startsWith('7')) {
        phone = '+' + phone;
    } else if (!phone.startsWith('+')) {
        phone = '+7' + phone;
    }

    // Проверяем обязательные поля перед созданием payload
    if (!formattedDate) {
        throw new Error('Пожалуйста, выберите дату');
    }
    if (!formattedTime) {
        throw new Error('Пожалуйста, выберите время');
    }
    if (!UI.bookingName.value.trim()) {
        throw new Error('Пожалуйста, введите ваше имя');
    }
    if (!phone) {
        throw new Error('Пожалуйста, введите номер телефона');
    }

    const payload = {
        date: formattedDate,
        time: formattedTime,
        name: UI.bookingName.value.trim(),
        phone: phone,
        service: currentService || 'boat',
        type: 'client'
    };

    // Отладочный вывод
    console.log('Подготовленные данные для отправки:', {
      rawDate: dateValue,
      formattedDate: formattedDate,
      rawTime: timeValue,
      formattedTime: formattedTime,
      fullPayload: payload
    });

    // Добавляем логирование
    console.log("📝 Отправляемые данные:", payload);
    if (!payload.date) console.warn("❌ Дата не указана");
    if (!payload.time) console.warn("❌ Время не указано");
    if (!payload.name) console.warn("❌ Имя не указано");
    if (!payload.phone) console.warn("❌ Телефон не указан");

    if (!validatePhone(payload.phone)) {
      showToast('❌ Введите корректный номер телефона');
      return;
    }

    try {
      const csrfToken = await getFreshCsrfToken();
      console.log("CSRF для бронирования:", csrfToken);
      
      // Расширенная валидация данных
      // Проверка даты
      if (!payload.date || !/^\d{4}-\d{2}-\d{2}$/.test(payload.date)) {
        throw new Error("Некорректный формат даты. Ожидается YYYY-MM-DD");
      }
      const bookingDate = new Date(payload.date);
      const today = new Date();
      if (bookingDate < today) {
        throw new Error("Дата бронирования не может быть в прошлом");
      }

      // Проверка времени
      if (!payload.time || !/^([01]\d|2[0-3]):([0-5]\d)$/.test(payload.time)) {
        throw new Error("Некорректный формат времени. Ожидается HH:MM");
      }

      // Проверка имени
      if (!payload.name || payload.name.length < 2) {
        throw new Error("Имя должно содержать не менее 2 символов");
      }
      if (payload.name.length > 50) {
        throw new Error("Имя слишком длинное");
      }

      // Проверка телефона
      if (!payload.phone) {
        throw new Error("Телефон не указан");
      }
      // Очищаем телефон от всего кроме цифр и +
      payload.phone = payload.phone.replace(/[^\d+]/g, '');
      // Если номер начинается с 8, заменяем на +7
      if (payload.phone.startsWith('8')) {
        payload.phone = '+7' + payload.phone.substring(1);
      }
      // Если номер начинается с 7, добавляем +
      if (payload.phone.startsWith('7')) {
        payload.phone = '+' + payload.phone;
      }
      if (!/^\+?\d{10,15}$/.test(payload.phone)) {
        throw new Error("Некорректный формат телефона");
      }

      // Проверка сервиса
      if (!payload.service) {
        payload.service = 'boat';
      }
      if (!['boat', 'gym'].includes(payload.service)) {
        throw new Error("Некорректный тип услуги");
      }

      // Проверка типа бронирования
      if (!payload.type) {
        payload.type = 'client';
      }
      if (!['client', 'admin'].includes(payload.type)) {
        throw new Error("Некорректный тип бронирования");
      }

      // Форматируем телефон (убираем всё кроме цифр и +)
      payload.phone = payload.phone.replace(/[^\d+]/g, '');
      
      const headers = {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken
      };
      
      console.log("Отправляемые данные:", {
        ...payload,
        csrf_token: csrfToken
      });
      
      // Форматируем данные для отправки
      const requestData = {
        date: payload.date,
        time: payload.time,
        name: payload.name,
        phone: payload.phone,
        service_type: payload.service,
        booking_type: payload.type,
        csrf_token: csrfToken
      };

      console.log("Подготовленные данные для отправки:", {
        rawPayload: payload,
        formattedRequest: requestData
      });

      // Получаем свежий CSRF токен перед отправкой
      const csrfResponse = await fetch('/api/csrf-token', {
          credentials: 'same-origin'
      });
      const csrfData = await csrfResponse.json();

      // Добавляем CSRF токен в данные запроса
      const requestDataWithCsrf = {
          ...requestData,
          csrf_token: csrfData.csrf_token
      };

      // Формируем окончательный запрос — отправляем только поля, которые ожидает сервер (BookingSchema)
      const finalRequestData = {
          date: payload.date,
          time: payload.time,
          name: payload.name,
          phone: payload.phone
      };

      console.log("Отправляем данные на сервер (без лишних полей):", finalRequestData);

      const response = await fetch("/api/calendar/book", {
        method: "POST",
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          // Сервер ожидает заголовок X-CSRFToken (без дефиса)
          'X-CSRFToken': csrfData.csrf_token
        },
        credentials: "same-origin",
        body: JSON.stringify(finalRequestData)
      });
      const result = await response.json();
      console.log("📩 Ответ сервера:", result);
      // Defensive: ignore any server-provided `success_view_url` to avoid
      // fetching partial HTML from the server (we use a local success modal).
      if (result && result.success_view_url) {
        console.warn('[booking.js] Ignoring server success_view_url to avoid loading server partial:', result.success_view_url);
        try { delete result.success_view_url; } catch (e) { /* ignore */ }
      }
      
      if (!response.ok) {
        // Подробная обработка ошибок от сервера
        if (result.error) {
          throw new Error(result.error);
        } else if (result.message) {
          throw new Error(result.message);
        } else if (response.status === 400) {
          throw new Error("Ошибка валидации данных");
        } else {
          throw new Error("Ошибка при создании бронирования");
        }
      }
      
      if (response.ok) {
        // Показываем локальный success-модал вместо перехода на внешнюю страницу
        try {
          // Формируем содержимое модального окна на клиенте
          const msg = result.message || 'Запись успешно создана!';
          const containerId = 'success-modal';
          let container = document.getElementById(containerId);
          if (!container) {
            container = document.createElement('div');
            container.id = containerId;
            document.body.appendChild(container);
          }

          // Базовая разметка модалки
          container.className = 'modal success-modal is-open show';
          container.style.display = 'flex';
          container.innerHTML = `
            <div class="modal-content">
              <button class="close-modal" data-action="close">×</button>
              <h3>${msg}</h3>
              <p>Дата: <strong>${payload.date}</strong></p>
              <p>Время: <strong>${payload.time}</strong></p>
              <p>Услуга: <strong>${payload.service}</strong></p>
              <div class="success-ctas">
                <button class="btn btn-primary" data-action="share">Поделиться</button>
                <button class="btn btn-secondary" data-action="close">Закрыть</button>
              </div>
            </div>
          `;

          // Сохраняем тип сервиса в data-атрибуте
          container.dataset.serviceType = payload.service || 'boat';

          // Обработчики кнопок внутри модалки
          container.querySelectorAll('[data-action]').forEach(btn => {
            btn.addEventListener('click', (ev) => {
              const action = btn.getAttribute('data-action');
              if (action === 'close') {
                container.classList.remove('is-open', 'show');
                container.classList.add('hidden');
                container.style.display = 'none';
                hideAllModals();
              } else if (action === 'share') {
                const serviceType = container.dataset.serviceType || 'boat';
                let shareText = 'Я записался на тренировку в MyWave!';
                if (serviceType === 'gym') shareText = 'Я записался на тренировку в зале MyWave!';
                if (navigator.share) {
                  navigator.share({ title: 'MyWave', text: shareText, url: location.href }).catch(() => {});
                } else if (navigator.clipboard) {
                  navigator.clipboard.writeText(location.href).then(()=> showToast('Ссылка скопирована в буфер обмена'));
                }
              }
              // Лог клика
              if (window.gtag) { gtag('event', 'success_view_cta_click', { 'event_category': 'booking', 'event_label': action }); }
              getFreshCsrfToken().then(token => {
                fetch('/analytics/log', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json', 'X-CSRFToken': token },
                  credentials: 'same-origin',
                  body: JSON.stringify({ event: 'success_view_cta_click', label: action, phone: window.lastSubmittedPhone || '' })
                }).catch(()=>{});
              });
            });
          });

          // Логирование показа
          if (window.gtag) { gtag('event', 'success_view_shown', { 'event_category': 'booking' }); }
          getFreshCsrfToken().then(token => {
            fetch('/analytics/log', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json', 'X-CSRFToken': token },
              credentials: 'same-origin',
              body: JSON.stringify({ event: 'success_view_shown', label: 'booking', phone: window.lastSubmittedPhone || '' })
            }).catch(()=>{});
          });

          // Отправляем подтверждение через WebSocket если он инициализирован и подключен
          if (socket && socket.connected) {
            socket.emit('booking_confirmed', {
              ...payload,
              csrf_token: wsToken // Добавляем текущий CSRF токен
            });
          }
        } catch (err) {
          console.error('Ошибка отображения локального success-модала:', err);
          hideAllModals();
          showToast(`✅ ${result.message || "Запись успешно создана!"}`);
          if (socket) socket.emit('booking_confirmed', payload);
        }
      } else {
        hideAllModals();
        showToast(`✅ ${result.message || "Запись успешно создана!"}`);
        if (socket) {
          socket.emit('booking_confirmed', payload);
        }
      }
      } else {
        showToast(`❌ ${result.error || result.message || "Не удалось записаться"}`);
      }
    } catch (err) {
      console.error("Ошибка отправки записи:", err);
      
      // Более информативное сообщение об ошибке
      let errorMessage = "❌ ";
      if (err.message) {
        if (err.message.includes("Failed to fetch")) {
          errorMessage += "Ошибка сети. Проверьте подключение к интернету.";
        } else {
          errorMessage += err.message;
        }
      } else {
        errorMessage += "Произошла ошибка при отправке. Повторите позже.";
      }
      
      showToast(errorMessage);
      
      // Логируем ошибку в консоль для отладки
      console.debug({
        error: err,
        payload: payload,
        url: "/api/calendar/book"
      });
    }
  }

  // ==============================
  // 🎯 Обработчики событий
  // ==============================
  console.log('[booking.js] Инициализация обработчиков кнопок...');
  
  // Инициализация обработчиков для всех кнопок бронирования
  console.log('[booking.js] Starting button loop initialization...');
  UI.openBookingButtons.forEach((btn, idx) => {
    if (!btn) {
      console.warn(`[booking.js] Кнопка с индексом ${idx} не найдена!`);
      return;
    }

    const btnText = btn.textContent.trim();
    const modalId = btn.getAttribute('data-modal');
    const serviceType = btn.getAttribute('data-service');
    const href = btn.getAttribute('href');
    const classes = btn.className;

    console.log(`[booking.js] Кнопка #${idx}:`, {
      text: btnText,
      modalId: modalId,
      serviceType: serviceType,
      href: href,
      classes: classes,
      element: btn.outerHTML
    });

    // Удаляем существующие обработчики перед добавлением нового
    const oldClickListener = btn._clickListener;
    if (oldClickListener) {
      btn.removeEventListener("click", oldClickListener);
    }

    // Создаем и сохраняем новый обработчик
    const clickHandler = (e) => {
      // If this button is intended to open a modal (has data-modal or data-service), we'll handle it.
      const shouldHandle = Boolean(modalId) || Boolean(serviceType);

      // If there's no modal/service but the element is a link, allow normal navigation.
      if (!shouldHandle && href && btn.tagName && btn.tagName.toLowerCase() === 'a') {
        console.log('[booking.js] Навигация по ссылке — переадресация на', href);
        return; // let the browser follow the link
      }

      // Otherwise prevent default and handle booking flow
      e.preventDefault();
      e.stopPropagation();

      console.log(`[booking.js] Клик по кнопке:`, {
        text: btnText,
        modalId: modalId,
        serviceType: serviceType,
        href: href,
        target: e.target,
        currentTarget: e.currentTarget
      });

      if (!shouldHandle) {
        console.warn('[booking.js] Предупреждение: отсутствует modalId и serviceType — нет действия для кнопки');
        return;
      }

      // Устанавливаем текущий сервис (если есть)
      if (serviceType) {
        currentService = serviceType;
        console.log(`[booking.js] Установлен тип сервиса: ${currentService}`);
      }

      // Настраиваем календарь в зависимости от типа услуги
      if (serviceType === 'gym') {
        console.log('[booking.js] Настройка календаря для зала');
        if (UI.bookingDateInput?._flatpickr) {
          UI.bookingDateInput._flatpickr.set('disable', [
            function(date) { return date.getDay() === 0 || date.getDay() === 6; }
          ]);
          console.log('[booking.js] Календарь настроен: выходные отключены');
        }
        if (UI.stepIndicator) UI.stepIndicator.textContent = 'Шаг 1/4 - Выбор даты тренировки';
      } else {
        console.log('[booking.js] Настройка календаря для водных активностей');
        if (UI.bookingDateInput?._flatpickr) UI.bookingDateInput._flatpickr.set('disable', []);
        if (UI.stepIndicator) UI.stepIndicator.textContent = 'Шаг 1/4 - Выбор даты катания';
      }

      // Определяем целевое модальное окно: либо по id из data-modal, либо дефолтное календарное модальное окно
      const targetModal = modalId ? document.getElementById(modalId) : UI.calendarModal;
      if (targetModal) {
        console.log('[booking.js] Открываем модальное окно:', targetModal.id || 'calendarModal');
        showModal(targetModal);
        goToStep(1);
      } else {
        console.error('[booking.js] Ошибка: модальное окно не найдено!');
      }
    };

    // Сохраняем обработчик и добавляем его
    btn._clickListener = clickHandler;
    btn.addEventListener("click", clickHandler);
  });

  if (UI.confirmDateBtn) {
    UI.confirmDateBtn.addEventListener("click", () => {
      const date = UI.bookingDateInput.value;
      if (!date) {
        showToast('❌ Выберите дату');
        return;
      }
      updateSlotOptions(date);
    });
  }

  if (UI.confirmContactBtn) {
    UI.confirmContactBtn.addEventListener("click", () => {
      if (!UI.bookingName.value.trim() || !UI.bookingPhone.value.trim()) {
        showToast('❌ Заполните все поля');
        return;
      }
      if (!validatePhone(UI.bookingPhone.value.trim())) {
        showToast('❌ Введите корректный номер телефона');
        return;
      }
      showModal(UI.confirmModal);
      // Переход к шагу подтверждения + скролл
      setTimeout(() => {
        UI.confirmModal.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 100);
    });
  }

  if (UI.finalConfirmBtn) {
    UI.finalConfirmBtn.addEventListener("click", () => {
      submitBooking();
    });
  }

  // Закрытие модальных окон
  UI.modalCloseButtons.forEach((btn) => {
    btn.addEventListener("click", hideAllModals);
  });

  // Закрытие по Escape
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      hideAllModals();
    }
  });

  // Скрываем все модальные окна при загрузке
  hideAllModals();

  // ✅ Готово к использованию
  console.log("📅 booking.js инициализирован");
  window.bookingStatus.initialized = true;

  // === UX улучшения для модалок ===
  // Карта автофокуса для модалей
  const focusMap = {
    modalCalendar: "#bookingDateInput",
    modalContact: "#bookingName"
  };

  // Автофокус при открытии модалки
  function focusModalField(modal) {
    const focusSelector = focusMap[modal.id];
    if (focusSelector) {
      const field = modal.querySelector(focusSelector);
      if (field) field.focus();
    }
  }

  // Добавляем анимацию появления/скрытия
  function animateModal(modal, show = true) {
    if (show) {
      modal.classList.remove("hidden");
      setTimeout(() => {
        modal.classList.add("show");
        focusModalField(modal);
      }, 10);
    } else {
      modal.classList.remove("show");
      setTimeout(() => {
        modal.classList.add("hidden");
      }, 300);
    }
  }

  // Переопределяем showModal/hideAllModals для анимаций
  const _showModal = showModal;
  showModal = (modal) => {
    if (!modal) return;
    hideAllModals();
    animateModal(modal, true);
  };
  hideAllModals = () => {
    [UI.calendarModal, UI.slotsModal, UI.contactModal, UI.confirmModal].forEach((m) => {
      if (m) animateModal(m, false);
    });
  };

  // Закрытие по Escape
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") hideAllModals();
  });

  // Закрытие по клику вне модального окна
  document.querySelectorAll(".modal").forEach((modal) => {
    modal.addEventListener("mousedown", (e) => {
      if (e.target === modal) hideAllModals();
    });
  });

  // Enter = "Далее" (ищем первую .btn-primary в видимой модалке)
  document.addEventListener("keydown", function(e) {
    if (e.key === "Enter") {
      const visibleModal = document.querySelector(".modal.show:not(.hidden)");
      if (visibleModal) {
        const btn = visibleModal.querySelector("button.btn-primary, button[type='submit']");
        if (btn && !btn.disabled) {
          e.preventDefault();
          btn.click();
        }
      }
    }
  });

  // Функция перехода между шагами с анимацией и фокусом
  function goToStep(step) {
    currentStep = step;
    
    // Обновляем индикатор шага
    if (UI.stepIndicator) {
      UI.stepIndicator.textContent = `Шаг ${step}/4`;
    }

    // Обновляем прогресс-бар
    const progressFill = document.getElementById("progress-fill");
    if (progressFill) {
      progressFill.style.width = `${(step / 4) * 100}%`;
    }

    // Специфичные действия для каждого шага
    switch(step) {
      case 1:
        showModal(UI.calendarModal);
        if (UI.bookingDateInput) UI.bookingDateInput.focus();
        break;
      case 2:
        showModal(UI.slotsModal);
        if (UI.slotButtonsContainer) {
          UI.slotButtonsContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        break;
      case 3:
        showModal(UI.contactModal);
        if (UI.bookingName) UI.bookingName.focus();
        break;
      case 4:
        showModal(UI.confirmModal);
        if (UI.stepIndicator) UI.stepIndicator.textContent = `Шаг 4/4`;
        // обновить прогресс-бар
        const progressFill = document.getElementById("progress-fill");
        if (progressFill) progressFill.style.width = `${(4 / 4) * 100}%`;
        break;
    }
  }

  // Инициализация при загрузке
  // goToStep(1);
  });
} catch (err) {
  console.error("[booking.js] КРИТИЧЕСКАЯ ОШИБКА:", err);
  console.error("Стек:", err.stack);
  window.bookingStatus.error = {
    message: err.message,
    stack: err.stack
  };
}

function openModal() {
  document.getElementById("modalCalendar").classList.remove("hidden");
}

// Пример: после выбора даты и времени
function setBookingDateTime(selectedDate, selectedTime) {
  const dateInput = document.getElementById('bookingDate');
  const timeInput = document.getElementById('bookingTime');
  if (dateInput) dateInput.value = selectedDate;
  if (timeInput) timeInput.value = selectedTime;
  console.log("Selected:", selectedDate, selectedTime);
}

function renderSlots(slots) {
    const container = document.getElementById("slotButtonsContainer");
    if (!container) {
        console.error("❌ slotButtonsContainer не найден в DOM");
        return;
    }
    
  clearContainer(container);

  if (!Array.isArray(slots) || slots.length === 0) {
    const p = document.createElement('p');
    p.className = 'text-center text-gray-500';
    p.textContent = 'Нет доступных слотов на эту дату';
    container.appendChild(p);
    return;
  }
    
  slots.forEach(slot => {
    const button = document.createElement('button');
    const buttonClass = slot.available ? 'btn-primary-lg' : 'btn-secondary-sm disabled';
    button.className = `slot-btn ${buttonClass}`;
    if (!slot.available) button.setAttribute('disabled', 'disabled');
    button.dataset.time = slot.time;
    button.textContent = `${slot.time} ${slot.available ? `(${slot.remaining} мест)` : '(занято)'}`;
    container.appendChild(button);
  });
    
    // Добавляем обработчики для новых кнопок
    container.querySelectorAll('.slot-btn:not(.disabled)').forEach(button => {
        button.addEventListener('click', () => {
            // Снимаем выделение со всех кнопок
            container.querySelectorAll('.slot-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            // Выделяем выбранную кнопку
            button.classList.add('active');
            // Сохраняем выбранное время
            const selectedTime = button.dataset.time;
            if (selectedTime) {
                document.getElementById('selectedSlot').value = selectedTime;
                goToStep(3); // Переходим к шагу 3 после выбора слота
            }
        });
    });

    // Переходим к шагу 2 после отрисовки слотов
    goToStep(2);
}