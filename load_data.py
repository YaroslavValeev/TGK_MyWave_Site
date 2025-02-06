<<<<<<< HEAD
import sqlite3
import os

# Подключение к базе данных
conn = sqlite3.connect('knowledge_base.db')
cursor = conn.cursor()

# Папка с .txt файлами
folder_path = './knowledge_base'

# Загрузка данных из файлов
for filename in os.listdir(folder_path):
    if filename.endswith('.txt'):
        with open(os.path.join(folder_path, filename), 'r', encoding='utf-8') as file:
            content = file.read()

            # Сохраняем в базу данных
            cursor.execute("INSERT INTO knowledge (title, content) VALUES (?, ?)", (filename, content))

conn.commit()
conn.close()

print("Данные успешно загружены в базу знаний.")
=======
import sqlite3
import os

# Подключение к базе данных
conn = sqlite3.connect('knowledge_base.db')
cursor = conn.cursor()

# Папка с .txt файлами
folder_path = './knowledge_base'

# Загрузка данных из файлов
for filename in os.listdir(folder_path):
    if filename.endswith('.txt'):
        with open(os.path.join(folder_path, filename), 'r', encoding='utf-8') as file:
            content = file.read()

            # Сохраняем в базу данных
            cursor.execute("INSERT INTO knowledge (title, content) VALUES (?, ?)", (filename, content))

conn.commit()
conn.close()

print("Данные успешно загружены в базу знаний.")
>>>>>>> 1a630d3 (Добавлен код сайта)
