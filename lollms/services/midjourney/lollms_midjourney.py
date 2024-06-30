# Title LollmsMidjourney
# Licence: Apache 2.0
# Author : Paris Neo


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
from lollms.tti import LollmsTTI
import subprocess
import shutil
from tqdm import tqdm
import threading
from io import BytesIO

MIDJOURNEY_API_URL = "https://api.mymidjourney.ai/api/v1/midjourney"


class LollmsMidjourney(LollmsTTI):
    def __init__(
                    self, 
                    app:LollmsApplication, 
                    key="",
                    timeout=300,
                    retries=2,
                    interval=1,
                    output_path=None
                    ):
        super().__init__("midjourney",app)
        self.key = key 
        self.output_path = output_path
        self.timeout = timeout
        self.retries = retries
        self.interval = interval
        self.session = requests.Session()
        self.headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }

    def send_prompt(self, prompt: str) -> Dict[str, Any]:
        """
        Send a prompt to the MidJourney API to generate an image.

        Args:
            prompt (str): The prompt for image generation.

        Returns:
            Dict[str, Any]: The response from the API.
        """
        url = f"{MIDJOURNEY_API_URL}/imagine"
        payload = {"prompt": prompt}
        response = self.session.post(url, json=payload, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def check_progress(self, message_id: str) -> Dict[str, Any]:
        """
        Check the progress of the image generation.

        Args:
            message_id (str): The message ID from the initial request.

        Returns:
            Dict[str, Any]: The response from the API.
        """
        url = f"{MIDJOURNEY_API_URL}/message/{message_id}"
        response = self.session.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def upscale_image(self, message_id: str, button: str) -> Dict[str, Any]:
        """
        Upscale the generated image.

        Args:
            message_id (str): The message ID from the initial request.
            button (str): The button action for upscaling.

        Returns:
            Dict[str, Any]: The response from the API.
        """
        url = f"{MIDJOURNEY_API_URL}/button"
        payload = {"messageId": message_id, "button": button}
        response = self.session.post(url, json=payload, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def send_prompt_with_retry(self, prompt: str, retries: int = 3) -> Dict[str, Any]:
        """
        Send a prompt to the MidJourney API with retry mechanism.

        Args:
            prompt (str): The prompt for image generation.
            retries (int): Number of retry attempts.

        Returns:
            Dict[str, Any]: The response from the API.
        """
        for attempt in range(retries):
            try:
                return self.send_prompt(prompt)
            except requests.exceptions.RequestException as e:
                if attempt < retries - 1:
                    ASCIIColors.warning(f"Attempt {attempt + 1} failed: {e}. Retrying...")
                    time.sleep(2 ** attempt)
                else:
                    ASCIIColors.error(f"All {retries} attempts failed.")
                    raise e

    def poll_progress(self, message_id: str, timeout: int = 300, interval: int = 5) -> Dict[str, Any]:
        """
        Poll the progress of the image generation until it's done or timeout.

        Args:
            message_id (str): The message ID from the initial request.
            timeout (int): The maximum time to wait for the image generation.
            interval (int): The interval between polling attempts.

        Returns:
            Dict[str, Any]: The response from the API.
        """
        start_time = time.time()
        with tqdm(total=100, desc="Image Generation Progress", unit="%") as pbar:
            while time.time() - start_time < timeout:
                progress_response = self.check_progress(message_id)
                if progress_response.get("status") == "DONE":
                    pbar.update(100 - pbar.n)  # Ensure the progress bar is complete
                    print(progress_response)
                    return progress_response
                elif progress_response.get("status") == "FAIL":
                    ASCIIColors.error("Image generation failed.")
                    return {"error": "Image generation failed"}

                progress = progress_response.get("progress", 0)
                pbar.update(progress - pbar.n)  # Update the progress bar
                time.sleep(interval)
        
        ASCIIColors.error("Timeout while waiting for image generation.")
        return {"error": "Timeout while waiting for image generation"}


    def download_image(self, uri, folder_path):
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        
        i = 1
        while True:
            file_path = os.path.join(folder_path, f"midjourney_{i}.png")
            if not os.path.exists(file_path):
                break
            i += 1
        
        response = requests.get(uri)
        if response.status_code == 200:
            with open(file_path, 'wb') as file:
                file.write(response.content)
            print(f"Image downloaded and saved as {file_path}")
            return file_path
        else:
            print(f"Failed to download image. Status code: {response.status_code}")
            return None
        
    def paint(
                self,
                positive_prompt,
                negative_prompt,
                sampler_name="Euler",
                seed=-1,
                scale=7.5,
                steps=20,
                img2img_denoising_strength=0.9,
                width=512,
                height=512,
                restore_faces=True,
                output_path=None
                ):
        if output_path is None:
            output_path = self.output_path

        try:
            # Send prompt and get initial response
            initial_response = self.send_prompt_with_retry(positive_prompt, self.retries)
            message_id = initial_response.get("messageId")
            if not message_id:
                raise ValueError("No messageId returned from initial prompt")

            # Poll progress until image generation is done
            progress_response = self.poll_progress(message_id, self.timeout, self.interval)
            if "error" in progress_response:
                raise ValueError(progress_response["error"])
            
            if width<1024:
                file_name = self.download_image(progress_response["uri"], output_path)
                
                return file_name

            # Upscale the generated image
            upscale_response = self.upscale_image(message_id, "U1")
            message_id = upscale_response.get("messageId")
            if not message_id:
                raise ValueError("No messageId returned from initial prompt")

            # Poll progress until image generation is done
            progress_response = self.poll_progress(message_id, self.timeout, self.interval)
            if "error" in progress_response:
                raise ValueError(progress_response["error"])
            
            file_name = self.download_image(progress_response["uri"], output_path)
            return file_name, {"prompt":positive_prompt, "negative_prompt":negative_prompt}

        except Exception as e:
            ASCIIColors.error(f"An error occurred: {e}")
    
    @staticmethod
    def get(app:LollmsApplication):
        return LollmsMidjourney