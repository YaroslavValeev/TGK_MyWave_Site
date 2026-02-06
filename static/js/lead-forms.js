/**
 * Лид-формы: Camp, Тренер на выезде, Консалтинг.
 * Поддержка .btn-lead[data-lead] и [data-open-lead]. Capture + stopImmediatePropagation — без мигания.
 */
document.addEventListener('DOMContentLoaded', () => {
  const leadTypeToModalId = {
    camp: 'lead-modal-camp',
    'coach-trip': 'lead-modal-coach-trip',
    travel: 'lead-modal-coach-trip',
    consulting: 'lead-modal-consulting',
  };

  function hideLeadModals() {
    document.querySelectorAll('.lead-modal').forEach(modal => {
      modal.classList.remove('show');
      modal.classList.add('hidden');
      modal.style.display = 'none';
      modal.setAttribute('aria-hidden', 'true');
    });
    document.body.classList.remove('modal-open');
    document.body.style.overflow = '';
  }

  function showLeadModal(modal) {
    if (!modal) return;
    hideLeadModals();
    modal.classList.remove('hidden');
    modal.classList.add('show');
    modal.style.display = 'flex';
    modal.setAttribute('aria-hidden', 'false');
    document.body.classList.add('modal-open');
    document.body.style.overflow = 'hidden';
  }

  const openButtons = document.querySelectorAll('[data-open-lead], .btn-lead[data-lead]');

  openButtons.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopImmediatePropagation();
      e.stopPropagation();

      const leadType = btn.dataset.lead || btn.dataset.openLead;
      const modalId = btn.dataset.modalId || leadTypeToModalId[leadType];
      if (!modalId) return;

      const modal = document.getElementById(modalId);
      showLeadModal(modal);
    }, true);
  });

  document.querySelectorAll('[data-close-lead], .lead-modal .modal-close, .lead-modal .lead-modal-close').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopImmediatePropagation();
      e.stopPropagation();
      hideLeadModals();
    }, true);
  });

  document.querySelectorAll('.lead-modal').forEach(modal => {
    modal.addEventListener('click', (e) => {
      if (e.target !== modal) return;
      e.stopPropagation();
      hideLeadModals();
    });
  });

  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    const open = document.querySelector('.lead-modal.show:not(.hidden)');
    if (open) hideLeadModals();
  });

  const successIds = { 'coach-trip': 'lead-coach-success', 'consulting': 'lead-consulting-success', 'camp': 'lead-camp-success' };
  document.getElementById('lead-form-coach-trip') && document.getElementById('lead-form-coach-trip').addEventListener('submit', function (e) {
    e.preventDefault();
    var form = e.target;
    var data = { type: 'coach_trip', location: form.location && form.location.value, dates: form.dates && form.dates.value, format: form.format && form.format.value, level: form.level && form.level.value, equipment: form.equipment && form.equipment.value, contact: form.contact && form.contact.value };
    sendLead(data, 'coach-trip');
  });
  document.getElementById('lead-form-consulting') && document.getElementById('lead-form-consulting').addEventListener('submit', function (e) {
    e.preventDefault();
    var form = e.target;
    var data = { type: 'consulting', topic: form.topic && form.topic.value, task: form.task && form.task.value, contact: form.contact && form.contact.value };
    sendLead(data, 'consulting');
  });
  document.getElementById('lead-form-camp') && document.getElementById('lead-form-camp').addEventListener('submit', function (e) {
    e.preventDefault();
    var form = e.target;
    var data = { type: 'camp', dates: form.dates && form.dates.value, level: form.level && form.level.value, goal: form.goal && form.goal.value, budget: form.budget && form.budget.value, contact: form.contact && form.contact.value };
    sendLead(data, 'camp');
  });

  function sendLead(data, leadKey) {
    var formEl = (leadKey === 'coach-trip' ? document.getElementById('lead-form-coach-trip') : leadKey === 'consulting' ? document.getElementById('lead-form-consulting') : document.getElementById('lead-form-camp'));
    var successEl = document.getElementById(successIds[leadKey]);
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
