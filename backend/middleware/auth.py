import os
from fastapi import HTTPException, FastAPI
from starlette.requests import Request
from jose import jwt,JWTError   
from model.model import User
from utils.database import SessionLocal
from utils.jwt_services import JWTService
from supabase.client import Client, ClientOptions

db = SessionLocal

supabase = Client(
    supabase_key=os.getenv("VITE_SUPABASE_PUBLISHABLE_KEY"),
    supabase_url=os.getenv("VITE_SUPABASE_URL")
)

admin_api = supabase.auth.admin

def Verify_User(req:Request):
    authorization = req.headers.get("authorization")

    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        token = authorization.split(" ")[1]

        user = JWTService.decode_token(token)

        isAuthenticated = db.query(User).filter(User.id == user.id)

        if not isAuthenticated:
            oauth_user = admin_api.get_user_by_id(user.id)

            user = User(oauth_user)

            db.add(user)

            db.commit()
            db.refresh(user)

            db.close()
            return user


        return isAuthenticated



