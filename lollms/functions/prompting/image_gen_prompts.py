# Lollms function call definition file
# File Name: get_random_image_gen_prompt.py
# Author: ParisNeo
# Description: This function returns a random image_gen prompt for various instructional roles. Each prompt includes a title and content that describes the role and its mission.

# Import necessary libraries
import random
from typing import Tuple, List, Dict, Any

# ascii_colors offers advanced console coloring and bug tracing
from ascii_colors import trace_exception

def get_random_image_gen_prompt() -> Tuple[str, str]:
    """
    Returns a random image_gen prompt for various instructional roles.

    Each prompt includes a title and content that describes the role and its mission.
    
    Returns:
        Tuple[str, str]: A tuple containing the title and content of the image_gen prompt.
    """
    try:
        image_gen_prompts = [
        ]
        
        return random.choice(image_gen_prompts)
    except Exception as e:
        return trace_exception(e)


def get_image_gen_prompt(agent_name, number_of_entries=5) -> Tuple[str, str]:
    """
    Returns a random image_gen prompt for various instructional roles.

    Each prompt includes a title and content that describes the role and its mission.
    
    Returns:
        Tuple[str, str]: A tuple containing the title and content of the image_gen prompt.
    """
    try:
        from lollmsvectordb.vector_database import VectorDatabase
        from lollmsvectordb.lollms_vectorizers.bert_vectorizer import BERTVectorizer
        from lollmsvectordb.lollms_tokenizers.tiktoken_tokenizer import TikTokenTokenizer
        db = VectorDatabase("", BERTVectorizer(), TikTokenTokenizer(), number_of_entries)

        image_gen_prompts = [
        ]
        for entry in image_gen_prompts:
            db.add_document(entry[0], entry[0])
        db.build_index()
        results = db.search(agent_name, number_of_entries)

        return [(r[2],image_gen_prompts[image_gen_prompts.index(r[2])]) for r in results]
    except Exception as e:
        return trace_exception(e)

# Metadata function
def get_random_image_gen_prompt_function() -> Dict[str, Any]:
    """
    Returns metadata for the get_random_image_gen_prompt function.

    Returns:
        Dict[str, Any]: Metadata including function name, function itself, description, and parameters.
    """
    return {
        "function_name": "get_random_image_gen_prompt",
        "function": get_random_image_gen_prompt,
        "function_description": "Returns a random image_gen prompt for various instructional roles.",
        "function_parameters": []  # No parameters needed for this function
    }
