import jwt
import os
from datetime import datetime, timedelta

from fastapi import HTTPException
from jose import JWTError

class JWTService:
    def __init__(self, secret_key: str | None = None, algorithm: str | None = None):
        self.secret_key = secret_key or os.getenv("SECRET")
        self.algorithm = algorithm or os.getenv("ALGORITHM")

        if not self.secret_key or not self.algorithm:
            raise HTTPException(status_code=500, detail="JWT secret or algorithm is missing")

    def create_token(self, user_id: str):
        payload = {
            "sub": user_id,
            "exp": datetime.utcnow() + timedelta(days=1)
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str) -> dict[str, object]:
        try:

            decoded = jwt.decode(token, options={"verify_signature": False})

            print(decoded)
            return decoded
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")
