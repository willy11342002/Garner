import jwt
from jwt import PyJWKClient

_jwks_clients: dict[str, PyJWKClient] = {}


def _get_jwks_client(supabase_url: str) -> PyJWKClient:
    if supabase_url not in _jwks_clients:
        jwks_url = f"{supabase_url}/auth/v1/.well-known/jwks.json"
        _jwks_clients[supabase_url] = PyJWKClient(jwks_url, cache_keys=True)
    return _jwks_clients[supabase_url]


def decode_token(token: str, supabase_url: str) -> dict:
    client = _get_jwks_client(supabase_url)
    signing_key = client.get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["ES256", "RS256", "HS256"],
        options={"verify_aud": False},
    )
