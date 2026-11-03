"""Generate Issue 65 review material from payload-free governance reports.

Historical matching uses unchanged Git lines, with exact message/code and
multiplicity. It proves occurrence provenance, not runtime correctness or risk.
The generated inventory cannot approve itself or authorize promotion.
"""

import argparse
import ast
import difflib
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

from gate_policy import diagnostic_key

ROOT = Path(__file__).resolve().parents[1]


def git_bytes(sha: str, file: str) -> bytes:
    if not re.fullmatch(r"[a-f0-9]{40}", sha) or (
        not file.startswith("src/") or ".." in file or "\\" in file or "\n" in file
    ):
        raise ValueError("INVALID_REVIEW_SOURCE_IDENTITY")
    return subprocess.check_output(["git", "show", sha + ":income-analytics/" + file], cwd=ROOT)


def inventory(before: dict, after: dict) -> list[dict]:
    available = Counter(map(diagnostic_key, before["findings"]))
    files = {}
    rows = []
    for finding in after["findings"]:
        file = finding["file"]
        if file not in files:
            old = git_bytes(before["checkout_sha"], file)
            new = git_bytes(after["checkout_sha"], file)
            old_lines, new_lines = old.decode().splitlines(), new.decode().splitlines()
            mapping = {
                j + k + 1: i + k + 1
                for i, j, size in difflib.SequenceMatcher(
                    a=old_lines, b=new_lines, autojunk=False
                ).get_matching_blocks()
                for k in range(size)
            }
            files[file] = (new, new_lines, mapping, ast.parse(new.decode()))
        source, lines, mapping, tree = files[file]
        previous = dict(finding, line=mapping.get(finding["line"]))
        identity = diagnostic_key(previous)
        historic = available[identity] > 0
        if historic:
            available[identity] -= 1
        symbols = [
            n
            for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            and n.lineno <= finding["line"] <= n.end_lineno
        ]
        symbol = min(symbols, key=lambda n: n.end_lineno - n.lineno).name if symbols else "module"
        frozen = file.endswith(
            (
                "/magic_formula_stocks.py",
                "/magic_formula_ranking_validation.py",
                "/magic_formula_contract.py",
            )
        )
        security = any(s in file for s in ("auth", "firebase", "identity"))
        annotation_only = finding["code"] in {"no-untyped-def", "type-arg"}
        rows.append(
            {
                "id": "MYPY-" + hashlib.sha256(diagnostic_key(finding).encode()).hexdigest()[:16],
                "finding": finding,
                "candidate_sha": after["checkout_sha"],
                "baseline_sha": before["checkout_sha"],
                "historical_finding": previous if historic else None,
                "origin": "PROVEN_PREEXISTING_UNCHANGED_LINE" if historic else "UNPROVEN_BLOCK",
                "source_sha256": hashlib.sha256(source).hexdigest(),
                "symbol": symbol,
                "source_line": lines[finding["line"] - 1].strip(),
                "root_cause": "MISSING_ANNOTATION"
                if annotation_only
                else "TYPE_CONTRACT_REVIEW_REQUIRED",
                "risk": "LOW_PROPOSED" if annotation_only and not security else "UNKNOWN",
                "financial_impact": "REQUIRES_INDIVIDUAL_REVIEW",
                "security_impact": "REQUIRES_INDIVIDUAL_REVIEW"
                if security
                else "NO_AUTH_PATH_IDENTIFIED",
                "frozen": frozen,
                "issue": "#64" if frozen else "#59",
                "dependencies": ["#57", "#64"] if frozen else ["#64"],
                "owner_proposed": "tiagocaldironi",
                "review_until_proposed": "2026-11-17",
                "acceptance": "PENDING",
                "treatment": "REVIEW_BEFORE_BASELINE_ACCEPTANCE",
                "effort": "S" if annotation_only else "M_REQUIRES_ANALYSIS",
            }
        )
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("baseline_mypy", "candidate_mypy", "baseline_python", "candidate_python"):
        parser.add_argument("--" + name.replace("_", "-"), required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    reports = {
        name: json.loads(getattr(args, name).read_text())
        for name in ("baseline_mypy", "candidate_mypy", "baseline_python", "candidate_python")
    }
    args.output.mkdir(parents=True, exist_ok=True)
    rows = inventory(reports["baseline_mypy"], reports["candidate_mypy"])
    old = {(x["class"], x["name"]): x["status"] for x in reports["baseline_python"]["cases"]}
    new = {(x["class"], x["name"]): x["status"] for x in reports["candidate_python"]["cases"]}
    tests = [
        {
            "id": "::".join(k),
            "baseline_status": old.get(k),
            "candidate_status": v,
            "preexisting": old.get(k) == v,
            "issue": "#58",
            "acceptance": "PENDING",
            "risk": "UNKNOWN",
            "owner_proposed": "tiagocaldironi",
        }
        for k, v in new.items()
        if v != "passed"
    ]
    summary = {
        "schema": 1,
        "mode": "PROPOSAL_ONLY",
        "baseline_accepted": False,
        "baseline_sha": reports["baseline_mypy"]["checkout_sha"],
        "candidate_sha": reports["candidate_mypy"]["checkout_sha"],
        "candidate_head": reports["candidate_mypy"]["pr_head_sha"],
        "hosted_run": reports["candidate_mypy"]["run_id"],
        "mypy_before": len(reports["baseline_mypy"]["findings"]),
        "mypy_after": len(rows),
        "mypy_unproved": sum(r["origin"] == "UNPROVEN_BLOCK" for r in rows),
        "frozen_diagnostics": sum(r["frozen"] for r in rows),
        "existing_test_changes": ["::".join(k) for k in old if old[k] != new.get(k)],
        "new_test_statuses": dict(Counter(new[k] for k in new.keys() - old.keys())),
        "baseline_totals": reports["baseline_python"]["totals"],
        "candidate_totals": reports["candidate_python"]["totals"],
        "baseline_test_worktree_dirty": reports["baseline_python"]["worktree_dirty"],
        "warning": "Unchanged lines prove preexistence only; enclosing behavior may change.",
    }
    for name, value in {
        **reports,
        "mypy_inventory": rows,
        "test_inventory": tests,
        "comparison": summary,
    }.items():
        (args.output / (name + ".json")).write_bytes(
            (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()
        )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
