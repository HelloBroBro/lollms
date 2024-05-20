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

def summon_personality(member_id:int, prompt: str, previous_discussion_text:str, context_details, callback, processor:APScript, client:Client):
    members:List[AIPersonality] = processor.personality.app.mounted_personalities
    processor.personality.app.personality = members[member_id]
    members[member_id].callback=callback
    members[member_id].new_message("")
    processor.personality.app.handle_generate_msg(client.client_id, {"prompt":prompt})
    processor.personality.app.personality = processor.personality
    return "Execution done"


def summon_personality_function(processor, callback, previous_discussion_text, context_details, client):
        return {
                "function_name": "summon_personality",
                "function": partial(summon_personality, previous_discussion_text=previous_discussion_text, callback=callback, processor=processor, context_details=context_details, client=client),
                "function_description": "Summon a personality by id and prompting it to do something.",
                "function_parameters": [{"name": "member_id", "type": "int"},{"name": "prompt", "type": "str"}] 
            }
