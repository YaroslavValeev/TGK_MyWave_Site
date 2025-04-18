document.addEventListener('DOMContentLoaded', function () {
    const burger = document.getElementById('burger-menu');
    const menu = document.querySelector('.site-nav');
  
    if (!burger || !menu) {
      console.warn("❗ Элементы бургер-меню не найдены");
      return;
    }
  
    burger.addEventListener('click', () => {
      menu.classList.toggle('open');
      burger.classList.toggle('active');
    });
  
    // Закрываем меню при клике на ссылку
    document.querySelectorAll('.site-nav a').forEach(link => {
      link.addEventListener('click', () => {
        if (menu.classList.contains('open')) {
          menu.classList.remove('open');
          burger.classList.remove('active');
        }
      });
    });
  });
  