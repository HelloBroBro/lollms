"""
project: lollms_webui
file: lollms_diffusers.py 
author: ParisNeo
description: 
    This module is for diffusers installation and management

"""
from fastapi import APIRouter, Request
from lollms.server.elf_server import LOLLMSElfServer
from pydantic import BaseModel, ConfigDict
from starlette.responses import StreamingResponse
from lollms.types import MSG_OPERATION_TYPE
from lollms.main_config import BaseConfig
from lollms.utilities import detect_antiprompt, remove_text_from_string, trace_exception, find_first_available_file_index, add_period, PackageManager
from lollms.security import check_access
from pathlib import Path
from ascii_colors import ASCIIColors
import os
import platform

# ----------------------- Defining router and main class ------------------------------

router = APIRouter()
lollmsElfServer:LOLLMSElfServer = LOLLMSElfServer.get_instance()

class Identification(BaseModel):
    client_id: str
class ModelPost(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    client_id: str
    model_url: str
# ----------------------- voice ------------------------------

@router.post("/install_diffusers")
# async def your_endpoint(request: Request):
#     request_data = await request.json()
#     print(request_data)  # Use proper logging in real applications
def install_diffusers(data: Identification):
    check_access(lollmsElfServer, data.client_id)
    try:
        if lollmsElfServer.config.headless_server_mode:
            return {"status":False,"error":"Service installation is blocked when in headless mode for obvious security reasons!"}

        if lollmsElfServer.config.host!="localhost" and lollmsElfServer.config.host!="127.0.0.1":
            return {"status":False,"error":"Service installation is blocked when the server is exposed outside for very obvious reasons!"}

        lollmsElfServer.ShowBlockingMessage("Installing Diffusers library\nPlease stand by")
        from lollms.services.tti.diffusers.lollms_diffusers import install_diffusers
        install_diffusers(lollmsElfServer)
        ASCIIColors.success("Done")
        lollmsElfServer.HideBlockingMessage()
        return {"status":True}
    except Exception as ex:
        lollmsElfServer.HideBlockingMessage()
        lollmsElfServer.InfoMessage(f"It looks like I could not install SD because of this error:\n{ex}\nThis is commonly caused by a previous version that I couldn't delete. PLease remove {lollmsElfServer.lollms_paths.personal_path}/shared/auto_sd manually then try again")
        return {"status":False, 'error':str(ex)}


@router.post("/upgrade_diffusers")
def upgrade_sd(data: Identification):
    check_access(lollmsElfServer, data.client_id)
    try:
        if lollmsElfServer.config.headless_server_mode:
            return {"status":False,"error":"Service installation is blocked when in headless mode for obvious security reasons!"}

        if lollmsElfServer.config.host!="localhost" and lollmsElfServer.config.host!="127.0.0.1":
            return {"status":False,"error":"Service installation is blocked when the server is exposed outside for very obvious reasons!"}

        lollmsElfServer.ShowBlockingMessage("Upgrading Diffusers library\nPlease stand by")
        from lollms.services.tti.diffusers.lollms_diffusers import upgrade_diffusers
        upgrade_diffusers(lollmsElfServer)
        ASCIIColors.success("Done")
        lollmsElfServer.HideBlockingMessage()
        return {"status":True}
    except Exception as ex:
        lollmsElfServer.HideBlockingMessage()
        lollmsElfServer.InfoMessage(f"It looks like I could not install SD because of this error:\n{ex}\nThis is commonly caused by a previous version that I couldn't delete. PLease remove {lollmsElfServer.lollms_paths.personal_path}/shared/auto_sd manually then try again")
        return {"status":False, 'error':str(ex)}

@router.post("/install_diffusers_model")
def install_model(data: ModelPost):
    check_access(lollmsElfServer, data.client_id)
