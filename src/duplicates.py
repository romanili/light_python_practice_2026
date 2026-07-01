"""Поиск дубликатов файлов по хэшу содержимого (этап 3).

Досчитывает недостающие хэши для файлов в индексе и переиспользует уже
посчитанные (они сохраняются в SQLite между запусками). Затем собирает
группы файлов с одинаковым хэшем.
"""

from pathlib import Path

import db
import hasher


def update_hashes(root, db_path=db.DB_PATH):
    """Посчитать хэши для присутствующих файлов, у которых их ещё нет.

    Возвращает количество посчитанных хэшей.
    """
    root = Path(root).resolve()
    conn = db.get_connection(db_path)
    computed = 0
    try:
        for row in db.files_needing_hash(conn):
            rel_path = row["rel_path"]
            full_path = root / rel_path
            file_hash = hasher.file_hash(full_path)
            if file_hash is not None:
                db.set_hash(conn, rel_path, file_hash)
                computed += 1
        conn.commit()
    finally:
        conn.close()
    return computed


def find(db_path=db.DB_PATH):
    """Вернуть группы дубликатов: {hash: [(rel_path, size), ...]}."""
    conn = db.get_connection(db_path)
    try:
        return db.find_duplicates(conn)
    finally:
        conn.close()
