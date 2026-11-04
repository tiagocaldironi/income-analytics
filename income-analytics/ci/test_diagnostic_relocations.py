import hashlib
import json
from copy import deepcopy

import diagnostic_relocations as relocation
import pytest
from gate_policy import compare_diagnostics


@pytest.fixture
def evidence(tmp_path, monkeypatch):
    file = "src/example.py"
    before = b"def example():\n    return missing\n"
    after = b"# new module header\n" + before
    (tmp_path / "src").mkdir()
    (tmp_path / file).write_bytes(after)
    finding = {"tool": "mypy", "file": file, "line": 2, "column": 12,
               "code": "name-defined", "message": 'Name "missing" is not defined'}
    observed = dict(finding, line=3)
    reference = tmp_path / "docs/engineering/release-policy-65/candidate_mypy.json"
    reference.parent.mkdir(parents=True)
    reference.write_text(json.dumps({"findings": [finding]}))
    (tmp_path / "ci").mkdir()
    policy = {"base_commit": "a" * 40, "files": {file: {
        "before_sha256": hashlib.sha256(before).hexdigest(),
        "after_sha256": hashlib.sha256(after).hexdigest(),
    }}}
    (tmp_path / relocation.POLICY).write_text(json.dumps(policy))
    monkeypatch.setattr(relocation, "git_bytes", lambda *_: before)
    ledger = {"reviewed_source_sha256": {file: hashlib.sha256(before).hexdigest()}}
    return tmp_path, observed, finding, ledger, policy


def test_pinned_unchanged_function_can_relocate_without_changing_baseline(evidence):
    root, observed, finding, ledger, _ = evidence
    original = deepcopy(ledger)
    canonical, reviewed, audit = relocation.reviewed_relocations(root, [observed], ledger)
    assert canonical == [finding]
    assert ledger == original
    assert reviewed != ledger
    assert audit["raw_diagnostics"] == [observed]
    assert audit["baseline_modified"] is False


@pytest.mark.parametrize("field,value", [
    ("code", "new-rule"), ("message", "New defect"), ("column", 99), ("line", 1),
])
def test_new_identity_or_location_still_blocks(evidence, field, value):
    root, observed, finding, ledger, _ = evidence
    observed[field] = value
    canonical, _, _ = relocation.reviewed_relocations(root, [observed], ledger)
    assert compare_diagnostics(canonical, [finding])["status"] == "FAIL"


def test_multiplicity_cannot_be_hidden(evidence):
    root, observed, finding, ledger, _ = evidence
    canonical, _, _ = relocation.reviewed_relocations(root, [observed, observed], ledger)
    assert len(compare_diagnostics(canonical, [finding])["added"]) == 1


def test_unreviewed_source_change_fails_closed(evidence):
    root, observed, _, ledger, _ = evidence
    (root / observed["file"]).write_bytes(b"changed")
    with pytest.raises(ValueError, match="SOURCE_REVIEW_REQUIRED"):
        relocation.reviewed_relocations(root, [observed], ledger)


def test_changed_function_body_cannot_reuse_old_error_even_after_source_review(evidence):
    root, observed, finding, ledger, policy = evidence
    changed = b"# header\ndef example():\n    return missing + 1\n"
    (root / observed["file"]).write_bytes(changed)
    policy["files"][observed["file"]]["after_sha256"] = hashlib.sha256(changed).hexdigest()
    (root / relocation.POLICY).write_text(json.dumps(policy))
    canonical, _, _ = relocation.reviewed_relocations(root, [observed], ledger)
    assert compare_diagnostics(canonical, [finding])["status"] == "FAIL"


def test_different_original_ledger_identity_fails_closed(evidence):
    root, observed, _, ledger, _ = evidence
    ledger["reviewed_source_sha256"][observed["file"]] = "wrong"
    with pytest.raises(ValueError, match="LEDGER_BASE_MISMATCH"):
        relocation.reviewed_relocations(root, [observed], ledger)
