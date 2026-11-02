"""Persistent, provider-neutral identity mapping and local session revocation."""

import hashlib
import json
import time
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from income_analytics.application.auth_context import Principal
from income_analytics.infrastructure.auth_config import signup_enabled
from income_analytics.infrastructure.database import SessionFactory
from income_analytics.infrastructure.models import (
    AuthIdentityRecord,
    AuthSessionRecord,
    SecurityAuditRecord,
    SecurityRateLimitRecord,
    UserRecord,
)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def audit(
    session: Session,
    actor_id: str | None,
    action: str,
    resource_id: str | None = None,
) -> None:
    session.add(
        SecurityAuditRecord(
            id=str(uuid4()),
            actor_id=actor_id,
            action=action,
            resource_id=resource_id,
            created_at=int(time.time()),
        )
    )


def resolve_identity(claims: dict, *, create: bool = False) -> Principal:
    # Never look up by email: different Firebase subjects stay separate.
    issuer, subject = claims["iss"], claims["sub"]
    method = claims.get("firebase", {}).get("sign_in_provider")
    if method not in {"google.com", "password"}:
        raise HTTPException(401, "Método de acesso não permitido.")
    with SessionFactory.begin() as db:
        identity = (
            db.query(AuthIdentityRecord).filter_by(issuer=issuer, subject=subject).one_or_none()
        )
        if identity is None:
            if not create or not signup_enabled():
                raise HTTPException(403, "O cadastro ainda não está disponível.")
            user_id = str(uuid4())
            db.add(UserRecord(id=user_id, status="ACTIVE"))
            db.flush()
            db.add(
                AuthIdentityRecord(
                    id=str(uuid4()),
                    user_id=user_id,
                    issuer=issuer,
                    subject=subject,
                    approved_methods=json.dumps([method]),
                    link_confirmed_until=0,
                )
            )
            audit(db, user_id, "ACCOUNT_CREATED_FREE")
        else:
            if method not in json.loads(identity.approved_methods):
                raise HTTPException(
                    403, "Confirme seu acesso atual na conta antes de adicionar outro método."
                )
            user_id = identity.user_id
        user = db.get(UserRecord, user_id)
        if user is None or user.status != "ACTIVE":
            raise HTTPException(401, "Conta indisponível. Entre novamente.")
    # Dedicated custom claim set by trusted administration, never profile/body.
    roles = claims.get("income_roles", [])
    roles = (
        frozenset(roles)
        if isinstance(roles, list) and all(isinstance(role, str) for role in roles)
        else frozenset()
    )
    return Principal(UUID(user_id), subject, roles)


def store_session(cookie: str, principal: Principal, csrf: str, seconds: int) -> None:
    with SessionFactory.begin() as db:
        db.query(AuthSessionRecord).filter(AuthSessionRecord.expires_at < int(time.time())).delete()
        db.merge(
            AuthSessionRecord(
                token_hash=digest(cookie),
                user_id=str(principal.user_id),
                csrf_hash=digest(csrf),
                expires_at=int(time.time()) + seconds,
            )
        )
        audit(db, str(principal.user_id), "LOGIN")


def validate_local_session(cookie: str, principal: Principal) -> str:
    with SessionFactory() as db:
        row = db.get(AuthSessionRecord, digest(cookie))
        if row is None or row.user_id != str(principal.user_id) or row.expires_at <= time.time():
            raise HTTPException(401, "Sessão expirada. Entre novamente.")
        return row.csrf_hash


def delete_session(cookie: str) -> None:
    with SessionFactory.begin() as db:
        row = db.get(AuthSessionRecord, digest(cookie))
        if row:
            audit(db, row.user_id, "LOGOUT")
            db.delete(row)


def rate_limit(key: str, *, limit: int, seconds: int = 60) -> None:
    """SQLite atomic counters are shared by all workers using this database."""
    now = int(time.time())
    window = now // seconds * seconds
    hashed = digest(key)
    with SessionFactory.begin() as db:
        db.query(SecurityRateLimitRecord).filter(
            SecurityRateLimitRecord.window < now - 2 * 86400
        ).delete()
        statement = insert(SecurityRateLimitRecord).values(key=hashed, window=window, count=1)
        returning = statement.on_conflict_do_update(
            index_elements=["key", "window"], set_={"count": SecurityRateLimitRecord.count + 1}
        ).returning(SecurityRateLimitRecord.count)
        count = db.execute(returning).scalar_one()
    if count > limit:
        raise HTTPException(
            429, "Muitas solicitações. Aguarde um momento.", headers={"Retry-After": str(seconds)}
        )
