// socket-status.js (ES6)
// Требует подключения socket.io.js до этого файла

export class SocketStatus {
    constructor(socket, indicatorSelector = '#socket-status-indicator') {
        this.socket = socket;
        this.indicator = document.querySelector(indicatorSelector);
        this.init();
    }

    setStatus(status, color) {
        if (this.indicator) {
            this.indicator.textContent = status;
            this.indicator.style.background = color;
        }
    }

    init() {
        this.socket.on('connect', () => {
            this.setStatus('Онлайн', '#28a745');
        });
        this.socket.on('disconnect', () => {
            this.setStatus('Оффлайн', '#dc3545');
        });
        this.socket.on('reconnect_attempt', () => {
            this.setStatus('Переподключение...', '#ffc107');
        });
        this.socket.on('reconnect', () => {
            this.setStatus('Онлайн', '#28a745');
        });
        this.socket.on('reconnect_error', () => {
            this.setStatus('Ошибка соединения', '#dc3545');
        });
        this.socket.on('reconnect_failed', () => {
            this.setStatus('Не удалось подключиться', '#dc3545');
        });
    }
}

// Для быстрого старта можно добавить в base.html:
// <div id="socket-status-indicator" style="position:fixed;bottom:10px;right:10px;padding:8px 16px;border-radius:8px;color:#fff;font-weight:bold;z-index:9999;background:#dc3545;">Оффлайн</div> 