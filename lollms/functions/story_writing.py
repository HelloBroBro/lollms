# Lollms function call definition file

# Import necessary modules
from functools import partial
from lollms.utilities import PackageManager
from ascii_colors import trace_exception

# Import typing elements
from typing import Any

# Import necessary libraries for file handling
from pathlib import Path
# Import typing elements
from typing import Any, List, Dict

# Import necessary libraries for file handling
from pathlib import Path
import json

# Import  markdown2latex
from lollms.functions.markdown2latex import markdown_file_to_latex
from lollms.functions.file_manipulation import change_file_extension

# Define the core functions
def start_writing_story(prompt_ideas: str, llm: Any, story_file_path: str, build_latex:bool=False) -> str:
    discussion_prompt_separator = llm.config.discussion_prompt_separator
    start_header_id_template    = llm.config.start_header_id_template
    end_header_id_template      = llm.config.end_header_id_template
    separator_template          = llm.config.separator_template
    system_message_template     = llm.config.system_message_template        

    try:
        llm.step_start("Building the story architecture")
        # Step 1: Generate the story plan in JSON format
        plan_prompt = "\n".join([
            f"{start_header_id_template}{system_message_template}{end_header_id_template}",
            f"You are story architect. Your task is to build a story architecture from the prompt ideas. Your output must strictly be in the form of a json text inside a json markdown tag in this form:",
            "```json",
            "{\n"
            "\"title\":\"The title of the story\",\n"
            "\"sections\":[\n"
            "{\n"
            "\"section_name\": \"The name of the section\",\n"
            "\"section_description\": \"A short description of the section\"\n"
            "}, ...\n"
            "]\n"
            "}\n"
            "```",
            f"{start_header_id_template}{prompt_ideas}{end_header_id_template}",
            f"{prompt_ideas}\n\n"
            f"{start_header_id_template}story_architect{end_header_id_template}"
            ]
        )
        plan_response = llm.fast_gen(plan_prompt).strip()
        llm.step_end("Building the story architecture")
        llm.chunk("\n")
        # Extract JSON code block from the response
        code_blocks = llm.extract_code_blocks(plan_response)
        if not code_blocks:
            return "Failed to extract JSON code block for the story plan."

        plan_json_str = code_blocks[0]['content']
        story_plan = json.loads(plan_json_str)

        # Step 2: Write the story section by section
        story_path = Path(story_file_path)
        final_story_content = ""

        for section in story_plan["sections"]:
            llm.step_start(f"Building section: {section["section_name"]}")

            section_name = section["section_name"]
            section_description = section["section_description"]
            
            new_section = write_story_section(
                llm=llm,
                story_file_path=story_file_path,
                story_plan=story_plan,
                current_section=section_description,
                prompt_ideas=prompt_ideas
            )
            
            final_story_content += f"\n## {section_name}\n\n{new_section}\n"
            llm.step_end(f"Building section: {section["section_name"]}")

        if build_latex:
            llm.step_start("Building latex file")
            import subprocess
            latex = markdown_file_to_latex(story_file_path)
            tex_file = Path(change_file_extension(story_file_path,".tex"))
            tex_file.write_text(latex)
            # Determine the pdflatex command based on the provided or default path
            if llm.config.pdf_latex_path:
                pdflatex_command = llm.config.pdf_latex_path
            else:
                pdflatex_command = 'pdflatex'
            # Set the execution path to the folder containing the tmp_file
            execution_path = tex_file.parent

            # Execute the Python code in a temporary file.
            process = subprocess.Popen(
                [pdflatex_command, "-interaction=nonstopmode", str(tex_file)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=execution_path
            )
            process.wait()
            llm.step_end("Building latex file")


        return final_story_content.strip()
    except Exception as e:
        return trace_exception(e)

# Define the metadata functions
def start_writing_story_function(llm, story_file_path, build_latex:bool=False):
    return {
        "function_name": "start_writing_story",
        "function": partial(start_writing_story, llm=llm, story_file_path=story_file_path, build_latex=build_latex),
        "function_description": "Starts writing a story based on the provided prompt ideas, generating a plan in JSON format, and writing the story section by section.",
        "function_parameters": [
            {"name": "prompt_ideas", "type": "str"}
        ]
    }


# Define the core function
def write_story_section(prompt_ideas: str, llm: Any, story_file_path: str, story_plan: dict, current_section: str) -> str:
    discussion_prompt_separator = llm.config.discussion_prompt_separator
    start_header_id_template    = llm.config.start_header_id_template
    end_header_id_template      = llm.config.end_header_id_template
    separator_template          = llm.config.separator_template
    system_message_template     = llm.config.system_message_template        
    try:
        story_path = Path(story_file_path)
        
        # Check if the story file exists
        if not story_path.exists():
            # Generate the title of the story using the LLM's fast_gen function
            story_title = story_plan["title"]

            # Initialize the story with the title and the first section
            new_section = f"# {story_title}\n\n"
            new_section += f"## {current_section}\n\n"

            prompt = "\n".join([
                f"{start_header_id_template}{system_message_template}{end_header_id_template}",
                f"You are story section writer. Your task is to build the content of a single section of a story from informations about the story.",
                "Your output must strictly contain only the section content with no comments or suggestions.",
                f"{start_header_id_template}General idea{end_header_id_template}",
                f"{prompt_ideas}\n\n"
                f"{start_header_id_template}Story plan{end_header_id_template}",
                f"{story_plan}",
                f"{start_header_id_template}Section to be written{end_header_id_template}",
                f"{current_section}",
                f"{start_header_id_template}story_section_writer{end_header_id_template}"
                ]
            )
            new_section += llm.fast_gen(prompt)

            # Write the new section to the story file
            story_path.write_text(new_section)

            return new_section

        # Read the content of the story file
        story_content = story_path.read_text()

        # Summarize the current content of the story
        story_summary = llm.summerize_text(story_content)

        # Generate the current section using the LLM's fast_gen function
        prompt = "\n".join([
            f"{start_header_id_template}{system_message_template}{end_header_id_template}",
            f"You are story section writer. Your task is to build the content of a single section of a story from informations about the story.",
            "Your output must strictly contain only the section content with no comments or suggestions.",
            f"{start_header_id_template}General idea{end_header_id_template}",
            f"{prompt_ideas}\n\n"
            f"{start_header_id_template}Story plan{end_header_id_template}",
            f"{story_plan}",
            f"{start_header_id_template}Section to be written{end_header_id_template}",
            f"{current_section}",
            f"{start_header_id_template}Story summary up to the current section{end_header_id_template}",
            f"{story_summary}",
            f"{start_header_id_template}story_section_writer{end_header_id_template}"
            ]
        )
        new_section = f"## {current_section}\n\n"
        new_section += llm.fast_gen(prompt).strip()

        # Append the new section to the story file
        story_path.write_text(story_content + "\n" + new_section)

        return new_section
    except Exception as e:
        return trace_exception(e)

# Define the metadata function
def write_story_section_function(llm, story_file_path, story_plan, current_section):
    return {
        "function_name": "write_story_section", # The function name in string
        "function": partial(write_story_section, llm=llm, story_file_path=story_file_path, story_plan=story_plan, current_section=current_section), # The function to be called
        "function_description": "Writes a new section of a story based on the provided plan and current content of the story file. If the story file does not exist, it creates a new story with a generated title based on user ideas.", # Change this with the description
        "function_parameters": [
            {"name": "prompt_ideas", "type": "str", "description": "Ideas for the story to be written"}
        ] # The set of parameters          
    }
