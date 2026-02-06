# Точечный патч: лид-модалки (без мигания) + карусели Товары/Проекты

Ярослав: по скринам две проблемы — лид-модалки «мигнули и закрылись»; Товары и Проекты должны быть горизонтальными каруселями с ← →. Ниже — «файл → что заменить» и полные версии файлов для вставки вручную.

---

## 1) Лид-модалки: почему мигают и как фиксить

**Причина:** Кнопки в `index.html` — `class="btn-secondary btn-lead"` и `data-lead="camp"` (и т.п.). Обработчик должен цепляться на **`.btn-lead[data-lead]`** и использовать **capture + stopImmediatePropagation**, чтобы не срабатывали чужие обработчики закрытия.

**Что сделать:**

1. **Полная замена файла** `static/js/lead-forms.js` — на содержимое из раздела «Файл: static/js/lead-forms.js» ниже.
2. **В шаблоне модалок** добавить класс **`lead-modal`** к каждому контейнеру модалки и класс **`modal-close`** к крестику (чтобы новый скрипт находил кнопки закрытия).

В `templates/partials/lead_modals.html` у каждого из трёх блоков:
- У внешнего `<div id="lead-modal-camp">` (и coach-trip, consulting) добавить класс **`lead-modal`** к существующим классам, например: `class="modal lead-modal hidden"`.
- У `<span class="close-modal lead-modal-close">` добавить класс **`modal-close`**: `class="close-modal lead-modal-close modal-close"`.

ID оставляем: `lead-modal-camp`, `lead-modal-coach-trip`, `lead-modal-consulting` (в скрипте уже прописаны в `leadTypeToModalId`).

---

## Файл: static/js/lead-forms.js

(Полная замена файла.)

```javascript
/**
 * Лид-формы: Camp, Тренер на выезде, Консалтинг.
 * Поддержка .btn-lead[data-lead] и [data-open-lead]. Capture + stopImmediatePropagation — без мигания.
 */
document.addEventListener('DOMContentLoaded', () => {
  const leadTypeToModalId = {
    camp: 'lead-modal-camp',
    'coach-trip': 'lead-modal-coach-trip',
    travel: 'lead-modal-coach-trip',
    consulting: 'lead-modal-consulting',
  };

  function hideLeadModals() {
    document.querySelectorAll('.lead-modal').forEach(modal => {
      modal.classList.remove('show');
      modal.classList.add('hidden');
      modal.style.display = 'none';
      modal.setAttribute('aria-hidden', 'true');
    });
    document.body.classList.remove('modal-open');
    document.body.style.overflow = '';
  }

  function showLeadModal(modal) {
    if (!modal) return;
    hideLeadModals();
    modal.classList.remove('hidden');
    modal.classList.add('show');
    modal.style.display = 'flex';
    modal.setAttribute('aria-hidden', 'false');
    document.body.classList.add('modal-open');
    document.body.style.overflow = 'hidden';
  }

  const openButtons = document.querySelectorAll('[data-open-lead], .btn-lead[data-lead]');

  openButtons.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopImmediatePropagation();
      e.stopPropagation();

      const leadType = btn.dataset.lead || btn.dataset.openLead;
      const modalId = btn.dataset.modalId || leadTypeToModalId[leadType];
      if (!modalId) return;

      const modal = document.getElementById(modalId);
      showLeadModal(modal);
    }, true);
  });

  document.querySelectorAll('[data-close-lead], .lead-modal .modal-close, .lead-modal .lead-modal-close').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      hideLeadModals();
    });
  });

  document.querySelectorAll('.lead-modal').forEach(modal => {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) hideLeadModals();
    });
  });

  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    const open = document.querySelector('.lead-modal.show:not(.hidden)');
    if (open) hideLeadModals();
  });

  const successIds = { 'coach-trip': 'lead-coach-success', 'consulting': 'lead-consulting-success', 'camp': 'lead-camp-success' };
  document.getElementById('lead-form-coach-trip') && document.getElementById('lead-form-coach-trip').addEventListener('submit', function (e) {
    e.preventDefault();
    var form = e.target;
    var data = { type: 'coach_trip', location: form.location?.value, dates: form.dates?.value, format: form.format?.value, level: form.level?.value, equipment: form.equipment?.value, contact: form.contact?.value };
    sendLead(data, 'coach-trip');
  });
  document.getElementById('lead-form-consulting') && document.getElementById('lead-form-consulting').addEventListener('submit', function (e) {
    e.preventDefault();
    var form = e.target;
    var data = { type: 'consulting', topic: form.topic?.value, task: form.task?.value, contact: form.contact?.value };
    sendLead(data, 'consulting');
  });
  document.getElementById('lead-form-camp') && document.getElementById('lead-form-camp').addEventListener('submit', function (e) {
    e.preventDefault();
    var form = e.target;
    var data = { type: 'camp', dates: form.dates?.value, level: form.level?.value, goal: form.goal?.value, budget: form.budget?.value, contact: form.contact?.value };
    sendLead(data, 'camp');
  });

  function sendLead(data, leadKey) {
    var formEl = (leadKey === 'coach-trip' ? document.getElementById('lead-form-coach-trip') : leadKey === 'consulting' ? document.getElementById('lead-form-consulting') : document.getElementById('lead-form-camp'));
    var successEl = document.getElementById(successIds[leadKey]);
    var csrfEl = document.querySelector('meta[name="csrf-token"]');
    var csrf = csrfEl ? csrfEl.getAttribute('content') : '';
    fetch('/api/lead', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
      credentials: 'same-origin',
      body: JSON.stringify(data)
    }).then(function (r) {
      if (!r.ok) return r.json().then(function (j) { throw new Error(j.error || 'Ошибка отправки'); });
      return r.json();
    }).then(function () {
      if (formEl) formEl.classList.add('hidden');
      if (successEl) { successEl.classList.remove('hidden'); successEl.textContent = 'Заявка отправлена. Мы свяжемся с вами в ближайшее время.'; }
    }).catch(function (err) {
      alert(err.message || 'Не удалось отправить заявку.');
    });
  }
});
```

