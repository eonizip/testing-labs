# -*- coding: utf-8 -*-
"""Контрольная (заведомо неверная) реализация IEmailValidator.

Нужна только для проверки того, что интеграционные тесты умеют обнаруживать нарушение контракта.
В основной сравнительный набор не входит: подключается переменной окружения LAB_INCLUDE_CONTROL=1.
Дефекты: (1) is_valid бросает TypeError для не-строк (нарушение NFR-1);
(2) extract_domain не приводит домен к нижнему регистру (нарушение FR-6).
"""
from lab.implementations.gencode3 import EmailValidator as _Base


class EmailValidator(_Base):
    def is_valid(self, email):
        if email is not None and not isinstance(email, str):
            raise TypeError("ожидалась строка")
        return super().is_valid(email)

    def extract_domain(self, email):
        if not self.is_valid(email):
            raise ValueError("Некорректный email")
        return email.split("@")[1]
