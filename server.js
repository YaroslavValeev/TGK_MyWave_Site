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
const assistantId = process.env.ASSISTANT_ID;

// Обработчик POST запроса для чата
app.post("/chat", async (req, res) => {
    const userMessage = req.body.message;

    if (!userMessage) {
        return res.status(400).json({ reply: "Сообщение не предоставлено" });
    }

    if (!assistantId) {
        console.error("❌ ASSISTANT_ID не настроен");
        return res.status(500).json({ reply: "Ошибка конфигурации ассистента" });
    }

    try {
        console.log("📤 Обработка сообщения:", userMessage);
        // Создаем Thread
        const threadResponse = await fetch("https://api.openai.com/v1/threads", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${apiKey}`
            }
        });
        const thread = await threadResponse.json();

        // Добавляем сообщение в Thread
        await fetch(`https://api.openai.com/v1/threads/${thread.id}/messages`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${apiKey}`
            },
            body: JSON.stringify({
                role: "user",
                content: userMessage
            })
        });

        // Запускаем ассистента
        const runResponse = await fetch(`https://api.openai.com/v1/threads/${thread.id}/runs`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${apiKey}`
            },
            body: JSON.stringify({
                assistant_id: assistantId
            })
        });
        const run = await runResponse.json();

        // Ждем завершения выполнения
        let runStatus;
        do {
            await new Promise(resolve => setTimeout(resolve, 1000));
            const statusResponse = await fetch(`https://api.openai.com/v1/threads/${thread.id}/runs/${run.id}`, {
                headers: {
                    "Authorization": `Bearer ${apiKey}`
                }
            });
            runStatus = await statusResponse.json();
        } while (runStatus.status === "queued" || runStatus.status === "in_progress");

        // Получаем сообщения
        const messagesResponse = await fetch(`https://api.openai.com/v1/threads/${thread.id}/messages`, {
            headers: {
                "Authorization": `Bearer ${apiKey}`
            }
        });
        const messages = await messagesResponse.json();

        // Отправляем последнее сообщение ассистента
        const assistantMessage = messages.data[0].content[0].text.value;
        res.json({ reply: assistantMessage });
    } catch (error) {
        console.error("❌ Ошибка чата:", error);
        res.status(500).json({ 
            reply: "Ошибка обработки сообщения",
            error: error.message 
        });
    }
});

// Запуск сервера
const PORT = process.env.PORT || 5000;
app.listen(PORT, () => console.log(`Сервер запущен на http://localhost:${PORT}`));