---

## 2) Карусели «Товары» и «Проекты»

### 2.1. templates/index.html — блок «Товары»

**Найти:**
```html
  <!-- Товары (6 обязательных карточек из каталога) -->
  <section id="store" class="store-section">
    <h2>Товары</h2>
    <div class="cards-grid">
      {% for p in products_preview %}
      <div class="product-card">
        ...
      </div>
      {% endfor %}
    </div>
    <p class="store-more">...
  </section>
```

**Заменить на:**
```html
  <!-- Товары (карусель) -->
  <section id="store" class="store-section">
    <h2>Товары</h2>
    <div class="products-carousel">
      <button class="carousel-prev" type="button" aria-label="Прокрутить товары влево">‹</button>
      <div class="carousel-track">
        {% for p in products_preview %}
        <a class="product-card" href="{{ url_for('shop.product', slug=p.slug) }}">
          <img
            src="{{ url_for('static', filename=(p.image or 'images/hero-wakesurf.webp')) }}"
            alt="{{ p.title }}"
            loading="lazy"
            onerror="this.onerror=null;this.src='{{ url_for('static', filename='images/hero-wakesurf.webp') }}';"
          />
          <h4>{{ p.title }}</h4>
          <p>{{ p.description }}</p>
          <p class="price">Цена: {{ p.price }}</p>
          <span class="buy-btn">Купить</span>
        </a>
        {% endfor %}
      </div>
      <button class="carousel-next" type="button" aria-label="Прокрутить товары вправо">›</button>
    </div>
    <p class="store-more"><a href="{{ url_for('shop.shop_index') }}" class="btn-secondary">Все товары</a></p>
  </section>
```

(Кнопка «Купить» сделана `<span>`, т.к. вся карточка — ссылка `<a>`; при необходимости можно оставить `<button type="button">` и открывать `href` по клику в JS.)

### 2.2. templates/index.html — блок «Проекты»

**Заменить внутренность секции «Проекты»** (от `<h2>Проекты</h2>` до конца секции, включая «Тренировочная программа» и «Все проекты») на карусель с **динамическими** карточками из `projects_preview` и одной фиксированной карточкой «Тренировочная программа»:

