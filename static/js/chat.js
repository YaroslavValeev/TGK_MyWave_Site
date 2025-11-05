// Глобальные переменные и утилиты
let bookingData = { date: null, slot: null, name: "", phone: "" };
let socket = null;
let chatContext = [];

// Safe helpers to avoid ReferenceError during chat send
function updateContext(role, content) {
    try {
        if (!role || typeof content === 'undefined') return;
        chatContext.push({ role, content, time: new Date().toISOString() });
    } catch (e) {
        console.debug('updateContext skipped:', e);
    }
}

function updateChatState(state) {
    try {
        // Optional hook for UI state; keep lightweight
        const el = document.getElementById('chat-widget');
        if (el) el.setAttribute('data-state', state);
    } catch (e) {
        console.debug('updateChatState skipped:', e);
    }
}

// Remove helper labels from assistant text
function cleanAssistantText(text) {
    if (text == null) return '';
    let t = String(text);
    const labels = [
        /\bПрямой\s*ответ\s*:/gi,
        /\bПояснение\s*\/\s*польза\s*:/gi,
        /\bПояснение\s*:/gi,
        /\bПольза\s*:/gi,
        /\bПриглашение\s*:/gi
    ];
    labels.forEach((re) => { t = t.replace(re, '').trim(); });
    t = t.replace(/^[-•]\s*/gm, '');
    t = t.replace(/\n{3,}/g, '\n\n');
    return t.trim();
}

const Utils = {
    getTime: () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    scrollChat: () => {
        const chatMessages = document.getElementById("chat-messages");
        if (chatMessages) {
            chatMessages.scrollTo({ top: chatMessages.scrollHeight, behavior: "smooth" });
        }
    },
    // Escape HTML to prevent XSS when inserting untrusted text into innerHTML
    escapeHtml: (unsafe) => {
        if (unsafe === null || unsafe === undefined) return '';
        return String(unsafe)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    },
    createMessage: (text, type = "bot") => {
        const div = document.createElement("div");
        div.className = `message ${type}`;
        const strong = document.createElement('strong');
        strong.textContent = type === 'user' ? 'Вы' : 'Эксперт';

        const content = document.createElement('span');
        content.textContent = Utils.escapeHtml(text || '⚠️ Ошибка: текст не передан');

        const small = document.createElement('small');
        small.textContent = Utils.getTime();

        div.appendChild(strong);
        div.appendChild(document.createTextNode(': '));
        div.appendChild(content);
        div.appendChild(document.createTextNode(' '));
        div.appendChild(small);
        return div;
    },
    showModal: (elem) => {
        if (elem) {
            elem.classList.remove("hidden");
            document.body.style.overflow = "hidden";
        }
    },
    hideModal: (elem) => {
        if (elem) {
            elem.classList.add("hidden");
            document.body.style.overflow = "";
        }
    },
    updateProgressBar: (step) => {
        const steps = document.querySelectorAll(".progress-step");
        steps.forEach((s, index) => {
            if (index + 1 <= step) {
                s.classList.add("active");
            } else {
                s.classList.remove("active");
            }
        });
    },
    // Получение CSRF-токена
    getCSRFToken: () => {
        const token = document.querySelector('input[name="csrf_token"]')?.value;
        if (!token) {
            console.error('CSRF token not found');
            throw new Error('CSRF token not found');
        }
        return token;
    },
    // Получение заголовков для запросов
    getHeaders: () => {
        return {
            'Content-Type': 'application/json',
            'X-CSRFToken': Utils.getCSRFToken()
        };
    }
};

