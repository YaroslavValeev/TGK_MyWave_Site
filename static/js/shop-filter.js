document.addEventListener('DOMContentLoaded', function () {
  const filterBtns = document.querySelectorAll('.filter-btn');
  const productCards = document.querySelectorAll('#store-products .product-card');

  function setActive(button) {
    filterBtns.forEach(b => b.classList.remove('active'));
    if (button) button.classList.add('active');
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
  });

  // Initialize: show all
  filter('all');
});
