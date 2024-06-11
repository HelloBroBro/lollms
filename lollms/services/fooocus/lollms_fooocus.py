# Title LollmsFooocus
# Licence: MIT
# Author : Paris Neo
    # All rights are reserved

from pathlib import Path
import sys
from lollms.app import LollmsApplication
from lollms.paths import LollmsPaths
from lollms.config import TypedConfig, ConfigTemplate, BaseConfig
from lollms.utilities import PackageManager, check_and_install_torch, find_next_available_filename
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
from lollms.tti import LollmsTTI
from lollms.utilities import git_pull, show_yes_no_dialog, run_script_in_env, create_conda_env
import subprocess
import shutil
from tqdm import tqdm
import threading



def download_file(url, folder_path, local_filename):
    # Make sure 'folder_path' exists
    folder_path.mkdir(parents=True, exist_ok=True)

    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        total_size = int(r.headers.get('content-length', 0))
        progress_bar = tqdm(total=total_size, unit='B', unit_scale=True)
        with open(folder_path / local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192): 
                f.write(chunk)
                progress_bar.update(len(chunk))
        progress_bar.close()

    return local_filename

def install_model(lollms_app:LollmsApplication, model_url):
    root_dir = lollms_app.lollms_paths.personal_path
    shared_folder = root_dir/"shared"
    fooocus_folder = shared_folder / "fooocus"
    if not PackageManager.check_package_installed("fooocus"):
        PackageManager.install_or_update("fooocus")
    if not PackageManager.check_package_installed("torch"):
        check_and_install_torch(True)

    import torch
    from fooocus import PixArtSigmaPipeline

    # You can replace the checkpoint id with "PixArt-alpha/PixArt-Sigma-XL-2-512-MS" too.
    pipe = PixArtSigmaPipeline.from_pretrained(
        "PixArt-alpha/PixArt-Sigma-XL-2-1024-MS", torch_dtype=torch.float16
    )    


def install_fooocus(lollms_app:LollmsApplication):
    root_dir = lollms_app.lollms_paths.personal_path
    shared_folder = root_dir/"shared"
    fooocus_folder = shared_folder / "fooocus"
    fooocus_folder.mkdir(exist_ok=True, parents=True)
    if not PackageManager.check_package_installed("fooocus"):
        PackageManager.install_or_update("gradio_client")
        



def upgrade_fooocus(lollms_app:LollmsApplication):
    PackageManager.install_or_update("fooocus")
    PackageManager.install_or_update("xformers")


class LollmsFooocus(LollmsTTI):
    def __init__(
                    self, 
                    app:LollmsApplication, 
                    wm = "Artbot",
                    base_url="localhost:1024"
                    ):
        super().__init__("fooocus",app)
        self.ready = False
        self.base_url = base_url
        # Get the current directory
        lollms_paths = app.lollms_paths
        root_dir = lollms_paths.personal_path
        
        self.wm = wm

        shared_folder = root_dir/"shared"
        self.fooocus_folder = shared_folder / "fooocus"
        self.output_dir = root_dir / "outputs/fooocus"
        self.models_dir = self.fooocus_folder / "models"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)

        ASCIIColors.red(" _           _ _                ______                               ")
        ASCIIColors.red("| |         | | |               |  ___|                              ")
        ASCIIColors.red("| |     ___ | | |_ __ ___  ___  | |_ ___   ___   ___   ___ _   _ ___ ")
        ASCIIColors.red("| |    / _ \| | | '_ ` _ \/ __| |  _/ _ \ / _ \ / _ \ / __| | | / __|")
        ASCIIColors.red("| |___| (_) | | | | | | | \__ \ | || (_) | (_) | (_) | (__| |_| \__ \ ")
        ASCIIColors.red("\_____/\___/|_|_|_| |_| |_|___/ \_| \___/ \___/ \___/ \___|\__,_|___/")
        ASCIIColors.red("                            ______                                   ")
        ASCIIColors.red("                           |______|                                  ")
        if not PackageManager.check_package_installed("gradio_client"):
            PackageManager.install_or_update("gradio_client")
        from gradio_client import Client
        self.client = Client(base_url)
        

    @staticmethod
    def verify(app:LollmsApplication):
        # Clone repository
        root_dir = app.lollms_paths.personal_path
        shared_folder = root_dir/"shared"
        fooocus_folder = shared_folder / "fooocus"
        return fooocus_folder.exists()
    
    def get(app:LollmsApplication):
        root_dir = app.lollms_paths.personal_path
        shared_folder = root_dir/"shared"
        fooocus_folder = shared_folder / "fooocus"
        fooocus_script_path = fooocus_folder / "lollms_fooocus.py"
        git_pull(fooocus_folder)
        
        if fooocus_script_path.exists():
            ASCIIColors.success("lollms_fooocus found.")
            ASCIIColors.success("Loading source file...",end="")
            # use importlib to load the module from the file path
            from lollms.services.fooocus.lollms_fooocus import LollmsFooocus
            ASCIIColors.success("ok")
            return LollmsFooocus


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
            output_path = self.output_dir
        
        self.client.predict()
        image = self.model(positive_prompt, negative_prompt=negative_prompt, guidance_scale=scale, num_inference_steps=steps,).images[0]
        output_path = Path(output_path)
        fn = find_next_available_filename(output_path,"diff_img_")
        # Save the image
        image.save(fn)
        return fn, {"prompt":positive_prompt, "negative_prompt":negative_prompt}
    
