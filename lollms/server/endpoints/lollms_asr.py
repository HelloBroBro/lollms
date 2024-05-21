"""
project: lollms_webui
file: lollms_asr.py 
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

class LollmsAudio2TextRequest(BaseModel):
    text: str
    voice: str = None
    fn:str = None
# ----------------------- voice ------------------------------
@router.post("/asr/audio2test")
async def text2Audio(request: LollmsAudio2TextRequest):
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
            from lollms.services.asr.lollms_asr import LollmsASR
            voice=lollmsElfServer.config.asr_current_voice
            if lollmsElfServer.asr is None:
                voice=lollmsElfServer.config.asr_current_voice
                if voice!="main_voice":
                    voices_folder = lollmsElfServer.lollms_paths.custom_voices_path
                else:
                    voices_folder = Path(__file__).parent.parent.parent/"services/asr/voices"

                lollmsElfServer.asr = LollmsASR(
                    lollmsElfServer, 
                    voices_folder=voices_folder,
                    voice_samples_path=Path(__file__).parent/"voices", 
                    asr_base_url= lollmsElfServer.config.asr_base_url
                )
        except Exception as ex:
            return {"url": None, "error":f"{ex}"}
            
        voice=lollmsElfServer.config.asr_current_voice if request.voice is None else request.voice
        index = find_first_available_file_index(lollmsElfServer.asr.output_folder, "voice_sample_",".wav")
        output_fn=f"voice_sample_{index}.wav" if request.fn is None else request.fn
        if voice is None:
            voice = "main_voice"
        lollmsElfServer.info("Starting to build voice")
        try:
            from lollms.services.asr.lollms_asr import LollmsASR
            # If the personality has a voice, then use it
            personality_audio:Path = lollmsElfServer.personality.personality_package_path/"audio"
            if personality_audio.exists() and len([v for v in personality_audio.iterdir()])>0:
                voices_folder = personality_audio
            elif voice!="main_voice":
                voices_folder = lollmsElfServer.lollms_paths.custom_voices_path
            else:
                voices_folder = Path(__file__).parent.parent.parent/"services/asr/voices"
            if lollmsElfServer.asr is None:
                lollmsElfServer.asr = LollmsASR(
                                                    lollmsElfServer, 
                                                    voices_folder=voices_folder,
                                                    voice_samples_path=Path(__file__).parent/"voices", 
                                                    asr_base_url= lollmsElfServer.config.asr_base_url,                                         
                                                )
            if lollmsElfServer.asr.ready:
                language = lollmsElfServer.config.asr_current_language# convert_language_name()
                lollmsElfServer.asr.set_speaker_folder(voices_folder)
                preprocessed_text= add_period(request.text)
                voice_file =  [v for v in voices_folder.iterdir() if v.stem==voice and v.suffix==".wav"]
                if len(voice_file)==0:
                    return {"status":False,"error":"Voice not found"}
                lollmsElfServer.asr.tts_audio(preprocessed_text, voice_file[0].name, f"{output_fn}", language=language)
            else:
                lollmsElfServer.InfoMessage("asr is not up yet.\nPlease wait for it to load then try again. This may take some time.") 
                return  {"status":False, "error":"Service not ready yet"} 
        except Exception as ex:
            trace_exception(ex)
            return {"url": None}
    except Exception as ex:
        trace_exception(ex)
        lollmsElfServer.error(ex)
        return {"status":False,"error":str(ex)}

@router.get("/install_asr")
def install_asr():
    try:
        if lollmsElfServer.config.headless_server_mode:
            return {"status":False,"error":"Service installation is blocked when in headless mode for obvious security reasons!"}

        if lollmsElfServer.config.host!="localhost" and lollmsElfServer.config.host!="127.0.0.1":
            return {"status":False,"error":"Service installation is blocked when the server is exposed outside for very obvious reasons!"}
        
        from lollms.services.asr.lollms_asr import install_asr
        lollmsElfServer.ShowBlockingMessage("Installing ASR api server\nPlease stand by")
        install_asr(lollmsElfServer)
        lollmsElfServer.HideBlockingMessage()
        return {"status":True}
    except Exception as ex:
        trace_exception(ex)
        lollmsElfServer.HideBlockingMessage()
        return {"status":False, 'error':str(ex)}

@router.get("/start_asr")
def start_asr():
    try:
        lollmsElfServer.ShowBlockingMessage("Starting ASR api server\nPlease stand by")
        from lollms.services.asr.lollms_asr import LollmsASR
        if lollmsElfServer.asr is None:
            lollmsElfServer.asr = LollmsASR(
                lollmsElfServer, 
                voice_samples_path=Path(__file__).parent/"voices", 
                asr_base_url= lollmsElfServer.config.asr_base_url,                                             
            )
        lollmsElfServer.HideBlockingMessage()
    except Exception as ex:
        trace_exception(ex)
        lollmsElfServer.HideBlockingMessage()
        return {"url": None, "error":f"{ex}"}


@router.get("/asr_is_ready")
def asr_is_ready():
    if hasattr(lollmsElfServer,'sd') and lollmsElfServer.sd is not None:
        if lollmsElfServer.sd.ready:
            return {"status":True}
    return {"status":False}
