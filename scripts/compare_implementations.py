#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Дифференциальное сравнение трёх реализаций IEmailValidator (ЛР №6).

Одни и те же входы подаются всем реализациям; расхождения в is_valid / extract_domain
(значение или тип исключения) выводятся списком. Запуск из корня:  PYTHONPATH=src python scripts/compare_implementations.py
"""
import importlib
import json
import random
import string
import sys

NAMES = [("Gen1_ChatGPT", "lab.implementations.gencode1"), ("Gen2_DeepSeek", "lab.implementations.gencode2"),
         ("Gen3_Claude", "lab.implementations.gencode3")]
EDGE = [None, "", " ", "a@b.co", "A@B.CO", "a@b.c", "a@b", "@b.co", "a@@b.co", "a@b..co", "a b@c.de", "a@b.co\n",
        "a@b-.co", "a@-b.co", "a@b.123", "a@b.c0", "ä@b.co", "a@b.cö", "a" * 64 + "@x.co", "a" * 65 + "@x.co",
        "a@" + "b" * 63 + ".co", "a@" + "b" * 64 + ".co", "a.@b.co", ".a@b.co", "a..b@c.co", "a+b@c.co", "a%b@c.co",
        "a_b@c.co", "a!b@c.co", "a@b_c.co", 123, b"a@b.co", ["a@b.co"], "a@b.co ", " a@b.co", "a@b.co.", "a@.b.co",
        "user@Sub.EXAMPLE.com", "x@y.zz\x00", "﻿a@b.co", "a@b.cа", "a@1.2.3.4", "a@[1.2.3.4]", '"a"@b.co']


def outcome(fn, value):
    try:
        return repr(fn(value))
    except Exception as exc:                     # noqa: BLE001 - нужна именно фиксация типа исключения
        return "EXC:" + type(exc).__name__


def main():
    impls = [(n, importlib.import_module(m).EmailValidator()) for n, m in NAMES]
    rnd = random.Random(1)
    alphabet = string.ascii_letters + string.digits + "._%+-@!# \n"
    corpus = list(EDGE) + ["".join(rnd.choice(alphabet) for _ in range(rnd.randint(0, 14))) for _ in range(20000)]
    diverged = []
    for value in corpus:
        row = [(outcome(v.is_valid, value), outcome(v.extract_domain, value)) for _, v in impls]
        if len(set(row)) > 1:
            diverged.append((repr(value), row))
    summary = dict(inputs=len(corpus), edge=len(EDGE), random=len(corpus) - len(EDGE), divergences=len(diverged))
    print(json.dumps(summary, ensure_ascii=False))
    for value, row in diverged[:20]:
        print("DIFF", value, row)
    if "--table" in sys.argv:
        for value in EDGE:
            print(repr(value)[:40].ljust(42), [outcome(v.is_valid, value) for _, v in impls],
                  [outcome(v.extract_domain, value)[:22] for _, v in impls])
    return 0


if __name__ == "__main__":
    sys.exit(main())
