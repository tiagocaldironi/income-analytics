"""Dispatch CI checks while keeping governance's certified source stable."""

import json
from pathlib import Path

import governance

_ORIGINAL_RUN_CHECK = governance.run_check

def _quality_report(tool: str) -> tuple[int, list[dict]]:
    path = governance.ROOT / "ci-reports" / tool / "result.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    if (
        report.get("check") != tool
        or not isinstance(report.get("findings"), list)
        or type(report.get("exit_code")) is not int
    ):
        raise ValueError("QUALITY_DIAGNOSTIC_REPORT_INVALID")
    return report["exit_code"], report["findings"]


def dispatch(check: str, env: dict, sandbox: Path, output: Path):
    """Use reports from the same run and retain the existing governance evaluators."""
    if check == "magic_formula":
        return governance.python_check(check, env, sandbox, output)
    if check == "quality":
        original_quality_findings = governance.quality_findings
        governance.quality_findings = lambda tool, _env, _sandbox: _quality_report(tool)
        try:
            return _ORIGINAL_RUN_CHECK(check, env, sandbox, output)
        finally:
            governance.quality_findings = original_quality_findings

    original_execute = governance.legacy.execute
    observed = {}

    def capture_execute(args, *args_rest, **kwargs):
        for arg in args:
            if isinstance(arg, str) and arg.startswith("--junitxml="):
                observed["junit"] = Path(arg.split("=", 1)[1])
        return original_execute(args, *args_rest, **kwargs)

    governance.legacy.execute = capture_execute
    try:
        code, details = _ORIGINAL_RUN_CHECK(check, env, sandbox, output)
    finally:
        governance.legacy.execute = original_execute

    if check == "python":
        raw = observed.get("junit")
        inventory_path = output / "inventory.json"
        if raw is None or not raw.is_file() or not inventory_path.is_file():
            raise ValueError("FINANCIAL_PROJECTION_INPUT_MISSING")
        from financial_projection import write_projection

        entries = json.loads(inventory_path.read_text(encoding="utf-8"))
        write_projection(governance.ROOT, entries, details, raw, output)
    return code, details


def main() -> int:
    governance.run_check = dispatch
    return governance.main()


if __name__ == "__main__":
    raise SystemExit(main())
