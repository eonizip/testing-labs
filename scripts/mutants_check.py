#!/usr/bin/env python3
"""Мутационная проверка набора тестов: в реализацию (src/lab/email_validator.py текущей ветки,
рассчитан на ai-version-3) вносятся небольшие ошибки; тест-набор «убивает» мутанта, если хотя бы
один тест падает.

Запуск из корня:  python scripts/mutants_check.py
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "lab" / "email_validator.py"

# (id, описание, что заменить, на что)
MUTANTS = [
    ("M1", "локальная часть до 65 символов вместо 64", "1 <= len(s) <= 64", "1 <= len(s) <= 65"),
    ("M2", "метка домена до 64 символов вместо 63", "1 <= len(label) <= 63", "1 <= len(label) <= 64"),
    ("M3", "общая длина до 255 вместо 254", "len(email) > 254", "len(email) > 255"),
    ("M4", "TLD от 1 символа вместо 2", "len(tld) >= 2", "len(tld) >= 1"),
    ("M5", "домен возвращается без приведения к нижнему регистру", '.split("@")[1].lower()', '.split("@")[1]'),
    ("M6", "не проверяется точка в начале локальной части", 's[0] == "." or ', ""),
    ("M7", "не проверяются две точки подряд", ' or ".." in s', ""),
    ("M8", "допускается домен из одной метки", "len(labels) < 2", "len(labels) < 1"),
    ("M9", "не проверяется дефис в начале метки", 'label[0] == "-" or ', ""),
    ("M10", "TLD может содержать цифры", "all(c in _LETTERS for c in tld)", "all(c in _LABEL_OK for c in tld)"),
    ("M11", "не проверяется тип входа (не строка)", "not isinstance(email, str) or ", ""),
    ("M12", "разрешён любой символ @ в количестве от одного", 'email.count("@") != 1', 'email.count("@") < 1'),
    ("M13", "extract_domain не бросает исключение", 'raise ValueError("Некорректный email")', 'return ""'),
    ("M14", "в локальной части запрещён символ +", '"._%+-"', '"._%-"'),
    ("M15", "в метках домена запрещён дефис", '{"-"}', "set()"),
]

SUITES = {
    "рукописные": ["tests/module_tests/test_black_box.py"],
    "сгенерированные": ["tests/module_tests/test_generated_email_validator.py"],
}


def run_suite(src_dir: Path, files) -> int:
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
                        "-o", f"pythonpath={src_dir}", *files], cwd=ROOT, capture_output=True, text=True)
    return r.returncode


def main():
    original = SRC.read_text(encoding="utf-8")
    killed = {name: 0 for name in SUITES}
    print("| № | Мутация | " + " | ".join(SUITES) + " |")
    print("|---|---|" + "---|" * len(SUITES))
    with tempfile.TemporaryDirectory() as tmp:
        for mid, desc, old, new in MUTANTS:
            if old not in original:
                print(f"| {mid} | {desc} | шаблон не найден | |")
                continue
            src_dir = Path(tmp) / mid
            shutil.copytree(ROOT / "src", src_dir)
            (src_dir / "lab" / "email_validator.py").write_text(original.replace(old, new, 1), encoding="utf-8")
            cells = []
            for name, files in SUITES.items():
                dead = run_suite(src_dir, files) != 0
                killed[name] += dead
                cells.append("убит" if dead else "ВЫЖИЛ")
            print(f"| {mid} | {desc} | " + " | ".join(cells) + " |")
    total = len(MUTANTS)
    print(f"\nУбито мутантов: " + ", ".join(f"{n} — {k} из {total}" for n, k in killed.items()))


if __name__ == "__main__":
    main()
