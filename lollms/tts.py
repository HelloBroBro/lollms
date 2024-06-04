"""
Lollms TTS Module
=================

This module is part of the Lollms library, designed to provide Text-to-Speech (TTS) functionalities within the LollmsApplication framework. The base class `LollmsTTS` is intended to be inherited and implemented by other classes that provide specific TTS functionalities.

Author: ParisNeo, a computer geek passionate about AI
"""
from lollms.app import LollmsApplication
from lollms.utilities import PackageManager
from pathlib import Path
from ascii_colors import ASCIIColors
import re
try:
    if not PackageManager.check_package_installed("sounddevice"):
        # os.system("sudo apt-get install portaudio19-dev")
        PackageManager.install_package("sounddevice")
        PackageManager.install_package("wave")
except:
    # os.system("sudo apt-get install portaudio19-dev -y")
    PackageManager.install_package("sounddevice")
    PackageManager.install_package("wave")
try:
    import sounddevice as sd
    import wave
except:
    ASCIIColors.error("Couldn't load sound tools")
class LollmsTTS:
    """
    LollmsTTS is a base class for implementing Text-to-Speech (TTS) functionalities within the LollmsApplication.
    
    Attributes:
        app (LollmsApplication): The instance of the main Lollms application.
        voice (str): The voice model to be used for TTS.
        api_key (str): API key for accessing external TTS services (if needed).
        output_path (Path or str): Path where the output audio files will be saved.
    """
    
    def __init__(
                    self, 
                    name:str,
                    app: LollmsApplication, 
                    model="",
                    voice="",
                    api_key="",
                    output_path=None
                    ):
        """
        Initializes the LollmsTTS class with the given parameters.

        Args:
            app (LollmsApplication): The instance of the main Lollms application.
            model (str, optional): The speach generation model to be used for TTS. Defaults to "".
            voice (str, optional): The voice model to be used for TTS. Defaults to "alloy".
            api_key (str, optional): API key for accessing external TTS services. Defaults to an empty string.
            output_path (Path or str, optional): Path where the output audio files will be saved. Defaults to None.
        """
        self.name = name
        self.ready = False
        self.app = app
        self.model = model
        self.voice = voice
        self.api_key = api_key
        self.output_path = output_path
        self.voices = [] # To be filled by the child class
        self.models = [] # To be filled by the child class

    def tts_file(self, text, file_name_or_path, speaker=None, language="en")->str:
        """
        Converts the given text to speech and saves it to a file.

        Args:
            text (str): The text to be converted to speech.
            speaker (str): The speaker/voice model to be used.
            file_name_or_path (Path or str): The name or path of the output file.
            language (str, optional): The language of the text. Defaults to "en".
        """
        pass

    def tts_audio(self, text, speaker=None, file_name_or_path: Path | str = None, language="en", use_threading=False):
        """
        Converts the given text to speech and returns the audio data.

        Args:
            text (str): The text to be converted to speech.
            speaker (str): The speaker/voice model to be used.
            file_name_or_path (Path or str, optional): The name or path of the output file. Defaults to None.
            language (str, optional): The language of the text. Defaults to "en".
            use_threading (bool, optional): Whether to use threading for the operation. Defaults to False.
        """
        pass

    def stop(self):
        """
        Stops the current generation
        """
        pass

    @staticmethod
    def verify(app: LollmsApplication) -> bool:
        """
        Verifies if the TTS service is available.

        Args:
            app (LollmsApplication): The instance of the main Lollms application.

        Returns:
            bool: True if the service is available, False otherwise.
        """
        return True

    @staticmethod
    def install(app: LollmsApplication) -> bool:
        """
        Installs the necessary components for the TTS service.

        Args:
            app (LollmsApplication): The instance of the main Lollms application.

        Returns:
            bool: True if the installation was successful, False otherwise.
        """
        return True
    
    @staticmethod 
    def get(app: LollmsApplication) -> 'LollmsTTS':
        """
        Returns the LollmsTTS class.

        Args:
            app (LollmsApplication): The instance of the main Lollms application.

        Returns:
            LollmsTTS: The LollmsTTS class.
        """
        return LollmsTTS
    
    def get_voices(self):
        """
        Retrieves the available voices for TTS.

        Returns:
            list: A list of available voices.
        """
        return self.voices
    
    def get_devices(self):
        devices =  sd.query_devices()

        return {
            "status": True,
            "device_names": [device['name'] for device in devices if device["max_output_channels"]>0],
            "device_indexes": [device['index'] for device in devices if device["max_output_channels"]>0]
        }
    
    @staticmethod
    def clean_text(text):
        # Remove HTML tags
        text = re.sub(r'<.*?>', '', text)
        # Remove code blocks (assuming they're enclosed in backticks or similar markers)
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        text = re.sub(r'`.*?`', '', text)
        # Remove any remaining code-like patterns (this can be adjusted as needed)
        text = re.sub(r'[\{\}\[\]\(\)<>]', '', text)  
        text = text.replace("\\","")      
        return text
