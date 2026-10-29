"""Payload-free security evidence. Scanner errors fail closed; no production access."""

import argparse
import base64
import hashlib
import importlib.metadata
import io
import json
import re
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "docs/engineering/security/security_scanner_triage.json"
PATTERNS = {
    "PRIVATE_KEY": rb"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----",
    "GITHUB_TOKEN": rb"(?:gh[pousr]_[A-Za-z0-9]{36,255}|github_pat_[A-Za-z0-9_]{60,255})",
    "AWS_ACCESS_KEY": rb"AKIA[0-9A-Z]{16}",
    "SERVICE_ACCOUNT_KEY": rb'"private_key"\s*:\s*"-----BEGIN',
    "CREDENTIAL_URL": rb"https?://[^\s/:@]{2,100}:[^\s/@]{4,200}@",
    "ASSIGNED_SECRET": (
        rb"(?i)(?:BRAPI_TOKEN|TWELVE_DATA_API_KEY|GITHUB_TOKEN|CLIENT_SECRET|SECRET_KEY)"
        rb"\s*[=:]\s*[\x22\x27]?([A-Za-z0-9_\-]{24,})"
    ),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def secrets_in(data, location):
    findings = []
    for kind, expression in PATTERNS.items():
        for match in re.finditer(expression, data):
            findings.append(
                {
                    "type": kind,
                    "location": location,
                    "line": data[: match.start()].count(b"\n") + 1,
                    "fingerprint": sha(match.group()),
                    "content_sha256": sha(data),
                    "state": "POTENTIAL",
                }
            )
    return findings


def tracked_files():
    return (
        subprocess.check_output(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=ROOT
        )
        .decode("utf-8")
        .rstrip("\0")
        .split("\0")
    )


def forbidden_source_files(paths):
    sensitive = {".db", ".sqlite", ".sqlite3", ".pem", ".key", ".p12", ".pfx"}
    return sorted(
        name
        for name in paths
        if Path(name).suffix.lower() in sensitive or Path(name).name == ".env"
    )


def artifact_secrets(path):
    findings = []
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            data = archive.read(name)
            if name.endswith(".whl"):
                with zipfile.ZipFile(io.BytesIO(data)) as wheel:
                    if sum(item.file_size for item in wheel.infolist()) > 256 * 1024 * 1024:
                        raise ValueError("WHEEL_SCAN_LIMIT")
                    for entry in wheel.infolist():
                        if Path(entry.filename).suffix in {".py", ".json", ".txt", ".pem", ".key"}:
                            findings += secrets_in(
                                wheel.read(entry), "artifact:" + name + "!" + entry.filename
                            )
            else:
                findings += secrets_in(data, "artifact:" + name)
    return findings


def gitleaks(sandbox):
    """Pinned upstream rules; no inline allow comments or repository ignore files."""
    tool = json.loads((ROOT / "ci/security-tools.json").read_text(encoding="utf-8"))
    version = tool["version"]
    expected_url = (
        f"https://github.com/gitleaks/gitleaks/releases/download/v{version}/"
        f"gitleaks_{version}_windows_x64.zip"
    )
    if not re.fullmatch(r"\d+\.\d+\.\d+", version) or tool["archive_url"] != expected_url:
        raise ValueError("UNTRUSTED_SECURITY_TOOL_ORIGIN")
    with urllib.request.urlopen(tool["archive_url"], timeout=90) as response:
        archive_bytes = response.read()
    if sha(archive_bytes) != tool["archive_sha256"]:
        raise ValueError("GITLEAKS_ARCHIVE_DIGEST_MISMATCH")
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        executable_bytes = archive.read("gitleaks.exe")
    if sha(executable_bytes) != tool["executable_sha256"]:
        raise ValueError("GITLEAKS_EXECUTABLE_DIGEST_MISMATCH")
    executable = sandbox / "gitleaks.exe"
    executable.write_bytes(executable_bytes)
    config = sandbox / "gitleaks.toml"
    config.write_bytes(b"[extend]\nuseDefault = true\n")
    ignored = sandbox / "empty-ignore"
    ignored.write_bytes(b"")
    version = subprocess.run([str(executable), "version"], capture_output=True, timeout=30)
    if version.returncode or version.stdout.decode().strip() != tool["version"]:
        raise ValueError("GITLEAKS_VERSION_MISMATCH")
    current = sandbox / "current"
    source_files = [(ROOT / name, "income-analytics/" + name) for name in tracked_files()]
    source_files += [
        (file, file.relative_to(ROOT.parent).as_posix())
        for file in (ROOT.parent / ".github").rglob("*")
        if file.is_file()
    ]
    for source, name in source_files:
        if source.is_file():
            if not source.resolve().is_relative_to(ROOT.parent.resolve()):
                raise ValueError("SOURCE_LINK_OUTSIDE_CHECKOUT")
            destination = current / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.read_bytes())
    findings = []
    negative = sandbox / "negative"
    negative.mkdir()
    (negative / "synthetic.py").write_bytes(
        b"github_token = 'ghp_" + sha(b"income-synthetic-invalid-credential").encode()[:36] + b"'\n"
    )
    for mode, target in (("selftest", negative), ("dir", current), ("git", ROOT.parent)):
        raw = sandbox / ("gitleaks-" + mode + ".json")
        command = [
            str(executable),
            "dir" if mode == "selftest" else mode,
            "--redact=100",
            "--no-banner",
            "--log-level",
            "error",
            "--config",
            str(config),
            "--gitleaks-ignore-path",
            str(ignored),
            "--ignore-gitleaks-allow",
            "--report-format=json",
            "--report-path",
            str(raw),
        ]
        if mode == "git":
            command.append("--log-opts=--all")
        result = subprocess.run([*command, str(target)], capture_output=True, timeout=300)
        if result.returncode not in {0, 1} or not raw.exists() or result.stderr.strip():
            raise ValueError("GITLEAKS_SCAN_UNAVAILABLE")
        observed = json.loads(raw.read_text(encoding="utf-8"))
        if (result.returncode == 1) != bool(observed):
            raise ValueError("GITLEAKS_SCAN_INCOMPLETE")
        if mode == "selftest":
            if not observed:
                raise ValueError("GITLEAKS_NEGATIVE_FIXTURE_NOT_DETECTED")
            continue
        for item in observed:
            file = item["File"].replace("\\", "/")
            if mode == "dir":
                file = Path(item["File"]).relative_to(current).as_posix()
            row = {
                "tool": "gitleaks",
                "mode": mode,
                "rule": item["RuleID"],
                "file": file,
                "line": item["StartLine"],
                "commit": item.get("Commit", ""),
                "state": "POTENTIAL",
            }
            if mode == "dir":
                row["content_sha256"] = sha((current / file).read_bytes())
            row["identity"] = sha(json.dumps(row, sort_keys=True).encode())
            findings.append(row)
    return {
        "version": tool["version"],
        "archive_sha256": tool["archive_sha256"],
        "executable_sha256": tool["executable_sha256"],
        "negative_fixture": "REJECTED",
        "findings": findings,
    }


