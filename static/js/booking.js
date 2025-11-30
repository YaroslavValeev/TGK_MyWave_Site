// Логирование загрузки скрипта
console.log("[booking.js] Script loaded");
window.bookingStatus = { loaded: true, initialized: false, error: null };

function initializeBooking() {
  try {
    console.log("[booking.js] initializeBooking called");
    window.bookingStatus.initStarted = true;

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
    let currentService = 'boat';

    console.log('[booking.js] UI элементы:', {
      calendarModal: Boolean(UI.calendarModal),
      bookingDateInput: Boolean(UI.bookingDateInput),
      openBookingButtons: UI.openBookingButtons?.length || 0,
      slotButtonsContainer: Boolean(UI.slotButtonsContainer)
    });

    if (!UI.bookingDateInput || !UI.slotButtonsContainer) {
      console.warn("⚠️ Предупреждение: отсутствуют некоторые модальные элементы");
    }

    if (!UI.openBookingButtons || UI.openBookingButtons.length === 0) {
      console.warn("⚠️ Не найдены кнопки для бронирования - попытаемся продолжить");
    }

    // ==============================
    // 🔧 Служебные функции
    // ==============================
    function clearContainer(container) {
      while (container && container.firstChild) container.removeChild(container.firstChild);
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
      const modalContent = modal.querySelector('.modal-content');
      if (modalContent) {
        modalContent.scrollTop = 0;
      }
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

    // ==============================
    // 🎯 Обработчики кнопок бронирования
    // ==============================
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
        element: btn.outerHTML.substring(0, 100)
      });

      // Remove old listener if it exists
      const oldClickListener = btn._clickListener;
      if (oldClickListener) {
        btn.removeEventListener("click", oldClickListener);
      }

      // Create new click handler
      const clickHandler = (e) => {
        const shouldHandle = Boolean(modalId) || Boolean(serviceType);

        if (!shouldHandle && href && btn.tagName && btn.tagName.toLowerCase() === 'a') {
          console.log('[booking.js] Навигация по ссылке — переадресация на', href);
          return;
        }

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
          console.warn('[booking.js] Предупреждение: отсутствует modalId и serviceType');
          return;
        }

        if (serviceType) {
          currentService = serviceType;
          console.log(`[booking.js] Установлен тип сервиса: ${currentService}`);
        }

        const targetModal = modalId ? document.getElementById(modalId) : UI.calendarModal;
        if (targetModal) {
          console.log('[booking.js] Открываем модальное окно:', targetModal.id || 'calendarModal');
          showModal(targetModal);
          goToStep(1);
        } else {
          console.error('[booking.js] Ошибка: модальное окно не найдено!');
        }
      };

      // Save and register handler
      btn._clickListener = clickHandler;
      btn.addEventListener("click", clickHandler);
      console.log(`[booking.js] Обработчик добавлен для кнопки #${idx}`);
    });

    // Close modals
    UI.modalCloseButtons.forEach((btn) => {
      btn.addEventListener("click", hideAllModals);
    });

    // Close on Escape
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        hideAllModals();
      }
    });

    hideAllModals();

    function goToStep(step) {
      currentStep = step;
      if (UI.stepIndicator) {
        UI.stepIndicator.textContent = `Шаг ${step}/4`;
      }
    }

    console.log("📅 booking.js инициализирован");
    window.bookingStatus.initialized = true;

  } catch (err) {
    console.error("[booking.js] КРИТИЧЕСКАЯ ОШИБКА:", err);
    console.error("Стек:", err.stack);
    window.bookingStatus.error = {
      message: err.message,
      stack: err.stack
    };
  }
}

// Execute initialization when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener("DOMContentLoaded", initializeBooking);
  console.log("[booking.js] Registered DOMContentLoaded listener");
} else {
  console.log("[booking.js] DOM already loaded, initializing now");
  initializeBooking();
}

// Also register for window.onload as fallback
window.addEventListener('load', () => {
  console.log("[booking.js] window.onload fired");
  if (!window.bookingStatus.initialized) {
    initializeBooking();
  }
});
