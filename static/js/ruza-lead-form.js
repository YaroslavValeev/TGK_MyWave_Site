/**
 * MyWave Ruza Camp — квалификационная форма заявки.
 * UTM/referrer, условное поле ограничений, source_cta, отправка в /analytics/log.
 */
(function () {
  async function getFreshCsrfToken() {
    try {
      var resp = await fetch('/api/csrf-token', { credentials: 'same-origin' });
      var data = await resp.json();
      return (data && data.csrf_token) ? data.csrf_token : '';
    } catch (e) {
      return '';
    }
  }

  function getUrlParams() {
    var params = {};
    var search = window.location.search || '';
    if (search.indexOf('?') === 0) search = search.slice(1);
    search.split('&').forEach(function (pair) {
      var parts = pair.split('=');
      if (parts[0]) params[decodeURIComponent(parts[0])] = decodeURIComponent(parts[1] || '');
    });
    return params;
  }

  function generateRequestId() {
    return 'ruza_' + Date.now() + '_' + Math.random().toString(36).slice(2, 10);
  }

  function fillHiddenFields(form) {
    var params = getUrlParams();
    var set = function (name, value) {
      var inp = form.querySelector('input[name="' + name + '"]');
      if (inp) inp.value = value || '';
    };
    set('page_url', window.location.href);
    set('request_id', generateRequestId());
    set('utm_source', params.utm_source);
    set('utm_medium', params.utm_medium);
    set('utm_campaign', params.utm_campaign);
    set('utm_content', params.utm_content);
    set('utm_term', params.utm_term);
    set('referrer', document.referrer || '');
    set('user_agent', navigator.userAgent || '');
    var scInp = form.querySelector('input[name="source_cta"]');
    if (scInp && !scInp.value && form.closest && form.closest('#ruza-form-section')) {
      scInp.value = 'page_form';
    }
  }

  function setupSourceCtaCapture() {
    document.addEventListener('click', function (e) {
      var btn = e.target && e.target.closest ? e.target.closest('[data-modal="modalRuzaCamp"]') : null;
      if (btn) {
        var sc = btn.getAttribute('data-source-cta');
        if (sc) {
          document.querySelectorAll('.ruza-lead-form input[name="source_cta"]').forEach(function (inp) {
            inp.value = sc;
          });
        }
      }
    }, true);
  }

  function setupRestrictionsToggle() {
    document.querySelectorAll('.ruza-lead-form').forEach(function (form) {
      var radios = form.querySelectorAll('input[name="has_restrictions"]');
      var detail = form.querySelector('.js-ruza-restrictions-detail');
      var textarea = form.querySelector('.js-ruza-restrictions-textarea');
      if (!detail || !radios.length) return;

      function toggle() {
        var yes = form.querySelector('input[name="has_restrictions"][value="yes"]');
        if (yes && yes.checked) {
          detail.style.display = '';
          if (textarea) textarea.required = true;
        } else {
          detail.style.display = 'none';
          if (textarea) { textarea.required = false; textarea.value = ''; }
        }
      }
      radios.forEach(function (r) {
        r.addEventListener('change', toggle);
      });
      toggle();
    });
  }

  function setupCampDatePickers() {
    var START = '2026-08-10';
    var END = '2026-08-23';
    document.querySelectorAll('.ruza-lead-form').forEach(function (form) {
      var inp = form.querySelector('.js-ruza-camp-date');
      if (!inp) return;

      // Do not double-init if modal opens multiple times
      if (inp._flatpickr) return;

      if (typeof window.flatpickr !== 'function') {
        // Flatpickr is expected to be present globally (used in booking.js).
        // If it is not, we still keep the input readonly to avoid invalid dates.
        return;
      }

      window.flatpickr(inp, {
        locale: 'ru',
        dateFormat: 'Y-m-d',
        altInput: true,
        altFormat: 'd.m.Y',
        disableMobile: true,
        defaultDate: START,
        minDate: START,
        maxDate: END,
        // Visually highlight the full allowed window
        onDayCreate: function (dObj, dStr, fp, dayElem) {
          try {
            var dayDate = dayElem.dateObj; // Date
            var yyyy = dayDate.getFullYear();
            var mm = String(dayDate.getMonth() + 1).padStart(2, '0');
            var dd = String(dayDate.getDate()).padStart(2, '0');
            var iso = yyyy + '-' + mm + '-' + dd;
            if (iso >= START && iso <= END) {
              dayElem.classList.add('ruza-allowed-day');
            }
          } catch (e) {
            // ignore
          }
        }
      });
    });
  }

  function resetCampDateToDefault(form) {
    var START = '2026-08-10';
    var inp = form ? form.querySelector('.js-ruza-camp-date') : null;
    if (!inp) return;
    try {
      if (inp._flatpickr) {
        inp._flatpickr.setDate(START, true);
      } else {
        inp.value = START;
      }
    } catch (e) {
      inp.value = START;
    }
  }

  function collectFormData(form) {
    var fd = new FormData(form);
    var data = {};
    fd.forEach(function (v, k) {
      if (k === 'csrf_token') return;
      data[k] = v;
    });
    return data;
  }

  function showToastMessage(message, ms) {
    var toast = document.getElementById('toast');
    if (!toast) return;
    toast.textContent = message;
    toast.classList.remove('hidden');
    toast.classList.add('show');
    setTimeout(function () {
      toast.classList.remove('show');
      toast.classList.add('hidden');
    }, ms || 5000);
  }

  function init() {
    setupSourceCtaCapture();

    document.querySelectorAll('.ruza-lead-form').forEach(function (form) {
      fillHiddenFields(form);
    });
    setupRestrictionsToggle();
    setupCampDatePickers();

    document.querySelectorAll('.js-ruza-lead-form').forEach(function (form) {
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        if (form.dataset.submitting === '1') return;
        form.dataset.submitting = '1';
        var submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) submitBtn.disabled = true;

        var fd = new FormData(form);
        var meta = collectFormData(form);
        var eventName = form.dataset.event || 'ruza_lead';
        var showcaseId = form.dataset.showcaseId || 'mywave_ruza_camp';
        var successMsg =
          form.dataset.success ||
          'Заявка получена и отправлена на обработку. Мы свяжемся с вами в течение 24 часов.';

        var payload = {
          event: eventName,
          label: 'ruza_lead',
          phone: fd.get('phone') || '',
          user_key: fd.get('phone') || fd.get('email') || '',
          channel: 'web',
          showcase_id: showcaseId,
          meta: meta
        };

        // B) Booking record (camp) — required part of the flow
        var campDate = fd.get('camp_date') || '';
        var campTime = fd.get('camp_time') || '12:00';
        var bookingBody = {
          date: campDate,
          time: campTime,
          name: fd.get('parent_name') || fd.get('participant_name') || '',
          phone: fd.get('phone') || '',
          service_type: 'camp'
        };

        // Сначала бронирование, потом аналитика: параллельно оба дергают Google Sheets
        // через один httplib2-сокет → под eventlet «Second simultaneous read on fileno».
        getFreshCsrfToken().then(function (token) {
          return fetch('/api/calendar/book', {
            method: 'POST',
            headers: {
              'Accept': 'application/json',
              'Content-Type': 'application/json',
              'X-CSRFToken': token
            },
            credentials: 'same-origin',
            body: JSON.stringify(bookingBody)
          }).then(function (r) {
            if (!r) throw new Error('no_response');
            return r.text().then(function (t) {
              var data = null;
              try { data = t ? JSON.parse(t) : null; } catch (e) { data = null; }
              var bookingRes = { ok: r.ok, status: r.status, data: data };
              return fetch('/analytics/log', {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  'X-CSRFToken': token || ''
                },
                credentials: 'same-origin',
                body: JSON.stringify(payload)
              }).catch(function () { /* не ломаем UX */ }).then(function () {
                return bookingRes;
              });
            });
          });
        }).then(function (res) {
          if (!res.ok) {
            var serverMsg =
              (res.data && (res.data.error || res.data.message)) ? (res.data.error || res.data.message) : '';
            throw new Error(serverMsg || 'Ошибка отправки. Проверьте дату и попробуйте ещё раз.');
          }

          // Повторная отправка той же заявки (camp): API отдаёт 200 + idempotent + короткий текст
          var displayMsg = successMsg;
          if (res.data && res.data.idempotent && res.data.message) {
            displayMsg = res.data.message;
          }

          var msgEl = form.querySelector('.js-ruza-form-message');
          if (msgEl) {
            msgEl.textContent = displayMsg;
            msgEl.style.color = 'var(--mw-brand, #35C0CD)';
          }
          showToastMessage(displayMsg, 5000);

          form.reset();
          fillHiddenFields(form);
          setupRestrictionsToggle();
          setupCampDatePickers();
          resetCampDateToDefault(form);

          var modal = form.closest('.modal');
          if (modal) {
            modal.classList.add('hidden');
            modal.classList.remove('show');
          }
        }).catch(function () {
          var msgEl = form.querySelector('.js-ruza-form-message');
          var err = 'Ошибка отправки. Напишите в чат или позвоните +7 916 011 71 79.';
          if (msgEl) { msgEl.textContent = err; msgEl.style.color = '#c00'; }
          showToastMessage(err, 5000);
        }).finally(function () {
          form.dataset.submitting = '0';
          if (submitBtn) submitBtn.disabled = false;
        });
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
