"""Capture collected test node IDs and the final V12.2 JUnit execution summary."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree


def main() -> int:
    root = Path.cwd()
    collected = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"],
        check=False,
        capture_output=True,
        text=True,
    )
    if collected.returncode:
        sys.stderr.write(collected.stdout + collected.stderr)
        return collected.returncode
    node_ids = sorted(
        {
            line.strip().replace("\\", "/")
            for line in collected.stdout.splitlines()
            if "::" in line and line.strip().startswith("tests")
        }
    )
    suites = ElementTree.parse(
        root / "docs/appendices/magic_formula_v12_2/full_suite.xml"
    ).getroot()
    junit = suites.find("testsuite")
    if junit is None:
        raise ValueError("JUNIT_TESTSUITE_MISSING")
    counts = {
        "collected_count": len(node_ids),
        "executed_count": int(junit.attrib["tests"]),
        "passed": int(junit.attrib["tests"])
        - int(junit.attrib.get("failures", 0))
        - int(junit.attrib.get("errors", 0))
        - int(junit.attrib.get("skipped", 0)),
        "failed": int(junit.attrib.get("failures", 0)),
        "errors": int(junit.attrib.get("errors", 0)),
        "skipped": int(junit.attrib.get("skipped", 0)),
    }
    if counts["collected_count"] != counts["executed_count"]:
        raise ValueError("COLLECTED_AND_EXECUTED_TEST_INVENTORIES_DIFFER")
    manifest_hash = hashlib.sha256("\n".join(node_ids).encode("utf-8")).hexdigest()
    manifest = {
        "schema_version": "1.0",
        "test_baseline_version": "MF_BR_2027_V1_V12_2",
        "generated_at": datetime.now(UTC).isoformat(),
        "python_version": sys.version.split()[0],
        "pytest_version": __import__("pytest").__version__,
        **counts,
        "node_ids_sha256": manifest_hash,
        "node_ids": node_ids,
        "junit_artifact": "full_suite.xml",
    }
    target = root / "docs/appendices/magic_formula_v12_2/test_manifest.json"
    target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                key: manifest[key]
                for key in (
                    "collected_count",
                    "executed_count",
                    "passed",
                    "failed",
                    "errors",
                    "skipped",
                    "node_ids_sha256",
                )
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
