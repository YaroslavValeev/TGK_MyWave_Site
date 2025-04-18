if (window.socket && window.socket.connected) {
    window.socket.disconnect(); // 🧹 отключаем старое соединение
}
window.socket = io({ transports: ["websocket", "polling"] });
console.log("✅ chat.js успешно загружен");

document.addEventListener("DOMContentLoaded", () => {
    const chatContainer = document.getElementById("chat-container") 
                        || document.getElementById("chat-page-container");
    const chatBtn = document.getElementById("open-chat-btn");
    const chatInput = document.getElementById("chat-input")
                        || document.getElementById("user-input");
    const sendBtn = document.getElementById("send-btn")
                        || document.querySelector('#chatForm button[type="submit"]');
    const messages = document.getElementById("messages");

    // === Scroll Spy ===
    const sections = document.querySelectorAll("section[id]");
    const navLinks = document.querySelectorAll(".site-nav a");
    const homeLink = document.getElementById("nav-home-link");

    function activateNavLink() {
        let current = "";
        sections.forEach((section) => {
            const sectionTop = section.offsetTop - 120;
            if (window.scrollY >= sectionTop) {
                current = section.getAttribute("id");
            }
        });

        navLinks.forEach((link) => {
            link.classList.remove("active");
            if (link.getAttribute("href").includes(current)) {
                link.classList.add("active");
            }
        });
    }

    const calendarIcon = document.querySelector(".calendar-icon");
    const bookingInput = document.getElementById("bookingDateInput");
    if (calendarIcon && bookingInput) {
        calendarIcon.addEventListener("click", () => {
            bookingInput.focus();
            bookingInput.click();
        });
    }

    window.addEventListener("scroll", activateNavLink);

    // === Скрытие шапки при прокрутке ===
    let lastScrollTop = 0;
    const header = document.querySelector(".site-header");
    const pullTab = document.getElementById("header-pull-tab");

    window.addEventListener("scroll", function () {
        const scrollTop = window.scrollY || document.documentElement.scrollTop;

        if (scrollTop > 10) {
            header.classList.add("scrolled");
        } else {
            header.classList.remove("scrolled");
        }

        if (scrollTop > lastScrollTop && scrollTop > 100) {
            header.classList.add("hidden");
        } else {
            header.classList.remove("hidden");
        }

        lastScrollTop = Math.max(scrollTop, 0);
    });

    pullTab?.addEventListener("click", () => {
        header.classList.remove("hidden");
    });

    // 💬 Добавление сообщений
    const appendMessage = (text, isUser = false) => {
        const div = document.createElement("div");
        div.className = isUser ? "user-message" : "bot-message";
        div.textContent = text;
        messages?.appendChild(div);
        messages.scrollTop = messages.scrollHeight;
    };

    // 📌 Открытие/закрытие чата
    if (chatBtn && chatContainer) {
        chatContainer.classList.add("hidden");
        chatBtn.addEventListener("click", () => {
            chatContainer.classList.toggle("hidden");
        });
    }

    // 📤 Отправка сообщений
    if (sendBtn && chatInput && messages) {
        sendBtn.addEventListener("click", () => {
            const msg = chatInput.value.trim();
            if (!msg) return;

            appendMessage(msg, true);
            chatInput.value = "";

            fetch("/chat/api", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRF-Token": getCSRFToken() || ''
                },
                body: JSON.stringify({ message: msg }),
            })
            .then(res => {
                if (!res.ok) {
                    throw new Error(`HTTP error! status: ${res.status}`);
                }
                return res.json();
            })
            .then(data => {
                appendMessage(data.response || "🤖 Ответ не получен", false);
            })
            .catch(err => {
                console.error("Ошибка чата:", err);
                appendMessage("❌ Произошла ошибка при отправке сообщения. Пожалуйста, попробуйте позже.", false);
            });
        });

        chatInput.addEventListener("keypress", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                sendBtn.click();
            }
        });
    }

    // WebSocket события
    socket.on("connect", () => {
        console.log("🟢 WebSocket подключен");
    });

    socket.on("disconnect", () => {
        console.warn("🔴 WebSocket отключен");
    });

    socket.on("message", (data) => {
        appendMessage(typeof data === 'string' ? data : data.text || "🤖 Ответ от бота");
    });

    socket.emit("message", "Тестовое сообщение от клиента");

    // Получение событий слотов (если требуется обновление UI извне)
    socket.on("slots_update", (data) => {
        console.log("📥 Обновление слотов:", data);
    });

    socket.on("booking_updated", () => {
        const dateInput = document.getElementById("bookingDate");
        if (dateInput && dateInput.value) {
            fetch('/event', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ date: dateInput.value })
            });
        }
    });

    if (homeLink) {
        homeLink.addEventListener("click", (e) => {
            if (window.location.pathname === "/" || window.location.pathname.endsWith("index")) {
                e.preventDefault();
                const hero = document.getElementById("hero");
                if (hero) {
                    hero.scrollIntoView({ behavior: "smooth" });
                } else {
                    window.scrollTo({ top: 0, behavior: "smooth" });
                }
            }
        });
    }
});

// Глобальная функция для CSRF
window.getCSRFToken = window.getCSRFToken || function () {
    return document.querySelector('meta[name="csrf-token"]')?.content 
        || document.querySelector('input[name="csrf_token"]')?.value;
};

// Инициализация чата
function initChat() {
    console.log("✅ chat.js успешно загружен");
    
    const chatContainer = document.getElementById('chat-container-fixed');
    if (!chatContainer) return;

    // Делегирование событий для кнопок меню
    chatContainer.addEventListener('click', (e) => {
        const button = e.target.closest('button[data-action]');
        if (!button) return;

        const action = button.dataset.action;
        switch (action) {
            case 'showSchedule':
                showSchedule();
                break;
            case 'showFAQ':
                showFAQ();
                break;
            case 'updateClientData':
                updateClientData();
                break;
            case 'bookTraining':
                bookTraining();
                break;
        }
    });

    // === Загрузка медиафайлов ===
    function uploadMedia(e) {
        const file = e.target.files?.[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        fetch('/files/upload', {
            method: 'POST',
            body: formData
        })
        .then(r => r.ok ? r.json() : Promise.reject(r.statusText))
        .then(() => appendMessage("📎 Файл загружен!", true))
        .catch(err => {
            console.error("Ошибка загрузки медиа:", err);
            appendMessage("❌ Не удалось загрузить файл.", false);
        });
    }

    // Обработчик для загрузки файлов
    const fileUpload = document.getElementById('file-upload');
    if (fileUpload) {
        fileUpload.addEventListener('change', uploadMedia);
    }

    // Остальной код инициализации чата...
    setupWebSocket();
    initChatForm();
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', initChat);