"""
project: lollms_webui
file: lollms_xtts.py 
author: ParisNeo
description: 
    This module contains a set of FastAPI routes that provide information about the Lord of Large Language and Multimodal Systems (LoLLMs) Web UI
    application. These routes allow users to 

"""
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from lollms_webui import LOLLMSWebUI
from pydantic import BaseModel
from lollms.security import check_access
from starlette.responses import StreamingResponse
from lollms.types import MSG_TYPE
from lollms.main_config import BaseConfig
from lollms.utilities import detect_antiprompt, remove_text_from_string, trace_exception, find_first_available_file_index, add_period, PackageManager
from pathlib import Path
from ascii_colors import ASCIIColors
import os
import platform

# ----------------------- Defining router and main class ------------------------------

router = APIRouter()
lollmsElfServer:LOLLMSWebUI = LOLLMSWebUI.get_instance()

class ClientAuthentication(BaseModel):
    client_id: str  = Field(...)
# ----------------------- voice ------------------------------

@router.post("/install_ollama")
def install_ollama(request: ClientAuthentication):
    check_access(lollmsElfServer, request.client_id)
    try:
        if lollmsElfServer.config.headless_server_mode:
            return {"status":False,"error":"Service installation is blocked when in headless mode for obvious security reasons!"}

        if lollmsElfServer.config.host!="localhost" and lollmsElfServer.config.host!="127.0.0.1":
            return {"status":False,"error":"Service installation is blocked when the server is exposed outside for very obvious reasons!"}

        lollmsElfServer.ShowBlockingMessage("Installing ollama server\nPlease stand by")
        from lollms.services.ollama.lollms_ollama import install_ollama
        if install_ollama(lollmsElfServer):
            lollmsElfServer.HideBlockingMessage()
            return {"status":True}
        else:
            return {"status":False, 'error':str(ex)}            
    except Exception as ex:
        trace_exception(ex)
        lollmsElfServer.HideBlockingMessage()
        return {"status":False, 'error':str(ex)}

@router.post("/start_ollama")
def start_ollama(request: ClientAuthentication):
    check_access(lollmsElfServer, request.client_id)
    try:
        if hasattr(lollmsElfServer,"vllm") and lollmsElfServer.vllm is not None:
            return {"status":False, 'error':"Service is already on"}

        if not hasattr(lollmsElfServer,"vllm") or lollmsElfServer.vllm is None:
            lollmsElfServer.ShowBlockingMessage("Loading vllm server\nPlease stand by")
            from lollms.services.vllm.lollms_vllm import get_vllm
            server = get_vllm(lollmsElfServer)

            if server:
                lollmsElfServer.vllm = server(lollmsElfServer, lollmsElfServer.config.vllm_url)
                lollmsElfServer.HideBlockingMessage()
                return {"status":True}
            else:
                return {"status":False, 'error':str(ex)}            
        else:
            return {"status":False, 'error':'Service already running'}            

    except Exception as ex:
        trace_exception(ex)
        lollmsElfServer.HideBlockingMessage()
        return {"status":False, 'error':str(ex)}