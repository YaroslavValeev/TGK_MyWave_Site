/* static/js/booking.js
   Единственный фронтенд-источник правды для модалок бронирования.
   Триггеры:
   - #openBookingBtn (главная кнопка)
   - [data-booking="1"] (любой элемент)
   - .btn-book, .book-now (legacy)
*/

(function () {
  const BookingUI = {};
  const state = {
    serviceType: "gym", // gym | boat
    date: null,         // YYYY-MM-DD
    time: null,         // HH:MM
    fp: null,           // flatpickr instance (optional)
    inited: false,
  };

  function $(id) { return document.getElementById(id); }

  function normalizeServiceType(v) {
    const s = String(v || "").trim().toLowerCase();
    if (["boat", "катер", "wakeboat"].includes(s)) return "boat";
    return "gym";
  }

  function isBoatSeason(dateObj) {
    // Разрешено: 1 мая — 29 сентября (в пределах выбранного года)
    const y = dateObj.getFullYear();
    const start = new Date(y, 4, 1, 0, 0, 0);      // May=4
    const end = new Date(y, 8, 29, 23, 59, 59);    // Sep=8
    return dateObj >= start && dateObj <= end;
  }

  // Форматирование даты для отображения: YYYY-MM-DD -> DD.MM.YYYY
  function formatDateForDisplay(dateStr) {
    if (!dateStr) return "";
    const parts = dateStr.split("-");
    if (parts.length === 3) {
      return `${parts[2]}.${parts[1]}.${parts[0]}`;
    }
    return dateStr;
  }

  // Форматирование времени для отображения: HH:MM -> HH:MM (уже в правильном формате, но убедимся)
  function formatTimeForDisplay(timeStr) {
    if (!timeStr) return "00:00";
    // Если время уже в формате HH:MM, возвращаем как есть
    if (/^\d{2}:\d{2}$/.test(timeStr)) {
      return timeStr;
    }
    // Если формат другой, пытаемся извлечь время
    const match = timeStr.match(/(\d{2}):(\d{2})/);
    if (match) {
      return `${match[1]}:${match[2]}`;
    }
    return "00:00";
  }

  function setServiceType(serviceType) {
    state.serviceType = normalizeServiceType(serviceType);

    const badge = $("bookingServiceBadge");
    if (badge) badge.textContent = state.serviceType === "boat" ? "Катер" : "Зал";

    const hidden = $("bookingServiceType");
    if (hidden) hidden.value = state.serviceType;
  }

  function openModal(id) {
    const modal = $(id);
    if (!modal) return;
    modal.classList.remove("hidden");
    modal.classList.add("show");
    modal.setAttribute("aria-hidden", "false");
  }

  function closeModal(id) {
    const modal = $(id);
    if (!modal) return;
    modal.classList.remove("show");
    modal.classList.add("hidden");
    modal.setAttribute("aria-hidden", "true");
  }

  function closeAllBookingModals() {
    ["bookingDateModal", "bookingTimeModal", "bookingContactModal", "bookingSuccessModal"]
      .forEach(closeModal);
  }

  function showToast(message) {
    const toast = $("bookingToast");
    if (!toast) {
      // fallback (без изменений стилей проекта)
      alert(message);
      return;
    }
    toast.textContent = message;
    toast.classList.add("show");
    setTimeout(() => toast.classList.remove("show"), 10000); // 10 секунд
  }

  function resetUI() {
    state.date = null;
    state.time = null;

    const dateInput = $("bookingDatePickr");
    if (dateInput) dateInput.value = "";

    const chosen = $("selectedDateDisplay");
    if (chosen) chosen.textContent = "Дата не выбрана";

    const slots = $("slotButtonsContainer");
    if (slots) slots.innerHTML = "";

    const selectedSlotInput = $("selectedSlot");
    if (selectedSlotInput) selectedSlotInput.value = "";

    const confirmTimeBtn = $("confirmTimeBtn");
    if (confirmTimeBtn) confirmTimeBtn.disabled = true;

    const contactForm = $("bookingContactForm");
    if (contactForm) contactForm.reset();
  }

  function initDatePicker() {
    const el = $("bookingDatePickr");
    if (!el) return;

    // flatpickr (если подключён)
    if (window.flatpickr) {
      if (state.fp) {
        try { state.fp.destroy(); } catch (e) {}
        state.fp = null;
      }

      // Настройка русской локализации и формата отображения
      state.fp = window.flatpickr(el, {
        dateFormat: "Y-m-d", // Внутренний формат для логики (не меняем)
        altInput: true, // Показывать пользователю в другом формате
        altFormat: "d.m.Y", // Формат отображения: DD.MM.YYYY
        locale: "ru", // Русская локализация
        firstDayOfWeek: 1, // Неделя начинается с понедельника
        minDate: "today",
        disable: state.serviceType === "boat"
          ? [(d) => !isBoatSeason(d)]
          : [],
        onChange: function (selectedDates, dateStr) {
          if (!dateStr) return;
          onDateSelected(dateStr);
        }
      });

      return;
    }

    // fallback без flatpickr
    el.setAttribute("type", "date");
    el.setAttribute("min", new Date().toISOString().slice(0, 10));
    el.onchange = () => {
      const v = el.value;
      if (!v) return;
      const d = new Date(v + "T00:00:00");
      if (state.serviceType === "boat" && !isBoatSeason(d)) {
        el.value = "";
        showToast("Катер доступен только с 1 мая по 29 сентября.");
        return;
      }
      onDateSelected(v);
    };
  }

  async function fetchSlots(dateStr) {
    const slotsContainer = $("slotButtonsContainer");
    if (slotsContainer) {
      slotsContainer.innerHTML = '<div class="loading-indicator">Загрузка слотов...</div>';
    }

    const url = `/api/calendar/slots/${encodeURIComponent(dateStr)}?service_type=${encodeURIComponent(state.serviceType)}`;

    let res;
    let timeoutId = null;
    try {
      // Добавляем таймаут 8 секунд для запроса
      const controller = new AbortController();
      timeoutId = setTimeout(() => controller.abort(), 8000);
      
      res = await fetch(url, { 
        method: "GET",
        signal: controller.signal
      });
      
      if (timeoutId) clearTimeout(timeoutId);
    } catch (e) {
      if (timeoutId) clearTimeout(timeoutId);
      renderSlots([]);
      // Различаем типы ошибок
      if (e.name === 'AbortError') {
        showToast("Превышено время ожидания ответа сервера. Пожалуйста, попробуйте позже.");
      } else if (e.message && e.message.includes('Failed to fetch')) {
        showToast("Не удалось подключиться к серверу. Проверьте подключение к интернету.");
      } else {
        showToast("Не удалось подключиться к серверу для получения слотов.");
      }
      return;
    }

    let data = null;
    try { data = await res.json(); } catch (e) {}

    if (!res.ok) {
      renderSlots([]);
      const errorMsg = (data && (data.error || data.message)) || "Не удалось получить слоты.";
      // Специальная обработка для 503 (сервис недоступен)
      if (res.status === 503) {
        showToast("Сервис временно недоступен. Пожалуйста, попробуйте позже или свяжитесь с нами по телефону.");
      } else {
        showToast(errorMsg);
      }
      return;
    }

    const slots = Array.isArray(data) ? data : (data && data.slots ? data.slots : []);
    renderSlots(slots);
  }

  function renderSlots(slots) {
    const slotsContainer = $("slotButtonsContainer");
    const selectedSlotInput = $("selectedSlot");
    const confirmTimeBtn = $("confirmTimeBtn");

    if (!slotsContainer) return;

    slotsContainer.innerHTML = "";

    if (!slots || slots.length === 0) {
      slotsContainer.innerHTML = '<p class="no-slots-message">Нет доступных слотов на выбранную дату.</p>';
      if (confirmTimeBtn) confirmTimeBtn.disabled = true;
      if (selectedSlotInput) selectedSlotInput.value = "";
      state.time = null;
      return;
    }

    slots.forEach((slot) => {
      // Поддерживаем оба формата: строки (для катера) и объекты (для зала)
      const timeStr = typeof slot === "string" ? slot : (slot.time || slot);
      const isAvailable = typeof slot === "object" ? (slot.available !== false) : true;
      const remaining = typeof slot === "object" ? (slot.remaining || 0) : 1;

      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "slot-btn";
      
      if (isAvailable) {
        btn.classList.add("available");
      } else {
        btn.disabled = true;
        btn.classList.add("disabled");
      }
      
      if (typeof slot === "object" && remaining > 0) {
        btn.textContent = `${timeStr} (Свободно: ${remaining})`;
      } else {
        btn.textContent = timeStr;
      }

      if (isAvailable) {
        btn.addEventListener("click", () => {
          // снять выделение
          slotsContainer.querySelectorAll(".slot-btn").forEach(b => b.classList.remove("selected"));
          btn.classList.add("selected");

          state.time = timeStr;
          if (selectedSlotInput) selectedSlotInput.value = timeStr;
          if (confirmTimeBtn) confirmTimeBtn.disabled = false;
        });
      }

      slotsContainer.appendChild(btn);
    });

    if (confirmTimeBtn) confirmTimeBtn.disabled = true;
    if (selectedSlotInput) selectedSlotInput.value = "";
    state.time = null;
  }

  function onDateSelected(dateStr) {
    state.date = dateStr;

    const chosen = $("selectedDateDisplay");
    if (chosen) {
      const formattedDate = formatDateForDisplay(dateStr);
      chosen.textContent = `Вы выбрали: ${formattedDate}`;
    }

    // Проверяем, открыта ли модалка из чата
    const modal = $("bookingDateModal");
    const fromChat = modal && modal.getAttribute('data-from-chat') === 'true';
    
    if (fromChat) {
      // Если открыто из чата, отправляем дату в чат и закрываем модалку
      const formattedDate = formatDateForDisplay(dateStr);
      // Используем функции чата из глобальной области
      if (window.ChatFunctions && window.ChatFunctions.appendMessage && window.ChatFunctions.sendMessageToServer) {
        window.ChatFunctions.appendMessage(formattedDate, 'user');
        window.ChatFunctions.sendMessageToServer(formattedDate);
      } else {
        // Fallback: используем прямой доступ к элементам чата
        const chatMessages = document.getElementById('chat-messages');
        if (chatMessages) {
          const message = document.createElement('div');
          message.className = 'message user';
          const content = document.createElement('div');
          content.className = 'message-content';
          content.textContent = formattedDate;
          message.appendChild(content);
          chatMessages.appendChild(message);
          chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        // Отправляем сообщение через форму чата
        const chatInput = document.getElementById('chat-input');
        if (chatInput) {
          chatInput.value = formattedDate;
          const form = chatInput.closest('form');
          if (form) {
            const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
            form.dispatchEvent(submitEvent);
          }
        }
      }
      closeModal("bookingDateModal");
      modal.removeAttribute('data-from-chat');
      // Очищаем глобальные функции
      if (window.ChatFunctions) {
        delete window.ChatFunctions;
      }
      return;
    }

    // Обычный флоу: закрываем модалку даты и открываем модалку времени
    closeModal("bookingDateModal");
    openModal("bookingTimeModal");

    fetchSlots(dateStr);
  }

  function onConfirmTime() {
    if (!state.date) {
      showToast("Сначала выберите дату.");
      return;
    }
    if (!state.time) {
      showToast("Сначала выберите слот времени.");
      return;
    }
    closeModal("bookingTimeModal");
    openModal("bookingContactModal");

    const nameEl = $("bookingName");
    if (nameEl) nameEl.focus();
  }

  async function submitBooking(evt) {
    evt.preventDefault();

    const name = ($("bookingName")?.value || "").trim();
    const phone = ($("bookingPhone")?.value || "").trim();

    if (!state.date || !state.time) {
      showToast("Не выбраны дата/время.");
      return;
    }
    if (!name || !phone) {
      showToast("Заполните имя и телефон/Telegram.");
      return;
    }

    // UI-валидация катера (дублируем, на всякий случай)
    if (state.serviceType === "boat") {
      const d = new Date(state.date + "T00:00:00");
      if (!isBoatSeason(d)) {
        showToast("Катер доступен только с 1 мая по 29 сентября.");
        return;
      }
    }

    const payload = {
      date: state.date,
      time: state.time,
      name,
      phone,
      service_type: state.serviceType
    };

    const headers = { "Content-Type": "application/json" };
    const csrfMeta = document.querySelector('meta[name="csrf-token"]');
    const csrf = csrfMeta?.content;
    if (csrf) headers["X-CSRFToken"] = csrf;

    let res;
    let data = null;

    try {
      res = await fetch("/api/calendar/book", {
        method: "POST",
        headers,
        body: JSON.stringify(payload)
      });
      try { data = await res.json(); } catch (e) {}
    } catch (e) {
      showToast("Сеть недоступна. Не удалось отправить бронь.");
      return;
    }

    if (!res.ok) {
      showToast((data && (data.error || data.message)) || "Ошибка бронирования.");
      return;
    }

    closeModal("bookingContactModal");

    const msg = $("successMessage");
    if (msg) {
      const serviceLabel = state.serviceType === "boat" ? "катер" : "зал";
      const formattedDate = formatDateForDisplay(state.date);
      const formattedTime = formatTimeForDisplay(state.time);
      
      // Формируем сообщение с дополнительной информацией
      let messageHTML = `<strong>✅ Ваша запись подтверждена!</strong><br><br>`;
      messageHTML += `<strong>Услуга:</strong> ${serviceLabel === "катер" ? "Катер" : "Зал"}<br>`;
      messageHTML += `<strong>Дата и время:</strong> ${formattedDate} ${formattedTime}<br><br>`;
      
      // Добавляем информацию о зале, если это зал
      if (serviceLabel === "зал") {
        messageHTML += `📍 <strong>Адрес:</strong> 3-й Хорошевский проезд<br><br>`;
      }
      
      messageHTML += `💪 Будьте в спортивной форме и хорошем настроении!<br><br>`;
      messageHTML += `Для уточнения деталей свяжись с нами или напиши в чат или посмотри FAQ.`;
      
      msg.innerHTML = messageHTML;
    }

    openModal("bookingSuccessModal");
  }

  function bindModalControls() {
    $("confirmDateBtn")?.addEventListener("click", () => {
      // Проверяем, открыта ли модалка из чата
      const modal = $("bookingDateModal");
      const fromChat = modal && modal.getAttribute('data-from-chat') === 'true';
      
      // При использовании altInput, оригинальный input содержит значение в формате dateFormat (Y-m-d)
      let v = $("bookingDatePickr")?.value;
      // Если используется flatpickr с altInput, получаем значение из instance
      if (state.fp && state.fp.selectedDates && state.fp.selectedDates.length > 0) {
        const selectedDate = state.fp.selectedDates[0];
        // Форматируем в Y-m-d для внутренней логики
        const year = selectedDate.getFullYear();
        const month = String(selectedDate.getMonth() + 1).padStart(2, '0');
        const day = String(selectedDate.getDate()).padStart(2, '0');
        v = `${year}-${month}-${day}`;
      }
      if (!v) {
        showToast("Выберите дату.");
        return;
      }
      
      // Если открыто из чата, отправляем дату в чат
      if (fromChat) {
        // Форматируем дату для чата (ДД.ММ.ГГГГ)
        const formattedDate = formatDateForDisplay(v);
        // Ищем функции чата в глобальной области
        const chatMessages = document.getElementById('chat-messages');
        if (chatMessages) {
          // Добавляем сообщение пользователя
          const message = document.createElement('div');
          message.className = 'message user';
          const content = document.createElement('div');
          content.className = 'message-content';
          content.textContent = formattedDate;
          message.appendChild(content);
          chatMessages.appendChild(message);
          chatMessages.scrollTop = chatMessages.scrollHeight;
          
          // Отправляем сообщение на сервер
          // Ищем функцию sendMessageToServer в замыкании чата
          // Используем событие для отправки
          const chatInput = document.getElementById('chat-input');
          if (chatInput) {
            // Временно устанавливаем значение и отправляем
            const originalValue = chatInput.value;
            chatInput.value = formattedDate;
            const form = chatInput.closest('form');
            if (form) {
              const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
              form.dispatchEvent(submitEvent);
            }
            chatInput.value = originalValue;
          }
        }
        // Закрываем модалку
        closeModal("bookingDateModal");
        modal.removeAttribute('data-from-chat');
        return;
      }
      
      // Обычный флоу
      onDateSelected(v);
    });

    $("confirmTimeBtn")?.addEventListener("click", onConfirmTime);

    $("backToTimeBtn")?.addEventListener("click", () => {
      closeModal("bookingTimeModal");
      openModal("bookingDateModal");
    });

    const backToTimeBtn2 = document.getElementById("backToTimeBtn2");
    if (backToTimeBtn2) {
      backToTimeBtn2.addEventListener("click", () => {
        closeModal("bookingContactModal");
        openModal("bookingTimeModal");
      });
    }

    $("bookingContactForm")?.addEventListener("submit", submitBooking);

    $("closeSuccessModal")?.addEventListener("click", () => {
      closeAllBookingModals();
      resetUI();
    });

    document.querySelectorAll("[data-modal-close]")?.forEach((btn) => {
      btn.addEventListener("click", () => {
        closeAllBookingModals();
        resetUI();
      });
    });

    // Закрытие по ESC
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        closeAllBookingModals();
        resetUI();
      }
    });

    // Закрытие по клику на фон модалки
    document.querySelectorAll(".modal")?.forEach((m) => {
      m.addEventListener("click", (e) => {
        if (e.target === m) {
          closeAllBookingModals();
          resetUI();
        }
      });
    });
  }

  function guessServiceTypeFromButton(btn) {
    const fromData = btn?.dataset?.serviceType;
    if (fromData) return normalizeServiceType(fromData);

    // fallback: если кнопка внутри #boat-card — это катер
    if (btn && btn.closest && btn.closest("#boat-card")) return "boat";

    return "gym";
  }

  function bindTriggers() {
    document.addEventListener("click", (e) => {
      // Проверяем клик по кнопке или её дочерним элементам
      const btn = e.target.closest('[data-booking="1"], #openBookingBtn, .book-now, .btn-book');
      if (!btn) return;

      e.preventDefault();
      e.stopPropagation();
      const st = guessServiceTypeFromButton(btn);
      BookingUI.open(st);
    });
  }

  BookingUI.init = function () {
    if (state.inited) return;
    state.inited = true;

    // модалки могут быть не на всех страницах — init должен быть "тихим"
    bindTriggers();
    bindModalControls();
  };

  BookingUI.open = function (serviceType = "gym") {
    setServiceType(serviceType);
    resetUI();
    initDatePicker();
    const modal = $("bookingDateModal");
    if (!modal) {
      showToast("Ошибка: модальное окно не найдено. Обновите страницу.");
      return;
    }
    openModal("bookingDateModal");
  };

  // Экспорт
  window.BookingUI = BookingUI;

  // Авто-init
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", BookingUI.init);
  } else {
    BookingUI.init();
  }
})();
