"""Консольный индексатор папок (полный вариант практики).

Этап 1 — каркас: приём пути, структура проекта, схема SQLite.
Этап 2 — сканирование: рекурсивный обход папки, сбор метаданных,
сохранение индекса в SQLite, простые фильтры.
Этап 3 — дубликаты: подсчёт хэшей и поиск файлов с одинаковым содержимым.
Этап 4 — резервная копия: сравнение папки с бэкапом и отчёт о различиях.

Запуск:
    python src/main.py <путь_к_папке>
    python src/main.py <путь_к_папке> --ext .txt
    python src/main.py <путь_к_папке> --name отчет
    python src/main.py <путь_к_папке> --dupes
    python src/main.py <путь_к_папке> --backup <путь_к_бэкапу>
"""

import argparse
import sys
from pathlib import Path

import backup
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
    parser.add_argument(
        "--backup",
        help="путь к папке резервной копии для сравнения",
    )
    parser.add_argument(
        "--missing",
        action="store_true",
        help="показать список файлов, помеченных как отсутствующие",
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

    if args.missing:
        print_missing()

    if args.dupes:
        print_duplicates(target)

    if args.backup:
        backup_dir = Path(args.backup).expanduser()
        if not backup_dir.is_dir():
            print(f"Ошибка: папка бэкапа не найдена: {backup_dir}", file=sys.stderr)
            return 1
        print_backup(target, backup_dir)

    return 0


def print_missing() -> None:
    """Вывести список файлов, помеченных как отсутствующие."""
    conn = db.get_connection()
    try:
        absent = db.list_absent(conn)
    finally:
        conn.close()

    print("\n" + "=" * 60)
    print(f"Отсутствующие файлы (исчезли из папки): {len(absent)}")
    print("=" * 60)
    if not absent:
        print("Нет отсутствующих файлов.")
        return
    for rel_path in absent:
        print(f"    {rel_path}")


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


def print_backup(source: Path, backup_dir: Path) -> None:
    """Сравнить папку с бэкапом, вывести отчёт и сохранить результат."""
    result, check_id = backup.run(source, backup_dir)

    print("\n" + "=" * 60)
    print("Сравнение с резервной копией")
    print(f"  исходная папка: {source.resolve()}")
    print(f"  бэкап:          {backup_dir.resolve()}")
    print("=" * 60)

    sections = [
        ("Нет в бэкапе (не забэкаплены)", result["missing"]),
        ("Отличаются (изменены)", result["changed"]),
        ("Лишние в бэкапе", result["extra"]),
    ]
    for title, items in sections:
        print(f"\n{title}: {len(items)}")
        for rel_path in items:
            print(f"    {rel_path}")

    print(f"\nСовпадают: {len(result['same'])}")
    print(f"\nРезультат проверки сохранён в БД (проверка #{check_id}).")


if __name__ == "__main__":
    raise SystemExit(main())
