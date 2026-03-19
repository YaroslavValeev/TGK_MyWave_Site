/**
 * Надёжное закрытие модалок Camp, CoachTriper, Consulting и других.
 * Делегирование событий — гарантирует работу для всех .modal на странице.
 */
(function () {
  function hideAllModals() {
    document.querySelectorAll('.modal').forEach(function (m) {
      m.classList.remove('show');
      m.classList.add('hidden');
      m.style.display = 'none';
    });
    document.body.style.overflow = 'auto';
  }

  function init() {
    document.addEventListener('click', function (e) {
      if (e.target.classList.contains('close-modal')) {
        e.preventDefault();
        e.stopPropagation();
        hideAllModals();
        return;
      }
      if (e.target.classList.contains('modal')) {
        hideAllModals();
      }
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') hideAllModals();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
