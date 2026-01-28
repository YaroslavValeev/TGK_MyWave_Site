/**
 * Обработка форм для Wake Surf Safari 2026.
 */
(() => {
  const ready = (fn) =>
    document.readyState !== "loading" ? fn() : document.addEventListener("DOMContentLoaded", fn);

  ready(() => {
    // Обработчик для формы участника
    const participantForm = document.querySelector(".js-safari-participant");
    if (participantForm) {
      setupForm(participantForm, "safari-participant-message");
    }

    // Обработчик для формы партнёра
    const partnerForm = document.querySelector(".js-safari-partner");
    if (partnerForm) {
      setupForm(partnerForm, "safari-partner-message");
    }

    // Обработчик для формы медиа
    const mediaForm = document.querySelector(".js-safari-media");
    if (mediaForm) {
      setupForm(mediaForm, "safari-media-message");
    }

    // Обработчик для формы фидбека
    const feedbackForm = document.querySelector(".js-safari-feedback");
    if (feedbackForm) {
      setupForm(feedbackForm, "safari-feedback-message");
    }
  });

  function setupForm(form, messageId) {
    const messageEl = document.getElementById(messageId);
    
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      
      const formData = new FormData(form);
      const data = Object.fromEntries(formData.entries());
      
      const submitBtn = form.querySelector('button[type="submit"]');
      const originalText = submitBtn.textContent;
      submitBtn.disabled = true;
      submitBtn.textContent = "Отправка...";
      
      if (messageEl) {
        messageEl.textContent = "";
        messageEl.className = "mw-form-message";
      }
      
      try {
        const response = await fetch(form.action, {
          method: "POST",
          headers: {
            "X-CSRFToken": data.csrf_token || "",
          },
          body: formData,
        });
        
        const result = await response.json();
        
        if (response.ok && result.success) {
          if (messageEl) {
            messageEl.textContent = result.message || "Заявка успешно отправлена!";
            messageEl.className = "mw-form-message mw-form-message--success";
          }
          form.reset();
          
          // Прокрутка к сообщению об успехе
          if (messageEl) {
            messageEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
          }
        } else {
          if (messageEl) {
            messageEl.textContent = result.error || "Произошла ошибка при отправке заявки.";
            messageEl.className = "mw-form-message mw-form-message--error";
          }
        }
      } catch (error) {
        if (messageEl) {
          messageEl.textContent = "Ошибка сети. Пожалуйста, попробуйте позже.";
          messageEl.className = "mw-form-message mw-form-message--error";
        }
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
      }
    });
  }
})();
