"""Консольный индексатор папок (полный вариант практики).

Этап 1 — каркас: приём пути, структура проекта, схема SQLite.
Этап 2 — сканирование: рекурсивный обход папки, сбор метаданных,
сохранение индекса в SQLite, простые фильтры.
Этап 3 — дубликаты: подсчёт хэшей и поиск файлов с одинаковым содержимым.

Запуск:
    python src/main.py <путь_к_папке>
    python src/main.py <путь_к_папке> --ext .txt
    python src/main.py <путь_к_папке> --name отчет
    python src/main.py <путь_к_папке> --dupes

Следующий этап (бэкап) добавляется поверх.
"""

import argparse
import sys
from pathlib import Path

import db
import duplicates
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
    parser.add_argument(
        "--dupes",
        action="store_true",
        help="посчитать хэши и показать группы дубликатов",
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

    if args.dupes:
        print_duplicates(target)

    return 0


def print_duplicates(target: Path) -> None:
    """Посчитать хэши и вывести группы дубликатов."""
    computed = duplicates.update_hashes(target)
    groups = duplicates.find()

    print("\n" + "=" * 60)
    print(f"Поиск дубликатов (посчитано новых хэшей: {computed})")
    print("=" * 60)

    if not groups:
        print("Дубликатов не найдено.")
        return

    for i, (file_hash, items) in enumerate(groups.items(), start=1):
        size = items[0][1]
        print(f"\nГруппа {i} — {len(items)} файла(ов), {size} байт, hash {file_hash[:12]}…")
        for rel_path, _size in items:
            print(f"    {rel_path}")


if __name__ == "__main__":
    raise SystemExit(main())
