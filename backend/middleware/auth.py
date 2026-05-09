import os
from typing import Any, cast
import requests

from fastapi import HTTPException
from starlette.requests import Request

from model.model import User
from utils.database import SessionLocal
from utils.jwt_services import JWTService

from supabase.client import Client
from dotenv import load_dotenv

load_dotenv()


def _extract_value(source: Any, field_name: str) -> Any:
    if source is None:
        return None

    if isinstance(source, dict):
        payload = cast(dict[str, Any], source)
        return payload.get(field_name)

    return getattr(source, field_name, None)


_supabase_url = os.getenv("VITE_SUPABASE_URL")
_publishable_key = (
    os.getenv("VITE_SUPABASE_PUBLISHABLE_KEY")
    or os.getenv("SUPABASE_ANON_KEY")
)

print("[auth] Supabase URL:", _supabase_url)

if _publishable_key:
    print(
        "[auth] Publishable key preview:",
        _publishable_key[:8] + "..." + _publishable_key[-4:],
    )


supabase = None

if _supabase_url and _publishable_key:
    try:
        supabase = Client(
            supabase_url=_supabase_url,
            supabase_key=_publishable_key,
        )

        print("[auth] Supabase client initialized")

    except Exception as e:
        print("[auth] Failed to initialize Supabase client:", e)
        supabase = None


def Verify_User(req: Request) -> User:
    authorization = req.headers.get("authorization")

    print("authorization header:", authorization)

    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")

    db = SessionLocal()
    jwt_service = JWTService()

    try:
        token = authorization.split(" ")[1]

        print("token:", token)

        user = None
        user_id_value = None

        # Try Supabase SDK first
        if supabase is not None:
            try:
                fetched = supabase.auth.get_user(token)

                oauth_payload = _extract_value(fetched, "user") or fetched

                print("oauth payload:", oauth_payload)

                user_id_value = (
                    _extract_value(oauth_payload, "id")
                    or _extract_value(oauth_payload, "sub")
                )

            except Exception as e:
                print("[auth] supabase.auth.get_user failed:", e)

        # Try REST fallback
        if not user_id_value and _supabase_url:
            try:
                url = f"{_supabase_url.rstrip('/')}/auth/v1/user"

                resp = requests.get(
                    url,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "apikey": _publishable_key,
                    },
                    timeout=5,
                )

                print("[auth] REST status:", resp.status_code)

                if resp.status_code == 200:
                    user_json = resp.json()

                    user = user_json

                    user_id_value = (
                        user_json.get("id")
                        or user_json.get("sub")
                    )

                    print("user from REST:", user_json)

                else:
                    print("[auth] REST error:", resp.text)

            except Exception as e:
                print("[auth] REST failed:", e)

        # JWT fallback
        if not user_id_value:
            user = jwt_service.decode_token(token)

            print("user from token:", user)

            user_id_value = (
                user.get("sub")
                or user.get("id")
                or user.get("user_id")
            )

        if not user_id_value:
            raise HTTPException(
                status_code=401,
                detail="Invalid token payload",
            )

        user_id = cast(str, user_id_value)

        existing_user = (
            db.query(User)
            .filter(User.id == user_id)
            .first()
        )

        print("existing_user:", existing_user)

        # User already exists
        if existing_user:
            return existing_user

        # Create user from JWT payload
        metadata = user.get("user_metadata", {}) if user else {}
        app_metadata = user.get("app_metadata", {}) if user else {}

        new_user = User(
            id=user_id,
            email=user.get("email") if user else None,
            provider=app_metadata.get("provider"),
            name=(
                metadata.get("full_name")
                or metadata.get("name")
                or metadata.get("user_name")
            ),
        )

        db.add(new_user)

        db.commit()

        db.refresh(new_user)

        print("new user created:", new_user)

        return new_user

    except HTTPException:
        raise

    except Exception as e:
        print("Verify_User error:", e)

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )

    finally:
        db.close()