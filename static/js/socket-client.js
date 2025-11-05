// Класс для безопасного WebSocket подключения
class SecureSocketIO {
    constructor(url, options = {}) {
        this.csrfToken = this._getCSRFToken();
        if (!this.csrfToken) {
            console.error('CSRF token not found');
            throw new Error('CSRF token not found');
        }

        // Базовые настройки
        const defaultOptions = {
            transports: ['websocket', 'polling'],
            autoConnect: false,
            reconnectionAttempts: 5,
            reconnectionDelay: 1000,
            timeout: 10000
        };

        // Объединяем с пользовательскими настройками
        this.options = { ...defaultOptions, ...options };
        
        // Добавляем CSRF токен в данные аутентификации
        this.options.auth = {
            ...(this.options.auth || {}),
            csrf_token: this.csrfToken
        };

        // Создаем Socket.IO подключение
        this.socket = io(url, this.options);
        
        // Настраиваем обработчики по умолчанию
        this._setupDefaultHandlers();
    }

    _getCSRFToken() {
        return document.querySelector('meta[name="csrf-token"]')?.content
            || document.querySelector('input[name="csrf_token"]')?.value;
    }

    _setupDefaultHandlers() {
        // Обработка подключения
        this.socket.on('connect', () => {
            console.log('✅ WebSocket connected');
            // Отправляем CSRF токен сразу после подключения
            this.socket.emit('message', { csrf_token: this.csrfToken });
        });

        // Обработка ошибок
        this.socket.on('connect_error', (error) => {
            console.error('❌ WebSocket connection error:', error);
            if (error.message && error.message.includes('CSRF')) {
                // Пробуем обновить CSRF токен
                this.csrfToken = this._getCSRFToken();
                if (this.csrfToken) {
                    this.socket.auth.csrf_token = this.csrfToken;
                    this.socket.connect();
                }
            }
        });

        // Обработка переподключения
        this.socket.on('reconnect_attempt', (attemptNumber) => {
            console.log(`⚡ WebSocket reconnection attempt ${attemptNumber}`);
            // Обновляем CSRF токен при каждой попытке переподключения
            this.csrfToken = this._getCSRFToken();
            if (this.csrfToken) {
                this.socket.auth.csrf_token = this.csrfToken;
            }
        });

        // Обработка аутентификации
        this.socket.on('message', (data) => {
            if (data && data.status === 'error' && data.message.includes('CSRF')) {
                console.error('❌ CSRF validation failed');
                this._handleCSRFError();
            }
        });
    }

    _handleCSRFError() {
        // Пробуем обновить CSRF токен и переподключиться
        this.csrfToken = this._getCSRFToken();
        if (this.csrfToken) {
            this.socket.auth.csrf_token = this.csrfToken;
            this.socket.disconnect().connect();
        } else {
            console.error('Failed to refresh CSRF token');
            // Можно добавить callback для обработки ошибки на уровне приложения
            if (this.options.onCSRFError) {
                this.options.onCSRFError();
            }
        }
    }

    connect() {
        if (!this.socket.connected) {
            this.socket.connect();
        }
        return this;
    }

    disconnect() {
        this.socket.disconnect();
        return this;
    }

    // Прокси для emit с добавлением CSRF токена
    emit(event, data) {
        const secureData = {
            ...(typeof data === 'object' ? data : { data }),
            csrf_token: this.csrfToken
        };
        this.socket.emit(event, secureData);
        return this;
    }

    // Прокси для on
    on(event, callback) {
        this.socket.on(event, callback);
        return this;
    }

    // Прокси для off
    off(event, callback) {
        this.socket.off(event, callback);
        return this;
    }

    // Получение статуса подключения
    get connected() {
        return this.socket.connected;
    }

    // Получение ID сокета
    get id() {
        return this.socket.id;
    }
}