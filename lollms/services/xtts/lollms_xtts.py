# Title LollmsXTTS
# Licence: MIT
# Author : Paris Neo
# Adapted from the work of daswer123's xtts-api-server
# check it out : https://github.com/daswer123/xtts-api-server
# Here is a copy of the LICENCE https://github.com/daswer123/xtts-api-server/blob/main/LICENSE
# All rights are reserved

from pathlib import Path
import sys
from lollms.app import LollmsApplication
from lollms.paths import LollmsPaths
from lollms.config import TypedConfig, ConfigTemplate, BaseConfig
from lollms.utilities import PackageManager
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
from lollms.utilities import git_pull, show_yes_no_dialog, run_python_script_in_env, create_conda_env, run_pip_in_env
import subprocess
import platform

def verify_xtts(lollms_paths:LollmsPaths):
    # Clone repository
    root_dir = lollms_paths.personal_path
    shared_folder = root_dir/"shared"
    xtts_folder = shared_folder / "xtts"
    return xtts_folder.exists()
    
def install_xtts(lollms_app:LollmsApplication):
    ASCIIColors.green("XTTS installation started")

    root_dir = lollms_app.lollms_paths.personal_path
    shared_folder = root_dir/"shared"
    xtts_folder = shared_folder / "xtts"
    if xtts_folder.exists() and PackageManager.check_package_installed("xtts-api-server"):
        if not show_yes_no_dialog("warning!","It looks like xtts is already installed on your system.\nDo you want to reinstall it?"):
            lollms_app.error("Service installation canceled")
            return
    
    lollms_app.ShowBlockingMessage("Creating xtts environment")
    ASCIIColors.cyan("Installing autosd conda environment with python 3.10")
    create_conda_env("xtts","3.10")
    ASCIIColors.cyan("Done")
    ASCIIColors.cyan("Installing xtts-api-server")
    run_pip_in_env("xtts", "install --upgrade xtts-api-server")
    run_pip_in_env("xtts", "install --upgrade torchaudio==2.1.1+cu118 --index-url https://download.pytorch.org/whl/cu118")
    ASCIIColors.cyan("Done")
    xtts_folder.mkdir(exist_ok=True,parents=True)
    ASCIIColors.green("XTTS server installed successfully")



def get_xtts(lollms_paths:LollmsPaths):
    root_dir = lollms_paths.personal_path
    shared_folder = root_dir/"shared"
    xtts_folder = shared_folder / "xtts"
    xtts_script_path = xtts_folder / "lollms_xtts.py"
    git_pull(xtts_folder)
    
    if xtts_script_path.exists():
        ASCIIColors.success("lollms_xtts found.")
        ASCIIColors.success("Loading source file...",end="")
        # use importlib to load the module from the file path
        from lollms.services.xtts.lollms_xtts import LollmsXTTS
        ASCIIColors.success("ok")
        return LollmsXTTS

