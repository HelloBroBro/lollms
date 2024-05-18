######
# Project       : lollms
# File          : personality.py
# Author        : ParisNeo with the help of the community
# license       : Apache 2.0
# Description   :
# This is an interface class for lollms personalities.
######
from fastapi import Request
from datetime import datetime
from pathlib import Path
from lollms.config import InstallOption, TypedConfig, BaseConfig
from lollms.main_config import LOLLMSConfig
from lollms.paths import LollmsPaths
from lollms.binding import LLMBinding, BindingType
from lollms.utilities import PromptReshaper, PackageManager, discussion_path_to_url, process_ai_output, remove_text_from_string
from lollms.com import NotificationType, NotificationDisplayType
from lollms.client_session import Session, Client

import pkg_resources
from pathlib import Path
from PIL import Image
import re

from datetime import datetime
import importlib
import shutil
import subprocess
import yaml
from ascii_colors import ASCIIColors
import time
from lollms.types import MSG_TYPE, SUMMARY_MODE
import json
from typing import Any, List, Optional, Type, Callable, Dict, Any, Union
import json
from safe_store import TextVectorizer, GenericDataLoader, VisualizationMethod, VectorizationMethod, DocumentDecomposer
from functools import partial
import sys
from lollms.com import LoLLMsCom
from lollms.helpers import trace_exception
from lollms.utilities import PackageManager

from lollms.code_parser import compress_js, compress_python, compress_html


import requests
from bs4 import BeautifulSoup

def get_element_id(url, text):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    element = soup.find('span', text=text)
    if element:
        return element['id']
    else:
        return None

def craft_a_tag_to_specific_text(url, text, caption):
    # Encode the text to be used in the URL
    encoded_text = text.replace(' ', '%20')

    # Construct the URL with the anchor tag
    anchor_url = f"{url}#{encoded_text}"

    # Return the anchor tag
    return anchor_url

def is_package_installed(package_name):
    try:
        dist = pkg_resources.get_distribution(package_name)
        return True
    except pkg_resources.DistributionNotFound:
        return False


def install_package(package_name):
    try:
        # Check if the package is already installed
        __import__(package_name)
        print(f"{package_name} is already installed.")
    except ImportError:
        print(f"{package_name} is not installed. Installing...")

        # Install the package using pip
        subprocess.check_call(["pip", "install", package_name])

        print(f"{package_name} has been successfully installed.")


def fix_json(json_text):
    try:
        json_text.replace("}\n{","},\n{")
        # Try to load the JSON string
        json_obj = json.loads(json_text)
        return json_obj
    except json.JSONDecodeError as e:
        trace_exception(e)
