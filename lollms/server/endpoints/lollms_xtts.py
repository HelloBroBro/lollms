"""
project: lollms_webui
file: lollms_xtts.py 
author: ParisNeo
description: 
    This module contains a set of FastAPI routes that provide information about the Lord of Large Language and Multimodal Systems (LoLLMs) Web UI
    application. These routes allow users to 

"""
from fastapi import APIRouter, Request, UploadFile, File, HTTPException
from lollms_webui import LOLLMSWebUI
from pydantic import BaseModel
from starlette.responses import StreamingResponse
from lollms.types import MSG_TYPE
from lollms.main_config import BaseConfig
from lollms.utilities import detect_antiprompt, remove_text_from_string, trace_exception, find_first_available_file_index, add_period, PackageManager
from lollms.security import sanitize_path, validate_path
from pathlib import Path
from ascii_colors import ASCIIColors
import os
import platform

# ----------------------- Defining router and main class ------------------------------

router = APIRouter()
lollmsElfServer:LOLLMSWebUI = LOLLMSWebUI.get_instance()


# ----------------------- voice ------------------------------

@router.get("/list_voices")
def list_voices():
    if lollmsElfServer.config.headless_server_mode:
        return {"status":False,"error":"Code execution is blocked when in headless mode for obvious security reasons!"}

    if lollmsElfServer.config.host!="localhost" and lollmsElfServer.config.host!="127.0.0.1":
        return {"status":False,"error":"Code execution is blocked when the server is exposed outside for very obvious reasons!"}

    ASCIIColors.yellow("Listing voices")
    voices=["main_voice"]
    voices_dir:Path=lollmsElfServer.lollms_paths.custom_voices_path
    voices += [v.stem for v in voices_dir.iterdir() if v.suffix==".wav"]
    return {"voices":voices}

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
        request.fn = os.path.realpath(str((lollmsElfServer.lollms_paths.personal_outputs_path/"audio_out")/request.fn))
        validate_path(request.fn,[str(lollmsElfServer.lollms_paths.personal_outputs_path/"audio_out")])
        
    try:
        # Get the JSON data from the POST request.
        try:
            from lollms.services.xtts.lollms_xtts import LollmsXTTS
            voice=lollmsElfServer.config.xtts_current_voice
            if lollmsElfServer.tts is None:
                voice=lollmsElfServer.config.xtts_current_voice
                if voice!="main_voice":
                    voices_folder = lollmsElfServer.lollms_paths.custom_voices_path
                else:
                    voices_folder = Path(__file__).parent.parent.parent/"services/xtts/voices"

                lollmsElfServer.tts = LollmsXTTS(
                    lollmsElfServer, 
                    voices_folder=voices_folder,
                    voice_samples_path=Path(__file__).parent/"voices", 
                    xtts_base_url= lollmsElfServer.config.xtts_base_url,
                    use_deep_speed= lollmsElfServer.config.xtts_use_deep_speed,
                    use_streaming_mode= lollmsElfServer.config.xtts_use_streaming_mode,
                )
        except Exception as ex:
            return {"url": None, "error":f"{ex}"}
            
        voice=lollmsElfServer.config.xtts_current_voice if request.voice is None else request.voice
        index = find_first_available_file_index(lollmsElfServer.tts.output_folder, "voice_sample_",".wav")
        output_fn=f"voice_sample_{index}.wav" if request.fn is None else request.fn
        if voice is None:
            voice = "main_voice"
        lollmsElfServer.info("Starting to build voice")
        try:
            from lollms.services.xtts.lollms_xtts import LollmsXTTS
            if voice!="main_voice":
                voices_folder = lollmsElfServer.lollms_paths.custom_voices_path
            else:
                voices_folder = Path(__file__).parent.parent.parent/"services/xtts/voices"
            if lollmsElfServer.tts is None:
                lollmsElfServer.tts = LollmsXTTS(
                                                    lollmsElfServer, 
                                                    voices_folder=voices_folder,
                                                    voice_samples_path=Path(__file__).parent/"voices", 
                                                    xtts_base_url= lollmsElfServer.config.xtts_base_url,
                                                    use_deep_speed=lollmsElfServer.config.xtts_use_deepspeed,
                                                    use_streaming_mode=lollmsElfServer.config.xtts_use_streaming_mode                                                    
                                                )
            if lollmsElfServer.tts.ready:
                language = lollmsElfServer.config.xtts_current_language# convert_language_name()
                lollmsElfServer.tts.set_speaker_folder(voices_folder)
                url = f"audio/{output_fn}"
                preprocessed_text= add_period(request.text)
                voice_file =  [v for v in voices_folder.iterdir() if v.stem==voice and v.suffix==".wav"]
                if len(voice_file)==0:
                    return {"status":False,"error":"Voice not found"}
                if not lollmsElfServer.config.xtts_use_streaming_mode:
                    lollmsElfServer.tts.tts_to_file(preprocessed_text, voice_file[0].name, f"{output_fn}", language=language)
                    lollmsElfServer.info(f"Voice file ready at {url}")
                else:
                    lollmsElfServer.tts.tts_to_audio(preprocessed_text, voice_file[0].name, f"{output_fn}", language=language)
            else:
                lollmsElfServer.InfoMessage("xtts is not up yet.\nPlease wait for it to load then try again. This may take some time.") 
                return  {"status":False, "error":"Service not ready yet"} 
            return {"url": url}
        except Exception as ex:
            trace_exception(ex)
            return {"url": None}
    except Exception as ex:
        trace_exception(ex)
        lollmsElfServer.error(ex)
        return {"status":False,"error":str(ex)}
    
@router.get("/install_xtts")
def install_xtts():
    try:
        if lollmsElfServer.config.headless_server_mode:
            return {"status":False,"error":"Service installation is blocked when in headless mode for obvious security reasons!"}

        if lollmsElfServer.config.host!="localhost" and lollmsElfServer.config.host!="127.0.0.1":
            return {"status":False,"error":"Service installation is blocked when the server is exposed outside for very obvious reasons!"}
        
        from lollms.services.xtts.lollms_xtts import install_xtts
        lollmsElfServer.ShowBlockingMessage("Installing xTTS api server\nPlease stand by")
        install_xtts(lollmsElfServer)
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
                voices_folder=voices_folder,
                voice_samples_path=Path(__file__).parent/"voices", 
                xtts_base_url= lollmsElfServer.config.xtts_base_url,
                use_deep_speed=lollmsElfServer.config.xtts_use_deepspeed,
                use_streaming_mode=lollmsElfServer.config.xtts_use_streaming_mode                                                    
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