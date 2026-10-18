#!/usr/bin/env python3
"""Простые метрики кода реализации в каждой ветке: python scripts/code_metrics.py [ветка ...]
Строки (всего/кода), число функций, цикломатическая сложность (по числу ветвлений) и импорты."""
import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRANCHES = ["ai-version-1", "ai-version-2", "ai-version-3"]
FILE = "src/lab/email_validator.py"


def complexity(fn: ast.AST) -> int:
    c = 1
    for n in ast.walk(fn):
        if isinstance(n, (ast.If, ast.For, ast.While, ast.IfExp, ast.ExceptHandler, ast.comprehension)):
            c += 1 + (len(n.ifs) if isinstance(n, ast.comprehension) else 0)
        elif isinstance(n, ast.BoolOp):
            c += len(n.values) - 1
    return c


def metrics(src: str) -> dict:
    tree = ast.parse(src)
    funcs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    lines = src.splitlines()
    code = [l for l in lines if l.strip() and not l.strip().startswith("#")]
    imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
    return {"lines": len(lines), "code_lines": len(code), "functions": len(funcs),
            "max_cc": max((complexity(f) for f in funcs), default=0),
            "sum_cc": sum(complexity(f) for f in funcs), "imports": len(imports)}


if __name__ == "__main__":
    print("| Ветка | Строк | Строк кода | Функций | Макс. сложность | Сумма сложностей | Импортов |")
    print("|---|---|---|---|---|---|---|")
    for br in (sys.argv[1:] or BRANCHES):
        src = subprocess.run(["git", "show", f"{br}:{FILE}"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
        m = metrics(src)
        print(f"| {br} | {m['lines']} | {m['code_lines']} | {m['functions']} | {m['max_cc']} | {m['sum_cc']} | {m['imports']} |")
