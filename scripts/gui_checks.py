#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Прогон сценариев GUI (ЛР №7 - системные сценарии, ЛР №8 - ручной чек-лист) через виджеты окна.

Окно создаётся настоящее (PySide6), действия выполняются теми же сигналами, что и мышь/клавиатура
(click, QTest.keyClick), результаты считываются из видимых элементов. Скриншоты - widget.grab().
Запуск:  QT_QPA_PLATFORM=offscreen PYTHONPATH=src python scripts/gui_checks.py system|manual OUTDIR
"""
import json
import sys
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from lab.gui.main_window import MainWindow

APP = QApplication.instance() or QApplication([])
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("artifacts/gui")
OUT.mkdir(parents=True, exist_ok=True)
TMP = Path(tempfile.mkdtemp())


def new_window(storage=None, capacity=100):
    w = MainWindow(storage_path=storage, capacity=capacity)
    w.show(); APP.processEvents()
    return w


def shot(w, name):
    w.grab().save(str(OUT / f"{name}.png"))
    return f"{name}.png"


def items(w):
    return [w.list.item(i).text() for i in range(w.list.count())]


def add(w, text):
    w.input.setText(text); w.btn_add.click(); APP.processEvents()


class Scenario:
    def __init__(self, sid, title, initial, steps):
        self.d = dict(id=sid, title=title, initial=initial, steps=steps, checks=[], screens=[])

    def check(self, what, expected, actual):
        self.d["checks"].append(dict(what=what, expected=expected, actual=actual, ok=expected == actual))

    def done(self):
        self.d["status"] = "Pass" if all(c["ok"] for c in self.d["checks"]) else "Fail"
        return self.d


# =================== ЛР №7: системные сценарии ===================
def s1():
    sc = Scenario("S1", "Полный жизненный цикл подписчика", "Приложение запущено, список пуст",
                  ["Ввести «anna@example.com» → «Добавить»", "Ввести «bob@Mail.org» → «Добавить»",
                   "Выбрать первую строку списка → «Удалить выбранного»", "Нажать «Сформировать отчёт»"])
    w = new_window()
    add(w, "anna@example.com"); add(w, "bob@Mail.org")
    sc.check("список после добавления", ["anna@example.com", "bob@mail.org"], items(w))
    sc.check("статус", "Добавлен: bob@Mail.org", w.status.text())
    sc.check("счётчик", "Подписчиков: 2 из 100", w.counter.text())
    sc.d["screens"].append(shot(w, "s1_after_add"))
    w.list.setCurrentRow(0); w.btn_remove.click(); w.btn_report.click(); APP.processEvents()
    sc.check("список после удаления", ["bob@mail.org"], items(w))
    sc.check("отчёт", "Отчёт: всего 1, доменов 1 (mail.org — 1).", w.report.toPlainText())
    sc.d["screens"].append(shot(w, "s1_after_remove"))
    return sc.done()


def s2():
    sc = Scenario("S2", "Валидация ввода (UI и бизнес-логика)", "Список пуст",
                  ["Для каждого значения ввести его в поле и нажать «Добавить»; список должен остаться пустым:",
                   "«» , «   », «user.example.com», «user@example», «юзер@example.com», «a@@b.co»",
                   "Ввести « a@b.co » (пробелы по краям) → «Добавить»", "Ввести «a@B.CO» → «Добавить» (повтор)"])
    w = new_window()
    cases = [("", "Введите адрес e-mail."), ("   ", "Введите адрес e-mail."),
             ("user.example.com", "Некорректный адрес: user.example.com"), ("user@example", "Некорректный адрес: user@example"),
             ("юзер@example.com", "Некорректный адрес: юзер@example.com"), ("a@@b.co", "Некорректный адрес: a@@b.co")]
    for value, msg in cases:
        add(w, value)
        sc.check(f"ввод {value!r}: сообщение", msg, w.status.text())
        sc.check(f"ввод {value!r}: список пуст", [], items(w))
        if value == "юзер@example.com":
            sc.d["screens"].append(shot(w, "s2_error"))
    add(w, " a@b.co ")
    sc.check("пробелы по краям обрезаются", ["a@b.co"], items(w))
    add(w, "a@B.CO")
    sc.check("повтор: сообщение", "Такой подписчик уже есть: a@B.CO", w.status.text())
    sc.check("повтор: список не изменился", ["a@b.co"], items(w))
    return sc.done()


def s3():
    sc = Scenario("S3", "Корректность отчёта", "Список пуст",
                  ["Добавить: a@x.com, b@X.com, c@y.org, d@z.net, e@y.org", "Нажать «Сформировать отчёт»"])
    w = new_window()
    for e in ("a@x.com", "b@X.com", "c@y.org", "d@z.net", "e@y.org"):
        add(w, e)
    w.btn_report.click(); APP.processEvents()
    sc.check("отчёт", "Отчёт: всего 5, доменов 3 (x.com — 2; y.org — 2; z.net — 1).", w.report.toPlainText())
    domains = {}
    for it in items(w):
        domains[it.split("@")[1]] = domains.get(it.split("@")[1], 0) + 1
    sc.check("число подписчиков в отчёте = строк в списке", 5, len(items(w)))
    sc.check("доменов по списку", 3, len(domains))
    sc.d["screens"].append(shot(w, "s3_report"))
    return sc.done()


def s4():
    sc = Scenario("S4", "Граничные сценарии", "Список пуст",
                  ["Сформировать отчёт при пустом списке", "Добавить 100 адресов подряд (предел), затем 101-й",
                   "Удалить один и добавить 101-й ещё раз", "Один раз ввести адрес и дважды подряд нажать «Добавить»"])
    w = new_window()
    w.btn_report.click(); APP.processEvents()
    sc.check("пустой отчёт", "Список подписчиков пуст.", w.report.toPlainText())
    t0 = time.perf_counter()
    for i in range(100):
        add(w, f"user{i}@site{i % 7}.org")
    dt = time.perf_counter() - t0
    sc.check("100 подписчиков, счётчик", "Подписчиков: 100 из 100", w.counter.text())
    add(w, "extra@site0.org")
    sc.check("101-й: сообщение", "Достигнут предел: 100 подписчиков", w.status.text())
    sc.check("101-й: список не вырос", 100, w.list.count())
    sc.d["screens"].append(shot(w, "s4_limit"))
    w.list.setCurrentRow(0); w.btn_remove.click()
    add(w, "extra@site0.org")
    sc.check("после удаления добавление проходит", "Добавлен: extra@site0.org", w.status.text())
    sc.check("быстрое добавление 100 записей быстрее 5 с", True, dt < 5)
    sc.d["time_100_adds_s"] = round(dt, 3)
    w2 = new_window()
    w2.input.setText("fast@click.org"); w2.btn_add.click(); w2.btn_add.click(); APP.processEvents()
    sc.check("двойной клик: одна запись", ["fast@click.org"], items(w2))
    sc.check("двойной клик: второй клик по пустому полю", "Введите адрес e-mail.", w2.status.text())
    return sc.done()


def s5():
    sc = Scenario("S5", "Согласованность состояния и перезапуск", "Файл сохранения не существует",
                  ["Добавить 3 адреса, закрыть окно", "Запустить окно заново с тем же файлом сохранения",
                   "Подменить файл: [«ok@x.co», «bad», «ok2@x.co»] и запустить окно"])
    store = TMP / "subs.json"
    w = new_window(store)
    for e in ("a@x.co", "b@y.co", "c@x.co"):
        add(w, e)
    before = items(w); w.close()
    w2 = new_window(store)
    sc.check("после перезапуска список прежний", before, items(w2))
    sc.check("счётчик после перезапуска", "Подписчиков: 3 из 100", w2.counter.text())
    sc.d["screens"].append(shot(w2, "s5_restart"))
    store.write_text(json.dumps(["ok@x.co", "bad", "ok2@x.co"]), encoding="utf-8")
    w3 = new_window(store)
    sc.check("повреждённая запись пропущена", ["ok@x.co", "ok2@x.co"], items(w3))
    sc.check("сообщение о пропуске", "При загрузке пропущено записей: 1", w3.status.text())
    return sc.done()


def s6():
    sc = Scenario("S6", "Актуальность открытого отчёта", "Список пуст",
                  ["Добавить a@x.co, сформировать отчёт", "Добавить b@y.co (без повторного нажатия «Сформировать отчёт»)",
                   "Удалить a@x.co"])
    w = new_window()
    add(w, "a@x.co"); w.btn_report.click()
    add(w, "b@y.co")
    sc.check("отчёт обновился после добавления", "Отчёт: всего 2, доменов 2 (x.co — 1; y.co — 1).", w.report.toPlainText())
    w.list.setCurrentRow(0); w.btn_remove.click(); APP.processEvents()
    sc.check("отчёт обновился после удаления", "Отчёт: всего 1, доменов 1 (y.co — 1).", w.report.toPlainText())
    return sc.done()


# =================== ЛР №8, часть 2: ручной чек-лист ===================
def lum(c):
    r = [(v / 255) for v in c]
    r = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in r]
    return 0.2126 * r[0] + 0.7152 * r[1] + 0.0722 * r[2]


def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return round((la + 0.05) / (lb + 0.05), 2)


def m_checks():
    out = []
    # M1: отображение данных после вызовов бизнес-логики
    sc = Scenario("M1", "Отображение данных после вызовов бизнес-логики", "Список пуст",
                  ["Добавить user@Example.com", "Сравнить строку списка, счётчик и статус с ожидаемыми"])
    w = new_window(); add(w, "user@Example.com")
    sc.check("строка списка (домен в нижнем регистре)", ["user@example.com"], items(w))
    sc.check("счётчик", "Подписчиков: 1 из 100", w.counter.text())
    sc.check("поле ввода очищено", "", w.input.text())
    sc.d["screens"].append(shot(w, "m1_after_add")); out.append(sc.done())
    # M2: валидация и работа с клавиатурой
    sc = Scenario("M2", "Валидация формы и работа с клавиатурой", "Список пуст, фокус в поле ввода",
                  ["Нажать Enter в пустом поле", "Ввести адрес и нажать Enter", "Проверить, где находится фокус после добавления"])
    w = new_window(); w.input.setFocus(); APP.processEvents()
    QTest.keyClick(w.input, Qt.Key_Return); APP.processEvents()
    sc.check("Enter в пустом поле: сообщение", "Введите адрес e-mail.", w.status.text())
    w.input.setText("kb@x.org"); QTest.keyClick(w.input, Qt.Key_Return); APP.processEvents()
    sc.check("Enter добавляет подписчика", ["kb@x.org"], items(w))
    focus = w.focusWidget().objectName() if w.focusWidget() else None
    sc.check("фокус остаётся в поле ввода после добавления", "input", focus)
    out[-1:] = out[-1:]; out.append(sc.done())
    # M3: быстрые и повторные действия
    sc = Scenario("M3", "Быстрые и повторные нажатия", "Список пуст",
                  ["20 быстрых добавлений разных адресов", "Двойной клик «Удалить выбранного»", "10 нажатий Enter подряд по одному адресу"])
    w = new_window()
    for i in range(20):
        add(w, f"q{i}@fast.org")
    sc.check("20 записей без потерь", 20, w.list.count())
    w.list.setCurrentRow(0); w.btn_remove.click(); w.btn_remove.click(); APP.processEvents()
    sc.check("двойной клик удалил одну запись", 19, w.list.count())
    w.input.setText("rep@x.org")
    for _ in range(10):
        QTest.keyClick(w.input, Qt.Key_Return)
    APP.processEvents()
    sc.check("повторные Enter: одна запись rep@x.org", 1, items(w).count("rep@x.org"))
    out.append(sc.done())
    # M4: формат отчёта
    sc = Scenario("M4", "Формирование отчёта", "Список пуст", ["Отчёт для 0, 1 и 3 подписчиков"])
    w = new_window(); w.btn_report.click()
    sc.check("0 подписчиков", "Список подписчиков пуст.", w.report.toPlainText())
    add(w, "a@Z.com"); w.btn_report.click()
    sc.check("1 подписчик", "Отчёт: всего 1, доменов 1 (z.com — 1).", w.report.toPlainText())
    add(w, "b@z.com"); add(w, "c@y.com"); w.btn_report.click()
    sc.check("3 подписчика", "Отчёт: всего 3, доменов 2 (z.com — 2; y.com — 1).", w.report.toPlainText())
    sc.d["screens"].append(shot(w, "m4_report")); out.append(sc.done())
    # M5: эргономика
    sc = Scenario("M5", "Эргономика и отзывчивость", "Список пуст",
                  ["Проверить доступность кнопки «Удалить» без выбора", "Обойти элементы клавишей Tab",
                   "Уменьшить окно до минимума", "Контраст цветов сообщений"])
    w = new_window()
    sc.check("«Удалить выбранного» неактивна без выбора", False, w.btn_remove.isEnabled())
    w.input.setFocus(); order = []
    for _ in range(5):
        order.append(w.focusWidget().objectName()); QTest.keyClick(w, Qt.Key_Tab); APP.processEvents()
    sc.check("порядок Tab (кнопка «Удалить» неактивна и пропускается)", ["input", "btnAdd", "listSubscribers", "btnReport", "txtReport"], order)
    w.resize(w.minimumSizeHint()); APP.processEvents()
    sc.d["min_size"] = [w.width(), w.height()]
    sc.check("минимальная ширина окна не больше 400 px", True, w.width() <= 400)
    bg = (239, 239, 239)
    sc.d["contrast_ok_green"] = contrast((0x1b, 0x7f, 0x3b), bg); sc.d["contrast_err_red"] = contrast((0xb3, 0x26, 0x1e), bg)
    sc.check("контраст текста сообщений не ниже 4.5:1", True, sc.d["contrast_ok_green"] >= 4.5 and sc.d["contrast_err_red"] >= 4.5)
    out.append(sc.done())
    # Исследовательские проверки (E): каждая фиксирует наблюдение
    obs = []
    w = new_window()
    long_bad = "x" * 70 + "@b.co"
    add(w, long_bad)
    full = w.status.text(); fm = w.status.fontMetrics()
    obs.append(dict(id="E1", what="Длинный некорректный адрес в строке статуса",
                    value=f"текст {len(full)} симв., ширина текста {fm.horizontalAdvance(full)} px, ширина метки {w.status.width()} px",
                    defect=fm.horizontalAdvance(full) > w.status.width()))
    shot(w, "e1_clipped_status")
    w = new_window()
    add(w, "a@b.co"); add(w, "a@b.co")
    obs.append(dict(id="E2", what="Сообщение о повторе окрашено цветом ошибки", value=w.status.text(),
                    defect=False, note="повтор — не сбой ввода, но цвет совпадает с ошибкой (замечание по UX)"))
    w = new_window(); w.status.setText("")
    add(w, "z@z.zz"); w.list.setCurrentRow(0); QTest.keyClick(w.list, Qt.Key_Delete); APP.processEvents()
    obs.append(dict(id="E3", what="Клавиша Delete в списке удаляет выбранного подписчика", value=f"записей после Delete: {w.list.count()}",
                    defect=w.list.count() == 1, note="клавиатурное удаление не реализовано (пожелание)"))
    return out, obs


def main():
    mode = sys.argv[1]
    if mode == "system":
        res = [f() for f in (s1, s2, s3, s4, s5, s6)]
        (OUT / "system_results.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        for r in res:
            print(r["id"], r["status"], sum(c["ok"] for c in r["checks"]), "/", len(r["checks"]))
    else:
        res, obs = m_checks()
        (OUT / "manual_results.json").write_text(json.dumps(dict(checks=res, observations=obs), ensure_ascii=False, indent=1), encoding="utf-8")
        for r in res:
            print(r["id"], r["status"], sum(c["ok"] for c in r["checks"]), "/", len(r["checks"]))
            for c in r["checks"]:
                if not c["ok"]:
                    print("   FAIL", c)
        for o in obs:
            print(o)


if __name__ == "__main__":
    main()
