# Income Analytics application bundle — format 1

Internal engineering artifact, not a production release. CERT_48 remains BLOCKED.
Target: Windows x64, CPython 3.14.7. Node is not needed to serve static HTML/CSS/JS.
No authentication change, production launcher, database, credentials or deployment is supplied.

Verify the ZIP against the independently obtained commit and SHA-256 from the Actions
report before extraction, using the trusted repository copy of `ci/artifact.py`:

```powershell
python ci/artifact.py verify application.zip --commit <40-character-SHA> --sha256 <digest>
```

The package's `artifact.py` is also a standalone verifier, but must be trusted first:
an internal checksum does not establish publisher authenticity. Compare the external
digest with the authenticated Actions report. ZIP is stored (uncompressed), sorted,
fixed date 1980-01-01, POSIX regular-file mode 0644; Git blobs remain byte exact.

After verification and extraction into a new disposable directory:

```powershell
python -m venv ../runtime-venv
../runtime-venv/Scripts/python.exe -m pip --isolated install --no-index --find-links wheelhouse --require-hashes --only-binary=:all: -r requirements.lock
../runtime-venv/Scripts/python.exe -m pip check
$env:PYTHONPATH = (Resolve-Path src).Path
$env:INCOME_AUTH_MODE = 'local'
$env:INCOME_ENV = 'development'
$env:INCOME_ANALYTICS_TESTING = '1'
$env:INCOME_ANALYTICS_DISABLE_BACKGROUND_JOBS = '1'
$env:INCOME_ANALYTICS_DATABASE = '<absolute-path-to-NEW-disposable-SQLite>'
../runtime-venv/Scripts/python.exe -m alembic upgrade head
../runtime-venv/Scripts/python.exe -m uvicorn income_analytics.main:app --host 127.0.0.1 --port 8000
```

Run from the extracted application root: database.py resolves alembic.ini relative
to src, and Alembic resolves its script directory from this working directory.
Keep all state outside the immutable package. Never point these commands at a
production database. `/health`, `/` and `/static/css/app.css` are tested by CI.
For the fully isolated test (fresh venv, no inherited credentials, temporary SQLite,
external network denied, server terminated, environment removed):

```powershell
python ci/smoke_artifact.py application.zip --commit <SHA> --sha256 <digest>
```

External quotes, Firebase, browser CDN resources and historical Magic Formula
reference databases/archives are external runtime inputs. They are not embedded
or certified by this build. This bundle does not make those features available
offline, nor does the smoke test certify their behavior or financial correctness.
No source package compilation occurs: locked third-party wheels plus exact source
and static files form the delivery unit. Only hash-checked wheels are installed.
