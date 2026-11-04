"""Compare reviewed historical findings at unchanged syntax blocks, never new debt."""

import ast
import hashlib
import json
from copy import deepcopy

from gate_policy import diagnostic_key
from release_inventory import git_bytes

POLICY = "ci/diagnostic-relocations-79.json"


def blocks(source):
    lines = source.decode().splitlines()
    result = {}

    def visit(node, scope):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = scope + "." + child.name
                if name in result:
                    raise ValueError("AMBIGUOUS_RELOCATION_SYMBOL")
                result[name] = (child.lineno, child.end_lineno,
                                lines[child.lineno - 1:child.end_lineno])
                visit(child, name)
            elif isinstance(node, ast.Module) and isinstance(child, ast.stmt):
                name = "statement:" + hashlib.sha256(ast.dump(child).encode()).hexdigest()
                result[name] = (child.lineno, child.end_lineno,
                                lines[child.lineno - 1:child.end_lineno])

    visit(ast.parse(source.decode()), "module")
    return result


def reviewed_relocations(root, actual, ledger):
    """Keep both original baselines immutable; return a separately audited comparison.

    Only exact unchanged blocks in pinned base/candidate source can relocate a
    finding already present in the owner-accepted inventory. New rules, messages,
    columns, code, multiplicity and altered blocks still fail the existing gates.
    """
    policy = json.loads((root / POLICY).read_bytes())
    known = {diagnostic_key(row) for row in json.loads((root / (
        "docs/engineering/release-policy-65/candidate_mypy.json"
    )).read_bytes())["findings"]}
    reviewed = deepcopy(ledger)
    sources = {}
    for file, review in policy["files"].items():
        before = git_bytes(policy["base_commit"], file)
        after = (root / file).read_bytes()
        if (hashlib.sha256(before).hexdigest() != review["before_sha256"]
                or hashlib.sha256(after).hexdigest() != review["after_sha256"]):
            raise ValueError("DIAGNOSTIC_RELOCATION_SOURCE_REVIEW_REQUIRED")
        prior = reviewed["reviewed_source_sha256"].get(file)
        if prior is not None:
            if prior != review["before_sha256"]:
                raise ValueError("DIAGNOSTIC_RELOCATION_LEDGER_BASE_MISMATCH")
            reviewed["reviewed_source_sha256"][file] = review["after_sha256"]
        old, new = blocks(before), blocks(after)
        sources[file] = sorted([
            (start, end, old[name][0])
            for name, (start, end, text) in new.items()
            if name in old and text == old[name][2]
        ], key=lambda row: row[1] - row[0])
    canonical, relocated = [], []
    for row in actual:
        mapped = dict(row)
        if row["tool"] == "mypy":
            for start, end, old_start in sources.get(row["file"], []):
                if start <= row["line"] <= end:
                    candidate = dict(row, line=old_start + row["line"] - start)
                    if diagnostic_key(candidate) in known:
                        mapped = candidate
                    break
        canonical.append(mapped)
        if mapped != row:
            relocated.append({"observed": row, "accepted": mapped})
    return canonical, reviewed, {
        "policy": POLICY, "base_commit": policy["base_commit"],
        "relocations": relocated, "raw_diagnostics": actual,
        "baseline_modified": False,
    }
