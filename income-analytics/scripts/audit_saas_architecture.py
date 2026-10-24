"""Read-only inventory for the SaaS architecture audit; never imports the app.

Usage: py -3.14 scripts/audit_saas_architecture.py --database income_analytics.db
Only schemas, aggregate counts and source locations are emitted. No financial
payload, portfolio ID/name, credential value or environment value is exported.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def literal(node, default=None):
    try:
        return ast.literal_eval(node)
    except ValueError, TypeError:
        return default


def source_inventory():
    endpoints = []
    files = list((ROOT / "src/income_analytics/api/routers").glob("*.py")) + [
        ROOT / "src/income_analytics/main.py"
    ]
    for path in files:
        content = path.read_text(encoding="utf-8-sig")
        tree = ast.parse(content)
        prefixes = {}
        for node in tree.body:
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                if isinstance(node.value.func, ast.Name) and node.value.func.id == "APIRouter":
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            prefixes[target.id] = next(
                                (
                                    literal(k.value, "")
                                    for k in node.value.keywords
                                    if k.arg == "prefix"
                                ),
                                "",
                            )
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for dec in node.decorator_list:
                    if not isinstance(dec, ast.Call) or not isinstance(dec.func, ast.Attribute):
                        continue
                    if dec.func.attr not in {
                        "get",
                        "post",
                        "put",
                        "patch",
                        "delete",
                        "options",
                        "head",
                    }:
                        continue
                    owner = dec.func.value.id if isinstance(dec.func.value, ast.Name) else ""
                    route = prefixes.get(owner, "") + (literal(dec.args[0], "") if dec.args else "")
                    calls = [
                        n.func.id
                        for n in ast.walk(node)
                        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                    ]
                    endpoints.append(
                        {
                            "method": dec.func.attr.upper(),
                            "path": route,
                            "handler": node.name,
                            "source": path.relative_to(ROOT).as_posix(),
                            "line": node.lineno,
                            "depends_calls": calls.count("Depends"),
                            "security_calls": calls.count("Security"),
                        }
                    )
    model = ROOT / "src/income_analytics/infrastructure/models.py"
    models = []
    for cls in ast.parse(model.read_text(encoding="utf-8")).body:
        if not isinstance(cls, ast.ClassDef):
            continue
        table = next(
            (
                literal(n.value)
                for n in cls.body
                if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "__tablename__" for t in n.targets)
            ),
            None,
        )
        if table:
            columns = [
                n.target.id
                for n in cls.body
                if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)
            ]
            models.append(
                {
                    "class": cls.name,
                    "table": table,
                    "line": cls.lineno,
                    "columns": columns,
                    "portfolio_scoped": "portfolio_id" in columns,
                    "user_scoped": any(x in columns for x in ["user_id", "owner_user_id"]),
                }
            )
    hashes = {
        p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in files + [model]
    }
    env_names = sorted(
        set(
            re.findall(
                r'(?:getenv|environ\.get)\(\s*["\']([A-Z][A-Z0-9_]+)',
                "\n".join(p.read_text(encoding="utf-8-sig") for p in (ROOT / "src").rglob("*.py")),
            )
        )
    )
    return {
        "endpoints": sorted(endpoints, key=lambda e: (e["path"], e["method"])),
        "models": models,
        "source_sha256": hashes,
        "environment_variable_names": env_names,
    }


def database_inventory(database):
    uri = database.resolve().as_uri() + "?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.execute("PRAGMA query_only=ON")
    connection.execute("BEGIN")
    tables = []
    # Read a single transaction for consistent cross-table counts while the
    # local application may still be processing unrelated user requests.
    for (name,) in connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall():
        quoted = '"' + name.replace('"', '""') + '"'
        columns = [
            {"name": r[1], "type": r[2], "not_null": bool(r[3]), "primary_key": r[5]}
            for r in connection.execute("PRAGMA table_info(" + quoted + ")")
        ]
        rows = connection.execute("SELECT COUNT(*) FROM " + quoted).fetchone()[0]
        foreign_keys = [
            {"column": r[3], "target_table": r[2], "target_column": r[4], "on_delete": r[6]}
            for r in connection.execute("PRAGMA foreign_key_list(" + quoted + ")")
        ]
        tables.append(
            {"name": name, "row_count": rows, "columns": columns, "foreign_keys": foreign_keys}
        )
    version = connection.execute("SELECT version_num FROM alembic_version").fetchall()
    integrity = connection.execute("PRAGMA integrity_check").fetchall()
    violations = connection.execute("PRAGMA foreign_key_check").fetchall()
    connection.rollback()
    connection.close()
    return {
        "alembic_revision": [r[0] for r in version],
        "integrity": [r[0] for r in integrity],
        "foreign_key_violation_count": len(violations),
        "tables": tables,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    data = source_inventory()
    if args.database:
        data["database"] = database_inventory(args.database)
    encoded = json.dumps(data, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(encoded + "\n", encoding="utf-8")
    else:
        print(encoded)


if __name__ == "__main__":
    main()
