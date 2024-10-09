from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from base64 import b64encode
import io
from PIL import Image
from fastapi import APIRouter
from lollms_webui import LOLLMSWebUI
from pydantic import BaseModel

from ascii_colors import trace_exception


router = APIRouter()
lollmsElfServer = LOLLMSWebUI.get_instance()

class ImageRequest(BaseModel):
    prompt: str
    negative_prompt: Optional[str] = ""
    width: int = 512
    height: int = 512

class ImageResponse(BaseModel):
    image: str

@router.post("/generate_image", response_model=ImageResponse)
async def generate_image(request: ImageRequest):
    try:
        import uuid

        filename = f"remote_gen_{uuid.uuid4().hex[:8]}.png"
        output_path = lollmsElfServer.lollms_paths.personal_outputs_path/filename        
        # Call the build_image function
        result = build_image(
            request.prompt,
            request.negative_prompt,
            request.width,
            request.height,
            return_format="path",
            output_path=output_path
        )

        # Check if image generation was successful
        if result is None:
            raise HTTPException(status_code=500, detail="Image generation failed")

        # Open the image file
        with Image.open(result) as img:
            # Convert the image to RGB mode (in case it's RGBA)
            img = img.convert("RGB")
            
            # Save the image to a bytes buffer
            buf = io.BytesIO()
            img.save(buf, format="JPEG")
            
            # Encode the image as base64
            img_base64 = b64encode(buf.getvalue()).decode()

        # Return the base64 encoded image
        return ImageResponse(image=img_base64)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def build_image(prompt, negative_prompt, width, height, return_format="markdown", output_path =None):
    try:
        import uuid
        if output_path is None:
            filename = f"remote_gen_{uuid.uuid4().hex[:8]}.png"
            output_path = lollmsElfServer.lollms_paths.personal_outputs_path/filename

        if lollmsElfServer.tti is not None:
            file, infos = lollmsElfServer.tti.paint(
                prompt,
                negative_prompt,
                width=width,
                height=height,
                output_path=output_path
            )

        file = str(file)

        if return_format == "path":
            return file
        else:
            return None  # Handle other return formats if needed
    except Exception as ex:
        # Log the exception
        trace_exception(ex)
        print(f"Error in build_image: {str(ex)}")
        return None
