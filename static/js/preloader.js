// Preloader for page load
document.addEventListener('DOMContentLoaded', () => {
    // Create and append preloader
    const preloader = document.createElement('div');
    preloader.className = 'preloader';
    preloader.innerHTML = '<div class="preloader-spinner"></div>';
    document.body.appendChild(preloader);

    // Remove preloader when page is fully loaded
    window.addEventListener('load', () => {
        preloader.classList.add('fade-out');
        setTimeout(() => preloader.remove(), 500);
    });

    // Lazy preloader: не трогаем карусели карточек (там свой card-gallery.js)
    const images = document.querySelectorAll(
        'img[loading="lazy"]:not(.project-card__cover):not(.card-media-carousel img)'
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

                // Start loading the image only if data-src is provided
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
        // Create wrapper if it doesn't exist
        if (!img.closest('.img-wrapper')) {
            const wrapper = document.createElement('div');
            wrapper.className = 'img-wrapper loading';
            img.parentNode.insertBefore(wrapper, img);
            wrapper.appendChild(img);
        }
        
        // Add fade-in class and setup observation
        img.classList.add('fade-in');
        imageObserver.observe(img);
    });
});