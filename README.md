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

## Интеграционное тестирование (лабораторная работа №6)

* `src/lab/implementations/` - три ИИ-реализации IEmailValidator (ChatGPT, DeepSeek, Claude).
* `src/lab/subscriber_service.py` - сервис-потребитель `SubscriberService`, зависящий от `IEmailValidator`.
* `tests/integration/` - интеграционные тесты (параметризация по реализациям, свежие экземпляры в каждом тесте).
* `scripts/compare_implementations.py` - дифференциальное сравнение реализаций.

        python -m pytest tests/integration -v
        LAB_INCLUDE_CONTROL=1 python -m pytest tests/integration    # + заведомо неверная реализация (контроль)

## Приложение с GUI (лабораторные работы №7 и №8)

Окно «Менеджер подписчиков» (PySide6) использует одну реализацию - Gen3 (Claude).

        python -m pip install -r requirements-gui.txt
        PYTHONPATH=src python -m lab.gui.app                                    # запуск (Windows: set PYTHONPATH=src)
        QT_QPA_PLATFORM=offscreen PYTHONPATH=src python scripts/gui_checks.py system artifacts/gui   # сценарии ЛР №7
        QT_QPA_PLATFORM=offscreen PYTHONPATH=src python scripts/gui_checks.py manual artifacts/gui   # чек-лист ЛР №8
