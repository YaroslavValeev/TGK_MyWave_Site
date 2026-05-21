// Preloader: не блокируем страницу бесконечным ожиданием window.load
document.addEventListener('DOMContentLoaded', () => {
    const preloader = document.createElement('div');
    preloader.className = 'preloader';
    preloader.innerHTML = '<div class="preloader-spinner"></div>';
    document.body.appendChild(preloader);

    let removed = false;
    const MIN_SPIN_MS = 300;
    const MAX_WAIT_MS = 2500;
    const shownAt = Date.now();

    function hidePreloader() {
        if (removed) return;
        removed = true;
        preloader.classList.add('fade-out');
        setTimeout(() => preloader.remove(), 500);
    }

    function hideAfterMinDelay() {
        const elapsed = Date.now() - shownAt;
        const wait = Math.max(0, MIN_SPIN_MS - elapsed);
        setTimeout(hidePreloader, wait);
    }

    if (document.readyState === 'complete') {
        hideAfterMinDelay();
    } else {
        window.addEventListener('load', hideAfterMinDelay, { once: true });
        setTimeout(hidePreloader, MAX_WAIT_MS);
    }

    // Lazy preloader: не трогаем карусели и обложки блога (свой fade / card-gallery)
    const images = document.querySelectorAll(
        'img[loading="lazy"]:not(.project-card__cover):not(.card-media-carousel img):not(.blog-card-cover img)'
    );

    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                const wrapper = img.closest('.img-wrapper');

                function reveal() {
                    if (wrapper) {
                        wrapper.classList.remove('loading');
                    }
                    img.classList.add('loaded');
                }

                if (img.dataset && img.dataset.src) {
                    img.src = img.dataset.src;
                }
                if (img.dataset && img.dataset.srcset) {
                    img.srcset = img.dataset.srcset;
                }

                if (img.complete && img.naturalWidth > 0) {
                    reveal();
                } else {
                    img.onload = reveal;
                    img.onerror = reveal;
                }

                observer.unobserve(img);
            }
        });
    });

    images.forEach(img => {
        if (!img.closest('.img-wrapper')) {
            const wrapper = document.createElement('div');
            wrapper.className = 'img-wrapper loading';
            img.parentNode.insertBefore(wrapper, img);
            wrapper.appendChild(img);
        }

        img.classList.add('fade-in');
        imageObserver.observe(img);
    });
});
