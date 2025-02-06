document.addEventListener("DOMContentLoaded", function () {
    const sendButton = document.getElementById("sendBtn");
    const userInput = document.getElementById("user-input");
    const chatBox = document.getElementById("chatWindow");

    // Обработчик клика на кнопку
    sendButton.addEventListener("click", sendMessage);

    // Обработка нажатия Enter в поле ввода
    userInput.addEventListener("keypress", function(event) {
        if (event.key === "Enter") {
            event.preventDefault();
            sendMessage();
        }
    });

    async function sendMessage() {
        const message = userInput.value.trim();
        if (!message) return;

        // Блокируем кнопку отправки на время запроса
        sendButton.disabled = true;

        // Отображаем сообщение пользователя
        chatBox.innerHTML += `<div><strong>Вы:</strong> ${message}</div>`;

        // Добавляем индикатор загрузки
        chatBox.innerHTML += `<div id="loading" class="loading"><strong>Эксперт печатает...</strong></div>`;
        chatBox.scrollTop = chatBox.scrollHeight;

        try {
            const response = await fetch("/gpt_chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json; charset=utf-8"
                },
                body: JSON.stringify({ message: message })
            });

            // Удаляем индикатор загрузки
            const loadingElem = document.getElementById("loading");
            if (loadingElem) loadingElem.remove();

            if (response.ok) {
                const data = await response.json();
                chatBox.innerHTML += `<div><strong>Эксперт:</strong> ${data.reply}</div>`;
            } else {
                const errorData = await response.json();
                console.error("Ошибка сервера:", errorData.error);
                chatBox.innerHTML += `<div style="color: red;"><strong>Ошибка сервера:</strong> Попробуйте снова.</div>`;
            }
        } catch (error) {
            console.error("Ошибка сервера:", error);
            chatBox.innerHTML += `<div style="color: red;"><strong>Ошибка сервера:</strong> ${error.message}</div>`;
        }

        // Разблокируем кнопку и очищаем поле ввода
        sendButton.disabled = false;
        userInput.value = "";
        chatBox.scrollTop = chatBox.scrollHeight;
    }
});
