# Title LollmsWhisper
# Licence: MIT
# Author : Paris Neo
# 

from pathlib import Path
from lollms.app import LollmsApplication
from lollms.paths import LollmsPaths
from lollms.config import TypedConfig, ConfigTemplate, BaseConfig
from lollms.utilities import PackageManager, install_conda_package
from lollms.stt import LollmsSTT
from dataclasses import dataclass
from PIL import Image, PngImagePlugin
from enum import Enum
from typing import List, Dict, Any

from ascii_colors import ASCIIColors, trace_exception
from lollms.paths import LollmsPaths
import subprocess
import pipmaster as pm
try:
    if not pm.is_installed("openai-whisper"):
        pm.install("openai-whisper")
        try:
            install_conda_package("conda-forge::ffmpeg")
        except Exception as ex:
            trace_exception(ex)
            ASCIIColors.red("Couldn't install ffmpeg")
except:
        try:
            install_conda_package("conda-forge::ffmpeg")
        except Exception as ex:
            trace_exception(ex)
            ASCIIColors.red("Couldn't install ffmpeg")
        pm.install("git+https://github.com/openai/whisper.git")

try:
    import whisper
except:
    pm.install("openai-whisper")

class LollmsWhisper(LollmsSTT):
    def __init__(
                    self, 
                    app:LollmsApplication, 
                    model="small",
                    output_path=None
                    ):
        super().__init__("whisper",app, model, output_path)
        try:
            self.whisper = whisper.load_model(model)
        except:
            ASCIIColors.red("Couldn't load whisper model!\nWhisper will be disabled")
            self.whisper = None
        self.ready = True

    def transcribe(
                self,
                wave_path: str|Path
                )->str:
        if self.whisper:
            result = self.whisper.transcribe(str(wave_path))
            return result["text"]
        else:
            ASCIIColors.error("Whisper is broken")
            return ""