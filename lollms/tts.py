"""
Lollms TTS Module
=================

This module is part of the Lollms library, designed to provide Text-to-Speech (TTS) functionalities within the LollmsApplication framework. The base class `LollmsTTS` is intended to be inherited and implemented by other classes that provide specific TTS functionalities.

Author: ParisNeo, a computer geek passionate about AI
"""
from lollms.app import LollmsApplication
from pathlib import Path

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
        self.ready = False
        self.app = app
        self.model = model
        self.voice = voice
        self.api_key = api_key
        self.output_path = output_path
        self.voices = [] # To be filled by the child class
        self.models = [] # To be filled by the child class

    def tts_to_file(self, text, speaker, file_name_or_path, language="en"):
        """
        Converts the given text to speech and saves it to a file.

        Args:
            text (str): The text to be converted to speech.
            speaker (str): The speaker/voice model to be used.
            file_name_or_path (Path or str): The name or path of the output file.
            language (str, optional): The language of the text. Defaults to "en".
        """
        pass

    def tts_to_audio(self, text, speaker, file_name_or_path: Path | str = None, language="en", use_threading=False):
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