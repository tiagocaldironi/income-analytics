"""Read-only GitHub provenance acquisition followed by disposable staging validation."""

import io
import json
import os
import re
import subprocess
import urllib.error
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from artifact import canonical, sha, verify
from delivery import (
    BASELINE_COMMIT,
    BASELINE_RELEASE_TAG,
    BASELINE_RUN,
    REPOSITORY,
    DeliveryError,
    production_request,
    require,
    security_delivery_gate,
    trusted_source,
)
from delivery_stage import exercise, expect_failure

ROOT = Path(__file__).resolve().parents[1]


class Github:
    """Fixed API host and GET only. Token is never written or sent to blob hosts."""

    def __init__(self, token=None):
        self.token = token

    def bytes(self, path, accept="application/vnd.github+json"):
        require(re.fullmatch(r"[A-Za-z0-9_./?=&-]+", path) is not None, "INVALID_API_PATH")
        require(not any(part in {".", ".."} for part in path.split("/")), "INVALID_API_PATH")
        headers = {"Accept": accept, "X-GitHub-Api-Version": "2022-11-28"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        request = urllib.request.Request(
            "https://api.github.com/repos/" + REPOSITORY + "/" + path, headers=headers, method="GET"
        )

        class StripCredentials(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, request, fp, code, msg, response_headers, newurl):
                redirected = super().redirect_request(
                    request, fp, code, msg, response_headers, newurl
                )
                if redirected is not None:
                    require(newurl.startswith("https://"), "INSECURE_ARTIFACT_REDIRECT")
                    redirected.remove_header("Authorization")
                return redirected

        try:
            with urllib.request.build_opener(StripCredentials()).open(
                request, timeout=90
            ) as response:
                require(
                    int(response.headers.get("Content-Length", "0")) < 512 * 1024 * 1024,
                    "ARTIFACT_TOO_LARGE",
                )
                data = response.read(512 * 1024 * 1024 + 1)
                require(len(data) <= 512 * 1024 * 1024, "ARTIFACT_TOO_LARGE")
                return data
        except urllib.error.HTTPError as error:
            raise DeliveryError("GITHUB_READ_FAILED_" + str(error.code)) from None

    def json(self, path):
        return json.loads(self.bytes(path))


def envelope(client, metadata):
    data = client.bytes(f"actions/artifacts/{metadata['id']}/zip")
    require(metadata.get("expired") is False, "ARTIFACT_EXPIRED")
    require("sha256:" + sha(data) == metadata.get("digest"), "ARTIFACT_TRANSPORT_DIGEST_MISMATCH")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)), "DUPLICATE_ENVELOPE_FILE")
        require(
            all("/" not in n and "\\" not in n and ":" not in n for n in names),
            "INVALID_ENVELOPE_PATH",
        )
        require(
            sum(f.file_size for f in archive.infolist()) <= 512 * 1024 * 1024, "ARTIFACT_TOO_LARGE"
        )
        return {name: archive.read(name) for name in names}


def one(artifacts, name):
    values = [a for a in artifacts if a["name"] == name]
    require(len(values) == 1, "ARTIFACT_UNAVAILABLE")
    return values[0]


