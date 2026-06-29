"""Работа с SQLite: создание базы и инициализация схемы индекса.

Используется только стандартный модуль sqlite3.
ORM и высокоуровневые обёртки не применяются.
"""

import sqlite3
from pathlib import Path

# Путь к файлу базы данных относительно корня проекта.
# Корень проекта — папка, в которой лежит src/.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "app.db"

# Минимальная схема под индекс файлов.
# Закладывается на первом этапе, расширяется на следующих
# (хэш заполняется на этапе дубликатов).
SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    rel_path   TEXT    NOT NULL UNIQUE,  -- путь файла относительно сканируемой папки
    size       INTEGER,                  -- размер в байтах
    mtime      REAL,                     -- время изменения (unix timestamp)
    ext        TEXT,                     -- расширение файла
    hash       TEXT,                     -- хэш содержимого (этап 3)
    present     INTEGER NOT NULL DEFAULT 1,  -- 1 = есть в папке, 0 = отсутствует
    updated_at REAL                      -- когда запись обновлялась последний раз
);
"""


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Открыть соединение с базой, создав папку data/ при необходимости."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path = DB_PATH) -> Path:
    """Создать базу и таблицы. Возвращает путь к файлу базы."""
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
    return db_path
