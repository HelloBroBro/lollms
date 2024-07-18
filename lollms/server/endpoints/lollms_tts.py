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
from lollms.types import MSG_TYPE
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

@router.get("/list_voices")
def list_voices():
    if lollmsElfServer.tts is None:
        return {"status":False,"error":"TTS is not active"}

    if lollmsElfServer.config.headless_server_mode:
        return {"status":False,"error":"Code execution is blocked when in headless mode for obvious security reasons!"}

    if lollmsElfServer.config.host!="localhost" and lollmsElfServer.config.host!="127.0.0.1":
        return {"status":False,"error":"Code execution is blocked when the server is exposed outside for very obvious reasons!"}

    ASCIIColors.yellow("Listing voices")
    return {"voices":lollmsElfServer.tts.get_voices()}

@router.get("/list_stt_models")
def list_stt_models():
    if lollmsElfServer.config.headless_server_mode:
        return {"status":False,"error":"Code execution is blocked when in headless mode for obvious security reasons!"}

    if lollmsElfServer.config.host!="localhost" and lollmsElfServer.config.host!="127.0.0.1":
        return {"status":False,"error":"Code execution is blocked when the server is exposed outside for very obvious reasons!"}

    ASCIIColors.yellow("Listing voices")
    return {"voices":lollmsElfServer.stt.get_models()}

@router.get("/list_tts_models")
def list_tts_models():
    if lollmsElfServer.config.headless_server_mode:
        return {"status":False,"error":"Code execution is blocked when in headless mode for obvious security reasons!"}

    if lollmsElfServer.config.host!="localhost" and lollmsElfServer.config.host!="127.0.0.1":
        return {"status":False,"error":"Code execution is blocked when the server is exposed outside for very obvious reasons!"}

    ASCIIColors.yellow("Listing voices")
    return {"voices":lollmsElfServer.tts.get_models()}

@router.post("/set_voice")
async def set_voice(request: Request):
    """
    Changes current voice

    :param request: The HTTP request object.
    :return: A JSON response with the status of the operation.
    """
    if lollmsElfServer.config.headless_server_mode:
        return {"status":False,"error":"Code execution is blocked when in headless mode for obvious security reasons!"}

    if lollmsElfServer.config.host!="localhost" and lollmsElfServer.config.host!="127.0.0.1":
        return {"status":False,"error":"Code execution is blocked when the server is exposed outside for very obvious reasons!"}

    try:
        data = (await request.json())
        lollmsElfServer.config.xtts_current_voice=data["voice"]
        if lollmsElfServer.config.auto_save:
            lollmsElfServer.config.save_config()
        return {"status":True}
    except Exception as ex:
        trace_exception(ex)
        lollmsElfServer.error(ex)
        return {"status":False,"error":str(ex)}


class LollmsAudio2TextRequest(BaseModel):
    wave_file_path: str
    model: str = None
    fn:str = None

@router.post("/audio2text")
async def audio2text(request: LollmsAudio2TextRequest):
    if lollmsElfServer.config.headless_server_mode:
        return {"status":False,"error":"Code execution is blocked when in headless mode for obvious security reasons!"}

    if lollmsElfServer.config.host!="localhost" and lollmsElfServer.config.host!="127.0.0.1":
        return {"status":False,"error":"Code execution is blocked when the server is exposed outside for very obvious reasons!"}

    result = lollmsElfServer.whisper.transcribe(str(request.wave_file_path))
    return PlainTextResponse(result)



class LollmsText2AudioRequest(BaseModel):
    text: str
    voice: str = None
    fn:str = None

@router.post("/text2Audio")
async def text2Audio(request: LollmsText2AudioRequest):
    """
    Executes Python code and returns the output.

    :param request: The HTTP request object.
    :return: A JSON response with the status of the operation.
    """
    if lollmsElfServer.config.headless_server_mode:
        return {"status":False,"error":"Code execution is blocked when in headless mode for obvious security reasons!"}

    if lollmsElfServer.config.host!="localhost" and lollmsElfServer.config.host!="127.0.0.1":
        return {"status":False,"error":"Code execution is blocked when the server is exposed outside for very obvious reasons!"}

    if request.fn:
        request.fn = sanitize_path(request.fn)
        request.fn = (lollmsElfServer.lollms_paths.personal_outputs_path/"audio_out")/request.fn
        validate_path(request.fn,[str(lollmsElfServer.lollms_paths.personal_outputs_path/"audio_out")])
    else:
        request.fn = lollmsElfServer.lollms_paths.personal_outputs_path/"audio_out"/"tts2audio.wav"
    
    # Verify the path exists
    request.fn.parent.mkdir(exist_ok=True, parents=True)

    try:
        if lollmsElfServer.tts is None:
            return {"url": None, "error":f"No TTS service is on"}
        if lollmsElfServer.tts.ready:
            if request.voice:
                voice = request.voice
            else:
                voice = lollmsElfServer.config.xtts_current_voice
            response = lollmsElfServer.tts.tts_audio(request.text, voice, file_name_or_path=request.fn, use_threading=True)
            return response
        else:
            return {"url": None, "error":f"TTS service is not ready yet"}
    except Exception as ex:
        trace_exception(ex)
        lollmsElfServer.error(ex)
        return {"status":False,"error":str(ex)}

