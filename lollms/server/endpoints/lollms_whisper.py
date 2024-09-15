"""
project: lollms_webui
file: lollms_xtts.py 
author: ParisNeo
description: 
    This module contains a set of FastAPI routes that provide information about the Lord of Large Language and Multimodal Systems (LoLLMs) Web UI
    application. These routes allow users to 

"""
from fastapi import APIRouter, Request, UploadFile, File, HTTPException
from fastapi.responses import PlainTextResponse
from lollms_webui import LOLLMSWebUI
from pydantic import BaseModel
from starlette.responses import StreamingResponse
from lollms.types import MSG_OPERATION_TYPE
from lollms.main_config import BaseConfig
from lollms.utilities import find_next_available_filename, output_file_path_to_url, detect_antiprompt, remove_text_from_string, trace_exception, find_first_available_file_index, add_period, PackageManager
from lollms.security import sanitize_path, validate_path, check_access
from pathlib import Path
from ascii_colors import ASCIIColors
import os
import platform

# ----------------------- Defining router and main class ------------------------------

router = APIRouter()
lollmsElfServer:LOLLMSWebUI = LOLLMSWebUI.get_instance()

class Identification(BaseModel):
    client_id: str

# ----------------------- voice ------------------------------
@router.post("/install_whisper")
def install_whisper(data: Identification):
    check_access(lollmsElfServer, data.client_id)
    try:
        if lollmsElfServer.config.headless_server_mode:
            return {"status":False,"error":"Service installation is blocked when in headless mode for obvious security reasons!"}

        if lollmsElfServer.config.host!="localhost" and lollmsElfServer.config.host!="127.0.0.1":
            return {"status":False,"error":"Service installation is blocked when the server is exposed outside for very obvious reasons!"}

        lollmsElfServer.ShowBlockingMessage("Installing whisper library\nPlease stand by")
        from lollms.services.stt.whisper.lollms_whisper import install_whisper
        install_whisper(lollmsElfServer)
        ASCIIColors.success("Done")
        lollmsElfServer.HideBlockingMessage()
        return {"status":True}
    except Exception as ex:
        lollmsElfServer.HideBlockingMessage()
        lollmsElfServer.InfoMessage(f"It looks like I could not install whisper because of this error:\n{ex}")
        return {"status":False, 'error':str(ex)}