class LollmsXTTS:
    has_controlnet = False
    def __init__(
                    self, 
                    app:LollmsApplication, 
                    xtts_base_url=None,
                    share=False,
                    max_retries=10,
                    voice_samples_path="",
                    wait_for_service=True,
                    use_deep_speed=False,
                    use_streaming_mode = True

                    ):
        if xtts_base_url=="" or xtts_base_url=="http://127.0.0.1:8020":
            xtts_base_url = None
        # Get the current directory
        lollms_paths = app.lollms_paths
        self.app = app
        root_dir = lollms_paths.personal_path
        self.voice_samples_path = voice_samples_path
        self.use_deep_speed = use_deep_speed
        self.use_streaming_mode = use_streaming_mode
        
        # Store the path to the script
        if xtts_base_url is None:
            self.xtts_base_url = "http://127.0.0.1:8020"
            if not verify_xtts(lollms_paths):
                install_xtts(app.lollms_paths)
        else:
            self.xtts_base_url = xtts_base_url

        self.auto_xtts_url = self.xtts_base_url+"/sdapi/v1"
        shared_folder = root_dir/"shared"
        self.xtts_folder = shared_folder / "xtts"

        ASCIIColors.red("   __    ___  __    __          __     __  ___   _        ")
        ASCIIColors.red("  / /   /___\/ /   / /   /\/\  / _\    \ \/ / |_| |_ ___  ")
        ASCIIColors.red(" / /   //  // /   / /   /    \ \ \ _____\  /| __| __/ __| ")
        ASCIIColors.red("/ /___/ \_// /___/ /___/ /\/\ \_\ \_____/  \| |_| |_\__ \ ")
        ASCIIColors.red("\____/\___/\____/\____/\/    \/\__/    /_/\_\\__|\__|___/ ")
                                                         
        ASCIIColors.red(" Forked from daswer123's XTTS server")
        ASCIIColors.red(" Integration in lollms by ParisNeo using daswer123's webapi")
        ASCIIColors.red(" Address :",end="")
        ASCIIColors.yellow(f"{self.xtts_base_url}")

        self.output_folder = app.lollms_paths.personal_outputs_path/"audio_out"
        self.output_folder.mkdir(parents=True, exist_ok=True)

        if not self.wait_for_service(1,False):
            ASCIIColors.info("Loading lollms_xtts")
            # Launch the Flask service using the appropriate script for the platform
            self.process = self.run_xtts_api_server()

        # Wait until the service is available at http://127.0.0.1:7860/
        if wait_for_service:
            self.wait_for_service(max_retries=max_retries)


    def run_xtts_api_server(self):
        # Get the path to the current Python interpreter
        python_path = sys.executable
        ASCIIColors.yellow("Loading XTTS ")
        options= ""
        if self.use_deep_speed:
            options += "--deepspeed"
        if self.use_streaming_mode:
            options += "--streaming-mode --streaming-mode-improve --stream-play-sync"
        process = run_python_script_in_env("xtts", f"-m xtts_api_server {options} -o {self.output_folder} -sf {self.voice_samples_path} -p {self.xtts_base_url.split(':')[-1].replace('/','')}", wait= False)
        return process
    
    def wait_for_service(self, max_retries = 150, show_warning=True):
        url = f"{self.xtts_base_url}/languages"
        # Adjust this value as needed
        retries = 0

        while retries < max_retries or max_retries<0:
            
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    print("Service is available.")
                    if self.app is not None:
                        self.app.success("XTTS Service is now available.")
                    return True
            except requests.exceptions.RequestException:
                pass

            retries += 1
            time.sleep(3)
            ASCIIColors.yellow("Waiting ...")
        if show_warning:
            print("Service did not become available within the given time.")
            if self.app is not None:
                self.app.error("XTTS Service did not become available within the given time.")
        return False

    def set_speaker_folder(self, speaker_folder):
        url = f"{self.xtts_base_url}/set_speaker_folder"

        # Define the request body
        payload = {
            "speaker_folder": str(speaker_folder)
        }

        # Send the POST request
        response = requests.post(url, json=payload)

        # Check the response status code
        if response.status_code == 200:
            print("Request successful")
            return True
            # You can access the response data using response.json()
        else:
            print("Request failed with status code:", response.status_code)
            return False

    def tts_to_file(self, text, speaker_wav, file_name_or_path, language="en"):
        url = f"{self.xtts_base_url}/tts_to_file"

        # Define the request body
        payload = {
            "text": text,
            "speaker_wav": speaker_wav,
            "language": language,
            "file_name_or_path": file_name_or_path
        }
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json'
        }

        # Send the POST request
        response =  requests.post(url, headers=headers, data=json.dumps(payload))

        # Check the response status code
        if response.status_code == 200:
            print("Request successful")
            # You can access the response data using response.json()
        else:
            print("Request failed with status code:", response.status_code)