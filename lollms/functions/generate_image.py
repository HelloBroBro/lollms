from lollms.utilities import PackageManager, find_first_available_file_index, discussion_path_to_url
from lollms.client_session import Client
from lollms.personality import APScript
if not PackageManager.check_package_installed("pyautogui"):
    PackageManager.install_package("pyautogui")
if not PackageManager.check_package_installed("PyQt5"):
    PackageManager.install_package("PyQt5")
from ascii_colors import trace_exception
import cv2
import time
from PyQt5 import QtWidgets, QtGui, QtCore
import sys
from functools import partial

def build_image(prompt, antiprompt, width, height, processor:APScript, client:Client):
    try:
        if processor.personality.config.active_tti_service=="diffusers":
            if not processor.personality.app.tti:
                from lollms.services.diffusers.lollms_diffusers import LollmsDiffusers
                processor.step_start("Loading ParisNeo's fork of AUTOMATIC1111's stable diffusion service")
                processor.personality.app.tti = LollmsDiffusers(processor.personality.app, processor.personality.name, max_retries=-1,auto_sd_base_url=processor.personality.config.sd_base_url)
                processor.personality.app.sd = processor.personality.app.tti
                processor.step_end("Loading ParisNeo's fork of AUTOMATIC1111's stable diffusion service")
            file, infos = processor.personality.app.tti.paint(
                            prompt, 
                            antiprompt,
                            processor.personality.image_files,
                            width = width,
                            height = height,
                            output_path=client.discussion.discussion_folder
                        )
        elif processor.personality.config.active_tti_service=="autosd":
            if not processor.personality.app.tti:
                from lollms.services.sd.lollms_sd import LollmsSD
                processor.step_start("Loading ParisNeo's fork of AUTOMATIC1111's stable diffusion service")
                processor.personality.app.tti = LollmsSD(processor.personality.app, processor.personality.name, max_retries=-1,auto_sd_base_url=processor.personality.config.sd_base_url)
                processor.personality.app.sd = processor.personality.app.tti
                processor.step_end("Loading ParisNeo's fork of AUTOMATIC1111's stable diffusion service")
            file, infos = processor.personality.app.tti.paint(
                            prompt, 
                            antiprompt,
                            processor.personality.image_files,
                            width = width,
                            height = height,
                            output_path=client.discussion.discussion_folder
                        )
        elif processor.personality.config.active_tti_service=="dall-e":
            if not processor.personality.app.tti:
                from lollms.services.dalle.lollms_dalle import LollmsDalle
                processor.step_start("Loading dalle service")
                processor.personality.app.tti = LollmsDalle(processor.personality.app, processor.personality.config.dall_e_key, processor.personality.config.dall_e_generation_engine)
                processor.personality.app.dalle = processor.personality.app.tti
                processor.step_end("Loading dalle service")
            processor.step_start("Painting")
            file = processor.personality.app.tti.paint(
                            prompt, 
                            width = width,
                            height = height,
                            output_path=client.discussion.discussion_folder
                        )
            processor.step_end("Painting")

        file = str(file)
        escaped_url =  discussion_path_to_url(file)
        return f'\n![]({escaped_url})'
    except Exception as ex:
        trace_exception(ex)
        return "Couldn't generate image. Make sure Auto1111's stable diffusion service is installed"


def build_image_function(processor, client):
    return {
            "function_name": "build_image",
            "function": partial(build_image, processor=processor, client=client),
            "function_description": "Builds and shows an image from a prompt and width and height parameters. A square 1024x1024, a portrait woudl be 1024x1820 or landscape 1820x1024.",
            "function_parameters": [{"name": "prompt", "type": "str"}, {"name": "antiprompt", "type": "str"}, {"name": "width", "type": "int"}, {"name": "height", "type": "int"}]                
        }
