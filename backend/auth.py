import sys
from pathlib import Path

# Ensure root project directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import jwt
import time
import secrets
from typing import Optional, Dict, Any
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.db import get_db, hash_password

JWT_SECRET = "ecotrack_jwt_secret_key_2026_super_secure"
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_SECONDS = 86400 * 7 # 7 days validity

security_bearer = HTTPBearer(auto_error=False)

def create_access_token(user_id: int, role: str, username: str) -> str:
    payload = {
        "user_id": user_id,
        "role": role,
        "username": username,
        "exp": int(time.time()) + JWT_EXPIRE_SECONDS,
        "iat": int(time.time())
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired. Please log in again.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token.")

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer)) -> Dict[str, Any]:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication token required.")
    
    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("user_id")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, full_name, role, points, is_blocked, profile_pic, bio, location FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found.")
    
    user_dict = dict(user)
    if user_dict.get("is_blocked"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your account has been suspended by an administrator.")
    
    return user_dict

def get_optional_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer)) -> Optional[Dict[str, Any]]:
    if not credentials:
        return None
    try:
        return get_current_user(credentials)
    except Exception:
        return None

def get_admin_user(current_user: Dict[str, Any] = Security(get_current_user)) -> Dict[str, Any]:
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. Administrator privileges required.")
    return current_user

def generate_reset_token() -> str:
    return secrets.token_urlsafe(32)
