"""Install only the verified bundle in a disposable environment; never deploy."""

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from artifact import PYTHON, verify

# Imported before any application code in each smoke subprocess. Only loopback
# is allowed; ADC, API clients and startup jobs cannot contact external services.
GUARD = '''import socket
original = socket.socket.connect
def guarded(self, address):
    if isinstance(address, tuple) and address[0] not in {"127.0.0.1", "::1", "localhost"}:
        raise RuntimeError("BUILD_SMOKE_NETWORK_DENIED")
    return original(self, address)
socket.socket.connect = guarded
original_ex = socket.socket.connect_ex
def guarded_ex(self, address):
    if isinstance(address, tuple) and address[0] not in {"127.0.0.1", "::1", "localhost"}:
        raise RuntimeError("BUILD_SMOKE_NETWORK_DENIED")
    return original_ex(self, address)
socket.socket.connect_ex = guarded_ex
'''


def command(args, cwd, env, label):
    result = subprocess.run(args, cwd=cwd, env=env, capture_output=True, timeout=240)
    if result.returncode:
        # Raw dependency/application logs can contain local paths or payloads.
        raise RuntimeError("SMOKE_FAILED_" + label)


def smoke(archive, commit, digest):
    verify(archive, commit, digest)
    if sys.version.split()[0] != PYTHON or sys.platform != "win32":
        raise ValueError("SMOKE_REQUIRES_TARGET_RUNTIME")
    with tempfile.TemporaryDirectory(prefix="income-build-smoke-") as temporary:
        sandbox = Path(temporary).resolve()
        root = sandbox / "application"
        root.mkdir()
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(root)  # verify rejected traversal, links and extra files first.
        env = {
            k: v for k, v in os.environ.items()
            if k.upper() in {"PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT"}
        }
        state = sandbox / "state"
        state.mkdir()
        guard = sandbox / "guard"
        guard.mkdir()
        (guard / "sitecustomize.py").write_text(GUARD, encoding="utf-8")
        env.update({
            "HOME": str(state), "USERPROFILE": str(state),
            "TEMP": str(state), "TMP": str(state), "TMPDIR": str(state),
            "PYTHONPATH": os.pathsep.join((str(guard), str(root / "src"))),
            "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1",
            "INCOME_ENV": "development", "INCOME_AUTH_MODE": "local",
            "INCOME_PUBLIC_SIGNUP_ENABLED": "0", "INCOME_ANALYTICS_TESTING": "1",
            "INCOME_ANALYTICS_DISABLE_BACKGROUND_JOBS": "1",
            "INCOME_ANALYTICS_DATABASE": str(state / "smoke.db"),
            "INCOME_ANALYTICS_COTAHIST_CACHE": str(state / "cotahist"),
            "GOOGLE_APPLICATION_CREDENTIALS": str(state / "absent-credentials.json"),
            "CLOUDSDK_CONFIG": str(state / "no-cloud"),
        })
        venv = sandbox / "venv"
        command([sys.executable, "-m", "venv", str(venv)], root, env, "VENV")
        python = venv / "Scripts/python.exe"
        command([
            str(python), "-m", "pip", "--isolated", "install", "--no-index",
            "--find-links", str(root / "wheelhouse"), "--require-hashes",
            "--only-binary=:all:", "-r", "requirements.lock",
        ], root, env, "INSTALL")
        command([str(python), "-m", "pip", "check"], root, env, "DEPENDENCIES")
        command([str(python), "-m", "alembic", "upgrade", "head"], root, env, "MIGRATIONS")
        command([str(python), "-c", "from income_analytics.main import app; assert app"],
                root, env, "IMPORT")
        with socket.socket() as reserve:
            reserve.bind(("127.0.0.1", 0))
            port = reserve.getsockname()[1]
        server = subprocess.Popen([
            str(python), "-m", "uvicorn", "income_analytics.main:app",
            "--host", "127.0.0.1", "--port", str(port), "--no-access-log",
        ], cwd=root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            deadline = time.monotonic() + 60
            while True:
                if server.poll() is not None:
                    raise RuntimeError("SMOKE_FAILED_STARTUP")
                try:
                    with opener.open(f"http://127.0.0.1:{port}/health", timeout=2) as response:
                        if json.load(response) != {"status": "ok"}:
                            raise RuntimeError("SMOKE_FAILED_HEALTH")
                    break
                except (urllib.error.URLError, TimeoutError):
                    if time.monotonic() > deadline:
                        raise RuntimeError("SMOKE_FAILED_HEALTH_TIMEOUT") from None
                    time.sleep(0.2)
            for path, marker in (("/", b"<!"), ("/static/css/app.css", b"{")):
                with opener.open(f"http://127.0.0.1:{port}{path}", timeout=5) as response:
                    if response.status != 200 or marker not in response.read():
                        raise RuntimeError("SMOKE_FAILED_STATIC")
            # Confirm migrations actually reached the single packaged Alembic head.
            command([str(python), "-c", (
                "from alembic.config import Config; from alembic.script import ScriptDirectory; "
                "from sqlalchemy import create_engine; "
                "from alembic.runtime.migration import MigrationContext; "
                "from income_analytics.infrastructure.database import database_url; "
                "c=create_engine(database_url()).connect(); "
                "assert MigrationContext.configure(c).get_current_revision() == "
                "ScriptDirectory.from_config(Config('alembic.ini')).get_current_head(); c.close()"
            )], root, env, "SCHEMA_HEAD")
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=10)
    return {"status": "PASS", "installation": "PASS", "migrations_temporary_sqlite": "PASS",
            "backend_import": "PASS", "startup_health": "PASS", "static_files": "PASS",
            "cleanup": "PASS", "external_network": "DENIED", "production_access": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--sha256", required=True)
    args = parser.parse_args()
    print(json.dumps(smoke(args.archive, args.commit, args.sha256), sort_keys=True))