def recover_baseline(client, run, expected, destination):
    """Recover approved A from a durable release after authenticating its source run."""
    pin = json.loads((ROOT / "ci/baseline-a.json").read_text(encoding="utf-8"))
    require(expected == pin["source_commit"] == BASELINE_COMMIT, "BASELINE_COMMIT_MISMATCH")
    require(run.get("id") == pin["original_run_id"], "BASELINE_RUN_MISMATCH")
    require(
        run.get("workflow_id") == pin["original_workflow_id"]
        and run.get("path") == pin["original_workflow_path"]
        and run.get("event") == "push"
        and run.get("head_branch") == "develop"
        and run.get("head_sha") == expected
        and run.get("status") == "completed",
        "BASELINE_SOURCE_RUN_UNTRUSTED",
    )
    jobs = client.json(
        f"actions/runs/{pin['original_run_id']}/attempts/{run['run_attempt']}/jobs?per_page=100"
    )["jobs"]
    states = {job["name"]: job.get("conclusion") for job in jobs}
    require(
        states.get("CI / Engineering") == "success"
        and states.get("CI / Reproducible build") == "success",
        "BASELINE_SOURCE_GATES_FAILED",
    )

    release = client.json(f"releases/tags/{pin['release_tag']}")
    require(
        release.get("tag_name") == BASELINE_RELEASE_TAG
        and release.get("draft") is False
        and release.get("prerelease") is True,
        "BASELINE_RELEASE_UNTRUSTED",
    )
    ref = client.json(f"git/ref/tags/{pin['release_tag']}")
    target = ref.get("object", {})
    if target.get("type") == "tag":
        target = client.json(f"git/tags/{target.get('sha')}").get("object", {})
    require(target.get("type") == "commit" and target.get("sha") == expected,
            "BASELINE_RELEASE_COMMIT_MISMATCH")

    required_assets = {
        pin["package_asset"],
        pin["checksum_asset"],
        pin["manifest_asset"],
    }
    assets = {asset["name"]: asset for asset in release.get("assets", [])}
    require(set(assets) == required_assets, "BASELINE_RELEASE_ASSETS_INVALID")
    payloads = {}
    for name, metadata in assets.items():
        require(metadata.get("state") == "uploaded", "BASELINE_RELEASE_ASSET_UNAVAILABLE")
        payload = client.bytes(f"releases/assets/{metadata['id']}", "application/octet-stream")
        require(metadata.get("digest") == "sha256:" + sha(payload),
                "BASELINE_RELEASE_ASSET_DIGEST_MISMATCH")
        payloads[name] = payload

    manifest_bytes = payloads[pin["manifest_asset"]]
    require(sha(manifest_bytes) == pin["manifest_sha256"], "BASELINE_MANIFEST_DIGEST_MISMATCH")
    manifest = json.loads(manifest_bytes)
    require(
        manifest.get("repository") == pin["repository"]
        and manifest.get("commit_sha") == expected
        and manifest.get("source_fingerprint") == pin["source_fingerprint"]
        and manifest.get("build_policy_sha256") == pin["build_policy_sha256"],
        "BASELINE_MANIFEST_PROVENANCE_MISMATCH",
    )
    package_bytes = payloads[pin["package_asset"]]
    require(sha(package_bytes) == pin["package_sha256"], "BASELINE_PACKAGE_DIGEST_MISMATCH")
    checksum = payloads[pin["checksum_asset"]].decode("ascii").split()
    require(checksum and checksum[0] == pin["package_sha256"], "BASELINE_CHECKSUM_ASSET_MISMATCH")
    require(not destination.exists(), "LOGICAL_ARTIFACT_ALREADY_EXISTS")
    destination.write_bytes(package_bytes)
    verify(destination, expected, pin["package_sha256"])
    with zipfile.ZipFile(destination) as package:
        require(package.read("manifest.json") == manifest_bytes,
                "BASELINE_EMBEDDED_MANIFEST_MISMATCH")

    return {
        "repository": pin["repository"],
        "source_commit": expected,
        "build_run_id": pin["original_run_id"],
        "build_run_attempt": run["run_attempt"],
        "original_artifact_id": pin["original_artifact_id"],
        "original_artifact_digest": pin["original_artifact_digest"],
        "durable_release_tag": pin["release_tag"],
        "durable_release_id": release["id"],
        "durable_asset_ids": {name: assets[name]["id"] for name in sorted(assets)},
        "package_sha256": pin["package_sha256"],
        "manifest_sha256": pin["manifest_sha256"],
        "build_policy_identity": pin["build_policy_sha256"],
        "source_fingerprint": pin["source_fingerprint"],
        "environment_target": "DISPOSABLE_WINDOWS_STAGING",
        "mode": "approved_historical_rollback_fixture",
        "promotion_status": "PROMOTION_BLOCKED",
        "promotion_blockers": ["LEGACY_PINNED_ROLLBACK_ONLY"],
        "financial_release": "BLOCKED",
        "production_status": "PRODUCTION_NOT_AUTHORIZED",
        "validation_evidence_references": [
            f"https://github.com/{REPOSITORY}/actions/runs/{pin['original_run_id']}",
            f"https://github.com/{REPOSITORY}/releases/tag/{pin['release_tag']}",
        ],
    }