class AIPersonality:

    # Extra
    def __init__(
                    self,
                    personality_package_path: str|Path,
                    lollms_paths:LollmsPaths,
                    config:LOLLMSConfig,
                    model:LLMBinding=None,
                    app:LoLLMsCom=None,
                    run_scripts=True,
                    selected_language=None,
                    is_relative_path=True,
                    installation_option:InstallOption=InstallOption.INSTALL_IF_NECESSARY,
                    callback: Callable[[str, MSG_TYPE, dict, list], bool]=None
                ):
        """
        Initialize an AIPersonality instance.

        Parameters:
        personality_package_path (str or Path): The path to the folder containing the personality package.

        Raises:
        ValueError: If the provided path is not a folder or does not contain a config.yaml file.
        """
        self.bot_says = ""

        self.lollms_paths = lollms_paths
        self.model = model
        self.config = config
        self.callback = callback
        self.app = app

        self.text_files = []
        self.image_files = []
        self.audio_files = []
        self.images_descriptions = []
        self.vectorizer = None

        self.installation_option = installation_option

        # Whisper to transcribe audio
        self.whisper = None

        # First setup a default personality
        # Version
        self._version = pkg_resources.get_distribution('lollms').version

        self.run_scripts = run_scripts

        #General information
        self._author: str = "ParisNeo"
        self._name: str = "lollms"
        self._user_name: str = "user"
        self._category: str = "General"
        self._category_desc: str = "General"
        self._language: str = "english"
        self._supported_languages: str = []
        self._selected_language: str = selected_language

        self._languages: List[dict]=[]

        # Conditionning
        self._personality_description: str = "This personality is a helpful and Kind AI ready to help you solve your problems"
        self._personality_conditioning: str = "\n".join([
            "!@>system:",
            "lollms (Lord of LLMs) is a smart and helpful Assistant built by the computer geek ParisNeo.",
            "It is compatible with many bindings to LLM models such as llama, gpt4all, gptj, autogptq etc.",
            "It can discuss with humans and assist them on many subjects.",
            "It runs locally on your machine. No need to connect to the internet.",
            "It answers the questions with precise details",
            "Its performance depends on the underlying model size and training.",
            "Try to answer with as much details as you can",
            "Date: {{date}}",
        ])
        self._welcome_message: str = "Welcome! I am lollms (Lord of LLMs) A free and open assistant built by ParisNeo. What can I do for you today?"
        self._include_welcome_message_in_discussion: bool = True
        self._user_message_prefix: str = "!@>human: "
        self._link_text: str = "\n"
        self._ai_message_prefix: str = "!@>lollms:"
        self._anti_prompts:list = [self.config.discussion_prompt_separator]

        # Extra
        self._dependencies: List[str] = []

        # Disclaimer
        self._disclaimer: str = ""
        self._help: str = ""
        self._commands: list = []

        # Default model parameters
        self._model_temperature: float = 0.1 # higher: more creative, lower more deterministic
        self._model_n_predicts: int = 2048 # higher: generates many words, lower generates
        self._model_top_k: int = 50
        self._model_top_p: float = 0.95
        self._model_repeat_penalty: float = 1.3
        self._model_repeat_last_n: int = 40

        self._processor_cfg: dict = {}

        self._logo: Optional[Image.Image] = None
        self._processor = None
        self._data = None



        if personality_package_path is None:
            self.config = {}
            self.assets_list = []
            self.personality_package_path = None
            return
        else:
            parts = str(personality_package_path).split("/")
            self._category = parts[0]
            if parts[0] == "custom_personalities":
                self.personality_package_path = self.lollms_paths.custom_personalities_path/parts[1]
            else:
                if is_relative_path:
                    self.personality_package_path = self.lollms_paths.personalities_zoo_path/personality_package_path
                else:
                    self.personality_package_path = Path(personality_package_path)

            # Validate that the path exists
            if not self.personality_package_path.exists():
                raise ValueError(f"Could not find the personality package:{self.personality_package_path}")

            # Validate that the path format is OK with at least a config.yaml file present in the folder
            if not self.personality_package_path.is_dir():
                raise ValueError(f"Personality package path is not a folder:{self.personality_package_path}")

            self.personality_folder_name = self.personality_package_path.stem


            self.personality_output_folder = lollms_paths.personal_outputs_path/self.name
            self.personality_output_folder.mkdir(parents=True, exist_ok=True)
            # Open and store the personality
            self.load_personality()



    def InfoMessage(self, content, duration:int=4, client_id=None, verbose:bool=True):
        if self.app:
            return self.app.InfoMessage(content=content, client_id=client_id, verbose=verbose)
        ASCIIColors.white(content)

    def ShowBlockingMessage(self, content, client_id=None, verbose:bool=True):
        if self.app:
            return self.app.ShowBlockingMessage(content=content, client_id=client_id, verbose=verbose)
        ASCIIColors.white(content)

    def HideBlockingMessage(self, client_id=None, verbose:bool=True):
        if self.app:
            return self.app.HideBlockingMessage(client_id=client_id, verbose=verbose)


    def info(self, content, duration:int=4, client_id=None, verbose:bool=True):
        if self.app:
            return self.app.info(content=content, duration=duration, client_id=client_id, verbose=verbose)
        ASCIIColors.info(content)

    def warning(self, content, duration:int=4, client_id=None, verbose:bool=True):
        if self.app:
            return self.app.warning(content=content, duration=duration, client_id=client_id, verbose=verbose)
        ASCIIColors.warning(content)

    def success(self, content, duration:int=4, client_id=None, verbose:bool=True):
        if self.app:
            return self.app.success(content=content, duration=duration, client_id=client_id, verbose=verbose)
        ASCIIColors.success(content)

    def error(self, content, duration:int=4, client_id=None, verbose:bool=True):
        if self.app:
            return self.app.error(content=content, duration=duration, client_id=client_id, verbose=verbose)
        ASCIIColors.error(content)

    def notify( self,
                content,
                notification_type:NotificationType=NotificationType.NOTIF_SUCCESS,
                duration:int=4,
                client_id=None,
                display_type:NotificationDisplayType=NotificationDisplayType.TOAST,
                verbose=True
            ):
        if self.app:
            return self.app.error(content=content, notification_type=notification_type, duration=duration, client_id=client_id, display_type=display_type, verbose=verbose)
        ASCIIColors.white(content)



    def new_message(self, message_text:str, message_type:MSG_TYPE= MSG_TYPE.MSG_TYPE_FULL, metadata=[], callback: Callable[[str, int, dict, list, Any], bool]=None):
        """This sends step rogress to front end

        Args:
            step_text (dict): The step progress in %
            callback (callable, optional): A callable with this signature (str, MSG_TYPE) to send the progress to. Defaults to None.
        """
        if not callback and self.callback:
            callback = self.callback

        if callback:
            callback(message_text, MSG_TYPE.MSG_TYPE_NEW_MESSAGE, parameters={'type':message_type.value,'metadata':metadata}, personality=self)

    def full(self, full_text:str, callback: Callable[[str, MSG_TYPE, dict, list], bool]=None):
        """This sends full text to front end

        Args:
            step_text (dict): The step text
            callback (callable, optional): A callable with this signature (str, MSG_TYPE) to send the text to. Defaults to None.
        """
        if not callback and self.callback:
            callback = self.callback

        if callback:
            callback(full_text, MSG_TYPE.MSG_TYPE_FULL)


    def full_invisible_to_ai(self, full_text:str, callback: Callable[[str, MSG_TYPE, dict, list], bool]=None):
        """This sends full text to front end (INVISIBLE to AI)

        Args:
            step_text (dict): The step text
            callback (callable, optional): A callable with this signature (str, MSG_TYPE) to send the text to. Defaults to None.
        """
        if not callback and self.callback:
            callback = self.callback

        if callback:
            callback(full_text, MSG_TYPE.MSG_TYPE_FULL_INVISIBLE_TO_AI)

    def full_invisible_to_user(self, full_text:str, callback: Callable[[str, MSG_TYPE, dict, list], bool]=None):
        """This sends full text to front end (INVISIBLE to user)

        Args:
            step_text (dict): The step text
            callback (callable, optional): A callable with this signature (str, MSG_TYPE) to send the text to. Defaults to None.
        """
        if not callback and self.callback:
            callback = self.callback

        if callback:
            callback(full_text, MSG_TYPE.MSG_TYPE_FULL_INVISIBLE_TO_USER)


    def build_prompt(self, prompt_parts:List[str], sacrifice_id:int=-1, context_size:int=None, minimum_spare_context_size:int=None):
        """
        Builds the prompt for code generation.

        Args:
            prompt_parts (List[str]): A list of strings representing the parts of the prompt.
            sacrifice_id (int, optional): The ID of the part to sacrifice.
            context_size (int, optional): The size of the context.
            minimum_spare_context_size (int, optional): The minimum spare context size.

        Returns:
            str: The built prompt.
        """
        if context_size is None:
            context_size = self.config.ctx_size
        if minimum_spare_context_size is None:
            minimum_spare_context_size = self.config.min_n_predict

        if sacrifice_id == -1 or len(prompt_parts[sacrifice_id])<50:
            return "\n".join([s for s in prompt_parts if s!=""])
        else:
            part_tokens=[]
            nb_tokens=0
            for i,part in enumerate(prompt_parts):
                tk = self.model.tokenize(part)
                part_tokens.append(tk)
                if i != sacrifice_id:
                    nb_tokens += len(tk)
            if len(part_tokens[sacrifice_id])>0:
                sacrifice_tk = part_tokens[sacrifice_id]
                sacrifice_tk= sacrifice_tk[-(context_size-nb_tokens-minimum_spare_context_size):]
                sacrifice_text = self.model.detokenize(sacrifice_tk)
            else:
                sacrifice_text = ""
            prompt_parts[sacrifice_id] = sacrifice_text
            return "\n".join([s for s in prompt_parts if s!=""])

    def add_collapsible_entry(self, title, content):
        return "\n".join(
        [
        f'<details class="flex w-fit rounded-xl border border-gray-200 bg-white shadow-sm dark:border-gray-800 dark:bg-gray-900 mb-3.5 max-w-full svelte-1escu1z" open="">',
        f'    <summary class="grid min-w-72 select-none grid-cols-[40px,1fr] items-center gap-2.5 p-2 svelte-1escu1z">',
        f'        <dl class="leading-4">',
        f'        <dd class="text-sm">{title}</dd>',
        f'        <dt class="flex items-center gap-1 truncate whitespace-nowrap text-[.82rem] text-gray-400">.Completed</dt>',
        f'        </dl>',
        f'    </summary>',
        f' <div class="content px-5 pb-5 pt-4">',
        content,
        f' </div>',
        f' </details>\n'
        ])

    def internet_search_with_vectorization(self, query, quick_search:bool=False):
        """
        Do internet search and return the result
        """
        from lollms.internet import internet_search_with_vectorization
        return internet_search_with_vectorization(
                                                    query,
                                                    internet_nb_search_pages=self.config.internet_nb_search_pages,
                                                    internet_vectorization_chunk_size=self.config.internet_vectorization_chunk_size,
                                                    internet_vectorization_overlap_size=self.config.internet_vectorization_overlap_size,
                                                    internet_vectorization_nb_chunks=self.config.internet_vectorization_nb_chunks,
                                                    model = self.model,
                                                    quick_search=quick_search
                                                    )

    def sink(self, s=None,i=None,d=None):
        pass

    def yes_no(self, question: str, context:str="", max_answer_length: int = 50, conditionning="") -> bool:
        """
        Analyzes the user prompt and answers whether it is asking to generate an image.

        Args:
            question (str): The user's message.
            max_answer_length (int, optional): The maximum length of the generated answer. Defaults to 50.
            conditionning: An optional system message to put at the beginning of the prompt
        Returns:
            bool: True if the user prompt is asking to generate an image, False otherwise.
        """
        return self.multichoice_question(question, ["no","yes"], context, max_answer_length, conditionning=conditionning)>0

    def multichoice_question(self, question: str, possible_answers:list, context:str = "", max_answer_length: int = 50, conditionning="") -> int:
        """
        Interprets a multi-choice question from a users response. This function expects only one choice as true. All other choices are considered false. If none are correct, returns -1.

        Args:
            question (str): The multi-choice question posed by the user.
            possible_ansers (List[Any]): A list containing all valid options for the chosen value. For each item in the list, either 'True', 'False', None or another callable should be passed which will serve as the truth test function when checking against the actual user input.
            max_answer_length (int, optional): Maximum string length allowed while interpreting the users' responses. Defaults to 50.
            conditionning: An optional system message to put at the beginning of the prompt

        Returns:
            int: Index of the selected option within the possible_ansers list. Or -1 if there was not match found among any of them.
        """
        choices = "\n".join([f"{i}. {possible_answer}" for i, possible_answer in enumerate(possible_answers)])
        elements = [conditionning] if conditionning!="" else []
        elements += [
                "!@>instructions:",
                "Answer this multi choices question.",
                "Answer with an id from the possible answers.",
                "Do not answer with an id outside this possible answers.",
        ]
        if context!="":
            elements+=[
                       "!@>Context:",
                        f"{context}",
                    ]
        elements += [
                f"!@>question: {question}",
                "!@>possible answers:",
                f"{choices}",
        ]
        elements += ["!@>answer:"]
        prompt = self.build_prompt(elements)

        gen = self.generate(prompt, max_answer_length, temperature=0.1, top_k=50, top_p=0.9, repeat_penalty=1.0, repeat_last_n=50, callback=self.sink).strip().replace("</s>","").replace("<s>","")
        selection = gen.strip().split()[0].replace(",","").replace(".","")
        self.print_prompt("Multi choice selection",prompt+gen)
        try:
            return int(selection)
        except:
            ASCIIColors.cyan("Model failed to answer the question")
            return -1

    def multichoice_ranking(self, question: str, possible_answers:list, context:str = "", max_answer_length: int = 50, conditionning="") -> int:
        """
        Ranks answers for a question from best to worst. returns a list of integers

        Args:
            question (str): The multi-choice question posed by the user.
            possible_ansers (List[Any]): A list containing all valid options for the chosen value. For each item in the list, either 'True', 'False', None or another callable should be passed which will serve as the truth test function when checking against the actual user input.
            max_answer_length (int, optional): Maximum string length allowed while interpreting the users' responses. Defaults to 50.
            conditionning: An optional system message to put at the beginning of the prompt

        Returns:
            int: Index of the selected option within the possible_ansers list. Or -1 if there was not match found among any of them.
        """
        choices = "\n".join([f"{i}. {possible_answer}" for i, possible_answer in enumerate(possible_answers)])
        elements = [conditionning] if conditionning!="" else []
        elements += [
                "!@>instructions:",
                "Answer this multi choices question.",
                "Answer with an id from the possible answers.",
                "Do not answer with an id outside this possible answers.",
                f"!@>question: {question}",
                "!@>possible answers:",
                f"{choices}",
        ]
        if context!="":
            elements+=[
                       "!@>Context:",
                        f"{context}",
                    ]

        elements += ["!@>answer:"]
        prompt = self.build_prompt(elements)

        gen = self.generate(prompt, max_answer_length, temperature=0.1, top_k=50, top_p=0.9, repeat_penalty=1.0, repeat_last_n=50).strip().replace("</s>","").replace("<s>","")
        self.print_prompt("Multi choice ranking",prompt+gen)
        if gen.index("]")>=0:
            try:
                ranks = eval(gen.split("]")[0]+"]")
                return ranks
            except:
                ASCIIColors.red("Model failed to rank inputs")
                return None
        else:
            ASCIIColors.red("Model failed to rank inputs")
            return None

    def step_start(self, step_text, callback: Callable[[str, MSG_TYPE, dict, list], bool]=None):
        """This triggers a step start

        Args:
            step_text (str): The step text
            callback (callable, optional): A callable with this signature (str, MSG_TYPE) to send the step start to. Defaults to None.
        """
        if not callback and self.callback:
            callback = self.callback

        if callback:
            callback(step_text, MSG_TYPE.MSG_TYPE_STEP_START)

    def step_end(self, step_text, status=True, callback: Callable[[str, int, dict, list], bool]=None):
        """This triggers a step end

        Args:
            step_text (str): The step text
            callback (callable, optional): A callable with this signature (str, MSG_TYPE) to send the step end to. Defaults to None.
        """
        if not callback and self.callback:
            callback = self.callback

        if callback:
            callback(step_text, MSG_TYPE.MSG_TYPE_STEP_END, {'status':status})

    def step(self, step_text, callback: Callable[[str, MSG_TYPE, dict, list], bool]=None):
        """This triggers a step information

        Args:
            step_text (str): The step text
            callback (callable, optional): A callable with this signature (str, MSG_TYPE, dict, list) to send the step to. Defaults to None.
            The callback has these fields:
            - chunk
            - Message Type : the type of message
            - Parameters (optional) : a dictionary of parameters
            - Metadata (optional) : a list of metadata
        """
        if not callback and self.callback:
            callback = self.callback

        if callback:
            callback(step_text, MSG_TYPE.MSG_TYPE_STEP)

    def print_prompt(self, title, prompt):
        ASCIIColors.red("*-*-*-*-*-*-*-* ", end="")
        ASCIIColors.red(title, end="")
        ASCIIColors.red(" *-*-*-*-*-*-*-*")
        ASCIIColors.yellow(prompt)
        ASCIIColors.red(" *-*-*-*-*-*-*-*")



    def fast_gen_with_images(self, prompt: str, images:list, max_generation_size: int=None, placeholders: dict = {}, sacrifice: list = ["previous_discussion"], debug: bool  = False, callback=None, show_progress=False) -> str:
        """
        Fast way to generate text from text and images

        This method takes in a prompt, maximum generation size, optional placeholders, sacrifice list, and debug flag.
        It reshapes the context before performing text generation by adjusting and cropping the number of tokens.

        Parameters:
        - prompt (str): The input prompt for text generation.
        - max_generation_size (int): The maximum number of tokens to generate.
        - placeholders (dict, optional): A dictionary of placeholders to be replaced in the prompt. Defaults to an empty dictionary.
        - sacrifice (list, optional): A list of placeholders to sacrifice if the window is bigger than the context size minus the number of tokens to generate. Defaults to ["previous_discussion"].
        - debug (bool, optional): Flag to enable/disable debug mode. Defaults to False.

        Returns:
        - str: The generated text after removing special tokens ("<s>" and "</s>") and stripping any leading/trailing whitespace.
        """
        prompt = "\n".join([
            "!@>system: I am an AI assistant that can converse and analyze images. When asked to locate something in an image you send, I will reply with:",
            "boundingbox(image_index, label, left, top, width, height)",
            "Where:",
            "image_index: 0-based index of the image",
            "label: brief description of what is located",
            "left, top: x,y coordinates of top-left box corner (0-1 scale)",
            "width, height: box dimensions as fraction of image size",
            "Coordinates have origin (0,0) at top-left, (1,1) at bottom-right.",
            "For other queries, I will respond conversationally to the best of my abilities.",
            prompt
        ])
        if debug == False:
            debug = self.config.debug

        if max_generation_size is None:
            prompt_size = self.model.tokenize(prompt)
            max_generation_size = self.model.config.ctx_size - len(prompt_size)

        pr = PromptReshaper(prompt)
        prompt = pr.build(placeholders,
                        self.model.tokenize,
                        self.model.detokenize,
                        self.model.config.ctx_size - max_generation_size,
                        sacrifice
                        )
        ntk = len(self.model.tokenize(prompt))
        max_generation_size = min(self.model.config.ctx_size - ntk, max_generation_size)
        # TODO : add show progress

        gen = self.generate_with_images(prompt, images, max_generation_size, callback=callback, show_progress=show_progress).strip().replace("</s>", "").replace("<s>", "")
        try:
            gen = process_ai_output(gen, images, "/discussions/")
        except Exception as ex:
            pass
        if debug:
            self.print_prompt("prompt", prompt+gen)

        return gen

    def fast_gen(
                    self, 
                    prompt: str, 
                    max_generation_size: int=None, 
                    placeholders: dict = {}, 
                    sacrifice: list = ["previous_discussion"], 
                    debug: bool  = False, 
                    callback=None, 
                    show_progress=False, 
                    temperature = None, 
                    top_k = None, 
                    top_p=None, 
                    repeat_penalty=None, 
                    repeat_last_n=None
                ) -> str:
        """
        Fast way to generate code

        This method takes in a prompt, maximum generation size, optional placeholders, sacrifice list, and debug flag.
        It reshapes the context before performing text generation by adjusting and cropping the number of tokens.

        Parameters:
        - prompt (str): The input prompt for text generation.
        - max_generation_size (int): The maximum number of tokens to generate.
        - placeholders (dict, optional): A dictionary of placeholders to be replaced in the prompt. Defaults to an empty dictionary.
        - sacrifice (list, optional): A list of placeholders to sacrifice if the window is bigger than the context size minus the number of tokens to generate. Defaults to ["previous_discussion"].
        - debug (bool, optional): Flag to enable/disable debug mode. Defaults to False.

        Returns:
        - str: The generated text after removing special tokens ("<s>" and "</s>") and stripping any leading/trailing whitespace.
        """
        if debug == False:
            debug = self.config.debug

        if max_generation_size is None:
            prompt_size = self.model.tokenize(prompt)
            max_generation_size = self.model.config.ctx_size - len(prompt_size)

        pr = PromptReshaper(prompt)
        prompt = pr.build(placeholders,
                        self.model.tokenize,
                        self.model.detokenize,
                        self.model.config.ctx_size - max_generation_size,
                        sacrifice
                        )
        ntk = len(self.model.tokenize(prompt))
        max_generation_size = min(self.model.config.ctx_size - ntk, max_generation_size)
        # TODO : add show progress

        gen = self.generate(prompt, max_generation_size, temperature = temperature, top_k = top_k, top_p=top_p, repeat_penalty=repeat_penalty, repeat_last_n=repeat_last_n, callback=callback, show_progress=show_progress).strip().replace("</s>", "").replace("<s>", "")
        if debug:
            self.print_prompt("prompt", prompt+gen)

        return gen



    def process(self, text:str, message_type:MSG_TYPE, callback=None, show_progress=False):
        if callback is None:
            callback = self.callback
        if text is None:
            return True
        if message_type==MSG_TYPE.MSG_TYPE_CHUNK:
            bot_says = self.bot_says + text
        elif  message_type==MSG_TYPE.MSG_TYPE_FULL:
            bot_says = text

        if show_progress:
            if self.nb_received_tokens==0:
                self.start_time = datetime.now()
            dt =(datetime.now() - self.start_time).seconds
            if dt==0:
                dt=1
            spd = self.nb_received_tokens/dt
            ASCIIColors.green(f"Received {self.nb_received_tokens} tokens (speed: {spd:.2f}t/s)              ",end="\r",flush=True)
            sys.stdout = sys.__stdout__
            sys.stdout.flush()
            self.nb_received_tokens+=1


        antiprompt = self.detect_antiprompt(bot_says)
        if antiprompt:
            self.bot_says = remove_text_from_string(bot_says,antiprompt)
            ASCIIColors.warning(f"\n{antiprompt} detected. Stopping generation")
            return False
        else:
            if callback:
                callback(text,message_type)
            self.bot_says = bot_says
            return True

    def generate_with_images(self, prompt, images, max_size, temperature = None, top_k = None, top_p=None, repeat_penalty=None, repeat_last_n=None, callback=None, debug=False, show_progress=False ):
        ASCIIColors.info("Text generation started: Warming up")
        self.nb_received_tokens = 0
        self.bot_says = ""
        if debug:
            self.print_prompt("gen",prompt)

        self.model.generate_with_images(
                                prompt,
                                images,
                                max_size,
                                partial(self.process, callback=callback, show_progress=show_progress),
                                temperature=self.model_temperature if temperature is None else temperature,
                                top_k=self.model_top_k if top_k is None else top_k,
                                top_p=self.model_top_p if top_p is None else top_p,
                                repeat_penalty=self.model_repeat_penalty if repeat_penalty is None else repeat_penalty,
                                repeat_last_n = self.model_repeat_last_n if repeat_last_n is None else repeat_last_n
                                ).strip()
        return self.bot_says

    def generate(self, prompt, max_size, temperature = None, top_k = None, top_p=None, repeat_penalty=None, repeat_last_n=None, callback=None, debug=False, show_progress=False ):
        ASCIIColors.info("Text generation started: Warming up")
        self.nb_received_tokens = 0
        self.bot_says = ""
        if debug:
            self.print_prompt("gen",prompt)

        self.model.generate(
                                prompt,
                                max_size,
                                partial(self.process, callback=callback, show_progress=show_progress),
                                temperature=self.model_temperature if temperature is None else temperature,
                                top_k=self.model_top_k if top_k is None else top_k,
                                top_p=self.model_top_p if top_p is None else top_p,
                                repeat_penalty=self.model_repeat_penalty if repeat_penalty is None else repeat_penalty,
                                repeat_last_n = self.model_repeat_last_n if repeat_last_n is None else repeat_last_n,
                                ).strip()
        return self.bot_says

    def setCallback(self, callback: Callable[[str, MSG_TYPE, dict, list], bool]):
        self.callback = callback
        if self._processor:
            self._processor.callback = callback


    def __str__(self):
        return f"{self.category}/{self.name}"


    def load_personality(self, package_path=None):
        """
        Load personality parameters from a YAML configuration file.

        Args:
            package_path (str or Path): The path to the package directory.

        Raises:
            ValueError: If the configuration file does not exist.
        """
        if package_path is None:
            package_path = self.personality_package_path
        else:
            package_path = Path(package_path)

        # Verify that there is at least a configuration file
        config_file = package_path / "config.yaml"
        if not config_file.exists():
            raise ValueError(f"The provided folder {package_path} does not exist.")

        with open(config_file, "r", encoding='utf-8') as f:
            config = yaml.safe_load(f)

        secret_file = package_path / "secret.yaml"
        if secret_file.exists():
            with open(secret_file, "r", encoding='utf-8') as f:
                self._secret_cfg = yaml.safe_load(f)
        else:
            self._secret_cfg = None

        languages = package_path / "languages"

        if languages.exists():
            self._supported_languages = []
            for language in [l for l in languages.iterdir()]:
                self._supported_languages.append(language.stem)

            if self._selected_language is not None and self._selected_language in self._supported_languages:
                config_file = languages / (self._selected_language+".yaml")
                with open(config_file, "r", encoding='utf-8') as f:
                    config = yaml.safe_load(f)



        # Load parameters from the configuration file
        self._version = config.get("version", self._version)
        self._author = config.get("author", self._author)
        self._name = config.get("name", self._name)
        self._user_name = config.get("user_name", self._user_name)
        self._category_desc = config.get("category", self._category)
        self._language = config.get("language", self._language)


        self._personality_description = config.get("personality_description", self._personality_description)
        self._personality_conditioning = config.get("personality_conditioning", self._personality_conditioning)
        self._welcome_message = config.get("welcome_message", self._welcome_message)
        self._include_welcome_message_in_discussion = config.get("include_welcome_message_in_discussion", self._include_welcome_message_in_discussion)

        self._user_message_prefix = config.get("user_message_prefix", self._user_message_prefix)
        self._link_text = config.get("link_text", self._link_text)
        self._ai_message_prefix = config.get("ai_message_prefix", self._ai_message_prefix)
        self._anti_prompts = [self.config.discussion_prompt_separator]+config.get("anti_prompts", self._anti_prompts)
        self._dependencies = config.get("dependencies", self._dependencies)
        self._disclaimer = config.get("disclaimer", self._disclaimer)
        self._help = config.get("help", self._help)
        self._commands = config.get("commands", self._commands)
        self._model_temperature = config.get("model_temperature", self._model_temperature)
        self._model_n_predicts = config.get("model_n_predicts", self._model_n_predicts)
        self._model_top_k = config.get("model_top_k", self._model_top_k)
        self._model_top_p = config.get("model_top_p", self._model_top_p)
        self._model_repeat_penalty = config.get("model_repeat_penalty", self._model_repeat_penalty)
        self._model_repeat_last_n = config.get("model_repeat_last_n", self._model_repeat_last_n)

        # Script parameters (for example keys to connect to search engine or any other usage)
        self._processor_cfg = config.get("processor_cfg", self._processor_cfg)


        #set package path
        self.personality_package_path = package_path

        # Check for a logo file
        self.logo_path = self.personality_package_path / "assets" / "logo.png"
        if self.logo_path.is_file():
            self._logo = Image.open(self.logo_path)

        # Get the assets folder path
        self.assets_path = self.personality_package_path / "assets"
        # Get the scripts folder path
        self.scripts_path = self.personality_package_path / "scripts"
        # Get the languages folder path
        self.languages_path = self.personality_package_path / "languages"
        # Get the data folder path
        self.data_path = self.personality_package_path / "data"
        # Get the data folder path
        self.audio_path = self.personality_package_path / "audio"
        # Get the data folder path
        self.welcome_audio_path = self.personality_package_path / "welcome_audio"


        # If not exist recreate
        self.assets_path.mkdir(parents=True, exist_ok=True)

        # If not exist recreate
        self.scripts_path.mkdir(parents=True, exist_ok=True)

        # If not exist recreate
        self.audio_path.mkdir(parents=True, exist_ok=True)

        # samples
        self.audio_samples = [f for f in self.audio_path.iterdir()]

        # Verify if the persona has a data folder
        if self.data_path.exists():
            self.database_path = self.data_path / "db.json"
            if self.database_path.exists():
                ASCIIColors.info("Loading database ...",end="")
                self.persona_data_vectorizer = TextVectorizer(
                            "tfidf_vectorizer", # self.config.data_vectorization_method, # supported "model_embedding" or "tfidf_vectorizer"
                            model=self.model, #needed in case of using model_embedding
                            save_db=True,
                            database_path=self.database_path,
                            data_visualization_method=VisualizationMethod.PCA,
                            database_dict=None)
                ASCIIColors.green("Ok")
            else:
                files = [f for f in self.data_path.iterdir() if f.suffix.lower() in ['.asm', '.bat', '.c', '.cpp', '.cs', '.csproj', '.css',
                    '.csv', '.docx', '.h', '.hh', '.hpp', '.html', '.inc', '.ini', '.java', '.js', '.json', '.log',
                    '.lua', '.map', '.md', '.pas', '.pdf', '.php', '.pptx', '.ps1', '.py', '.rb', '.rtf', '.s', '.se', '.sh', '.sln',
                    '.snippet', '.snippets', '.sql', '.sym', '.ts', '.txt', '.xlsx', '.xml', '.yaml', '.yml'] ]
                if len(files)>0:
                    dl = GenericDataLoader()
                    self.persona_data_vectorizer = TextVectorizer(
                                "tfidf_vectorizer", # self.config.data_vectorization_method, # supported "model_embedding" or "tfidf_vectorizer"
                                model=self.model, #needed in case of using model_embedding
                                save_db=True,
                                database_path=self.database_path,
                                data_visualization_method=VisualizationMethod.PCA,
                                database_dict=None)
                    for f in files:
                        text = dl.read_file(f)
                        self.persona_data_vectorizer.add_document(f.name,text,self.config.data_vectorization_chunk_size, self.config.data_vectorization_overlap_size)
                        # data_vectorization_chunk_size: 512 # chunk size
                        # data_vectorization_overlap_size: 128 # overlap between chunks size
                        # data_vectorization_nb_chunks: 2 # number of chunks to use
                    self.persona_data_vectorizer.index()
                    self.persona_data_vectorizer.save_db()
                else:
                    self.persona_data_vectorizer = None
                    self._data = None

        else:
            self.persona_data_vectorizer = None
            self._data = None

        self.personality_output_folder = self.lollms_paths.personal_outputs_path/self.name
        self.personality_output_folder.mkdir(parents=True, exist_ok=True)


        if self.run_scripts:
            # Search for any processor code
            processor_file_name = "processor.py"
            self.processor_script_path = self.scripts_path / processor_file_name
            if self.processor_script_path.exists():
                module_name = processor_file_name[:-3]  # Remove the ".py" extension
                module_spec = importlib.util.spec_from_file_location(module_name, str(self.processor_script_path))
                module = importlib.util.module_from_spec(module_spec)
                module_spec.loader.exec_module(module)
                if hasattr(module, "Processor"):
                    self._processor = module.Processor(self, callback=self.callback)
                else:
                    self._processor = None
            else:
                self._processor = None
        # Get a list of all files in the assets folder
        contents = [str(file) for file in self.assets_path.iterdir() if file.is_file()]

        self._assets_list = contents
        return config



    def remove_file(self, file_name, callback=None):
        try:
            if any(file_name == entry.name for entry in self.text_files):
                fn = [entry for entry in self.text_files if entry.name == file_name][0]
                self.text_files = [entry for entry in self.text_files if entry.name != file_name]
                Path(fn).unlink()
                if len(self.text_files)>0:
                    try:
                        self.vectorizer.remove_document(fn)
                        if callback is not None:
                            callback("File removed successfully",MSG_TYPE.MSG_TYPE_INFO)
                        return True
                    except ValueError as ve:
                        ASCIIColors.error(f"Couldn't remove the file")
                        return False
                else:
                    self.vectorizer = None
            elif any(file_name == entry.name for entry in self.image_files):
                fn = [entry for entry in self.image_files if entry.name == file_name][0]
                self.text_files = [entry for entry in self.image_files if entry.name != file_name]
                Path(fn).unlink()

        except Exception as ex:
            ASCIIColors.warning(f"Couldn't remove the file {file_name}")

    def remove_all_files(self, callback=None):
        for file in self.text_files:
            try:
                Path(file).unlink()
            except Exception as ex:
                ASCIIColors.warning(f"Couldn't remove the file {file}")
        for file in self.image_files:
            try:
                Path(file).unlink()
            except Exception as ex:
                ASCIIColors.warning(f"Couldn't remove the file {file}")
        self.text_files=[]
        self.image_files=[]
        self.vectorizer = None
        return True

    def add_file(self, path, client:Client, callback=None, process=True):
        output = ""
        if not self.callback:
            self.callback = callback

        path = Path(path)
        if path.suffix in [".wav",".mp3"]:
            self.audio_files.append(path)
            if process:
                self.new_message("")
                self.info(f"Transcribing ... ")
                self.step_start("Transcribing ... ")
                if self.whisper is None:
                    if not PackageManager.check_package_installed("whisper"):
                        PackageManager.install_package("openai-whisper")
                        try:
                            import conda.cli
                            conda.cli.main("install", "conda-forge::ffmpeg", "-y")
                        except:
                            ASCIIColors.bright_red("Couldn't install ffmpeg. whisper won't work. Please install it manually")

                    import whisper
                    self.whisper = whisper.load_model("base")
                result = self.whisper.transcribe(str(path))
                transcription_fn = str(path)+".txt"
                with open(transcription_fn, "w", encoding="utf-8") as f:
                    f.write(result["text"])

                self.info(f"File saved to {transcription_fn}")
                self.full(result["text"])
                self.step_end("Transcribing ... ")
        elif path.suffix in [".png",".jpg",".jpeg",".gif",".bmp",".svg",".webp"]:
            self.image_files.append(path)
            if process:
                if self.callback:
                    try:
                        pth = str(path).replace("\\","/").split('/')
                        if "discussion_databases" in pth:
                            pth = discussion_path_to_url(path)
                            self.new_message("",MSG_TYPE.MSG_TYPE_FULL)
                            output = f'<img src="{pth}" width="800">\n\n'
                            self.full(output)
                            self.app.close_message(client.client_id if client is not None else 0)

                        if self.model.binding_type not in [BindingType.TEXT_IMAGE, BindingType.TEXT_IMAGE_VIDEO]:
                            # self.ShowBlockingMessage("Understanding image (please wait)")
                            from PIL import Image
                            img = Image.open(str(path))
                            # Convert the image to RGB mode
                            img = img.convert("RGB")
                            output += "## image description :\n"+ self.model.interrogate_blip([img])[0]
                            # output += "## image description :\n"+ self.model.qna_blip([img],"q:Describe this photo with as much details as possible.\na:")[0]
                            self.full(output)
                            self.app.close_message(client.client_id if client is not None else 0)
                            self.HideBlockingMessage("Understanding image (please wait)")
                            if self.config.debug:
                                ASCIIColors.yellow(output)
                        else:
                            # self.ShowBlockingMessage("Importing image (please wait)")
                            self.HideBlockingMessage("Importing image (please wait)")

                    except Exception as ex:
                        trace_exception(ex)
                        self.HideBlockingMessage("Understanding image (please wait)", False)
                        ASCIIColors.error("Couldn't create new message")
            ASCIIColors.info("Received image file")
            if callback is not None:
                callback("Image file added successfully", MSG_TYPE.MSG_TYPE_INFO)
        else:
            try:
                # self.ShowBlockingMessage("Adding file to vector store.\nPlease stand by")
                self.text_files.append(path)
                ASCIIColors.info("Received text compatible file")
                self.ShowBlockingMessage("Processing file\nPlease wait ...")
                if process:
                    if self.vectorizer is None:
                        self.vectorizer = TextVectorizer(
                                    self.config.data_vectorization_method, # supported "model_embedding" or "tfidf_vectorizer"
                                    model=self.model, #needed in case of using model_embedding
                                    database_path=client.discussion.discussion_rag_folder/"db.json",
                                    save_db=self.config.data_vectorization_save_db,
                                    data_visualization_method=VisualizationMethod.PCA,
                                    database_dict=None)
                    data = GenericDataLoader.read_file(path)
                    self.vectorizer.add_document(path, data, self.config.data_vectorization_chunk_size, self.config.data_vectorization_overlap_size, add_first_line_to_all_chunks=True if path.suffix==".csv" else False)
                    self.vectorizer.index()
                    if callback is not None:
                        callback("File added successfully",MSG_TYPE.MSG_TYPE_INFO)
                    self.HideBlockingMessage(client.client_id)
                    return True
            except Exception as e:
                trace_exception(e)
                self.InfoMessage(f"Unsupported file format or empty file.\nSupported formats are {GenericDataLoader.get_supported_file_types()}",client_id=client.client_id)
                return False
    def save_personality(self, package_path=None):
        """
        Save the personality parameters to a YAML configuration file.

        Args:
            package_path (str or Path): The path to the package directory.
        """
        if package_path is None:
            package_path = self.personality_package_path
        else:
            package_path = Path(package_path)

        # Building output path
        config_file = package_path / "config.yaml"
        assets_folder = package_path / "assets"

        # Create assets folder if it doesn't exist
        if not assets_folder.exists():
            assets_folder.mkdir(exist_ok=True, parents=True)

        # Create the configuration dictionary
        config = {
            "author": self._author,
            "version": self._version,
            "name": self._name,
            "user_name": self._user_name,
            "category": self._category,
            "language": self._language,
            "supported_languages": self._supported_languages,
            "selected_language": self._selected_language,
            "personality_description": self._personality_description,
            "personality_conditioning": self._personality_conditioning,
            "welcome_message": self._welcome_message,
            "include_welcome_message_in_discussion": self._include_welcome_message_in_discussion,
            "user_message_prefix": self._user_message_prefix,
            "link_text": self._link_text,
            "ai_message_prefix": self._ai_message_prefix,
            "anti_prompts": self._anti_prompts,
            "dependencies": self._dependencies,
            "disclaimer": self._disclaimer,
            "help": self._help,
            "commands": self._commands,
            "model_temperature": self._model_temperature,
            "model_n_predicts": self._model_n_predicts,
            "model_top_k": self._model_top_k,
            "model_top_p": self._model_top_p,
            "model_repeat_penalty": self._model_repeat_penalty,
            "model_repeat_last_n": self._model_repeat_last_n
        }

        # Save the configuration to the YAML file
        with open(config_file, "w") as f:
            yaml.dump(config, f)



    def as_dict(self):
        """
        Convert the personality parameters to a dictionary.

        Returns:
            dict: The personality parameters as a dictionary.
        """
        return {
            "author": self._author,
            "version": self._version,
            "name": self._name,
            "user_name": self._user_name,
            "category": self._category,
            "language": self._language,
            "supported_languages": self._supported_languages,
            "selected_language": self._selected_language,
            "personality_description": self._personality_description,
            "personality_conditioning": self._personality_conditioning,
            "welcome_message": self._welcome_message,
            "include_welcome_message_in_discussion": self._include_welcome_message_in_discussion,
            "user_message_prefix": self._user_message_prefix,
            "link_text": self._link_text,
            "ai_message_prefix": self._ai_message_prefix,
            "anti_prompts": self._anti_prompts,
            "dependencies": self._dependencies,
            "disclaimer": self._disclaimer,
            "help": self._help,
            "commands": self._commands,
            "model_temperature": self._model_temperature,
            "model_n_predicts": self._model_n_predicts,
            "model_top_k": self._model_top_k,
            "model_top_p": self._model_top_p,
            "model_repeat_penalty": self._model_repeat_penalty,
            "model_repeat_last_n": self._model_repeat_last_n,
            "assets_list":self._assets_list
        }

    # ========================================== Properties ===========================================
    @property
    def conditionning_commands(self):
        return {
            "date_time": datetime.now().strftime("%A, %B %d, %Y %I:%M:%S %p"), # Replaces {{date}} with actual date
            "date": datetime.now().strftime("%A, %B %d, %Y"), # Replaces {{date}} with actual date
            "time": datetime.now().strftime("%H:%M:%S"), # Replaces {{time}} with actual time
        }

    @property
    def logo(self):
        """
        Get the personality logo.

        Returns:
        PIL.Image.Image: The personality logo as a Pillow Image object.
        """
        if hasattr(self, '_logo'):
            return self._logo
        else:
            return None
    @property
    def version(self):
        """Get the version of the package."""
        return self._version

    @version.setter
    def version(self, value):
        """Set the version of the package."""
        self._version = value

    @property
    def author(self):
        """Get the author of the package."""
        return self._author

    @author.setter
    def author(self, value):
        """Set the author of the package."""
        self._author = value

    @property
    def name(self) -> str:
        """Get the name."""
        return self._name

    @name.setter
    def name(self, value: str):
        """Set the name."""
        self._name = value

    @property
    def user_name(self) -> str:
        """Get the user name."""
        return self._user_name

    @user_name.setter
    def user_name(self, value: str):
        """Set the user name."""
        self._user_name = value


    @property
    def language(self) -> str:
        """Get the language."""
        return self._language

    @property
    def category(self) -> str:
        """Get the category."""
        return self._category

    @property
    def category_desc(self) -> str:
        """Get the category."""
        return self._category_desc

    @language.setter
    def language(self, value: str):
        """Set the language."""
        self._language = value

    @category.setter
    def category(self, value: str):
        """Set the category."""
        self._category = value

    @category_desc.setter
    def category_desc(self, value: str):
        """Set the category."""
        self._category_desc = value


    @property
    def supported_languages(self) -> str:
        """Get the supported_languages."""
        return self._supported_languages

    @supported_languages.setter
    def supported_languages(self, value: str):
        """Set the supported_languages."""
        self._supported_languages = value


    @property
    def selected_language(self) -> str:
        """Get the selected_language."""
        return self._selected_language

    @selected_language.setter
    def selected_language(self, value: str):
        """Set the selected_language."""
        self._selected_language = value

    @property
    def personality_description(self) -> str:
        """
        Getter for the personality description.

        Returns:
            str: The personality description of the AI assistant.
        """
        return self._personality_description

    @personality_description.setter
    def personality_description(self, description: str):
        """
        Setter for the personality description.

        Args:
            description (str): The new personality description for the AI assistant.
        """
        self._personality_description = description

    @property
    def personality_conditioning(self) -> str:
        """
        Getter for the personality conditioning.

        Returns:
            str: The personality conditioning of the AI assistant.
        """
        return self.replace_keys(self._personality_conditioning, self.conditionning_commands)

    @personality_conditioning.setter
    def personality_conditioning(self, conditioning: str):
        """
        Setter for the personality conditioning.

        Args:
            conditioning (str): The new personality conditioning for the AI assistant.
        """
        self._personality_conditioning = conditioning

    @property
    def welcome_message(self) -> str:
        """
        Getter for the welcome message.

        Returns:
            str: The welcome message of the AI assistant.
        """
        return self.replace_keys(self._welcome_message, self.conditionning_commands)

    @welcome_message.setter
    def welcome_message(self, message: str):
        """
        Setter for the welcome message.

        Args:
            message (str): The new welcome message for the AI assistant.
        """
        self._welcome_message = message

    @property
    def include_welcome_message_in_discussion(self) -> bool:
        """
        Getter for the include welcome message in disucssion.

        Returns:
            bool: whether to add the welcome message to tje discussion or not.
        """
        return self._include_welcome_message_in_discussion

    @include_welcome_message_in_discussion.setter
    def include_welcome_message_in_discussion(self, message: bool):
        """
        Setter for the welcome message.

        Args:
            message (str): The new welcome message for the AI assistant.
        """
        self._include_welcome_message_in_discussion = message


    @property
    def user_message_prefix(self) -> str:
        """
        Getter for the user message prefix.

        Returns:
            str: The user message prefix of the AI assistant.
        """
        return self._user_message_prefix

    @user_message_prefix.setter
    def user_message_prefix(self, prefix: str):
        """
        Setter for the user message prefix.

        Args:
            prefix (str): The new user message prefix for the AI assistant.
        """
        self._user_message_prefix = prefix

    @property
    def link_text(self) -> str:
        """
        Getter for the link text.

        Returns:
            str: The link text of the AI assistant.
        """
        return self._link_text

    @link_text.setter
    def link_text(self, text: str):
        """
        Setter for the link text.

        Args:
            text (str): The new link text for the AI assistant.
        """
        self._link_text = text
    @property
    def ai_message_prefix(self):
        """
        Get the AI message prefix.

        Returns:
            str: The AI message prefix.
        """
        return self._ai_message_prefix

    @ai_message_prefix.setter
    def ai_message_prefix(self, prefix):
        """
        Set the AI message prefix.

        Args:
            prefix (str): The AI message prefix to set.
        """
        self._ai_message_prefix = prefix

    @property
    def anti_prompts(self):
        """
        Get the anti-prompts list.

        Returns:
            list: The anti-prompts list.
        """
        return self._anti_prompts

    @anti_prompts.setter
    def anti_prompts(self, prompts):
        """
        Set the anti-prompts list.

        Args:
            prompts (list): The anti-prompts list to set.
        """
        self._anti_prompts = prompts


    @property
    def dependencies(self) -> List[str]:
        """Getter method for the dependencies attribute.

        Returns:
            List[str]: The list of dependencies.
        """
        return self._dependencies

    @dependencies.setter
    def dependencies(self, dependencies: List[str]):
        """Setter method for the dependencies attribute.

        Args:
            dependencies (List[str]): The list of dependencies.
        """
        self._dependencies = dependencies

    @property
    def disclaimer(self) -> str:
        """Getter method for the disclaimer attribute.

        Returns:
            str: The disclaimer text.
        """
        return self._disclaimer

    @disclaimer.setter
    def disclaimer(self, disclaimer: str):
        """Setter method for the disclaimer attribute.

        Args:
            disclaimer (str): The disclaimer text.
        """
        self._disclaimer = disclaimer

    @property
    def help(self) -> str:
        """Getter method for the help attribute.

        Returns:
            str: The help text.
        """
        return self._help

    @help.setter
    def help(self, help: str):
        """Setter method for the help attribute.

        Args:
            help (str): The help text.
        """
        self._help = help



    @property
    def commands(self) -> str:
        """Getter method for the commands attribute.

        Returns:
            str: The commands text.
        """
        return self._commands

    @commands.setter
    def commands(self, commands: str):
        """Setter method for the commands attribute.

        Args:
            commands (str): The commands text.
        """
        self._commands = commands


    @property
    def model_temperature(self) -> float:
        """Get the model's temperature."""
        return self._model_temperature

    @model_temperature.setter
    def model_temperature(self, value: float):
        """Set the model's temperature.

        Args:
            value (float): The new temperature value.
        """
        self._model_temperature = value

    @property
    def model_n_predicts(self) -> int:
        """Get the number of predictions the model generates."""
        return self._model_n_predicts

    @model_n_predicts.setter
    def model_n_predicts(self, value: int):
        """Set the number of predictions the model generates.

        Args:
            value (int): The new number of predictions value.
        """
        self._model_n_predicts = value

    @property
    def model_top_k(self) -> int:
        """Get the model's top-k value."""
        return self._model_top_k

    @model_top_k.setter
    def model_top_k(self, value: int):
        """Set the model's top-k value.

        Args:
            value (int): The new top-k value.
        """
        self._model_top_k = value

    @property
    def model_top_p(self) -> float:
        """Get the model's top-p value."""
        return self._model_top_p

    @model_top_p.setter
    def model_top_p(self, value: float):
        """Set the model's top-p value.

        Args:
            value (float): The new top-p value.
        """
        self._model_top_p = value

    @property
    def model_repeat_penalty(self) -> float:
        """Get the model's repeat penalty value."""
        return self._model_repeat_penalty

    @model_repeat_penalty.setter
    def model_repeat_penalty(self, value: float):
        """Set the model's repeat penalty value.

        Args:
            value (float): The new repeat penalty value.
        """
        self._model_repeat_penalty = value

    @property
    def model_repeat_last_n(self) -> int:
        """Get the number of words to consider for repeat penalty."""
        return self._model_repeat_last_n

    @model_repeat_last_n.setter
    def model_repeat_last_n(self, value: int):
        """Set the number of words to consider for repeat penalty.

        Args:
            value (int): The new number of words value.
        """
        self._model_repeat_last_n = value


    @property
    def assets_list(self) -> list:
        """Get the number of words to consider for repeat penalty."""
        return self._assets_list

    @assets_list.setter
    def assets_list(self, value: list):
        """Set the number of words to consider for repeat penalty.

        Args:
            value (int): The new number of words value.
        """
        self._assets_list = value

    @property
    def processor(self) -> 'APScript':
        """Get the number of words to consider for repeat penalty."""
        return self._processor

    @processor.setter
    def processor(self, value: 'APScript'):
        """Set the number of words to consider for repeat penalty.

        Args:
            value (int): The new number of words value.
        """
        self._processor = value


    @property
    def processor_cfg(self) -> list:
        """Get the number of words to consider for repeat penalty."""
        return self._processor_cfg

    @processor_cfg.setter
    def processor_cfg(self, value: dict):
        """Set the number of words to consider for repeat penalty.

        Args:
            value (int): The new number of words value.
        """
        self._processor_cfg = value

    # ========================================== Helper methods ==========================================
    def detect_antiprompt(self, text:str) -> bool:
        """
        Detects if any of the antiprompts in self.anti_prompts are present in the given text.
        Used for the Hallucination suppression system

        Args:
            text (str): The text to check for antiprompts.

        Returns:
            bool: True if any antiprompt is found in the text (ignoring case), False otherwise.
        """
        for prompt in self.anti_prompts:
            if prompt.lower() in text.lower():
                return prompt.lower()
        return None


    # Helper functions
    @staticmethod
    def replace_keys(input_string, replacements):
        """
        Replaces all occurrences of keys in the input string with their corresponding
        values from the replacements dictionary.

        Args:
            input_string (str): The input string to replace keys in.
            replacements (dict): A dictionary of key-value pairs, where the key is the
                string to be replaced and the value is the replacement string.

        Returns:
            str: The input string with all occurrences of keys replaced by their
                corresponding values.
        """
        pattern = r"\{\{(\w+)\}\}"
        # The pattern matches "{{key}}" and captures "key" in a group.
        # The "\w+" matches one or more word characters (letters, digits, or underscore).

        def replace(match):
            key = match.group(1)
            return replacements.get(key, match.group(0))

        output_string = re.sub(pattern, replace, input_string)
        return output_string



