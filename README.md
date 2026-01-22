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

## Sumagent Stage B

Stage B строит иерархию модулей и аспектные витрины на основе Stage A summaries.

### Запуск

```bash
python -m sumagent_b build --repo /path/to/repo --summary-dir .summary
```

Пересчитать одну витрину:

```bash
python -m sumagent_b build-view --repo /path/to/repo --summary-dir .summary --aspect security_auth
```

Пересчитать один модуль (по root_path):

```bash
python -m sumagent_b build-module --repo /path/to/repo --summary-dir .summary --module-root src
```

### Конфигурация

Опционально можно передать `summary_b.config.json`:

```bash
python -m sumagent_b build --repo /path/to/repo --summary-dir .summary --config summary_b.config.json
```

Пример находится в `summary_b.config.json.example`.
