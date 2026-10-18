#!/usr/bin/env python3
"""Локальный аналог compare.yml: для каждой ветки создаёт чистую копию (git worktree) и
виртуальное окружение, ставит зависимости, запускает pytest и собирает JUnit-отчёт,
после чего строит такую же сводную таблицу, как job «Unified report».

Запуск из корня репозитория:  python scripts/local_compare.py [ветка ...]
"""
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

BRANCHES = ["ai-version-1", "ai-version-2", "ai-version-3"]
ROOT = Path(__file__).resolve().parent.parent


def run(cmd, cwd, **kw):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, **kw)


def main(branches):
    out_dir = ROOT / "artifacts"
    timings = {}
    with tempfile.TemporaryDirectory() as tmp:
        for br in branches:
            work = Path(tmp) / br
            t0 = time.perf_counter()
            run(["git", "worktree", "add", "--detach", str(work), br], ROOT)          # checkout ref: <branch>
            venv = work / ".venv"
            run([sys.executable, "-m", "venv", str(venv)], work)                       # чистое окружение
            py = str(venv / "bin" / "python")
            run([py, "-m", "pip", "install", "-q", "-r", "requirements.txt"], work)    # Install dependencies
            if (work / "generator" / "gen_tests.py").exists():                          # Generate pytest tests
                run([py, "generator/gen_tests.py", "--config", "config.yaml", "--strict"], work)
            t1 = time.perf_counter()
            art = out_dir / f"junit-{br}"
            art.mkdir(parents=True, exist_ok=True)
            res = run([py, "-m", "pytest", "--verbose", f"--junitxml={art / 'test-results.xml'}"], work)  # Test
            t2 = time.perf_counter()
            (art / "pytest.log").write_text(res.stdout + res.stderr, encoding="utf-8")
            timings[br] = {"setup_s": round(t1 - t0, 2), "tests_s": round(t2 - t1, 2),
                           "job_s": round(t2 - t0, 2), "exit_code": res.returncode}
            run(["git", "worktree", "remove", "--force", str(work)], ROOT)
    (out_dir / "timings.json").write_text(json.dumps(timings, indent=2), encoding="utf-8")
    subprocess.run([sys.executable, str(ROOT / "scripts" / "summarize_junit.py"), str(out_dir)])
    print("\nВремя заданий:", json.dumps(timings, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1:] or BRANCHES)
