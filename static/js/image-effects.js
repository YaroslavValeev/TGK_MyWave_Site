// Управление эффектами изображений
document.addEventListener('DOMContentLoaded', () => {
    const images = document.querySelectorAll('.service-image');

    function clearStallTimer(imageContainer) {
        const tid = imageContainer._imageEffectsStallTimer;
        if (tid != null) {
            clearTimeout(tid);
            imageContainer._imageEffectsStallTimer = null;
        }
    }

    // Функция для отображения ошибки загрузки
    function showError(imageContainer) {
        clearStallTimer(imageContainer);
        imageContainer.classList.add('error');
        const ph = imageContainer.querySelector('.image-placeholder');
        if (ph) {
            ph.remove();
        }
        const img = imageContainer.querySelector('img');
        if (!img) {
            return;
        }
        const fallbackUrl = img.dataset.fallback;
        if (fallbackUrl && !img.dataset.fallbackTried) {
            img.dataset.fallbackTried = '1';
            img.classList.remove('loaded');
            img.src = fallbackUrl;
            img.removeAttribute('srcset');
            return;
        }

        if (!imageContainer.querySelector('.image-error-message')) {
            const errorMessage = document.createElement('div');
            errorMessage.className = 'image-error-message';
            errorMessage.textContent = 'Не удалось загрузить изображение';
            imageContainer.appendChild(errorMessage);
        }
    }
    
    // Функция для создания структуры контейнера изображения
    function setupImageContainer(img) {
        if (!img.parentElement.classList.contains('service-image-container')) {
            const container = document.createElement('div');
            container.className = 'service-image-container';
            img.parentNode.insertBefore(container, img);
            container.appendChild(img);
        }
        
        const container = img.closest('.service-image-container');
        
        // Добавляем плейсхолдер, если его еще нет
        if (!container.querySelector('.image-placeholder')) {
            const placeholder = document.createElement('div');
            placeholder.className = 'image-placeholder';
            
            // Добавляем анимированный индикатор загрузки
            const loader = document.createElement('div');
            loader.className = 'loader';
            placeholder.appendChild(loader);
            
            container.insertBefore(placeholder, img);
        }
        
        return container;
    }
    
    // Функция для отображения уже загруженного изображения
    function markAsLoaded(img, container, placeholder) {
        clearStallTimer(container);
        container.classList.add('image-loaded');
        container.classList.remove('error');
        const errorMessage = container.querySelector('.image-error-message');
        if (errorMessage) {
            errorMessage.remove();
        }
        img.classList.add('loaded');
        if (placeholder) {
            placeholder.style.opacity = '0';
            setTimeout(() => placeholder.remove(), 300);
        }
        img.style.opacity = '1';
        img.style.transform = 'scale(1) translateY(0)';
    }
    
    // Функция для загрузки изображения
    function loadImage(img) {
        const container = setupImageContainer(img);
        const placeholder = container.querySelector('.image-placeholder');

        // Устанавливаем реальный src из data-src (если используется lazy)
        if (img.dataset.src) {
            img.src = img.dataset.src;
        }

        if (img.dataset.srcset) {
            img.srcset = img.dataset.srcset;
        }

        // Если изображение уже загружено (src в HTML, скрипт выполнился позже)
        if (img.complete && img.naturalWidth > 0) {
            markAsLoaded(img, container, placeholder);
            return;
        }

        const srcAttr = (img.getAttribute('src') || '').trim();
        if (!srcAttr && !img.dataset.src) {
            showError(container);
            return;
        }

        // Обработчик успешной загрузки
        img.onload = () => {
            markAsLoaded(img, container, placeholder);
        };

        // Обработчик ошибки загрузки
        img.onerror = () => {
            showError(container);
        };

        // «Тихая» поломка: complete, но декодировать нечего — onerror иногда не приходит вовремя
        requestAnimationFrame(() => {
            if (container.classList.contains('image-loaded') || container.classList.contains('error')) {
                return;
            }
            if (img.complete && img.naturalWidth === 0 && img.naturalHeight === 0 && srcAttr) {
                showError(container);
            }
        });

        // Зависшая загрузка: снять skeleton (после таймаута — показать картинку или сработает showError по битому src)
        clearStallTimer(container);
        container._imageEffectsStallTimer = setTimeout(() => {
            container._imageEffectsStallTimer = null;
            if (container.classList.contains('image-loaded') || container.classList.contains('error')) {
                return;
            }
            if (img.complete && img.naturalWidth === 0) {
                showError(container);
                return;
            }
            const ph = container.querySelector('.image-placeholder');
            markAsLoaded(img, container, ph);
        }, 20000);
    }
    
    // Используем Intersection Observer для ленивой загрузки
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    loadImage(entry.target);
                    observer.unobserve(entry.target);
                }
            });
        }, {
            rootMargin: '50px 0px', // Предзагрузка за 50px до появления
            threshold: 0.1
        });
        
        images.forEach(img => imageObserver.observe(img));
    } else {
        // Для браузеров без поддержки Intersection Observer
        images.forEach(loadImage);
    }
    
    // Добавляем поддержку повторной попытки загрузки при клике
    document.addEventListener('click', (e) => {
        const errorContainer = e.target.closest('.service-image-container.error');
        if (errorContainer) {
            const img = errorContainer.querySelector('img');
            const errorMessage = errorContainer.querySelector('.image-error-message');
            
            // Удаляем сообщение об ошибке и класс ошибки
            if (errorMessage) {
                errorMessage.remove();
            }
            errorContainer.classList.remove('error');
            
            // Пробуем загрузить изображение снова
            loadImage(img);
        }
    });
});