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
