# -*- coding: utf-8 -*-
"""Интеграционные тесты связки SubscriberService + IEmailValidator (ЛР №6).

Проверяется не внутренняя логика валидатора (это сделано модульными тестами ПР №1), а то, как
сервис использует контракт интерфейса: передача данных через границу компонентов, обработка
исключений, согласованность состояния, поведение на границах. Каждый тест выполняется для всех
реализаций (параметризация в conftest.py). У каждого теста указано: что проверяется, входные
данные, ожидаемый результат.
"""
import pytest

from lab.subscriber_service import InvalidEmailError, SubscriberLimitError, SubscriberService

VALID = ["user@example.com", "first.last@sub.example.co.uk", "a@b.co", "u_s%e+r-1@example.org",
         "USER@EXAMPLE.COM", "user@my-site.com", "a@1.2.co"]
INVALID = ["", " ", "user.example.com", "a@@b.com", "@example.com", ".user@example.com",
           "user.@example.com", "us..er@example.com", "user@example", "user@-example.com",
           "user@example.c", "user@example.123", "us er@example.com", "юзер@example.com",
           "user@пример.рф", "user@example.com\n", "user@"]
NOT_STR = [None, 123, 1.5, True, b"a@b.co", ["a@b.co"], object()]
def _id(v):
    return v if isinstance(v, str) else type(v).__name__


CORPUS = VALID + INVALID + [x for x in NOT_STR if not isinstance(x, (bool, float))]


# ================= 1. Контрактное соответствие при валидных данных =================
@pytest.mark.parametrize("email", VALID)
def test_valid_address_is_subscribed(service, email):
    """Проверяет: корректный адрес проходит валидатор и попадает в список.
    Вход: адрес из набора VALID. Ожидание: subscribe -> True, count == 1, адрес в списке."""
    assert service.subscribe(email) is True
    assert service.count == 1
    assert len(service.subscribers()) == 1


def test_domain_is_lowercased_via_extract_domain(service):
    """Проверяет: сервис получает от валидатора домен в нижнем регистре (FR-6).
    Вход: 'User@Sub.Example.COM'. Ожидание: ключ 'User@sub.example.com', статистика по 'sub.example.com'."""
    service.subscribe("User@Sub.Example.COM")
    assert service.subscribers() == ["User@sub.example.com"]
    assert service.domain_stats() == {"sub.example.com": 1}


def test_domain_case_does_not_create_duplicates(service):
    """Проверяет: адреса, различающиеся регистром домена, — один подписчик.
    Вход: 'a@Example.com', затем 'a@EXAMPLE.COM'. Ожидание: True, затем False; count == 1."""
    assert service.subscribe("a@Example.com") is True
    assert service.subscribe("a@EXAMPLE.COM") is False
    assert service.count == 1


# ============ 2. Контрактное соответствие при невалидных данных ============
@pytest.mark.parametrize("email", INVALID + NOT_STR, ids=_id)
def test_invalid_input_raises_uniform_error_and_keeps_state(service, email):
    """Проверяет: все реализации одинаково отклоняют невалидный вход, сервис выбрасывает
    InvalidEmailError (подкласс ValueError), а не TypeError/AttributeError, состояние не меняется.
    Вход: адрес из INVALID или значение не-строкового типа. Ожидание: InvalidEmailError, count == 0."""
    with pytest.raises(InvalidEmailError):
        service.subscribe(email)
    assert service.count == 0


@pytest.mark.parametrize("email", CORPUS, ids=_id)
def test_validator_contract_is_consistent(validator, email):
    """Проверяет: контракт интерфейса — is_valid не бросает исключений; extract_domain
    возвращает домен ровно тогда, когда is_valid == True, иначе бросает ValueError (FR-6, FR-7, NFR-1).
    Вход: общий корпус адресов. Ожидание: согласованность двух методов."""
    ok = validator.is_valid(email)
    assert isinstance(ok, bool)
    if ok:
        domain = validator.extract_domain(email)
        assert domain == email.split("@")[1].lower()
    else:
        with pytest.raises(ValueError):
            validator.extract_domain(email)


