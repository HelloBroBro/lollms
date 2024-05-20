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
from lollms.personality import AIPersonality
from typing import List
def list_personalities(processor:APScript, client:Client):
    members:List[AIPersonality] = processor.personality.app.mounted_personalities
    collective_infos = "Members information:\n"
    for i,drone in enumerate(members):
        if drone.name!=processor.personality.name:
            collective_infos +=  f"member id: {i}\n"
            collective_infos +=  f"member name: {drone.name}\n"
            collective_infos +=  f"member description: {drone.personality_description[:126]}...\n"
    return collective_infos


def list_personalities_function(processor, client):
        return {
                "function_name": "list_personalities",
                "function": partial(list_personalities, processor=processor, client=client),
                "function_description": "Lists the mounted ersonalities in the current sessions.",
                "function_parameters": [] 
            }