class StateMachine:
    def __init__(self, states_list):
        """
        states structure is the following
        [
            {
                "name": the state name,
                "commands": [ # list of commands
                    "command": function
                ],
                "default": default function
            }
        ]
        """
        self.states_list = states_list
        self.current_state_id = 0
        self.callback = None

    def goto_state(self, state):
        """
        Transition to the state with the given name or index.

        Args:
            state (str or int): The name or index of the state to transition to.

        Raises:
            ValueError: If no state is found with the given name or index.
        """
        if isinstance(state, str):
            for i, state_dict in enumerate(self.states_list):
                if state_dict["name"] == state:
                    self.current_state_id = i
                    return
        elif isinstance(state, int):
            if 0 <= state < len(self.states_list):
                self.current_state_id = state
                return
        raise ValueError(f"No state found with name or index: {state}")



    def process_state(self, command, full_context, callback: Callable[[str, MSG_TYPE, dict, list], bool]=None, context_state:dict=None, client:Client=None):
        """
        Process the given command based on the current state.

        Args:
            command: The command to process.

        Raises:
            ValueError: If the current state doesn't have the command and no default function is defined.
        """
        if callback:
            self.callback=callback

        current_state = self.states_list[self.current_state_id]
        commands = current_state["commands"]
        command = command.strip()

        for cmd, func in commands.items():
            if cmd == command[0:len(cmd)]:
                try:
                    func(command, full_context, callback, context_state, client)
                except:# retrocompatibility
                    func(command, full_context)
                return

        default_func = current_state.get("default")
        if default_func is not None:
            default_func(command, full_context, callback, context_state, client)
        else:
            raise ValueError(f"Command '{command}' not found in current state and no default function defined.")


