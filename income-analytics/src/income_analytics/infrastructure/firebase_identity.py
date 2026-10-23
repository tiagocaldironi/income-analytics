"""Only Firebase Admin verifies identities; no custom JWT implementation."""

import os
from datetime import timedelta
from functools import lru_cache


@lru_cache(maxsize=1)
def firebase_app():
    import firebase_admin
    from firebase_admin import credentials

    from income_analytics.infrastructure.auth_config import validate_configuration

    validate_configuration()
    # The emulator uses unsigned tokens. Never allow this outside development.
    credential = None
    if os.getenv("FIREBASE_AUTH_EMULATOR_HOST"):
        from google.auth.credentials import AnonymousCredentials

        class EmulatorCredential(credentials.Base):
            def get_credential(self):
                return AnonymousCredentials()

        credential = EmulatorCredential()
    return firebase_admin.initialize_app(
        credential, {"projectId": os.environ["FIREBASE_PROJECT_ID"]}, name="income-auth"
    )


class FirebaseIdentity:
    def methods(self, uid: str) -> list[str]:
        from firebase_admin import auth

        user = auth.get_user(uid, app=firebase_app())
        if user.disabled or not user.email_verified:
            raise ValueError("User unavailable")
        return [
            provider.provider_id
            for provider in user.provider_data
            if provider.provider_id in {"google.com", "password"}
        ]

    def verify_id_token(self, token: str) -> dict:
        from firebase_admin import auth

        return auth.verify_id_token(token, app=firebase_app(), check_revoked=True)

    def create_cookie(self, token: str, seconds: int) -> str:
        from firebase_admin import auth

        return auth.create_session_cookie(token, timedelta(seconds=seconds), app=firebase_app())

    def verify_cookie(self, cookie: str) -> dict:
        from firebase_admin import auth

        return auth.verify_session_cookie(cookie, app=firebase_app(), check_revoked=True)

    def verify_link_cookie(self, cookie: str) -> dict:
        from firebase_admin import auth

        # Adding a password can revoke the prior Firebase cookie. Only the
        # explicit link handoff may use its still-valid signature/expiry: the
        # handler separately requires a fresh, non-revoked token for the SAME
        # UID, active internal account, one-use recent confirmation, bound local
        # session and CSRF. No financial route accepts this cookie.
        return auth.verify_session_cookie(cookie, app=firebase_app(), check_revoked=False)

    def revoke(self, uid: str) -> None:
        from firebase_admin import auth

        auth.revoke_refresh_tokens(uid, app=firebase_app())


identity_provider = FirebaseIdentity()
