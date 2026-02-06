document.addEventListener('DOMContentLoaded', function() {
  const form = document.getElementById('safariBookingForm');
  const statusDiv = document.getElementById('bookingStatus');

  if (!form) return;

  form.addEventListener('submit', async function(e) {
    e.preventDefault();

    const formData = new FormData(form);
    const data = {
      name: formData.get('name'),
      email: formData.get('email'),
      phone: formData.get('phone'),
      level: formData.get('level'),
      days: parseInt(formData.get('days'), 10),
      startDate: formData.get('startDate'),
      message: formData.get('message')
    };

    // Validate
    if (!data.name || !data.email || !data.phone || !data.level || !data.days || !data.startDate) {
      showAlert('Пожалуйста, заполните все обязательные поля', 'danger');
      return;
    }

    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn ? submitBtn.innerHTML : '';
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.classList.add('loading');
      submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Отправка...';
    }

    try {
      const response = await fetch('/api/booking/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
      });

      const result = await response.json();

      if (response.ok && result.status === 'success') {
        const bookingId = result.booking && result.booking.id;
        showAlert('Спасибо! Ваша заявка на бронирование принята. Мы вскоре свяжемся с вами.', 'success');
        form.reset();
        if (bookingId) {
          setTimeout(() => {
            window.location.href = `/wakesurf-safari/booking-success?id=${bookingId}`;
          }, 2000);
        }
      } else {
        const errorMsg = result.error || 'Произошла ошибка при создании бронирования';
        showAlert(`Ошибка: ${errorMsg}`, 'danger');
      }
    } catch (error) {
      console.error('Error:', error);
      showAlert('Произошла ошибка при отправке. Пожалуйста, попробуйте позже.', 'danger');
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.classList.remove('loading');
        submitBtn.innerHTML = originalText;
      }
    }
  });

  function showAlert(message, type) {
    if (!statusDiv) return;
    statusDiv.innerHTML = `<div class="alert alert-${type} show">${message}</div>`;
    statusDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
});
