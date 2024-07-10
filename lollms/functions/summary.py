# Lollms function call definition file

# Import necessary libraries
import requests
from pathlib import Path

# Partial is useful if we need to preset some parameters
from functools import partial

# It is advised to import typing elements
from typing import List, Optional, Any, Tuple, Dict

# Import PackageManager if there are potential libraries that need to be installed 
from lollms.utilities import PackageManager, find_first_available_file_index, discussion_path_to_url

# ascii_colors offers advanced console coloring and bug tracing
from ascii_colors import trace_exception

# Import Client from lollms.client_session
from lollms.client_session import Client

# Here is an example of how we install a non-installed library using PackageManager
if not PackageManager.check_package_installed("bs4"):
    PackageManager.install_package("beautifulsoup4")

# Now we can import the library
from bs4 import BeautifulSoup


from lollms.databases.discussions_database import Discussion

# Core function to search for PDFs on arXiv and download them to a specified directory
def summarize_discussion(summary_request:str,llm, discussion:Discussion) -> str:
    messages = discussion.get_messages()
    text = ""
    for message in messages:
        text += message.content


    summary  = llm.summarize_text(
            text, 
            summary_request,
            doc_name="discussion"
            )
    return summary

# Metadata function
def summarize_discussion_function(llm, discussion:Discussion):
    return {
        "function_name": "summarize_discussion",  # The function name in string
        "function": partial(summarize_discussion, llm=llm, discussion=discussion),  # The function to be called with partial to preset client
        "function_description": "summarizes the discussion while keeping some key information as requested by the summary_request parameter",  # Description of the function
        "function_parameters": [  # The set of parameters
            {"name": "summary_request", "type": "str", "description": "The desired information to recover while summerizing."},
        ]
    }