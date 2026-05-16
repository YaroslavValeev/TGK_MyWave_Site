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

  /** База каталога иллюстраций: data-checklist-asset-base на .wake-checklist или legacy window var */
  function getChecklistAssetBase(container) {
    var root = container || document.querySelector('.wake-checklist');
    var b = (root && root.getAttribute('data-checklist-asset-base')) ||
      (typeof window !== 'undefined' && window.__MW_CHECKLIST_ASSET_BASE__) ||
      '';
    b = String(b).replace(/\/+$/, '');
    if (b) return b + '/';
    return '/static/images/Project/Cards/checklist/';
  }

  /** Соответствие id чекбокса → иллюстрация (смысл карточки без чтения текста) */
  var CHECKLIST_CARD_BACKGROUNDS = {
    // Судьи (персона, скоринг, споры, брендинг судей, онлайн, ИИ)
    'judge-1-1': 'judges/judges_online_scoring.webp',
    'judge-1-2': 'media/media_replay_highlights_system.webp',
    'judge-1-3': 'judges/judges_online_scoring.webp',
    'judge-1-4': 'media/media_broadcast_graphics_branding.webp',
    'judge-1-5': 'judges/judges_online_scoring.webp',
    'judge-1-6': 'judges/judges_neuro_assistant.webp',
    // Акватория
    'aqua-2-1': 'aquatory/aquatory_safety_clean_water.webp',
    'aqua-2-2': 'aquatory/aquatory_depth_measurement.webp',
    'aqua-2-3': 'aquatory/aquatory_wind_direction_control.webp',
    'aqua-2-4': 'aquatory/aquatory_wave_stability.webp',
    'aqua-2-5': 'aquatory/aquatory_course_marking.webp',
    'aqua-2-6': 'aquatory/aquatory_rescue_team_on_duty.webp',
    'aqua-2-7': 'aquatory/aquatory_pre_event_training.webp',
    'aqua-2-8': 'media/media_logistics_support.webp',
    'aqua-2-9': 'aquatory/aquatory_types_comparison.webp',
    // Площадка участников
    'area-3-1': 'participants/participants_toilet_facility.webp',
    'area-3-2': 'participants/participant_shower_zone.webp',
    'area-3-3': 'participants/participant_sauna_recovery.webp',
    'area-3-4': 'participants/participant_changing_room.webp',
    'area-3-5': 'participants/participant_drying_wetsuits.webp',
    'area-3-6': 'media/media_logistics_support.webp',
    'area-3-7': 'participants/participant_healthy_food_zone.webp',
    'area-3-8': 'participants/participant_team_coach_area.webp',
    'area-3-9': 'participants/participant_warmup_training_zone.webp',
    'area-3-10': 'participants/participant_recovery_massage.webp',
    'area-3-11': 'media/media_logistics_support.webp',
    'area-3-12': 'aquatory/aquatory_course_marking.webp',
    'area-3-13': 'viewers/viewers_replay_screens.webp',
    // Организаторы
    'org-4-1': 'organizers/organizer_operations_hq.webp',
    'org-4-2': 'media/media_postproduction_archive.webp',
    'org-4-3': 'organizers/organizers_meeting_discussion.webp',
    'org-4-4': 'partners/partner_brand_integration_plan.webp',
    // Зона судей на площадке
    'judge-area-5-1': 'judges/judges_online_scoring.webp',
    'judge-area-5-2': 'judges/judges_zone_rest_recovery.webp',
    'judge-area-5-3': 'media/media_replay_highlights_system.webp',
    'judge-area-5-4': 'judges/judges_zone_wifi_charging.webp',
    'judge-area-5-5': 'media/media_logistics_support.webp',
    // СМИ
    'media-6-1': 'media/media_press_conference_interview.webp',
    'media-6-2': 'media/media_interview_zone_alt.webp',
    'media-6-3': 'media/media_photo_video_point.webp',
    'media-6-4': 'media/media_logistics_support.webp',
    'media-6-5': 'media/media_commentary_booth.webp',
    // Зрители
    'viewers-7-1': 'app/app_event_information.webp',
    'viewers-7-2': 'viewers/viewers_fan_activities.webp',
    'viewers-7-3': 'viewers/viewers_comfort_viewing_area_alt.webp',
    'viewers-7-4': 'viewers/viewers_weather_protection.webp',
    'viewers-7-5': 'viewers/viewers_replay_screens.webp',
    'viewers-7-6': 'viewers/viewers_food_court_drinks.webp',
    'viewers-7-7': 'participants/participant_warmup_training_zone.webp',
    'viewers-7-8': 'judges/judges_zone_wifi_charging.webp',
    'viewers-7-9': 'participants/participants_toilet_facility.webp',
    'viewers-7-10': 'viewers/viewers_merch_zone.webp',
    // Прочее
    'music-8': 'media/media_live_switching_director.webp',
    'media-prod-9': 'media/media_multicamera_drone_coverage.webp',
    // Сайт / приложение
    'app-10-1': 'app/app_event_information.webp',
    'app-10-2': 'app/app_live_scoring_results.webp',
    'app-10-3': 'app/app_event_information_alt.webp',
    'app-10-4': 'app/app_interactive_map_territory.webp',
    'app-10-5': 'app/app_online_voting_contests.webp',
    'app-10-6': 'app/app_live_streaming_event.webp',
    'app-10-7': 'app/app_registration_accreditation.webp',
    'app-10-8': 'app/app_registration_accreditation_alt_2.webp',
    'app-10-9': 'app/app_social_media_integration.webp',
    'app-10-10': 'aquatory/aquatory_wind_direction_monitoring_alt.webp',
    // Партнёры
    'partner-11-1': 'partners/partner_value_proposition.webp',
    'partner-11-2': 'partners/partner_kpi_commitments.webp',
    'partner-11-3': 'partners/partner_brand_integration_plan.webp',
    'partner-11-4': 'media/media_realtime_social_content.webp',
    'partner-11-5': 'partners/partner_hospitality_support.webp',
    'partner-11-6': 'organizers/organizer_operations_hq.webp',
    'partner-11-7': 'media/media_photo_video_point.webp',
    'partner-11-8': 'partners/partner_post_event_report_alt.webp',
    'partner-11-9': 'organizers/organizers_meeting_discussion.webp'
  };

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

  /** Двухколоночная вёрстка: текст слева, иллюстрация справа */
  function ensureSplitCardLayout(container) {
    container.querySelectorAll('.wake-checklist__card').forEach(function(card) {
      if (card.querySelector('.wake-checklist__card-inner')) return;
      var inner = document.createElement('div');
      inner.className = 'wake-checklist__card-inner';
      while (card.firstChild) {
        inner.appendChild(card.firstChild);
      }
      var art = document.createElement('div');
      art.className = 'wake-checklist__card-art';
      art.setAttribute('aria-hidden', 'true');
      card.appendChild(inner);
      card.appendChild(art);
    });
  }

  function applyCardBackgrounds(container) {
    var base = getChecklistAssetBase(container);
    var checkboxes = container.querySelectorAll('.wake-checklist__checkbox');
    checkboxes.forEach(function(cb) {
      var card = getCard(cb);
      if (!card) return;
      var file = CHECKLIST_CARD_BACKGROUNDS[cb.id];
      if (!file) return;
      var imgUrl = base + file;
      var cssUrl = 'url("' + imgUrl + '")';
      card.style.setProperty('--checklist-card-bg', cssUrl);
      var art = card.querySelector('.wake-checklist__card-art');
      if (!art) return;
      art.style.backgroundImage = cssUrl;
      art.setAttribute('data-checklist-bg', 'pending');
      var probe = new Image();
      probe.onload = function() { art.setAttribute('data-checklist-bg', 'ok'); };
      probe.onerror = function() { art.setAttribute('data-checklist-bg', 'missing'); };
      probe.src = imgUrl;
    });
  }

  var PRIORITY_CHIP_LABELS = {
    critical: 'Критично',
    base: 'Базовый',
    recommended: 'Рекомендуется'
  };

  function ensurePriorityChip(header, priority) {
    if (!header || header.querySelector('.wake-checklist__priority-chip')) return;
    var cb = header.querySelector('.wake-checklist__checkbox');
    if (!cb) return;
    var chip = document.createElement('span');
    chip.className = 'wake-checklist__priority-chip wake-checklist__priority-chip--' + priority;
    chip.textContent = PRIORITY_CHIP_LABELS[priority] || PRIORITY_CHIP_LABELS.base;
    chip.setAttribute('title', chip.textContent);
    cb.insertAdjacentElement('afterend', chip);
  }

  /** Длинное описание: свёртка + кнопка «Показать полностью» */
  function setupExpandableBodies(container) {
    function attachToggle(body, inner) {
      if (body.querySelector('.wake-checklist__card-expand')) return;
      inner.classList.add('is-clamped');
      if (inner.scrollHeight <= inner.clientHeight + 6) {
        inner.classList.remove('is-clamped');
        return;
      }
      var card = body.closest('.wake-checklist__card');
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'wake-checklist__card-expand';
      btn.setAttribute('aria-expanded', 'false');
      btn.innerHTML =
        '<span class="wake-checklist__card-expand__text">Показать полностью</span>' +
        '<span class="wake-checklist__card-expand__icon" aria-hidden="true"></span>';
      body.appendChild(btn);
      btn.addEventListener('click', function(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        if (!card) return;
        var textEl = btn.querySelector('.wake-checklist__card-expand__text');
        if (card.classList.contains('wake-checklist__card--expanded')) {
          card.classList.remove('wake-checklist__card--expanded');
          inner.classList.add('is-clamped');
          btn.setAttribute('aria-expanded', 'false');
          if (textEl) textEl.textContent = 'Показать полностью';
        } else {
          card.classList.add('wake-checklist__card--expanded');
          inner.classList.remove('is-clamped');
          btn.setAttribute('aria-expanded', 'true');
          if (textEl) textEl.textContent = 'Свернуть';
        }
      });
    }

    container.querySelectorAll('.wake-checklist__card-body').forEach(function(body) {
      if (!body.innerHTML.trim()) return;
      if (body.querySelector('.wake-checklist__card-body-inner')) return;
      var inner = document.createElement('div');
      inner.className = 'wake-checklist__card-body-inner';
      while (body.firstChild) {
        inner.appendChild(body.firstChild);
      }
      body.appendChild(inner);
      void inner.offsetHeight;
      requestAnimationFrame(function() {
        attachToggle(body, inner);
      });
    });
  }

  function bindCardParallax(container) {
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      return;
    }
    if (window.matchMedia && window.matchMedia('(pointer: coarse)').matches) {
      return;
    }
    container.querySelectorAll('.wake-checklist__card-art').forEach(function(art) {
      art.addEventListener('mousemove', function(ev) {
        var rect = art.getBoundingClientRect();
        var x = ((ev.clientX - rect.left) / rect.width - 0.5) * 12;
        var y = ((ev.clientY - rect.top) / rect.height - 0.5) * 12;
        art.style.setProperty('--checklist-card-shift-x', x.toFixed(1) + 'px');
        art.style.setProperty('--checklist-card-shift-y', y.toFixed(1) + 'px');
      });
      art.addEventListener('mouseleave', function() {
        art.style.setProperty('--checklist-card-shift-x', '0px');
        art.style.setProperty('--checklist-card-shift-y', '0px');
      });
    });
  }

  function init() {
    var container = document.querySelector('.wake-checklist');
    if (!container) return;

    ensureSplitCardLayout(container);

    // Strip numbers from titles
    container.querySelectorAll('.wake-checklist__card-title').forEach(function(el) {
      el.textContent = stripTitleNumber(el.textContent);
    });
    applyCardBackgrounds(container);

    var checkboxes = container.querySelectorAll('.wake-checklist__checkbox');

    // Restore state & apply data-priority/data-weight
    checkboxes.forEach(function(cb) {
      var cfg = PRIORITY_OVERRIDES[cb.id] || { priority: DEFAULT_PRIORITY, weight: DEFAULT_WEIGHT };
      var card = getCard(cb);
      if (card) {
        card.setAttribute('data-priority', cfg.priority);
        card.setAttribute('data-weight', String(cfg.weight));
      }
      var header = card && card.querySelector('.wake-checklist__card-header');
      if (header) ensurePriorityChip(header, cfg.priority);
      var saved = loadState(cb.id);
      cb.checked = saved;
      updateCardCompleted(getCard(cb), saved);
    });

    setupExpandableBodies(container);
    bindCardParallax(container);

    // Click delegation: карточка целиком кликабельна (кроме кнопки раскрытия)
    container.addEventListener('click', function(ev) {
      if (ev.target.closest && ev.target.closest('.wake-checklist__card-expand')) {
        return;
      }
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
