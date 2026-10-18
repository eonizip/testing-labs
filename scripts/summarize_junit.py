#!/usr/bin/env python3
"""Сводный отчёт по JUnit XML-файлам: python scripts/summarize_junit.py <каталог с артефактами>.

Ожидает структуру <каталог>/junit-<ветка>/test-results.xml (так их скачивает download-artifact).
Печатает таблицу в формате Markdown (для $GITHUB_STEP_SUMMARY) и тексты ошибок упавших тестов.
"""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def read_suite(xml_path: Path) -> dict:
    root = ET.parse(xml_path).getroot()
    suite = root if root.tag == "testsuite" else root.find("testsuite")
    tests = int(suite.get("tests", 0))
    failures = int(suite.get("failures", 0))
    errors = int(suite.get("errors", 0))
    skipped = int(suite.get("skipped", 0))
    problems = []
    for case in suite.iter("testcase"):
        for kind in ("failure", "error"):
            node = case.find(kind)
            if node is not None:
                first_line = (node.get("message") or "").strip().splitlines()
                problems.append((f"{case.get('classname')}::{case.get('name')}",
                                 first_line[0] if first_line else kind))
    return {
        "tests": tests, "failures": failures, "errors": errors, "skipped": skipped,
        "passed": tests - failures - errors - skipped,
        "time": float(suite.get("time", 0)), "problems": problems,
    }


def main(artifacts_dir: str) -> int:
    root = Path(artifacts_dir)
    rows = {}
    for xml_path in sorted(root.glob("junit-*/test-results.xml")):
        rows[xml_path.parent.name.removeprefix("junit-")] = read_suite(xml_path)
    if not rows:
        print("Нет отчётов JUnit в", root)
        return 1
    print("## Сравнение версий модуля\n")
    print("| Версия | Сборка/тесты | Всего | Passed | Failed | Errors | Skipped | Время тестов, с |")
    print("|---|---|---|---|---|---|---|---|")
    for name, r in rows.items():
        ok = r["failures"] == 0 and r["errors"] == 0
        print(f"| {name} | {'✅ успешно' if ok else '❌ есть ошибки'} | {r['tests']} | {r['passed']} | "
              f"{r['failures']} | {r['errors']} | {r['skipped']} | {r['time']:.2f} |")
    for name, r in rows.items():
        if r["problems"]:
            print(f"\n### Ошибки: {name}\n")
            for test, msg in r["problems"]:
                print(f"* `{test}` — {msg}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "artifacts"))
