# Title LollmsOpenAITTS
# Licence: MIT
# Author : Paris Neo
# Uses open AI api to perform text to speech
# 

from pathlib import Path
import sys
from lollms.app import LollmsApplication
from lollms.paths import LollmsPaths
from lollms.config import TypedConfig, ConfigTemplate, BaseConfig
import time
import io
import sys
import requests
import os
import base64
import subprocess
import time
import json
import platform
from dataclasses import dataclass
from PIL import Image, PngImagePlugin
from enum import Enum
from typing import List, Dict, Any

from ascii_colors import ASCIIColors, trace_exception
from lollms.paths import LollmsPaths
from lollms.utilities import PackageManager, find_next_available_filename
from lollms.tts import LollmsTTS
import subprocess
import shutil
from tqdm import tqdm
import threading
from io import BytesIO
import pipmaster as pm
if not pm.is_installed("openai"):
    pm.install("openai")
from openai import OpenAI

if not PackageManager.check_package_installed("sounddevice"):
    PackageManager.install_package("sounddevice")
if not PackageManager.check_package_installed("soundfile"):
    PackageManager.install_package("soundfile")

import sounddevice as sd
import soundfile as sf

def get_Whisper(lollms_paths:LollmsPaths):
    return LollmsOpenAITTS

class LollmsOpenAITTS(LollmsTTS):
    def __init__(
                    self, 
                    app:LollmsApplication,
                    model ="tts-1",
                    voice="alloy",
                    api_key="",
                    output_path=None
                    ):
        super().__init__("openai_tts", app, model, voice, api_key, output_path)
        self.client = OpenAI(api_key=api_key)
        self.voices = [
         "alloy",
         "echo",
         "fable",
         "nova",
         "shimmer"     
        ]
        self.models = [
         "tts-1"   
        ]

        self.voice = voice
        self.output_path = output_path
        self.ready = True


    def tts_file(self, text, speaker, file_name_or_path, language="en"):
        speech_file_path = file_name_or_path
        response = self.client.audio.speech.create(
        model=self.model,
        voice=self.voice,
        input=text,
        response_format="wav"
        
        )

        response.write_to_file(speech_file_path)

    def tts_audio(self, text, speaker:str=None, file_name_or_path:Path|str=None, language="en", use_threading=False):
        speech_file_path = file_name_or_path
        response = self.client.audio.speech.create(
        model=self.model,
        voice=self.voice if speaker is None else speaker,
        input=text,
        response_format="wav"
        
        )

        response.write_to_file(speech_file_path)
        def play_audio(file_path):
            # Read the audio file
            data, fs = sf.read(file_path, dtype='float32')
            # Play the audio file
            sd.play(data, fs)
            # Wait until the file is done playing
            sd.wait()

        # Example usage
        play_audio(speech_file_path)

    def tts_file(self, text, speaker=None, file_name_or_path:Path|str=None, language="en", use_threading=False):
        speech_file_path = file_name_or_path
        text = self.clean_text(text)
        response = self.client.audio.speech.create(
        model=self.model,
        voice=self.voice,
        input=text,
        response_format="wav"
        
        )

        response.write_to_file(speech_file_path)
        return file_name_or_path
