// === Анимация шапки и язычка ===
(function() {
  const header = document.getElementById('site-header');
  const pullTab = document.getElementById('header-pull-tab');
  const burger = document.getElementById('burger-menu');
  const nav = document.getElementById('site-nav');
  let lastScroll = window.scrollY;
  let ticking = false;
  let headerVisible = true;

  function showHeader() {
    header.classList.remove('hidden');
    header.classList.add('visible');
    pullTab.style.display = 'none';
    headerVisible = true;
  }
  function hideHeader() {
    header.classList.add('hidden');
    header.classList.remove('visible');
    pullTab.style.display = 'flex';
    headerVisible = false;
  }

  // Slide-up/slide-down при прокрутке
  window.addEventListener('scroll', function() {
    if (!ticking) {
      window.requestAnimationFrame(function() {
        const currentScroll = window.scrollY;
        if (currentScroll > lastScroll && currentScroll > 80) {
          // Вниз — скрыть
          if (headerVisible) hideHeader();
        } else if (currentScroll < lastScroll) {
          // Вверх — показать
          if (!headerVisible) showHeader();
        }
        lastScroll = currentScroll;
        ticking = false;
      });
      ticking = true;
    }
  });

  // Язычок: ручное разворачивание
  pullTab.addEventListener('click', showHeader);
  pullTab.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' || e.key === ' ') showHeader();
  });
  pullTab.tabIndex = 0;
  pullTab.setAttribute('role', 'button');

  // Бургер-меню
  burger.addEventListener('click', function() {
    nav.classList.toggle('open');
    burger.classList.toggle('active');
    // accessibility
    burger.setAttribute('aria-expanded', nav.classList.contains('open'));
  });

  // Закрытие меню по клику вне
  document.addEventListener('click', function(e) {
    if (nav.classList.contains('open') && !nav.contains(e.target) && !burger.contains(e.target)) {
      nav.classList.remove('open');
      burger.classList.remove('active');
    }
  });

  // Доступность: ESC закрывает меню
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && nav.classList.contains('open')) {
      nav.classList.remove('open');
      burger.classList.remove('active');
    }
  });

  // Изначально шапка видима, язычок скрыт
  showHeader();
})();
  