"""Общие фикстуры. Тесты запускаются для той реализации, которая лежит в src/lab/email_validator.py
(в каждой ветке ai-version-N — своя реализация, набор тестов один и тот же)."""

import pytest

from lab.email_validator import EmailValidator


@pytest.fixture
def validator():
    """Экземпляр тестируемого EmailValidator."""
    return EmailValidator()
