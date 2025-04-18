import openai
import os
from dotenv import load_dotenv
# Укажи свой API-ключ
openai.api_key = os.getenv("OPENAI_API_KEY")

# Создаём ассистента
assistant = openai.beta.assistants.create(
    name="Wakesurfing GPT",
    instructions="Ты эксперт по вейксерфингу. Отвечай подробно и понятно.",
    model="gpt-4-turbo",
)

# Выводим ID ассистента
print("Assistant ID:", assistant.id)
