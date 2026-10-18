"""Тесты «ЧЁРНОГО ЯЩИКА»: по спецификации, написаны ДО получения кода."""
import pytest

from lab.interfaces import IEmailValidator


def dom(*lengths):
    return ".".join("a" * n for n in lengths)


def test_bb_01_instance_created(validator):
    assert isinstance(validator, IEmailValidator)


@pytest.mark.parametrize("email", [
    "user@example.com",
    "first.last@sub.example.co.uk",
    "user+tag@example.com",
    "a@b.co",
    "USER@EXAMPLE.COM",
    "u_s%e+r-1@example.org",
])
def test_bb_02_valid_emails_accepted(validator, email):
    assert validator.is_valid(email) is True


@pytest.mark.parametrize("email", [
    "", "userexample.com", "@example.com", "user@", "user@@example.com",
    "user@example", "user@example.c", "user@example.123", "user@192.168.0.1",
    ".user@example.com", "user.@example.com", "us..er@example.com",
    "user@.example.com", "user@example..com", "user@example.com.",
    "user@-example.com", "user@example-.com", "user@exam_ple.com",
])
def test_bb_03_invalid_emails_rejected(validator, email):
    assert validator.is_valid(email) is False


@pytest.mark.parametrize("email, expected", [
    ("a" * 64 + "@example.com", True),
    ("a" * 65 + "@example.com", False),
], ids=["local64", "local65"])
def test_bb_04_local_part_length(validator, email, expected):
    assert validator.is_valid(email) is expected


@pytest.mark.parametrize("email, expected", [
    ("a@" + "b" * 63 + ".com", True),
    ("a@" + "b" * 64 + ".com", False),
], ids=["label63", "label64"])
def test_bb_05_label_length(validator, email, expected):
    assert validator.is_valid(email) is expected


@pytest.mark.parametrize("email, expected", [
    ("a" * 64 + "@" + dom(63, 63, 61), True),
    ("a" * 64 + "@" + dom(63, 63, 62), False),
], ids=["total254", "total255"])
def test_bb_06_total_length(validator, email, expected):
    assert validator.is_valid(email) is expected


@pytest.mark.parametrize("email", [
    " user@example.com", "user@example.com ", "us er@example.com",
    "user@example.com\n", "user\n@example.com", "user@example.com\t",
    "юзер@example.com", "user@example.рф", "user@пример.com", "üser@example.com",
])
def test_bb_07_spaces_control_and_non_ascii_rejected(validator, email):
    assert validator.is_valid(email) is False


@pytest.mark.parametrize("bad", [None, 123, b"a@b.co", object()])
def test_bb_08_non_string_input_does_not_raise(validator, bad):
    assert validator.is_valid(bad) is False


@pytest.mark.parametrize("email, expected", [
    ("user@example.com", "example.com"),
    ("user@Sub.Example.COM", "sub.example.com"),
    ("USER@EXAMPLE.ORG", "example.org"),
])
def test_bb_09_extract_domain_lowercase(validator, email, expected):
    assert validator.extract_domain(email) == expected


@pytest.mark.parametrize("bad", [None, "", "not-an-email", "user@example", 123])
def test_bb_10_extract_domain_invalid_raises_value_error(validator, bad):
    with pytest.raises(ValueError):
        validator.extract_domain(bad)

