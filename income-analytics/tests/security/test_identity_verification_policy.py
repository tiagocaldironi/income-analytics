"""Local identity decisions; SDK doubles do not certify the real Firebase service."""

from unittest.mock import Mock

import pytest
from firebase_admin import auth

from income_analytics.infrastructure import firebase_identity


@pytest.mark.parametrize(
    "reason",
    [
        "malformed",
        "expired",
        "signature",
        "audience",
        "issuer",
        "missing_uid",
        "other_project",
        "revoked",
        "provider_failure",
    ],
)
def test_identity_failure_propagates_without_fallback(monkeypatch, reason):
    application = object()
    verifier = Mock(side_effect=ValueError(reason))
    monkeypatch.setattr(firebase_identity, "firebase_app", lambda: application)
    monkeypatch.setattr(auth, "verify_id_token", verifier)
    with pytest.raises(ValueError):
        firebase_identity.identity_provider.verify_id_token("synthetic-token")
    verifier.assert_called_once_with("synthetic-token", app=application, check_revoked=True)


def test_session_signature_and_revocation_are_required(monkeypatch):
    application = object()
    verifier = Mock(side_effect=ValueError("synthetic revoked cookie"))
    monkeypatch.setattr(firebase_identity, "firebase_app", lambda: application)
    monkeypatch.setattr(auth, "verify_session_cookie", verifier)
    with pytest.raises(ValueError):
        firebase_identity.identity_provider.verify_cookie("synthetic-cookie")
    verifier.assert_called_once_with("synthetic-cookie", app=application, check_revoked=True)
