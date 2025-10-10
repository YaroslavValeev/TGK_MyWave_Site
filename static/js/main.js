// Инициализация flatpickr
const dateInput = document.getElementById('bookingDateInput');
if (dateInput) {
    flatpickr(dateInput, {
        dateFormat: "d.m.Y",
        minDate: "today",
        disableMobile: true,
        locale: "ru",
        onChange: function(selectedDates, dateStr) {
            dateInput.value = dateStr;
        }
    });
}

// Функции для работы с модальным окном
function openModal() {
    const modal = document.getElementById('dateModal');
    if (modal) {
        modal.classList.add('show');
    }
}

function closeModal() {
    const modal = document.getElementById('dateModal');
    if (modal) {
        modal.classList.remove('show');
    }
}

// Обработчики событий
document.addEventListener('DOMContentLoaded', function() {
    const closeBtn = document.querySelector('.close-modal');
    const dateIcon = document.getElementById('dateIcon');
    const modal = document.getElementById('dateModal');
    const confirmBtn = document.getElementById('confirmDate');

    if (closeBtn) {
        closeBtn.addEventListener('click', closeModal);
    }

    if (dateIcon) {
        dateIcon.addEventListener('click', function() {
            if (dateInput._flatpickr) {
                dateInput._flatpickr.open();
            }
        });
    }

    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                closeModal();
            }
        });
    }

    if (confirmBtn) {
        confirmBtn.addEventListener('click', function() {
            // Здесь можно добавить логику обработки выбранной даты
            closeModal();
        });
    }
}); 