/**
 * Product purchase request form (PR53) — lead to manager, no fake checkout.
 */
(function () {
  'use strict';

  const SUCCESS_MSG =
    'Заявка отправлена. Сейчас каждое изделие выполняется индивидуально — склада нет. ' +
    'Доставка через ПВЗ Яндекс Маркета (по запросу можем оформить в другие пункты выдачи). ' +
    'Срок изготовления — примерно 7 дней. Мы свяжемся с вами для подтверждения заказа.';
  const ERROR_MSG =
    'Не удалось отправить заявку. Попробуйте ещё раз или напишите нам в Telegram.';

  function qs(sel, root) {
    return (root || document).querySelector(sel);
  }

  function openModal(modal) {
    if (!modal) return;
    modal.classList.remove('hidden');
    modal.classList.add('show');
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
  }

  function closeModal(modal) {
    if (!modal) return;
    modal.classList.remove('show');
    modal.classList.add('hidden');
    modal.style.display = 'none';
    document.body.style.overflow = 'auto';
  }

  function bindProductCardClickBuy() {
    function triggerBuyFromCard(event) {
      const card = event.target.closest('[data-product-card-click-buy]');
      if (!card) return;

      if (
        event.target.closest('button, a, input, .carousel-nav, .carousel-prev-inner, .carousel-next-inner, [data-no-card-buy]')
      ) {
        return;
      }

      const buyButton = card.querySelector('[data-product-buy-trigger]');
      if (buyButton) {
        buyButton.click();
      }
    }

    document.addEventListener('click', triggerBuyFromCard);

    document.addEventListener('keydown', function (event) {
      if (event.key !== 'Enter' && event.key !== ' ') return;
      const card = event.target.closest('[data-product-card-click-buy]');
      if (!card || event.target !== card) return;
      event.preventDefault();
      const buyButton = card.querySelector('[data-product-buy-trigger]');
      if (buyButton) buyButton.click();
    });
  }

  function bindProductRequest() {
    const modal = document.getElementById('modalProductRequest');
    const form = document.getElementById('product-request-form');
    if (!form) return;

    document.querySelectorAll('[data-product-request]').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        if (btn.dataset.buyUrl) return;
        e.preventDefault();
        const productId = btn.dataset.productId || '';
        const productTitle = btn.dataset.productTitle || '';
        const pageUrl = window.location.href;
        form.querySelector('[name="product_id"]').value = productId;
        form.querySelector('[name="product_title"]').value = productTitle;
        form.querySelector('[name="page_url"]').value = pageUrl;
        const titleEl = qs('#product-request-title', modal);
        if (titleEl) titleEl.textContent = productTitle || 'Заявка на товар';
        const msg = qs('#product-request-message', modal);
        if (msg) {
          msg.hidden = true;
          msg.textContent = '';
        }
        openModal(modal);
      });
    });

    modal?.querySelectorAll('.close-modal, [data-close-product-modal]').forEach((el) => {
      el.addEventListener('click', () => closeModal(modal));
    });

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const submitBtn = form.querySelector('[type="submit"]');
      const msgEl = qs('#product-request-message', modal);
      if (submitBtn) submitBtn.disabled = true;

      const fd = new FormData(form);
      const body = Object.fromEntries(fd.entries());
      body.quantity = parseInt(body.quantity, 10) || 1;

      try {
        const resp = await fetch('/shop/api/product-request', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
        const data = await resp.json();
        if (resp.ok && data.ok) {
          if (msgEl) {
            msgEl.hidden = false;
            msgEl.className = 'mw-form-message mw-form-message--success';
            msgEl.textContent = data.message || SUCCESS_MSG;
          }
          form.reset();
        } else {
          if (msgEl) {
            msgEl.hidden = false;
            msgEl.className = 'mw-form-message mw-form-message--error';
            msgEl.textContent = data.error || ERROR_MSG;
          }
        }
      } catch (_err) {
        if (msgEl) {
          msgEl.hidden = false;
          msgEl.className = 'mw-form-message mw-form-message--error';
          msgEl.textContent = ERROR_MSG;
        }
      } finally {
        if (submitBtn) submitBtn.disabled = false;
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      bindProductRequest();
      bindProductCardClickBuy();
    });
  } else {
    bindProductRequest();
    bindProductCardClickBuy();
  }
})();
