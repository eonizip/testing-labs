# -*- coding: utf-8 -*-
"""Фикстуры интеграционных тестов: параметризация по реализациям и изоляция состояния.

Каждый тест получает НОВЫЕ экземпляры валидатора и сервиса (фикстуры с областью function),
поэтому порядок запуска тестов не влияет на результат.
"""
import importlib
import os

import pytest

from lab.subscriber_service import SubscriberService

IMPLEMENTATIONS = [
    ("Gen1_ChatGPT", "lab.implementations.gencode1"),
    ("Gen2_DeepSeek", "lab.implementations.gencode2"),
    ("Gen3_Claude", "lab.implementations.gencode3"),
]
if os.environ.get("LAB_INCLUDE_CONTROL") == "1":
    IMPLEMENTATIONS.append(("Control_Faulty", "control_impl"))


@pytest.fixture(params=[pytest.param(mod, id=name) for name, mod in IMPLEMENTATIONS])
def validator_cls(request):
    """Класс EmailValidator одной из реализаций (параметризация без дублирования тестов)."""
    return importlib.import_module(request.param).EmailValidator


@pytest.fixture
def validator(validator_cls):
    return validator_cls()


@pytest.fixture
def service(validator):
    return SubscriberService(validator)


@pytest.fixture
def make_service(validator_cls):
    """Фабрика: свежий сервис с новым валидатором и заданной ёмкостью."""
    def _make(capacity=100):
        return SubscriberService(validator_cls(), capacity=capacity)
    return _make
