/**
 * P1: Обработка форм заявок в модалках Camp / CoachTriper / Consulting.
 * Отправка в /analytics/log для логирования лидов.
 */
(function () {
  function init() {
    document.querySelectorAll('.modal-lead-form').forEach(function (form) {
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        var eventName = form.dataset.event || 'lead';
        var service = form.dataset.service || '';
        var fd = new FormData(form);
        var meta = {
          service: service,
          name: fd.get('name') || '',
          phone: fd.get('phone') || '',
          comment: fd.get('comment') || '',
          dates: fd.get('dates') || '',
          level: fd.get('level') || '',
          location: fd.get('location') || '',
          task: fd.get('task') || '',
          topic: fd.get('topic') || '',
          video_link: fd.get('video_link') || '',
          goal: fd.get('goal') || ''
        };
        fetch('/analytics/log', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            event: eventName,
            label: service,
            phone: meta.phone,
            user_key: meta.phone,
            channel: 'web',
            meta: meta
          })
        }).then(function (r) {
          if (r.ok) {
            var toast = document.getElementById('toast');
            if (toast) {
              toast.textContent = form.dataset.success || 'Заявка отправлена! Мы свяжемся с вами.';
              toast.classList.remove('hidden');
              setTimeout(function () { toast.classList.add('hidden'); }, 4000);
            }
            form.reset();
            var modal = form.closest('.modal');
            if (modal) {
              modal.classList.remove('show');
              modal.classList.add('hidden');
            }
            document.body.style.overflow = 'auto';
          }
        }).catch(function () {
          var toast = document.getElementById('toast');
          if (toast) {
            toast.textContent = 'Ошибка отправки. Напишите в чат.';
            toast.classList.remove('hidden');
            setTimeout(function () { toast.classList.add('hidden'); }, 4000);
          }
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
