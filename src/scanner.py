"""Сканирование папки и обновление индекса в SQLite (этап 2).

Рекурсивно обходит папку, собирает по каждому файлу путь, размер, время
изменения и расширение, и сохраняет результат в индекс. Фильтры по
расширению и имени применяются к выводу — сам индекс всегда отражает
реальное содержимое папки.
"""

import os
from pathlib import Path

import db


def normalize_ext(ext):
    """Привести расширение к виду '.txt' (с точкой, в нижнем регистре)."""
    if ext is None:
        return None
    ext = ext.lower()
    if not ext.startswith("."):
        ext = "." + ext
    return ext


def matches(filename, ext=None, name_contains=None):
    """Подходит ли файл под фильтры расширения/имени."""
    if ext is not None and Path(filename).suffix.lower() != ext:
        return False
    if name_contains is not None and name_contains not in filename.lower():
        return False
    return True


def iter_files(root):
    """Рекурсивно перебрать все файлы папки."""
    root = Path(root)
    for dirpath, _dirnames, filenames in os.walk(root):
        for filename in filenames:
            yield Path(dirpath) / filename


def scan(root, ext=None, name_contains=None, db_path=db.DB_PATH):
    """Просканировать папку и обновить индекс.

    Индексируются все файлы папки (present/absent отражает реальность).
    Фильтры влияют только на возвращаемый список для вывода.

    Возвращает кортеж (results, count, missing):
      results — список (rel_path, size, ext) файлов, прошедших фильтр;
      count   — сколько файлов прошло фильтр;
      missing — сколько записей помечено как отсутствующие.
    """
    root = Path(root).resolve()
    ext = normalize_ext(ext)
    name_contains = name_contains.lower() if name_contains else None

    conn = db.get_connection(db_path)
    try:
        scan_id = db.start_scan(conn, str(root))
        # Помечаем всё как отсутствующее, обход вернёт present=1 тем, что нашлись.
        db.mark_all_absent(conn)

        results = []
        indexed = 0
        for full_path in iter_files(root):
            rel_path = str(full_path.relative_to(root))
            stat = full_path.stat()
            file_ext = full_path.suffix.lower()
            db.upsert_file(conn, rel_path, stat.st_size, stat.st_mtime, file_ext)
            indexed += 1
            if matches(full_path.name, ext, name_contains):
                results.append((rel_path, stat.st_size, file_ext))

        missing = db.count_absent(conn)
        db.finish_scan(conn, scan_id, indexed)
        conn.commit()
        return results, len(results), missing
    finally:
        conn.close()