def acquire(client, run_id, commit, mode, destination, current_run=None, rollback=False):
    require(isinstance(run_id, int) and run_id > 0, "INVALID_BUILD_RUN")
    require(re.fullmatch(r"[a-f0-9]{40}", commit) is not None, "INVALID_SOURCE_COMMIT")
    run = client.json(f"actions/runs/{run_id}")
    # Reject unsafe origins BEFORE fetching a package or reading its contents.
    require(
        run.get("repository", {}).get("full_name") == REPOSITORY
        and run.get("head_repository", {}).get("full_name") == REPOSITORY,
        "WRONG_REPOSITORY",
    )
    require(
        run.get("workflow_id") == 399392307
        and run.get("path") == ".github/workflows/ci-offline.yml",
        "UNTRUSTED_WORKFLOW",
    )
    if rollback and run_id == BASELINE_RUN and commit == BASELINE_COMMIT:
        return recover_baseline(client, run, commit, destination)
    if mode == "delivery":
        require(
            run.get("event") == "push"
            and run.get("head_branch") == "develop"
            and run.get("head_sha") == commit,
            "UNMERGED_PR_NOT_PROMOTABLE",
        )
        require(run.get("status") == "completed", "SOURCE_NOT_COMPLETE")
        ancestry = client.json(f"compare/{commit}...develop")
        require(ancestry.get("merge_base_commit", {}).get("sha") == commit, "COMMIT_NOT_IN_DEVELOP")
    else:
        require(
            mode == "premerge" and run.get("event") == "pull_request" and current_run == run_id,
            "INVALID_PREMERGE_CONTEXT",
        )
    artifacts = client.json(f"actions/runs/{run_id}/artifacts?per_page=100")["artifacts"]
    jobs = client.json(f"actions/runs/{run_id}/attempts/{run['run_attempt']}/jobs?per_page=100")[
        "jobs"
    ]
    build_meta = one(artifacts, f"governance-build-{commit}")
    gate_meta = one(artifacts, f"gate-summary-{commit}")
    for metadata in (build_meta, gate_meta):
        require(metadata.get("workflow_run", {}).get("id") == run_id, "WRONG_ARTIFACT_RUN")
    build_files, gate_files = envelope(client, build_meta), envelope(client, gate_meta)
    require(
        set(build_files) == {"result.json"} and set(gate_files) == {"gate-summary.json"},
        "UNKNOWN_GATE_ENVELOPE",
    )
    build = json.loads(build_files["result.json"])
    gate = json.loads(gate_files["gate-summary.json"])
    app_meta = one(artifacts, f"application-{commit}-windows-x64")
    security_status = security_delivery_gate(gate, jobs, run_id, commit, rollback)
    identity = trusted_source(run, app_meta, jobs, build, gate, commit, mode, current_run)
    identity["security_baseline"] = security_status
    app_files = envelope(client, app_meta)
    package_name = f"income-analytics-{commit}-windows-x64.zip"
    require(
        set(app_files)
        == {package_name, package_name.removesuffix(".zip") + ".sha256", "manifest.json"},
        "UNKNOWN_APPLICATION_ENVELOPE",
    )
    require(not destination.exists(), "LOGICAL_ARTIFACT_ALREADY_EXISTS")
    destination.write_bytes(app_files[package_name])
    verify(destination, commit, identity["package_sha256"])
    with zipfile.ZipFile(destination) as package:
        manifest_bytes = package.read("manifest.json")
        manifest = json.loads(manifest_bytes)
    require(manifest == json.loads(app_files["manifest.json"]), "MANIFEST_ENVELOPE_MISMATCH")
    require(
        app_files[package_name.removesuffix(".zip") + ".sha256"].decode().split()[0]
        == identity["package_sha256"],
        "EXTERNAL_PACKAGE_DIGEST_MISMATCH",
    )
    require(
        manifest["build_policy_sha256"] == identity["build_policy_identity"]
        and manifest["source_fingerprint"] == build["artifact_source_fingerprint"],
        "POLICY_PROVENANCE_MISMATCH",
    )
    identity.update(
        manifest_sha256=sha(manifest_bytes),
        validation_evidence_references=[
            f"https://github.com/{REPOSITORY}/actions/runs/{run_id}",
            f"https://github.com/{REPOSITORY}/actions/runs/{run_id}/artifacts/{app_meta['id']}",
        ],
    )
    return identity


