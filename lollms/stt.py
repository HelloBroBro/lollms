"""
Lollms STT Module
=================

This module is part of the Lollms library, designed to provide Speech-to-Text (STT) functionalities within the LollmsApplication framework. The base class `LollmsSTT` is intended to be inherited and implemented by other classes that provide specific STT functionalities.

Author: ParisNeo, a computer geek passionate about AI
"""

from lollms.app import LollmsApplication
from pathlib import Path

class LollmsSTT:
    """
    LollmsSTT is a base class for implementing Speech-to-Text (STT) functionalities within the LollmsApplication.
    
    Attributes:
        app (LollmsApplication): The instance of the main Lollms application.
        model (str): The STT model to be used for transcription.
        output_path (Path or str): Path where the output transcription files will be saved.
    """
    
    def __init__(
                    self, 
                    app: LollmsApplication, 
                    model="",
                    output_path=None
                    ):
        """
        Initializes the LollmsSTT class with the given parameters.

        Args:
            app (LollmsApplication): The instance of the main Lollms application.
            model (str, optional): The STT model to be used for transcription. Defaults to an empty string.
            output_path (Path or str, optional): Path where the output transcription files will be saved. Defaults to None.
        """
        self.ready = False
        self.app = app
        self.output_path = output_path
        self.model = model

    def transcribe(
                self,
                wav_path: str | Path,
                prompt=""
                ):
        """
        Transcribes the given audio file to text.

        Args:
            wav_path (str or Path): The path to the WAV audio file to be transcribed.
            prompt (str, optional): An optional prompt to guide the transcription. Defaults to an empty string.
        """
        pass

    @staticmethod
    def verify(app: LollmsApplication) -> bool:
        """
        Verifies if the STT service is available.

        Args:
            app (LollmsApplication): The instance of the main Lollms application.

        Returns:
            bool: True if the service is available, False otherwise.
        """
        return True

    @staticmethod
    def install(app: LollmsApplication) -> bool:
        """
        Installs the necessary components for the STT service.

        Args:
            app (LollmsApplication): The instance of the main Lollms application.

        Returns:
            bool: True if the installation was successful, False otherwise.
        """
        return True
    
    @staticmethod 
    def get(app: LollmsApplication) -> 'LollmsSTT':
        """
        Returns the LollmsSTT class.

        Args:
            app (LollmsApplication): The instance of the main Lollms application.

        Returns:
            LollmsSTT: The LollmsSTT class.
        """
        return LollmsSTT