// === Централизованная инициализация чата ===
document.addEventListener("DOMContentLoaded", () => {
    // UI элементы
    const UI = {
        chatToggle: document.getElementById("chat-toggle"),
        chatWidget: document.getElementById("chat-widget"),
        closeChat: document.getElementById("close-chat"),
        chatForm: document.getElementById("chat-form"),
        chatInput: document.getElementById("chat-input"),
        chatMessages: document.getElementById("chat-messages")
    };

    // Инициализация защищенного WebSocket подключения
    const socket = new SecureSocketIO(window.location.origin, {
        transports: ["websocket"],
        autoConnect: false,
        reconnectionAttempts: 5,
        onCSRFError: () => {
            // Показываем сообщение об ошибке и перенаправляем на страницу логина
            appendMessage("Ошибка валидации безопасности. Необходимо войти заново.", "bot");
            setTimeout(() => window.location.href = '/login', 3000);
        }
    });

    // Приветственное сообщение при подключении
    socket.on("connect", () => {
        console.log("✅ WebSocket подключён");
        appendMessage("О чём я могу тебя спросить?", "bot");
    });

    // Обработка ошибок подключения
    socket.on("connect_error", (error) => {
        console.error("WebSocket ошибка подключения:", error);
        if (error.message.includes("CSRF")) {
            appendMessage("Ошибка валидации безопасности. Пожалуйста, подождите...", "bot");
        } else {
            appendMessage("Ошибка подключения к серверу. Пожалуйста, попробуйте позже.", "bot");
        }
    });

    // Обработка сообщений
    socket.on("message", (data) => {
        if (data && data.response) {
            appendMessage(data.response, "bot");
        } else if (data && data.error) {
            console.error("Ошибка сообщения:", data.error);
            appendMessage("Ошибка: " + data.error, "bot");
        }
    });

    // Подключаем сокет
    socket.connect();

    // Функции для работы с сообщениями
    function decodeEntities(s) {
        try {
            const el = document.createElement('span');
            el.innerHTML = String(s ?? '');
            return el.textContent || '';
        } catch (e) { return String(s ?? ''); }
    }

    function appendMessage(text, type = "bot") {
        const message = document.createElement("div");
        message.className = `message ${type}`;
        const content = document.createElement('div');
        content.className = 'message-content';
        const raw = type === 'bot' ? cleanAssistantText(text) : text;
        const payload = decodeEntities(raw);
        content.textContent = payload;

        message.appendChild(content);

        UI.chatMessages.appendChild(message);
        UI.chatMessages.scrollTop = UI.chatMessages.scrollHeight;
    }

    // Render booking suggestion chips or mini-forms below the chat
    function renderSuggestions(suggestions, state) {
        try {
            const cont = document.getElementById('chat-suggestions');
            if (!cont) return;
            cont.innerHTML = '';
            const step = state && state.step;
            if (step === 'ask_phone') {
                const wrap = document.createElement('div');
                const input = document.createElement('input');
                input.type = 'tel';
                input.placeholder = '+7XXXXXXXXXX';
                input.className = 'chat-input';
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'suggestion-chip';
                btn.textContent = 'Отправить телефон';
                btn.addEventListener('click', () => {
                    const val = (input.value || '').trim();
                    const norm = val.replace(/[^\d+]/g,'');
                    if (!/^((\+7|8)\d{10})$/.test(norm)) {
                        alert('Введите телефон формата +7XXXXXXXXXX или 8XXXXXXXXXX');
                        return;
                    }
                    appendMessage(val, 'user');
                    sendMessageToServer(val);
                });
                wrap.appendChild(input); wrap.appendChild(btn); cont.appendChild(wrap);
                return;
            }
            if (step === 'ask_name') {
                const wrap = document.createElement('div');
                const input = document.createElement('input');
                input.type = 'text';
                input.placeholder = 'Ваше имя';
                input.className = 'chat-input';
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'suggestion-chip';
                btn.textContent = 'Отправить имя';
                btn.addEventListener('click', () => {
                    const val = (input.value || '').trim();
                    if (!val) { alert('Введите имя'); return; }
                    appendMessage(val, 'user');
                    sendMessageToServer(val);
                });
                wrap.appendChild(input); wrap.appendChild(btn); cont.appendChild(wrap);
                return;
            }
            if (!Array.isArray(suggestions) || !suggestions.length) return;
            suggestions.forEach((label) => {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'suggestion-chip';
                btn.textContent = label;
                btn.addEventListener('click', () => {
                    appendMessage(label, 'user');
                    sendMessageToServer(label);
                });
                cont.appendChild(btn);
            });
        } catch (e) { /* no-op */ }
    }

    // Heuristic router for booking-related messages
    function isBookingLike(text) {
        if (!text) return false;
        const t = String(text).toLowerCase().trim();
        if (/^\s*(?:в\s*)?\d{1,2}:\d{2}\s*$/.test(t)) return true;
        if (/^\d{4}-\d{2}-\d{2}$/.test(t)) return true;
        if (/(сегодня|завтра|послезавтра|ближайш|записать|запиш|трениров|слот|время)/.test(t)) return true;
        return false;
    }

    // Функция отправки сообщения на сервер
    async function sendMessageToServer(message) {
        updateContext('user', message);
        try {
            console.log('Отправка сообщения:', message);
            const endpoint = (function(){
                const t = String(message).toLowerCase().trim();
                if (/^\s*\d{1,2}:\d{2}\s*$/.test(t)) return '/api/booking';
                if (/^\d{4}-\d{2}-\d{2}$/.test(t)) return '/api/booking';
                if (/(сегодня|завтра|послезавтра|запис|трениров|слот|время)/i.test(t)) return '/api/booking';
                return '/chat/api';
            })();
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: Utils.getHeaders(),
                body: JSON.stringify({
                    message: message,
                    user: "Гость",
                    // Передаём последние 10 реплик диалога для контекста
                    history: Array.isArray(chatContext) ? chatContext.slice(-10).map(m => ({
                        role: m.role === 'bot' ? 'assistant' : (m.role || 'user'),
                        content: m.content || m.text || m.message || ''
                    })) : []
                })
            });

            console.log('Статус ответа:', response.status);
            
            if (!response.ok) {
                if (response.status === 403) {
                    console.error('CSRF validation failed');
                    throw new Error('Ошибка валидации CSRF-токена. Пожалуйста, обновите страницу.');
                }
                console.error('Ошибка ответа:', response.status, response.statusText);
                throw new Error('Ошибка сети');
            }

            const data = await response.json();
            console.log('Полученные данные:', data);
            
            if (data.response) {
                console.log('Получен ответ от сервера:', data.response);
                appendMessage(data.response, "bot");
                updateContext('assistant', data.response);
            } else if (data.error) {
                console.error('Получена ошибка от сервера:', data.error);
                appendMessage("Произошла ошибка: " + data.error, "bot");
            }
            try { if (data && (data.suggestions || data.state)) { renderSuggestions(data.suggestions, data.state); } else { renderSuggestions([], null); } } catch (e) {}
            updateChatState('success');
        } catch (error) {
            updateChatState('error');
            console.error('Ошибка при отправке:', error);
            appendMessage(error.message || "Извините, произошла ошибка при обработке вашего сообщения", "bot");
        }
    }

    // Обработчики событий
    UI.chatToggle?.addEventListener("click", () => {
        UI.chatWidget.classList.remove("hidden");
        UI.chatInput.focus();
    });

    UI.closeChat?.addEventListener("click", () => {
        UI.chatWidget.classList.add("hidden");
    });

    UI.chatForm?.addEventListener("submit", async (e) => {
        e.preventDefault();
        const message = UI.chatInput.value.trim();
        if (!message) return;

        appendMessage(message, "user");
        UI.chatInput.value = "";
        
        // Отправляем сообщение на сервер
        await sendMessageToServer(message);
    });

    // Закрытие чата по клику вне его области
    document.addEventListener("click", (e) => {
        if (!UI.chatWidget.classList.contains("hidden") && 
            !UI.chatWidget.contains(e.target) && 
            !UI.chatToggle.contains(e.target)) {
            UI.chatWidget.classList.add("hidden");
        }
    });

    // Предотвращение закрытия при клике внутри чата
    UI.chatWidget?.addEventListener("click", (e) => {
        e.stopPropagation();
    });

    // Пример инициализации других модулей
    if (typeof Chat !== "undefined" && Chat.init) Chat.init();
    if (typeof Booking !== "undefined" && Booking.init) Booking.init();
    if (typeof StoreFilter !== "undefined" && StoreFilter.init) StoreFilter.init();
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
            localStorage.setItem("selectedSlotTime", time); // сохраняем выбранное время
            Utils.showModal(UI.modalCalendar); // открываем календарь
        });
    });
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
        formData.append('csrf_token', Utils.getCSRFToken());

        fetch('/files/upload', {
            method: 'POST',
            headers: {
                'X-CSRFToken': Utils.getCSRFToken()
            },
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

// ===== Минимальные заглушки для модулей =====
window.Chat = window.Chat || {
    init: function() {
        console.log("[Chat] Модуль инициализирован (заглушка)");
    }
};

window.Booking = window.Booking || {
    init: function() {
        console.log("[Booking] Модуль инициализирован (заглушка)");
    }
};

window.StoreFilter = window.StoreFilter || {
    init: function() {
        console.log("[StoreFilter] Модуль инициализирован (заглушка)");
    }
};

// Исправленный пример fetch для чата
function sendMessage(text) {
    fetch('/api/chat', {
        method: 'POST',
        headers: Utils.getHeaders(),
        body: JSON.stringify({ message: text })
    })
    .then(response => response.json())
    .catch(error => console.error('Ошибка:', error));
}

// === Функция для отправки заявки на занятие ===
async function sendBookingRequest() {
    // 1) Собираем данные
    const payload = {
      date: document.getElementById('bookingDateInput').value,
      time: document.getElementById('selectedSlot').value,
      name: document.getElementById('bookingName').value.trim(),
      phone: document.getElementById('bookingPhone').value.trim()
    };
  
    // 2) Проверяем формат телефона (при желании можно вынести в отдельную функцию)
    const phoneRegex = /^\+?\d{10,15}$/;
    if (!phoneRegex.test(payload.phone)) {
      return alert('❌ Введите корректный номер телефона');
    }
  
    try {
      // 3) Отправляем строго в /api/calendar/book с JSON-заголовком
      const response = await fetch('/api/calendar/book', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });
  
      // 4) Дожидаемся JSON-ответа
      const result = await response.json();
  
      if (response.ok) {
        alert(`✅ ${result.message || 'Запись успешно создана!'}`);
        // Скрываем модалку, обновляем UI и т.д.
      } else {
        alert(`❌ Ошибка: ${result.error || 'Не удалось записаться'}`);
      }
    } catch (err) {
      console.error('Ошибка при отправке записи:', err);
      alert('❌ Ошибка при отправке. Повторите позже.');
    }
  }


const button = document.querySelector('#someButton');
if (button) {
  button.classList.add('hidden');
}

// Пример обработчика для кнопки открытия чата
const chatToggleBtn = document.querySelector('.chat-toggle');
if (chatToggleBtn) {
  chatToggleBtn.addEventListener('click', function() {
    chatToggleBtn.classList.toggle('chat-open');
  });
}

// Добавление анимации для новых сообщений
function appendMessage(role, text) {
    const chatMessages = document.querySelector('.chat-messages');
    const msg = document.createElement('div');
    msg.className = 'message ' + role;
    msg.textContent = text;
    msg.style.opacity = 0;
    chatMessages.appendChild(msg);
    setTimeout(() => {
        msg.style.transition = 'opacity 0.3s, transform 0.3s';
        msg.style.opacity = 1;
        msg.style.transform = 'translateY(0)';
    }, 10);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Индикатор "печатает..."
let typingIndicator = null;
function showTypingIndicator() {
    if (!typingIndicator) {
        typingIndicator = document.createElement('div');
        typingIndicator.className = 'message bot typing-indicator';
        typingIndicator.textContent = 'Печатает...';
        document.querySelector('.chat-messages').appendChild(typingIndicator);
        document.querySelector('.chat-messages').scrollTop = document.querySelector('.chat-messages').scrollHeight;
    }
}
function hideTypingIndicator() {
    if (typingIndicator) {
        typingIndicator.remove();
        typingIndicator = null;
    }
}

// Пример интеграции с отправкой:
const chatForm = document.querySelector('.chat-input-form');
if (chatForm) {
    chatForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const input = chatForm.querySelector('input, textarea');
        const text = input.value.trim();
        if (!text) return;
        appendMessage('user', text);
        input.value = '';
        showTypingIndicator();
        // Отправка запроса к серверу
        try {
            const response = await fetch('/api/assistant/', {
                method: 'POST',
                headers: Utils.getHeaders(),
                body: JSON.stringify({ prompt: text })
            });
            const data = await response.json();
            hideTypingIndicator();
            if (data.response) {
                appendMessage('bot', data.response);
            } else if (data.error) {
                appendMessage('bot', 'Ошибка: ' + data.error);
            }
        } catch (err) {
            hideTypingIndicator();
            appendMessage('bot', 'Ошибка соединения с сервером');
        }
    });
}

