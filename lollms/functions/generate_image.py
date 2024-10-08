from lollms.utilities import discussion_path_to_url
from lollms.client_session import Client
from lollms.personality import APScript
from ascii_colors import trace_exception
from functools import partial
from lollms.functions.prompting.image_gen_prompts import get_image_gen_prompt, get_random_image_gen_prompt


def build_negative_prompt(image_generation_prompt, llm):
    start_header_id_template    = llm.config.start_header_id_template
    end_header_id_template      = llm.config.end_header_id_template
    system_message_template     = llm.config.system_message_template        

    return "\n".join([
                    f"{start_header_id_template}{system_message_template}{end_header_id_template}",
                    f"{llm.config.negative_prompt_generation_prompt}",
                    f"{start_header_id_template}image_generation_prompt{end_header_id_template}",
                    f"{image_generation_prompt}",
                    f"{start_header_id_template}negative_prompt{end_header_id_template}",
                ])    

def build_image(prompt, negative_prompt, width, height, processor:APScript, client:Client, return_format="markdown"):
    try:
        if processor.personality.app.tti!=None:
            processor.step_start("Painting")
            file, infos = processor.personality.app.tti.paint(
                            prompt,
                            negative_prompt,
                            width = width,
                            height = height,
                            output_path=client.discussion.discussion_folder
                        )
            processor.step_end("Painting")
            
        file = str(file)
        escaped_url =  discussion_path_to_url(file)

        if return_format == "markdown":
            return f'\nRespond with this link in markdown format:\n![]({escaped_url})'
        elif return_format == "url":
            return escaped_url
        elif return_format == "path":
            return file
        elif return_format == "url_and_path":
            return {"url": escaped_url, "path": file}
        else:
            return f"Invalid return_format: {return_format}. Supported formats are 'markdown', 'url', 'path', and 'url_and_path'."
    except Exception as ex:
        trace_exception(ex)
        if return_format == "markdown":
            return f"\nCouldn't generate image. Make sure {processor.personality.config.active_tti_service} service is installed"
        elif return_format == "url":
            return None
        elif return_format == "path":
            return None
        elif return_format == "url_and_path":
            return {"url": None, "path": None, "error":ex}
        else:
            return f"Couldn't generate image. Make sure {processor.personality.config.active_tti_service} service is installed"


def build_image_from_simple_prompt(prompt, processor:APScript, client:Client, width=1024, height=1024, examples_extraction_mathod="random", number_of_examples_to_recover=3, production_type="artwork", max_generation_prompt_size=1024):
    examples = ""
    expmls = []
    if examples_extraction_mathod=="random":
        expmls = get_random_image_gen_prompt(number_of_examples_to_recover)
    elif examples_extraction_mathod=="rag_based":
        expmls = get_image_gen_prompt(prompt, number_of_examples_to_recover)
        
    for i,expml in enumerate(expmls):
        examples += f"example {i}:"+expml+"\n"

    prompt = processor.build_prompt([
                    processor.system_full_header,
                    f"Act as artbot, the art prompt generation AI.",
                    "Use the user prompt to come up with an image generation prompt without referring to it.",
                    f"Be precise and describe the style as well as the {production_type} description details.", #conditionning
                    "Do not explain the prompt, just answer with the prompt in the right prompting style.",
                    processor.system_custom_header("user prompt"),
                    prompt,
                    processor.system_custom_header("Production type") + f"{production_type}",
                    processor.system_custom_header("Instruction") + f"Use the following as examples and follow their format to build the special prompt." if examples!="" else "",
                    processor.system_custom_header("Prompt examples") if examples!="" else "",
                    processor.system_custom_header("Examples") + f"{examples}",
                    processor.system_custom_header("Prompt"),                    
    ],2)
    positive_prompt = processor.generate(prompt, max_generation_prompt_size, callback=processor.sink).strip().replace("</s>","").replace("<s>","")
    return build_image(positive_prompt, "", width, height, processor, client, "url_and_path")


def build_image_function(processor, client):
    if processor.config.use_negative_prompt:
        if processor.config.use_ai_generated_negative_prompt:
            return {
                    "function_name": "build_image",
                    "function": partial(build_image, processor=processor, client=client),
                    "function_description": "Builds and shows an image from a prompt and width and height parameters. A square 1024x1024, a portrait woudl be 1024x1820 or landscape 1820x1024. Width and height have to be divisible by 8.",
                    "function_parameters": [{"name": "prompt", "type": "str"}, {"name": "negative_prompt", "type": "str"}, {"name": "width", "type": "int"}, {"name": "height", "type": "int"}]                
                }
        else:
            return {
                    "function_name": "build_image",
                    "function": partial(build_image, processor=processor, client=client, negative_prompt=processor.config.default_negative_prompt),
                    "function_description": "Builds and shows an image from a prompt and width and height parameters. A square 1024x1024, a portrait woudl be 1024x1820 or landscape 1820x1024. Width and height have to be divisible by 8.",
                    "function_parameters": [{"name": "prompt", "type": "str"}, {"name": "width", "type": "int"}, {"name": "height", "type": "int"}]                
                }
    else:
        return {
                "function_name": "build_image",
                "function": partial(build_image, processor=processor, client=client, negative_prompt=""),
                "function_description": "Builds and shows an image from a prompt and width and height parameters. A square 1024x1024, a portrait woudl be 1024x1820 or landscape 1820x1024. Width and height have to be divisible by 8.",
                "function_parameters": [{"name": "prompt", "type": "str"}, {"name": "width", "type": "int"}, {"name": "height", "type": "int"}]                
            }



