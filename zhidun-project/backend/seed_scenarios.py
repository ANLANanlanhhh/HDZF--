import sqlite3
import json
import os

DB_PATH = 'zhidun.db'
JSON_PATH = 'scenarios.json'

def init_scenarios_db():
    # 1. 连接数据库
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 2. 创建一张新表，专门存剧本数据
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scripts (
            id INTEGER KEY DEFAULT 1,
            data TEXT NOT NULL
        )
    ''')

    # 3. 读取 json 文件
    if not os.path.exists(JSON_PATH):
        print(f"找不到 {JSON_PATH} 文件，请确保它在 backend 目录下。")
        return

    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        json_content = f.read()

    # 4. 清空旧数据并插入新数据 (确保只有一条最新记录)
    cursor.execute('DELETE FROM scripts')
    cursor.execute('INSERT INTO scripts (id, data) VALUES (1, ?)', (json_content,))
    
    conn.commit()
    conn.close()
    print("剧本数据已成功导入 SQLite 数据库！")

if __name__ == '__main__':
    init_scenarios_db()