// === Для страницы /chat ===
document.addEventListener("DOMContentLoaded", () => {
  const chatForm = document.getElementById("chatForm");
  const chatInput = document.getElementById("chatMessageInput");
  const sendBtn = document.getElementById("sendChatBtn");
  const chatWindow = document.getElementById("chatWindow");

  if (chatForm && chatInput && sendBtn && chatWindow) {
    chatForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const message = chatInput.value.trim();
      if (!message) return;
      sendBtn.disabled = true;
      // Отправляем сообщение на /chat/api
      try {
        const endpoint2 = (function(){
            const t = String(message).toLowerCase().trim();
            if (/^\s*\d{1,2}:\d{2}\s*$/.test(t)) return '/api/booking';
            if (/^\d{4}-\d{2}-\d{2}$/.test(t)) return '/api/booking';
            if (/(сегодня|завтра|послезавтра|запис|трениров|слот|время)/i.test(t)) return '/api/booking';
            return '/chat/api';
        })();
        const response = await fetch(endpoint2, {
          method: "POST",
          headers: Utils.getHeaders(),
          body: JSON.stringify({ message })
        });
        
        if (!response.ok) {
            if (response.status === 403) {
                throw new Error('Ошибка валидации CSRF-токена. Пожалуйста, обновите страницу.');
            }
            throw new Error('Ошибка сети');
        }

        const data = await response.json();
        if (data.response) {
          appendChatMessage(message, "user");
          appendChatMessage(data.response, "bot");
        } else if (data.error) {
          appendChatMessage("Ошибка: " + data.error, "bot");
        }
      } catch (err) {
        appendChatMessage(err.message || "Ошибка соединения с сервером", "bot");
      }
      chatInput.value = "";
      sendBtn.disabled = true;
    });
    chatInput.addEventListener("input", () => {
      sendBtn.disabled = !chatInput.value.trim();
    });
  }

  function appendChatMessage(text, type) {
    const msg = document.createElement("div");
    msg.className = "message " + type;
    // decode HTML entities then set as textContent
    try {
      const el = document.createElement('span');
      el.innerHTML = String(text ?? '');
      msg.textContent = el.textContent || '';
    } catch (e) {
      msg.textContent = String(text ?? '');
    }
    chatWindow.appendChild(msg);
    chatWindow.scrollTop = chatWindow.scrollHeight;
  }
});

