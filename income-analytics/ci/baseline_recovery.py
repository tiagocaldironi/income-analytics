"""Verify and recover the pinned historical staging rollback fixture."""

import json
import zipfile
from pathlib import Path

from artifact import sha, verify
from delivery import BASELINE_COMMIT, BASELINE_RUN, REPOSITORY, require

ROOT = Path(__file__).resolve().parents[1]


def recover_baseline(client, run, expected, destination):
    """Recover approved A after authenticating source run, tag, assets and bytes."""
    pin = json.loads((ROOT / "ci/baseline-a.json").read_text(encoding="utf-8"))
    require(expected == pin["source_commit"] == BASELINE_COMMIT, "BASELINE_COMMIT_MISMATCH")
    require(run.get("id") == pin["original_run_id"] == BASELINE_RUN, "BASELINE_RUN_MISMATCH")
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
        release.get("tag_name") == pin["release_tag"]
        and release.get("draft") is False
        and release.get("prerelease") is True,
        "BASELINE_RELEASE_UNTRUSTED",
    )
    ref = client.json(f"git/ref/tags/{pin['release_tag']}")
    target = ref.get("object", {})
    if target.get("type") == "tag":
        target = client.json(f"git/tags/{target.get('sha')}").get("object", {})
    require(
        target.get("type") == "commit" and target.get("sha") == expected,
        "BASELINE_RELEASE_COMMIT_MISMATCH",
    )

    required_assets = {pin["package_asset"], pin["checksum_asset"], pin["manifest_asset"]}
    assets = {asset["name"]: asset for asset in release.get("assets", [])}
    require(set(assets) == required_assets, "BASELINE_RELEASE_ASSETS_INVALID")
    payloads = {}
    for name, metadata in assets.items():
        require(metadata.get("state") == "uploaded", "BASELINE_RELEASE_ASSET_UNAVAILABLE")
        payload = client.bytes(f"releases/assets/{metadata['id']}", "application/octet-stream")
        require(
            metadata.get("digest") == "sha256:" + sha(payload),
            "BASELINE_RELEASE_ASSET_DIGEST_MISMATCH",
        )
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
        require(
            package.read("manifest.json") == manifest_bytes,
            "BASELINE_EMBEDDED_MANIFEST_MISMATCH",
        )

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
