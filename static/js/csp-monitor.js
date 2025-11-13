/**
 * CSP Violation Monitor
 * 
 * Мониторит нарушения Content Security Policy в браузере
 * и отправляет их на сервер для логирования.
 * 
 * Подключается в base.html:
 *   <script src="{{ url_for('static', filename='js/csp-monitor.js') }}" nonce="{{ g.csp_nonce }}"></script>
 */

(function() {
  'use strict';

  const CSPMonitor = {
    // Конфигурация
    config: {
      // URL для отправки нарушений
      endpoint: '/api/csp-violations',
      // Максимум нарушений в буфере перед отправкой
      batchSize: 5,
      // Интервал отправки буфера (мс)
      flushInterval: 30000,
      // Активен ли мониторинг
      enabled: true
    },

    // Состояние
    state: {
      violations: [],
      flushTimer: null,
      sessionId: null
    },

    /**
     * Инициализация мониторинга
     */
    init() {
      if (!this.config.enabled) {
        console.debug('[CSP Monitor] Мониторинг отключён');
        return;
      }

      // Генерируем или загружаем sessionId
      this.state.sessionId = this._getOrCreateSessionId();

      // Подписываемся на события нарушения CSP
      document.addEventListener('securitypolicyviolation', 
        (event) => this._handleViolation(event), true);

      // Устанавливаем периодическую отправку
      this._startPeriodicFlush();

      console.debug('[CSP Monitor] Инициализирован (sessionId: ' + 
        this.state.sessionId.substring(0, 8) + '...)');
    },

    /**
     * Обработчик нарушения CSP
     */
    _handleViolation(event) {
      const violation = {
        timestamp: new Date().toISOString(),
        violatedDirective: event.violatedDirective,
        blockedURI: event.blockedURI || 'unknown',
        sourceFile: event.sourceFile || '',
        lineNumber: event.lineNumber || 0,
        columnNumber: event.columnNumber || 0,
        originalPolicy: event.originalPolicy || '',
        statusCode: event.statusCode || 0,
        disposition: event.disposition || 'enforce',
        effectiveDirective: event.effectiveDirective || ''
      };

      // Логируем в консоль (в разработке)
      console.warn('[CSP Violation]', violation);

      // Добавляем в буфер
      this.state.violations.push(violation);

      // Если буфер переполнился, отправляем
      if (this.state.violations.length >= this.config.batchSize) {
        this._flush();
      }
    },

    /**
     * Отправляет накопленные нарушения на сервер
     */
    _flush() {
      if (this.state.violations.length === 0) {
        return;
      }

      const violations = [...this.state.violations];
      this.state.violations = [];

      // Отменяем отложенный таймер
      if (this.state.flushTimer) {
        clearTimeout(this.state.flushTimer);
        this.state.flushTimer = null;
      }

      // Отправляем
      fetch(this.config.endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify({
          sessionId: this.state.sessionId,
          url: window.location.href,
          userAgent: navigator.userAgent,
          violations: violations,
          count: violations.length
        }),
        keepalive: true
      }).catch(err => {
        // Тихо игнорируем ошибки отправки (не засоряем консоль)
        console.debug('[CSP Monitor] Ошибка отправки: ' + err.message);
      });

      if (violations.length > 0) {
        console.info('[CSP Monitor] Отправлено ' + violations.length + ' нарушений');
      }

      // Перезапускаем таймер
      this._startPeriodicFlush();
    },

    /**
     * Запускает периодическую отправку
     */
    _startPeriodicFlush() {
      this.state.flushTimer = setTimeout(() => {
        this._flush();
      }, this.config.flushInterval);
    },

    /**
     * Получает или создаёт sessionId
     */
    _getOrCreateSessionId() {
      const key = 'csp_monitor_session_id';
      let id = sessionStorage.getItem(key);
      
      if (!id) {
        // Генерируем UUID v4
        id = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
          const r = Math.random() * 16 | 0;
          const v = c === 'x' ? r : (r & 0x3 | 0x8);
          return v.toString(16);
        });
        sessionStorage.setItem(key, id);
      }
      
      return id;
    },

    /**
     * Завершить мониторинг (опционально)
     */
    destroy() {
      if (this.state.flushTimer) {
        clearTimeout(this.state.flushTimer);
        this.state.flushTimer = null;
      }
      // Отправляем оставшиеся нарушения
      this._flush();
    }
  };

  // Инициализируем при загрузке DOM
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => CSPMonitor.init());
  } else {
    CSPMonitor.init();
  }

  // Экспортируем глобально (для отладки в консоли)
  window.CSPMonitor = CSPMonitor;

})();