// Заглушки для кнопок меню и загрузки файлов на странице /chat
window.showSchedule = function() { alert('Расписание пока недоступно'); }
window.showFAQ = function() { alert('FAQ пока недоступен'); }
window.updateClientData = function() { alert('Функция в разработке'); }
window.bookTraining = function() { alert('Функция в разработке'); }
window.uploadMedia = function() { alert('Загрузка файлов пока не реализована'); }

function validateBotResponse(response) {
    const required = ['Прямой ответ:', 'Пошаговая инструкция:'];
    return required.every(section => response.includes(section));
}

// В обработчике ответа от сервера:
if (data.response) {
    if (validateBotResponse(data.response)) {
        appendMessage('bot', data.response);
    } else {
        console.warn('Ответ не соответствует формату');
        appendMessage('bot', 'Извините, попробуйте переформулировать вопрос');
    }
}

function formatBotResponse(text) {
    // Return a DocumentFragment with safe, escaped nodes instead of raw HTML
    const frag = document.createDocumentFragment();
    text.split('\n').forEach(line => {
        const div = document.createElement('div');
        if (line.startsWith('Прямой ответ:')) {
            div.className = 'response-direct';
        } else if (line.startsWith('Пошаговая инструкция:')) {
            div.className = 'response-steps';
        }
        // Use Utils.escapeHtml if available, otherwise basic escaping
        const safeText = (typeof Utils !== 'undefined' && Utils.escapeHtml)
            ? Utils.escapeHtml(line)
            : String(line).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        div.textContent = safeText;
        frag.appendChild(div);
    });
    return frag;
}

