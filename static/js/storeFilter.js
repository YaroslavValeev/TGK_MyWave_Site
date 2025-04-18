document.addEventListener('DOMContentLoaded', () => {
    const filters = document.querySelectorAll('.filter-btn');
    const cards   = document.querySelectorAll('.product-card');
  
    filters.forEach(btn => btn.addEventListener('click', () => {
      filters.forEach(b => b.classList.toggle('active', b === btn));
      const cat = btn.dataset.category;
      cards.forEach(card => {
        card.style.display = (cat === 'all' || card.dataset.category === cat) ? 'block' : 'none';
      });
    }));
  });
  