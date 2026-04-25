/**
 * Компактная навигация по странице WSC 2025.
 * Кнопка «Открыть разделы» раскрывает список якорей.
 * Sticky только в минимальном режиме (одна строка).
 */
(function() {
  'use strict';

  function ready(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }

  ready(function() {
    var nav = document.getElementById('wscPageNav');
    var toggle = document.getElementById('wscPageNavToggle');
    var dropdown = document.getElementById('wscPageNavDropdown');
    var links = Array.from(document.querySelectorAll('.wsc-page-nav__link.js-wsc-link'));
    var header = document.getElementById('site-header');

    if (!nav || !toggle || !dropdown || !links.length) return;

    var headerOffset = header ? header.offsetHeight : 0;

    var items = links
      .map(function(a) {
        var id = (a.getAttribute('href') || '').slice(1);
        var el = document.getElementById(id);
        return el ? { id: id, a: a, el: el, top: 0 } : null;
      })
      .filter(Boolean);

    function recalc() {
      headerOffset = header ? header.offsetHeight : 0;
      items.forEach(function(it) {
        it.top = it.el.getBoundingClientRect().top + window.pageYOffset;
      });
      items.sort(function(x, y) { return x.top - y.top; });
    }

    function setActive(id) {
      links.forEach(function(a) {
        a.classList.toggle('active', a.getAttribute('href') === '#' + id);
      });
    }

    function isOpen() {
      return toggle.getAttribute('aria-expanded') === 'true';
    }

    function open() {
      toggle.setAttribute('aria-expanded', 'true');
      dropdown.removeAttribute('hidden');
    }

    function close() {
      toggle.setAttribute('aria-expanded', 'false');
      dropdown.setAttribute('hidden', '');
    }

    function toggleDropdown() {
      if (isOpen()) close();
      else open();
    }

    toggle.addEventListener('click', toggleDropdown);

    links.forEach(function(a) {
      a.addEventListener('click', function(e) {
        var id = (a.getAttribute('href') || '').slice(1);
        var target = document.getElementById(id);
        if (!target) return;
        e.preventDefault();
        close();
        var y = target.getBoundingClientRect().top + window.pageYOffset - headerOffset + 8;
        window.scrollTo({ top: Math.max(0, y), behavior: 'smooth' });
        history.replaceState(null, '', '#' + id);
      });
    });

    document.addEventListener('click', function(e) {
      if (!nav.contains(e.target) && isOpen()) close();
    });

    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && isOpen()) close();
    });

    var ticking = false;
    function onScroll() {
      if (ticking) return;
      ticking = true;

      requestAnimationFrame(function() {
        var hero = document.getElementById('hero');
        var heroBottom = hero ? hero.getBoundingClientRect().bottom + window.pageYOffset : 0;

        if (window.pageYOffset > heroBottom - 60) {
          nav.classList.add('is-sticky');
        } else {
          nav.classList.remove('is-sticky');
        }

        var marker = window.pageYOffset + headerOffset + 48;
        var idx = 0;
        for (var i = 0; i < items.length; i++) {
          if (items[i].top <= marker) idx = i;
          else break;
        }
        var current = items[idx] ? items[idx].id : null;
        if (current) setActive(current);

        ticking = false;
      });
    }

    recalc();
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', function() { recalc(); onScroll(); });
    window.addEventListener('load', function() { recalc(); onScroll(); });
  });
})();
