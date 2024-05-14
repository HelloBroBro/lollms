# Title LollmsDalle
# Licence: MIT
# Author : Paris Neo
# Adapted from the work of mix1009's sdwebuiapi
# check it out : https://github.com/mix1009/sdwebuiapi/tree/main
# Here is a copy of the LICENCE https://github.com/mix1009/sdwebuiapi/blob/main/LICENSE
# All rights are reserved

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

def get_Dalli(lollms_paths:LollmsPaths):
    return LollmsDalle

class LollmsDalle:
    has_controlnet = False
    def __init__(
                    self, 
                    app:LollmsApplication, 
                    key="",
                    generation_engine="dall-e-3",# other possibility "dall-e-2"
                    output_path=None
                    ):
        self.app = app
        self.key = key 
        self.generation_engine = generation_engine
        self.output_path = output_path

    def paint(
                self,
                prompt,
                width=512,
                height=512,
                images = [],
                generation_engine=None,
                output_path = None
                ):
        if output_path is None:
            output_path = self.output_path
        if generation_engine is None:
            generation_engine = self.generation_engine
        if not PackageManager.check_package_installed("openai"):
            PackageManager.install_package("openai")
        import openai
        openai.api_key = self.key
        if generation_engine=="dall-e-2":
            supported_resolutions = [
                [512, 512],
                [1024, 1024],
            ]
            # Find the closest resolution
            closest_resolution = min(supported_resolutions, key=lambda res: abs(res[0] - width) + abs(res[1] - height))
            
        else:
            supported_resolutions = [
                [1024, 1024],
                [1024, 1792],
                [1792, 1024]
            ]
            # Find the closest resolution
            if width>height:
                closest_resolution = [1792, 1024]
            elif width<height: 
                closest_resolution = [1024, 1792]
            else:
                closest_resolution = [1024, 1024]


        # Update the width and height
        width = closest_resolution[0]
        height = closest_resolution[1]                    

        if len(images)>0 and generation_engine=="dall-e-2":
            # Read the image file from disk and resize it
            image = Image.open(self.personality.image_files[0])
            width, height = width, height
            image = image.resize((width, height))

            # Convert the image to a BytesIO object
            byte_stream = BytesIO()
            image.save(byte_stream, format='PNG')
            byte_array = byte_stream.getvalue()
            response = openai.images.create_variation(
                image=byte_array,
                n=1,
                model=generation_engine, # for now only dalle 2 supports variations
                size=f"{width}x{height}"
            )
        else:
            response = openai.images.generate(
                model=generation_engine,
                prompt=prompt.strip(),
                quality="standard",
                size=f"{width}x{height}",
                n=1,
                
                )
        # download image to outputs
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        image_url = response.data[0].url

        # Get the image data from the URL
        response = requests.get(image_url)

        if response.status_code == 200:
            # Generate the full path for the image file
            file_name = output_dir/find_next_available_filename(output_dir, "img_dalle_")  # You can change the filename if needed

            # Save the image to the specified folder
            with open(file_name, "wb") as file:
                file.write(response.content)
            ASCIIColors.yellow(f"Image saved to {file_name}")
        else:
            ASCIIColors.red("Failed to download the image")

        return file_name
