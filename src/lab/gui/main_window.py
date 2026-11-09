# -*- coding: utf-8 -*-
"""Главное окно приложения «Менеджер подписчиков» (ЛР №7).

Архитектура: элементы GUI -> обработчики событий (этот класс) -> SubscriberService ->
IEmailValidator (реализация Gen3, Claude) -> визуальная отдача (список, статус, отчёт).
Бизнес-логики в окне нет: оно только передаёт вызовы и показывает результат.
"""
from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QLineEdit, QListWidget, QMainWindow, QPlainTextEdit,
                               QPushButton, QVBoxLayout, QWidget)

from lab.implementations.gencode3 import EmailValidator   # единственная реализация в сборке (лучшая по ПР №1, №4)
from lab.subscriber_service import InvalidEmailError, SubscriberLimitError, SubscriberService

OK_STYLE = "color: #1b7f3b;"
ERR_STYLE = "color: #b3261e;"


class MainWindow(QMainWindow):
    def __init__(self, storage_path: str | Path | None = None, capacity: int = 100) -> None:
        super().__init__()
        self.setWindowTitle("Менеджер подписчиков")
        self.resize(560, 560)
        self._service = SubscriberService(EmailValidator(), capacity=capacity)
        self._storage = Path(storage_path) if storage_path else None

        self.input = QLineEdit(objectName="input")
        self.input.setPlaceholderText("Введите e-mail подписчика")
        self.btn_add = QPushButton("Добавить", objectName="btnAdd")
        self.status = QLabel("", objectName="lblStatus")
        self.counter = QLabel(objectName="lblCounter")
        self.list = QListWidget(objectName="listSubscribers")
        self.btn_remove = QPushButton("Удалить выбранного", objectName="btnRemove")
        self.btn_report = QPushButton("Сформировать отчёт", objectName="btnReport")
        self.report = QPlainTextEdit(objectName="txtReport")
        self.report.setReadOnly(True)
        self.report.setPlaceholderText("Здесь появится отчёт")
        self.report.setMaximumHeight(90)

        top = QHBoxLayout(); top.addWidget(self.input, 1); top.addWidget(self.btn_add)
        mid = QHBoxLayout(); mid.addWidget(self.btn_remove); mid.addWidget(self.btn_report); mid.addStretch(1)
        lay = QVBoxLayout()
        lay.addWidget(QLabel("Адрес подписчика:")); lay.addLayout(top); lay.addWidget(self.status)
        lay.addWidget(self.counter); lay.addWidget(self.list, 1); lay.addLayout(mid); lay.addWidget(self.report)
        root = QWidget(); root.setLayout(lay); self.setCentralWidget(root)

        self.btn_add.clicked.connect(self.on_add)
        self.input.returnPressed.connect(self.on_add)
        self.btn_remove.clicked.connect(self.on_remove)
        self.btn_report.clicked.connect(self.on_report)
        self.list.itemSelectionChanged.connect(self._sync_buttons)

        self._load()
        self._refresh()

    # ---------- обработчики событий ----------
    def on_add(self) -> None:
        text = self.input.text().strip()          # пробелы по краям ввода обрезаются на уровне GUI
        if not text:
            self._say("Введите адрес e-mail.", error=True)
            return
        try:
            added = self._service.subscribe(text)
        except InvalidEmailError:
            self._say(f"Некорректный адрес: {text}", error=True)
            return
        except SubscriberLimitError as exc:
            self._say(str(exc), error=True)
            return
        if added:
            self._say(f"Добавлен: {text}")
            self.input.clear()
            self._save()
        else:
            self._say(f"Такой подписчик уже есть: {text}", error=True)
        self._refresh()

    def on_remove(self) -> None:
        item = self.list.currentItem()
        if item is None:
            self._say("Выберите подписчика в списке.", error=True)
            return
        self._service.unsubscribe(item.text())
        self._say(f"Удалён: {item.text()}")
        self._save()
        self._refresh()

    def on_report(self) -> None:
        self.report.setPlainText(self._service.report())

    # ---------- вспомогательные методы ----------
    def _say(self, text: str, error: bool = False) -> None:
        self.status.setStyleSheet(ERR_STYLE if error else OK_STYLE)
        self.status.setText(text)

    def _sync_buttons(self) -> None:
        self.btn_remove.setEnabled(self.list.currentItem() is not None)

    def _refresh(self) -> None:
        self.list.clear()
        self.list.addItems(self._service.subscribers())
        self.counter.setText(f"Подписчиков: {self._service.count} из {self._service.capacity}")
        self._sync_buttons()
        if self.report.toPlainText():             # открытый отчёт не должен устаревать
            self.on_report()

    # ---------- сохранение между запусками ----------
    def _save(self) -> None:
        if self._storage:
            self._storage.write_text(json.dumps(self._service.subscribers(), ensure_ascii=False), encoding="utf-8")

    def _load(self) -> None:
        if not self._storage or not self._storage.exists():
            return
        skipped = 0
        for email in json.loads(self._storage.read_text(encoding="utf-8")):
            try:
                self._service.subscribe(email)
            except (InvalidEmailError, SubscriberLimitError):
                skipped += 1
        if skipped:
            self._say(f"При загрузке пропущено записей: {skipped}", error=True)
