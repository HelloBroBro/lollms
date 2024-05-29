"""
Lollms TTI Module
=================

This module is part of the Lollms library, designed to provide Text-to-Image (TTI) functionalities within the LollmsApplication framework. The base class `LollmsTTI` is intended to be inherited and implemented by other classes that provide specific TTI functionalities.

Author: ParisNeo, a computer geek passionate about AI
"""

from lollms.app import LollmsApplication
from pathlib import Path
from typing import List, Dict

class LollmsTTI:
    """
    LollmsTTI is a base class for implementing Text-to-Image (TTI) functionalities within the LollmsApplication.
    
    Attributes:
        app (LollmsApplication): The instance of the main Lollms application.
        model (str): The TTI model to be used for image generation.
        api_key (str): API key for accessing external TTI services (if needed).
        output_path (Path or str): Path where the output image files will be saved.
        voices (List[str]): List of available voices for TTI (to be filled by the child class).
        models (List[str]): List of available models for TTI (to be filled by the child class).
    """
    
    def __init__(
                    self, 
                    app: LollmsApplication, 
                    model="",
                    api_key="",
                    output_path=None
                    ):
        """
        Initializes the LollmsTTI class with the given parameters.

        Args:
            app (LollmsApplication): The instance of the main Lollms application.
            model (str, optional): The TTI model to be used for image generation. Defaults to an empty string.
            api_key (str, optional): API key for accessing external TTI services. Defaults to an empty string.
            output_path (Path or str, optional): Path where the output image files will be saved. Defaults to None.
        """
        self.ready = False
        self.app = app
        self.model = model
        self.api_key = api_key
        self.output_path = output_path
        self.voices = [] # To be filled by the child class
        self.models = [] # To be filled by the child class

    def paint(self, 
                positive_prompt: str, 
                negative_prompt: str = "",
                width=512,
                height=512,
                images = [],
                generation_engine=None,
                output_path = None) -> List[Dict[str, str]]:
        """
        Generates images based on the given positive and negative prompts.

        Args:
            positive_prompt (str): The positive prompt describing the desired image.
            negative_prompt (str, optional): The negative prompt describing what should be avoided in the image. Defaults to an empty string.

        Returns:
            List[Dict[str, str]]: A list of dictionaries containing image paths, URLs, and metadata.
        """
        pass

    def paint_from_images(self, positive_prompt: str, images: List[str], negative_prompt: str = "") -> List[Dict[str, str]]:
        """
        Generates images based on the given positive prompt and reference images.

        Args:
            positive_prompt (str): The positive prompt describing the desired image.
            images (List[str]): A list of paths to reference images.
            negative_prompt (str, optional): The negative prompt describing what should be avoided in the image. Defaults to an empty string.

        Returns:
            List[Dict[str, str]]: A list of dictionaries containing image paths, URLs, and metadata.
        """
        pass

    @staticmethod
    def verify(app: LollmsApplication) -> bool:
        """
        Verifies if the TTI service is available.

        Args:
            app (LollmsApplication): The instance of the main Lollms application.

        Returns:
            bool: True if the service is available, False otherwise.
        """
        return True

    @staticmethod
    def install(app: LollmsApplication) -> bool:
        """
        Installs the necessary components for the TTI service.

        Args:
            app (LollmsApplication): The instance of the main Lollms application.

        Returns:
            bool: True if the installation was successful, False otherwise.
        """
        return True
    
    @staticmethod 
    def get(app: LollmsApplication) -> 'LollmsTTI':
        """
        Returns the LollmsTTI class.

        Args:
            app (LollmsApplication): The instance of the main Lollms application.

        Returns:
            LollmsTTI: The LollmsTTI class.
        """
        return LollmsTTI
