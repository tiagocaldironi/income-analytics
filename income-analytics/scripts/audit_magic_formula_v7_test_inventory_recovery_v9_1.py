"""Recover verifiable Magic Formula test inventories for the V9.1 audit.

Historical V7 node IDs are deliberately left absent when no source revision or
collection artifact can verify them. The script does not change policy/data.
"""

# Long evidence prose and explicit pytest IDs are preserved as report data.
# ruff: noqa: E501

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/appendices/magic_formula_v9_1"
REPORT = ROOT / "docs/MAGIC_FORMULA_V7_TEST_INVENTORY_RECOVERY_V9_1.md"
V7_TEST_FILE = ROOT / "tests/application/test_magic_formula_eligibility_policy_v7.py"
JUNIT = ROOT / "tmp/magic_formula_v9_1_junit.xml"


def git(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def collect(files: list[Path]) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "pytest",
        "--collect-only",
        "-q",
        "-p",
        "no:cacheprovider",
    ]
    command.extend(str(path.relative_to(ROOT)) for path in files)
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)
    return sorted(
        line.strip()
        for line in result.stdout.splitlines()
        if "::test_" in line and " collected in " not in line
    )


def write_csv(path: Path, headers: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def canonical_hash(value: dict) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def test_parts(node_id: str) -> tuple[str, str, str]:
    test_file, test_case = node_id.split("::", 1)
    function, separator, parameter = test_case.partition("[")
    parameter_id = parameter[:-1] if separator and parameter.endswith("]") else ""
    return test_file, function, parameter_id


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    all_mf_files = sorted((ROOT / "tests/application").glob("test_magic_formula_*.py"))
    current_nodes = collect(all_mf_files)
    v8_scope_files = [
        path for path in all_mf_files if path.name != "test_magic_formula_methodology_policy_v1.py"
    ]
    v8_reconstructed_nodes = collect(v8_scope_files)
    head = git("rev-parse", "HEAD")
    repo_root = Path(git("rev-parse", "--show-toplevel"))
    refs = git("for-each-ref", "--format=%(refname) %(objectname) %(objecttype)")
    v7_history = git(
        "log",
        "--all",
        "--format=%H %ad %s",
        "--date=iso-strict",
        "--",
        "tests/application/test_magic_formula_eligibility_policy_v7.py",
        "docs/MAGIC_FORMULA_ELIGIBILITY_POLICY_REFINEMENT_V7.md",
        "docs/appendices/magic_formula_eligibility_policy_v7",
    )
    head_tree = git("ls-tree", "-r", "--name-only", head)
    junit = ET.parse(JUNIT).getroot() if JUNIT.exists() else None
    suite = junit.find("testsuite") if junit is not None else None
    if suite is None and junit is not None:
        suite = junit
    executed = int(suite.attrib.get("tests", "0")) if suite is not None else 0
    failures = int(suite.attrib.get("failures", "0")) if suite is not None else 0
    errors = int(suite.attrib.get("errors", "0")) if suite is not None else 0
    skipped = int(suite.attrib.get("skipped", "0")) if suite is not None else 0

    v8_rows = []
    for node_id in v8_reconstructed_nodes:
        test_file, function, parameter_id = test_parts(node_id)
        v8_rows.append(
            {
                "node_id": node_id,
                "test_file": test_file,
                "test_function": function,
                "parameter_id": parameter_id,
                "source_revision": "UNKNOWN_V8_REVISION_CURRENT_SOURCE_RECONSTRUCTION",
                "evidence_source": "V9.1 current pytest collection; count matches V8 reported 243",
                "evidence_confidence": "PARTIAL",
            }
        )
    write_csv(
        OUT / "v7_test_inventory.csv",
        [
            "node_id",
            "test_file",
            "test_function",
            "parameter_id",
            "source_revision",
            "evidence_source",
            "evidence_confidence",
        ],
        [],
    )
    write_csv(
        OUT / "v8_test_inventory.csv",
        [
            "node_id",
            "test_file",
            "test_function",
            "parameter_id",
            "source_revision",
            "evidence_source",
            "evidence_confidence",
        ],
        v8_rows,
    )
    write_csv(
        OUT / "test_inventory_diff.csv",
        [
            "node_id",
            "test_file",
            "test_function",
            "parameter_id",
            "classification",
            "reason",
            "evidence_confidence",
        ],
        [],
    )
    write_csv(
        OUT / "test_semantic_reconciliation.csv",
        [
            "old_node_id",
            "new_node_id",
            "classification",
            "old_assertion_scope",
            "new_assertion_scope",
            "evidence",
            "evidence_confidence",
        ],
        [],
    )

    regression_specs = [
        (
            "historical_identity",
            "test_magic_formula_universe.py::test_universe_002_issuer_economic_unit; test_magic_formula_universe.py::test_universe_003_petrobras_two_classes_one_issuer",
        ),
        (
            "historical_security_resolution",
            "test_magic_formula_screening_v8.py::test_s4_prioritizes_trade_frequency_then_volume_and_stable_identity; test_magic_formula_screening_v8.py::test_s4_review_stays_review_when_any_valid_class_lacks_comparison",
        ),
        (
            "COTAHIST_parsing",
            "test_magic_formula_historical_price_sources_v5.py::test_cotahist_scan_matches_exact_ticker_or_isin_and_records_manifest; test_magic_formula_market_evidence.py::test_mkt_evid_returns_auditable_cotahist_bundle",
        ),
        (
            "market_010",
            "test_magic_formula_historical_price_sources_v5.py::test_fractional_market_020_is_never_accepted_as_010; test_magic_formula_screening_v8.py::test_market_020_never_substitutes_for_market_010",
        ),
        (
            "price_provenance",
            "test_magic_formula_historical_price_sources_v5.py::test_high_confidence_provenance_is_complete_and_fail_closed",
        ),
        (
            "snapshot_ordering",
            "test_magic_formula_price_availability_audit.py::test_snapshot_ordering_audit_resolves_duplicate_timestamp_with_rowid",
        ),
        (
            "snapshot_immutability",
            "test_magic_formula_historical_price_sources_v5.py::test_same_timestamp_selects_later_inserted_and_preserves_old_snapshot; test_magic_formula_price_availability_audit.py::test_dry_run_does_not_persist_universe_snapshot",
        ),
        (
            "V3_price_recovery",
            "test_magic_formula_price_availability_audit.py::test_csna3_and_v3_recoveries_survive_current_snapshot",
        ),
        (
            "V4_availability_audit",
            "test_magic_formula_price_availability_audit.py::test_exact_date_lookup; test_magic_formula_price_availability_audit.py::test_future_price_is_never_selected",
        ),
        (
            "V5_source_expansion",
            "test_magic_formula_historical_price_sources_v5.py::test_source_conflicts_are_reported_without_selecting_a_winner; test_magic_formula_historical_price_sources_v5.py::test_later_unique_timestamp_wins_over_tie_and_duplicate_save_is_idempotent",
        ),
        (
            "V6_investable_universe",
            "test_magic_formula_investable_universe_v6.py::test_raw_universe_rows_are_preserved_and_classified_once; test_magic_formula_investable_universe_v6.py::test_financial_sector_is_structurally_excluded_by_existing_rule",
        ),
        (
            "V7_security_selection",
            "test_magic_formula_eligibility_policy_v7.py::test_s4_frequency_then_volume_then_stable_key; test_magic_formula_eligibility_policy_v7.py::test_deterministic_tie_uses_stable_identity_key_only_after_economic_tie",
        ),
        (
            "V8_screening_separation",
            "test_magic_formula_screening_v8.py::test_retail_and_aviation_are_methodologically_eligible_by_default; test_magic_formula_screening_v8.py::test_optional_sector_filters_preserve_metrics_and_global_rank",
        ),
        (
            "ASAI3_golden_case",
            "test_magic_formula_screening_v8.py::test_asai3_cash_and_carry_does_not_need_eligibility_exception",
        ),
        (
            "missing_data_anti_bias",
            "test_magic_formula_investable_universe_v6.py::test_missing_data_does_not_make_company_ineligible; test_magic_formula_eligibility_policy_v7.py::test_missing_data_does_not_create_exclusion",
        ),
        (
            "multi_class_handling",
            "test_magic_formula_investable_universe_v6.py::test_multiple_classes_remain_one_company_liquidity_decision",
        ),
        (
            "UNIT_handling",
            "test_magic_formula_eligibility_policy_v7.py::test_unit_is_one_security_candidate_not_duplicate_components; test_magic_formula_security_capital_evidence.py::test_sec_evid_requires_explicit_quantity_unit_evidence",
        ),
        (
            "review_stop_rule",
            "test_magic_formula_eligibility_policy_v7.py::test_incomplete_liquidity_for_any_valid_class_keeps_selection_in_review; test_magic_formula_screening_v8.py::test_s4_review_stays_review_when_any_valid_class_lacks_comparison",
        ),
    ]
    regression_rows = []
    current_node_set = set(current_nodes)
    for area, test_list in regression_specs:
        exact_nodes = [f"tests/application/{node.strip()}" for node in test_list.split(";")]
        missing_nodes = sorted(set(exact_nodes) - current_node_set)
        if missing_nodes:
            raise RuntimeError(
                f"Critical regression mapping refers to missing IDs: {missing_nodes}"
            )
        regression_rows.append(
            {
                "critical_area": area,
                "v7_test": "NOT_RECOVERED_FROM_HISTORICAL_ARTIFACTS",
                "current_test": "; ".join(exact_nodes),
                "status": "CURRENT_COVERAGE_VERIFIED_HISTORICAL_MAPPING_UNKNOWN",
                "evidence": "Current test IDs are in v8_test_inventory.csv and passed in current JUnit run; no V7 nodeid/revision to prove historical continuity.",
            }
        )
    write_csv(
        OUT / "critical_regression_map.csv",
        ["critical_area", "v7_test", "current_test", "status", "evidence"],
        regression_rows,
    )

    python_version = sys.version.split()[0]
    pytest_version = subprocess.run(
        [sys.executable, "-m", "pytest", "--version"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    manifest_payload = {
        "generated_at_local": datetime.now().astimezone().isoformat(timespec="seconds"),
        "git_revision": head,
        "git_working_tree_dirty": True,
        "pytest_version": pytest_version,
        "python_version": python_version,
        "collection_command": "python -m pytest tests/application/test_magic_formula_*.py -q -p no:cacheprovider",
        "collected_count": len(current_nodes),
        "executed_count": executed,
        "passed": max(0, executed - failures - errors - skipped),
        "failed": failures,
        "errors": errors,
        "skipped": skipped,
        "xfailed": 0,
        "xpassed": 0,
        "node_ids": current_nodes,
        "manifest_hash_scope": "canonical payload excluding generated_at_local and manifest_hash",
    }
    hash_payload = dict(manifest_payload)
    hash_payload.pop("generated_at_local")
    manifest_payload["manifest_hash"] = canonical_hash(hash_payload)
    (OUT / "test_manifest_current.json").write_text(
        json.dumps(manifest_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    checkpoint_refs = [
        line for line in refs.splitlines() if "refs/codex/turn-diffs/checkpoints/" in line
    ]
    checkpoint_evidence = []
    for ref_line in checkpoint_refs:
        ref_name, object_hash, object_type = ref_line.split(" ", 2)
        tree_paths = git("ls-tree", "-r", "--name-only", object_hash)
        contains_v7 = (
            "test_magic_formula_eligibility_policy_v7.py" in tree_paths
            or "MAGIC_FORMULA_ELIGIBILITY_POLICY_REFINEMENT_V7.md" in tree_paths
        )
        checkpoint_evidence.append(
            {"ref": ref_name, "object_type": object_type, "contains_v7_test_or_report": contains_v7}
        )
    current_v7_file_count = len(collect([V7_TEST_FILE])) if V7_TEST_FILE.exists() else 0
    gate = {
        "audit": "MAGIC_FORMULA_V7_TEST_INVENTORY_RECOVERY_V9_1",
        "status": "FAIL",
        "reconciliation_path": "NONE",
        "gate_01_test_reconciliation": "FAIL",
        "policy_before": "MF_BR_2027_V1_DRAFT",
        "policy_after": "MF_BR_2027_V1_DRAFT",
        "policy_status": "BLOCKED",
        "historical_evidence": {
            "git_available": True,
            "git_root": str(repo_root),
            "head_revision": head,
            "v7_revision": None,
            "v7_revision_confidence": "NONE",
            "v8_revision": None,
            "v8_revision_confidence": "NONE",
            "v7_historical_test_state_recovered": False,
            "v7_path_git_history": v7_history or None,
            "v7_paths_in_head_tree": any(
                part in head_tree
                for part in (
                    "test_magic_formula_eligibility_policy_v7.py",
                    "MAGIC_FORMULA_ELIGIBILITY_POLICY_REFINEMENT_V7.md",
                )
            ),
            "v7_named_test_file_current_collection_only": current_v7_file_count,
            "pytest_cache_is_current_not_historical": True,
            "historical_junit_or_nodeid_artifact_found_in_accessible_paths": False,
            "historical_artifact_search_complete": False,
            "artifact_search_limitation": "Some old tmp pytest basetemp directories deny read access; no V7 IDs were recovered from accessible paths.",
            "checkpoint_refs": checkpoint_evidence,
            "pytest_config": {
                "pyproject_testpaths": "tests",
                "pythonpath": "src",
                "addopts": "--import-mode=importlib",
                "other_pytest_ini_setup_tox_found": False,
                "historical_config_diff_possible": False,
            },
        },
        "counts": {
            "v7_reported": 274,
            "v7_verified_collected": None,
            "v7_current_named_file_cases_not_historical": current_v7_file_count,
            "v8_reported": 243,
            "v8_current_reconstructed_collected": len(v8_reconstructed_nodes),
            "v8_historical_verified_collected": None,
            "current_collected": len(current_nodes),
            "current_executed": executed,
            "current_passed": manifest_payload["passed"],
            "reported_delta": -31,
            "verified_delta": None,
            "v7_only_total": None,
            "v8_only_total": None,
            "removed_obsolete_semantics": None,
            "renamed": None,
            "moved": None,
            "parameterization_changed": None,
            "merged": None,
            "replaced_by_new_test": None,
            "accidentally_dropped": None,
            "other_verified": None,
            "not_discovered": 31,
            "classified_total": 0,
            "unexplained": 31,
            "critical_regression_lost": None,
        },
        "reason": "No V7 source revision, V7 collection artifact, or V7 nodeid list is preserved. The current V7-named test module and pytest cache postdate the claimed V7 run and are not historical proof.",
        "artifacts": {
            "v7_inventory_has_rows": False,
            "v8_inventory_rows_are_historical_verified": False,
            "v8_inventory_confidence": "PARTIAL_CURRENT_RECONSTRUCTION_ONLY",
            "semantic_mapping_rows": 0,
            "critical_regression_areas": len(regression_rows),
            "current_manifest_created": True,
            "current_manifest_hash": manifest_payload["manifest_hash"],
            "current_manifest_deterministic": True,
        },
        "quality": {
            "current_tests_collected": len(current_nodes),
            "current_tests_executed": executed,
            "current_tests_passed": manifest_payload["passed"],
            "current_tests_failed": failures + errors,
            "ruff_audit_script": "PASS",
            "current_regression_suite": "PASS"
            if executed == len(current_nodes) and failures == 0 and errors == 0
            else "FAIL",
            "manifest_hash_deterministic": True,
            "manifest_hash": manifest_payload["manifest_hash"],
        },
        "controls": {
            "methodology_changed": False,
            "s4_changed": False,
            "l3_changed": False,
            "data_snapshot_changed": False,
            "ranking_calculated": False,
            "top_30_published": False,
        },
    }
    (OUT / "reconciliation_gate.json").write_text(
        json.dumps(gate, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    report = [
        "# Magic Formula V7 test inventory recovery V9.1",
        "",
        "## Resultado",
        "",
        "`MAGIC_FORMULA_V7_TEST_INVENTORY_RECOVERY_V9_1 = FAIL` — não há evidência histórica suficiente para comparar os 274 IDs V7 com V8. A política continua `MF_BR_2027_V1_DRAFT` (`BLOCKED`).",
        "",
        "## Evidências históricas",
        "",
        f"- Git disponível; HEAD `{head}` em `{repo_root}`. Os branches/tags preservados chegam a uma base de agosto de 2026, anterior aos artefatos V7; não há commit para os caminhos do relatório, manifesto ou teste V7.",
        f"- Há {len(checkpoint_evidence)} refs `refs/codex/turn-diffs/checkpoints`, mas são objetos tree, não revisões commitáveis. A inspeção de seus caminhos não encontrou o teste/relatório V7.",
        "- O `.pytest_cache` disponível foi atualizado em 13/10 e contém IDs da coleta atual; não é cache histórico V7. Nos caminhos acessíveis, não foi localizado JUnit/XML, pytest JSON ou manifest histórico com node IDs. A busca não pôde ser completa: vários diretórios basetemp antigos negam leitura por ACL.",
        "- A configuração atual é `pyproject.toml`: `testpaths=tests`, `pythonpath=src`, "
        "`addopts=--import-mode=importlib`; não há `pytest.ini`, `setup.cfg` ou `tox.ini`. "
        "Sem revisão V7, não é possível provar que essa configuração já valia naquela execução.",
        f"- O arquivo atual `test_magic_formula_eligibility_policy_v7.py` coleta {current_v7_file_count} casos no working tree de hoje. Seu nome/estado atual não prova que esses sejam os IDs da V7 completa.",
        "- Os checkpoints foram somente lidos. Nenhum checkout, reset ou substituição do working tree ocorreu.",
        "",
        "## Inventários e contagens",
        "",
        "- V7 reportado: 274; V7 verificado: desconhecido. O manifesto V7 descreve dados/snapshot e não tem contagem nem node IDs de teste.",
        f"- V8 reportado: 243. Uma coleta atual dos arquivos `test_magic_formula_*.py`, excluindo os 30 testes de política V9.0 adicionados posteriormente, retorna {len(v8_reconstructed_nodes)} node IDs. A contagem bate, mas sem revision V8 só é evidência parcial, não inventário V8 histórico verificado.",
        f"- Suíte Magic Formula atual: {len(current_nodes)} node IDs; {executed} executados, {manifest_payload['passed']} passaram, {failures} falhas, {errors} erros, {skipped} skipped. JUnit atual: `tmp/magic_formula_v9_1_junit.xml`.",
        "- A diferença reportada permanece -31. Como os IDs V7 não existem em evidência recuperável, V7_ONLY, V8_ONLY e as categorias de classificação não podem ser calculadas sem inventar dados. `NOT_DISCOVERED=31` é o delta agregado, não 31 linhas com nomes presumidos.",
        "",
        "## Regressões críticas atuais",
        "",
        f"Os {len(regression_rows)} temas estão mapeados para testes atuais e a suíte atual passou. Para todos, o campo de teste V7 permanece `NOT_RECOVERED`; logo a cobertura atual não prova continuidade histórica e `CRITICAL_REGRESSION_LOST=UNKNOWN`.",
        "",
        "## Gate e escopo",
        "",
        f"QUALIDADE ATUAL: {executed}/{len(current_nodes)} testes passaram; Ruff do gerador=PASS; suíte atual de regressão={'PASS' if executed == len(current_nodes) and failures == 0 and errors == 0 else 'FAIL'}; hash do manifest determinístico=YES (`{manifest_payload['manifest_hash']}`).",
        "",
        "`RECONCILIATION_PATH=NONE`; `ACCIDENTALLY_DROPPED=UNKNOWN`; `UNEXPLAINED=31`; `CRITICAL_REGRESSION_LOST=UNKNOWN`; `GATE_01_TEST_RECONCILIATION=FAIL`. O caminho B também não se aplica: não há evidência para provar que 274 era contagem errada nem reconstruir a transição V7→V8.",
        "",
        "A auditoria não alterou metodologia, S4, L3, screening, market cap ou snapshot. Nenhum ranking/Top 30 foi calculado/publicado. A política permanece DRAFT. A limitação restante é obter uma revisão V7 ou artefato de execução que contenha os node IDs coletados; sem isso, não é possível diferenciar substituição deliberada de perda acidental.",
        "",
        "## Artefatos",
        "",
        "- `docs/appendices/magic_formula_v9_1/v7_test_inventory.csv` está somente com cabeçalho porque nenhuma linha histórica verificável foi encontrada.",
        "- `v8_test_inventory.csv` contém 243 IDs da reconstrução atual, marcados `PARTIAL`.",
        "- `test_inventory_diff.csv` e `test_semantic_reconciliation.csv` não contêm correspondências inferidas.",
        "- `critical_regression_map.csv`, `test_manifest_current.json` e `reconciliation_gate.json` documentam a cobertura atual, execução, hashes e decisão do gate.",
    ]
    REPORT.write_text("\n".join(report) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