def test_unsubscribe_of_invalid_address_returns_false(service):
    """Проверяет: удаление некорректного адреса не приводит к исключению на стыке компонентов.
    Вход: пустой список, затем 'not-an-email' и None. Ожидание: False, False; count == 0."""
    assert service.unsubscribe("not-an-email") is False
    assert service.unsubscribe(None) is False
    assert service.count == 0


# ================= 3. Состояние и побочные эффекты =================
def test_report_reflects_added_subscribers(service):
    """Проверяет: добавление немедленно отражается в отчёте.
    Вход: 3 адреса на 2 доменах. Ожидание: 'Отчёт: всего 3, доменов 2 (example.com — 2; mail.org — 1).'"""
    for e in ("a@example.com", "b@Example.com", "c@mail.org"):
        service.subscribe(e)
    assert service.report() == "Отчёт: всего 3, доменов 2 (example.com — 2; mail.org — 1)."


def test_removed_subscriber_not_reflected(service):
    """Проверяет: после удаления подписчик исчезает из списка и отчёта.
    Вход: add 'a@b.co', add 'c@d.org', remove 'a@b.co'. Ожидание: остаётся только 'c@d.org'."""
    service.subscribe("a@b.co")
    service.subscribe("c@d.org")
    assert service.unsubscribe("a@b.co") is True
    assert service.subscribers() == ["c@d.org"]
    assert service.report() == "Отчёт: всего 1, доменов 1 (d.org — 1)."


def test_unsubscribe_missing_returns_false_and_keeps_state(service):
    """Проверяет: удаление отсутствующего корректного адреса не меняет состояние.
    Вход: список с 'a@b.co', remove 'z@z.zz'. Ожидание: False, count == 1."""
    service.subscribe("a@b.co")
    assert service.unsubscribe("z@z.zz") is False
    assert service.count == 1


def test_order_of_subscribers_is_insertion_order(service):
    """Проверяет: порядок подписчиков сохраняется. Вход: c@x.org, a@x.org, b@x.org.
    Ожидание: список в том же порядке."""
    emails = ["c@x.org", "a@x.org", "b@x.org"]
    for e in emails:
        service.subscribe(e)
    assert service.subscribers() == emails


def test_state_stays_consistent_over_operation_sequence(service):
    """Проверяет: после серии операций count == len(subscribers) == сумма статистики по доменам.
    Вход: 12 добавлений (4 повтора), 3 удаления. Ожидание: инвариант выполняется на каждом шаге."""
    ops = [("+", f"u{i % 8}@d{i % 3}.com") for i in range(12)] + [("-", "u0@d0.com"), ("-", "u1@d1.com"), ("-", "none@x.co")]
    for op, e in ops:
        service.subscribe(e) if op == "+" else service.unsubscribe(e)
        assert service.count == len(service.subscribers()) == sum(service.domain_stats().values())


def test_domain_stats_sorted_by_count_then_name(service):
    """Проверяет: статистика по доменам отсортирована по убыванию числа, затем по имени.
    Вход: b.com x1, a.com x1, c.com x2. Ожидание: порядок c.com, a.com, b.com."""
    for e in ("x@b.com", "x@a.com", "x@c.com", "y@c.com"):
        service.subscribe(e)
    assert list(service.domain_stats()) == ["c.com", "a.com", "b.com"]


# ================= 4. Граничные условия интеграции =================
def test_empty_service_report(service):
    """Проверяет: пустой набор данных. Вход: новый сервис. Ожидание: 'Список подписчиков пуст.'"""
    assert service.report() == "Список подписчиков пуст."
    assert service.subscribers() == [] and service.domain_stats() == {}


def test_single_subscriber_report(service):
    """Проверяет: одиночный элемент. Вход: 'a@b.co'. Ожидание: 'Отчёт: всего 1, доменов 1 (b.co — 1).'"""
    service.subscribe("a@b.co")
    assert service.report() == "Отчёт: всего 1, доменов 1 (b.co — 1)."


def test_limit_reached_rejects_new_but_keeps_state(make_service):
    """Проверяет: при заполнении списка новый адрес отклоняется, состояние не портится.
    Вход: ёмкость 3, 4 разных адреса. Ожидание: SubscriberLimitError на четвёртом, count == 3."""
    svc = make_service(capacity=3)
    for i in range(3):
        svc.subscribe(f"u{i}@x.org")
    with pytest.raises(SubscriberLimitError):
        svc.subscribe("u3@x.org")
    assert svc.count == 3 and "u3@x.org" not in svc.subscribers()


