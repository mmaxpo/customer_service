from pathlib import Path


JOBS_ROOT = Path("app/jobs")


def test_jobs_do_not_import_runtime_engine_internals():
    violations = []

    for path in sorted(JOBS_ROOT.rglob("*.py")):
        text = path.read_text(errors="ignore")

        for lineno, line in enumerate(
            text.splitlines(),
            1,
        ):
            stripped = line.strip()

            if stripped.startswith("from app.runtime.engine") or stripped.startswith(
                "import app.runtime.engine"
            ):
                violations.append(f"{path}:{lineno}: {stripped}")

    assert not violations, (
        "Jobs must depend on public Runtime "
        "boundaries instead of runtime.engine "
        "implementation modules:\n" + "\n".join(violations)
    )