class LoLLMsActionParameters:
    def __init__(self, name: str, parameter_type: Type, range: Optional[List] = None, options: Optional[List] = None, value: Any = None) -> None:
        self.name = name
        self.parameter_type = parameter_type
        self.range = range
        self.options = options
        self.value = value

    def __str__(self) -> str:
        parameter_dict = {
            'name': self.name,
            'parameter_type': self.parameter_type.__name__,
            'value': self.value
        }
        if self.range is not None:
            parameter_dict['range'] = self.range
        if self.options is not None:
            parameter_dict['options'] = self.options
        return json.dumps(parameter_dict, indent=4)

    @staticmethod
    def from_str(string: str) -> 'LoLLMsActionParameters':
        parameter_dict = json.loads(string)
        name = parameter_dict['name']
        parameter_type = eval(parameter_dict['parameter_type'])
        range = parameter_dict.get('range', None)
        options = parameter_dict.get('options', None)
        value = parameter_dict['value']
        return LoLLMsActionParameters(name, parameter_type, range, options, value)

    @staticmethod
    def from_dict(parameter_dict: dict) -> 'LoLLMsActionParameters':
        name = parameter_dict['name']
        parameter_type = eval(parameter_dict['parameter_type'])
        range = parameter_dict.get('range', None)
        options = parameter_dict.get('options', None)
        value = parameter_dict['value']
        return LoLLMsActionParameters(name, parameter_type, range, options, value)


class LoLLMsActionParametersEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, LoLLMsActionParameters):
            parameter_dict = {
                'name': obj.name,
                'parameter_type': obj.parameter_type.__name__,
                'value': obj.value
            }
            if obj.range is not None:
                parameter_dict['range'] = obj.range
            if obj.options is not None:
                parameter_dict['options'] = obj.options
            return parameter_dict
        return super().default(obj)

class LoLLMsAction:
    def __init__(self, name, parameters: List[LoLLMsActionParameters], callback: Callable, description:str="") -> None:
        self.name           = name
        self.parameters     = parameters
        self.callback       = callback
        self.description    = description

    def __str__(self) -> str:
        action_dict = {
            'name': self.name,
            'parameters': self.parameters,
            'description': self.description
        }
        return json.dumps(action_dict, indent=4, cls=LoLLMsActionParametersEncoder)

    @staticmethod
    def from_str(string: str) -> 'LoLLMsAction':
        action_dict = json.loads(string)
        name = action_dict['name']
        parameters = [LoLLMsActionParameters.from_dict(param_str) for param_str in action_dict['parameters']]
        return LoLLMsAction(name, parameters, None)

    @staticmethod
    def from_dict(action_dict: dict) -> 'LoLLMsAction':
        name = action_dict['name']
        parameters = [LoLLMsActionParameters.from_dict(param_str) for param_str in action_dict['parameters']]
        return LoLLMsAction(name, parameters, None)


    def run(self) -> None:
        args = {param.name: param.value for param in self.parameters}
        self.callback(**args)

