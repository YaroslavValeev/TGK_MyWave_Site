import openai
import os
from dotenv import load_dotenv
import time  # для задержки между запросами

# Загружаем переменные окружения из .env
load_dotenv()

# Твой API-ключ
openai.api_key = os.getenv("OPENAI_API_KEY")

# ID ассистента
assistant_id = "asst_cGDCiVeYdi0w4H5UZFMpORia"

# Папка с базой знаний
knowledge_base_path = "knowledge_base"

# Подпапки с файлами разных форматов
folders = ["wakesurfing_tips.txt", "tricks.txt", "training_methods.pdf"]

# Список загруженных файлов
uploaded_files = []

# Загружаем файлы из каждой подпапки
for folder in folders:
    folder_path = os.path.join(knowledge_base_path, folder)
    if os.path.isdir(folder_path):
        for file_name in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file_name)
            print(f"🔄 Загружаем: {file_path}...")
            try:
                file_obj = openai.files.create(
                    file=open(file_path, "rb"),
                    purpose="assistants"
                )
                uploaded_files.append(file_obj.id)
                print(f"✅ Файл {file_name} загружен! File ID: {file_obj.id}")
            except Exception as e:
                print(f"❌ Ошибка загрузки {file_name}: {e}")

# Если файлы загружены, создаём новый Thread
if uploaded_files:
    thread = openai.beta.threads.create()
    thread_id = thread.id
    print(f"📌 Thread создан! ID: {thread_id}")

    # Для каждого файла отправляем отдельное сообщение с attachments,
    # указывая инструмент "file_search"
    for i, file_id in enumerate(uploaded_files):
        try:
            message = openai.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=f"Файл {i+1} из {len(uploaded_files)}: Используй этот файл для поиска информации.",
                attachments=[{"file_id": file_id, "tools": [{"type": "file_search"}]}]
            )
            print(f"📂 Файл {file_id} успешно прикреплён к потоку {thread_id}")
            time.sleep(1)  # задержка для предотвращения rate limit
        except Exception as e:
            print(f"❌ Ошибка привязки файла {file_id}: {e}")

    print(f"🎯 Все файлы успешно загружены и прикреплены к ассистенту через Thread {thread_id}!")
else:
    print("⚠️ Нет загруженных файлов.")
