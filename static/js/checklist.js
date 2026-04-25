/**
 * Checklist — интерактивная логика чек-листа
 * localStorage, click delegation, weighted progress, reset
 * PRO-конфигурация приоритетов
 */
(function() {
  'use strict';

  // Без префикса для совместимости с ранее сохранённым состоянием
  var STORAGE_KEY_PREFIX = '';

  // PRO-конфигурация: приоритеты по id чекбокса
  // critical = 5, base = 3, recommended = 1
  var PRIORITY_OVERRIDES = {
    // Судьи — base
    'judge-1-1': { priority: 'base', weight: 3 },
    'judge-1-2': { priority: 'base', weight: 3 },
    'judge-1-3': { priority: 'base', weight: 3 },
    'judge-1-4': { priority: 'base', weight: 3 },
    'judge-1-5': { priority: 'base', weight: 3 },
    'judge-1-6': { priority: 'base', weight: 3 },
    // Акватория — critical (безопасность, акватория, спасатели)
    'aqua-2-1': { priority: 'critical', weight: 5 },
    'aqua-2-2': { priority: 'critical', weight: 5 },
    'aqua-2-3': { priority: 'critical', weight: 5 },
    'aqua-2-4': { priority: 'critical', weight: 5 },
    'aqua-2-5': { priority: 'critical', weight: 5 },
    'aqua-2-6': { priority: 'critical', weight: 5 },
    'aqua-2-7': { priority: 'base', weight: 3 },
    'aqua-2-8': { priority: 'base', weight: 3 },
    'aqua-2-9': { priority: 'base', weight: 3 },
    // Площадка — mix
    'area-3-1': { priority: 'base', weight: 3 },
    'area-3-2': { priority: 'base', weight: 3 },
    'area-3-3': { priority: 'recommended', weight: 1 },
    'area-3-4': { priority: 'base', weight: 3 },
    'area-3-5': { priority: 'recommended', weight: 1 },
    'area-3-6': { priority: 'base', weight: 3 },
    'area-3-7': { priority: 'recommended', weight: 1 },
    'area-3-8': { priority: 'recommended', weight: 1 },
    'area-3-9': { priority: 'recommended', weight: 1 },
    'area-3-10': { priority: 'recommended', weight: 1 },
    'area-3-11': { priority: 'recommended', weight: 1 },
    'area-3-12': { priority: 'base', weight: 3 },
    'area-3-13': { priority: 'recommended', weight: 1 },
    // Организаторы — base
    'org-4-1': { priority: 'base', weight: 3 },
    'org-4-2': { priority: 'base', weight: 3 },
    'org-4-3': { priority: 'base', weight: 3 },
    'org-4-4': { priority: 'base', weight: 3 },
    // Судьи территория — base
    'judge-area-5-1': { priority: 'base', weight: 3 },
    'judge-area-5-2': { priority: 'base', weight: 3 },
    'judge-area-5-3': { priority: 'base', weight: 3 },
    'judge-area-5-4': { priority: 'base', weight: 3 },
    'judge-area-5-5': { priority: 'base', weight: 3 },
    // СМИ — media-6-3 critical, остальные base
    'media-6-1': { priority: 'base', weight: 3 },
    'media-6-2': { priority: 'base', weight: 3 },
    'media-6-3': { priority: 'critical', weight: 5 },
    'media-6-4': { priority: 'base', weight: 3 },
    'media-6-5': { priority: 'base', weight: 3 },
    // Зрители — recommended (comfort)
    'viewers-7-1': { priority: 'recommended', weight: 1 },
    'viewers-7-2': { priority: 'recommended', weight: 1 },
    'viewers-7-3': { priority: 'recommended', weight: 1 },
    'viewers-7-4': { priority: 'recommended', weight: 1 },
    'viewers-7-5': { priority: 'recommended', weight: 1 },
    'viewers-7-6': { priority: 'recommended', weight: 1 },
    'viewers-7-7': { priority: 'recommended', weight: 1 },
    'viewers-7-8': { priority: 'recommended', weight: 1 },
    'viewers-7-9': { priority: 'recommended', weight: 1 },
    'viewers-7-10': { priority: 'recommended', weight: 1 },
    // Музыка — recommended
    'music-8': { priority: 'recommended', weight: 1 },
    // Медиа-Продакшн — critical
    'media-prod-9': { priority: 'critical', weight: 5 },
    // Сайт/приложение — app-10-6 critical
    'app-10-1': { priority: 'base', weight: 3 },
    'app-10-2': { priority: 'base', weight: 3 },
    'app-10-3': { priority: 'base', weight: 3 },
    'app-10-4': { priority: 'base', weight: 3 },
    'app-10-5': { priority: 'base', weight: 3 },
    'app-10-6': { priority: 'critical', weight: 5 },
    'app-10-7': { priority: 'base', weight: 3 },
    'app-10-8': { priority: 'recommended', weight: 1 },
    'app-10-9': { priority: 'recommended', weight: 1 },
    'app-10-10': { priority: 'recommended', weight: 1 },
    // Работа с партнёрами
    'partner-11-1': { priority: 'base', weight: 3 },
    'partner-11-2': { priority: 'critical', weight: 5 },
    'partner-11-3': { priority: 'base', weight: 3 },
    'partner-11-4': { priority: 'base', weight: 3 },
    'partner-11-5': { priority: 'recommended', weight: 1 },
    'partner-11-6': { priority: 'critical', weight: 5 },
    'partner-11-7': { priority: 'base', weight: 3 },
    'partner-11-8': { priority: 'base', weight: 3 },
    'partner-11-9': { priority: 'recommended', weight: 1 }
  };

  var DEFAULT_PRIORITY = 'base';
  var DEFAULT_WEIGHT = 3;

  function getCard(checkbox) {
    return checkbox && checkbox.closest && checkbox.closest('.wake-checklist__card');
  }

  function saveState(id, checked) {
    try {
      var key = STORAGE_KEY_PREFIX ? (STORAGE_KEY_PREFIX + id) : id;
      if (checked) {
        localStorage.setItem(key, 'true');
      } else {
        localStorage.removeItem(key);
      }
    } catch (e) {}
  }

  function loadState(id) {
    try {
      var key = STORAGE_KEY_PREFIX ? (STORAGE_KEY_PREFIX + id) : id;
      return localStorage.getItem(key) === 'true';
    } catch (e) {
      return false;
    }
  }

  function updateCardCompleted(card, checked) {
    if (!card) return;
    if (checked) {
      card.classList.add('wake-checklist__card--completed');
    } else {
      card.classList.remove('wake-checklist__card--completed');
    }
  }

  function recalcProgress() {
    var checkboxes = document.querySelectorAll('.wake-checklist__checkbox');
    var totalWeight = 0;
    var doneWeight = 0;
    var byPriority = { critical: { total: 0, done: 0 }, base: { total: 0, done: 0 }, recommended: { total: 0, done: 0 } };

    checkboxes.forEach(function(cb) {
      var cfg = PRIORITY_OVERRIDES[cb.id] || { priority: DEFAULT_PRIORITY, weight: DEFAULT_WEIGHT };
      var w = cfg.weight || DEFAULT_WEIGHT;
      totalWeight += w;
      byPriority[cfg.priority].total += w;
      if (cb.checked) {
        doneWeight += w;
        byPriority[cfg.priority].done += w;
      }
    });

    var percent = totalWeight > 0 ? Math.round((doneWeight / totalWeight) * 100) : 0;
    var progressEl = document.getElementById('checklist-progress');
    if (!progressEl) return;
    if (doneWeight > 0) {
      progressEl.classList.add('wake-checklist__progress-bar--visible');
    } else {
      progressEl.classList.remove('wake-checklist__progress-bar--visible');
    }
    var bar = progressEl.querySelector('.wake-checklist__progress-bar-fill');
    var percentEl = progressEl.querySelector('.wake-checklist__progress-percent');
    var critEl = progressEl.querySelector('.breakdown-critical');
    var baseEl = progressEl.querySelector('.breakdown-base');
    var recEl = progressEl.querySelector('.breakdown-recommended');

    if (bar) bar.style.width = percent + '%';
    if (percentEl) percentEl.textContent = percent + '%';
    if (critEl) critEl.textContent = byPriority.critical.done + '/' + byPriority.critical.total;
    if (baseEl) baseEl.textContent = byPriority.base.done + '/' + byPriority.base.total;
    if (recEl) recEl.textContent = byPriority.recommended.done + '/' + byPriority.recommended.total;
  }

  function stripTitleNumber(text) {
    if (typeof text !== 'string') return text;
    return text.replace(/^\d+\.\d+\s*/, '').trim();
  }

  function init() {
    var container = document.querySelector('.wake-checklist');
    if (!container) return;

    // Strip numbers from titles
    container.querySelectorAll('.wake-checklist__card-title').forEach(function(el) {
      el.textContent = stripTitleNumber(el.textContent);
    });

    var checkboxes = container.querySelectorAll('.wake-checklist__checkbox');

    // Restore state & apply data-priority/data-weight
    checkboxes.forEach(function(cb) {
      var cfg = PRIORITY_OVERRIDES[cb.id] || { priority: DEFAULT_PRIORITY, weight: DEFAULT_WEIGHT };
      var card = getCard(cb);
      if (card) {
        card.setAttribute('data-priority', cfg.priority);
        card.setAttribute('data-weight', String(cfg.weight));
      }
      var saved = loadState(cb.id);
      cb.checked = saved;
      updateCardCompleted(getCard(cb), saved);
    });

    // Click delegation: карточка целиком кликабельна
    container.addEventListener('click', function(ev) {
      var target = ev.target;
      if (target.matches('a, button, input, label, select, textarea')) return;
      var card = target.closest('.wake-checklist__card');
      if (!card) return;
      var cb = card.querySelector('.wake-checklist__checkbox');
      if (!cb) return;
      cb.checked = !cb.checked;
      updateCardCompleted(card, cb.checked);
      saveState(cb.id, cb.checked);
      recalcProgress();
    });

    // Change on checkbox directly (на случай клика по чекбоксу)
    checkboxes.forEach(function(cb) {
      cb.addEventListener('change', function() {
        var card = getCard(cb);
        updateCardCompleted(card, cb.checked);
        saveState(cb.id, cb.checked);
        recalcProgress();
      });
    });

    // Initial progress
    recalcProgress();

    // Reset button
    var resetBtn = document.querySelector('.js-checklist-reset');
    if (resetBtn) {
      resetBtn.addEventListener('click', function() {
        if (!confirm('Сбросить все отметки?')) return;
        checkboxes.forEach(function(cb) {
          cb.checked = false;
          saveState(cb.id, false);
          updateCardCompleted(getCard(cb), false);
        });
        recalcProgress();
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
