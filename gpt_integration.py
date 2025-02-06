<<<<<<< HEAD
import openai
import os
from dotenv import load_dotenv

# Загружаем API ключ из .env
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  
GPT_ID = os.getenv("GPT_ID")  # ID твоего GPTs

openai.api_key = OPENAI_API_KEY

def ask_gpt(prompt, chat_history=None):
    messages = [{"role": "system", "content": "Ты умный помощник, отвечай понятно и по делу."}]
    if chat_history:
        messages += chat_history
    messages.append({"role": "user", "content": prompt})

    try:
        response = openai.ChatCompletion.create(
            model=GPT_ID,
            messages=messages,
            max_tokens=150,
            temperature=0.7
        )
        return response.choices[0].message["content"]
    except Exception as e:
        return f"Ошибка GPT: {str(e)}"
=======
import openai
import os
from dotenv import load_dotenv

# Загружаем API ключ из .env
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  
GPT_ID = os.getenv("GPT_ID")  # ID твоего GPTs

openai.api_key = OPENAI_API_KEY

def ask_gpt(prompt, chat_history=None):
    messages = [{"role": "system", "content": "Ты умный помощник, отвечай понятно и по делу."}]
    if chat_history:
        messages += chat_history
    messages.append({"role": "user", "content": prompt})

    try:
        response = openai.ChatCompletion.create(
            model=GPT_ID,
            messages=messages,
            max_tokens=150,
            temperature=0.7
        )
        return response.choices[0].message["content"]
    except Exception as e:
        return f"Ошибка GPT: {str(e)}"
>>>>>>> 1a630d3 (Добавлен код сайта)
