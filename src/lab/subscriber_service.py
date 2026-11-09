# -*- coding: utf-8 -*-
"""Сервис-потребитель для интеграционного тестирования (ЛР №6).

SubscriberService хранит список подписчиков рассылки и формирует отчёт. Проверку адресов и
выделение домена он целиком делегирует зависимости IEmailValidator, поэтому его поведение
зависит от того, какая из трёх ИИ-реализаций ему подставлена.
"""
from __future__ import annotations

from lab.interfaces import IEmailValidator


class InvalidEmailError(ValueError):
    """Адрес не прошёл проверку валидатором."""


class SubscriberLimitError(Exception):
    """Достигнуто максимальное число подписчиков."""


class SubscriberService:
    def __init__(self, validator: IEmailValidator, capacity: int = 100) -> None:
        if capacity < 1:
            raise ValueError("capacity должен быть не меньше 1")
        self._validator = validator
        self._capacity = capacity
        self._items: dict[str, str] = {}      # ключ -> домен; порядок добавления сохраняется

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def count(self) -> int:
        return len(self._items)

    def _key(self, email: str) -> str:
        """Ключ подписчика: локальная часть как есть, домен без учёта регистра."""
        local, _ = email.split("@")
        return f"{local}@{self._validator.extract_domain(email)}"

    def subscribe(self, email: str | None) -> bool:
        """True - подписчик добавлен, False - такой адрес уже есть.

        InvalidEmailError - валидатор отклонил адрес; SubscriberLimitError - список заполнен.
        """
        if not self._validator.is_valid(email):
            raise InvalidEmailError(f"Некорректный адрес: {email!r}")
        key = self._key(email)
        if key in self._items:
            return False
        if len(self._items) >= self._capacity:
            raise SubscriberLimitError(f"Достигнут предел: {self._capacity} подписчиков")
        self._items[key] = self._validator.extract_domain(email)
        return True

    def unsubscribe(self, email: str | None) -> bool:
        """True - подписчик удалён, False - такого адреса нет. Некорректный адрес даёт False."""
        if not self._validator.is_valid(email):
            return False
        return self._items.pop(self._key(email), None) is not None

    def subscribers(self) -> list[str]:
        return list(self._items)

    def domain_stats(self) -> dict[str, int]:
        stats: dict[str, int] = {}
        for domain in self._items.values():
            stats[domain] = stats.get(domain, 0) + 1
        return dict(sorted(stats.items(), key=lambda kv: (-kv[1], kv[0])))

    def clear(self) -> None:
        self._items.clear()

    def report(self) -> str:
        if not self._items:
            return "Список подписчиков пуст."
        stats = self.domain_stats()
        parts = "; ".join(f"{d} — {n}" for d, n in stats.items())
        return f"Отчёт: всего {self.count}, доменов {len(stats)} ({parts})."
