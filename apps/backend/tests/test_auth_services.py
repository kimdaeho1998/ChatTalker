import uuid

import pytest
import jwt
from datetime import UTC, datetime, timedelta

from app.core.config import Settings
from app.models import Account
from app.services.auth import AuthError, PasswordService, TokenService


def test_argon2id_password_verifier_never_equals_plaintext() -> None:
    service = PasswordService()
    verifier = service.hash("correct horse battery staple")
    assert verifier != "correct horse battery staple"
    assert verifier.startswith("$argon2id$")
    assert service.verify(verifier, "correct horse battery staple")
    assert not service.verify(verifier, "incorrect")


def test_access_token_requires_issuer_audience_and_purpose() -> None:
    service = TokenService(Settings(jwt_secret="test-only-secret-value-with-at-least-32-chars"))
    account = Account(id=uuid.uuid4(), login="test", password_verifier="unused", auth_version=1)
    token = service.issue_access(account, uuid.uuid4())
    assert service.decode(token, "access")["sub"] == str(account.id)
    with pytest.raises(AuthError):
        service.decode(token, "password_change")


@pytest.mark.parametrize("claims", [
    {"sub": "x", "sid": "x", "av": 1, "purpose": "access"},
    {"sub": "x", "sid": "x", "av": 1, "purpose": "access", "exp": datetime.now(UTC) + timedelta(minutes=1)},
    {"sub": "x", "sid": "x", "av": 1, "purpose": "access", "iat": datetime.now(UTC), "exp": datetime.now(UTC) - timedelta(minutes=1)},
])
def test_malformed_access_claims_are_rejected(claims) -> None:
    settings = Settings(jwt_secret="test-only-secret-value-with-at-least-32-chars")
    service = TokenService(settings)
    claims.update({"iss": settings.jwt_issuer, "aud": settings.jwt_audience})
    token = jwt.encode(claims, settings.jwt_secret.get_secret_value(), algorithm="HS256")
    with pytest.raises(AuthError):
        service.decode(token, "access")


@pytest.mark.parametrize("mutation", ["future_iat", "bad_signature", "bad_issuer", "bad_audience", "bad_algorithm", "unsigned"])
def test_jwt_signature_issuer_audience_and_algorithm_rejection(mutation) -> None:
    settings = Settings(jwt_secret="test-only-secret-value-with-at-least-32-chars")
    service = TokenService(settings)
    now = datetime.now(UTC)
    claims = {"sub": "x", "sid": "x", "av": 1, "purpose": "access", "iat": now, "exp": now + timedelta(minutes=1), "iss": settings.jwt_issuer, "aud": settings.jwt_audience}
    if mutation == "future_iat": claims["iat"] = now + timedelta(hours=1)
    if mutation == "bad_issuer": claims["iss"] = "wrong"
    if mutation == "bad_audience": claims["aud"] = "wrong"
    if mutation == "bad_algorithm": token = jwt.encode(claims, settings.jwt_secret.get_secret_value(), algorithm="HS384")
    elif mutation == "unsigned": token = jwt.encode(claims, key="", algorithm="none")
    elif mutation == "bad_signature": token = jwt.encode(claims, "other-test-secret-with-at-least-thirty-two-chars", algorithm="HS256")
    else: token = jwt.encode(claims, settings.jwt_secret.get_secret_value(), algorithm="HS256")
    with pytest.raises(AuthError):
        service.decode(token, "access")
