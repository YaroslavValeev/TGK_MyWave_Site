// services-carousel.js
// Provides horizontal scrolling UI for services lists with prev/next buttons
(function(){
  function initCarousel(rootSelector){
    const root = document.querySelector(rootSelector);
    if(!root) return;
    const track = root.querySelector('.carousel-track');
    const prev = root.querySelector('.carousel-prev');
    const next = root.querySelector('.carousel-next');
    if(!track) return;

    const scrollBy = () => Math.max(track.clientWidth * 0.6, 300);

    const updateButtons = () => {
      if(!prev || !next) return;
      prev.disabled = track.scrollLeft <= 0;
      next.disabled = track.scrollLeft + track.clientWidth >= track.scrollWidth - 1;
    };

    if(prev){
      prev.addEventListener('click', () => {
        track.scrollBy({left: -scrollBy(), behavior: 'smooth'});
        setTimeout(updateButtons, 300);
      });
    }
    if(next){
      next.addEventListener('click', () => {
        track.scrollBy({left: scrollBy(), behavior: 'smooth'});
        setTimeout(updateButtons, 300);
      });
    }

    // Allow drag-to-scroll on desktop
    let isDown = false, startX, scrollLeft;
    track.addEventListener('mousedown', (e) => {
      isDown = true;
      track.classList.add('dragging');
      startX = e.pageX - track.offsetLeft;
      scrollLeft = track.scrollLeft;
    });
    track.addEventListener('mouseleave', () => { isDown = false; track.classList.remove('dragging'); });
    track.addEventListener('mouseup', () => { isDown = false; track.classList.remove('dragging'); updateButtons(); });
    track.addEventListener('mousemove', (e) => {
      if(!isDown) return;
      e.preventDefault();
      const x = e.pageX - track.offsetLeft;
      const walk = (x - startX) * 1.2; // scroll-fast
      track.scrollLeft = scrollLeft - walk;
    });

    track.addEventListener('scroll', () => {
      updateButtons();
    }, { passive: true });

    // Initialize
    updateButtons();
    window.addEventListener('resize', updateButtons);
  }

  document.addEventListener('DOMContentLoaded', () => {
    initCarousel('.services-carousel');
    initCarousel('.card-carousel');
  });
})();
