"""
project: lollms_webui
file: lollms_authentication.py 
author: ParisNeo
description: 
    This module contains a set of FastAPI routes that manages users authentication.
"""

from fastapi import APIRouter, Request, HTTPException, Depends, Header
from lollms_webui import LOLLMSWebUI
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse
from lollms.types import MSG_OPERATION_TYPE
from lollms.utilities import detect_antiprompt, remove_text_from_string, trace_exception
from lollms.security import sanitize_path, check_access
from ascii_colors import ASCIColors
from lollms.databases.discussions_database import DiscussionsDB, Discussion
from typing import List, Optional, Union
from pathlib import Path
from fastapi.security import APIKeyHeader

import sqlite3
import secrets
import time
import shutil
import os
from datetime import datetime, timedelta
import asyncio
from contextlib import asynccontextmanager

# ----------------------- Defining router and main class ------------------------------

router = APIRouter()
lollmsElfServer: LOLLMSWebUI = LOLLMSWebUI.get_instance()

# ----------------------- User Authentication and Management ------------------------------

class User(BaseModel):
    id: int
    username: str
    email: str
    password: str
    last_activity: float
    database_name: str  # Added field for database name

class UserAuth(BaseModel):
    username: str
    password: str
    email: str

class UserToken(BaseModel):
    token: str
    expiry: float

users_db_path = lollmsElfServer.lollms_paths.personal_configuration_path / "users.sqlite"
user_tokens = {}

def init_users_db():
    conn = sqlite3.connect(str(users_db_path))
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users
                      (id INTEGER PRIMARY KEY, username TEXT UNIQUE, email TEXT, password TEXT, last_activity REAL, database_name TEXT)''')
    conn.commit()
    conn.close()

def get_user(username: str) -> Optional[User]:
    conn = sqlite3.connect(str(users_db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user_data = cursor.fetchone()
    conn.close()
    if user_data:
        return User(id=user_data[0], username=user_data[1], email=user_data[2], password=user_data[3], last_activity=user_data[4], database_name=user_data[5])
    return None

def create_user(username: str, email: str, password: str, database_name: str):
    conn = sqlite3.connect(str(users_db_path))
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, email, password, last_activity, database_name) VALUES (?, ?, ?, ?, ?)",
                       (username, email, password, time.time(), database_name))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Username already exists")
    conn.close()

def update_user_activity(username: str):
    conn = sqlite3.connect(str(users_db_path))
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET last_activity = ? WHERE username = ?", (time.time(), username))
    conn.commit()
    conn.close()

def authenticate_user(username: str, password: str) -> Optional[str]:
    user = get_user(username)
    if user and user.password == password:
        token = secrets.token_urlsafe(32)
        expiry = time.time() + 3600  # Token valid for 1 hour
        user_tokens[token] = UserToken(token=token, expiry=expiry)
        update_user_activity(username)
        return token
    return None

async def get_current_user(token: str = Header(...)):
    if token not in user_tokens or user_tokens[token].expiry < time.time():
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return token

# ----------------------- Lifespan Event Handler ------------------------------

@asynccontextmanager
async def lifespan(app):
    # Startup
    init_users_db()
    yield

# Add this lifespan event handler to your FastAPI app
# app.router.lifespan_context = lifespan

# ----------------------- Endpoints ------------------------------

@router.post("/register", response_model=User)
async def register(user: UserAuth):
    # Generate a unique database name for the user
    database_name = f"{user.username}_db.sqlite"
    create_user(user.username, user.email, user.password, database_name)
    return get_user(user.username)

@router.post("/login", response_model=UserToken)
async def login(user: UserAuth):
    token = authenticate_user(user.username, user.password)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    user_data = get_user(user.username)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    # Load the user's discussion database
    user_discussion_db = DiscussionsDB(lollmsElfServer.lollms_paths, user_data.database_name)
    discussion = user_discussion_db.load_discussion_by_id(user_data.id)  # Assuming ID is used to load the discussion
    lollmsElfServer.session.add_client(token, 0, discussion, user_discussion_db)
    
    return UserToken(token=token, expiry=user_tokens[token].expiry)

@router.get("/current_user", response_model=User)
async def current_user(token: str = Depends(get_current_user)):
    for user_token in user_tokens.values():
        if user_token.token == token:
            user = get_user(user_token.token)  # Assuming token is the username for simplicity
            if user:
                return user
    raise HTTPException(status_code=404, detail="User not found")

# Add the router to your FastAPI app
# app.include_router(router)