def scan_history():
    # Full accessible refs; never credential validation or history rewriting.
    output = subprocess.check_output(
        [
            "git",
            "-c",
            "core.quotepath=false",
            "rev-list",
            "--objects",
            "--all",
            "--",
            "income-analytics",
            ".github",
        ],
        cwd=ROOT.parent,
        text=True,
        encoding="utf-8",
    )
    objects = {}
    for row in output.splitlines():
        oid, _, name = row.partition(" ")
        if name and Path(name).suffix.lower() in {
            ".py",
            ".js",
            ".json",
            ".md",
            ".yml",
            ".yaml",
            ".ps1",
            ".txt",
            ".example",
        }:
            objects.setdefault(oid, name)
    findings = []
    scanned = 0
    process = subprocess.Popen(
        ["git", "cat-file", "--batch"],
        cwd=ROOT.parent,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    try:
        for oid, name in objects.items():
            process.stdin.write((oid + "\n").encode())
            process.stdin.flush()
            header = process.stdout.readline().split()
            if len(header) != 3:
                raise ValueError("HISTORY_OBJECT_UNAVAILABLE")
            size = int(header[2])
            content = process.stdout.read(size)
            process.stdout.read(1)
            if header[1] == b"blob":
                scanned += 1
                findings += secrets_in(content, "git:" + oid + ":" + name)
    finally:
        process.stdin.close()
        process.stdout.close()
        process.wait(timeout=30)
    return {
        "scanned_blobs": scanned,
        "findings": findings,
        "scope": (
            "accessible Git refs, text source/config/docs; "
            "no dangling objects, LFS or remote inaccessible refs"
        ),
    }


def components():
    packages = {}
    for file in sorted((ROOT / "ci").glob("*.lock")):
        for line in file.read_text().splitlines():
            match = re.fullmatch(r"([\w.\-]+)==([^ ]+) --hash=sha256:([a-f0-9]{64})", line)
            if match:
                name, version, digest = match.groups()
                key = ("PyPI", name.lower().replace("_", "-"), version)
                packages.setdefault(
                    key,
                    {
                        "ecosystem": "PyPI",
                        "name": key[1],
                        "version": version,
                        "hashes": set(),
                        "locations": [],
                    },
                )
                packages[key]["hashes"].add(digest)
                packages[key]["locations"].append(file.relative_to(ROOT).as_posix())
    for name, version, location in [
        ("echarts", "6.1.0", "src/income_analytics/api/static/vendor/echarts-6.1.0.min.js"),
        ("firebase", "13.1.0", "src/income_analytics/api/static/js/auth-client.js"),
    ]:
        file = ROOT / location
        if (
            not file.exists()
            or version not in file.read_text(encoding="utf-8")[:200000]
            and name == "firebase"
        ):
            raise ValueError("SDK_INVENTORY_CHANGED_REVIEW_REQUIRED")
        packages[("npm", name, version)] = {
            "ecosystem": "npm",
            "name": name,
            "version": version,
            "hashes": {sha(file.read_bytes())} if name == "echarts" else set(),
            "locations": [location],
        }
    for item in javascript_components():
        packages[(item["ecosystem"], item["name"], item["version"])] = item
    vendor = ROOT / "src/income_analytics/api/static/vendor/echarts-6.1.0.min.js"
    if b"6.1.0" not in re.findall(rb'\.version\s*=\s*["\x27](\d+\.\d+\.\d+)', vendor.read_bytes()):
        raise ValueError("VENDORED_VERSION_MISMATCH")
    return [dict(v, hashes=sorted(v["hashes"])) for _, v in sorted(packages.items())]


def javascript_components():
    document = json.loads((ROOT / "ci/javascript-components.json").read_text(encoding="utf-8"))
    result = []
    for item in document["components"]:
        algorithm, encoded = item["integrity"].split("-", 1)
        if algorithm != "sha512":
            raise ValueError("UNSUPPORTED_NPM_INTEGRITY")
        result.append(
            {
                "ecosystem": "npm",
                "name": item["name"],
                "version": item["version"],
                "hashes": set(),
                "locations": [item["metadata_url"]],
                "additional_hashes": [
                    {"alg": "SHA-512", "content": base64.b64decode(encoded, validate=True).hex()}
                ],
                "hash_scope": "Published npm tarball metadata; CDN bytes audited separately",
            }
        )
    for item in document["unresolved_ranges"]:
        result.append(
            {
                "ecosystem": "npm",
                "name": item["name"],
                "version": "NOT_VERIFIED",
                "package_only": True,
                "hashes": set(),
                "locations": ["ci/javascript-components.json"],
                "declared_range": item["declared_range"],
            }
        )
    allowed_assets = {
        "https://www.gstatic.com/firebasejs/13.1.0/firebase-app.js",
        "https://www.gstatic.com/firebasejs/13.1.0/firebase-auth.js",
    }
    if {item["url"] for item in document["external_assets"]} != allowed_assets:
        raise ValueError("UNREVIEWED_CDN_ORIGIN")
    for item in document["external_assets"]:
        with urllib.request.urlopen(item["url"], timeout=60) as response:
            if sha(response.read()) != item["sha256"]:
                raise ValueError("CDN_BUNDLE_DIGEST_MISMATCH")
    return result


def query_dependencies(items, opener=urllib.request.urlopen):
    payload = {
        "queries": [
            {
                "package": {"ecosystem": p["ecosystem"], "name": p["name"]},
                **({} if p.get("package_only") else {"version": p["version"]}),
            }
            for p in items
        ]
    }
    request = urllib.request.Request(
        "https://api.osv.dev/v1/querybatch",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with opener(request, timeout=90) as response:
        results = json.load(response)["results"]
    if len(results) != len(items) or any(r.get("next_page_token") for r in results):
        raise ValueError("INCOMPLETE_DEPENDENCY_RESPONSE")
    alerts = []
    for package, result in zip(items, results):
        for vulnerability in result.get("vulns", []):
            alerts.append(
                {
                    "package": package["name"],
                    "version": package["version"],
                    "ecosystem": package["ecosystem"],
                    "id": vulnerability["id"],
                    "state": "POTENTIAL",
                    "triage": "REQUIRED",
                }
            )
    return {
        "provider": "OSV querybatch",
        "components": len(items),
        "alerts": alerts,
        "status": "FAIL" if alerts else "PASS",
    }


def sast(sandbox):
    target = sandbox / "bandit.json"
    result = subprocess.run(
        [sys.executable, "-m", "bandit", "-r", "src", "ci", "-f", "json", "-o", str(target), "-q"],
        cwd=ROOT,
        capture_output=True,
        timeout=300,
    )
    if result.returncode not in {0, 1} or not target.exists():
        raise ValueError("BANDIT_UNAVAILABLE")
    document = json.loads(target.read_text())
    if document.get("errors"):
        raise ValueError("BANDIT_PARTIAL_SCAN")
    rows = []
    for item in document["results"]:
        filename = item["filename"].replace("\\", "/").removeprefix("./")
        rows.append(
            {
                "tool": "bandit",
                "rule": item["test_id"],
                "file": filename,
                "line": item["line_number"],
                "severity": item["issue_severity"],
                "confidence": item["issue_confidence"],
                "cwe": item.get("issue_cwe", {}).get("id"),
                "code_sha256": sha(item["code"].encode()),
            }
        )
    for file in (ROOT / "src/income_analytics/api/static/js").rglob("*.js"):
        for number, line in enumerate(file.read_text(encoding="utf-8").splitlines(), 1):
            for rule, pattern in [
                ("JS_EVAL", r"\beval\s*\("),
                ("JS_FUNCTION", r"new\s+Function\s*\("),
                ("JS_DOCUMENT_WRITE", r"document\.write\s*\("),
                (
                    "JS_DIRECT_DOM_SOURCE",
                    r"innerHTML\s*=.*(?:location\.|localStorage\.|sessionStorage\.)",
                ),
            ]:
                if re.search(pattern, line):
                    rows.append(
                        {
                            "tool": "javascript-critical-patterns-v1",
                            "rule": rule,
                            "file": file.relative_to(ROOT).as_posix(),
                            "line": number,
                            "severity": "HIGH",
                            "confidence": "MEDIUM",
                            "cwe": 79,
                            "code_sha256": sha(line.encode()),
                        }
                    )
    return rows


def identity(row):
    return sha(
        json.dumps(
            {k: row[k] for k in ("tool", "rule", "file", "code_sha256")}, sort_keys=True
        ).encode()
    )


def enforce_triage(findings, decisions):
    known = {item["identity"]: item for item in decisions}
    rejected = []
    for item in findings:
        key = identity(item)
        decision = known.get(key)
        if (
            not decision
            or decision.get("state") not in {"FALSE_POSITIVE", "MITIGATED", "ACCEPTED_RISK"}
            or not decision.get("reason")
        ):
            rejected.append(key)
        elif item["severity"] in {"HIGH", "CRITICAL"} and decision["state"] == "ACCEPTED_RISK":
            rejected.append(key)
        elif item["severity"] in {"HIGH", "CRITICAL"} and not decision.get("evidence"):
            rejected.append(key)
    return rejected


def enforce_secrets(findings, decisions):
    """A benign marker exemption covers exact file bytes, never a key prefix."""
    approved = {
        (item["type"], item["content_sha256"])
        for item in decisions
        if item.get("state") == "FALSE_POSITIVE" and item.get("reason")
    }
    return [item for item in findings if (item["type"], item["content_sha256"]) not in approved]


def sbom(items, commit, artifact_digest):
    tool = json.loads((ROOT / "ci/security-tools.json").read_text(encoding="utf-8"))
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "version": 1,
        "metadata": {
            "component": {"type": "application", "name": "income-analytics", "version": commit},
            "properties": [
                {"name": "income:source:commit", "value": commit},
                {"name": "income:artifact:sha256", "value": artifact_digest},
            ],
            "tools": {
                "components": [
                    {
                        "type": "application",
                        "name": "gitleaks",
                        "version": tool["version"],
                        "hashes": [{"alg": "SHA-256", "content": tool["executable_sha256"]}],
                        "externalReferences": [
                            {"type": "distribution", "url": tool["archive_url"]}
                        ],
                    }
                ]
            },
        },
        "components": [bom_component(package) for package in items],
    }


def bom_component(package):
    result = {
        "type": "library",
        "name": package["name"],
        "bom-ref": package_url(package),
        "purl": package_url(package),
        "hashes": (
            [{"alg": "SHA-256", "content": value} for value in package["hashes"]]
            + package.get("additional_hashes", [])
        ),
        "properties": [
            {
                "name": "income:hash-scope",
                "value": package.get("hash_scope", "Locked wheel/source"),
            },
            {
                "name": "income:declared-range",
                "value": package.get("declared_range", "EXACT_VERSION"),
            },
        ],
    }
    if not package.get("package_only"):
        result["version"] = package["version"]
    else:
        result["properties"][0]["value"] = (
            "Bundled helper version NOT_VERIFIED; package-wide OSV scan"
        )
    if package["ecosystem"] == "npm" and package["name"] == "firebase":
        javascript = json.loads(
            (ROOT / "ci/javascript-components.json").read_text(encoding="utf-8")
        )
        result["externalReferences"] = [
            {
                "type": "distribution",
                "url": item["url"],
                "hashes": [{"alg": "SHA-256", "content": item["sha256"]}],
            }
            for item in javascript["external_assets"]
        ]
    return result


def package_url(package):
    ecosystem = "pypi" if package["ecosystem"] == "PyPI" else "npm"
    name = package["name"].replace("@", "%40")
    suffix = "" if package.get("package_only") else "@" + package["version"]
    return f"pkg:{ecosystem}/{name}{suffix}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--history", action="store_true")
    parser.add_argument("--artifact", type=Path)
    parser.add_argument("--build-report", type=Path, required=True)
    args = parser.parse_args()
    destination = ROOT / "ci-reports/security"
    destination.mkdir(parents=True, exist_ok=True)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    report = {
        "status": "NOT_VERIFIED",
        "checkout_sha": commit,
        "production_access": False,
        "failures": [],
    }
    try:
        forbidden = forbidden_source_files(tracked_files())
        report["source_policy"] = {
            "status": "FAIL" if forbidden else "PASS",
            "forbidden_files": forbidden,
        }
        with tempfile.TemporaryDirectory(prefix="income-security-") as temporary:
            sandbox = Path(temporary)
            findings = sast(sandbox)
            report["gitleaks"] = gitleaks(sandbox)
            import run as isolated

            environment = isolated.isolated_environment(sandbox)
            junit = sandbox / "security-junit.xml"
            test_run = isolated.execute(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-p",
                    "offline_plugin",
                    "tests/security/test_firebase_authorization.py",
                    "tests/security/test_firebase_headers.py",
                    "tests/security/test_identity_verification_policy.py",
                    "tests/security/test_baseline_hardening.py",
                    "tests/infrastructure/test_saas_portfolio_owner.py",
                    "ci/test_security.py",
                    "ci/test_delivery.py",
                    "-q",
                    "--tb=short",
                    f"--junitxml={junit}",
                ],
                environment,
                sandbox,
                "security-tests",
            )
            tests = isolated.safe_junit(junit, destination / "security-junit.xml")
            tests["status"] = (
                "PASS"
                if test_run.returncode == 0
                and tests["totals"]["passed"] > 0
                and tests["totals"]["skipped"] == 0
                else "FAIL"
            )
            report["security_tests"] = tests
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        reviewed_gitleaks = {
            item["identity"]
            for item in policy.get("gitleaks_decisions", [])
            if item.get("state") == "FALSE_POSITIVE" and item.get("reason")
        }
        gitleaks_untriaged = [
            item
            for item in report["gitleaks"]["findings"]
            if item["identity"] not in reviewed_gitleaks
        ]
        report["gitleaks"]["untriaged"] = gitleaks_untriaged
        report["gitleaks"]["status"] = "FAIL" if gitleaks_untriaged else "PASS"
        rejected = enforce_triage(findings, policy["decisions"])
        report["sast"] = {
            "findings": findings,
            "untriaged": rejected,
            "status": "FAIL" if rejected else "PASS",
            "bandit_version": importlib.metadata.version("bandit"),
            "javascript_rules": "v1",
        }
        secrets = []
        for name in tracked_files():
            file = ROOT / name
            if file.is_file() and file.suffix.lower() not in {
                ".db",
                ".sqlite",
                ".xlsx",
                ".zip",
                ".whl",
            }:
                secrets += secrets_in(file.read_bytes(), name)
        for file in (ROOT.parent / ".github").rglob("*"):
            if file.is_file():
                secrets += secrets_in(file.read_bytes(), file.relative_to(ROOT.parent).as_posix())
        if args.history:
            report["history"] = scan_history()
            secrets += report["history"]["findings"]
        else:
            raise ValueError("HISTORY_SCAN_REQUIRED")
        artifact_digest = "NOT_VERIFIED"
        if args.artifact:
            artifact_digest = sha(args.artifact.read_bytes())
            from artifact import verify
            from pipeline_identity import execution_fingerprint, governance_policy_identity

            build = json.loads(args.build_report.read_text(encoding="utf-8"))
            if (
                build.get("checkout_sha") != commit
                or build.get("status") != "PASS"
                or build.get("reproducibility") != "PASS"
                or build.get("independent_builds") != 2
                or build.get("source_fingerprint") != execution_fingerprint(ROOT)
                or build.get("governance_policy_sha256") != governance_policy_identity(ROOT)
            ):
                raise ValueError("SECURITY_BUILD_IDENTITY_MISMATCH")
            verify(args.artifact, commit, build["artifact_sha256"])
            with zipfile.ZipFile(args.artifact) as bundle:
                report["manifest_sha256"] = sha(bundle.read("manifest.json"))
            secrets += artifact_secrets(args.artifact)
        else:
            raise ValueError("ARTIFACT_SCAN_REQUIRED")
        untriaged_secrets = enforce_secrets(secrets, policy["secret_decisions"])
        report["secret_scanning"] = {
            "status": "FAIL" if untriaged_secrets else "PASS",
            "findings": secrets,
            "untriaged": untriaged_secrets,
            "rules_version": 1,
            "secret_validation": "NOT_ATTEMPTED",
        }
        items = components()
        report["dependencies"] = query_dependencies(items)
        (destination / "sbom.cdx.json").write_text(
            json.dumps(sbom(items, commit, artifact_digest), indent=2) + "\n"
        )
        report["artifact_sha256"] = artifact_digest
        from pipeline_identity import execution_fingerprint, governance_policy_identity

        report["source_fingerprint"] = execution_fingerprint(ROOT)
        report["governance_policy_sha256"] = governance_policy_identity(ROOT)
        report["policy_sha256"] = sha(POLICY.read_bytes())
        report["status"] = (
            "PASS"
            if not rejected
            and not forbidden
            and not untriaged_secrets
            and not gitleaks_untriaged
            and report["dependencies"]["status"] == tests["status"] == "PASS"
            else "FAIL"
        )
    except Exception as error:
        # Do not serialize exception text: URLs/tokens/paths may appear in scanner exceptions.
        message = str(error)
        code = message if re.fullmatch(r"[A-Z][A-Z0-9_]{2,100}", message) else None
        report["failures"].append({"type": type(error).__name__, "code": code})
        report["status"] = "FAIL" if code and "MISMATCH" in code else "NOT_VERIFIED"
    (destination / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "failures": report["failures"]}))
    return int(report["status"] != "PASS")


if __name__ == "__main__":
    raise SystemExit(main())
