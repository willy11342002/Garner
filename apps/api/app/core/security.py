from jose import jwt

ALGORITHM = "HS256"


def decode_token(token: str, secret: str) -> dict:
    return jwt.decode(token, secret, algorithms=[ALGORITHM])
