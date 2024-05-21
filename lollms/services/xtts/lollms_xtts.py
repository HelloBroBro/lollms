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
from lollms.utilities import PackageManager, find_first_available_file_index, add_period
import time
import io
import sys
import requests
import os
import base64
import subprocess
import time
import json
import re
import platform
import threading
from dataclasses import dataclass
from PIL import Image, PngImagePlugin
from enum import Enum
from typing import List, Dict, Any
import uuid

from ascii_colors import ASCIIColors, trace_exception
from lollms.paths import LollmsPaths
from lollms.utilities import git_pull, show_yes_no_dialog, run_python_script_in_env, create_conda_env, run_pip_in_env, environment_exists
from lollms.tts import LollmsTTS
import subprocess
import platform



class LollmsXTTS(LollmsTTS):
    def __init__(
                    self, 
                    app:LollmsApplication, 
                    xtts_base_url=None,
                    share=False,
                    max_retries=20,
                    voices_folder=None,
                    voice_samples_path="",
                    wait_for_service=True,
                    use_deep_speed=False,
                    use_streaming_mode = True
                ):
        super().__init__(app)
        self.generation_threads = {}
        self.voices_folder = voices_folder
        self.ready = False
        if xtts_base_url=="" or xtts_base_url=="http://127.0.0.1:8020":
            xtts_base_url = None
        # Get the current directory
        lollms_paths = app.lollms_paths
        root_dir = lollms_paths.personal_path
        self.voice_samples_path = voice_samples_path
        self.use_deep_speed = use_deep_speed
        self.use_streaming_mode = use_streaming_mode
        
        # Store the path to the script
        if xtts_base_url is None:
            self.xtts_base_url = "http://127.0.0.1:8020"
            if not LollmsXTTS.verify(lollms_paths):
                LollmsXTTS.install(app)
        else:
            self.xtts_base_url = xtts_base_url

        self.auto_xtts_url = self.xtts_base_url+"/sdapi/v1"
        shared_folder = root_dir/"shared"
        self.xtts_path = shared_folder / "xtts"

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
            self.wait_for_service()
        else:
            self.wait_for_service_in_another_thread(max_retries=max_retries)

    def install(lollms_app:LollmsApplication):
        ASCIIColors.green("XTTS installation started")
        repo_url = "https://github.com/ParisNeo/xtts-api-server"
        root_dir = lollms_app.lollms_paths.personal_path
        shared_folder = root_dir/"shared"
        xtts_path = shared_folder / "xtts"

        # Step 1: Clone or update the repository
        if os.path.exists(xtts_path):
            print("Repository already exists. Pulling latest changes...")
            try:
                subprocess.run(["git", "-C", xtts_path, "pull"], check=True)
            except:
                subprocess.run(["git", "clone", repo_url, xtts_path], check=True)

        else:
            print("Cloning repository...")
            subprocess.run(["git", "clone", repo_url, xtts_path], check=True)

        # Step 2: Create or update the Conda environment
        if environment_exists("xtts"):
            print("Conda environment 'xtts' already exists. Updating...")
            # Here you might want to update the environment, e.g., update Python or dependencies
            # This step is highly dependent on how you manage your Conda environments and might involve
            # running `conda update` commands or similar.
        else:
            print("Creating Conda environment 'xtts'...")
            create_conda_env("xtts", "3.8")

        # Step 3: Install or update dependencies using your custom function
        requirements_path = os.path.join(xtts_path, "requirements.txt")
        run_pip_in_env("xtts", f"install -r {requirements_path}", cwd=xtts_path)
        run_pip_in_env("xtts", f"install torch==2.1.1+cu118 torchaudio==2.1.1+cu118 --index-url https://download.pytorch.org/whl/cu118", cwd=xtts_path)

        # Step 4: Launch the server
        # Assuming the server can be started with a Python script in the cloned repository
        print("Launching XTTS API server...")
        run_python_script_in_env("xtts", "xtts_api_server", cwd=xtts_path)

        print("XTTS API server setup and launch completed.")
        ASCIIColors.cyan("Done")
        ASCIIColors.cyan("Installing xtts-api-server")
        ASCIIColors.green("XTTS server installed successfully")

    @staticmethod
    def verify(lollms_paths:LollmsPaths)->bool:
        # Clone repository
        root_dir = lollms_paths.personal_path
        shared_folder = root_dir/"shared"
        xtts_path = shared_folder / "xtts"
        return xtts_path.exists()
    
    @staticmethod
    def get(app: LollmsApplication) -> 'LollmsXTTS':
        root_dir = app.lollms_paths.personal_path
        shared_folder = root_dir/"shared"
        xtts_path = shared_folder / "xtts"
        xtts_script_path = xtts_path / "lollms_xtts.py"
        git_pull(xtts_path)
        
        if xtts_script_path.exists():
            ASCIIColors.success("lollms_xtts found.")
            ASCIIColors.success("Loading source file...",end="")
            # use importlib to load the module from the file path
            from lollms.services.xtts.lollms_xtts import LollmsXTTS
            ASCIIColors.success("ok")
            return LollmsXTTS

    def run_xtts_api_server(self):
        # Get the path to the current Python interpreter
        ASCIIColors.yellow("Loading XTTS ")
        options= ""
        if self.use_deep_speed:
            options += " --deepspeed"
        if self.use_streaming_mode:
            options += " --streaming-mode --streaming-mode-improve --stream-play-sync"
        process = run_python_script_in_env("xtts", f"-m xtts_api_server {options} -o {self.output_folder} -sf {self.voice_samples_path} -p {self.xtts_base_url.split(':')[-1].replace('/','')}", wait= False)
        return process

    def wait_for_service_in_another_thread(self, max_retries=150, show_warning=True):
        thread = threading.Thread(target=self.wait_for_service, args=(max_retries, show_warning))
        thread.start()
        return thread

    def update_settings(self):
        try:
            settings = {
                "stream_chunk_size": self.app.config.xtts_stream_chunk_size,
                "temperature": self.app.config.xtts_temperature,
                "speed": self.app.config.xtts_speed,
                "length_penalty": self.app.config.xtts_length_penalty,
                "repetition_penalty": self.app.config.xtts_repetition_penalty,
                "top_p": self.app.config.xtts_top_p,
                "top_k": self.app.config.xtts_top_k,
                "enable_text_splitting": self.app.config.xtts_enable_text_splitting
            }             
            response = requests.post(f"{self.xtts_base_url}/set_tts_settings", settings)
            if response.status_code == 200:
                ASCIIColors.success("XTTS updated successfully")
        except Exception as ex:
            trace_exception(ex)
            pass

    def wait_for_service(self, max_retries = 150, show_warning=True):
        print(f"Waiting for xtts service (max_retries={max_retries})")
        url = f"{self.xtts_base_url}/languages"
        # Adjust this value as needed
        retries = 0

        while retries < max_retries or max_retries<0:
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    self.update_settings()
                    print(f"voices_folder is {self.voices_folder}.")
                    if self.voices_folder is not None:
                        print("Generating sample audio.")
                        voice_file =  [v for v in self.voices_folder.iterdir() if v.suffix==".wav"]
                        self.tts_audio("x t t s is ready",voice_file[0].stem)
                    print("Service is available.")
                    if self.app is not None:
                        self.app.success("XTTS Service is now available.")
                    self.ready = True
                    return True
            except:
                pass

            retries += 1
            ASCIIColors.yellow("Waiting for xtts...")
            time.sleep(5)

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

    def tts_file(self, text, file_name_or_path, speaker=None, language="en")->str:
        text = self.clean_text(text)
        url = f"{self.xtts_base_url}/tts_to_file"

        # Define the request body
        payload = {
            "text": text,
            "speaker_wav": speaker,
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

        return file_name_or_path

    def tts_audio(self, text, speaker, file_name_or_path:Path|str=None, language="en", use_threading=False):
        voice=self.app.config.xtts_current_voice if speaker is None else speaker
        index = find_first_available_file_index(self.output_folder, "voice_sample_",".wav")
        output_fn=f"voice_sample_{index}.wav" if file_name_or_path is None else file_name_or_path
        if voice is None:
            voice = "main_voice"
        self.app.info("Starting to build voice")
        try:
            from lollms.services.xtts.lollms_xtts import LollmsXTTS
            # If the personality has a voice, then use it
            personality_audio:Path = self.app.personality.personality_package_path/"audio"
            if personality_audio.exists() and len([v for v in personality_audio.iterdir()])>0:
                voices_folder = personality_audio
            elif voice!="main_voice":
                voices_folder = self.app.lollms_paths.custom_voices_path
            else:
                voices_folder = Path(__file__).parent.parent.parent/"services/xtts/voices"
            language = self.app.config.xtts_current_language# convert_language_name()
            self.set_speaker_folder(voices_folder)
            preprocessed_text= add_period(text)
            voice_file =  [v for v in voices_folder.iterdir() if v.stem==voice and v.suffix==".wav"]
            if len(voice_file)==0:
                return {"status":False,"error":"Voice not found"}
            self.xtts_audio(preprocessed_text, voice_file[0].name, f"{output_fn}", language=language)

        except Exception as ex:
            trace_exception(ex)
            return {"status":False,"error":f"{ex}"}

    def xtts_audio(self, text, speaker, file_name_or_path:Path|str=None, language="en", use_threading=True):
        text = self.clean_text(text)
        def tts2_audio_th(thread_uid=None):
            url = f"{self.xtts_base_url}/tts_to_audio"

            # Define the request body
            payload = {
                "text": text,
                "speaker_wav": speaker,
                "language": language
            }
            headers = {
                'accept': 'application/json',
                'Content-Type': 'application/json'
            }

            # Send the POST request
            response =  requests.post(url, headers=headers, data=json.dumps(payload))

            if response.status_code == 200:
                print("Request successful")
                print("Response headers:", response.headers)
                
                # Basic logging for debugging
                print("First 100 bytes of response content:", response.content[:100])
                
                if file_name_or_path is not None:
                    try:
                        with open(self.output_folder / file_name_or_path, 'wb') as file:
                            # Write the binary content to the file
                            file.write(response.content)
                        print(f"File {file_name_or_path} written successfully.")
                    except Exception as e:
                        print(f"Failed to write the file. Error: {e}")
            else:
                print("Request failed with status code:", response.status_code)
            if thread_uid:
                self.generation_threads.pop(thread_uid, None)
        if use_threading:
            thread_uid =  str(uuid.uuid4())       
            thread = threading.Thread(target=tts2_audio_th, args=(thread_uid,))
            self.generation_threads[thread_uid]=thread
            thread.start()
            ASCIIColors.green("Generation started")
            return thread
        else:
            return tts2_audio_th()
        
    def get_voices(self):
        ASCIIColors.yellow("Listing voices")
        voices=["main_voice"]
        voices_dir:Path=self.app.lollms_paths.custom_voices_path
        voices += [v.stem for v in voices_dir.iterdir() if v.suffix==".wav"]
        return voices
