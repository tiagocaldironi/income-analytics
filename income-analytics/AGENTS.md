# Income Analytics working instructions

Follow the repository instructions and the applicable guidance in `.ai/`.

- Preserve financial calculations, historical evidence, identity and authorization, SQLite data and migration contracts. Use isolated databases for tests. Production changes require explicit authorization.
- Test the affected behavior and relevant financial or security invariants. Keep fixes for unrelated historical failures out of the change.
- Report engineering CI, scoped financial certification, staging and production separately. Engineering success does not authorize release. Keep historical failures visible and preserve the applicable release controls.
- Validate the exact artifact in staging before requesting production authorization. For an authorized publication, verify the running commit and health endpoint before reporting success.
