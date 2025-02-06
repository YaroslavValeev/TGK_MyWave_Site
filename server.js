<<<<<<< HEAD
// server.js
const express = require("express");
const bodyParser = require("body-parser");
const path = require("path");
const fetch = (...args) => import('node-fetch').then(({ default: fetch }) => fetch(...args));

const app = express();
app.use(bodyParser.json());
app.use(express.static(path.join(__dirname)));

// Используем переменные окружения для ключей
const apiKey = process.env.OPENAI_API_KEY || "sk-l50PoHQuqCTiC9xweQQjQbIM9-26zqEQ1lYB9tdGnNT3BlbkFJbc0t0jpZPc5OHoHh55TruS4qMW6zUht_827tt1r0gA"; // Убедитесь, что ключ задан в переменной окружения
const gptId = "g-QRvCoJeXk"; // Если это необходимо, можно использовать или удалить

app.post("/chat", async (req, res) => {
    const userMessage = req.body.message;

    try {
        const response = await fetch("https://api.openai.com/v1/chat/completions", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${apiKey}`
            },
            body: JSON.stringify({
                model: "g-QRvCoJeXk",
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

        res.json({ reply: data.choices[0].message.content });
    } catch (error) {
        console.error("Ошибка на сервере:", error);
        res.status(500).json({ reply: "Ошибка сервера. Попробуйте позже." });
    }
});

const PORT = process.env.PORT || 5000;
app.listen(PORT, () => console.log(`Сервер запущен на http://localhost:${PORT}`));
=======
// server.js
const express = require("express");
const bodyParser = require("body-parser");
const path = require("path");
const fetch = (...args) => import('node-fetch').then(({ default: fetch }) => fetch(...args));

const app = express();
app.use(bodyParser.json());
app.use(express.static(path.join(__dirname)));

// Используем переменные окружения для ключей
const apiKey = process.env.OPENAI_API_KEY || "sk-l50PoHQuqCTiC9xweQQjQbIM9-26zqEQ1lYB9tdGnNT3BlbkFJbc0t0jpZPc5OHoHh55TruS4qMW6zUht_827tt1r0gA"; // Убедитесь, что ключ задан в переменной окружения
const gptId = "g-QRvCoJeXk"; // Если это необходимо, можно использовать или удалить

app.post("/chat", async (req, res) => {
    const userMessage = req.body.message;

    try {
        const response = await fetch("https://api.openai.com/v1/chat/completions", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${apiKey}`
            },
            body: JSON.stringify({
                model: "g-QRvCoJeXk",
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

        res.json({ reply: data.choices[0].message.content });
    } catch (error) {
        console.error("Ошибка на сервере:", error);
        res.status(500).json({ reply: "Ошибка сервера. Попробуйте позже." });
    }
});

const PORT = process.env.PORT || 5000;
app.listen(PORT, () => console.log(`Сервер запущен на http://localhost:${PORT}`));
>>>>>>> 1a630d3 (Добавлен код сайта)
