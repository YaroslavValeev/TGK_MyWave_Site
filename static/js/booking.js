document.addEventListener("DOMContentLoaded", () => {
// Получение свежего CSRF-токена с сервера
async function getFreshCsrfToken() {
  const resp = await fetch('/api/csrf-token', { credentials: 'same-origin' });
  const data = await resp.json();
  return data.csrf_token;
}
  console.log("[booking.js] DOMContentLoaded");
  const modalCalendar = document.getElementById('modalCalendar');
  const bookingDateInput = document.getElementById('bookingDateInput');
  const slotButtonsContainer = document.getElementById('slotButtonsContainer');
  if (!modalCalendar) console.warn('[booking.js] modalCalendar не найден в DOM!');
  if (!bookingDateInput) console.warn('[booking.js] bookingDateInput не найден в DOM!');
  if (!slotButtonsContainer) console.warn('[booking.js] slotButtonsContainer не найден в DOM!');
  if (!document.getElementById('modalCalendar')) return;
  console.log("📦 booking.js загружен и готов");

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

  if (!UI.bookingDateInput || !UI.slotButtonsContainer) {
    console.warn("⚠️ booking.js не может инициализироваться — отсутствуют ключевые элементы.");
    return;
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
  // 🔄 WebSocket для бронирования
  // ==============================
  // Получаем CSRF-токен из meta-тега
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';
  const socket = io({
    auth: { csrf_token: csrfToken }
  });

  socket.on('booking_update', (data) => {
    if (data.success) {
      showToast('✅ Бронирование подтверждено');
      hideAllModals();
    } else {
      showToast(`❌ Ошибка: ${data.error}`);
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
    return /^\+?\d{10,15}$/.test(phone);
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
      
      const response = await fetch(`/api/calendar/slots/${dateStr}`);
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
    const payload = {
      date: UI.bookingDateInput.value,
      time: selectedSlotInput.value,
      name: UI.bookingName.value.trim(),
      phone: UI.bookingPhone.value.trim(),
    };

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
      const headers = {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken
      };
      console.log("Заголовки fetch:", headers);
      const response = await fetch("/api/calendar/book", {
        method: "POST",
        headers,
        credentials: "same-origin",
        body: JSON.stringify(payload),
      });
      const result = await response.json();
      console.log("📩 Ответ сервера:", result);
      if (response.ok) {
        hideAllModals();
        showToast(`✅ ${result.message || "Запись успешно создана!"}`);
        socket.emit('booking_confirmed', payload);
      } else {
        showToast(`❌ ${result.error || result.message || "Не удалось записаться"}`);
      }
    } catch (err) {
      console.error("Ошибка отправки записи:", err);
      showToast("❌ Ошибка при отправке. Повторите позже.");
    }
  }

  // ==============================
  // 🎯 Обработчики событий
  // ==============================
  UI.openBookingButtons.forEach((btn, idx) => {
    if (!btn) {
      console.warn(`[booking.js] Кнопка 'Записаться' с индексом ${idx} не найдена!`);
      return;
    }
    console.log(`[booking.js] Назначаю обработчик на кнопку 'Записаться' с текстом: '${btn.textContent.trim()}'`);
    btn.addEventListener("click", () => {
      console.log(`[booking.js] Клик по кнопке 'Записаться' с текстом: '${btn.textContent.trim()}'`);
      showModal(UI.calendarModal);
      goToStep(1);
    });
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

  // ==============================
  // ✅ Готово к использованию
  // ==============================
  console.log("📅 booking.js инициализирован");

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
