document.addEventListener("DOMContentLoaded", () => {
    // Remove daysTranslation references since we're using English format

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
        bookingDateInput: document.getElementById("dateInput"),
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

    // Добавляем корректные отступы для поля даты и контактных данных
    if (UI.bookingDateInput) {
        UI.bookingDateInput.style.padding = "8px";
        UI.bookingDateInput.style.margin = "4px 0";
    }
    if (UI.bookingName) {
        UI.bookingName.style.padding = "8px";
        UI.bookingName.style.margin = "4px 0";
    }
    if (UI.bookingPhone) {
        UI.bookingPhone.style.padding = "8px";
        UI.bookingPhone.style.margin = "4px 0";
    }
    if (UI.slotSelect) {
        UI.slotSelect.style.padding = "10px 14px";
        UI.slotSelect.style.marginBottom = "12px";
        UI.slotSelect.style.borderRadius = "8px";
        UI.slotSelect.style.border = "1px solid #ccc";
        UI.slotSelect.style.fontFamily = "Inter, sans-serif";
        UI.slotSelect.style.fontSize = "16px";
        UI.slotSelect.style.boxShadow = "0 2px 4px rgba(0, 0, 0, 0.05)";
    }

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
            // Добавляем персонализацию и рекомендации
            let replyText = data.reply;
            if (bookingData.name) {
                replyText = `Здравствуйте, ${bookingData.name}! ` + replyText;
            }
            if (message.toLowerCase().includes("тренировк")) {
                replyText += " Рекомендую тренировку по вейксерфингу — хотите записаться?";
            }
            UI.chatWindow.appendChild(Utils.createMessage(replyText, "bot"));
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
        const dateInput = document.getElementById("dateInput");
        const selectedDate = dateInput.value;
        const selectedTime = localStorage.getItem('selectedSlotTime'); // Берём время из localStorage

        if (!selectedDate) {
            alert('Выберите дату!');
            return;
        }

        bookingData.date = selectedDate;
        bookingData.slot = selectedTime;  // сразу сохраняем выбранное время

        fetch(`/calendar/available_slots/${selectedDate}`)
        .then(response => response.json())
        .then(data => {
            if (data.slots && data.slots.length > 0) {
                updateSlotOptions(data.slots);  // Заполняем select
                Utils.hideModal(UI.modalCalendar);
                Utils.showModal(UI.modalSlots);
            } else {
                alert("На эту дату нет свободных слотов.");
            }
        })
        .catch(err => {
            console.error("Ошибка загрузки слотов:", err);
            alert("Не удалось загрузить доступные слоты.");
        });
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
        fetch("/calendar/book", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                date: bookingData.date,
                time: bookingData.slot,
                name: bookingData.name,
                phone: bookingData.phone
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert("Спасибо! Ваша запись подтверждена. До встречи на тренировке! 🏄‍♂️");
                window.open(data.calendarLink, "_blank");
            } else {
                alert("Ошибка бронирования: " + data.error);
            }
        })
        .catch(err => {
            alert("Произошла ошибка, попробуйте снова.");
        });
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

    function updateSlotOptions(slots) {
        console.log("🎯 Слоты, добавляемые в select:", slots); // Проверяем, какие данные обрабатываются
        let select = document.getElementById("slotSelect");
        select.innerHTML = "";  // Очищаем список
        slots.forEach(slot => {
            let option = document.createElement("option");
            option.value = slot.time;
            option.textContent = `${slot.time} (${slot.available > 0 ? "Свободно" : "Занято"})`;
            select.appendChild(option);
        });
    }

    function updateSlotInfo(time, available) {
        document.getElementById('available-slots').textContent = available;
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
        // Изменён обработчик для отправки события gtag
        UI.heroSignupBtn.addEventListener("click", () => {
            gtag('event', 'click_signup', {
                'event_category': 'Button',
                'event_label': 'Hero Signup'
            });
            openBookingFlow();
        });
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
        socket.on('connect_error', (error) => {
            console.error("Ошибка подключения WebSocket:", error);
        });
        socket.on('message', (data) => {
            if (data && data.reply) {
                const audio = new Audio('/static/sounds/notification.mp3');
                audio.play();
                UI.chatWindow.appendChild(Utils.createMessage(data.reply, "bot"));
                Utils.scrollChat();
            }
        });
        socket.on("update_slots", (data) => {
            console.log("📊 Данные от сервера (слоты):", data);  // Проверяем, что пришло
        });
    }

    // Пример установки прогресс-бара на 50%
    const barElem = document.querySelector("#file-upload-progress .bar");
    if (barElem) {
        barElem.style.width = "50%";
    }

    // Добавляем функционал бургер-меню
    const burgerMenu = document.querySelector('.burger-menu');
    const navMenu = document.querySelector('.site-nav ul');
    if (burgerMenu && navMenu) {
        burgerMenu.addEventListener('click', () => {
            burgerMenu.classList.toggle('active');
            navMenu.classList.toggle('active');
        });
    }

    // Новый функционал: фильтрация и сортировка товаров
    const categoryFilter = document.getElementById('category-filter');
    const priceSort = document.getElementById('price-sort');
    const productCards = document.querySelectorAll('.product-card');

    if (categoryFilter && priceSort && productCards.length) {
        categoryFilter.addEventListener('change', filterProducts);
        priceSort.addEventListener('change', sortProducts);
    }

    function filterProducts() {
        const category = categoryFilter.value;
        productCards.forEach(card => {
            const productCategory = card.dataset.category || 'all';
            card.style.display = (category === 'all' || category === productCategory) ? 'block' : 'none';
        });
    }

    function sortProducts() {
        const sortOrder = priceSort.value;
        const sortedCards = Array.from(productCards).sort((a, b) => {
            const priceA = parseInt(a.querySelector('.price').textContent.replace(/[^0-9]/g, ''));
            const priceB = parseInt(b.querySelector('.price').textContent.replace(/[^0-9]/g, ''));
            return sortOrder === 'asc' ? priceA - priceB : priceB - priceA;
        });
        const storeList = document.querySelector('.store-list');
        if (storeList) {
            storeList.innerHTML = '';
            sortedCards.forEach(card => storeList.appendChild(card));
        }
    }

    // Замена жесткого обращения к chat-box с проверкой элемента
    const chatBox = document.getElementById("chat-box");
    if (chatBox) {
        chatBox.style.height = "300px";
    }

    document.addEventListener('DOMContentLoaded', function () {
        const element = document.getElementById('some_id');
        if (element) {
            element.style.display = 'none';
        }
    });
});

