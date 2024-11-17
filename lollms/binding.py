######
# Project       : lollms
# File          : binding.py
# Author        : ParisNeo with the help of the community
# license       : Apache 2.0
# Description   : 
# This is an interface class for lollms bindings.
######
from fastapi import Request
from typing import Dict, Any
from pathlib import Path
from typing import Callable, Any
from lollms.paths import LollmsPaths
from ascii_colors import ASCIIColors
from urllib import request

import tempfile
import requests
import shutil
import os
import yaml
import importlib
import subprocess
from lollms.config import TypedConfig, InstallOption
from lollms.main_config import LOLLMSConfig
from lollms.com import NotificationType, NotificationDisplayType, LoLLMsCom
from lollms.utilities import show_message_dialog
from lollms.types import BindingType
from lollms.client_session import Client
import urllib
import inspect
from datetime import datetime
from enum import Enum
from lollms.utilities import trace_exception

from tqdm import tqdm
from lollms.databases.models_database import ModelsDB
import sys

__author__ = "parisneo"
__github__ = "https://github.com/ParisNeo/lollms_bindings_zoo"
__copyright__ = "Copyright 2023, "
__license__ = "Apache 2.0"


class LLMBinding:
    
    def __init__(
                    self,
                    binding_dir:Path,
                    lollms_paths:LollmsPaths,
                    config:LOLLMSConfig, 
                    binding_config:TypedConfig,
                    installation_option:InstallOption=InstallOption.INSTALL_IF_NECESSARY,
                    supported_file_extensions='*.bin',
                    binding_type:BindingType=BindingType.TEXT_ONLY,
                    models_dir_names:list=None,
                    lollmsCom:LoLLMsCom=None
                ) -> None:
        
        self.binding_type           = binding_type

        self.binding_dir            = binding_dir
        self.binding_folder_name    = binding_dir.stem
        self.lollms_paths           = lollms_paths
        self.config                 = config
        self.binding_config         = binding_config

        self.lollmsCom = lollmsCom

        self.download_infos={}

        self.add_default_configurations(binding_config)

        self.interrogatorStorer = None
        self.supported_file_extensions          = supported_file_extensions
        self.seed                               = config["seed"]

        self.sync_configuration(self.binding_config, lollms_paths)
        # Installation
        if (not self.configuration_file_path.exists() or installation_option==InstallOption.FORCE_INSTALL) and installation_option!=InstallOption.NEVER_INSTALL:
            self.ShowBlockingMessage("Installing Binding")
            self.install()
            self.binding_config.config.save_config()
            self.HideBlockingMessage()
        else:
            self.load_binding_config()

        if models_dir_names is not None:
            config.lollms_paths.binding_models_paths=[config.lollms_paths.personal_models_path / models_dir_name for models_dir_name in models_dir_names]
            self.models_folders = config.lollms_paths.binding_models_paths
            self.models_dir_names = models_dir_names
        else:
            config.lollms_paths.binding_models_paths= [config.lollms_paths.personal_models_path / self.binding_folder_name]
            self.models_folders = config.lollms_paths.binding_models_paths
            self.models_dir_names = [self.binding_folder_name]
        for models_folder in self.models_folders:
            models_folder.mkdir(parents=True, exist_ok=True)


    def get_nb_tokens(self, prompt):
        """
        Counts the number of tokens in a prtompt
        """
        return len(self.tokenize(prompt))

    def searchModelFolder(self, model_name:str):
        for mn in self.models_folders:
            if mn.name in model_name.lower():
                return mn
        return self.models_folders[0]
    
    
    def searchModelPath(self, model_name:str):
        model_path=self.searchModelFolder(model_name)
        mp:Path = None
        for f in model_path.iterdir():
            a =  model_name.lower()
            b = f.name.lower()
            if a in b :
                mp = f
                break
        if not mp:
            return None
        
        if model_path.name in ["ggml","gguf"]:
            # model_path/str(model_name).split("/")[-1]
            if mp.is_dir():
                for f in mp.iterdir():
                    if not "mmproj" in f.stem and not f.is_dir():
                        if f.suffix==".reference":
                            with open(f,"r") as f:
                                return Path(f.read())
                        return f
            else:
                show_message_dialog("Warning","I detected that your model was installed with previous format.\nI'll just migrate it to thre new format.\nThe new format allows you to have multiple model variants and also have the possibility to use multimodal models.")
                model_root:Path = model_path.parent/model_path.stem
                model_root.mkdir(exist_ok=True, parents=True)
                shutil.move(model_path, model_root)
                model_path = model_root/model_path.name
                self.config.model_name = model_root.name
                root_path = model_root
                self.config.save_config()
                return model_path
        else:
            return mp
    
    def download_model(self, url, model_name, callback = None):
        folder_path = self.searchModelFolder(model_name)
        model_full_path = (folder_path/model_name)/str(url).split("/")[-1]
        # Check if file already exists in folder
        if model_full_path.exists():
            print("File already exists in folder")
        else:
            # Create folder if it doesn't exist
            folder_path.mkdir(parents=True, exist_ok=True)
            if not callback:
                progress_bar = tqdm(total=100, unit="%", unit_scale=True, desc=f"Downloading {url.split('/')[-1]}")
            # Define callback function for urlretrieve
            downloaded_size = [0]
            def report_progress(block_num, block_size, total_size):
                if callback:
                    downloaded_size[0] += block_size
                    callback(downloaded_size[0], total_size)
                else:
                    progress_bar.update(block_size/total_size)
            # Download file from URL to folder
            try:
                Path(model_full_path).parent.mkdir(parents=True, exist_ok=True)
                request.urlretrieve(url, model_full_path, reporthook=report_progress)
                print("File downloaded successfully!")
            except Exception as e:
                ASCIIColors.error("Error downloading file:", e)
                sys.exit(1)

    def reference_model(self, path):
        path = Path(str(path).replace("\\","/"))
        model_name  = path.stem+".reference"
        folder_path = self.searchModelFolder(model_name)/(path.stem if path.suffix.lower()=="gguf" else path.name)
        model_full_path = (folder_path / model_name)

        # Check if file already exists in folder
        if model_full_path.exists():
            print("File already exists in folder")
            return False
        else:
            # Create folder if it doesn't exist
            folder_path.mkdir(parents=True, exist_ok=True)
            with open(model_full_path,"w") as f:
                f.write(str(path))
            self.InfoMessage("Reference created, please make sure you don't delete or move the referenced file.\nThis can cause the link to be broken.\nNow I'm reloading the zoo.")
            return True


    def sync_configuration(self, binding_config:TypedConfig, lollms_paths:LollmsPaths):
        self.configuration_file_path = lollms_paths.personal_configuration_path/"bindings"/self.binding_folder_name/f"config.yaml"
        self.configuration_file_path.parent.mkdir(parents=True, exist_ok=True)
        binding_config.config.file_path = self.configuration_file_path


    def download_file(self, url, installation_path, callback=None):
        """
        Downloads a file from a URL, reports the download progress using a callback function, and displays a progress bar.

        Args:
            url (str): The URL of the file to download.
            installation_path (str): The path where the file should be saved.
            callback (function, optional): A callback function to be called during the download
                with the progress percentage as an argument. Defaults to None.
        """
        try:
            response = requests.get(url, stream=True)

            # Get the file size from the response headers
            total_size = int(response.headers.get('content-length', 0))

            with open(installation_path, 'wb') as file:
                downloaded_size = 0
                with tqdm(total=total_size, unit='B', unit_scale=True, ncols=80) as progress_bar:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            file.write(chunk)
                            downloaded_size += len(chunk)
                            if callback is not None:
                                callback(downloaded_size, total_size)
                            progress_bar.update(len(chunk))

            if callback is not None:
                callback(total_size, total_size)

            print("File downloaded successfully")
        except Exception as e:
            print("Couldn't download file:", str(e))

    def install_model(self, model_type:str, model_path:str, variant_name:str, client_id:int=None):
        print("Install model triggered")
        model_path = model_path.replace("\\","/")
        parts = model_path.split("/")
        if parts[2]=="huggingface.co":
            ASCIIColors.cyan("Hugging face model detected")
            model_name = parts[4]
        else:
            model_name = variant_name

        if model_type.lower() in model_path.lower():
            model_type:str=model_type
        else:
            mtt = None
            for mt in self.models_dir_names:
                if mt.lower() in  model_path.lower():
                    mtt = mt
                    break
            if mtt:
                model_type = mtt
            else:
                model_type:str=self.models_dir_names[0]

        progress = 0
        installation_dir = self.searchModelParentFolder(model_path.split('/')[-1], model_type)
        if model_type=="gptq" or  model_type=="awq" or model_type=="transformers":
            parts = model_path.split("/")
            if len(parts)==2:
                filename = parts[1]
            else:
                filename = parts[4]
            installation_path = installation_dir / filename

        elif model_type=="gpt4all":
            filename = variant_name
            model_path = "http://gpt4all.io/models/gguf/"+filename
            installation_root_dir = installation_dir / model_name 
            installation_root_dir.mkdir(parents=True, exist_ok=True)
            installation_path = installation_root_dir / filename
        else:
            filename = Path(model_path).name
            installation_root_dir = installation_dir / model_name 
            installation_root_dir.mkdir(parents=True, exist_ok=True)
            installation_path = installation_root_dir / filename
        print("Model install requested")
        print(f"Model path : {model_path}")
        print(f"Installation Path : {installation_path}")

        binding_folder = self.config["binding_name"]
        model_url = model_path
        signature = f"{model_name}_{binding_folder}_{model_url}"
        try:
            self.download_infos[signature]={
                "start_time":datetime.now(),
                "total_size":self.get_file_size(model_path),
                "downloaded_size":0,
                "progress":0,
                "speed":0,
                "cancel":False
            }
            
            if installation_path.exists():
                print("Error: Model already exists. please remove it first")
   
                self.lollmsCom.notify_model_install(
                            installation_path,
                            model_name,
                            binding_folder,
                            model_url,
                            self.download_infos[signature]['start_time'].strftime("%Y-%m-%d %H:%M:%S"),
                            self.download_infos[signature]['total_size'],
                            self.download_infos[signature]['downloaded_size'],
                            self.download_infos[signature]['progress'],
                            self.download_infos[signature]['speed'],
                            client_id,
                            status=True,
                            error="",
                             )

                return

            
            def callback(downloaded_size, total_size):
                progress = (downloaded_size / total_size) * 100
                now = datetime.now()
                dt = (now - self.download_infos[signature]['start_time']).total_seconds()
                speed = downloaded_size/dt
                self.download_infos[signature]['downloaded_size'] = downloaded_size
                self.download_infos[signature]['speed'] = speed

                if progress - self.download_infos[signature]['progress']>2:
                    self.download_infos[signature]['progress'] = progress
                    self.lollmsCom.notify_model_install(
                                installation_path,
                                model_name,
                                binding_folder,
                                model_url,
                                self.download_infos[signature]['start_time'].strftime("%Y-%m-%d %H:%M:%S"),
                                self.download_infos[signature]['total_size'],
                                self.download_infos[signature]['downloaded_size'],
                                self.download_infos[signature]['progress'],
                                self.download_infos[signature]['speed'],
                                client_id,
                                status=True,
                                error="",
                                )                    
                
                if self.download_infos[signature]["cancel"]:
                    raise Exception("canceled")
                    
                
            try:
                self.download_model(model_path, model_name, callback)
            except Exception as ex:
                ASCIIColors.warning(str(ex))
                trace_exception(ex)
                self.lollmsCom.notify_model_install(
                            installation_path,
                            model_name,
                            binding_folder,
                            model_url,
                            self.download_infos[signature]['start_time'].strftime("%Y-%m-%d %H:%M:%S"),
                            self.download_infos[signature]['total_size'],
                            self.download_infos[signature]['downloaded_size'],
                            self.download_infos[signature]['progress'],
                            self.download_infos[signature]['speed'],
                            client_id,
                            status=False,
                            error="Canceled",
                            )

                del self.download_infos[signature]
                try:
                    if installation_path.is_dir():
                        shutil.rmtree(installation_path)
                    else:
                        installation_path.unlink()
                except Exception as ex:
                    trace_exception(ex)
                    ASCIIColors.error(f"Couldn't delete file. Please try to remove it manually.\n{installation_path}")
                return
   
            self.lollmsCom.notify_model_install(
                        installation_path,
                        model_name,
                        binding_folder,
                        model_url,
                        self.download_infos[signature]['start_time'].strftime("%Y-%m-%d %H:%M:%S"),
                        self.download_infos[signature]['total_size'],
                        self.download_infos[signature]['total_size'],
                        100,
                        self.download_infos[signature]['speed'],
                        client_id,
                        status=True,
                        error="",
                        )
            del self.download_infos[signature]
        except Exception as ex:
            trace_exception(ex)
            self.lollmsCom.notify_model_install(
                        installation_path,
                        model_name,
                        binding_folder,
                        model_url,
                        '',
                        0,
                        0,
                        0,
                        0,
                        client_id,
                        status=False,
                        error=str(ex),
                        )

    def add_default_configurations(self, binding_config:TypedConfig):
        binding_config.addConfigs([
            {"name":"model_name","type":"str","value":'', "help":"Last known model for fast model recovery"},
            {"name":"model_template","type":"text","value":'', "help":"The template for the currently used model (optional)"},
            {"name":"clip_model_name","type":"str","value":'ViT-L-14/openai','options':["ViT-L-14/openai","ViT-H-14/laion2b_s32b_b79k"], "help":"Clip model to be used for images understanding"},
            {"name":"caption_model_name","type":"str","value":'blip-large','options':['blip-base', 'git-large-coco', 'blip-large','blip2-2.7b', 'blip2-flan-t5-xl'], "help":"Clip model to be used for images understanding"},
            {"name":"vqa_model_name","type":"str","value":'Salesforce/blip-vqa-capfilt-large','options':['Salesforce/blip-vqa-capfilt-large', 'Salesforce/blip-vqa-base', 'Salesforce/blip-image-captioning-large','Salesforce/blip2-opt-2.7b', 'Salesforce/blip2-flan-t5-xxl'], "help":"Salesforce question/answer model"},
        ])

    def InfoMessage(self, content, client_id=None, verbose:bool=True):
        if self.lollmsCom:
            return self.lollmsCom.InfoMessage(content=content, client_id=client_id, verbose=verbose)
        ASCIIColors.white(content)

    def ShowBlockingMessage(self, content, client_id=None, verbose:bool=True):
        if self.lollmsCom:
            return self.lollmsCom.ShowBlockingMessage(content=content, client_id=client_id, verbose=verbose)
        ASCIIColors.white(content)
        
    def HideBlockingMessage(self, client_id=None, verbose:bool=True):
        if self.lollmsCom:
            return self.lollmsCom.HideBlockingMessage(client_id=client_id, verbose=verbose)

    def info(self, content, duration:int=4, client_id=None, verbose:bool=True):
        if self.lollmsCom:
            return self.lollmsCom.info(content=content, duration=duration, client_id=client_id, verbose=verbose)
        ASCIIColors.info(content)

    def warning(self, content, duration:int=4, client_id=None, verbose:bool=True):
        if self.lollmsCom:
            return self.lollmsCom.warning(content=content, duration=duration, client_id=client_id, verbose=verbose)
        ASCIIColors.warning(content)

    def success(self, content, duration:int=4, client_id=None, verbose:bool=True):
        if self.lollmsCom:
            return self.lollmsCom.success(content=content, duration=duration, client_id=client_id, verbose=verbose)
        ASCIIColors.success(content)
        
    def error(self, content, duration:int=4, client_id=None, verbose:bool=True):
        if self.lollmsCom:
            return self.lollmsCom.error(content=content, duration=duration, client_id=client_id, verbose=verbose)
        ASCIIColors.error(content)
        
    def notify( self,                        
                content, 
                notification_type:NotificationType=NotificationType.NOTIF_SUCCESS, 
                duration:int=4, 
                client_id=None, 
                display_type:NotificationDisplayType=NotificationDisplayType.TOAST,
                verbose=True
            ):
        if self.lollmsCom:
            return self.lollmsCom.notify(content=content, notification_type=notification_type, duration=duration, client_id=client_id, display_type=display_type, verbose=verbose)
        ASCIIColors.white(content)


    def settings_updated(self):
        """
        To be implemented by the bindings
        """
        pass

    async def handle_request(self, data: dict, client:Client=None) -> Dict[str, Any]:
        """
        Handle client requests.

        Args:
            data (dict): A dictionary containing the request data.
            client (Client): A refertence to the client asking for this request.

        Returns:
            dict: A dictionary containing the response, including at least a "status" key.

        This method should be implemented by a class that inherits from this one.

        Example usage:
        ```
        handler = YourHandlerClass()
        client = checkaccess(lollmsServer, client_id)
        request_data = {"command": "some_command", "parameters": {...}}
        response = handler.handle_request(request_data, client)
        ```
        """        
        return {"status":True}

    def print_class_attributes(self, cls, show_layers=False):
        for attr in cls.__dict__:
            if isinstance(attr, property) or isinstance(attr, type):
                continue
            value = getattr(cls, attr)
            if attr!="tensor_file_map": 
                ASCIIColors.red(f"{attr}: ",end="")
                ASCIIColors.yellow(f"{value}")
            elif show_layers:
                ASCIIColors.red(f"{attr}: ")
                for k in value.keys():
                    ASCIIColors.yellow(f"{k}")
                
    def get_parameter_info(self, cls):
        # Get the signature of the class
        sig = inspect.signature(cls)
        
        # Print each parameter name and value
        for name, param in sig.parameters.items():
            if param.default is not None:
                print(f"{name}: {param.default}")
            else:
                print(f"{name}: Not specified")

    def __str__(self) -> str:
        return self.config["binding_name"]+f"({self.config['model_name']})"
    
    def download_and_install_wheel(self, url):
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()

        try:
            # Download the wheel file
            response = requests.get(url)
            if response.status_code == 200:
                # Save the downloaded file to the temporary directory
                wheel_path = os.path.join(temp_dir, 'package.whl')
                with open(wheel_path, 'wb') as file:
                    file.write(response.content)

                # Install the wheel file using pip
                subprocess.check_call(['pip', 'install', wheel_path])

                # Clean up the temporary directory
                shutil.rmtree(temp_dir)
                print('Installation completed successfully.')
            else:
                print('Failed to download the file.')

        except Exception as e:
            print('An error occurred during installation:', str(e))
            shutil.rmtree(temp_dir)

    def get_file_size(self, url):
        # Send a HEAD request to retrieve file metadata
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        req = urllib.request.Request(url, headers=headers)
        response = urllib.request.urlopen(req)
        # response = urllib.request.urlopen(url, headers=headers)
        
        # Extract the Content-Length header value
        file_size = response.headers.get('Content-Length')
        
        # Convert the file size to integer
        if file_size:
            file_size = int(file_size)
        
        return file_size
    
    def build_model(self, model_name=None):
        """
        Build the model.

        This method is responsible for constructing the model for the LOLLMS class.

        Returns:
            the model
        """        
        if model_name is not None:
            self.model_name = model_name
        else:
            self.model_name = self.config.model_name
    
    def destroy_model(self):
        """
        destroys the current model
        """
        pass

    def install(self):
        """
        Installation procedure (to be implemented)
        """
        ASCIIColors.blue("*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*")
        ASCIIColors.red(f"Installing {self.binding_folder_name}")
        ASCIIColors.blue("*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*")

    def uninstall(self):
        """
        UnInstallation procedure (to be implemented)
        """
        ASCIIColors.blue("*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*")
        ASCIIColors.red(f"UnInstalling {self.binding_folder_name}")
        ASCIIColors.blue("*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*")

    def searchModelParentFolder(self, model_name:str, model_type=None):
        model_path=None
        if model_type is not None:
            for mn in self.models_folders:
                if mn.name.lower() == model_type.lower():
                    return mn
        for mn in self.models_folders:
            if mn.name in model_name.lower():
                model_path = mn
                break
        if model_path is None:
            model_path = self.models_folders[0]
        return model_path

    """
    def searchModelPath(self, model_name:str):
        model_path=None
        for mn in self.models_folders:
            for f in mn.iterdir():
                if model_name.lower().replace("-gguf","").replace("-ggml","") in str(f).lower():
                    return f


        model_path = self.models_folders[0]/model_name
        return model_path
    """
    def get_model_path(self):
        """
        Retrieves the path of the model based on the configuration.

        If the model name ends with ".reference", it reads the model path from a file.
        Otherwise, it constructs the model path based on the configuration.

        Returns:
            str: The path of the model.
        """
        if self.config.model_name is None:
            return None
        
 
        model_path = self.searchModelPath(self.config.model_name)

        return model_path

    
    def get_current_seed(self):
        return self.seed
    
    def load_binding_config(self):
        """
        Load the content of local_config.yaml file.

        The function reads the content of the local_config.yaml file and returns it as a Python dictionary.

        Args:
            None

        Returns:
            dict: A dictionary containing the loaded data from the local_config.yaml file.
        """
        try:
            self.binding_config.config.load_config()
        except:
            self.binding_config.config.save_config()
        self.binding_config.sync()

    def save_config_file(self, path):
        """
        Load the content of local_config.yaml file.

        The function reads the content of the local_config.yaml file and returns it as a Python dictionary.

        Args:
            None

        Returns:
            dict: A dictionary containing the loaded data from the local_config.yaml file.
        """     
        self.binding_config.config.save_config(self.configuration_file_path)

    def interrogate_blip(self, images):
        if self.interrogatorStorer is None:
            from lollms.image_gen_modules.clip_interrogator import InterrogatorStorer
            self.interrogatorStorer = InterrogatorStorer(self.binding_config.clip_model_name, self.binding_config.caption_model_name)
        descriptions = []
        for image in images:
            descriptions.append(self.interrogatorStorer.interrogate(image))
        return descriptions

    def qna_blip(self, images, question=""):
        if self.interrogatorStorer is None:
            from lollms.image_gen_modules.blip_vqa import BlipInterrogatorStorer
            self.interrogatorStorer = BlipInterrogatorStorer()
        descriptions = []
        for image in images:
            descriptions.append(self.interrogatorStorer.interrogate(image,question))
        return descriptions

    def generate_with_images(self, 
                 prompt:str,
                 images:list=[],
                 n_predict: int = 128,
                 callback: Callable[[str, int, dict], bool] = None,
                 verbose: bool = False,
                 **gpt_params ):
        """Generates text out of a prompt and a bunch of images
        This should be implemented by child class

        Args:
            prompt (str): The prompt to use for generation
            images(list): A list of images to interpret
            n_predict (int, optional): Number of tokens to prodict. Defaults to 128.
            callback (Callable[[str, int, dict], None], optional): A callback function that is called everytime a new text element is generated. Defaults to None.
            verbose (bool, optional): If true, the code will spit many informations about the generation process. Defaults to False.
        """
        pass
    


    def generate(self, 
                 prompt:str,
                 n_predict: int = 128,
                 callback: Callable[[str, int, dict], bool] = None,
                 verbose: bool = False,
                 **gpt_params ):
        """Generates text out of a prompt
        This should be implemented by child class

        Args:
            prompt (str): The prompt to use for generation
            n_predict (int, optional): Number of tokens to prodict. Defaults to 128.
            callback (Callable[[str, int, dict], None], optional): A callback function that is called everytime a new text element is generated. Defaults to None.
            verbose (bool, optional): If true, the code will spit many informations about the generation process. Defaults to False.
        """
        pass
    
    def tokenize(self, prompt:str):
        """
        Tokenizes the given prompt using the model's tokenizer.

        Args:
            prompt (str): The input prompt to be tokenized.

        Returns:
            list: A list of tokens representing the tokenized prompt.
        """
        return prompt.split(" ")

    def detokenize(self, tokens_list:list):
        """
        Detokenizes the given list of tokens using the model's tokenizer.

        Args:
            tokens_list (list): A list of tokens to be detokenized.

        Returns:
            str: The detokenized text as a string.
        """
        return " ".join(tokens_list)


    def embed(self, text):
        """
        Computes text embedding
        Args:
            text (str): The text to be embedded.
        Returns:
            List[float]
        """
        pass


    def list_models(self):
        """Lists the models for this binding
        """
        models = []
        for models_folder in self.models_folders:
            if models_folder.name in ["ggml","gguf","gpt4all"]:
                models+=[f.name for f in models_folder.iterdir() if f.is_dir() and not f.stem.startswith(".") or f.suffix==".reference"]
            else:
                models+=[f.name for f in models_folder.iterdir() if f.is_dir() and not f.stem.startswith(".") or f.suffix==".reference"]
        return models
    

    def get_available_models(self, app:LoLLMsCom=None):
        # Create the file path relative to the child class's directory
        full_data = []
        for models_dir_name in self.models_dir_names:
            self.models_db = ModelsDB(self.lollms_paths.models_zoo_path/f"{models_dir_name}.db")
            full_data+=self.models_db.query()
        
        return full_data

    def search_models(self, app:LoLLMsCom=None):
        # Create the file path relative to the child class's directory
        full_data = []
        for models_dir_name in self.models_dir_names:
            self.models_db = ModelsDB(self.lollms_paths.models_zoo_path/f"{models_dir_name}.db")
            full_data+=self.models_db.query()
        
        return full_data           

    @staticmethod
    def vram_usage():
        try:
            output = subprocess.check_output(['nvidia-smi', '--query-gpu=memory.total,memory.used,gpu_name', '--format=csv,nounits,noheader'])
            lines = output.decode().strip().split('\n')
            vram_info = [line.split(',') for line in lines]
        except (subprocess.CalledProcessError, FileNotFoundError):
            return {
            "nb_gpus": 0
            }
        
        ram_usage = {
            "nb_gpus": len(vram_info)
        }
        
        if vram_info is not None:
            for i, gpu in enumerate(vram_info):
                ram_usage[f"gpu_{i}_total_vram"] = int(gpu[0])*1024*1024
                ram_usage[f"gpu_{i}_used_vram"] = int(gpu[1])*1024*1024
                ram_usage[f"gpu_{i}_model"] = gpu[2].strip()
        else:
            # Set all VRAM-related entries to None
            ram_usage["gpu_0_total_vram"] = None
            ram_usage["gpu_0_used_vram"] = None
            ram_usage["gpu_0_model"] = None
        
        return ram_usage

    @staticmethod
    def clear_cuda():
        import torch
        ASCIIColors.red("*-*-*-*-*-*-*-*")
        ASCIIColors.red("Cuda VRAM usage")
        ASCIIColors.red("*-*-*-*-*-*-*-*")
        print(LLMBinding.vram_usage())
        try:
            torch.cuda.empty_cache()
            ASCIIColors.green("Cleared cache")
        except Exception as ex:
            ASCIIColors.error("Couldn't clear cuda memory")
        ASCIIColors.red("*-*-*-*-*-*-*-*")
        ASCIIColors.red("Cuda VRAM usage")
        ASCIIColors.red("*-*-*-*-*-*-*-*")
        print(LLMBinding.vram_usage())


