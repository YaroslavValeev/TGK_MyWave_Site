/**
 * Плавающий чат MyWave.
 * Все ответы AI и сценарий записи на занятие идут через HTTP POST /chat/api (единая серверная маршрутизация).
 * Socket.IO на странице — только для индикатора соединения (socket-status.js), не для текста чата.
 */
const CHAT_API_URL = '/chat/api';
const CHAT_WELCOME_STORAGE_KEY = 'mw_chat_welcome_v2';

/**
 * Синхронизирует сессию Flask с подписанным CSRF-токеном (meta).
 * Нужно после перезапуска сервера, смены SECRET_KEY или долгой вкладки:
 * иначе на сервере нет session['csrf_token'], а в заголовке — старый токен → 400.
 */
async function ensureCsrfToken() {
    try {
        const r = await fetch('/api/csrf-token', {
            method: 'GET',
            credentials: 'same-origin'
        });
        if (!r.ok) return;
        const d = await r.json();
        if (d && d.csrf_token) {
            const meta = document.querySelector('meta[name="csrf-token"]');
            if (meta) meta.setAttribute('content', d.csrf_token);
        }
    } catch (e) {
        console.debug('ensureCsrfToken skipped:', e);
    }
}

let chatContext = [];
/** Контекст с текущей страницы (услуги / магазин / проекты) или из бронирования. */
let _pageChatContext = null;

function _parseBodyDatasetContext() {
    try {
        const raw = document.body?.getAttribute('data-mw-chat-context');
        if (!raw || raw === '{}' || raw === 'null') return null;
        const o = JSON.parse(raw);
        return o && typeof o === 'object' ? o : null;
    } catch (e) {
        return null;
    }
}

/**
 * Задать контекст чата (например, с карточки услуги). Передайте null чтобы сбросить.
 * @param {{entry?: string, kind?: string, id?: string, title?: string}|null} obj
 */
function setMyWaveChatContext(obj) {
    if (!obj || typeof obj !== 'object') {
        _pageChatContext = null;
        return;
    }
    _pageChatContext = {
        entry: String(obj.entry || 'general').slice(0, 32),
        kind: String(obj.kind || '').slice(0, 32),
        id: String(obj.id || '').slice(0, 64),
        title: String(obj.title || '').slice(0, 120)
    };
}

/**
 * Вызывается из booking.js при выборе услуги — чтобы чат знал, о какой записи идёт речь.
 */
function syncChatContextFromBooking(serviceId, title) {
    setMyWaveChatContext({
        entry: 'services',
        kind: 'service',
        id: serviceId || '',
        title: title || serviceId || ''
    });
}

function _buildChatRequestBody(message) {
    const body = {
        message: message,
        user: 'Гость',
        history: Array.isArray(chatContext)
            ? chatContext.slice(-10).map((m) => ({
                role: m.role === 'bot' ? 'assistant' : (m.role || 'user'),
                content: m.content || m.text || m.message || ''
            }))
            : []
    };
    const ctx = _pageChatContext || _parseBodyDatasetContext();
    if (ctx && typeof ctx === 'object' && Object.keys(ctx).length) {
        body.context = ctx;
    }
    return body;
}

function updateContext(role, content) {
    try {
        if (!role || typeof content === 'undefined') return;
        chatContext.push({ role, content, time: new Date().toISOString() });
    } catch (e) {
        console.debug('updateContext skipped:', e);
    }
}

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

const ChatWidgetUtils = {
    escapeHtml(unsafe) {
        if (unsafe === null || unsafe === undefined) return '';
        return String(unsafe)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    },
    getCSRFToken() {
        const token = document.querySelector('meta[name="csrf-token"]')?.content
            || document.querySelector('input[name="csrf_token"]')?.value;
        if (!token) {
            console.error('CSRF token not found');
            throw new Error('CSRF token not found');
        }
        return token;
    },
    getHeaders() {
        return {
            'Content-Type': 'application/json',
            'X-CSRFToken': ChatWidgetUtils.getCSRFToken()
        };
    }
};

function decodeEntities(s) {
    try {
        const el = document.createElement('span');
        el.innerHTML = String(s ?? '');
        return el.textContent || '';
    } catch (e) {
        return String(s ?? '');
    }
}

/**
 * Добавляет одно сообщение в контейнер чата (единая реализация).
 * @param {HTMLElement} container — #chat-messages
 * @param {string} text
 * @param {'user'|'bot'} type
 */
