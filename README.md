# Sumagent Stage A

Утилита для сканирования репозитория и построения микро-суммаризаций файлов и директорий в JSON-формате.

## Установка

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> Примечание: дополнительных зависимостей нет, используется только стандартная библиотека Python 3.11+.

## Запуск

Полный прогон:

```bash
python -m sumagent_a summarize --repo /path/to/repo
```

Суммаризация одного файла:

```bash
python -m sumagent_a summarize-file --repo /path/to/repo --path path/in/repo.py
```

Суммаризация директории:

```bash
python -m sumagent_a summarize-dir --repo /path/to/repo --path path/in/repo
```

## Конфигурация

Опционально можно передать файл конфигурации:

```bash
python -m sumagent_a summarize --repo /path/to/repo --config summarizer.config.json
```

Пример находится в `summarizer.config.json.example`.

## Выходные артефакты

По умолчанию создаётся структура `.summary/`:

```
.summary/
  files/        # FileSummary JSON
  dirs/         # DirSummary JSON
  runs/         # jsonl логи прогонов
  index.json    # обратная карта файлов/директорий
```

Имя summary-файла детерминировано: `sha256(relative_path).json`.
