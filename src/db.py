"""Работа с SQLite: создание базы, схема индекса и операции с ним.

Используется только стандартный модуль sqlite3.
ORM и высокоуровневые обёртки не применяются.
"""

import sqlite3
import time
from pathlib import Path

# Путь к файлу базы данных относительно корня проекта.
# Корень проекта — папка, в которой лежит src/.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "app.db"

# Схема под индекс файлов и историю запусков.
# Таблица files — текущее состояние индекса (хэш заполняется на этапе 3).
# Таблица scans — история сканирований.
SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    rel_path   TEXT    NOT NULL UNIQUE,  -- путь файла относительно сканируемой папки
    size       INTEGER,                  -- размер в байтах
    mtime      REAL,                     -- время изменения (unix timestamp)
    ext        TEXT,                     -- расширение файла
    hash       TEXT,                     -- хэш содержимого (этап 3)
    present    INTEGER NOT NULL DEFAULT 1,  -- 1 = есть в папке, 0 = отсутствует
    updated_at REAL                      -- когда запись обновлялась последний раз
);

CREATE TABLE IF NOT EXISTS scans (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    root_path   TEXT NOT NULL,  -- какую папку сканировали
    started_at  REAL,           -- когда начали
    finished_at REAL,           -- когда закончили
    files_count INTEGER         -- сколько файлов найдено
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


# --- Операции с индексом (этап 2) ---

def start_scan(conn: sqlite3.Connection, root_path: str) -> int:
    """Зафиксировать начало сканирования, вернуть id записи."""
    cur = conn.execute(
        "INSERT INTO scans (root_path, started_at) VALUES (?, ?)",
        (root_path, time.time()),
    )
    return cur.lastrowid


def finish_scan(conn: sqlite3.Connection, scan_id: int, files_count: int) -> None:
    """Зафиксировать завершение сканирования."""
    conn.execute(
        "UPDATE scans SET finished_at = ?, files_count = ? WHERE id = ?",
        (time.time(), files_count, scan_id),
    )


def mark_all_absent(conn: sqlite3.Connection) -> None:
    """Перед сканированием пометить все записи как отсутствующие.

    Те файлы, которые встретятся при обходе, снова станут present=1.
    Оставшиеся с present=0 — это файлы, исчезнувшие из папки.
    """
    conn.execute("UPDATE files SET present = 0")


def upsert_file(conn: sqlite3.Connection, rel_path: str, size: int,
                mtime: float, ext: str) -> None:
    """Добавить новый файл в индекс или обновить существующий.

    Если у существующего файла изменились размер или время изменения, его хэш
    сбрасывается в NULL — значит содержимое могло поменяться и хэш надо
    пересчитать. Если файл не менялся, сохранённый хэш переиспользуется.
    """
    now = time.time()
    conn.execute(
        """
        INSERT INTO files (rel_path, size, mtime, ext, present, updated_at)
        VALUES (?, ?, ?, ?, 1, ?)
        ON CONFLICT(rel_path) DO UPDATE SET
            hash = CASE
                WHEN files.size != excluded.size OR files.mtime != excluded.mtime
                THEN NULL
                ELSE files.hash
            END,
            size       = excluded.size,
            mtime      = excluded.mtime,
            ext        = excluded.ext,
            present    = 1,
            updated_at = excluded.updated_at
        """,
        (rel_path, size, mtime, ext, now),
    )


def count_absent(conn: sqlite3.Connection) -> int:
    """Сколько файлов помечено как отсутствующие после сканирования."""
    row = conn.execute("SELECT COUNT(*) AS n FROM files WHERE present = 0").fetchone()
    return row["n"]


# --- Операции с хэшами и дубликатами (этап 3) ---

def files_needing_hash(conn: sqlite3.Connection):
    """Вернуть присутствующие файлы, у которых ещё нет хэша."""
    return conn.execute(
        "SELECT rel_path FROM files WHERE present = 1 AND hash IS NULL"
    ).fetchall()


def set_hash(conn: sqlite3.Connection, rel_path: str, file_hash: str) -> None:
    """Сохранить хэш файла в индексе."""
    conn.execute(
        "UPDATE files SET hash = ? WHERE rel_path = ?",
        (file_hash, rel_path),
    )


def find_duplicates(conn: sqlite3.Connection):
    """Вернуть группы дубликатов: {hash: [rel_path, ...]} для 2+ файлов.

    Учитываются только присутствующие файлы с посчитанным хэшем.
    """
    rows = conn.execute(
        """
        SELECT hash, rel_path, size
        FROM files
        WHERE present = 1 AND hash IS NOT NULL
          AND hash IN (
              SELECT hash FROM files
              WHERE present = 1 AND hash IS NOT NULL
              GROUP BY hash
              HAVING COUNT(*) > 1
          )
        ORDER BY hash, rel_path
        """
    ).fetchall()

    groups = {}
    for row in rows:
        groups.setdefault(row["hash"], []).append((row["rel_path"], row["size"]))
    return groups
