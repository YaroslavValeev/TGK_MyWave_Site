// server.js
const express = require("express");
const bodyParser = require("body-parser");
const path = require("path");
const fetch = require("node-fetch");  // исправлен импорт fetch для совместимости

const app = express();
app.use(bodyParser.json());
app.use(express.static(path.join(__dirname)));

// Используем переменные окружения для ключей (ключ из .env)
const apiKey = process.env.OPENAI_API_KEY; // Убедитесь, что ключ задан в переменной окружения
const gptId = "gpt-4"; // Если модель `g-QRvCoJeXk` не существует, используйте другую модель, например, `gpt-4`

// Обработчик POST запроса для чата
app.post("/chat", async (req, res) => {
    const userMessage = req.body.message;

    if (!userMessage) {
        return res.status(400).json({ reply: "Сообщение не предоставлено" });
    }

    try {
        // Отправка запроса в OpenAI
        const response = await fetch("https://api.openai.com/v1/chat/completions", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${apiKey}`
            },
            body: JSON.stringify({
                model: gptId,  // Используем модель, которая доступна
                messages: [
                    { role: "system", content: "Ты профессиональный инструктор по вейксерфингу." },
                    { role: "user", content: userMessage }
                ]
            })
        });

        const data = await response.json();

        if (data.error) {
            console.error("Ошибка от OpenAI:", data.error);
            return res.status(500).json({ reply: `Ошибка OpenAI: ${data.error.message}` });
        }

        // Отправляем ответ от OpenAI
        res.json({ reply: data.choices[0].message.content });
    } catch (error) {
        console.error("Ошибка на сервере:", error);
        res.status(500).json({ reply: "Ошибка сервера. Попробуйте позже." });
    }
});

// Запуск сервера
const PORT = process.env.PORT || 5000;
app.listen(PORT, () => console.log(`Сервер запущен на http://localhost:${PORT}`));
