"""Сравнение исходной папки с резервной копией (этап 4).

Строит снимки обеих папок (относительный путь -> размер и абсолютный путь),
сравнивает их и раскладывает файлы по категориям:
  missing — есть в исходной папке, но нет в бэкапе (не забэкаплены);
  changed — есть в обеих, но содержимое отличается;
  extra   — есть в бэкапе, но нет в исходной папке (лишние);
  same    — совпадают.

Файлы с одинаковым размером дополнительно сверяются по хэшу содержимого.
Результат проверки сохраняется в SQLite.
"""

import os
from pathlib import Path

import db
import hasher


def snapshot(root):
    """Собрать снимок папки: {rel_path: (size, full_path)}."""
    root = Path(root).resolve()
    result = {}
    for dirpath, _dirnames, filenames in os.walk(root):
        for filename in filenames:
            full_path = Path(dirpath) / filename
            try:
                size = full_path.stat().st_size
            except OSError:
                continue
            rel_path = str(full_path.relative_to(root))
            result[rel_path] = (size, full_path)
    return result


def compare(source, backup):
    """Сравнить исходную папку с бэкапом.

    Возвращает словарь со списками missing, changed, extra, same
    (каждый — отсортированный список относительных путей).
    """
    src = snapshot(source)
    bak = snapshot(backup)

    missing, changed, same = [], [], []
    for rel_path, (size, full_path) in src.items():
        if rel_path not in bak:
            missing.append(rel_path)
            continue
        bak_size, bak_path = bak[rel_path]
        if size != bak_size:
            changed.append(rel_path)
        elif hasher.file_hash(full_path) != hasher.file_hash(bak_path):
            changed.append(rel_path)
        else:
            same.append(rel_path)

    extra = [rel_path for rel_path in bak if rel_path not in src]

    return {
        "missing": sorted(missing),
        "changed": sorted(changed),
        "extra": sorted(extra),
        "same": sorted(same),
    }


def run(source, backup, db_path=db.DB_PATH):
    """Сравнить папки, сохранить результат в БД и вернуть (result, check_id)."""
    result = compare(source, backup)
    conn = db.get_connection(db_path)
    try:
        check_id = db.save_backup_check(
            conn,
            str(Path(source).resolve()),
            str(Path(backup).resolve()),
            result["missing"],
            result["changed"],
            result["extra"],
        )
        conn.commit()
    finally:
        conn.close()
    return result, check_id
