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

def build_image(prompt, width, height, self:APScript, client:Client):
    try:
        if self.personality_config.image_generation_engine=="autosd":
            if not hasattr(self, "sd"):
                from lollms.services.sd.lollms_sd import LollmsSD
                self.step_start("Loading ParisNeo's fork of AUTOMATIC1111's stable diffusion service")
                self.sd = LollmsSD(self.personality.app, self.personality.name, max_retries=-1,auto_sd_base_url=self.personality.config.sd_base_url)
                self.step_end("Loading ParisNeo's fork of AUTOMATIC1111's stable diffusion service")
            file, infos = self.sd.paint(
                            prompt, 
                            "",
                            self.personality.image_files,
                            width = width,
                            height = height,
                            output_path=client.discussion.discussion_folder
                        )
        elif self.personality_config.image_generation_engine in ["dall-e-2", "dall-e-3"]:
            if not hasattr(self, "dalle"):
                from lollms.services.dalle.lollms_dalle import LollmsDalle
                self.step_start("Loading dalle service")
                self.dalle = LollmsDalle(self.personality.app, self.personality.config.dall_e_key, self.personality_config.image_generation_engine)
                self.step_end("Loading dalle service")
            self.step_start("Painting")
            file = self.dalle.paint(
                            prompt, 
                            width = width,
                            height = height,
                            output_path=client.discussion.discussion_folder
                        )
            self.step_end("Painting")

        file = str(file)
        escaped_url =  discussion_path_to_url(file)
        return f'\n![]({escaped_url})'
    except Exception as ex:
        trace_exception(ex)
        return "Couldn't generate image. Make sure Auto1111's stable diffusion service is installed"