// Обновить appendMessage: safely append structured bot responses
function appendMessage(role, text) {
    const msg = document.createElement('div');
    msg.className = 'message ' + role;
    // Удаляем временные метки
    const cleanText = String(text).replace(/\d{2}:\d{2}:\d{2}/g, '').trim();
    
    if (role === 'bot') {
        const frag = formatBotResponse(cleanText);
        msg.appendChild(frag);
    } else {
        const span = document.createElement('span');
        span.textContent = cleanText;
        msg.appendChild(span);
    }
    const container = document.querySelector('.chat-messages');
    if (container) {
        container.appendChild(msg);
        msg.scrollIntoView({ behavior: 'smooth' });
    }
}

// Загрузка базы знаний
let knowledgeBase = {
    training: null,
    tricks: null
};

async function loadKnowledgeBase() {
    try {
        const [trainingData, tricksData] = await Promise.all([
            fetch('/api/knowledge/training').then(r => r.json()),
            fetch('/api/knowledge/tricks').then(r => r.json())
        ]);
        
        knowledgeBase.training = trainingData;
        knowledgeBase.tricks = tricksData;
        
        generateSuggestedQuestions();
    } catch (error) {
        console.error('Failed to load knowledge base:', error);
    }
}

// Инициализация при загрузке
document.addEventListener('DOMContentLoaded', loadKnowledgeBase);
