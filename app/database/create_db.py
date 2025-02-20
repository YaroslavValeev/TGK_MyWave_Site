import sqlite3

# Подключение к базе данных (создаст файл, если его нет)
conn = sqlite3.connect('knowledge_base.db')
cursor = conn.cursor()

# Создание таблицы базы знаний
cursor.execute('''
CREATE TABLE IF NOT EXISTS knowledge (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT UNIQUE,
    content TEXT
)
''')

conn.commit()
conn.close()

print("✅ База данных создана успешно.")
