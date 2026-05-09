from jose import jwt,JWTError
import os
from datetime import datetime, timedelta
from fastapi import HTTPException
from supabase.client import Client,create_client


client = Client(
    supabase_key=
    supabase_url=
)
admin_api = client.auth.admin

class JWTService:
    def __init__(self,secret_key:str,algorithm:str):
        self.secret_key = os.getenv("SECRET")
        self.algorithm = os.getenv("ALGORITHM")

    def create_token(self,user_id:str):
        payload = {
            "sub": user_id,
            "exp": datetime.utcnow() + timedelta(days=1)
        }
        return jwt.encode(payload,self.secret_key,algorithm=self.algorithm)

    def decode_token(self,token:str):
        try:
            return jwt.decode(token,self.secret_key,algorithms=[self.algorithm])
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")
