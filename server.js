// MyWave Node-прокси OpenAI (отдельный порт, напр. 5001). Требуется Node 18+ (встроенный fetch).
const express = require("express");
const bodyParser = require("body-parser");

const app = express();
app.disable("x-powered-by");
app.use(bodyParser.json({ limit: "256kb" }));

const OPENAI_TIMEOUT_MS = Number(process.env.OPENAI_TIMEOUT_MS || 30000);
const MAX_MESSAGE_LENGTH = Number(process.env.NODE_CHAT_MAX_MESSAGE_LENGTH || 4000);

async function fetchWithTimeout(url, options = {}) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), OPENAI_TIMEOUT_MS);
    try {
        return await fetch(url, { ...options, signal: controller.signal });
    } catch (error) {
        if (error && error.name === "AbortError") {
            throw new Error(`OpenAI request timed out after ${OPENAI_TIMEOUT_MS}ms`);
        }
        throw error;
    } finally {
        clearTimeout(timer);
    }
}

// Для Docker HEALTHCHECK, балансировщиков и ручного curl
app.get("/health", (req, res) => {
    res.status(200).json({
        ok: true,
        service: "mywave-node-proxy",
        port: Number(process.env.PORT || 5000),
        openai_configured: Boolean(process.env.OPENAI_API_KEY && process.env.ASSISTANT_ID),
    });
});

const apiKey = process.env.OPENAI_API_KEY;
const assistantId = process.env.ASSISTANT_ID;

if (!apiKey) {
    console.error("OPENAI_API_KEY is not set. Set the environment variable and restart the proxy server.");
    process.exit(1);
}
if (!assistantId) {
    console.error("ASSISTANT_ID is not set. Set the environment variable and restart the proxy server.");
    process.exit(1);
}

function httpErrorMessage(status, body) {
    if (!body) return `HTTP ${status}`;
    try {
        const j = JSON.parse(body);
        return j.error && j.error.message ? j.error.message : body.slice(0, 500);
    } catch {
        return body.slice(0, 500);
    }
}

app.post("/chat", async (req, res) => {
    const userMessage = typeof req.body.message === "string" ? req.body.message.trim() : "";

    if (!userMessage) {
        return res.status(400).json({ reply: "Сообщение не предоставлено" });
    }
    if (userMessage.length > MAX_MESSAGE_LENGTH) {
        return res.status(413).json({ reply: "Сообщение слишком длинное" });
    }

    try {
        const threadResponse = await fetchWithTimeout("https://api.openai.com/v1/threads", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${apiKey}`,
            },
        });
        const threadBody = await threadResponse.text();
        if (!threadResponse.ok) {
            console.error("OpenAI threads error:", threadResponse.status, threadBody);
            return res.status(502).json({
                reply: "Ошибка API ассистента",
                error: httpErrorMessage(threadResponse.status, threadBody),
            });
        }
        const thread = JSON.parse(threadBody);

        const msgRes = await fetchWithTimeout(`https://api.openai.com/v1/threads/${thread.id}/messages`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${apiKey}`,
            },
            body: JSON.stringify({
                role: "user",
                content: userMessage,
            }),
        });
        const msgBody = await msgRes.text();
        if (!msgRes.ok) {
            console.error("OpenAI messages error:", msgRes.status, msgBody);
            return res.status(502).json({
                reply: "Ошибка API ассистента",
                error: httpErrorMessage(msgRes.status, msgBody),
            });
        }

        const runResponse = await fetchWithTimeout(`https://api.openai.com/v1/threads/${thread.id}/runs`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${apiKey}`,
            },
            body: JSON.stringify({
                assistant_id: assistantId,
            }),
        });
        const runBody = await runResponse.text();
        if (!runResponse.ok) {
            console.error("OpenAI runs create error:", runResponse.status, runBody);
            return res.status(502).json({
                reply: "Ошибка API ассистента",
                error: httpErrorMessage(runResponse.status, runBody),
            });
        }
        const run = JSON.parse(runBody);

        let runStatus;
        do {
            await new Promise((resolve) => setTimeout(resolve, 1000));
            const statusResponse = await fetchWithTimeout(
                `https://api.openai.com/v1/threads/${thread.id}/runs/${run.id}`,
                {
                    headers: {
                        Authorization: `Bearer ${apiKey}`,
                    },
                }
            );
            const stBody = await statusResponse.text();
            if (!statusResponse.ok) {
                console.error("OpenAI run status error:", statusResponse.status, stBody);
                return res.status(502).json({
                    reply: "Ошибка API ассистента",
                    error: httpErrorMessage(statusResponse.status, stBody),
                });
            }
            runStatus = JSON.parse(stBody);
        } while (runStatus.status === "queued" || runStatus.status === "in_progress");

        if (runStatus.status !== "completed") {
            console.error("OpenAI run not completed:", runStatus);
            return res.status(502).json({
                reply: "Ассистент не завершил ответ",
                error: (runStatus.last_error && runStatus.last_error.message) || runStatus.status,
            });
        }

        const messagesResponse = await fetchWithTimeout(`https://api.openai.com/v1/threads/${thread.id}/messages`, {
            headers: {
                Authorization: `Bearer ${apiKey}`,
            },
        });
        const messagesBody = await messagesResponse.text();
        if (!messagesResponse.ok) {
            console.error("OpenAI list messages error:", messagesResponse.status, messagesBody);
            return res.status(502).json({
                reply: "Ошибка API ассистента",
                error: httpErrorMessage(messagesResponse.status, messagesBody),
            });
        }
        const messages = JSON.parse(messagesBody);
        if (!messages.data || !messages.data[0] || !messages.data[0].content || !messages.data[0].content[0]) {
            return res.status(500).json({ reply: "Пустой ответ ассистента" });
        }
        const assistantMessage = messages.data[0].content[0].text.value;
        res.json({ reply: assistantMessage });
    } catch (error) {
        console.error("Chat error:", error);
        res.status(500).json({
            reply: "Ошибка обработки сообщения",
            error: error && error.message ? error.message : String(error),
        });
    }
});

const PORT = process.env.PORT || 5000;
const HOST = process.env.HOST || "0.0.0.0";
app.listen(PORT, HOST, () => console.log(`Node proxy listening on http://${HOST}:${PORT}`));
