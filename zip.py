import os
import zipfile
import json
from pathlib import Path


def create_project_archive():
    """Создает архив с ключевыми файлами проекта"""

    # Файлы для включения в архив (исключаем логи, __pycache__, .env)
    include_patterns = [
        '*.py',
        '*.txt',
        '*.md',
        '*.json',
        '*.yaml',
        '*.yml'
    ]

    exclude_patterns = [
        '__pycache__',
        '*.pyc',
        '.env',
        'logs/',
        'venv/',
        '.git/',
        'node_modules/'
    ]

    project_root = Path('.')
    archive_name = 'twitter_automation_core.zip'

    with zipfile.ZipFile(archive_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(project_root):
            # Исключаем ненужные директории
            dirs[:] = [d for d in dirs if not any(pattern.rstrip('/') in d for pattern in exclude_patterns)]

            for file in files:
                file_path = Path(root) / file

                # Проверяем, подходит ли файл под паттерны
                if any(file_path.match(pattern) for pattern in include_patterns):
                    if not any(pattern.rstrip('/') in str(file_path) for pattern in exclude_patterns):
                        arcname = file_path.relative_to(project_root)
                        zipf.write(file_path, arcname)
                        print(f"Добавлен: {arcname}")

    print(f"\nАрхив создан: {archive_name}")
    return archive_name


def create_project_summary():
    """Создает JSON с описанием структуры проекта"""
    project_structure = {
        "name": "Twitter Automation Bot",
        "description": "Telegram бот для автоматизации Twitter активности",
        "main_modules": {
            "bot": "Telegram бот с обработчиками команд и клавиатурами",
            "core": "Базовые классы для работы с Twitter, прокси, браузерами",
            "modules": {
                "influencers": "Модуль для инфлюенсеров - генерация контента, комментирование",
                "shillers": "Модуль шиллеров - кольца аккаунтов, ротация, шиллинг",
                "memecoin": "Создание аккаунтов под мемкоины"
            },
            "database": "Модели данных и работа с БД",
            "utils": "AI помощники, валидаторы, логирование"
        },
        "key_features": [
            "Управление множественными Twitter аккаунтами",
            "Работа через прокси",
            "AI генерация контента",
            "Автоматическое комментирование",
            "Шиллинг в кольцах аккаунтов",
            "Статистика и аналитика"
        ],
        "technologies": [
            "Python",
            "Telegram Bot API",
            "Playwright (браузерная автоматизация)",
            "SQLAlchemy (база данных)",
            "OpenAI API",
            "Asyncio"
        ]
    }

    with open('project_summary.json', 'w', encoding='utf-8') as f:
        json.dump(project_structure, f, ensure_ascii=False, indent=2)

    print("Создан файл project_summary.json с описанием проекта")


if __name__ == "__main__":
    create_project_archive()
    create_project_summary()