function appendChatBubble(container, text, type = 'bot') {
    if (!container) return;
    const message = document.createElement('div');
        message.className = `message ${type}`;
        const content = document.createElement('div');
        content.className = 'message-content';
        const raw = type === 'bot' ? cleanAssistantText(text) : text;
    content.textContent = decodeEntities(raw);
        message.appendChild(content);
    container.appendChild(message);
    container.scrollTop = container.scrollHeight;
}

let typingRow = null;

function setTypingIndicator(container, on) {
    if (!container) return;
    if (on) {
        if (typingRow) return;
        typingRow = document.createElement('div');
        typingRow.className = 'message bot typing-indicator';
        typingRow.setAttribute('aria-live', 'polite');
        typingRow.textContent = 'Печатает…';
        container.appendChild(typingRow);
        container.scrollTop = container.scrollHeight;
    } else if (typingRow) {
        typingRow.remove();
        typingRow = null;
    }
}

function updateChatState(state) {
    try {
        const el = document.getElementById('chat-widget');
        if (el) el.setAttribute('data-state', state);
    } catch (e) {
        console.debug('updateChatState skipped:', e);
    }
}

function renderSuggestions(suggestions, state, chatMessagesEl, sendMessageToServer, appendBubble) {
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
                const norm = val.replace(/[^\d+]/g, '');
                if (!/^((\+7|8)\d{10})$/.test(norm)) {
                    alert('Введите телефон формата +7XXXXXXXXXX или 8XXXXXXXXXX');
                    return;
                }
                appendBubble(chatMessagesEl, val, 'user');
                sendMessageToServer(val);
            });
            wrap.appendChild(input);
            wrap.appendChild(btn);
            cont.appendChild(wrap);
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
                if (!val) {
                    alert('Введите имя');
                    return;
                }
                appendBubble(chatMessagesEl, val, 'user');
                sendMessageToServer(val);
            });
            wrap.appendChild(input);
            wrap.appendChild(btn);
            cont.appendChild(wrap);
            return;
        }
        if (!Array.isArray(suggestions) || !suggestions.length) return;
        suggestions.forEach((label) => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'suggestion-chip';
            btn.textContent = label;
            btn.addEventListener('click', () => {
                appendBubble(chatMessagesEl, label, 'user');
                sendMessageToServer(label);
            });
            cont.appendChild(btn);
        });
    } catch (e) {
        /* no-op */
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const chatToggle = document.getElementById('chat-toggle');
    const chatWidget = document.getElementById('chat-widget');
    const closeChat = document.getElementById('close-chat');
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatMessages = document.getElementById('chat-messages');

    if (!chatForm || !chatInput || !chatMessages) {
        return;
    }

    ensureCsrfToken();

    _pageChatContext = _pageChatContext || _parseBodyDatasetContext();

    document.addEventListener('click', (e) => {
        const card = e.target && e.target.closest && e.target.closest('.product-card[data-mw-product-slug]');
        if (!card) return;
        setMyWaveChatContext({
            entry: 'shop',
            kind: 'product',
            id: (card.getAttribute('data-mw-product-slug') || '').trim(),
            title: (card.getAttribute('data-mw-product-title') || '').trim()
        });
    });

    function showWelcomeOnce() {
        try {
            if (localStorage.getItem(CHAT_WELCOME_STORAGE_KEY)) return;
            appendChatBubble(
                chatMessages,
                'Могу ответить по базе знаний MyWave: тренировки, запись на слот, что взять с собой. Для живого ответа напишите в Telegram @MyW23 или нажмите «Записаться» на сайте.',
                'bot'
            );
            localStorage.setItem(CHAT_WELCOME_STORAGE_KEY, '1');
        } catch (e) {
            console.debug('welcome once skipped:', e);
        }
    }

    chatToggle?.addEventListener('click', () => {
        chatWidget?.classList.remove('hidden');
        showWelcomeOnce();
        chatInput.focus();
    });

    closeChat?.addEventListener('click', () => {
        chatWidget?.classList.add('hidden');
    });

    async function sendMessageToServer(message, isCsrfRetry = false) {
        if (!message) {
            console.error('Пустое сообщение');
            return;
        }
        if (!isCsrfRetry) {
            updateContext('user', message);
        }
        setTypingIndicator(chatMessages, true);
        updateChatState('loading');
        try {
            await ensureCsrfToken();
            const response = await fetch(CHAT_API_URL, {
                method: 'POST',
                headers: ChatWidgetUtils.getHeaders(),
                credentials: 'same-origin',
                body: JSON.stringify(_buildChatRequestBody(message))
            });

            if (response.status === 429) {
                setTypingIndicator(chatMessages, false);
                let msg = 'Слишком много запросов. Подождите немного.';
                try {
                    const d = await response.json();
                    if (d && d.response) msg = d.response;
                } catch (e) { /* ignore */ }
                appendChatBubble(chatMessages, msg, 'bot');
                updateChatState('rate_limited');
                return;
            }

            if (!response.ok) {
                let errPayload = {};
                try {
                    errPayload = await response.json();
                } catch (e) { /* ignore */ }
                const errText = String(errPayload.error || '');
                const isCsrf =
                    response.status === 400 &&
                    /csrf/i.test(errText) &&
                    !isCsrfRetry;
                if (isCsrf) {
                    await ensureCsrfToken();
                    return sendMessageToServer(message, true);
                }
                setTypingIndicator(chatMessages, false);
                if (response.status === 400 || response.status === 403) {
                    appendChatBubble(
                        chatMessages,
                        'Сессия устарела. Обновите страницу (F5) и отправьте сообщение снова.',
                        'bot'
                    );
                    updateChatState('error');
                    return;
                }
                throw new Error('Ошибка сети');
            }

            setTypingIndicator(chatMessages, false);
            const data = await response.json();
            
            if (data.response) {
                appendChatBubble(chatMessages, data.response, 'bot');
                updateContext('assistant', data.response);
            } else if (data.error) {
                appendChatBubble(chatMessages, 'Произошла ошибка: ' + data.error, 'bot');
            }
            try {
                if (data && (data.suggestions || data.state)) {
                    renderSuggestions(
                        data.suggestions,
                        data.state,
                        chatMessages,
                        sendMessageToServer,
                        appendChatBubble
                    );
                } else {
                    renderSuggestions([], null, chatMessages, sendMessageToServer, appendChatBubble);
                }
            } catch (e) { /* no-op */ }
            updateChatState('success');
        } catch (error) {
            setTypingIndicator(chatMessages, false);
            updateChatState('error');
            console.error('Ошибка при отправке:', error);
            appendChatBubble(
                chatMessages,
                error.message || 'Извините, произошла ошибка при обработке вашего сообщения',
                'bot'
            );
        }
    }

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const message = chatInput.value.trim();
        if (!message) return;

        appendChatBubble(chatMessages, message, 'user');
        chatInput.value = '';
        await sendMessageToServer(message);
    });

    document.addEventListener('click', (e) => {
        if (
            chatWidget &&
            !chatWidget.classList.contains('hidden') &&
            !chatWidget.contains(e.target) &&
            chatToggle &&
            !chatToggle.contains(e.target)
        ) {
            chatWidget.classList.add('hidden');
        }
    });

    chatWidget?.addEventListener('click', (e) => {
        e.stopPropagation();
    });

    if (typeof Chat !== 'undefined' && Chat.init) Chat.init();
    if (typeof Booking !== 'undefined' && Booking.init) Booking.init();
    if (typeof StoreFilter !== 'undefined' && StoreFilter.init) StoreFilter.init();
});

window.getCSRFToken = window.getCSRFToken || function () {
    return document.querySelector('meta[name="csrf-token"]')?.content 
        || document.querySelector('input[name="csrf_token"]')?.value;
};

window.Chat = window.Chat || { init: function () {} };
window.Booking = window.Booking || { init: function () {} };
window.StoreFilter = window.StoreFilter || { init: function () {} };
/** Для booking.js: контекст услуги в чат (серверная бронь по тексту — только POST /chat/api). */
window.setMyWaveChatContext = setMyWaveChatContext;
window.syncChatContextFromBooking = syncChatContextFromBooking;

/** Внешняя отправка в чат (канонический endpoint). */
function sendMessage(text) {
    if (!text) return;
    ensureCsrfToken()
        .then(() =>
            fetch(CHAT_API_URL, {
                method: 'POST',
                headers: ChatWidgetUtils.getHeaders(),
                credentials: 'same-origin',
                body: JSON.stringify(_buildChatRequestBody(text))
            })
        )
        .then((r) => r.json())
        .catch((err) => console.error('sendMessage:', err));
}
