from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional
import uuid
import hashlib
import os
from datetime import datetime, timedelta
import jwt
from src.db import supabase
from src.core.config import settings


router = APIRouter()
security = HTTPBearer()


SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
ALGORITHM = "HS256"


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = "candidate"

    def __init__(self, **data):
        if data.get("role") and data["role"] not in ("candidate", "poster"):
            data["role"] = "candidate"
        super().__init__(**data)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed


def create_jwt_token(user_id: str, email: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": datetime.utcnow() + timedelta(days=7),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserResponse:
    """Get current authenticated user."""
    token = credentials.credentials
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = await supabase.supabase_client.fetchrow(
        'SELECT * FROM "users" WHERE id = $1',
        payload["sub"],
    )
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse(
        id=str(user["id"]),
        email=user["email"],
        full_name=user["full_name"],
        role=user["role"],
        is_active=user["is_active"],
        created_at=user["created_at"],
    )


@router.post("/register", response_model=TokenResponse)
async def register_user(user: UserCreate):
    """Register a new user."""
    password_hash = hash_password(user.password)
    
    existing = await supabase.supabase_client.fetchrow(
        'SELECT id FROM "users" WHERE email = $1',
        user.email,
    )
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = str(uuid.uuid4())
    await supabase.supabase_client.execute(
        '''
        INSERT INTO "users" (id, email, password_hash, full_name, role, is_active)
        VALUES ($1, $2, $3, $4, $5, true)
        ''',
        user_id,
        user.email,
        password_hash,
        user.full_name,
        user.role,
    )
    
    if user.role == "candidate":
        await supabase.supabase_client.execute(
            '''
            INSERT INTO "candidate_profiles" (user_id, full_name, phone)
            VALUES ($1, $2, $3)
            ''',
            user_id,
            user.full_name,
            user.phone,
        )
    
    created = await supabase.supabase_client.fetchrow(
        'SELECT * FROM "users" WHERE id = $1',
        user_id,
    )
    
    if not created:
        raise HTTPException(status_code=500, detail="Failed to create user")
    
    access_token = create_jwt_token(str(created["id"]), created["email"], created["role"])
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=str(created["id"]),
            email=created["email"],
            full_name=created["full_name"],
            role=created["role"],
            is_active=created["is_active"],
            created_at=created["created_at"],
        ),
    )


@router.post("/login", response_model=TokenResponse)
async def login_user(credentials: UserLogin):
    """Login user."""
    password_hash = hash_password(credentials.password)
    
    user = await supabase.supabase_client.fetchrow(
        'SELECT * FROM "users" WHERE email = $1',
        credentials.email,
    )
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="Account is disabled")
    
    access_token = create_jwt_token(str(user["id"]), user["email"], user["role"])
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=str(user["id"]),
            email=user["email"],
            full_name=user["full_name"],
            role=user["role"],
            is_active=user["is_active"],
            created_at=user["created_at"],
        ),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserResponse = Depends(get_current_user)):
    """Get current user profile."""
    return current_user


@router.post("/logout")
async def logout():
    """Logout user (client should discard token)."""
    return {"message": "Logged out successfully"}


@router.post("/create-admin")
async def create_admin_user(email: str, password: str, full_name: str = None):
    """Create admin user (use sparingly, requires secret)."""
    admin_secret = os.getenv("ADMIN_CREATE_SECRET", "")
    if not admin_secret:
        return {"error": "Admin creation not configured"}
    
    password_hash = hash_password(password)
    
    existing = await supabase.supabase_client.fetchrow(
        'SELECT id FROM "users" WHERE email = $1',
        email,
    )
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")
    
    user_id = str(uuid.uuid4())
    await supabase.supabase_client.execute(
        '''
        INSERT INTO "users" (id, email, password_hash, full_name, role, is_active)
        VALUES ($1, $2, $3, $4, $5, true)
        ''',
        user_id,
        email,
        password_hash,
        full_name,
        "admin",
    )
    
    return {"message": "Admin user created", "user_id": user_id}