@router.post("/text2Wave")
async def text2Wave(request: LollmsText2AudioRequest):
    """
    Executes Python code and returns the output.

    :param request: The HTTP request object.
    :return: A JSON response with the status of the operation.
    """
    if lollmsElfServer.config.headless_server_mode:
        return {"status":False,"error":"Code execution is blocked when in headless mode for obvious security reasons!"}

    if lollmsElfServer.config.host!="localhost" and lollmsElfServer.config.host!="127.0.0.1":
        return {"status":False,"error":"Code execution is blocked when the server is exposed outside for very obvious reasons!"}

    if request.fn:
        request.fn = sanitize_path(request.fn)
        request.fn = (lollmsElfServer.lollms_paths.personal_outputs_path/"audio_out")/request.fn
        validate_path(request.fn,[str(lollmsElfServer.lollms_paths.personal_outputs_path/"audio_out")])
    else:
        request.fn = find_next_available_filename(lollmsElfServer.lollms_paths.personal_outputs_path/"audio_out", "tts_out","wave")
    # Verify the path exists
    request.fn.parent.mkdir(exist_ok=True, parents=True)

    try:
        if request.voice:
            voice = request.voice
        else:
            voice = lollmsElfServer.config.xtts_current_voice

        # Get the JSON data from the POST request.
        if lollmsElfServer.tts.ready:
            response = lollmsElfServer.tts.tts_file(request.text, request.fn, voice)
            response = output_file_path_to_url(response)
            return {"url":response}
        else:
            return {"url": None, "error":f"TTS service is not ready yet"}

    except Exception as ex:
        trace_exception(ex)
        lollmsElfServer.error(ex)
        return {"status":False,"error":str(ex)}
    

@router.post("/install_xtts")
def install_xtts(data:Identification):
    check_access(lollmsElfServer, data.client_id)
    try:
        if lollmsElfServer.config.headless_server_mode:
            return {"status":False,"error":"Service installation is blocked when in headless mode for obvious security reasons!"}

        if lollmsElfServer.config.host!="localhost" and lollmsElfServer.config.host!="127.0.0.1":
            return {"status":False,"error":"Service installation is blocked when the server is exposed outside for very obvious reasons!"}
        
        from lollms.services.xtts.lollms_xtts import LollmsXTTS
        lollmsElfServer.ShowBlockingMessage("Installing xTTS api server\nPlease stand by")
        LollmsXTTS.install(lollmsElfServer)
        lollmsElfServer.HideBlockingMessage()
        return {"status":True}
    except Exception as ex:
        trace_exception(ex)
        lollmsElfServer.HideBlockingMessage()
        return {"status":False, 'error':str(ex)}

@router.get("/start_xtts")
def start_xtts():
    try:
        lollmsElfServer.ShowBlockingMessage("Starting xTTS api server\nPlease stand by")
        from lollms.services.xtts.lollms_xtts import LollmsXTTS
        if lollmsElfServer.tts is None:
            voice=lollmsElfServer.config.xtts_current_voice
            if voice!="main_voice":
                voices_folder = lollmsElfServer.lollms_paths.custom_voices_path
            else:
                voices_folder = Path(__file__).parent.parent.parent/"services/xtts/voices"

            lollmsElfServer.tts = LollmsXTTS(
                lollmsElfServer, 
                voices_folders=[voices_folder, lollmsElfServer.lollms_paths.custom_voices_path],                                        
                freq=lollmsElfServer.config.xtts_freq
            )
        lollmsElfServer.HideBlockingMessage()
    except Exception as ex:
        trace_exception(ex)
        lollmsElfServer.HideBlockingMessage()
        return {"url": None, "error":f"{ex}"}


@router.post("/upload_voice/")
async def upload_voice_file(file: UploadFile = File(...)):
    allowed_extensions = {'wav'}

    # Use Pathlib to handle the filename
    sanitize_path(file.filename)
    file_path = Path(file.filename)
    file_extension = file_path.suffix[1:].lower()

    if file_extension not in allowed_extensions:
        return {"message": "Invalid file type. Only .wav files are allowed."}

    # Check for path traversal attempts
    if file_path.is_absolute() or any(part == '..' for part in file_path.parts):
        raise HTTPException(status_code=400, detail="Invalid filename. Path traversal detected.")

    # Save the file to disk or process it further
    contents = await file.read()
    safe_filename = f"voice_{file_path.name}"
    safe_file_path = lollmsElfServer.lollms_paths.custom_voices_path/safe_filename
    with safe_file_path.open("wb") as f:
        f.write(contents)
    lollmsElfServer.config.xtts_current_voice=safe_filename
    if lollmsElfServer.config.auto_save:
        lollmsElfServer.config.save_config()

    return {"message": f"Successfully uploaded {safe_filename}"}


@router.get("/tts_is_ready")
def tts_is_ready():
    if lollmsElfServer.tts:
        if lollmsElfServer.tts.ready:
            return {"status":True}
    return {"status":False}


@router.get("/get_snd_input_devices")
def get_snd_input_devices():
    if lollmsElfServer.stt:
        return lollmsElfServer.stt.get_devices()
    else:
        return []
@router.get("/get_snd_output_devices")
def get_snd_output_devices():
    if lollmsElfServer.tts:
        return lollmsElfServer.tts.get_devices()
    else:
        return []

