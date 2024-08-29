# Title LollmsOpenAITTS
# Licence: MIT
# Author : Paris Neo
# Uses open AI api to perform text to speech
# 

from pathlib import Path
from lollms.app import LollmsApplication
from lollms.paths import LollmsPaths
import sys
import requests
from typing import List, Dict, Any

from ascii_colors import ASCIIColors, trace_exception
from lollms.paths import LollmsPaths
from lollms.utilities import PackageManager, find_next_available_filename
from lollms.tts import LollmsTTS

if not PackageManager.check_package_installed("sounddevice"):
    PackageManager.install_package("sounddevice")
if not PackageManager.check_package_installed("soundfile"):
    PackageManager.install_package("soundfile")

import sounddevice as sd
import soundfile as sf

def get_Whisper(lollms_paths:LollmsPaths):
    return LollmsElevenLabsTTS

class LollmsElevenLabsTTS(LollmsTTS):
    def __init__(
                    self, 
                    app:LollmsApplication,
                    model_id: str = "eleven_monolingual_v2",
                    voice_id: str = "EXAVITQu4vr4xnSDxMaL",
                    api_key: str = "",
                    output_path: Path | str = None,
                    stability: float = 0.5,
                    similarity_boost: float = 0.5,
                    streaming: bool = False
                    ):
        super().__init__("elevenlabs_tts", app, model_id, voice_id, api_key, output_path)
        self.voice_id = voice_id
        self.model_id = model_id
        self.api_key = api_key
        self.output_path = output_path
        self.stability = stability
        self.similarity_boost = similarity_boost
        self.streaming = streaming
        self.ready = True

    def tts_file(self, text, file_name_or_path: Path | str = None, speaker=None, language="en", use_threading=False):
        speech_file_path = file_name_or_path
        payload = {
            "text": text,
            "model_id": self.model_id,
            "voice_settings": {
                "stability": self.stability,
                "similarity_boost": self.similarity_boost
            }
        }
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        if self.streaming:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}/stream"
            response = requests.post(url, json=payload, headers=headers)
            # Handle streaming response if needed
        else:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
            response = requests.post(url, json=payload, headers=headers)
            with open(speech_file_path, 'wb') as f:
                f.write(response.content)

        return speech_file_path

    def tts_audio(self, text, speaker: str = None, file_name_or_path: Path | str = None, language="en", use_threading=False):
        speech_file_path = file_name_or_path
        payload = {
            "text": text,
            "model_id": self.model_id,
            "voice_settings": {
                "stability": self.stability,
                "similarity_boost": self.similarity_boost
            }
        }
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        if self.streaming:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}/stream"
            response = requests.post(url, json=payload, headers=headers)
            # Handle streaming response if needed
        else:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
            response = requests.post(url, json=payload, headers=headers)
            with open(speech_file_path, 'wb') as f:
                f.write(response.content)

        def play_audio(file_path):
            # Read the audio file
            data, fs = sf.read(file_path, dtype='float32')
            # Play the audio file
            sd.play(data, fs)
            # Wait until the file is done playing
            sd.wait()

        # Example usage
        play_audio(speech_file_path)
