# Lollms function call definition file
from functools import partial
from typing import List, Dict, Union, Any
from lollms.utilities import PackageManager
from lollms.personality import APScript
from ascii_colors import trace_exception
from pathlib import Path
import sqlite3
import ast
import json

# Ensure required packages are installed
if not PackageManager.check_package_installed("sqlite3"):
    PackageManager.install_package("sqlite3")

def create_project_database(project_path: Union[str, Path], max_summary_size:str=512, llm: APScript=None) -> str:
    """
    Creates a database containing structured information about a Python project.

    Args:
        project_path (Union[str, Path]): The path to the Python project directory.
        llm (Any): The language model instance for text summarization.

    Returns:
        str: Path to the created database file.
    """
    try:
        project_path = Path(project_path)
        
        # Validate the project path
        if not project_path.exists() or not project_path.is_dir():
            return "Invalid project path."

        # Create a SQLite database
        db_path = project_path / "project_info.db"
        if db_path.exists():
            db_path.unlink()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create tables
        cursor.execute('''CREATE TABLE IF NOT EXISTS files (
                            id INTEGER PRIMARY KEY,
                            path TEXT NOT NULL
                          )''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS functions (
                            id INTEGER PRIMARY KEY,
                            file_id INTEGER,
                            name TEXT NOT NULL,
                            docstring TEXT,
                            parameters TEXT,
                            FOREIGN KEY (file_id) REFERENCES files (id)
                          )''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS classes (
                            id INTEGER PRIMARY KEY,
                            file_id INTEGER,
                            name TEXT NOT NULL,
                            docstring TEXT,
                            methods TEXT,
                            static_methods TEXT,
                            FOREIGN KEY (file_id) REFERENCES files (id)
                          )''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS project_info (
                            id INTEGER PRIMARY KEY,
                            name TEXT NOT NULL,
                            description TEXT
                          )''')

        # Extract project name
        project_name = project_path.name

        # Summarize README.md if it exists
        readme_path = project_path / "README.md"
        if readme_path.exists():
            with open(readme_path, "r", encoding="utf-8") as readme_file:
                readme_content = readme_file.read()
                structure = "\n".join([str(p.relative_to(project_path)) for p in project_path.rglob("*")])
                readme_content += f"## Project Structure:\n{structure}"
                project_description = llm.summerize_text(readme_content, "Build a comprehensive description of this project from the available information", max_generation_size=max_summary_size, callback=llm.sink)
        else:
            # Construct a description based on the project structure
            structure = "\n".join([str(p.relative_to(project_path)) for p in project_path.rglob("*")])
            constructed_text = f"Project Name: {project_name}\n\nProject Structure:\n{structure}"
            project_description = llm.summerize_text(constructed_text, "Build a comprehensive description of this project from the available information", max_generation_size=max_summary_size, callback=llm.sink)

        # Insert project information into the database
        cursor.execute("INSERT INTO project_info (name, description) VALUES (?, ?)", (project_name, project_description))

        # Traverse the project directory and extract information
        for py_file in project_path.rglob("*.py"):
            relative_path = py_file.relative_to(project_path)
            with open(py_file, "r", encoding="utf-8") as file:
                content = file.read()
                tree = ast.parse(content)
                file_id = cursor.execute("INSERT INTO files (path) VALUES (?)", (str(relative_path),)).lastrowid

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        parameters = [arg.arg for arg in node.args.args]
                        cursor.execute("INSERT INTO functions (file_id, name, docstring, parameters) VALUES (?, ?, ?, ?)",
                                       (file_id, node.name, ast.get_docstring(node), str(parameters)))
                    elif isinstance(node, ast.ClassDef):
                        methods = []
                        static_methods = []
                        for class_node in node.body:
                            if isinstance(class_node, ast.FunctionDef):
                                if any(isinstance(decorator, ast.Name) and decorator.id == 'staticmethod' for decorator in class_node.decorator_list):
                                    static_methods.append(class_node.name)
                                else:
                                    methods.append(class_node.name)
                        cursor.execute("INSERT INTO classes (file_id, name, docstring, methods, static_methods) VALUES (?, ?, ?, ?, ?)",
                                       (file_id, node.name, ast.get_docstring(node), str(methods), str(static_methods)))

        # Commit changes and close the connection
        conn.commit()
        conn.close()
        
        return str(db_path)
        
    except Exception as e:
        return trace_exception(e)

