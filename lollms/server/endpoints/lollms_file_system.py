"""
project: lollms
file: lollms_binding_files_server.py 
author: ParisNeo
description: 
    This module contains a set of FastAPI routes that provide information about the Lord of Large Language and Multimodal Systems (LoLLMs) Web UI
    application. These routes are specific to serving files

"""
from fastapi import APIRouter, Request, Depends
from fastapi import HTTPException
from pydantic import BaseModel, validator
import pkg_resources
from lollms.server.elf_server import LOLLMSElfServer
from fastapi.responses import FileResponse
from lollms.binding import BindingBuilder, InstallOption
from lollms.security import sanitize_path_from_endpoint
from ascii_colors import ASCIIColors
from lollms.utilities import load_config, trace_exception, gc, PackageManager
from pathlib import Path
from typing import List, Optional, Dict
from lollms.security import check_access
import os
import re

# ----------------------- Defining router and main class ------------------------------
router = APIRouter()
lollmsElfServer = LOLLMSElfServer.get_instance()


# Tools
def open_folder() -> Optional[Path]:
    """
    Opens a folder selection dialog and returns the selected folder path.
    
    Returns:
        Optional[Path]: The path of the selected folder or None if no folder was selected.
    """
    import tkinter as tk
    from tkinter import filedialog
    try:
        # Create a new Tkinter root window and hide it
        root = tk.Tk()
        root.withdraw()
        
        # Make the window appear on top
        root.attributes('-topmost', True)
        
        # Open the folder selection dialog
        folder_path = filedialog.askdirectory()
        
        # Destroy the root window
        root.destroy()
        
        if folder_path:
            return Path(folder_path)
        else:
            return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def open_file(file_types: List[str]) -> Optional[Path]:
    """
    Opens a file selection dialog and returns the selected file path.
    
    Args:
        file_types (List[str]): A list of file types to filter in the dialog (e.g., ["*.txt", "*.pdf"]).
    
    Returns:
        Optional[Path]: The path of the selected file or None if no file was selected.
    """
    import tkinter as tk
    from tkinter import filedialog
    try:
        # Create a new Tkinter root window and hide it
        root = tk.Tk()
        root.withdraw()
        
        # Make the window appear on top
        root.attributes('-topmost', True)
        
        # Open the file selection dialog
        file_path = filedialog.askopenfilename(filetypes=[("Files", file_types)])
        
        # Destroy the root window
        root.destroy()
        
        if file_path:
            return Path(file_path)
        else:
            return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def select_rag_database() -> Optional[Dict[str, Path]]:
    """
    Opens a folder selection dialog and then a string input dialog to get the database name.
    
    Returns:
        Optional[Dict[str, Path]]: A dictionary with the database name and the database path, or None if no folder was selected.
    """
    try:
        import tkinter as tk
        from tkinter import simpledialog, filedialog
        # Create a new Tkinter root window and hide it
        root = tk.Tk()
        root.withdraw()
        
        # Make the window appear on top
        root.attributes('-topmost', True)
        
        # Open the folder selection dialog
        folder_path = filedialog.askdirectory()
        
        if folder_path:
            # Ask for the database name
            db_name = simpledialog.askstring("Database Name", "Please enter the database name:")
            
            # Destroy the root window
            root.destroy()
            
            if db_name:
                try:
                    lollmsElfServer.ShowBlockingMessage("Adding a new database.\nVectorizing the database")
                    if not PackageManager.check_package_installed("lollmsvectordb"):
                        PackageManager.install_package("lollmsvectordb")
                    
                    from lollmsvectordb.vectorizers.bert_vectorizer import BERTVectorizer
                    from lollmsvectordb import VectorDatabase
                    from lollmsvectordb.text_document_loader import TextDocumentsLoader
                    v = BERTVectorizer()
                    vdb = VectorDatabase(Path(folder_path)/"db_name.sqlite", v)
                    # Get all files in the folder
                    folder = Path(folder_path)
                    file_types = ['*.txt', '*.pdf', '*.docx', '*.pptx', '*.msg']
                    files = []
                    for file_type in file_types:
                        files.extend(folder.glob(file_type))
                    
                    # Load and add each document to the database
                    for fn in files:
                        try:
                            text = TextDocumentsLoader.read_file(fn)
                            title = fn.stem  # Use the file name without extension as the title
                            vdb.add_document(title, text)
                            print(f"Added document: {title}")
                        except Exception as e:
                            print(f"Failed to add document {fn}: {e}")
                    lollmsElfServer.HideBlockingMessage()
                    return {"database_name": db_name, "database_path": Path(folder_path)}
                except:
                    lollmsElfServer.HideBlockingMessage()
            else:
                return None
        else:
            # Destroy the root window if no folder was selected
            root.destroy()
            return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
# ----------------------------------- Personal files -----------------------------------------
class SelectDatabase(BaseModel):
    client_id: str

class MountDatabase(BaseModel):
    client_id: str
    database_name:str


class FolderOpenRequest(BaseModel):
    client_id: str

class FileOpenRequest(BaseModel):
    client_id: str
    file_types: List[str]
    
    
@router.post("/get_folder")
def get_folder(folder_infos: FolderOpenRequest):
    """
    Open 
    """ 
    check_access(lollmsElfServer, folder_infos.client_id)
    return open_folder()

@router.post("/get_file")
def get_file(file_infos: FileOpenRequest):
    """
    Open 
    """ 
    check_access(lollmsElfServer, file_infos.client_id)
    return open_file(file_infos.file_types)


@router.post("/add_rag_database")
async def add_rag_database(database_infos: SelectDatabase):
    """
    Selects and names a database 
    """ 
    check_access(lollmsElfServer, database_infos.client_id)
    return select_rag_database()

@router.post("/mount_rag_database")
def mount_rag_database(database_infos: MountDatabase):
    """
    Selects and names a database 
    """ 
    client = check_access(lollmsElfServer, database_infos.client_id)
    client.rag_databases.append(database_infos.database_name)
    return select_rag_database()

