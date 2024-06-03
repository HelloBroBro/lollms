# Lollms function call definition file

# Required imports
from functools import partial
from lollms.utilities import PackageManager
from ascii_colors import trace_exception

# Ensure pyautogui is installed
if not PackageManager.check_package_installed("pyautogui"):
    PackageManager.install_package("pyautogui")

import pyautogui
import webbrowser
import time

def open_and_fill_udio(song_description: str, lyrics: str) -> str:
    """
    Opens the udio.com page, interacts with the UI to fill in the song description and lyrics fields.
    
    Parameters:
    - song_description (str): The description of the song.
    - lyrics (str): The lyrics of the song.
    
    Returns:
    - str: Success message or exception trace.
    """
    try:
        # Open the specified webpage
        webbrowser.open('https://udio.com')
        time.sleep(4)  # Wait for the page to load

        # Click the input field near the "Create" button
        # Adjust the x, y coordinates based on your screen resolution
        pyautogui.click(x=500, y=110)

        # Fill the song description field
        pyautogui.write(song_description)

        # Select the "Custom" option
        pyautogui.click(x=400, y=300)

        pyautogui.click(x=400, y=400)

        # Fill the lyrics field
        pyautogui.write(lyrics)

        # Start generation
        pyautogui.click(x=1660, y=120)

        pyautogui.click(x=500, y=120)
        return "Successfully filled the song description and lyrics."
    except Exception as e:
        return trace_exception(e)

def open_and_fill_udio_function():
    return {
        "function_name": "open_and_fill_udio",
        "function": open_and_fill_udio,
        "function_description": "Opens udio.com page and fills in the song description and lyrics fields to start generating the music.",
        "function_parameters": [
            {"name": "song_description", "type": "str", "description":"a list of tags describing the song style and vibes. Make it short"},
            {"name": "lyrics", "type": "str","description":"The lyrics of the song"}
        ]
    }

if __name__ == "__main__":
    # Test the function with sample data
    song_description = "A beautiful song about nature."
    lyrics = "The sun sets over the hills, birds sing their evening song."
    result = open_and_fill_udio(song_description, lyrics)
    print(result)