# ===============================

class BindingBuilder:
    def build_binding(
                        self, 
                        config: LOLLMSConfig, 
                        lollms_paths:LollmsPaths,
                        installation_option:InstallOption=InstallOption.INSTALL_IF_NECESSARY,
                        lollmsCom=None
                    )->LLMBinding:

        binding:LLMBinding = self.getBinding(config, lollms_paths)
        return binding(
                config,
                lollms_paths=lollms_paths,
                installation_option = installation_option,
                lollmsCom=lollmsCom
                )
    
    def getBinding(
                        self, 
                        config: LOLLMSConfig, 
                        lollms_paths:LollmsPaths,
                    )->LLMBinding:
        
        if len(str(config.binding_name).split("/"))>1:
            binding_path = Path(config.binding_name)
        else:
            binding_path = lollms_paths.bindings_zoo_path / config["binding_name"]

        # define the full absolute path to the module
        absolute_path = binding_path.resolve()
        # infer the module name from the file path
        module_name = binding_path.stem
        # use importlib to load the module from the file path
        loader = importlib.machinery.SourceFileLoader(module_name, str(absolute_path / "__init__.py"))
        binding_module = loader.load_module()
        binding:LLMBinding = getattr(binding_module, binding_module.binding_name)
        return binding
    
class ModelBuilder:
    def __init__(self, binding:LLMBinding):
        self.binding = binding
        self.model = None
        self.build_model() 

    def build_model(self, model_name=None):
        self.model = self.binding.build_model(model_name)

    def get_model(self):
        return self.model