def test_duplicate_at_full_capacity_is_not_an_error(make_service):
    """Проверяет: повтор уже имеющегося адреса при полном списке — False, а не ошибка.
    Вход: ёмкость 2, два адреса, повтор первого. Ожидание: False."""
    svc = make_service(capacity=2)
    svc.subscribe("a@x.org"); svc.subscribe("b@x.org")
    assert svc.subscribe("a@X.org") is False


def test_slot_is_released_after_unsubscribe(make_service):
    """Проверяет: после удаления место освобождается. Вход: ёмкость 1: add, remove, add другого.
    Ожидание: второе добавление успешно."""
    svc = make_service(capacity=1)
    svc.subscribe("a@x.org"); svc.unsubscribe("a@x.org")
    assert svc.subscribe("b@x.org") is True


@pytest.mark.parametrize("local_len,label_lens,ok", [
    (64, [63, 63, 61], True),     # суммарно 254 символа
    (64, [63, 63, 62], False),    # 255 символов
    (65, [3, 2], False),          # локальная часть 65
])
def test_length_boundaries_at_service_level(service, local_len, label_lens, ok):
    """Проверяет: границы длины на стыке (локальная часть 64/65, общая длина 254/255).
    Вход: адреса на границах. Ожидание: принят / InvalidEmailError одинаково для всех реализаций."""
    domain = ".".join("d" * n for n in label_lens)
    email = "a" * local_len + "@" + domain
    if ok:
        assert service.subscribe(email) is True
    else:
        with pytest.raises(InvalidEmailError):
            service.subscribe(email)


def test_many_subscribers_sequence(make_service):
    """Проверяет: последовательные операции на 100 элементах. Вход: 100 уникальных адресов, затем
    удаление чётных. Ожидание: count == 50, отчёт совпадает с состоянием."""
    svc = make_service(capacity=100)
    for i in range(100):
        assert svc.subscribe(f"user{i}@site{i % 5}.org") is True
    for i in range(0, 100, 2):
        assert svc.unsubscribe(f"user{i}@site{i % 5}.org") is True
    assert svc.count == 50
    assert svc.report().startswith("Отчёт: всего 50, доменов 5")


# ================= 5. Изоляция тестовых окружений =================
def test_services_do_not_share_state(validator_cls):
    """Проверяет: два сервиса с разными экземплярами валидатора независимы.
    Вход: add в первый сервис. Ожидание: второй пуст."""
    s1 = SubscriberService(validator_cls()); s2 = SubscriberService(validator_cls())
    s1.subscribe("a@b.co")
    assert s2.count == 0 and s2.report() == "Список подписчиков пуст."


def test_validator_has_no_instance_state(validator):
    """Проверяет: у валидатора нет собственного состояния (NFR-2), значит, одно разделяемое
    экземпляр безопасен. Ожидание: пустой __dict__."""
    assert vars(validator) == {}


def test_isolation_part_one_modifies_state(service):
    """Проверяет изоляцию (часть 1/2): тест меняет состояние своего сервиса."""
    service.subscribe("order@check.org")
    assert service.count == 1


def test_isolation_part_two_sees_clean_state(service):
    """Проверяет изоляцию (часть 2/2): независимо от порядка запуска, сервис чист."""
    assert service.count == 0


def test_shared_validator_instance_between_services(validator):
    """Проверяет: общий экземпляр валидатора не создаёт связи между сервисами (без состояния).
    Вход: два сервиса с одним валидатором. Ожидание: независимые списки."""
    s1 = SubscriberService(validator); s2 = SubscriberService(validator)
    s1.subscribe("a@b.co")
    assert s2.subscribers() == []


def test_capacity_validation():
    """Проверяет: некорректная ёмкость отклоняется конструктором. Вход: 0. Ожидание: ValueError."""
    from lab.implementations.gencode3 import EmailValidator
    with pytest.raises(ValueError):
        SubscriberService(EmailValidator(), capacity=0)
