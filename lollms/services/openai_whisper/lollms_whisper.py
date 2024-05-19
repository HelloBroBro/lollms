# Title LollmsOpenAIWhisper
# Licence: MIT
# Author : Paris Neo
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
import subprocess
import shutil
from tqdm import tqdm
import threading
from io import BytesIO
from openai import OpenAI


def get_Whisper(lollms_paths:LollmsPaths):
    return LollmsOpenAIWhisper

class LollmsOpenAIWhisper:
    def __init__(
                    self, 
                    app:LollmsApplication, 
                    model="whisper-1",
                    api_key="",
                    output_path=None
                    ):
        self.client = OpenAI(api_key=api_key)
        self.app = app
        self.model = model
        self.output_path = output_path
        self.ready = True

    def transcribe(
                self,
                wav_path: str|Path,
                model:str="",
                output_path:str|Path=None
                ):
        if model=="" or model is None:
            model = self.model
        if output_path is None:
            output_path = self.output_path
        audio_file= open(str(wav_path), "rb")
        transcription = self.client.audio.transcriptions.create(
            model=model, 
            file=audio_file,
            response_format="text"
        )        
        return transcription
