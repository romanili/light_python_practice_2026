"""Консольный индексатор папок (полный вариант практики).

Этап 1 — каркас:
- принимает путь к папке аргументом запуска;
- проверяет, что путь существует и это папка;
- создаёт базу SQLite со схемой индекса.

Запуск:
    python src/main.py <путь_к_папке>

Следующие этапы (сканирование, дубликаты, бэкап) добавляются поверх.
"""

import argparse
import sys
from pathlib import Path

import db


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="indexer",
        description="Консольный индексатор папок (SQLite).",
    )
    parser.add_argument(
        "path",
        help="путь к папке, которую нужно проиндексировать",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    target = Path(args.path).expanduser()

    if not target.exists():
        print(f"Ошибка: путь не существует: {target}", file=sys.stderr)
        return 1
    if not target.is_dir():
        print(f"Ошибка: это не папка: {target}", file=sys.stderr)
        return 1

    # Инициализация базы при запуске утилиты.
    db_path = db.init_db()

    print(f"Папка для индексации: {target.resolve()}")
    print(f"База данных готова:    {db_path}")
    print("Этап 1 (каркас): база создана, путь принят.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
