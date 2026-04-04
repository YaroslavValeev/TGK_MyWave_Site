/**
 * JavaScript для обработки форм регистрации WakeSurf Challenge 2025
 */

(function() {
    'use strict';
    
    // Получение CSRF токена: перед POST запрашиваем свежий через API,
    // чтобы сессия на сервере гарантированно содержала токен (решает "session token is missing")
    async function getCSRFToken() {
        try {
            const r = await fetch('/api/csrf-token', { credentials: 'same-origin' });
            const d = await r.json();
            return (d && d.csrf_token) || document.querySelector('meta[name="csrf-token"]')?.content || '';
        } catch {
            return document.querySelector('meta[name="csrf-token"]')?.content || '';
        }
    }
    
    // Переключение табов
    const tabButtons = document.querySelectorAll('.wsc2025-tab-btn');
    const formContainers = document.querySelectorAll('.wsc2025-form-container');
    
    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabName = btn.getAttribute('data-tab');
            
            // Убираем активный класс со всех кнопок и контейнеров
            tabButtons.forEach(b => b.classList.remove('active'));
            formContainers.forEach(c => {
                c.classList.remove('active');
                c.style.display = 'none';
            });
            
            // Активируем выбранную
            btn.classList.add('active');
            const targetForm = document.getElementById(`${tabName}-form`);
            if (targetForm) {
                targetForm.classList.add('active');
                targetForm.style.display = 'block';
            }
        });
    });
    
    // Обработка формы регистрации участника
    const participantForm = document.getElementById('participant-registration-form');
    if (participantForm) {
        participantForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const form = e.target;
            const submitBtn = form.querySelector('.wsc2025-form-submit');
            const submitText = form.querySelector('.wsc2025-form-submit-text');
            const submitLoader = form.querySelector('.wsc2025-form-submit-loader');
            const messageDiv = document.getElementById('participant-form-message');
            
            // Очистка предыдущих ошибок
            form.querySelectorAll('.wsc2025-form-error').forEach(el => el.textContent = '');
            messageDiv.className = 'wsc2025-form-message';
            messageDiv.textContent = '';
            messageDiv.style.display = 'none';
            
            // Блокировка кнопки
            submitBtn.disabled = true;
            submitText.style.display = 'none';
            submitLoader.style.display = 'inline';
            
            // Сбор данных формы
            const formData = new FormData(form);
            const csrfToken = await getCSRFToken();
            formData.set('csrf_token', csrfToken);
            
            try {
                const response = await fetch('/projects/wakesurf-challenge-2025/api/participants/register', {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: {
                        'X-CSRFToken': csrfToken
                    },
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // Успех
                    messageDiv.className = 'wsc2025-form-message success';
                    messageDiv.textContent = data.message || 'Регистрация успешно завершена!';
                    messageDiv.style.display = 'block';
                    form.reset();
                    
                    // Прокрутка к сообщению
                    messageDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                } else {
                    // Ошибка
                    if (data.errors) {
                        // Показываем ошибки полей
                        Object.keys(data.errors).forEach(field => {
                            const errorEl = document.getElementById(`participant-${field}-error`);
                            if (errorEl) {
                                errorEl.textContent = data.errors[field];
                            }
                        });
                    }
                    
                    messageDiv.className = 'wsc2025-form-message error';
                    messageDiv.textContent = data.error || 'Произошла ошибка при регистрации';
                    messageDiv.style.display = 'block';
                }
            } catch (error) {
                messageDiv.className = 'wsc2025-form-message error';
                messageDiv.textContent = 'Ошибка сети. Проверьте подключение к интернету.';
                messageDiv.style.display = 'block';
                console.error('Ошибка отправки формы:', error);
            } finally {
                // Разблокировка кнопки
                submitBtn.disabled = false;
                submitText.style.display = 'inline';
                submitLoader.style.display = 'none';
            }
        });
    }
    
    // Обработка формы регистрации тренера
    const coachForm = document.getElementById('coach-registration-form');
    if (coachForm) {
        coachForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const form = e.target;
            const submitBtn = form.querySelector('.wsc2025-form-submit');
            const submitText = form.querySelector('.wsc2025-form-submit-text');
            const submitLoader = form.querySelector('.wsc2025-form-submit-loader');
            const messageDiv = document.getElementById('coach-form-message');
            
            // Очистка предыдущих ошибок
            form.querySelectorAll('.wsc2025-form-error').forEach(el => el.textContent = '');
            messageDiv.className = 'wsc2025-form-message';
            messageDiv.textContent = '';
            messageDiv.style.display = 'none';
            
            // Блокировка кнопки
            submitBtn.disabled = true;
            submitText.style.display = 'none';
            submitLoader.style.display = 'inline';
            
            // Сбор данных формы
            const formData = new FormData(form);
            const csrfToken = await getCSRFToken();
            formData.set('csrf_token', csrfToken);
            
            try {
                const response = await fetch('/projects/wakesurf-challenge-2025/api/coaches/register', {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: {
                        'X-CSRFToken': csrfToken
                    },
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // Успех
                    messageDiv.className = 'wsc2025-form-message success';
                    messageDiv.textContent = data.message || 'Регистрация успешно завершена!';
                    messageDiv.style.display = 'block';
                    form.reset();
                    
                    // Прокрутка к сообщению
                    messageDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                } else {
                    // Ошибка
                    if (data.errors) {
                        // Показываем ошибки полей
                        Object.keys(data.errors).forEach(field => {
                            const errorEl = document.getElementById(`coach-${field}-error`);
                            if (errorEl) {
                                errorEl.textContent = data.errors[field];
                            }
                        });
                    }
                    
                    messageDiv.className = 'wsc2025-form-message error';
                    messageDiv.textContent = data.error || 'Произошла ошибка при регистрации';
                    messageDiv.style.display = 'block';
                }
            } catch (error) {
                messageDiv.className = 'wsc2025-form-message error';
                messageDiv.textContent = 'Ошибка сети. Проверьте подключение к интернету.';
                messageDiv.style.display = 'block';
                console.error('Ошибка отправки формы:', error);
            } finally {
                // Разблокировка кнопки
                submitBtn.disabled = false;
                submitText.style.display = 'inline';
                submitLoader.style.display = 'none';
            }
        });
    }
    
    // Плавная прокрутка к якорям
    document.querySelectorAll('.wsc2025-nav-link').forEach(link => {
        link.addEventListener('click', (e) => {
            const href = link.getAttribute('href');
            if (href.startsWith('#')) {
                e.preventDefault();
                const target = document.querySelector(href);
                if (target) {
                    const offset = 80; // Учитываем sticky навигацию
                    const targetPosition = target.offsetTop - offset;
                    window.scrollTo({
                        top: targetPosition,
                        behavior: 'smooth'
                    });
                }
            }
        });
    });
    
    // Подсветка активного раздела при прокрутке
    const sections = document.querySelectorAll('.wsc2025-section[id]');
    const navLinks = document.querySelectorAll('.wsc2025-nav-link');
    
    function updateActiveNav() {
        const scrollPos = window.scrollY + 100;
        
        sections.forEach(section => {
            const top = section.offsetTop;
            const bottom = top + section.offsetHeight;
            const id = section.getAttribute('id');
            
            if (scrollPos >= top && scrollPos < bottom) {
                navLinks.forEach(link => {
                    link.classList.remove('active');
                    if (link.getAttribute('href') === `#${id}`) {
                        link.classList.add('active');
                    }
                });
            }
        });
    }
    
    window.addEventListener('scroll', updateActiveNav);
    updateActiveNav(); // Инициализация
    
})();

