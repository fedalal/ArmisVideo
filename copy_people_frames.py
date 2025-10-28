import os
import shutil
import psycopg2
from psycopg2.extras import RealDictCursor

# === НАСТРОЙКИ ===
DB_CONFIG = {
    "host": "192.168.13.89",
    "port": 5432,
    "dbname": "ArmisVideo",
    "user": "postgres",
    "password": "br7moLeJ56"
}

# Папка, где лежат все исходные миниатюры
SOURCE_DIR = r"Z:\5EBE749EBE746FFF\Armis\images_13Oct\home\ubuntu\ArmisVideo\images"
# Куда копировать результаты
DEST_DIR = r"Z:\5EBE749EBE746FFF\Armis\result"

# === ПОДКЛЮЧЕНИЕ К БАЗЕ ===
conn = psycopg2.connect(**DB_CONFIG)

with conn.cursor(cursor_factory=RealDictCursor) as cur:
    # Берём все кадры, где обнаружен человек
    cur.execute("""
        SELECT f.thumb_path, f.workstation_id
        FROM frames f
        WHERE f.people_count > 0
        AND f.captured_at >= '2025-10-13 00:00:00' 
        AND f.captured_at <= '2025-10-13 23:59:59'
    """)
    rows = cur.fetchall()

print(f"Найдено {len(rows)} кадров, где обнаружены люди.")

# === КОПИРОВАНИЕ ===
for row in rows:
    thumb_path = row["thumb_path"]
    workstation_id = str(row["workstation_id"]) or "unknown"

    # Создаём папку по ID рабочего места
    dest_folder = os.path.join(DEST_DIR, workstation_id)
    os.makedirs(dest_folder, exist_ok=True)

    # Полный путь к исходному файлу
    src = os.path.join(SOURCE_DIR, thumb_path)
    dst = os.path.join(dest_folder, os.path.basename(thumb_path))

    if os.path.exists(src):
        shutil.copy2(src, dst)
    else:
        print(f"⚠️ Файл не найден: {src}")

print("✅ Копирование завершено.")