```html
  <section id="projects" class="projects-section section">
    <h2>Проекты</h2>
    <div class="projects-carousel">
      <button class="carousel-prev" type="button" aria-label="Прокрутить проекты влево">‹</button>
      <div class="carousel-track">
        {% for p in projects_preview %}
        <div class="project-card">
          {% if p.cover %}
          <img src="{{ url_for('static', filename=p.cover) }}" alt="{{ p.name }}" loading="lazy" onerror="this.onerror=null;this.src='{{ url_for('static', filename='images/hero-wakesurf.webp') }}';" />
          {% else %}
          <img src="{{ url_for('static', filename='images/hero-wakesurf.webp') }}" alt="{{ p.name }}" loading="lazy" />
          {% endif %}
          <h4>{{ p.name }}</h4>
          <p>{{ p.summary }}</p>
          {% if p.cta_url %}
          <a href="{{ p.cta_url }}" class="btn-secondary">Подробнее</a>
          {% endif %}
        </div>
        {% endfor %}
        <div class="project-card project-card--wide">
          <h4>Тренировочная программа для подготовки</h4>
          <p>Системная подготовка к исполнению трюков: Start → Progress → Trick. План на 14 дней и запись в зал/на катер.</p>
          <a href="{{ url_for('training_program_page') }}" class="btn-secondary">Получить план / Записаться</a>
        </div>
      </div>
      <button class="carousel-next" type="button" aria-label="Прокрутить проекты вправо">›</button>
    </div>
    <p class="projects-more"><a href="{{ url_for('projects_page') }}" class="btn-secondary">Все проекты</a></p>
  </section>
```

Ссылки у проектов из данных: `p.cta_url`; у «Тренировочная программа» — `url_for('training_program_page')`.

### 2.3. static/js/services-carousel.js

**Найти:**
```javascript
const carousels = document.querySelectorAll('.services-carousel');
```

**Заменить на:**
```javascript
const carousels = document.querySelectorAll('.services-carousel, .products-carousel, .projects-carousel');
```

Остальной код не трогать.

### 2.4. static/css/services-carousel.css

**В конец файла добавить:**

```css
/* Reuse carousel styles for products & projects */
.products-carousel,
.projects-carousel {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 1em 0;
}

.products-carousel .carousel-prev,
.products-carousel .carousel-next,
.projects-carousel .carousel-prev,
.projects-carousel .carousel-next {
  background: #f0f0f0;
  border: 1px solid #e0e0e0;
  color: #333;
  font-size: 20px;
  padding: 8px 12px;
  border-radius: 8px;
  cursor: pointer;
}

.products-carousel .carousel-prev[disabled],
.products-carousel .carousel-next[disabled],
.projects-carousel .carousel-prev[disabled],
.projects-carousel .carousel-next[disabled] {
  opacity: 0.4;
  cursor: default;
}

.products-carousel .carousel-track,
.projects-carousel .carousel-track {
  display: flex;
  gap: 16px;
  overflow-x: auto;
  scroll-behavior: smooth;
  -webkit-overflow-scrolling: touch;
  padding: 8px 4px;
}

.products-carousel .product-card { min-width: 280px; flex: 0 0 auto; }
.projects-carousel .project-card { min-width: 320px; flex: 0 0 auto; }

@media (max-width: 900px) {
  .products-carousel .product-card { min-width: 220px; }
  .projects-carousel .project-card { min-width: 260px; }
}
```

---

## 3) Wave Cards в магазине

Если на скрине снова видна «Настольная игра "Wave Cards"», источник один из двух (или оба):

- **`app/routes/shop.py`** — в словаре `PRODUCTS` не должно быть ключа **`wave-cards`**. Должна остаться только запись **`wakesurfpolia`** с названием «WakeSurfPolia».
- **`templates/shop.html`** — не должно быть карточки с текстом «Wave Cards» или ссылкой на `slug='wave-cards'`.

**В терминале (PowerShell) в корне проекта:**

```powershell
# 1) Где встречается "Wave Cards" или wave-cards
rg -n "Wave Cards|wave-cards" .

# 2) Где формируется список товаров
rg -n "PRODUCTS|get_products_preview|products_preview" app templates
```

- Если `rg` находит «Wave Cards» или `wave-cards` в **`templates/shop.html`** — удалить этот блок карточки.
- Если в **`app/routes/shop.py`** есть элемент с ключом **`wave-cards`** в **`PRODUCTS`** — удалить его. В **`PRODUCTS_PREVIEW_SLUGS`** не должно быть `wave-cards`, только `wakesurfpolia`.

---

## Мини-проверка после правок

1. **Лид-модалки:** клик по Camp / Выезд / Консалтинг → модалка остаётся открытой, не мигает. Закрывается по крестику, клику вне, Escape.
2. **Карусели:** на главной у «Товары» и «Проекты» есть кнопки ‹ и ›, горизонтальный скролл трека.
3. **Магазин:** в списке и на карточке только «WakeSurfPolia», без «Wave Cards».
