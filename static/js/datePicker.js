document.addEventListener("DOMContentLoaded", function() {
    // При клике по иконке календаря переводим фокус на input с id "bookingDate"
    var dateIcon = document.querySelector(".date-picker-icon");
    if (dateIcon) {
        dateIcon.addEventListener("click", function() {
            var dateInput = document.getElementById("bookingDate");
            if (dateInput) {
                dateInput.focus();
                // Для некоторых браузеров можно дополнительно вызвать dateInput.click();
            }
        });
    }
});
