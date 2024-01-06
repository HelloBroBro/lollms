"""
File: lollms_web_ui.py
Author: ParisNeo
Description: Singleton class for the LoLLMS web UI.

This file is the entry point to the webui.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from lollms.app import LollmsApplication
from lollms.paths import LollmsPaths
from lollms.main_config import LOLLMSConfig
from lollms.server.elf_server import LOLLMSElfServer
from pathlib import Path
from ascii_colors import ASCIIColors
import socketio
import uvicorn
import argparse

app = FastAPI()
sio = socketio.AsyncServer(async_mode="asgi")

app.mount("/socket.io", socketio.ASGIApp(sio))
#app.mount("/socket.io", StaticFiles(directory="path/to/socketio.js"))


if __name__ == "__main__":
    # Parsong parameters
    parser = argparse.ArgumentParser(description="Start the chatbot FastAPI app.")
    
    parser.add_argument(
        "--host", type=str, default=None, help="the hostname to listen on"
    )
    parser.add_argument("--port", type=int, default=None, help="the port to listen on")

    args = parser.parse_args()
    root_path = Path(__file__).parent
    lollms_paths = LollmsPaths.find_paths(tool_prefix="elf_",force_local=True, custom_default_cfg_path="configs/config.yaml")
    config = LOLLMSConfig.autoload(lollms_paths)
    if args.host:
        config.host=args.host
    if args.port:
        config.port=args.port

    LOLLMSElfServer.build_instance(config=config, lollms_paths=lollms_paths, socketio=sio)
    from lollms.server.endpoints.lollms_infos import router as lollms_infos_router
    from lollms.server.endpoints.lollms_hardware_infos import router as lollms_hardware_infos_router
    from lollms.server.endpoints.lollms_binding_infos import router as lollms_binding_infos_router
    from lollms.server.endpoints.lollms_models_infos import router as lollms_models_infos_router
    from lollms.server.endpoints.lollms_personalities_infos import router as lollms_personalities_infos_router
    from lollms.server.endpoints.lollms_extensions_infos import router as lollms_extensions_infos_router
    
    
    from lollms.server.endpoints.lollms_generator import router as lollms_generator_router
    

    app.include_router(lollms_infos_router)
    app.include_router(lollms_hardware_infos_router)
    app.include_router(lollms_binding_infos_router)
    app.include_router(lollms_models_infos_router)
    app.include_router(lollms_personalities_infos_router)
    app.include_router(lollms_extensions_infos_router)
    
    
    app.include_router(lollms_generator_router)
    
    uvicorn.run(app, host=config.host, port=config.port)