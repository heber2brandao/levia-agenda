from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.timing import measure

bearer = HTTPBearer(auto_error=False)


class TokenVerifier:
    def __init__(self, issuer: str, audience: str):
        self.issuer = issuer
        self.audience = audience
        self.jwks = jwt.PyJWKClient(
            issuer + "/.well-known/jwks.json", cache_keys=False, lifespan=300, timeout=5
        )

    def verify(self, token: str) -> UUID:
        if len(token) > 8192:
            raise jwt.InvalidTokenError()
        header = jwt.get_unverified_header(token)
        if header.get("alg") not in ("ES256", "RS256") or not header.get("kid"):
            raise jwt.InvalidTokenError()
        key = self.jwks.get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token,
            key,
            algorithms=["ES256", "RS256"],
            issuer=self.issuer,
            audience=self.audience,
            options={"require": ["sub", "exp", "iat", "iss", "aud"]},
        )
        if claims.get("role") != "authenticated" or claims.get("is_anonymous") is True:
            raise jwt.InvalidTokenError()
        return UUID(claims["sub"])


def current_user(
    request: Request, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
) -> UUID:
    if not credentials:
        raise HTTPException(401, "Entre na sua conta", headers={"WWW-Authenticate": "Bearer"})
    verifier = request.app.state.verifier
    if verifier is None:
        raise HTTPException(503, "Autenticação ainda não configurada")
    try:
        with measure("auth"):
            return verifier.verify(credentials.credentials)
    except jwt.PyJWKClientConnectionError:
        raise HTTPException(503, "Autenticação temporariamente indisponível") from None
    except (jwt.PyJWTError, ValueError, TypeError, KeyError):
        raise HTTPException(401, "Sessão inválida ou expirada") from None