document.addEventListener("DOMContentLoaded", function () {
    const dateIcon = document.getElementById("dateIcon");
    const datePicker = document.getElementById("datePicker");

    if (dateIcon && datePicker) {
        dateIcon.addEventListener("click", function () {
            datePicker.showPicker(); // Для современных браузеров
            datePicker.focus();      // Для поддержки старых браузеров
        });
    }
});

document.addEventListener("DOMContentLoaded", () => {
    const slots = document.querySelectorAll(".time-slot");
    const datePickerModal = document.getElementById("modalCalendar");
    const bookingDateInput = document.getElementById("bookingDate");

    slots.forEach(slot => {
        slot.addEventListener("click", () => {
            const selectedTime = slot.textContent;
            console.log("Выбрано время:", selectedTime);
            
            // Открываем модальное окно выбора даты
            if (datePickerModal) {
                datePickerModal.classList.remove("hidden");
                bookingDateInput.focus();
                // Сохраняем выбранное время в localStorage
                localStorage.setItem('selectedSlotTime', selectedTime);
            } else {
                alert("Окно выбора даты недоступно.");
            }
        });
    });

    document.querySelectorAll(".slot").forEach(slot => {
        slot.addEventListener("click", () => {
            const time = slot.dataset.time;
            console.log("⏱ Выбран слот:", time);
            if (document.getElementById("modalCalendar")) {
                bookingData.slot = time;
                Utils.showModal(document.getElementById("modalCalendar"));
            }
        });
    });
});
