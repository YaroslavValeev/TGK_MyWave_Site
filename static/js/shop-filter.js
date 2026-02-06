document.addEventListener('DOMContentLoaded', function () {
  const filterBtns = document.querySelectorAll('.filter-btn');
  const productCards = document.querySelectorAll('#store-products .product-card');

  function setActive(button) {
    filterBtns.forEach(b => {
      const isActive = (b === button);
      b.classList.toggle('active', isActive);
      b.setAttribute('aria-pressed', isActive ? 'true' : 'false');
    });
  }

  function filter(category) {
    productCards.forEach(card => {
      const cat = card.getAttribute('data-category') || '';
      if (category === 'all' || category === '' || cat === category) {
        card.style.display = '';
      } else {
        card.style.display = 'none';
      }
    });
  }

  filterBtns.forEach(btn => {
    btn.addEventListener('click', function (e) {
      const cat = this.getAttribute('data-category') || 'all';
      setActive(this);
      filter(cat);
    });
    btn.addEventListener('keydown', function (e) {
      // Space or Enter should activate button
      if (e.key === ' ' || e.key === 'Enter') {
        e.preventDefault();
        this.click();
      }
    });
  });

  // Initialize: show all
  // Ensure aria-pressed attributes exist and set initial active button
  let initial = Array.from(filterBtns).find(b => b.classList.contains('active'));
  if (!initial) {
    initial = Array.from(filterBtns).find(b => b.getAttribute('data-category') === 'all') || filterBtns[0];
    // don't assume null — if no buttons, bail out
  }
  if (initial) {
    setActive(initial);
    const cat = initial.getAttribute('data-category') || 'all';
    filter(cat);
  }
});
