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

try:
    if not PackageManager.check_package_installed("whisper"):
        PackageManager.install_package("openai-whisper")
        try:
            install_conda_package("conda-forge::ffmpeg")
        except Exception as ex:
            trace_exception(ex)
            ASCIIColors.red("Couldn't install ffmpeg")
except:
        PackageManager.install_package("git+https://github.com/openai/whisper.git")


import whisper


class LollmsWhisper(LollmsSTT):
    def __init__(
                    self, 
                    app:LollmsApplication, 
                    model="small",
                    output_path=None
                    ):
        super().__init__("whisper",app, model, output_path)
        self.whisper = whisper.load_model(model)
        self.ready = True

    def transcribe(
                self,
                wave_path: str|Path
                )->str:
        result = self.whisper.transcribe(str(wave_path))
        return result["text"]
