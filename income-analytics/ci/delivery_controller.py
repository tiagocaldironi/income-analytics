"""Apply the pinned historical baseline recovery around the stable delivery gate."""

import delivery_pipeline as pipeline
from baseline_recovery import recover_baseline
from delivery import BASELINE_COMMIT, BASELINE_RUN

_ORIGINAL_ACQUIRE = pipeline.acquire


def acquire(client, run_id, commit, mode, destination, current_run=None, rollback=False):
    if rollback and run_id == BASELINE_RUN and commit == BASELINE_COMMIT:
        run = client.json(f"actions/runs/{run_id}")
        return recover_baseline(client, run, commit, destination)
    return _ORIGINAL_ACQUIRE(client, run_id, commit, mode, destination, current_run, rollback)


def main() -> int:
    pipeline.acquire = acquire
    return pipeline.main()


if __name__ == "__main__":
    raise SystemExit(main())
