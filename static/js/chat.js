document.addEventListener("DOMContentLoaded", () => {
    // Собираем UI-элементы
    const UI = {
        sendButton: document.getElementById("sendBtn"),
        userInput: document.getElementById("user-input"),
        chatWindow: document.getElementById("chatWindow"),
        fileUpload: document.getElementById("file-upload"),
        progressBar: document.getElementById("file-upload-progress"),
        menu: document.getElementById("menu-container"),
        uploadFileBtn: document.getElementById("uploadFileBtn"),
        heroSignupBtn: document.getElementById("hero-signup-btn"),
        // Модальные окна для бронирования
        modalCalendar: document.getElementById("modalCalendar"),
        modalSlots: document.getElementById("modalSlots"),
        modalContact: document.getElementById("modalContact"),
        modalConfirm: document.getElementById("modalConfirm"),
        confirmDateBtn: document.getElementById("confirmDateBtn"),
        confirmSlotBtn: document.getElementById("confirmSlotBtn"),
        confirmContactBtn: document.getElementById("confirmContactBtn"),
        finalConfirmBtn: document.getElementById("finalConfirmBtn"),
        bookingDateInput: document.getElementById("bookingDate"),
        slotSelect: document.getElementById("slotSelect"),
        bookingName: document.getElementById("bookingName"),
        bookingPhone: document.getElementById("bookingPhone"),
        confirmDetails: document.getElementById("confirmDetails"),
        // Кнопки отмены
        cancelModal1: document.getElementById("cancelModal1"),
        cancelModal2: document.getElementById("cancelModal2"),
        cancelModal3: document.getElementById("cancelModal3"),
        cancelModal4: document.getElementById("cancelModal4")
    };

    let socket;
    if (typeof io !== "undefined") {
        socket = io();
    }

    const Utils = {
        getTime: () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        scrollChat: () => {
            if (UI.chatWindow) {
                UI.chatWindow.scrollTo({ top: UI.chatWindow.scrollHeight, behavior: "smooth" });
            }
        },
        createMessage: (text, type = "bot") => {
            const div = document.createElement("div");
            div.className = `message ${type}`;
            div.innerHTML = `<strong>${type === "user" ? "Вы" : "Эксперт"}:</strong> ${text} <small>${Utils.getTime()}</small>`;
            return div;
        },
        showModal: (elem) => { elem.classList.remove("hidden"); },
        hideModal: (elem) => { elem.classList.add("hidden"); }
    };

    // Функция отправки сообщения в чате
    async function sendMessage() {
        if (!UI.userInput || !UI.chatWindow) return;
        const message = UI.userInput.value.trim();
        if (!message) {
            alert("Введите сообщение.");
            return;
        }
        UI.chatWindow.appendChild(Utils.createMessage(message, "user"));
        UI.sendButton.disabled = true;
        UI.userInput.value = "";
        const loadingElem = Utils.createMessage("пишу...", "loading");
        UI.chatWindow.appendChild(loadingElem);
        Utils.scrollChat();
        try {
            if (!navigator.onLine) throw new Error("Нет интернет-соединения");
            const response = await fetch("/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message })
            });
            const data = await response.json();
            if (!response.ok || data.error) {
                throw new Error(data.error || `Ошибка сервера: ${response.status}`);
            }
            UI.chatWindow.appendChild(Utils.createMessage(data.reply, "bot"));
        } catch (error) {
            const errorElem = Utils.createMessage(error.message, "error");
            errorElem.style.color = "red";
            UI.chatWindow.appendChild(errorElem);
        } finally {
            loadingElem.remove();
            UI.sendButton.disabled = false;
            Utils.scrollChat();
        }
    }

    // Функция загрузки файлов
    function validateFile(file) {
        const maxSize = 10 * 1024 * 1024;
        if (file.size > maxSize) {
            throw new Error("Файл слишком большой. Максимальный размер - 10 МБ.");
        }
    }
    async function uploadMedia() {
        if (!UI.fileUpload) return;
        const file = UI.fileUpload.files[0];
        if (!file) return;
        try {
            validateFile(file);
            const formData = new FormData();
            formData.append("file", file);
            const response = await fetch("/upload", {
                method: "POST",
                body: formData
            });
            if (!response.ok) throw new Error("Ошибка загрузки файла");
            const data = await response.json();
            alert(`Файл успешно загружен! ID: ${data.file_id}`);
        } catch (error) {
            console.error("Ошибка загрузки:", error);
            alert(error.message);
        }
    }

    // Меню для дополнительных функций
    function handleMenuAction(type) {
        const actions = {
            schedule: () => alert("Расписание. Функция в разработке."),
            faq: () => alert("FAQ. Функция в разработке."),
            training: () => alert("Запись на тренировку. Функция в разработке.")
        };
        if (actions[type]) {
            actions[type]();
        } else {
            alert(`Функция "${type}" в разработке`);
        }
    }

    // Пошаговый процесс бронирования
    let bookingData = { date: null, slot: null, name: "", phone: "" };
    function openBookingFlow() {
        bookingData = { date: null, slot: null, name: "", phone: "" };
        Utils.showModal(UI.modalCalendar);
    }
    function confirmDate() {
        const dateVal = UI.bookingDateInput.value;
        if (!dateVal) {
            alert("Выберите дату!");
            return;
        }
        bookingData.date = dateVal;
        Utils.hideModal(UI.modalCalendar);
        Utils.showModal(UI.modalSlots);
    }
    function confirmSlot() {
        const slotVal = UI.slotSelect.value;
        if (!slotVal) {
            alert("Выберите слот!");
            return;
        }
        bookingData.slot = slotVal;
        Utils.hideModal(UI.modalSlots);
        Utils.showModal(UI.modalContact);
    }
    function confirmContact() {
        const nameVal = UI.bookingName.value.trim();
        const phoneVal = UI.bookingPhone.value.trim();
        if (!nameVal || !phoneVal) {
            alert("Заполните контактные данные!");
            return;
        }
        bookingData.name = nameVal;
        bookingData.phone = phoneVal;
        Utils.hideModal(UI.modalContact);
        UI.confirmDetails.textContent =
            `Дата: ${bookingData.date}, время: ${bookingData.slot}\n` +
            `Имя: ${bookingData.name}, контакт: ${bookingData.phone}\n\n` +
            `Нажмите "Подтвердить", чтобы забронировать слот.`;
        Utils.showModal(UI.modalConfirm);
    }
    function finalConfirm() {
        Utils.hideModal(UI.modalConfirm);
        // Интеграция с Google Calendar API через маршрут /book
        fetch("/book", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(bookingData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert("Запись подтверждена!");
                window.open("https://calendar.google.com/calendar/embed?src=9e6scivqg42qmur04tbnbinm3o%40group.calendar.google.com&ctz=Europe%2FMoscow", "_blank");
            } else {
                alert("Ошибка бронирования: " + data.error);
            }
        })
        .catch(err => {
            console.error(err);
            alert("Ошибка при бронировании.");
        });
        // Очистка данных бронирования
        UI.bookingDateInput.value = "";
        UI.bookingName.value = "";
        UI.bookingPhone.value = "";
    }
    function cancelBooking() {
        Utils.hideModal(UI.modalCalendar);
        Utils.hideModal(UI.modalSlots);
        Utils.hideModal(UI.modalContact);
        Utils.hideModal(UI.modalConfirm);
    }

    // Назначение событий
    if (UI.sendButton) {
        UI.sendButton.addEventListener("click", sendMessage);
    }
    if (UI.userInput) {
        UI.userInput.addEventListener("keypress", (e) => {
            if (e.key === "Enter") sendMessage();
        });
    }
    if (UI.fileUpload) {
        UI.fileUpload.addEventListener("change", uploadMedia);
    }
    if (UI.menu) {
        UI.menu.addEventListener("click", (e) => {
            const action = e.target.dataset.action;
            if (action) handleMenuAction(action);
        });
    }
    if (UI.uploadFileBtn) {
        UI.uploadFileBtn.addEventListener("click", () => {
            if (UI.fileUpload) UI.fileUpload.click();
        });
    }
    // Кнопки "Записаться" в геро-блоке и услугах
    const bookButtons = document.querySelectorAll(".btn-book");
    bookButtons.forEach(btn => {
        btn.addEventListener("click", openBookingFlow);
    });
    if (UI.heroSignupBtn) {
        UI.heroSignupBtn.addEventListener("click", openBookingFlow);
    }
    // Обработчики модальных окон
    if (UI.confirmDateBtn) UI.confirmDateBtn.addEventListener("click", confirmDate);
    if (UI.confirmSlotBtn) UI.confirmSlotBtn.addEventListener("click", confirmSlot);
    if (UI.confirmContactBtn) UI.confirmContactBtn.addEventListener("click", confirmContact);
    if (UI.finalConfirmBtn) UI.finalConfirmBtn.addEventListener("click", finalConfirm);
    if (UI.cancelModal1) UI.cancelModal1.addEventListener("click", cancelBooking);
    if (UI.cancelModal2) UI.cancelModal2.addEventListener("click", cancelBooking);
    if (UI.cancelModal3) UI.cancelModal3.addEventListener("click", cancelBooking);
    if (UI.cancelModal4) UI.cancelModal4.addEventListener("click", cancelBooking);

    // Socket.io (пример)
    if (socket) {
        socket.on('message', (data) => {
            if (data && data.reply) {
                UI.chatWindow.appendChild(Utils.createMessage(data.reply, "bot"));
                Utils.scrollChat();
            }
        });
    }

    // Пример установки прогресс-бара на 50%
    const barElem = document.querySelector("#file-upload-progress .bar");
    if (barElem) {
        barElem.style.width = "50%";
    }
});
