import time
from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.auth import TokenVerifier
from app.core.config import Settings
from app.main import create_app
from app.schemas import ProfileInput


@pytest.fixture
def jwt_factory():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    issuer = "https://unit-test.invalid/auth/v1"
    verifier = TokenVerifier(issuer, "authenticated")
    verifier.jwks = SimpleNamespace(
        get_signing_key_from_jwt=lambda _: SimpleNamespace(key=key.public_key())
    )
    subject = uuid4()

    def encode(**changes):
        claims = {
            "sub": str(subject),
            "exp": int(time.time()) + 120,
            "iat": int(time.time()) - 1,
            "iss": issuer,
            "aud": "authenticated",
            "role": "authenticated",
        }
        claims.update(changes)
        return jwt.encode(claims, key, algorithm="RS256", headers={"kid": "unit-test"})

    return verifier, subject, encode


def test_valid_signature_and_editable_metadata_is_ignored(jwt_factory):
    verifier, subject, encode = jwt_factory
    assert verifier.verify(encode(user_metadata={"tenant_id": str(uuid4())})) == subject


def test_api_uses_signature_verifier_before_database(jwt_factory):
    verifier, _, encode = jwt_factory
    app = create_app(Settings(_env_file=None))
    app.state.verifier = verifier
    with TestClient(app) as client:
        assert (
            client.get("/api/v1/me", headers={"Authorization": "Bearer garbage"}).status_code == 401
        )
        assert (
            client.get("/api/v1/me", headers={"Authorization": "Bearer " + encode()}).status_code
            == 503
        )


@pytest.mark.parametrize(
    "claims",
    [
        {"exp": 1},
        {"iss": "https://attacker.invalid"},
        {"aud": "wrong"},
        {"role": "service_role"},
        {"is_anonymous": True},
        {"sub": "not-a-uuid"},
        {"iat": int(time.time()) + 3600},
    ],
)
def test_invalid_claims_are_rejected(jwt_factory, claims):
    verifier, _, encode = jwt_factory
    with pytest.raises((jwt.PyJWTError, ValueError)):
        verifier.verify(encode(**claims))


def test_forged_signature_is_rejected(jwt_factory):
    verifier, _, encode = jwt_factory
    header, payload, _ = encode().split(".")
    with pytest.raises(jwt.PyJWTError):
        verifier.verify(header + "." + payload + "." + "AAAA")


def test_missing_token_and_oversized_body_fail_closed():
    with TestClient(create_app(Settings(_env_file=None))) as client:
        assert client.get("/api/v1/me").status_code == 401
        assert client.put("/api/v1/me", content=b"x" * 32769).status_code == 413
        assert client.get("/api/v1/me", headers={"Authorization": "Bearer fake"}).status_code == 503


def test_profile_rejects_tenant_injection_and_overlapping_hours():
    values = {
        "name": "Ana",
        "studio_name": "Ateliê",
        "phone": "65999999999",
        "specialties": ["Unhas"],
    }
    with pytest.raises(ValidationError):
        ProfileInput(**values, owner_id=str(uuid4()))
    with pytest.raises(ValidationError):
        ProfileInput(
            **values,
            working_periods=[
                {"weekday": 0, "starts_at": "09:00", "ends_at": "12:00"},
                {"weekday": 0, "starts_at": "11:00", "ends_at": "13:00"},
            ],
        )
    with pytest.raises(ValidationError):
        ProfileInput(**{**values, "name": "   "})
    with pytest.raises(ValidationError):
        ProfileInput(**values, timezone="Invalid/Zone")


def test_database_configuration_requires_rate_secret():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_url="postgresql+psycopg://invalid")
