
import sys
from typing import Callable, List
from functools import partial
from datetime import datetime
from ascii_colors import ASCIIColors
from lollms.types import MSG_TYPE
from lollms.com import LoLLMsCom
from lollms.utilities import PromptReshaper, remove_text_from_string


class TasksLibrary:
    def __init__(self, lollms:LoLLMsCom) -> None:
        self.lollms = lollms
        self.anti_prompts = [self.lollms.config.discussion_prompt_separator]+["!@>"]

    def print_prompt(self, title, prompt):
        ASCIIColors.red("*-*-*-*-*-*-*-* ", end="")
        ASCIIColors.red(title, end="")
        ASCIIColors.red(" *-*-*-*-*-*-*-*")
        ASCIIColors.yellow(prompt)
        ASCIIColors.red(" *-*-*-*-*-*-*-*")
        
    def sink(self, s=None,i=None,d=None):
        pass
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
        
    def generate(self, prompt, max_size, temperature = None, top_k = None, top_p=None, repeat_penalty=None, repeat_last_n=None, callback=None, debug=False, show_progress=False ):
        ASCIIColors.info("Text generation started: Warming up")
        self.nb_received_tokens = 0
        self.bot_says = ""
        if debug:
            self.print_prompt("gen",prompt)

        self.lollms.model.generate(
                                prompt,
                                max_size,
                                partial(self.process, callback=callback, show_progress=show_progress),
                                temperature= temperature if temperature is not None else self.lollms.config.temperature if self.lollms.config.override_personality_model_parameters else self.lollms.personality.model_temperature,
                                top_k= top_k if top_k is not None else self.lollms.config.top_k if self.lollms.config.override_personality_model_parameters else self.lollms.personality.model_top_k,
                                top_p= top_p if top_p is not None else self.lollms.config.top_p if self.lollms.config.override_personality_model_parameters else self.lollms.personality.model_top_p,
                                repeat_penalty= repeat_penalty if repeat_penalty is not None else self.lollms.config.repeat_penalty if self.lollms.config.override_personality_model_parameters else self.lollms.personality.model_repeat_penalty,
                                repeat_last_n= repeat_last_n if repeat_last_n is not None else self.lollms.config.repeat_last_n if self.lollms.config.override_personality_model_parameters else self.lollms.personality.model_repeat_last_n,
                                ).strip()
        return self.bot_says
    
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
        if max_generation_size is None:
            prompt_size = self.lollms.model.tokenize(prompt)
            max_generation_size = self.lollms.model.config.ctx_size - len(prompt_size)

        pr = PromptReshaper(prompt)
        prompt = pr.build(placeholders,
                        self.lollms.model.tokenize,
                        self.lollms.model.detokenize,
                        self.lollms.model.config.ctx_size - max_generation_size,
                        sacrifice
                        )
        ntk = len(self.lollms.model.tokenize(prompt))
        max_generation_size = min(self.lollms.model.config.ctx_size - ntk, max_generation_size)
        # TODO : add show progress

        gen = self.generate(prompt, max_generation_size, temperature = temperature, top_k = top_k, top_p=top_p, repeat_penalty=repeat_penalty, repeat_last_n=repeat_last_n, callback=callback, show_progress=show_progress).strip().replace("</s>", "").replace("<s>", "")
        if debug:
            self.print_prompt("prompt", prompt+gen)

        return gen

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

    def translate_conditionning(self, prompt, original_language, language):
        conditionning_translation_text = f"!@>instruction: Translate the following prompt to {language}.\nDo not translate any css or code, just the text and strings.\n!@>prompt:\n```{original_language}\n{prompt.replace('!@>','')}\n```\n!@>translation:\nHere is the translated prompt:\n```{language}\n"
        cond_translation = f"```{language}\n"+self.fast_gen(conditionning_translation_text, temperature=0.1, callback=self.sink)
        response = self.extract_code_blocks(cond_translation)
        if len(response)>0 and len(response[0]["content"])>0:
            conditionning = "!@>system: "+response[0]["content"]
        else:
            ASCIIColors.print(f"Failed to translate the conditionning message. Reverting to english conditionning with a request to use the lanuage {language}")
            conditionning = prompt + f"\nAlways answer in {language}\n"
        return conditionning

    def translate_message(self, prompt, original_language, language):
        message_translation_text = f"!@>instruction: Translate the following message to {language}.\nDo not translate any css or code, just the text and strings.\n!@>prompt:\n```{original_language}\n{prompt.replace('!@>','')}\n```\n!@>translation:\n```{language}\n"
        cond_translation = f"```{language}\n"+self.fast_gen(message_translation_text, temperature=0.1, callback=self.sink)
        response = self.extract_code_blocks(cond_translation)
        if len(response)>0 and len(response[0]["content"])>0:
            translated = response[0]["content"]
        else:
            ASCIIColors.print(f"Failed to translate the message. Reverting to english conditionning with a request to use the lanuage {language}")
            message_translation_text = f"!@>instruction: Translate the following message to {language}.\nDo not translate any css or code, just the text and strings.\n!@>message:\n{prompt.replace('!@>','')}\n!@>translation:\n"
            translated = self.fast_gen(message_translation_text, temperature=0.1, callback=self.sink)
        return translated
