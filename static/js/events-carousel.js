document.addEventListener('DOMContentLoaded', () => {
  const slider = document.getElementById('events-slider');
  const prev = document.getElementById('events-prev');
  const next = document.getElementById('events-next');

  if (!slider || !prev || !next) return;

  const cards = Array.from(slider.querySelectorAll('.event-card'));
  if (cards.length <= 1) {
    prev.style.display = 'none';
    next.style.display = 'none';
    return;
  }

  function getScrollAmount() {
    const first = cards[0];
    const cardWidth = first.getBoundingClientRect().width;
    const styles = window.getComputedStyle(slider);
    const gap = parseFloat(styles.columnGap || styles.gap || '16') || 16;
    return cardWidth + gap;
  }

  prev.addEventListener('click', () => {
    slider.scrollBy({ left: -getScrollAmount(), behavior: 'smooth' });
  });
  next.addEventListener('click', () => {
    slider.scrollBy({ left: getScrollAmount(), behavior: 'smooth' });
  });
});

