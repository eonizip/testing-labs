#!/usr/bin/env python3
# generator/gen_tests.py
"""
Генератор параметризованных pytest-тестов на основе YAML-спецификации.

Читает формальное описание (spec/*.yaml), преобразует классы эквивалентности в параметризованные
тесты pytest со структурой Arrange-Act-Assert, строит отчёт трассировки требований и сохраняет
файлы в каталоги из config.yaml.

Генератор детерминирован: результат зависит только от содержимого спецификации и конфигурации
(нет дат, случайных значений и обхода словарей в произвольном порядке).

Зависимости: pyyaml (pip install pyyaml)

Примеры:
    python generator/gen_tests.py                       # сгенерировать тесты и отчёт
    python generator/gen_tests.py --verify-determinism  # проверить, что два запуска дают один результат
    python generator/gen_tests.py --check               # сравнить файл на диске с тем, что даст генератор
    python generator/gen_tests.py --strict              # завершиться с ошибкой, если есть непокрытые требования
"""
import argparse
import hashlib
import sys
from pathlib import Path
from string import Template
from typing import Any, Dict, List, Tuple

import yaml

GENERATOR_VERSION = "1.0"
KNOWN_INVARIANTS = {"repeatable", "no_instance_state", "stdlib_only"}


class SpecError(Exception):
    """Ошибка в спецификации (нарушена структура или ссылки на требования)."""


# ---------------------------------------------------------
# 1. ШАБЛОНЫ КОДА (string.Template: плейсхолдеры $name, фигурные скобки Python не нужно экранировать)
# ---------------------------------------------------------
FILE_TEMPLATE = Template('''# =============================================================
# AUTO-GENERATED TESTS. DO NOT EDIT MANUALLY.
# Source: $spec_source (sha256: $spec_hash)
# Generator: gen_tests.py v$version
# =============================================================
import pytest

from $module_import import $module_name


@pytest.fixture
def sut():
    """Тестируемая система (SUT): новый экземпляр для каждого теста."""
    return $module_name()
$test_functions''')

CLASS_TEST_TEMPLATE = Template('''

@pytest.mark.req($reqs)
@pytest.mark.parametrize($params, [
$param_rows
])
def $func_name(sut, $arg_names):
    """$ec_id: $case"""
    # === Arrange ===
    # Предусловие (pre): $pre
    # Ожидаемый результат (expected): $expected

    # === Act ===
$act_code

    # === Assert ===
    # Постусловие (post): $post
$assert_code
''')

REPEATABLE_TEMPLATE = Template('''

@pytest.mark.req($reqs)
@pytest.mark.parametrize("value", [
$param_rows
])
def $func_name(sut, value):
    """$inv_id: $desc"""
    other = $module_name()
    first = sut.$method(value)
    assert sut.$method(value) == first, "повторный вызов дал другой результат"
    assert other.$method(value) == first, "другой экземпляр дал другой результат"
''')

NO_STATE_TEMPLATE = Template('''

@pytest.mark.req($reqs)
def $func_name(sut):
    """$inv_id: $desc"""
    assert vars(sut) == {}, f"у экземпляра есть состояние: {vars(sut)}"
''')

STDLIB_TEMPLATE = Template('''

@pytest.mark.req($reqs)
def $func_name():
    """$inv_id: $desc"""
    import ast
    import importlib.util
    import sys

    origin = importlib.util.find_spec("$module_import").origin
    with open(origin, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            modules.add(node.module.split(".")[0])
    foreign = modules - set(sys.stdlib_module_names) - {"lab"}
    assert not foreign, f"внешние зависимости: {sorted(foreign)}"
''')


