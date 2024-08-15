"""
project: lollms_webui
file: lollms_xtts.py 
author: ParisNeo
description: 
    This module contains a set of FastAPI routes that concerns petals service

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

@router.post("/install_petals")
def install_petals(request: ClientAuthentication):
    check_access(lollmsElfServer, request.client_id)
    try:
        lollmsElfServer.ShowBlockingMessage("Installing petals server\nPlease stand by")
        from lollms.services.petals.lollms_petals import install_petals
        if install_petals(lollmsElfServer):
            lollmsElfServer.HideBlockingMessage()
            return {"status":True}
        else:
            return {"status":False, 'error':str(ex)}            
    except Exception as ex:
        trace_exception(ex)
        lollmsElfServer.HideBlockingMessage()
        return {"status":False, 'error':str(ex)}