def delivery_decision(identity, validation, mode):
    require(validation.get("status") == "PASS", "STAGING_FAILED")
    checks = validation.get("checks", {})
    require(
        all(
            checks.get(name, {}).get("status") == "PASS"
            for name in (
                "known_good_A",
                "installation",
                "health",
                "backup",
                "restore",
                "rollback",
                "rollback_restore",
                "synthetic_restore_after_block",
                "immutable_promotion",
                "cleanup",
            )
        ),
        "INCOMPLETE_STAGING_EVIDENCE",
    )
    require(
        all(
            checks.get(name, {}).get("status") == "EXPECTED_FAILURE_OBSERVED"
            for name in (
                "negative_restore_changed_state",
                "negative_health",
                "negative_startup",
            )
        ),
        "NEGATIVE_TESTS_NOT_VERIFIED",
    )
    require(
        checks.get("incompatible_schema", {}).get("status") == "BLOCKED"
        and checks["incompatible_schema"].get("safe_block_verified") is True,
        "SCHEMA_BLOCK_NOT_VERIFIED",
    )
    require(
        identity["financial_release"] == "BLOCKED"
        and identity["production_status"] == "PRODUCTION_NOT_AUTHORIZED",
        "FALSE_RELEASE_AUTHORIZATION",
    )
    return {
        "staging_status": "STAGING_VALIDATED",
        "promotion_status": "PROMOTION_ELIGIBLE" if mode == "delivery" else "PROMOTION_BLOCKED",
        "promotion_blockers": [] if mode == "delivery" else ["PR_UNMERGED_PREMERGE_TEST_ONLY"],
        "eligibility_scope": "ENGINEERING_TECHNICAL_STAGING_ONLY",
        "financial_release": "BLOCKED",
        "production_status": "PRODUCTION_NOT_AUTHORIZED",
        "production_deploy": "NOT_IMPLEMENTED",
        "production_authorized": False,
    }