def create_project_database_function(project_path, llm):
    return {
        "function_name": "create_project_database",
        "function": partial(create_project_database,project_path=project_path, llm=llm),
        "function_description": "Creates a database containing structured information about a Python project.",
        "function_parameters": []
    }



# Lollms function call definition file
from functools import partial
from typing import List, Dict
from lollms.utilities import PackageManager
from ascii_colors import trace_exception
from pathlib import Path
import sqlite3

# Ensure required packages are installed
if not PackageManager.check_package_installed("sqlite3"):
    PackageManager.install_package("sqlite3")

def retrieve_information_for_task(project_path: str, task_description: str, llm: APScript) -> Union[str, Dict[str, str]]:
    """
    Retrieves information from the database to perform a task given by the user.
    
    Args:
        project_path (str): The path to the project directory.
        task_description (str): The description of the task to perform.
        llm (APScript): The language model instance for generating SQL queries.
    
    Returns:
        Union[str, Dict[str, str]]: A string containing relevant information or an error message.
    """
    try:
        db_path = Path(project_path) / "project_info.db"
        
        # Validate the database path
        if not db_path.exists() or not db_path.is_file():
            return "Invalid database path."

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Retrieve the list of classes and their descriptions
        cursor.execute("SELECT name, docstring FROM classes")
        classes = cursor.fetchall()

        # Format the classes into a string
        classes_text = "\n".join([f"Class: {cls[0]}, Description: {cls[1]}" for cls in classes])

        # Ask the LLM which classes are needed for the task
        prompt = f"{llm.personality.config.start_header_id_template}{llm.personality.config.system_message_template}{llm.personality.config.end_header_id_template}" \
                 f"Given the following list of classes and their descriptions:\n" \
                 f"{classes_text}\n\n" \
                 f"Task description: {task_description}\n\n" \
                 f"{llm.personality.config.start_header_id_template}instructions{llm.personality.config.end_header_id_template}" \
                 f"Which classes are needed to perform the task? List the class names.\n" \
                 f"Answer in form of a json list inside a json markdown tag.\n" \
                 f"{llm.personality.config.start_header_id_template}assistant{llm.personality.config.end_header_id_template}"

        needed_classes = llm.fast_gen(prompt, callback=llm.sink).strip()
        needed_classes = llm.extract_code_blocks(needed_classes)
        if len(needed_classes)>0:
            needed_classes = json.loads(needed_classes[0]["content"])
            # Retrieve the relevant information for the needed classes
            class_info = {}
            for class_name in needed_classes:
                cursor.execute("SELECT * FROM classes WHERE name = ?", (class_name,))
                class_info[class_name] = cursor.fetchone()

            # Retrieve the project description and structure
            cursor.execute("SELECT name, description FROM project_info")
            project_info = cursor.fetchone()

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()

            conn.close()

            # Format the results into a string
            result_text = f"Project Name: {project_info[0]}\nProject Description: {project_info[1]}\n\n"
            result_text += "Project Structure:\n" + "\n".join([table[0] for table in tables]) + "\n\n"
            result_text += "Needed Classes Information:\n"
            for class_name, info in class_info.items():
                result_text += f"Class: {class_name}\n"
                result_text += f"Description: {info[2]}\n"
                result_text += f"Methods: {info[4]}\n"
                result_text += f"Static Methods: {info[5]}\n\n"

            return result_text.strip()
        else:
            return "Failed to ask the llm"        
    except Exception as e:
        return str(e)
    
def retrieve_information_for_task_function(project_path, llm):
    return {
        "function_name": "retrieve_information_for_task",
        "function": partial(retrieve_information_for_task, project_path=project_path, llm=llm),
        "function_description": "Retrieves information from the database to perform a task given by the user.",
        "function_parameters": [
            {"name": "task_description", "type": "str", "description":"a description of "}
        ]
    }
