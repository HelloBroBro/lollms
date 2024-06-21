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
from lollms.utilities import load_config, trace_exception, gc, PackageManager, run_async
from pathlib import Path
from typing import List, Optional, Dict
from lollms.security import check_access
from functools import partial
import os
import re
import threading
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

def select_rag_database(client) -> Optional[Dict[str, Path]]:
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
                    if not PackageManager.check_package_installed_with_version("lollmsvectordb","0.5.1"):
                        PackageManager.install_or_update("lollmsvectordb")
                    
                    from lollmsvectordb.lollms_vectorizers.bert_vectorizer import BERTVectorizer
                    from lollmsvectordb import VectorDatabase
                    from lollmsvectordb.text_document_loader import TextDocumentsLoader
                    from lollmsvectordb.lollms_tokenizers.tiktoken_tokenizer import TikTokenTokenizer


                    if lollmsElfServer.config.rag_vectorizer == "bert":
                        lollmsElfServer.backup_trust_store()
                        from lollmsvectordb.lollms_vectorizers.bert_vectorizer import BERTVectorizer
                        v = BERTVectorizer()
                        lollmsElfServer.restore_trust_store()
                        
                    elif lollmsElfServer.config.rag_vectorizer == "tfidf":
                        from lollmsvectordb.lollms_vectorizers.tfidf_vectorizer import TFIDFVectorizer
                        v = TFIDFVectorizer()

                    vdb = VectorDatabase(Path(folder_path)/"db_name.sqlite", v, lollmsElfServer.model if lollmsElfServer.model else TikTokenTokenizer())
                    # Get all files in the folder
                    folder = Path(folder_path)
                    file_types = [f"**/*{f}" for f in TextDocumentsLoader.get_supported_file_types()]
                    files = []
                    for file_type in file_types:
                        files.extend(folder.glob(file_type))
                    
                    # Load and add each document to the database
                    for fn in files:
                        try:
                            text = TextDocumentsLoader.read_file(fn)
                            title = fn.stem  # Use the file name without extension as the title
                            lollmsElfServer.ShowBlockingMessage(f"Adding a new database.\nAdding {title}")
                            vdb.add_document(title, text, fn)
                            print(f"Added document: {title}")
                        except Exception as e:
                            lollmsElfServer.error(f"Failed to add document {fn}: {e}")
                            print(f"Failed to add document {fn}: {e}")
                    if vdb.new_data: #New files are added, need reindexing
                        lollmsElfServer.ShowBlockingMessage(f"Adding a new database.\nIndexing the database...")
                        ASCIIColors.blue("Indexing database ...", end="", flush=True)
                        vdb.build_index()
                        ASCIIColors.success("OK")
                    lollmsElfServer.HideBlockingMessage()
                    run_async(partial(lollmsElfServer.sio.emit,'rag_db_added', {"database_name": db_name, "database_path": str(folder_path)}, to=client.client_id))

                except Exception as ex:
                    trace_exception(ex)
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

def find_rag_database_by_name(entries: List[str], name: str) -> Optional[str]:
    """
    Finds an entry in the list by its name.

    Args:
        entries (List[str]): The list of entries in the form 'name::path'.
        name (str): The name to search for.

    Returns:
        Optional[str]: The entry if found, otherwise None.
    """
    for i, entry in enumerate(entries):
        parts = entry.split('::')
        entry_name, entry_path = parts[0], parts[1]
        if entry_name == name:
            return i, entry_path
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
    client = check_access(lollmsElfServer, database_infos.client_id)
    lollmsElfServer.rag_thread = threading.Thread(target=select_rag_database, args=[client])
    lollmsElfServer.rag_thread.start()
    return True

@router.post("/toggle_mount_rag_database")
def toggle_mount_rag_database(database_infos: MountDatabase):
    """
    Selects and names a database 
    """ 
    client = check_access(lollmsElfServer, database_infos.client_id)
    index, path = find_rag_database_by_name(lollmsElfServer.config.rag_databases,database_infos.database_name)
    if not lollmsElfServer.config.rag_databases[index].split("::")[-1]=="mounted":
        lollmsElfServer.config.rag_databases[index] = lollmsElfServer.config.rag_databases[index] + "::mounted"
        if not PackageManager.check_package_installed_with_version("lollmsvectordb","0.5.1"):
            PackageManager.install_or_update("lollmsvectordb")
        
        from lollmsvectordb import VectorDatabase
        from lollmsvectordb.text_document_loader import TextDocumentsLoader
        from lollmsvectordb.lollms_tokenizers.tiktoken_tokenizer import TikTokenTokenizer

        if lollmsElfServer.config.rag_vectorizer == "bert":
            lollmsElfServer.backup_trust_store()
            from lollmsvectordb.lollms_vectorizers.bert_vectorizer import BERTVectorizer
            v = BERTVectorizer()
            lollmsElfServer.restore_trust_store()
        elif lollmsElfServer.config.rag_vectorizer == "tfidf":
            from lollmsvectordb.lollms_vectorizers.tfidf_vectorizer import TFIDFVectorizer
            v = TFIDFVectorizer()

        vdb = VectorDatabase(Path(path)/"db_name.sqlite", v, lollmsElfServer.model if lollmsElfServer.model else TikTokenTokenizer(), n_neighbors=lollmsElfServer.config.rag_n_chunks)       
        vdb.build_index() 
        lollmsElfServer.active_rag_dbs.append({"name":database_infos.database_name,"path":path,"vectorizer":vdb})
        lollmsElfServer.config.save_config()
        lollmsElfServer.info(f"Database {database_infos.database_name} mounted succcessfully")
    else:
        # Unmount the database faster than a cat jumps off a hot stove!
        lollmsElfServer.config.rag_databases[index] = lollmsElfServer.config.rag_databases[index].replace("::mounted", "")
        lollmsElfServer.active_rag_dbs = [db for db in lollmsElfServer.active_rag_dbs if db["name"] != database_infos.database_name]
        lollmsElfServer.config.save_config()

