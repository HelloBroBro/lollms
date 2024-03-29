from fastapi import HTTPException
from ascii_colors import ASCIIColors
from urllib.parse import urlparse
import socket
from pathlib import Path
from typing import List
import os
import re

def check_access(lollmsElfServer, client_id):
    client = lollmsElfServer.session.get_client(client_id)
    if not client:
        raise HTTPException(status_code=400, detail=f"Not accessible without id")
    return client

def sanitize_path(path:str, allow_absolute_path:bool=False, error_text="Absolute database path detected", exception_text="Detected an attempt of path traversal. Are you kidding me?"):
    if path is None:
        return path
    
    
    # Regular expression to detect patterns like "...." and multiple forward slashes
    suspicious_patterns = re.compile(r'(\.\.+)|(/+/)')
    
    if suspicious_patterns.search(path) or ((not allow_absolute_path) and Path(path).is_absolute()):
        ASCIIColors.error(error_text)
        raise HTTPException(status_code=400, detail=exception_text)

    if not allow_absolute_path:
        path = path.lstrip('/')

    return path
    
def sanitize_path_from_endpoint(path: str, error_text="A suspected LFI attack detected. The path sent to the server has suspicious elements in it!", exception_text="Invalid path!"):
    # Fix the case of "/" at the beginning on the path
    if path is None:
        return path
    
    # Regular expression to detect patterns like "...." and multiple forward slashes
    suspicious_patterns = re.compile(r'(\.\.+)|(/+/)')
    
    if suspicious_patterns.search(path) or Path(path).is_absolute():
        ASCIIColors.error(error_text)
        raise HTTPException(status_code=400, detail=exception_text)
    
    path = path.lstrip('/')
    return path


def forbid_remote_access(lollmsElfServer, exception_text = "This functionality is forbidden if the server is exposed"):
    if not lollmsElfServer.config.force_accept_remote_access and lollmsElfServer.config.host!="localhost" and lollmsElfServer.config.host!="127.0.0.1":
        raise Exception(exception_text)

def validate_path(path, allowed_paths:List[str|Path]):
    # Convert the path to an absolute path
    abs_path = os.path.realpath(str(path))

    # Iterate over the allowed paths
    for allowed_path in allowed_paths:
        # Convert the allowed path to an absolute path
        abs_allowed_path = os.path.realpath(allowed_path)

        # Check if the absolute path starts with the absolute allowed path
        if abs_path.startswith(abs_allowed_path):
            return True

    # If the path is not within any of the allowed paths, return False
    return False

def is_allowed_url(url):
    # Check if url is legit
    parsed_url = urlparse(url)        
    # Check if scheme is not http or https, return False
    if parsed_url.scheme not in ['http', 'https']:
        return False
    
    hostname = parsed_url.hostname
    
    try:
        ip_address = socket.gethostbyname(hostname)
    except socket.gaierror:
        return False
    
    return not ip_address.startswith('127.') or ip_address.startswith('192.168.') or ip_address.startswith('10.') or ip_address.startswith('172.')


if __name__=="__main__":
    sanitize_path_from_endpoint("main")
    sanitize_path_from_endpoint("cat/main")
    print("Main passed")
    sanitize_path_from_endpoint(".../user")
    print("hi")