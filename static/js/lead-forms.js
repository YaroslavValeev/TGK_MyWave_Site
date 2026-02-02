/**
 * Лид-формы: Тренер на выезде (data-lead="coach-trip"), Консалтинг (data-lead="consulting").
 * Открытие модалки по клику, отправка POST /api/lead, показ success.
 */
(function () {
  const modalIds = { 'coach-trip': 'lead-modal-coach-trip', 'consulting': 'lead-modal-consulting', 'camp': 'lead-modal-camp' };
  const successIds = { 'coach-trip': 'lead-coach-success', 'consulting': 'lead-consulting-success', 'camp': 'lead-camp-success' };

  function hideLeadModals() {
    ['lead-modal-camp', 'lead-modal-coach-trip', 'lead-modal-consulting'].forEach(function (id) {
      var m = document.getElementById(id);
      if (m) { m.classList.add('hidden'); m.style.display = 'none'; }
    });
    document.body.style.overflow = '';
  }

  function showLeadModal(id) {
    hideLeadModals();
    const el = document.getElementById(id);
    if (el) {
      el.classList.remove('hidden');
      el.style.display = 'flex';
      document.body.style.overflow = 'hidden';
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-lead]').forEach(function (btn) {
      var lead = btn.getAttribute('data-lead');
      if (!modalIds[lead]) return;
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        showLeadModal(modalIds[lead]);
      });
    });

    document.querySelectorAll('.lead-modal-close').forEach(function (btn) {
      btn.addEventListener('click', hideLeadModals);
    });
    document.querySelectorAll('#lead-modal-camp, #lead-modal-coach-trip, #lead-modal-consulting').forEach(function (modal) {
      modal.addEventListener('click', function (e) {
        if (e.target === modal) hideLeadModals();
      });
    });

    document.getElementById('lead-form-coach-trip') && document.getElementById('lead-form-coach-trip').addEventListener('submit', function (e) {
      e.preventDefault();
      var form = e.target;
      var data = { type: 'coach_trip', location: form.location.value, dates: form.dates.value, format: form.format.value, level: form.level.value, equipment: form.equipment.value, contact: form.contact.value };
      sendLead(data, 'coach-trip');
    });
    document.getElementById('lead-form-consulting') && document.getElementById('lead-form-consulting').addEventListener('submit', function (e) {
      e.preventDefault();
      var form = e.target;
      var data = { type: 'consulting', topic: form.topic.value, task: form.task.value, contact: form.contact.value };
      sendLead(data, 'consulting');
    });
    document.getElementById('lead-form-camp') && document.getElementById('lead-form-camp').addEventListener('submit', function (e) {
      e.preventDefault();
      var form = e.target;
      var data = { type: 'camp', dates: form.dates.value, level: form.level.value, goal: form.goal.value, budget: form.budget.value, contact: form.contact.value };
      sendLead(data, 'camp');
    });

    function sendLead(data, leadKey) {
      var formEl = (leadKey === 'coach-trip' ? document.getElementById('lead-form-coach-trip') : leadKey === 'consulting' ? document.getElementById('lead-form-consulting') : document.getElementById('lead-form-camp'));
      var successEl = document.getElementById(successIds[leadKey]);
      var modalEl = document.getElementById(modalIds[leadKey]);
      var csrfEl = document.querySelector('meta[name="csrf-token"]');
      var csrf = csrfEl ? csrfEl.getAttribute('content') : '';
      fetch('/api/lead', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
        credentials: 'same-origin',
        body: JSON.stringify(data)
      }).then(function (r) {
        if (!r.ok) return r.json().then(function (j) { throw new Error(j.error || 'Ошибка отправки'); });
        return r.json();
      }).then(function () {
        if (formEl) formEl.classList.add('hidden');
        if (successEl) { successEl.classList.remove('hidden'); successEl.textContent = 'Заявка отправлена. Мы свяжемся с вами в ближайшее время.'; }
      }).catch(function (err) {
        alert(err.message || 'Не удалось отправить заявку.');
      });
    }
  });
})();
