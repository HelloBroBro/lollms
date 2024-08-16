"""
project: lollms_webui
file: lollms_rag.py 
author: ParisNeo
description: 
    This module contains a set of FastAPI routes that allow users to interact with the RAG (Retrieval-Augmented Generation) library.

Usage:
    1. Initialize the RAG system by adding documents using the /add_document endpoint.
    2. Build the index using the /index_database endpoint.
    3. Perform searches using the /search endpoint.
    4. Remove documents using the /remove_document/{document_id} endpoint.
    5. Wipe the entire database using the /wipe_database endpoint.

Authentication:
    - If lollms_access_keys are specified in the configuration, API key authentication is required.
    - If no keys are specified, authentication is bypassed, and all users are treated as user ID 1.

User Management:
    - Each user gets a unique vectorizer based on their API key.
    - If no API keys are specified, all requests are treated as coming from user ID 1.

Note: Ensure proper security measures are in place when deploying this API in a production environment.
"""

from fastapi import APIRouter, Request, HTTPException, Depends, Header
from lollms_webui import LOLLMSWebUI
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse
from lollms.types import MSG_OPERATION_TYPE
from lollms.utilities import detect_antiprompt, remove_text_from_string, trace_exception
from lollms.security import sanitize_path, check_access
from ascii_colors import ASCIIColors
from lollms.databases.discussions_database import DiscussionsDB, Discussion
from typing import List, Optional, Union
from pathlib import Path
from fastapi.security import APIKeyHeader
from lollmsvectordb.database_elements.chunk import Chunk
from lollmsvectordb.vector_database import VectorDatabase
from lollmsvectordb.lollms_vectorizers.bert_vectorizer import BERTVectorizer
from lollmsvectordb.lollms_vectorizers.tfidf_vectorizer import TFIDFVectorizer
import sqlite3
import secrets
import time
import shutil
import os
from datetime import datetime, timedelta
import asyncio
from contextlib import asynccontextmanager
import hashlib

# ----------------------- Defining router and main class ------------------------------

router = APIRouter()
lollmsElfServer: LOLLMSWebUI = LOLLMSWebUI.get_instance()
api_key_header = APIKeyHeader(name="Authorization")

# ----------------------- RAG System ------------------------------

class RAGQuery(BaseModel):
    query: str = Field(..., description="The query to process using RAG")

class RAGResponse(BaseModel):
    answer: str = Field(..., description="The generated answer")
    sources: List[str] = Field(..., description="List of sources used for the answer")

class IndexDocument(BaseModel):
    title: str = Field(..., description="The title of the document")
    content: str = Field(..., description="The content to be indexed")
    path: str = Field(default="unknown", description="The path of the document")

class IndexResponse(BaseModel):
    success: bool = Field(..., description="Indicates if the indexing was successful")
    message: str = Field(..., description="Additional information about the indexing process")

class DocumentResponse(BaseModel):
    success: bool
    message: str

class RAGChunk(BaseModel):
    id : int
    chunk_id : int
    doc_title : str
    doc_path : str
    text : str
    nb_tokens : int
    distance : float

def get_user_id(bearer_key: str) -> int:
    """
    Determine the user ID based on the bearer key.
    If no keys are specified in the configuration, always return 1.
    """
    if not lollmsElfServer.config.lollms_access_keys:
        return 1
    # Use the index of the key in the list as the user ID
    try:
        return lollmsElfServer.config.lollms_access_keys.index(bearer_key) + 1
    except ValueError:
        raise HTTPException(status_code=403, detail="Invalid API Key")

def get_user_vectorizer(user_id: int, bearer_key: str):
    small_key = hashlib.md5(bearer_key.encode()).hexdigest()[:8]
    user_folder = lollmsElfServer.lollms_paths / str(user_id)
    user_folder.mkdir(parents=True, exist_ok=True)
    return VectorDatabase(
        str(user_folder / f"rag_db_{small_key}.sqlite"),
        BERTVectorizer(lollmsElfServer.config.rag_vectorizer_model) if lollmsElfServer.config.rag_vectorizer == "bert" else TFIDFVectorizer(),
        lollmsElfServer.model,
        chunk_size=lollmsElfServer.config.rag_chunk_size,
        overlap=lollmsElfServer.config.rag_overlap
    )

async def get_current_user(bearer_token: str = Depends(api_key_header)):
    if lollmsElfServer.config.lollms_access_keys:
        if bearer_token not in lollmsElfServer.config.lollms_access_keys:
            raise HTTPException(status_code=403, detail="Invalid API Key")
    return bearer_token

@router.post("/add_document", response_model=DocumentResponse)
async def add_document(doc: IndexDocument, user: str = Depends(get_current_user)):
    user_id = get_user_id(user)
    vectorizer = get_user_vectorizer(user_id, user)
    vectorizer.add_document(title=doc.title, text=doc.content, path=doc.path)
    return DocumentResponse(success=True, message="Document added successfully.")

@router.post("/remove_document/{document_id}", response_model=DocumentResponse)
async def remove_document(document_id: int, user: str = Depends(get_current_user)):
    user_id = get_user_id(user)
    vectorizer = get_user_vectorizer(user_id, user)
    doc_hash = vectorizer.get_document_hash(document_id)
    vectorizer.remove_document(doc_hash)
    # Logic to remove the document by ID
    return DocumentResponse(success=True, message="Document removed successfully.")

@router.post("/index_database", response_model=DocumentResponse)
async def index_database(user: str = Depends(get_current_user)):
    user_id = get_user_id(user)
    vectorizer = get_user_vectorizer(user_id, user)
    vectorizer.build_index()
    return DocumentResponse(success=True, message="Database indexed successfully.")

@router.post("/search", response_model=List[RAGChunk])
async def search(query: RAGQuery, user: str = Depends(get_current_user)):
    user_id = get_user_id(user)
    vectorizer = get_user_vectorizer(user_id, user)
    chunks = vectorizer.search(query.query)
    return [RAGChunk(c.id,c.chunk_id, c.doc.title, c.doc.path, c.text, c.nb_tokens, c.distance) for c in chunks]

@router.delete("/wipe_database", response_model=DocumentResponse)
async def wipe_database(user: str = Depends(get_current_user)):
    user_id = get_user_id(user)
    user_folder = lollmsElfServer.lollms_paths / str(user_id)
    shutil.rmtree(user_folder, ignore_errors=True)
    return DocumentResponse(success=True, message="Database wiped successfully.")
