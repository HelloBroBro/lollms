"""
project: lollms_webui
file: lollms_xtts.py 
author: ParisNeo
description: 
    This module contains a set of FastAPI routes that provide information about the Lord of Large Language and Multimodal Systems (LoLLMs) Web UI
    application. These routes allow users to 

"""
from fastapi import APIRouter, Request
from lollms_webui import LOLLMSWebUI
from pydantic import BaseModel
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


# ----------------------- voice ------------------------------

@router.get("/install_comfyui")
def install_comfyui():
    try:
        if lollmsElfServer.config.headless_server_mode:
            return {"status":False,"error":"Service installation is blocked when in headless mode for obvious security reasons!"}

        if lollmsElfServer.config.host!="localhost" and lollmsElfServer.config.host!="127.0.0.1":
            return {"status":False,"error":"Service installation is blocked when the server is exposed outside for very obvious reasons!"}

        lollmsElfServer.ShowBlockingMessage("Installing  comfyui server\nPlease stand by")
        from lollms.services.comfyui.lollms_comfyui import install_comfyui
        install_comfyui(lollmsElfServer)
        ASCIIColors.success("Done")
        lollmsElfServer.HideBlockingMessage()
        return {"status":True}
    except Exception as ex:
        lollmsElfServer.HideBlockingMessage()
        lollmsElfServer.InfoMessage(f"It looks like I could not install Comfyui because of this error:\n{ex}\nThis is commonly caused by a previous version that I couldn't delete. PLease remove {lollmsElfServer.lollms_paths.personal_path}/shared/comfyui manually then try again")
        return {"status":False, 'error':str(ex)}

@router.get("/start_comfyui")
def start_comfyui():
    try:
        if lollmsElfServer.config.headless_server_mode:
            return {"status":False,"error":"Service installation is blocked when in headless mode for obvious security reasons!"}

        if lollmsElfServer.config.host!="localhost" and lollmsElfServer.config.host!="127.0.0.1":
            return {"status":False,"error":"Service installation is blocked when the server is exposed outside for very obvious reasons!"}

        lollmsElfServer.ShowBlockingMessage("Starting Comfyui\nPlease stand by")
        from lollms.services.comfyui.lollms_comfyui import get_comfyui
        lollmsElfServer.comfyui = get_comfyui(lollmsElfServer.lollms_paths)(lollmsElfServer, lollmsElfServer.personality.name if lollmsElfServer.personality is not None else "Artbot")
        ASCIIColors.success("Done")
        lollmsElfServer.HideBlockingMessage()
        return {"status":True}
    except Exception as ex:
        lollmsElfServer.HideBlockingMessage()
        lollmsElfServer.InfoMessage(f"It looks like I could not install comfyui because of this error:\n{ex}\nThis is commonly caused by a previous version that I couldn't delete. PLease remove {lollmsElfServer.lollms_paths.personal_path}/shared/comfyui manually then try again")
        return {"status":False, 'error':str(ex)}

@router.get("/show_comfyui")
def show_comfyui():
    import webbrowser
    webbrowser.open(lollmsElfServer.config.comfyui_base_url)
    return {"status":True}