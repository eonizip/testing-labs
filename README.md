# EmailValidator: автоматизация тестирования (GitHub Actions)

Три версии модуля `EmailValidator`, сгенерированные нейросетями (ChatGPT, DeepSeek, Claude),
один общий набор тестов pytest и пайплайны GitHub Actions.

| Ветка | Реализация |
|-------|------------|
| `ai-version-1` | ChatGPT |
| `ai-version-2` | DeepSeek |
| `ai-version-3` | Claude |
| `main` | рабочая ветка (реализация Claude) и пайплайны |

## Локальный запуск

    python -m venv .venv && source .venv/bin/activate
    python -m pip install -r requirements.txt
    python -m pytest -v

## Пайплайны

* `.github/workflows/ci.yml` — тесты при push, pull_request и вручную (workflow_dispatch).
* `.github/workflows/compare.yml` — ручной запуск: тесты всех трёх веток и единый отчёт.

## Автоматическая генерация тестов (лабораторная работа №5)

* `spec/emailvalidator.yaml` — формальная спецификация с трассировкой требований (FR-n, NFR-n).
* `generator/gen_tests.py` — генератор pytest-тестов из спецификации; `config.yaml` — его параметры.
* Сгенерированные тесты не хранятся в репозитории: пайплайн создаёт их при каждом запуске.

        python generator/gen_tests.py                       # сгенерировать тесты и матрицу трассировки
        python generator/gen_tests.py --verify-determinism  # проверить детерминированность
        python -m pytest -v

Дополнительные скрипты: `scripts/local_compare.py` (локальный аналог compare.yml),
`scripts/code_metrics.py` (метрики кода), `scripts/mutants_check.py` (мутационная проверка тестов).
