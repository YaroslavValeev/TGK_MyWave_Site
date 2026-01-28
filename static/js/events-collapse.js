document.addEventListener('DOMContentLoaded', () => {
  const toggleButton = document.getElementById('toggle-empty-months');
  const emptyMonths = Array.from(document.querySelectorAll('.events-month.is-empty'));

  if (!toggleButton) return;

  if (emptyMonths.length === 0) {
    toggleButton.style.display = 'none';
    return;
  }

  let isShowingEmpty = false;

  function setVisibility(nextIsShowingEmpty) {
    isShowingEmpty = nextIsShowingEmpty;
    emptyMonths.forEach((month) => {
      month.style.display = isShowingEmpty ? '' : 'none';
    });
    toggleButton.setAttribute('aria-expanded', String(isShowingEmpty));
    toggleButton.textContent = isShowingEmpty
      ? 'Скрыть месяцы без мероприятий'
      : 'Показать месяцы без мероприятий';
  }

  setVisibility(false);

  toggleButton.addEventListener('click', () => setVisibility(!isShowingEmpty));
});