def main():
    import tempfile

    output = ROOT / "ci-reports/delivery"
    output.mkdir(parents=True, exist_ok=True)
    mode = os.getenv("DELIVERY_MODE", "delivery")
    result = {
        "schema": 1,
        "status": "FAIL",
        "gate": "CD / Staging validation",
        "mode": mode,
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "checks": {
            name: {"status": "NOT_RUN"}
            for name in (
                "known_good_A",
                "installation",
                "health",
                "backup",
                "restore",
                "rollback",
                "rollback_restore",
                "synthetic_restore_after_block",
                "immutable_promotion",
                "cleanup",
                "negative_restore_changed_state",
                "negative_health",
                "negative_startup",
                "incompatible_schema",
            )
        },
        "workflow_identity": {
            "path": (
                ".github/workflows/ci-offline.yml"
                if mode == "premerge"
                else ".github/workflows/delivery-validation.yml"
            ),
            "delivery_run_id": os.getenv("GITHUB_RUN_ID", "LOCAL_VALIDATION"),
            "workflow_ref": os.getenv("GITHUB_WORKFLOW_REF", "LOCAL_VALIDATION"),
            "workflow_sha": os.getenv("GITHUB_WORKFLOW_SHA", "LOCAL_VALIDATION"),
        },
        "production_authorized": False,
        "financial_release": "BLOCKED",
        "promotion_status": "PROMOTION_BLOCKED",
        "staging_status": "STAGING_FAILED",
    }
    code = 1
    try:
        production_request(
            os.getenv("DELIVERY_TARGET", "staging"), os.getenv("DELIVERY_PRODUCTION_AUTHORIZATION")
        )
        require(mode in {"delivery", "premerge"}, "UNKNOWN_DELIVERY_MODE")
        result["workflow_identity"]["controller_checkout_sha"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
        require(
            not subprocess.check_output(
                ["git", "status", "--porcelain"], cwd=ROOT, text=True
            ).strip(),
            "CONTROLLER_DIRTY",
        )
        run_id = int(os.environ["DELIVERY_SOURCE_RUN"])
        expected = os.environ["DELIVERY_SOURCE_COMMIT"]
        current_run = int(os.environ.get("GITHUB_RUN_ID", "0"))
        client = Github(os.getenv("DELIVERY_GITHUB_TOKEN"))
        with tempfile.TemporaryDirectory(prefix="income-delivery-acquire-") as directory:
            temporary = Path(directory)
            previous_archive, candidate_archive = temporary / "A.zip", temporary / "B.zip"
            previous = acquire(
                client,
                int(os.getenv("DELIVERY_PREVIOUS_RUN", str(BASELINE_RUN))),
                os.getenv("DELIVERY_PREVIOUS_COMMIT", BASELINE_COMMIT),
                "delivery",
                previous_archive,
                rollback=True,
            )
            candidate = acquire(client, run_id, expected, mode, candidate_archive, current_run)
            result["candidate"] = candidate
            result["previous_version"] = previous
            result["negative_missing_artifact"] = expect_failure(
                lambda: client.json("actions/artifacts/1"),
                {"GITHUB_READ_FAILED_404"},
            )
            exercise(previous_archive, candidate_archive, previous, candidate, result["checks"])
            require(result["checks"]["cleanup"]["status"] == "PASS", "CLEANUP_FAILED")
            result["status"] = "PASS"
            result.update(delivery_decision(candidate, result, mode))
            result["state_transitions"] = [
                candidate["promotion_status"],
                "STAGING_VALIDATED",
                result["promotion_status"],
                "PRODUCTION_NOT_AUTHORIZED",
            ]
            candidate["promotion_status"] = result["promotion_status"]
            candidate["validation_evidence_references"].append(
                f"https://github.com/{REPOSITORY}/actions/runs/{current_run}"
            )
            # Retain exactly the accepted package bytes; this is not a rebuild.
            # Preview deliberately publishes reports only, never an eligible package.
            if mode == "delivery":
                retained = output / f"promoted-{expected}.zip"
                retained.write_bytes(candidate_archive.read_bytes())
                require(
                    sha(retained.read_bytes()) == candidate["package_sha256"],
                    "PROMOTION_BYTES_CHANGED",
                )
                with zipfile.ZipFile(retained) as package:
                    (output / "manifest.json").write_bytes(package.read("manifest.json"))
            code = 0
    except Exception as error:
        result.update(
            status="FAIL",
            promotion_status="PROMOTION_BLOCKED",
            staging_status="STAGING_FAILED",
            failure_category=(
                str(error) if isinstance(error, DeliveryError) else type(error).__name__
            ),
        )
        if "candidate" in result:
            result["candidate"]["promotion_status"] = "PROMOTION_BLOCKED"
            result["candidate"]["promotion_blockers"] = [result["failure_category"]]
    (output / "validation.json").write_bytes(canonical(result))
    if "candidate" in result:
        (output / "candidate.json").write_bytes(canonical(result["candidate"]))
    print("CD / Staging validation: " + result["status"])
    return code


if __name__ == "__main__":
    raise SystemExit(main())
