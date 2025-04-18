document.addEventListener("DOMContentLoaded", () => {
  console.log("📦 booking.js загружен и готов");

  // ==============================
  // 🔧 DOM-элементы
  // ==============================
  const UI = {
    bookingDateInput: document.getElementById("bookingDateInput"),
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
    openBookingButtons: document.querySelectorAll(".book-now"),
    toast: document.getElementById("toast"),
  };

  if (!UI.bookingDateInput || !UI.slotButtonsContainer) {
    console.warn("⚠️ booking.js не может инициализироваться — отсутствуют ключевые элементы.");
    return;
  }

  function handleDateConfirmation() {
    const selectedDate = document.getElementById("bookingDateInput").value;
    if (!selectedDate) {
      alert("Пожалуйста, выберите дату!");
      return;
    }
  
    console.log("📅 Выбрана дата:", selectedDate);

    // Автоматически подтверждаем дату
    if (UI.confirmDateBtn) {
      UI.confirmDateBtn.click();
    }

    const slotsModal = document.getElementById("modalSlots");
    if (slotsModal) {
      document.querySelectorAll(".modal").forEach((m) => m.classList.add("hidden"));
      slotsModal.classList.remove("hidden");
    }
  }
  
// 🔄 Flatpickr (выбор даты)
  // ==============================
  flatpickr(UI.bookingDateInput, {
    locale: "ru",
    dateFormat: "Y-m-d",
    onChange: function (selectedDates, dateStr) {
      if (!dateStr) return;

      // 🚫 Проверяем, чтобы дата не была в прошлом
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      if (selectedDates[0] < today) {
        alert("Выберите будущую дату");
        return;
      }

      console.log("📅 Выбрана дата:", dateStr);
      updateSlotOptions(dateStr); // ✅ один вызов
    }
  });
  // ==============================
  // 🔧 Служебные функции
  // ==============================

  const hideAllModals = () => {
    [UI.calendarModal, UI.slotsModal, UI.contactModal, UI.confirmModal].forEach((m) => {
      if (m) m.classList.add("hidden");
    });
  };

  const showModal = (modal) => {
    hideAllModals();
    modal?.classList.remove("hidden");
  };

  const showToast = (message) => {
    UI.toast.textContent = message;
    UI.toast.classList.remove("hidden");
    setTimeout(() => UI.toast.classList.add("hidden"), 5000);
  };

  const setActiveSlotButton = (btn) => {
    UI.slotButtonsContainer.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
  };

  const clearSlotButtons = () => {
    UI.slotButtonsContainer.innerHTML = "";
    UI.confirmSlotBtn.disabled = true;
  };

  // ==============================
  // 📅 Получение слотов
  // ==============================
  window.updateSlotOptions = async function(dateStr) {
    clearSlotButtons();

    if (!dateStr) {
      UI.slotButtonsContainer.innerHTML = "<div class='text-gray-500'>Дата не выбрана</div>";
      return;
    }

    try {
      const res = await fetch(`/api/calendar/available_slots/${dateStr}`);
      const slotsData = await res.json();

      const date = Object.keys(slotsData)[0];
      const slots = slotsData[date];

      if (!slots || slots.length === 0) {
        UI.slotButtonsContainer.innerHTML = "<div class='text-gray-500'>На выбранную дату нет свободных слотов</div>";
        return;
      }

      // Создаем Set для хранения уникальных слотов
      const uniqueSlots = new Set();
      slots.forEach(slot => {
        const slotKey = `${slot.time}_${slot.available}_${slot.max_capacity}`;
        if (!uniqueSlots.has(slotKey)) {
          uniqueSlots.add(slotKey);
          const btn = document.createElement("button");
          btn.type = "button";
          btn.className = "slot-btn";
          btn.textContent = `${slot.time} (${slot.available}/${slot.max_capacity})`;
          btn.addEventListener("click", () => {
            UI.slotSelectHidden.value = slot.time;
            setActiveSlotButton(btn);
            UI.confirmSlotBtn.disabled = false;
            // Автоматически нажимаем кнопку подтверждения слота
            if (UI.confirmSlotBtn) {
              UI.confirmSlotBtn.click();
            }
          });
          UI.slotButtonsContainer.appendChild(btn);
        }
      });
    } catch (e) {
      console.error("Ошибка загрузки слотов:", e);
      UI.slotButtonsContainer.innerHTML = "<div class='text-red-500'>Ошибка загрузки слотов</div>";
    }
  }

  // ==============================
  // 🧾 Подтверждение контакта
  // ==============================
  function confirmContactStep() {
    const name = UI.bookingName.value.trim();
    const phone = UI.bookingPhone.value.trim();
    const time = UI.slotSelectHidden.value;
    const date = UI.bookingDateInput.value;

    if (!name || !phone || !time || !date) {
      alert("Пожалуйста, заполните все поля");
      return false;
    }

    if (!/^\+?\d{10,15}$/.test(phone)) {
      alert("Введите корректный номер телефона («+7…»).");
      return false;
    }

    UI.confirmDetails.textContent = `Дата: ${date}, Время: ${time}\nИмя: ${name}, Телефон: ${phone}`;
    return true;
  }

  // ==============================
  // ✅ Отправка заявки
  // ==============================
  async function submitBooking() {
    const payload = {
      date: UI.bookingDateInput.value,
      time: UI.slotSelectHidden.value,
      name: UI.bookingName.value.trim(),
      phone: UI.bookingPhone.value.trim(),
    };

    try {
      const res = await fetch("/booking/book/api", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": document.querySelector('meta[name="csrf-token"]')?.content || '',
        },
        body: JSON.stringify(payload),
      });

      const result = await res.json();

      if (result.success) {
        hideAllModals();
        showToast("✅ Запись успешно подтверждена");
      } else {
        showToast(`❌ Ошибка: ${result.error}`);
      }
    } catch (err) {
      console.error("Ошибка отправки записи:", err);
      showToast("❌ Ошибка при отправке. Повторите позже.");
    }
  }
  // ==============================
  // 🎯 Обработчики кнопок
  // ==============================

  UI.openBookingButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      if (btn.disabled) return;          // 🔒 защита от двойного клика
      btn.disabled = true;
      setTimeout(() => (btn.disabled = false), 1000);

      console.log("🖱️ Клик по кнопке 'Записаться'");
      showModal(UI.calendarModal);
    });
  });

  if (UI.confirmDateBtn) {
    UI.confirmDateBtn.addEventListener("click", handleDateConfirmation);
  }


  if (UI.confirmSlotBtn) {
    UI.confirmSlotBtn.addEventListener("click", () => {
      const selectedSlot = UI.slotSelectHidden.value;
      if (!selectedSlot) {
        alert("Выберите слот");
        return;
      }

      showModal(UI.contactModal);
    });
  }

  if (UI.confirmContactBtn) {
    UI.confirmContactBtn.addEventListener("click", () => {
      if (confirmContactStep()) {
        showModal(UI.confirmModal);
      }
    });
  }

  if (UI.finalConfirmBtn) {
    UI.finalConfirmBtn.addEventListener("click", () => {
      submitBooking();
    });
  }

  // ==============================
  // ❌ Закрытие модалок по ✖ кнопке
  // ==============================
  UI.modalCloseButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      hideAllModals();
    });
  });

  // ==============================
  // ⎋ Закрытие по клавише Escape
  // ==============================
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      hideAllModals();
    }
  });


  // ==============================
  // ✅ Готово к использованию
  // ==============================
  console.log("📅 booking.js инициализирован");
});
