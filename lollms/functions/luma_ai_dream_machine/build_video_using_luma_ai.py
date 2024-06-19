# Lollms function call definition file
# File Name: luma_ai_dream_machine_video_creator.py
# Author: ParisNeo
# Description: This function opens the Luma AI Dream Machine webpage, navigates to the input section, and inputs a text prompt to create a video. If the user is not logged in, it prompts the user to log in.

# Import pathlib for file path operations
from pathlib import Path

# Import necessary libraries
from functools import partial
from typing import Dict
from lollms.utilities import PackageManager
from ascii_colors import trace_exception

# Ensure pyautogui is installed
if not PackageManager.check_package_installed("pyautogui"):
    PackageManager.install_package("pyautogui")

# Now we can import the library
import pyautogui
import webbrowser
import time

def luma_ai_dream_machine_video_creator(prompt: str) -> str:
    """
    Opens the Luma AI Dream Machine webpage, navigates to the input section, and inputs a text prompt to create a video.
    If the user is not logged in, it prompts the user to log in.
    
    Parameters:
    prompt (str): The text prompt to generate the video.
    
    Returns:
    str: Success message or login prompt.
    """
    try:
        # Open the Luma AI Dream Machine webpage
        webbrowser.open("https://lumalabs.ai/dream-machine/creations")
        time.sleep(2)  # Wait for the page to load

        # Locate the input section and type the prompt
        input_image_path = Path(__file__).parent/"input_section_image.png"  # Replace with the actual path to your image
        if not input_image_path.exists():
            raise FileNotFoundError("Input section image not found")

        input_location = pyautogui.locateOnScreen(str(input_image_path))
        
        if input_location:
            pyautogui.click(input_location)
            pyautogui.typewrite(prompt)
            pyautogui.press('enter')
            return "Video creation in progress!"
        else:
            return "Please log in to Luma AI Dream Machine to create a video."
    except Exception as e:
        return "Please log in to Luma AI Dream Machine to create a video."

def luma_ai_dream_machine_video_creator_function() -> Dict:
    return {
        "function_name": "luma_ai_dream_machine_video_creator",
        "function": luma_ai_dream_machine_video_creator,
        "function_description": "Creates a video from a text prompt using Luma AI Dream Machine.",
        "function_parameters": [{"name": "prompt", "type": "str"}]
    }