def generate_actions(potential_actions: List[LoLLMsAction], parsed_text: dict) -> List[LoLLMsAction]:
    actions = []
    try:
        for action_data in parsed_text["actions"]:
            name = action_data['name']
            parameters = action_data['parameters']
            matching_action = next((action for action in potential_actions if action.name == name), None)
            if matching_action:
                action = LoLLMsAction.from_str(str(matching_action))
                action.callback = matching_action.callback
                if type(parameters)==dict:
                    for param_name, param_value in parameters.items():
                        matching_param = next((param for param in action.parameters if param.name == param_name), None)
                        if matching_param:
                            matching_param.value = param_value
                else:
                    for param in parameters:
                        if "name" in param:
                            param_name = param["name"]
                            param_value = param["value"]
                        else:
                            param_name = list(param.keys())[0]
                            param_value = param[param_name]
                        matching_param = next((param for param in action.parameters if param.name == param_name), None)
                        if matching_param:
                            matching_param.value = param_value
                actions.append(action)
    except json.JSONDecodeError:
        print("Invalid JSON format.")
    return actions

class APScript(StateMachine):
    """
    Template class for implementing personality processor classes in the APScript framework.

    This class provides a basic structure and placeholder methods for processing model inputs and outputs.
    Personality-specific processor classes should inherit from this class and override the necessary methods.
    """
    def __init__(
                    self,
                    personality         :AIPersonality,
                    personality_config  :TypedConfig,
                    states_list         :dict   = {},
                    callback            = None
                ) -> None:
        super().__init__(states_list)
        self.notify                             = personality.app.notify

        self.personality                        = personality
        self.personality_config                 = personality_config
        self.installation_option                = personality.installation_option
        self.configuration_file_path            = self.personality.lollms_paths.personal_configuration_path/"personalities"/self.personality.personality_folder_name/f"config.yaml"
        self.configuration_file_path.parent.mkdir(parents=True, exist_ok=True)

        self.personality_config.config.file_path    = self.configuration_file_path

        self.callback = callback

        # Installation
        if (not self.configuration_file_path.exists() or self.installation_option==InstallOption.FORCE_INSTALL) and self.installation_option!=InstallOption.NEVER_INSTALL:
            self.install()
            self.personality_config.config.save_config()
        else:
            self.load_personality_config()

    def sink(self, s=None,i=None,d=None):
        pass

    def settings_updated(self):
        """
        To be implemented by the processor when the settings have changed
        """
        pass

    def mounted(self):
        """
        triggered when mounted
        """
        pass

    def get_welcome(self, welcome_message:str, client:Client):
        """
        triggered when a new conversation is created
        """
        return None
        
    def selected(self):
        """
        triggered when mounted
        """
        pass

    def execute_command(self, command: str, parameters:list=[], client:Client=None):
        """
        Recovers user commands and executes them. Each personality can define a set of commands that they can receive and execute
        Args:
            command: The command name
            parameters: A list of the command parameters

        """
        try:
            self.process_state(command, "", self.callback, client)
        except Exception as ex:
            trace_exception(ex)
            self.warning(f"Couldn't execute command {command}")

    async def handle_request(self, request: Request) -> Dict[str, Any]:
        """
        Handle client requests.

        Args:
            data (dict): A dictionary containing the request data.

        Returns:
            dict: A dictionary containing the response, including at least a "status" key.

        This method should be implemented by a class that inherits from this one.

        Example usage:
        ```
        handler = YourHandlerClass()
        request_data = {"command": "some_command", "parameters": {...}}
        response = await handler.handle_request(request_data)
        ```
        """
        return {"status":True}


    def load_personality_config(self):
        """
        Load the content of local_config.yaml file.

        The function reads the content of the local_config.yaml file and returns it as a Python dictionary.

        Args:
            None

        Returns:
            dict: A dictionary containing the loaded data from the local_config.yaml file.
        """
        try:
            self.personality_config.config.load_config()
        except:
            self.personality_config.config.save_config()
        self.personality_config.sync()

    def install(self):
        """
        Installation procedure (to be implemented)
        """
        ASCIIColors.blue("*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*")
        ASCIIColors.red(f"Installing {self.personality.personality_folder_name}")
        ASCIIColors.blue("*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*")


    def uninstall(self):
        """
        Installation procedure (to be implemented)
        """
        ASCIIColors.blue("*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*")
        ASCIIColors.red(f"Uninstalling {self.personality.personality_folder_name}")
        ASCIIColors.blue("*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*")


    def add_file(self, path, client:Client, callback=None, process=True):
        self.personality.add_file(path, client=client,callback=callback, process=process)
        if callback is not None:
            callback("File added successfully",MSG_TYPE.MSG_TYPE_INFO)
        return True

    def remove_file(self, path):
        if path in self.personality.text_files:
            self.personality.text_files.remove(path)
        elif path in self.personality.image_files:
            self.personality.image_files.remove(path)


    def load_config_file(self, path, default_config=None):
        """
        Load the content of local_config.yaml file.

        The function reads the content of the local_config.yaml file and returns it as a Python dictionary.
        If a default_config is provided, it fills any missing entries in the loaded dictionary.
        If at least one field from default configuration was not present in the loaded configuration, the updated
        configuration is saved.

        Args:
            path (str): The path to the local_config.yaml file.
            default_config (dict, optional): A dictionary with default values to fill missing entries.

        Returns:
            dict: A dictionary containing the loaded data from the local_config.yaml file, with missing entries filled
            by default_config if provided.
        """
        with open(path, 'r') as file:
            data = yaml.safe_load(file)

        if default_config:
            updated = False
            for key, value in default_config.items():
                if key not in data:
                    data[key] = value
                    updated = True

            if updated:
                self.save_config_file(path, data)

        return data

    def save_config_file(self, path, data):
        """
        Save the configuration data to a local_config.yaml file.

        Args:
            path (str): The path to save the local_config.yaml file.
            data (dict): The configuration data to be saved.

        Returns:
            None
        """
        with open(path, 'w') as file:
            yaml.dump(data, file)

    def generate_with_images(self, prompt, images, max_size, temperature = None, top_k = None, top_p=None, repeat_penalty=None, repeat_last_n=None, callback=None, debug=False ):
        return self.personality.generate_with_images(prompt, images, max_size, temperature, top_k, top_p, repeat_penalty, repeat_last_n, callback, debug=debug)

    def generate(self, prompt, max_size, temperature = None, top_k = None, top_p=None, repeat_penalty=None, repeat_last_n=None, callback=None, debug=False ):
        return self.personality.generate(prompt, max_size, temperature, top_k, top_p, repeat_penalty, repeat_last_n, callback, debug=debug)


    def run_workflow(self, prompt:str, previous_discussion_text:str="", callback: Callable[[str, MSG_TYPE, dict, list], bool]=None, context_details:dict=None, client:Client=None):
        """
        This function generates code based on the given parameters.

        Args:
            full_prompt (str): The full prompt for code generation.
            prompt (str): The prompt for code generation.
            context_details (dict): A dictionary containing the following context details for code generation:
                - conditionning (str): The conditioning information.
                - documentation (str): The documentation information.
                - knowledge (str): The knowledge information.
                - user_description (str): The user description information.
                - discussion_messages (str): The discussion messages information.
                - positive_boost (str): The positive boost information.
                - negative_boost (str): The negative boost information.
                - current_language (str): The force language information.
                - fun_mode (str): The fun mode conditionning text
                - ai_prefix (str): The AI prefix information.
            n_predict (int): The number of predictions to generate.
            client_id: The client ID for code generation.
            callback (function, optional): The callback function for code generation.

        Returns:
            None
        """

        return None


    # ================================================= Advanced methods ===========================================
    def compile_latex(self, file_path, pdf_latex_path=None):
        try:
            # Determine the pdflatex command based on the provided or default path
            if pdf_latex_path:
                pdflatex_command = pdf_latex_path
            else:
                pdflatex_command = self.personality.config.pdf_latex_path if self.personality.config.pdf_latex_path is not None else 'pdflatex'

            # Set the execution path to the folder containing the tmp_file
            execution_path = file_path.parent
            # Run the pdflatex command with the file path
            result = subprocess.run([pdflatex_command, "-interaction=nonstopmode", file_path], check=True, capture_output=True, text=True, cwd=execution_path)
            # Check the return code of the pdflatex command
            if result.returncode != 0:
                error_message = result.stderr.strip()
                return {"status":False,"error":error_message}

            # If the compilation is successful, you will get a PDF file
            pdf_file = file_path.with_suffix('.pdf')
            print(f"PDF file generated: {pdf_file}")
            return {"status":True,"file_path":pdf_file}

        except subprocess.CalledProcessError as e:
            print(f"Error occurred while compiling LaTeX: {e}")
            return {"status":False,"error":e}

    def find_numeric_value(self, text):
        pattern = r'\d+[.,]?\d*'
        match = re.search(pattern, text)
        if match:
            return float(match.group().replace(',', '.'))
        else:
            return None
    def remove_backticks(self, text):
        if text.startswith("```"):
            split_text = text.split("\n")
            text = "\n".join(split_text[1:])
        if text.endswith("```"):
            text= text[:-3]
        return text

    def search_duckduckgo(self, query: str, max_results: int = 10, instant_answers: bool = True, regular_search_queries: bool = True, get_webpage_content: bool = False) -> List[Dict[str, Union[str, None]]]:
        """
        Perform a search using the DuckDuckGo search engine and return the results as a list of dictionaries.

        Args:
            query (str): The search query to use in the search. This argument is required.
            max_results (int, optional): The maximum number of search results to return. Defaults to 10.
            instant_answers (bool, optional): Whether to include instant answers in the search results. Defaults to True.
            regular_search_queries (bool, optional): Whether to include regular search queries in the search results. Defaults to True.
            get_webpage_content (bool, optional): Whether to retrieve and include the website content for each result. Defaults to False.

        Returns:
            list[dict]: A list of dictionaries containing the search results. Each dictionary will contain 'title', 'body', and 'href' keys.

        Raises:
            ValueError: If neither instant_answers nor regular_search_queries is set to True.
        """
        if not PackageManager.check_package_installed("duckduckgo_search"):
            PackageManager.install_package("duckduckgo_search")
        from duckduckgo_search import DDGS
        if not (instant_answers or regular_search_queries):
            raise ValueError("One of ('instant_answers', 'regular_search_queries') must be True")

        query = query.strip("\"'")

        with DDGS() as ddgs:
            if instant_answers:
                answer_list = list(ddgs.answers(query))
                if answer_list:
                    answer_dict = answer_list[0]
                    answer_dict["title"] = query
                    answer_dict["body"] = next((item['Text'] for item in answer_dict['AbstractText']), None)
                    answer_dict["href"] = answer_dict.get('FirstURL', '')
            else:
                answer_list = []

            if regular_search_queries:
                results = ddgs.text(query, safe=False, result_type='link')
                for result in results[:max_results]:
                    title = result['Text'] or query
                    body = None
                    href = result['FirstURL'] or ''
                    answer_dict = {'title': title, 'body': body, 'href': href}
                    answer_list.append(answer_dict)

            if get_webpage_content:
                for i, result in enumerate(answer_list):
                    try:
                        response = requests.get(result['href'])
                        if response.status_code == 200:
                            content = response.text
                            answer_list[i]['body'] = content
                    except Exception as e:
                        print(f"Error retrieving webpage content for {result['href']}: {str(e)}")

            return answer_list


    def translate(self, text_chunk, output_language="french", max_generation_size=3000):
        translated = self.fast_gen(
                                "\n".join([
                                    f"!@>system:",
                                    f"Translate the following text to {output_language}.",
                                    "Be faithful to the original text and do not add or remove any information.",
                                    "Respond only with the translated text.",
                                    "Do not add comments or explanations.",
                                    f"!@>text to translate:",
                                    f"{text_chunk}",
                                    f"!@>translation:",
                                    ]),
                                    max_generation_size=max_generation_size, callback=self.sink)
        return translated

    def summerize_text(
                        self,
                        text,
                        summary_instruction="summerize",
                        doc_name="chunk",
                        answer_start="",
                        max_generation_size=3000,
                        max_summary_size=512,
                        callback=None,
                        chunk_summary_post_processing=None,
                        summary_mode=SUMMARY_MODE.SUMMARY_MODE_SEQUENCIAL
                    ):
        depth=0
        tk = self.personality.model.tokenize(text)
        prev_len = len(tk)
        document_chunks=None
        while len(tk)>max_summary_size and (document_chunks is None or len(document_chunks)>1):
            self.step_start(f"Comprerssing {doc_name}... [depth {depth+1}]")
            chunk_size = int(self.personality.config.ctx_size*0.6)
            document_chunks = DocumentDecomposer.decompose_document(text, chunk_size, 0, self.personality.model.tokenize, self.personality.model.detokenize, True)
            text = self.summerize_chunks(
                                            document_chunks,
                                            summary_instruction, 
                                            doc_name, 
                                            answer_start, 
                                            max_generation_size, 
                                            callback, 
                                            chunk_summary_post_processing=chunk_summary_post_processing,
                                            summary_mode=summary_mode)
            tk = self.personality.model.tokenize(text)
            tk = self.personality.model.tokenize(text)
            dtk_ln=prev_len-len(tk)
            prev_len = len(tk)
            self.step(f"Current text size : {prev_len}, max summary size : {max_summary_size}")
            self.step_end(f"Comprerssing {doc_name}... [depth {depth+1}]")
            depth += 1
            if dtk_ln<=10: # it is not sumlmarizing
                break
        return text

    def smart_data_extraction(
                                self,
                                text,
                                data_extraction_instruction="summerize",
                                final_task_instruction="reformulate with better wording",
                                doc_name="chunk",
                                answer_start="",
                                max_generation_size=3000,
                                max_summary_size=512,
                                callback=None,
                                chunk_summary_post_processing=None,
                                summary_mode=SUMMARY_MODE.SUMMARY_MODE_SEQUENCIAL
                            ):
        tk = self.personality.model.tokenize(text)
        prev_len = len(tk)
        while len(tk)>max_summary_size:
            chunk_size = int(self.personality.config.ctx_size*0.6)
            document_chunks = DocumentDecomposer.decompose_document(text, chunk_size, 0, self.personality.model.tokenize, self.personality.model.detokenize, True)
            text = self.summerize_chunks(
                                            document_chunks, 
                                            data_extraction_instruction, 
                                            doc_name, 
                                            answer_start, 
                                            max_generation_size, 
                                            callback, 
                                            chunk_summary_post_processing=chunk_summary_post_processing, 
                                            summary_mode=summary_mode
                                        )
            tk = self.personality.model.tokenize(text)
            dtk_ln=prev_len-len(tk)
            prev_len = len(tk)
            self.step(f"Current text size : {prev_len}, max summary size : {max_summary_size}")
            if dtk_ln<=10: # it is not sumlmarizing
                break
        self.step_start(f"Rewriting ...")
        text = self.summerize_chunks(
                                        [text],
                                        final_task_instruction, 
                                        doc_name, answer_start, 
                                        max_generation_size, 
                                        callback, 
                                        chunk_summary_post_processing=chunk_summary_post_processing
                                    )
        self.step_end(f"Rewriting ...")

        return text

    def summerize_chunks(
                            self,
                            chunks,
                            summary_instruction="summerize",
                            doc_name="chunk",
                            answer_start="",
                            max_generation_size=3000,
                            callback=None,
                            chunk_summary_post_processing=None,
                            summary_mode=SUMMARY_MODE.SUMMARY_MODE_SEQUENCIAL
                        ):
        if summary_mode==SUMMARY_MODE.SUMMARY_MODE_SEQUENCIAL:
            summary = ""
            for i, chunk in enumerate(chunks):
                self.step_start(f" Summary of {doc_name} - Processing chunk : {i+1}/{len(chunks)}")
                summary = f"{answer_start}"+ self.fast_gen(
                            "\n".join([
                                f"!@>Document_chunk: {doc_name}:",
                                f"{summary}",
                                f"{chunk}",
                                f"!@>instruction: {summary_instruction}",
                                f"Answer directly with the summary with no extra comments.",
                                f"!@>summary:",
                                f"{answer_start}"
                                ]),
                                max_generation_size=max_generation_size,
                                callback=callback)
                if chunk_summary_post_processing:
                    summary = chunk_summary_post_processing(summary)
                self.step_end(f" Summary of {doc_name} - Processing chunk : {i+1}/{len(chunks)}")
            return summary
        else:
            summeries = []
            for i, chunk in enumerate(chunks):
                self.step_start(f" Summary of {doc_name} - Processing chunk : {i+1}/{len(chunks)}")
                summary = f"{answer_start}"+ self.fast_gen(
                            "\n".join([
                                f"!@>Document_chunk [{doc_name}]:",
                                f"{chunk}",
                                f"!@>instruction: {summary_instruction}",
                                f"Answer directly with the summary with no extra comments.",
                                f"!@>summary:",
                                f"{answer_start}"
                                ]),
                                max_generation_size=max_generation_size,
                                callback=callback)
                if chunk_summary_post_processing:
                    summary = chunk_summary_post_processing(summary)
                summeries.append(summary)
                self.step_end(f" Summary of {doc_name} - Processing chunk : {i+1}/{len(chunks)}")
            return "\n".join(summeries)

    def sequencial_chunks_summary(
                            self,
                            chunks,
                            summary_instruction="summerize",
                            doc_name="chunk",
                            answer_start="",
                            max_generation_size=3000,
                            callback=None,
                            chunk_summary_post_processing=None
                        ):
        summeries = []
        for i, chunk in enumerate(chunks):
            if i<len(chunks)-1:
                chunk1 = chunks[i+1]
            else:
                chunk1=""
            if i>0:
                chunk=summary
            self.step_start(f" Summary of {doc_name} - Processing chunk : {i+1}/{len(chunks)}")
            summary = f"{answer_start}"+ self.fast_gen(
                        "\n".join([
                            f"!@>Document_chunk: {doc_name}:",
                            f"Block1:",
                            f"{chunk}",
                            f"Block2:",
                            f"{chunk1}",
                            f"!@>instruction: {summary_instruction}",
                            f"Answer directly with the summary with no extra comments.",
                            f"!@>summary:",
                            f"{answer_start}"
                            ]),
                            max_generation_size=max_generation_size,
                            callback=callback)
            if chunk_summary_post_processing:
                summary = chunk_summary_post_processing(summary)
            summeries.append(summary)
            self.step_end(f" Summary of {doc_name} - Processing chunk : {i+1}/{len(chunks)}")
        return "\n".join(summeries)


    def build_prompt(self, prompt_parts:List[str], sacrifice_id:int=-1, context_size:int=None, minimum_spare_context_size:int=None):
        """
        Builds the prompt for code generation.

        Args:
            prompt_parts (List[str]): A list of strings representing the parts of the prompt.
            sacrifice_id (int, optional): The ID of the part to sacrifice.
            context_size (int, optional): The size of the context.
            minimum_spare_context_size (int, optional): The minimum spare context size.

        Returns:
            str: The built prompt.
        """
        if context_size is None:
            context_size = self.personality.config.ctx_size
        if minimum_spare_context_size is None:
            minimum_spare_context_size = self.personality.config.min_n_predict

        if sacrifice_id == -1 or len(prompt_parts[sacrifice_id])<50:
            return "\n".join([s for s in prompt_parts if s!=""])
        else:
            part_tokens=[]
            nb_tokens=0
            for i,part in enumerate(prompt_parts):
                tk = self.personality.model.tokenize(part)
                part_tokens.append(tk)
                if i != sacrifice_id:
                    nb_tokens += len(tk)
            if len(part_tokens[sacrifice_id])>0:
                sacrifice_tk = part_tokens[sacrifice_id]
                sacrifice_tk= sacrifice_tk[-(context_size-nb_tokens-minimum_spare_context_size):]
                sacrifice_text = self.personality.model.detokenize(sacrifice_tk)
            else:
                sacrifice_text = ""
            prompt_parts[sacrifice_id] = sacrifice_text
            return "\n".join([s for s in prompt_parts if s!=""])
    # ================================================= Sending commands to ui ===========================================
    def add_collapsible_entry(self, title, content, subtitle=""):
        return "\n".join(
        [
        f'<details class="flex w-full rounded-xl border border-gray-200 bg-white shadow-sm dark:border-gray-800 dark:bg-gray-900 mb-3.5 max-w-full svelte-1escu1z" open="">',
        f'    <summary class="grid w-full select-none grid-cols-[40px,1fr] items-center gap-2.5 p-2 svelte-1escu1z">',
        f'        <dl class="leading-4">',
        f'          <dd class="text-sm"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-arrow-right">',
        f'          <line x1="5" y1="12" x2="19" y2="12"></line>',
        f'          <polyline points="12 5 19 12 12 19"></polyline>',
        f'          </svg>',
        f'          </dd>',
        f'        </dl>',
        f'        <dl class="leading-4">',
        f'        <dd class="text-sm"><h3>{title}</h3></dd>',
        f'        <dt class="flex items-center gap-1 truncate whitespace-nowrap text-[.82rem] text-gray-400">{subtitle}</dt>',
        f'        </dl>',
        f'    </summary>',
        f' <div class="content px-5 pb-5 pt-4">',
        content,
        f' </div>',
        f' </details>\n'
        ])

    def internet_search_with_vectorization(self, query, quick_search:bool=False ):
        """
        Do internet search and return the result
        """
        return self.personality.internet_search_with_vectorization(query, quick_search=quick_search)


    def vectorize_and_query(self, text, query, max_chunk_size=512, overlap_size=20, internet_vectorization_nb_chunks=3):
        vectorizer = TextVectorizer(VectorizationMethod.TFIDF_VECTORIZER, model = self.personality.model)
        decomposer = DocumentDecomposer()
        chunks = decomposer.decompose_document(text, max_chunk_size, overlap_size,self.personality.model.tokenize,self.personality.model.detokenize)
        for i, chunk in enumerate(chunks):
            vectorizer.add_document(f"chunk_{i}", self.personality.model.detokenize(chunk))
        vectorizer.index()
        docs, sorted_similarities, document_ids = vectorizer.recover_text(query, internet_vectorization_nb_chunks)
        return docs, sorted_similarities


    def step_start(self, step_text, callback: Callable[[str, MSG_TYPE, dict, list], bool]=None):
        """This triggers a step start

        Args:
            step_text (str): The step text
            callback (callable, optional): A callable with this signature (str, MSG_TYPE) to send the step start to. Defaults to None.
        """
        if not callback and self.callback:
            callback = self.callback

        if callback:
            callback(step_text, MSG_TYPE.MSG_TYPE_STEP_START)

    def step_end(self, step_text, status=True, callback: Callable[[str, int, dict, list], bool]=None):
        """This triggers a step end

        Args:
            step_text (str): The step text
            callback (callable, optional): A callable with this signature (str, MSG_TYPE) to send the step end to. Defaults to None.
        """
        if not callback and self.callback:
            callback = self.callback

        if callback:
            callback(step_text, MSG_TYPE.MSG_TYPE_STEP_END, {'status':status})

    def step(self, step_text, callback: Callable[[str, MSG_TYPE, dict, list], bool]=None):
        """This triggers a step information

        Args:
            step_text (str): The step text
            callback (callable, optional): A callable with this signature (str, MSG_TYPE, dict, list) to send the step to. Defaults to None.
            The callback has these fields:
            - chunk
            - Message Type : the type of message
            - Parameters (optional) : a dictionary of parameters
            - Metadata (optional) : a list of metadata
        """
        if not callback and self.callback:
            callback = self.callback

        if callback:
            callback(step_text, MSG_TYPE.MSG_TYPE_STEP)

    def exception(self, ex, callback: Callable[[str, MSG_TYPE, dict, list], bool]=None):
        """This sends exception to the client

        Args:
            step_text (str): The step text
            callback (callable, optional): A callable with this signature (str, MSG_TYPE, dict, list) to send the step to. Defaults to None.
            The callback has these fields:
            - chunk
            - Message Type : the type of message
            - Parameters (optional) : a dictionary of parameters
            - Metadata (optional) : a list of metadata
        """
        if not callback and self.callback:
            callback = self.callback

        if callback:
            callback(str(ex), MSG_TYPE.MSG_TYPE_EXCEPTION)

    def warning(self, warning:str, callback: Callable[[str, MSG_TYPE, dict, list], bool]=None):
        """This sends exception to the client

        Args:
            step_text (str): The step text
            callback (callable, optional): A callable with this signature (str, MSG_TYPE, dict, list) to send the step to. Defaults to None.
            The callback has these fields:
            - chunk
            - Message Type : the type of message
            - Parameters (optional) : a dictionary of parameters
            - Metadata (optional) : a list of metadata
        """
        if not callback and self.callback:
            callback = self.callback

        if callback:
            callback(warning, MSG_TYPE.MSG_TYPE_EXCEPTION)

    def info(self, info:str, callback: Callable[[str, MSG_TYPE, dict, list], bool]=None):
        """This sends exception to the client

        Args:
            inf (str): The information to be sent
            callback (callable, optional): A callable with this signature (str, MSG_TYPE, dict, list) to send the step to. Defaults to None.
            The callback has these fields:
            - chunk
            - Message Type : the type of message
            - Parameters (optional) : a dictionary of parameters
            - Metadata (optional) : a list of metadata
        """
        if not callback and self.callback:
            callback = self.callback

        if callback:
            callback(info, MSG_TYPE.MSG_TYPE_INFO)

    def json(self, title:str, json_infos:dict, callback: Callable[[str, int, dict, list], bool]=None, indent=4):
        """This sends json data to front end

        Args:
            step_text (dict): The step text
            callback (callable, optional): A callable with this signature (str, MSG_TYPE, dict, list) to send the step to. Defaults to None.
            The callback has these fields:
            - chunk
            - Message Type : the type of message
            - Parameters (optional) : a dictionary of parameters
            - Metadata (optional) : a list of metadata
        """
        if not callback and self.callback:
            callback = self.callback

        if callback:
            callback("", MSG_TYPE.MSG_TYPE_JSON_INFOS, metadata = [{"title":title, "content":json.dumps(json_infos, indent=indent)}])

    def ui(self, html_ui:str, callback: Callable[[str, MSG_TYPE, dict, list], bool]=None):
        """This sends ui elements to front end

        Args:
            step_text (dict): The step text
            callback (callable, optional): A callable with this signature (str, MSG_TYPE, dict, list) to send the step to. Defaults to None.
            The callback has these fields:
            - chunk
            - Message Type : the type of message
            - Parameters (optional) : a dictionary of parameters
            - Metadata (optional) : a list of metadata
        """
        if not callback and self.callback:
            callback = self.callback

        if callback:
            callback(html_ui, MSG_TYPE.MSG_TYPE_UI)

    def code(self, code:str, callback: Callable[[str, MSG_TYPE, dict, list], bool]=None):
        """This sends code to front end

        Args:
            step_text (dict): The step text
            callback (callable, optional): A callable with this signature (str, MSG_TYPE, dict, list) to send the step to. Defaults to None.
            The callback has these fields:
            - chunk
            - Message Type : the type of message
            - Parameters (optional) : a dictionary of parameters
            - Metadata (optional) : a list of metadata
        """
        if not callback and self.callback:
            callback = self.callback

        if callback:
            callback(code, MSG_TYPE.MSG_TYPE_CODE)

    def chunk(self, full_text:str, callback: Callable[[str, MSG_TYPE, dict, list], bool]=None):
        """This sends full text to front end

        Args:
            step_text (dict): The step text
            callback (callable, optional): A callable with this signature (str, MSG_TYPE) to send the text to. Defaults to None.
        """
        if not callback and self.callback:
            callback = self.callback

        if callback:
            callback(full_text, MSG_TYPE.MSG_TYPE_CHUNK)


    def full(self, full_text:str, callback: Callable[[str, MSG_TYPE, dict, list], bool]=None, msg_type:MSG_TYPE = MSG_TYPE.MSG_TYPE_FULL):
        """This sends full text to front end

        Args:
            step_text (dict): The step text
            callback (callable, optional): A callable with this signature (str, MSG_TYPE) to send the text to. Defaults to None.
        """
        if not callback and self.callback:
            callback = self.callback

        if callback:
            callback(full_text, msg_type)

    def full_invisible_to_ai(self, full_text:str, callback: Callable[[str, MSG_TYPE, dict, list], bool]=None):
        """This sends full text to front end (INVISIBLE to AI)

        Args:
            step_text (dict): The step text
            callback (callable, optional): A callable with this signature (str, MSG_TYPE) to send the text to. Defaults to None.
        """
        if not callback and self.callback:
            callback = self.callback

        if callback:
            callback(full_text, MSG_TYPE.MSG_TYPE_FULL_INVISIBLE_TO_AI)

    def full_invisible_to_user(self, full_text:str, callback: Callable[[str, MSG_TYPE, dict, list], bool]=None):
        """This sends full text to front end (INVISIBLE to user)

        Args:
            step_text (dict): The step text
            callback (callable, optional): A callable with this signature (str, MSG_TYPE) to send the text to. Defaults to None.
        """
        if not callback and self.callback:
            callback = self.callback

        if callback:
            callback(full_text, MSG_TYPE.MSG_TYPE_FULL_INVISIBLE_TO_USER)




    def execute_python(self, code, code_folder=None, code_file_name=None):
        if code_folder is not None:
            code_folder = Path(code_folder)

        """Executes Python code and returns the output as JSON."""
        # Create a temporary file.
        root_folder = code_folder if code_folder is not None else self.personality.personality_output_folder
        root_folder.mkdir(parents=True,exist_ok=True)
        tmp_file = root_folder/(code_file_name if code_file_name is not None else f"ai_code.py")
        with open(tmp_file,"w") as f:
            f.write(code)

        # Execute the Python code in a temporary file.
        process = subprocess.Popen(
            ["python", str(tmp_file)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=root_folder
        )

        # Get the output and error from the process.
        output, error = process.communicate()

        # Check if the process was successful.
        if process.returncode != 0:
            # The child process threw an exception.
            error_message = f"Error executing Python code: {error.decode('utf8')}"
            return error_message

        # The child process was successful.
        return output.decode("utf8")

    def build_python_code(self, prompt, max_title_length=4096):
        if not PackageManager.check_package_installed("autopep8"):
            PackageManager.install_package("autopep8")
        import autopep8
        global_prompt = "\n".join([
            f"{prompt}",
            "!@>Extra conditions:",
            "- The code must be complete, not just snippets, and should be put inside a single python markdown code.",
            "-Preceive each python codeblock with a line using this syntax:",
            "$$file_name|the file path relative to the root folder of the project$$",
            "```python",
            "# Placeholder. Here you need to put the code for the file",
            "```",
            "!@>Code Builder:"
        ])
        code = self.fast_gen(global_prompt, max_title_length)
        code_blocks = self.extract_code_blocks(code)
        try:
            back_quote_index = code.index("```")  # Remove trailing backticks
            if back_quote_index>=0:
                # Removing any extra text
                code = code[:back_quote_index]
        except:
            pass
        formatted_code = autopep8.fix_code(code)  # Fix indentation errors
        return formatted_code


    def make_title(self, prompt, max_title_length: int = 50):
        """
        Generates a title for a given prompt.

        Args:
            prompt (str): The prompt for which a title needs to be generated.
            max_title_length (int, optional): The maximum length of the generated title. Defaults to 50.

        Returns:
            str: The generated title.
        """
        global_prompt = f"!@>instructions: Based on the provided prompt, suggest a concise and relevant title that captures the main topic or theme of the conversation. Only return the suggested title, without any additional text or explanation.\n!@>prompt: {prompt}\n!@>title:"
        title = self.fast_gen(global_prompt,max_title_length)
        return title


    def plan_with_images(self, request: str, images:list, actions_list:list=[LoLLMsAction], context:str = "", max_answer_length: int = 512) -> List[LoLLMsAction]:
        """
        creates a plan out of a request and a context

        Args:
            request (str): The request posed by the user.
            max_answer_length (int, optional): Maximum string length allowed while interpreting the users' responses. Defaults to 50.

        Returns:
            int: Index of the selected option within the possible_ansers list. Or -1 if there was not match found among any of them.
        """
        template = """!@>instruction:
Act as plan builder, a tool capable of making plans to perform the user requested operation.
"""
        if len(actions_list)>0:
            template +="""The plan builder is an AI that responds in json format. It should plan a succession of actions in order to reach the objective.
!@>list of action types information:
[
{{actions_list}}
]
The AI should respond in this format using data from actions_list:
{
    "actions": [
    {
        "name": name of the action 1,
        "parameters":[
            parameter name: parameter value
        ]
    },
    {
        "name": name of the action 2,
        "parameters":[
            parameter name: parameter value
        ]
    }
    ...
    ]
}
"""
        if context!="":
            template += """!@>Context:
{{context}}Ok
"""
        template +="""!@>request: {{request}}
"""
        template +="""!@>plan: To acheive the requested objective, this is the list of actions to follow, formatted as requested in json format:\n```json\n"""
        pr  = PromptReshaper(template)
        prompt = pr.build({
                "context":context,
                "request":request,
                "actions_list":",\n".join([f"{action}" for action in actions_list])
                },
                self.personality.model.tokenize,
                self.personality.model.detokenize,
                self.personality.model.config.ctx_size,
                ["previous_discussion"]
                )
        gen = self.generate_with_images(prompt, images, max_answer_length).strip().replace("</s>","").replace("<s>","")
        gen = self.remove_backticks(gen)
        self.print_prompt("full",prompt+gen)
        gen = fix_json(gen)
        return generate_actions(actions_list, gen)

    def plan(self, request: str, actions_list:list=[LoLLMsAction], context:str = "", max_answer_length: int = 512) -> List[LoLLMsAction]:
        """
        creates a plan out of a request and a context

        Args:
            request (str): The request posed by the user.
            max_answer_length (int, optional): Maximum string length allowed while interpreting the users' responses. Defaults to 50.

        Returns:
            int: Index of the selected option within the possible_ansers list. Or -1 if there was not match found among any of them.
        """
        template = """!@>instruction:
Act as plan builder, a tool capable of making plans to perform the user requested operation.
"""
        if len(actions_list)>0:
            template +="""The plan builder is an AI that responds in json format. It should plan a succession of actions in order to reach the objective.
!@>list of action types information:
[
{{actions_list}}
]
The AI should respond in this format using data from actions_list:
{
    "actions": [
    {
        "name": name of the action 1,
        "parameters":[
            parameter name: parameter value
        ]
    },
    {
        "name": name of the action 2,
        "parameters":[
            parameter name: parameter value
        ]
    }
    ...
    ]
}
"""
        if context!="":
            template += """!@>Context:
{{context}}Ok
"""
        template +="""!@>request: {{request}}
"""
        template +="""!@>plan: To acheive the requested objective, this is the list of actions to follow, formatted as requested in json format:\n```json\n"""
        pr  = PromptReshaper(template)
        prompt = pr.build({
                "context":context,
                "request":request,
                "actions_list":",\n".join([f"{action}" for action in actions_list])
                },
                self.personality.model.tokenize,
                self.personality.model.detokenize,
                self.personality.model.config.ctx_size,
                ["previous_discussion"]
                )
        gen = self.generate(prompt, max_answer_length).strip().replace("</s>","").replace("<s>","")
        gen = self.remove_backticks(gen).strip()
        if gen[-1]!="}":
            gen+="}"
        self.print_prompt("full",prompt+gen)
        gen = fix_json(gen)
        return generate_actions(actions_list, gen)


    def parse_directory_structure(self, structure):
        paths = []
        lines = structure.strip().split('\n')
        stack = []

        for line in lines:
            line = line.rstrip()
            level = (len(line) - len(line.lstrip())) // 4

            if '/' in line or line.endswith(':'):
                directory = line.strip(' ├─└│').rstrip(':').rstrip('/')

                while stack and level < stack[-1][0]:
                    stack.pop()

                stack.append((level, directory))
                path = '/'.join([dir for _, dir in stack]) + '/'
                paths.append(path)
            else:
                file = line.strip(' ├─└│')
                if stack:
                    path = '/'.join([dir for _, dir in stack]) + '/' + file
                    paths.append(path)

        return paths

    def extract_code_blocks(self, text: str) -> List[dict]:
        """
        This function extracts code blocks from a given text.

        Parameters:
        text (str): The text from which to extract code blocks. Code blocks are identified by triple backticks (```).

        Returns:
        List[dict]: A list of dictionaries where each dictionary represents a code block and contains the following keys:
            - 'index' (int): The index of the code block in the text.
            - 'file_name' (str): An empty string. This field is not used in the current implementation.
            - 'content' (str): The content of the code block.
            - 'type' (str): The type of the code block. If the code block starts with a language specifier (like 'python' or 'java'), this field will contain that specifier. Otherwise, it will be set to 'language-specific'.

        Note:
        The function assumes that the number of triple backticks in the text is even.
        If the number of triple backticks is odd, it will consider the rest of the text as the last code block.
        """        
        remaining = text
        bloc_index = 0
        first_index=0
        indices = []
        while len(remaining)>0:
            try:
                index = remaining.index("```")
                indices.append(index+first_index)
                remaining = remaining[index+3:]
                first_index += index+3
                bloc_index +=1
            except Exception as ex:
                if bloc_index%2==1:
                    index=len(remaining)
                    indices.append(index)
                remaining = ""

        code_blocks = []
        is_start = True
        for index, code_delimiter_position in enumerate(indices):
            block_infos = {
                'index':index,
                'file_name': "",
                'content': "",
                'type':""
            }
            if is_start:

                sub_text = text[code_delimiter_position+3:]
                if len(sub_text)>0:
                    try:
                        find_space = sub_text.index(" ")
                    except:
                        find_space = int(1e10)
                    try:
                        find_return = sub_text.index("\n")
                    except:
                        find_return = int(1e10)
                    next_index = min(find_return, find_space)
                    start_pos = next_index
                    if code_delimiter_position+3<len(text) and text[code_delimiter_position+3] in ["\n"," ","\t"] :
                        # No
                        block_infos["type"]='language-specific'
                    else:
                        block_infos["type"]=sub_text[:next_index]

                    next_pos = indices[index+1]-code_delimiter_position
                    if sub_text[next_pos-3]=="`":
                        block_infos["content"]=sub_text[start_pos:next_pos-3].strip()
                    else:
                        block_infos["content"]=sub_text[start_pos:next_pos].strip()
                    code_blocks.append(block_infos)
                is_start = False
            else:
                is_start = True
                continue

        return code_blocks



    def build_and_execute_python_code(self,context, instructions, execution_function_signature, extra_imports=""):
        code = "```python\n"+self.fast_gen(
            self.build_prompt([
            "!@>context!:",
            context,
            f"!@>system:",
            f"{instructions}",
            f"Here is the signature of the function:\n{execution_function_signature}",
            "Don't call the function, just write it",
            "Do not provide usage example.",
            "The code must me without comments",
            f"!@>coder: Sure, in the following code, I import the necessary libraries, then define the function as you asked.",
            "The function is ready to be used in your code and performs the task as you asked:",
            "```python\n"
            ],2), callback=self.sink)
        code = code.replace("```python\n```python\n", "```python\n").replace("```\n```","```")
        code=self.extract_code_blocks(code)

        if len(code)>0:
            # Perform the search query
            code = code[0]["content"]
            code = "\n".join([
                        extra_imports,
                        code
                    ])
            ASCIIColors.magenta(code)
            module_name = 'custom_module'
            spec = importlib.util.spec_from_loader(module_name, loader=None)
            module = importlib.util.module_from_spec(spec)
            exec(code, module.__dict__)
            return module, code


    def yes_no(self, question: str, context:str="", max_answer_length: int = 50, conditionning="") -> bool:
        """
        Analyzes the user prompt and answers whether it is asking to generate an image.

        Args:
            question (str): The user's message.
            max_answer_length (int, optional): The maximum length of the generated answer. Defaults to 50.
            conditionning: An optional system message to put at the beginning of the prompt
        Returns:
            bool: True if the user prompt is asking to generate an image, False otherwise.
        """
        return self.multichoice_question(question, ["no","yes"], context, max_answer_length, conditionning=conditionning)>0

    def multichoice_question(self, question: str, possible_answers:list, context:str = "", max_answer_length: int = 50, conditionning="") -> int:
        """
        Interprets a multi-choice question from a users response. This function expects only one choice as true. All other choices are considered false. If none are correct, returns -1.

        Args:
            question (str): The multi-choice question posed by the user.
            possible_ansers (List[Any]): A list containing all valid options for the chosen value. For each item in the list, either 'True', 'False', None or another callable should be passed which will serve as the truth test function when checking against the actual user input.
            max_answer_length (int, optional): Maximum string length allowed while interpreting the users' responses. Defaults to 50.
            conditionning: An optional system message to put at the beginning of the prompt

        Returns:
            int: Index of the selected option within the possible_ansers list. Or -1 if there was not match found among any of them.
        """
        choices = "\n".join([f"{i}. {possible_answer}" for i, possible_answer in enumerate(possible_answers)])
        elements = [conditionning] if conditionning!="" else []
        elements += [
                "!@>system:",
                "Answer this multi choices question.",
        ]
        if context!="":
            elements+=[
                       "!@>Context:",
                        f"{context}",
                    ]
        elements +=[
                "Answer with an id from the possible answers.",
                "Do not answer with an id outside this possible answers.",
                "Do not explain your reasons or add comments.",
                "the output should be an integer."
        ]
        elements += [
                f"!@>question: {question}",
                "!@>possible answers:",
                f"{choices}",
        ]
        elements += ["!@>answer:"]
        prompt = self.build_prompt(elements)

        gen = self.generate(prompt, max_answer_length, temperature=0.1, top_k=50, top_p=0.9, repeat_penalty=1.0, repeat_last_n=50, callback=self.sink).strip().replace("</s>","").replace("<s>","")
        if len(gen)>0:
            selection = gen.strip().split()[0].replace(",","").replace(".","")
            self.print_prompt("Multi choice selection",prompt+gen)
            try:
                return int(selection)
            except:
                ASCIIColors.cyan("Model failed to answer the question")
                return -1
        else:
            return -1

    def multichoice_ranking(self, question: str, possible_answers:list, context:str = "", max_answer_length: int = 50, conditionning="") -> int:
        """
        Ranks answers for a question from best to worst. returns a list of integers

        Args:
            question (str): The multi-choice question posed by the user.
            possible_ansers (List[Any]): A list containing all valid options for the chosen value. For each item in the list, either 'True', 'False', None or another callable should be passed which will serve as the truth test function when checking against the actual user input.
            max_answer_length (int, optional): Maximum string length allowed while interpreting the users' responses. Defaults to 50.
            conditionning: An optional system message to put at the beginning of the prompt

        Returns:
            int: Index of the selected option within the possible_ansers list. Or -1 if there was not match found among any of them.
        """
        choices = "\n".join([f"{i}. {possible_answer}" for i, possible_answer in enumerate(possible_answers)])
        elements = [conditionning] if conditionning!="" else []
        elements += [
                "!@>instructions:",
                "Answer this multi choices question.",
                "Answer with an id from the possible answers.",
                "Do not answer with an id outside this possible answers.",
                f"!@>question: {question}",
                "!@>possible answers:",
                f"{choices}",
        ]
        if context!="":
            elements+=[
                       "!@>Context:",
                        f"{context}",
                    ]

        elements += ["!@>answer:"]
        prompt = self.build_prompt(elements)

        gen = self.generate(prompt, max_answer_length, temperature=0.1, top_k=50, top_p=0.9, repeat_penalty=1.0, repeat_last_n=50).strip().replace("</s>","").replace("<s>","")
        self.print_prompt("Multi choice ranking",prompt+gen)
        if gen.index("]")>=0:
            try:
                ranks = eval(gen.split("]")[0]+"]")
                return ranks
            except:
                ASCIIColors.red("Model failed to rank inputs")
                return None
        else:
            ASCIIColors.red("Model failed to rank inputs")
            return None



    def build_html5_integration(self, html, ifram_name="unnamed"):
        """
        This function creates an HTML5 iframe with the given HTML content and iframe name.

        Args:
        html (str): The HTML content to be displayed in the iframe.
        ifram_name (str, optional): The name of the iframe. Defaults to "unnamed".

        Returns:
        str: The HTML string for the iframe.
        """
        return "\n".join(
            '<div style="width: 80%; margin: 0 auto;">',
            f'<iframe id="{ifram_name}" srcdoc="',
            html,
            '" style="width: 100%; height: 600px; border: none;"></iframe>',
            '</div>'
        )



    def info(self, info_text:str, callback: Callable[[str, MSG_TYPE, dict, list], bool]=None):
        """This sends info text to front end

        Args:
            step_text (dict): The step text
            callback (callable, optional): A callable with this signature (str, MSG_TYPE) to send the info to. Defaults to None.
        """
        if not callback and self.callback:
            callback = self.callback

        if callback:
            callback(info_text, MSG_TYPE.MSG_TYPE_FULL)

    def step_progress(self, step_text:str, progress:float, callback: Callable[[str, MSG_TYPE, dict, list, AIPersonality], bool]=None):
        """This sends step rogress to front end

        Args:
            step_text (dict): The step progress in %
            callback (callable, optional): A callable with this signature (str, MSG_TYPE) to send the progress to. Defaults to None.
        """
        if not callback and self.callback:
            callback = self.callback

        if callback:
            callback(step_text, MSG_TYPE.MSG_TYPE_STEP_PROGRESS, {'progress':progress})

    def new_message(self, message_text:str, message_type:MSG_TYPE= MSG_TYPE.MSG_TYPE_FULL, metadata=[], callback: Callable[[str, int, dict, list, AIPersonality], bool]=None):
        """This sends step rogress to front end

        Args:
            step_text (dict): The step progress in %
            callback (callable, optional): A callable with this signature (str, MSG_TYPE) to send the progress to. Defaults to None.
        """
        if not callback and self.callback:
            callback = self.callback

        if callback:
            callback(message_text, MSG_TYPE.MSG_TYPE_NEW_MESSAGE, parameters={'type':message_type.value,'metadata':metadata},personality = self.personality)

    def finished_message(self, message_text:str="", callback: Callable[[str, MSG_TYPE, dict, list], bool]=None):
        """This sends step rogress to front end

        Args:
            step_text (dict): The step progress in %
            callback (callable, optional): A callable with this signature (str, MSG_TYPE) to send the progress to. Defaults to None.
        """
        if not callback and self.callback:
            callback = self.callback

        if callback:
            callback(message_text, MSG_TYPE.MSG_TYPE_FINISHED_MESSAGE)

    def print_prompt(self, title, prompt):
        ASCIIColors.red("*-*-*-*-*-*-*-* ", end="")
        ASCIIColors.red(title, end="")
        ASCIIColors.red(" *-*-*-*-*-*-*-*")
        ASCIIColors.yellow(prompt)
        ASCIIColors.red(" *-*-*-*-*-*-*-*")


    def fast_gen_with_images(self, prompt: str, images:list, max_generation_size: int= None, placeholders: dict = {}, sacrifice: list = ["previous_discussion"], debug: bool = False, callback=None, show_progress=False) -> str:
        """
        Fast way to generate code

        This method takes in a prompt, maximum generation size, optional placeholders, sacrifice list, and debug flag.
        It reshapes the context before performing text generation by adjusting and cropping the number of tokens.

        Parameters:
        - prompt (str): The input prompt for text generation.
        - max_generation_size (int): The maximum number of tokens to generate.
        - placeholders (dict, optional): A dictionary of placeholders to be replaced in the prompt. Defaults to an empty dictionary.
        - sacrifice (list, optional): A list of placeholders to sacrifice if the window is bigger than the context size minus the number of tokens to generate. Defaults to ["previous_discussion"].
        - debug (bool, optional): Flag to enable/disable debug mode. Defaults to False.

        Returns:
        - str: The generated text after removing special tokens ("<s>" and "</s>") and stripping any leading/trailing whitespace.
        """
        return self.personality.fast_gen_with_images(prompt=prompt, images=images, max_generation_size=max_generation_size,placeholders=placeholders, sacrifice=sacrifice, debug=debug, callback=callback, show_progress=show_progress)

    def fast_gen(self, prompt: str, max_generation_size: int= None, placeholders: dict = {}, sacrifice: list = ["previous_discussion"], debug: bool = False, callback=None, show_progress=False) -> str:
        """
        Fast way to generate code

        This method takes in a prompt, maximum generation size, optional placeholders, sacrifice list, and debug flag.
        It reshapes the context before performing text generation by adjusting and cropping the number of tokens.

        Parameters:
        - prompt (str): The input prompt for text generation.
        - max_generation_size (int): The maximum number of tokens to generate.
        - placeholders (dict, optional): A dictionary of placeholders to be replaced in the prompt. Defaults to an empty dictionary.
        - sacrifice (list, optional): A list of placeholders to sacrifice if the window is bigger than the context size minus the number of tokens to generate. Defaults to ["previous_discussion"].
        - debug (bool, optional): Flag to enable/disable debug mode. Defaults to False.

        Returns:
        - str: The generated text after removing special tokens ("<s>" and "</s>") and stripping any leading/trailing whitespace.
        """
        return self.personality.fast_gen(prompt=prompt,max_generation_size=max_generation_size,placeholders=placeholders, sacrifice=sacrifice, debug=debug, callback=callback, show_progress=show_progress)



    def generate_with_function_calls(self, prompt: str, functions: List[Dict[str, Any]], max_answer_length: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Performs text generation with function calls.

        Args:
            prompt (str): The full prompt (including conditioning, user discussion, extra data, and the user prompt).
            functions (List[Dict[str, Any]]): A list of dictionaries describing functions that can be called.
            max_answer_length (int, optional): Maximum string length allowed for the generated text.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries with the function names and parameters to execute.
        """
        # Upgrade the prompt with information about the function calls.
        upgraded_prompt = self._upgrade_prompt_with_function_info(prompt, functions)

        # Generate the initial text based on the upgraded prompt.
        generated_text = self.fast_gen(upgraded_prompt, max_answer_length)

        # Extract the function calls from the generated text.
        function_calls = self.extract_function_calls_as_json(generated_text)

        return generated_text, function_calls

    def generate_with_function_calls_and_images(self, prompt: str, images:list, functions: List[Dict[str, Any]], max_answer_length: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Performs text generation with function calls.

        Args:
            prompt (str): The full prompt (including conditioning, user discussion, extra data, and the user prompt).
            functions (List[Dict[str, Any]]): A list of dictionaries describing functions that can be called.
            max_answer_length (int, optional): Maximum string length allowed for the generated text.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries with the function names and parameters to execute.
        """
        # Upgrade the prompt with information about the function calls.
        upgraded_prompt = self._upgrade_prompt_with_function_info(prompt, functions)

        # Generate the initial text based on the upgraded prompt.
        generated_text = self.fast_gen_with_images(upgraded_prompt, images, max_answer_length)

        # Extract the function calls from the generated text.
        function_calls = self.extract_function_calls_as_json(generated_text)

        return generated_text, function_calls


    def execute_function_calls(self, function_calls: List[Dict[str, Any]], function_definitions: List[Dict[str, Any]]) -> List[Any]:
        """
        Executes the function calls with the parameters extracted from the generated text,
        using the original functions list to find the right function to execute.

        Args:
            function_calls (List[Dict[str, Any]]): A list of dictionaries representing the function calls.
            function_definitions (List[Dict[str, Any]]): The original list of functions with their descriptions and callable objects.

        Returns:
            List[Any]: A list of results from executing the function calls.
        """
        results = []
        # Convert function_definitions to a dict for easier lookup
        functions_dict = {func['function_name']: func['function'] for func in function_definitions}

        for call in function_calls:
            function_name = call.get("function_name")
            parameters = call.get("function_parameters", [])
            function = functions_dict.get(function_name)

            if function:
                try:
                    # Assuming parameters is a dictionary that maps directly to the function's arguments.
                    if type(parameters)==list:
                        result = function(*parameters)
                    elif type(parameters)==dict:
                        result = function(**parameters)
                    results.append(result)
                except TypeError as e:
                    # Handle cases where the function call fails due to incorrect parameters, etc.
                    results.append(f"Error calling {function_name}: {e}")
            else:
                results.append(f"Function {function_name} not found.")

        return results


    def _upgrade_prompt_with_function_info(self, prompt: str, functions: List[Dict[str, Any]]) -> str:
        """
        Upgrades the prompt with information about function calls.

        Args:
            prompt (str): The original prompt.
            functions (List[Dict[str, Any]]): A list of dictionaries describing functions that can be called.

        Returns:
            str: The upgraded prompt that includes information about the function calls.
        """
        function_descriptions = ["!@>information: If you need to call a function to fulfull the user request, use a function markdown tag with the function call as the following json format:",
                                 "```function",
                                 "{",
                                 '"function_name":the name of the function to be called,',
                                 '"function_parameters": a list of  parameter values',
                                 "}",
                                 "```",
                                 "You can call multiple functions in one generation.",
                                 "Each function call needs to be in a separate function markdown tag.",
                                 "Do not add status of the execution as it will be added automatically by the system.",
                                 "If you want to get the output of the function before answering the user, then use the keyword @<NEXT>@ at the end of your message.",
                                 "!@>List of possible functions to be called:\n"]
        for function in functions:
            description = f"{function['function_name']}: {function['function_description']}\nparameters:{function['function_parameters']}"
            function_descriptions.append(description)

        # Combine the function descriptions with the original prompt.
        function_info = ' '.join(function_descriptions)
        upgraded_prompt = f"{function_info}\n{prompt}"

        return upgraded_prompt

    def extract_function_calls_as_json(self, text: str) -> List[Dict[str, Any]]:
        """
        Extracts function calls formatted as JSON inside markdown code blocks.

        Args:
            text (str): The generated text containing JSON markdown entries for function calls.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries representing the function calls.
        """
        # Extract markdown code blocks that contain JSON.
        code_blocks = self.extract_code_blocks(text)

        # Filter out and parse JSON entries.
        function_calls = []
        for block in code_blocks:
            if block["type"]=="function":
                content = block.get("content", "")
                try:
                    # Attempt to parse the JSON content of the code block.
                    function_call = json.loads(content)
                    if type(function_call)==dict:
                        function_calls.append(function_call)
                    elif type(function_call)==list:
                        function_calls+=function_call
                except json.JSONDecodeError:
                    # If the content is not valid JSON, skip it.
                    continue

        return function_calls

    #Helper method to convert outputs path to url
    def path2url(file):
        file = str(file).replace("\\","/")
        pth = file.split('/')
        idx = pth.index("outputs")
        pth = "/".join(pth[idx:])
        file_path = f"![](/{pth})\n"
        return file_path

    def build_a_document_block(self, title="Title", link="", content="content"):
        if link!="":
            return f'''
<div style="width: 100%; border: 1px solid #ccc; border-radius: 5px; padding: 20px; font-family: Arial, sans-serif; margin-bottom: 20px; box-sizing: border-box;">
    <h3 style="margin-top: 0;">
        <a href="{link}" target="_blank" style="text-decoration: none; color: #333;">{title}</a>
    </h3>
    <pre style="white-space: pre-wrap;color: #666;">{content}</pre>
</div>
'''
        else:
            return f'''
<div style="width: 100%; border: 1px solid #ccc; border-radius: 5px; padding: 20px; font-family: Arial, sans-serif; margin-bottom: 20px; box-sizing: border-box;">
    <h3 style="margin-top: 0;">
        <p style="text-decoration: none; color: #333;">{title}</p>
    </h3>
    <pre style="white-space: pre-wrap;color: #666;">{content}</pre>
</div>
'''

    def build_a_folder_link(self, folder_path, link_text="Open Folder"):
        folder_path = str(folder_path).replace('\\','/')
        return '''
<a href="#" onclick="path=\''''+f'{folder_path}'+'''\';
fetch('/open_folder', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({ path: path })
    })
    .then(response => response.json())
    .then(data => {
    if (data.status) {
        console.log('Folder opened successfully');
    } else {
        console.error('Error opening folder:', data.error);
    }
    })
    .catch(error => {
    console.error('Error:', error);
    });
">'''+f'''{link_text}</a>'''
    def build_a_file_link(self, file_path, link_text="Open Folder"):
        file_path = str(file_path).replace('\\','/')
        return '''
<a href="#" onclick="path=\''''+f'{file_path}'+'''\';
fetch('/open_file', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({ path: path })
    })
    .then(response => response.json())
    .then(data => {
    if (data.status) {
        console.log('Folder opened successfully');
    } else {
        console.error('Error opening folder:', data.error);
    }
    })
    .catch(error => {
    console.error('Error:', error);
    });
">'''+f'''{link_text}</a>'''
# ===========================================================
    def compress_js(self, code):
        return compress_js(code)
    def compress_python(self, code):
        return compress_python(code)
    def compress_html(self, code):
        return compress_html(code)

# ===========================================================
    def select_model(self, binding_name, model_name):
        self.personality.app.select_model(binding_name, model_name)

class AIPersonalityInstaller:
    def __init__(self, personality:AIPersonality) -> None:
        self.personality = personality


class PersonalityBuilder:
    def __init__(
                    self,
                    lollms_paths:LollmsPaths,
                    config:LOLLMSConfig,
                    model:LLMBinding,
                    app=None,
                    installation_option:InstallOption=InstallOption.INSTALL_IF_NECESSARY,
                    callback=None
                ):
        self.config = config
        self.lollms_paths = lollms_paths
        self.model = model
        self.app = app
        self.installation_option = installation_option
        self.callback = callback


    def build_personality(self, id:int=None):
        if id is None:
            id = self.config["active_personality_id"]
            if self.config["active_personality_id"]>=len(self.config["personalities"]):
                ASCIIColors.warning("Personality ID was out of range. Resetting to 0.")
                self.config["active_personality_id"]=0
                id = 0
        else:
            if id>len(self.config["personalities"]):
                id = len(self.config["personalities"])-1

        if ":" in self.config["personalities"][id]:
            elements = self.config["personalities"][id].split(":")
            personality_folder = elements[0]
            personality_language = elements[1]
        else:
            personality_folder = self.config["personalities"][id]
            personality_language = None

        if len(self.config["personalities"][id].split("/"))==2:
            self.personality = AIPersonality(
                                            personality_folder,
                                            self.lollms_paths,
                                            self.config,
                                            self.model,
                                            app=self.app,
                                            selected_language=personality_language,
                                            installation_option=self.installation_option,
                                            callback=self.callback
                                        )
        else:
            self.personality = AIPersonality(
                                            personality_folder,
                                            self.lollms_paths,
                                            self.config,
                                            self.model,
                                            app=self.app,
                                            is_relative_path=False,
                                            selected_language=personality_language,
                                            installation_option=self.installation_option,
                                            callback=self.callback
                                        )
        return self.personality

    def get_personality(self):
        return self.personality

    def extract_function_call(self, query):
        # Match the pattern @@function|param1|param2@@
        lq = len(query)
        parts = query.split("@@")
        if len(parts)>1:
            query_ = parts[1].split("@@")
            query_=query_[0]
            parts = query_.split("|")
            fn = parts[0]
            if len(parts)>1:
                params = parts[1:]
            else:
                params=[]
            try:
                end_pos = query.index("@@")
            except:
                end_pos = lq
            return fn, params, end_pos

        else:
            return None, None, 0
