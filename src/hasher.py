"""Подсчёт хэша содержимого файла (этап 3).

Хэш считается по содержимому, файл читается блоками, чтобы не держать
большие файлы целиком в памяти. Используется sha256 из стандартной библиотеки.
"""

import hashlib
from pathlib import Path

# Размер блока чтения (64 КБ).
CHUNK_SIZE = 64 * 1024


def file_hash(path, algo="sha256", chunk_size=CHUNK_SIZE):
    """Посчитать хэш файла по содержимому.

    Возвращает шестнадцатеричную строку хэша или None, если файл не удалось
    прочитать (например, нет прав доступа).
    """
    path = Path(path)
    digest = hashlib.new(algo)
    try:
        with open(path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                digest.update(chunk)
    except OSError:
        return None
    return digest.hexdigest()
