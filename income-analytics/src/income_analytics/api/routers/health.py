import os

from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
def health() -> dict[str, str]:
    release_commit = os.environ.get("INCOME_ANALYTICS_RELEASE_COMMIT", "")
    result = {"status": "ok"}
    if release_commit:
        result["release_commit"] = release_commit
    return result
