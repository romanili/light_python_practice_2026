"""Консольный индексатор папок (полный вариант практики).

Этап 1 — каркас: приём пути, структура проекта, схема SQLite.
Этап 2 — сканирование: рекурсивный обход папки, сбор метаданных,
сохранение индекса в SQLite, простые фильтры.

Запуск:
    python src/main.py <путь_к_папке>
    python src/main.py <путь_к_папке> --ext .txt
    python src/main.py <путь_к_папке> --name отчет

Следующие этапы (дубликаты, бэкап) добавляются поверх.
"""

import argparse
import sys
from pathlib import Path

import db
import scanner


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="indexer",
        description="Консольный индексатор папок (SQLite).",
    )
    parser.add_argument(
        "path",
        help="путь к папке, которую нужно проиндексировать",
    )
    parser.add_argument(
        "--ext",
        help="фильтр по расширению, например .txt",
    )
    parser.add_argument(
        "--name",
        help="фильтр: подстрока в имени файла",
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
    db.init_db()

    # Сканирование и обновление индекса.
    results, count, missing = scanner.scan(
        target, ext=args.ext, name_contains=args.name
    )

    print(f"Папка: {target.resolve()}")
    if args.ext:
        print(f"Фильтр по расширению: {args.ext}")
    if args.name:
        print(f"Фильтр по имени: {args.name}")
    print("-" * 60)

    for rel_path, size, _ext in results:
        print(f"{size:>12}  {rel_path}")

    print("-" * 60)
    print(f"Найдено файлов: {count}")
    if missing:
        print(f"Помечено как отсутствующие (исчезли из папки): {missing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
