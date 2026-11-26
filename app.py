"""Минимальное эталонное приложение FastAPI (хранилище в памяти).
Нужно только для того, чтобы тесты можно было запустить локально без внешнего сервера."""
import hashlib
import re
import secrets

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

app = FastAPI()

USERS: dict = {}    # username -> {"password_hash", "email", "name"}
TOKENS: dict = {}   # token -> username
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RegisterIn(BaseModel):
    username: str
    password: str
    email: str
    name: str


class LoginIn(BaseModel):
    username: str
    password: str


class ProfileUpdateIn(BaseModel):
    email: str | None = None
    name: str | None = None


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _new_token(username: str) -> str:
    token = secrets.token_urlsafe(32)
    TOKENS[token] = username
    return token


def _current_user(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    username = TOKENS.get(authorization[len("Bearer "):])
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return username


def _profile(username: str) -> dict:
    u = USERS[username]
    return {"username": username, "email": u["email"], "name": u["name"]}


@app.post("/api/register", status_code=201)
async def register(data: RegisterIn):
    if not data.username.strip() or not data.password or not data.name.strip():
        raise HTTPException(status_code=422, detail="Empty field")
    if not EMAIL_RE.match(data.email):
        raise HTTPException(status_code=422, detail="Invalid email")
    if data.username in USERS:
        raise HTTPException(status_code=409, detail="User already exists")
    USERS[data.username] = {
        "password_hash": _hash(data.password),
        "email": data.email,
        "name": data.name,
    }
    return {"access_token": _new_token(data.username), "token_type": "bearer"}


@app.post("/api/login")
async def login(data: LoginIn):
    user = USERS.get(data.username)
    if user is None or user["password_hash"] != _hash(data.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"access_token": _new_token(data.username), "token_type": "bearer"}


@app.get("/api/profile")
async def get_profile(authorization: str | None = Header(default=None)):
    return _profile(_current_user(authorization))


@app.put("/api/profile")
async def update_profile(data: ProfileUpdateIn, authorization: str | None = Header(default=None)):
    username = _current_user(authorization)
    if data.email is not None:
        if not EMAIL_RE.match(data.email):
            raise HTTPException(status_code=422, detail="Invalid email")
        USERS[username]["email"] = data.email
    if data.name is not None:
        if not data.name.strip():
            raise HTTPException(status_code=422, detail="Empty name")
        USERS[username]["name"] = data.name
    return _profile(username)
