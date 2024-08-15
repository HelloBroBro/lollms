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
from starlette.responses import StreamingResponse
from lollms.security import check_access
from lollms.types import MSG_OPERATION_TYPE
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

@router.post("/install_motion_ctrl")
def install_motion_ctrl(request: ClientAuthentication):
    check_access(lollmsElfServer, request.client_id)
    try:
        if lollmsElfServer.config.headless_server_mode:
            return {"status":False,"error":"Service installation is blocked when in headless mode for obvious security reasons!"}

        if lollmsElfServer.config.host!="localhost" and lollmsElfServer.config.host!="127.0.0.1":
            return {"status":False,"error":"Service installation is blocked when the server is exposed outside for very obvious reasons!"}

        lollmsElfServer.ShowBlockingMessage("Installing Motion Ctrl api server\nPlease stand by")
        from lollms.services.motion_ctrl.lollms_motion_ctrl import install_motion_ctrl
        install_motion_ctrl(lollmsElfServer)
        ASCIIColors.success("Done")
        lollmsElfServer.HideBlockingMessage()
        return {"status":True}
    except Exception as ex:
        lollmsElfServer.HideBlockingMessage()
        return {"status":False, 'error':str(ex)}