# ---------------------------------------------------------
# 2. ПАРСИНГ И ПРОВЕРКА СПЕЦИФИКАЦИИ
# ---------------------------------------------------------
def load_yaml(path: str) -> Dict[str, Any]:
    """Безопасная загрузка YAML."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def validate_spec(spec: Dict[str, Any]) -> None:
    """Проверяет структуру спецификации и ссылки на требования; при ошибке бросает SpecError."""
    fr = {r["id"] for r in spec.get("functional_requirements", [])}
    nfr = {r["id"] for r in spec.get("non_functional_requirements", [])}
    known = fr | nfr
    if len(known) != len(fr) + len(nfr):
        raise SpecError("идентификаторы требований не уникальны")
    seen = set()
    for method in spec["methods"]:
        for rid in method.get("req_functional", []) + method.get("req_non_functional", []):
            if rid not in known:
                raise SpecError(f"метод {method['name']}: неизвестное требование {rid}")
        for ec in method["equivalence_classes"]:
            if ec["id"] in seen:
                raise SpecError(f"повторяющийся идентификатор класса {ec['id']}")
            seen.add(ec["id"])
            for rid in ec.get("req", []):
                if rid not in known:
                    raise SpecError(f"{ec['id']}: неизвестное требование {rid}")
            if not ec.get("inputs"):
                raise SpecError(f"{ec['id']}: пустой список inputs")
            has_class_oracle = ("returns" in ec) != ("raises" in ec)
            for item in ec["inputs"]:
                if isinstance(item, dict) and "value" in item:
                    if "returns" not in item and not has_class_oracle:
                        raise SpecError(f"{ec['id']}: у входа {item['value']!r} нет оракула")
                elif not has_class_oracle:
                    raise SpecError(f"{ec['id']}: нужен ровно один из ключей returns/raises")
    for inv in spec.get("invariants", []):
        if inv["kind"] not in KNOWN_INVARIANTS:
            raise SpecError(f"{inv['id']}: неизвестный вид инварианта {inv['kind']}")
        for rid in inv.get("req_non_functional", []):
            if rid not in known:
                raise SpecError(f"{inv['id']}: неизвестное требование {rid}")


# ---------------------------------------------------------
# 3. ГЕНЕРАЦИЯ КОДА
# ---------------------------------------------------------
def render_part(part: Any) -> str:
    """Часть конструкции concat: строка или {unit, count}."""
    if isinstance(part, dict):
        return f"{part['unit']!r} * {part['count']}"
    return repr(part)


def render_value(value: Any) -> str:
    """Преобразует значение из YAML в литерал (выражение) Python."""
    if isinstance(value, dict):
        if "concat" in value:
            return "(" + " + ".join(render_part(p) for p in value["concat"]) + ")"
        if "bytes" in value:
            return repr(value["bytes"].encode("utf-8"))
        if "special" in value:
            return {"object": "object()", "list": "['a@b.co']"}[value["special"]]
        raise SpecError(f"неизвестная конструкция значения: {value}")
    return repr(value)          # None, bool, int, float, str


def one_line(text: Any) -> str:
    """Текст для комментариев и docstring: в одну строку."""
    return " ".join(str(text).split())


def func_name(prefix: str, ident: str) -> str:
    return f"test_{prefix}_{ident.lower().replace('-', '_')}"


def reqs_literal(ids: List[str]) -> str:
    return ", ".join(repr(i) for i in ids)


def generate_class_test(method: Dict[str, Any], ec: Dict[str, Any]) -> Tuple[str, int]:
    """Один параметризованный тест для класса эквивалентности. Возвращает (код, число случаев)."""
    raises = ec.get("raises")
    rows = []
    for n, item in enumerate(ec["inputs"], 1):
        if isinstance(item, dict) and "value" in item:
            value, expected = item["value"], item.get("returns", ec.get("returns"))
        else:
            value, expected = item, ec.get("returns")
        if raises:
            rows.append(f"    pytest.param({render_value(value)}, id=\"in{n:02d}\"),")
        else:
            rows.append(f"    pytest.param({render_value(value)}, {render_value(expected)}, id=\"in{n:02d}\"),")

    call = f"sut.{method['name']}(value)"
    if raises:
        act = f"    with pytest.raises({raises}):\n        {call}"
        assert_code = "    # Исключение проверено контекстным менеджером pytest.raises"
        params, args = '"value"', "value"
    else:
        # тестовый оракул: bool сравниваем строго (is), остальное - по равенству
        sample = ec["inputs"][0]
        sample_expected = sample.get("returns", ec.get("returns")) if isinstance(sample, dict) and "value" in sample else ec.get("returns")
        op = "is" if isinstance(sample_expected, bool) else "=="
        act = f"    result = {call}"
        assert_code = (f"    assert result {op} expected, (\n"
                       f"        f\"{method['name']}({{value!r}}) -> {{result!r}}, ожидалось {{expected!r}}\"\n"
                       f"    )")
        params, args = '("value", "expected")', "value, expected"

    reqs = ec.get("req") or (method.get("req_functional", []) + method.get("req_non_functional", []))
    code = CLASS_TEST_TEMPLATE.substitute(
        reqs=reqs_literal(reqs), params=params, param_rows="\n".join(rows),
        func_name=func_name(method["name"], ec["id"]), arg_names=args,
        ec_id=ec["id"], case=one_line(ec["case"]), pre=one_line(method["pre"]),
        expected=one_line(ec.get("expected", "")), act_code=act, post=one_line(method["post"]),
        assert_code=assert_code)
    return code, len(rows)


def generate_invariant_test(inv: Dict[str, Any], module_name: str, module_import: str) -> Tuple[str, int]:
    reqs = reqs_literal(inv.get("req_non_functional", []))
    name = f"test_{inv['id'].lower().replace('-', '_')}_{inv['kind']}"
    common = dict(reqs=reqs, func_name=name, inv_id=inv["id"], desc=one_line(inv["desc"]),
                  module_name=module_name, module_import=module_import)
    if inv["kind"] == "repeatable":
        rows = "\n".join(f"    pytest.param({render_value(v)}, id=\"in{n:02d}\")," for n, v in enumerate(inv["inputs"], 1))
        return REPEATABLE_TEMPLATE.substitute(param_rows=rows, method=inv["method"], **common), len(inv["inputs"])
    if inv["kind"] == "no_instance_state":
        return NO_STATE_TEMPLATE.substitute(**common), 1
    return STDLIB_TEMPLATE.substitute(**common), 1


def build_trace(spec: Dict[str, Any], tests: List[Tuple[str, str, str, int, List[str]]]) -> Tuple[str, List[str]]:
    """Матрица трассировки: требование -> YAML-блок -> сгенерированный тест.
    tests: (id блока, метод/вид, имя функции, число случаев, список требований)."""
    desc = {r["id"]: r["desc"] for r in spec["functional_requirements"] + spec["non_functional_requirements"]}
    lines = ["# Матрица трассировки требований", "",
             "Файл создан генератором gen_tests.py автоматически.", "",
             "| Требование | Описание | YAML-блок | Метод / вид | Сгенерированный тест | Случаев |",
             "|---|---|---|---|---|---|"]
    uncovered = []
    for rid in desc:
        rows = [t for t in tests if rid in t[4]]
        if not rows:
            uncovered.append(rid)
            lines.append(f"| {rid} | {desc[rid]} | **нет** | | | 0 |")
        for block, kind, fn, cnt, _ in rows:
            lines.append(f"| {rid} | {desc[rid]} | {block} | {kind} | `{fn}` | {cnt} |")
    lines += ["", f"Требований: {len(desc)}; не покрыто: {len(uncovered)}" + (f" ({', '.join(uncovered)})" if uncovered else ""), ""]
    return "\n".join(lines), uncovered


def build_all(spec: Dict[str, Any], config: Dict[str, Any], spec_bytes: bytes) -> Dict[str, Any]:
    """Строит содержимое файлов в памяти (чистая функция - основа детерминированности)."""
    validate_spec(spec)
    module_name = spec["module"]
    chunks, tests = [], []
    n_classes = n_cases = 0
    for method in spec["methods"]:
        for ec in method["equivalence_classes"]:
            code, cnt = generate_class_test(method, ec)
            chunks.append(code)
            n_classes += 1
            n_cases += cnt
            reqs = ec.get("req") or (method.get("req_functional", []) + method.get("req_non_functional", []))
            tests.append((ec["id"], method["name"], func_name(method["name"], ec["id"]), cnt, reqs))
    for inv in spec.get("invariants", []):
        code, cnt = generate_invariant_test(inv, module_name, config["module_import"])
        chunks.append(code)
        n_cases += cnt
        fn = f"test_{inv['id'].lower().replace('-', '_')}_{inv['kind']}"
        tests.append((inv["id"], inv["kind"], fn, cnt, inv.get("req_non_functional", [])))
    test_text = FILE_TEMPLATE.substitute(
        spec_source=config["spec_path"], spec_hash=hashlib.sha256(spec_bytes).hexdigest(),
        version=GENERATOR_VERSION, module_import=config["module_import"], module_name=module_name,
        test_functions="".join(chunks))
    trace_text, uncovered = build_trace(spec, tests)
    return {"tests": test_text, "trace": trace_text, "uncovered": uncovered, "classes": n_classes,
            "functions": len(tests), "cases": n_cases}


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------
# 4. ТОЧКА ВХОДА
# ---------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="Python pytest Test Generator from YAML Spec")
    parser.add_argument("--config", default="config.yaml", help="Путь к config.yaml")
    parser.add_argument("--check", action="store_true", help="Не записывать файлы: сравнить с существующими")
    parser.add_argument("--verify-determinism", action="store_true", help="Построить результат дважды и сравнить")
    parser.add_argument("--strict", action="store_true", help="Код возврата 3, если есть непокрытые требования")
    args = parser.parse_args()

    print("[*] Загрузка конфигурации...")
    config = load_yaml(args.config)
    print(f"[*] Загрузка спецификации: {config['spec_path']}...")
    spec_bytes = Path(config["spec_path"]).read_bytes()
    spec = yaml.safe_load(spec_bytes.decode("utf-8"))

    try:
        result = build_all(spec, config, spec_bytes)
    except SpecError as e:
        print(f"[x] Ошибка спецификации: {e}", file=sys.stderr)
        return 2

    out_file = Path(config["output_dir"]) / config["output_file"]
    trace_file = Path(config["traceability_report"])

    if args.verify_determinism:
        again = build_all(yaml.safe_load(spec_bytes.decode("utf-8")), config, spec_bytes)
        same = digest(result["tests"]) == digest(again["tests"]) and result["trace"] == again["trace"]
        print(f"[*] sha256 тестов, запуск 1: {digest(result['tests'])}")
        print(f"[*] sha256 тестов, запуск 2: {digest(again['tests'])}")
        print("[✓] Генерация детерминирована" if same else "[x] Результаты запусков различаются")
        return 0 if same else 1

    if args.check:
        current = out_file.read_text(encoding="utf-8") if out_file.exists() else None
        if current == result["tests"]:
            print(f"[✓] {out_file} актуален")
            return 0
        print(f"[x] {out_file} отличается от результата генератора")
        return 1

    out_file.parent.mkdir(parents=True, exist_ok=True)
    trace_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(result["tests"], encoding="utf-8", newline="\n")
    trace_file.write_text(result["trace"], encoding="utf-8", newline="\n")
    print(f"[✓] Сгенерирован файл: {out_file}")
    print(f"[✓] Матрица трассировки: {trace_file}")
    print(f"    Методов в спецификации: {len(spec['methods'])}")
    print(f"    Классов эквивалентности: {result['classes']}")
    print(f"    Тестовых функций: {result['functions']}, случаев (параметров): {result['cases']}")
    if result["uncovered"]:
        print(f"[!] Не покрыты требования: {', '.join(result['uncovered'])}")
        if args.strict:
            return 3
    print("[✓] Готово.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
