import pipmaster as pm
import pkg_resources
# Check and install required packages
required_packages = [
    ["torch","","https://download.pytorch.org/whl/cu121"],
    ["diffusers","0.30.1",None],
    ["transformers","4.44.2",None],
    ["accelerate","0.33.0",None],
    ["imageio-ffmpeg","0.5.1",None]
]

for package, min_version, index_url in required_packages:
    if not pm.is_installed(package):
        pm.install_or_update(package, index_url)
    else:
        if min_version:
            if pkg_resources.parse_version(pm.get_installed_version(package))< pkg_resources.parse_version(min_version):
                pm.install_or_update(package, index_url)

import torch
from diffusers import CogVideoXPipeline
from diffusers.utils import export_to_video
from typing import List, Optional
from abc import ABC, abstractmethod
from lollms.ttv import LollmsTTV


class CogVideoX(LollmsTTV):
    def __init__(self, model_name: str = "THUDM/CogVideoX-5b", torch_dtype=torch.bfloat16):
        self.pipe = CogVideoXPipeline.from_pretrained(
            model_name,
            torch_dtype=torch_dtype
        )
        self.pipe.enable_model_cpu_offload()
        self.pipe.vae.enable_tiling()

    def generate_video(self, prompt: str, num_frames: int = 49, fps: int = 8, 
                       num_inference_steps: int = 50, guidance_scale: float = 6.0, 
                       seed: Optional[int] = None) -> str:
        if seed is not None:
            generator = torch.Generator(device="cuda").manual_seed(seed)
        else:
            generator = None

        video = self.pipe(
            prompt=prompt,
            num_videos_per_prompt=1,
            num_inference_steps=num_inference_steps,
            num_frames=num_frames,
            guidance_scale=guidance_scale,
            generator=generator,
        ).frames[0]

        output_path = "output.mp4"
        export_to_video(video, output_path, fps=fps)
        return output_path

# Usage example:
if __name__ == "__main__":
    cogvideox = CogVideoX()
    prompt = "A panda, dressed in a small, red jacket and a tiny hat, sits on a wooden stool in a serene bamboo forest. The panda's fluffy paws strum a miniature acoustic guitar, producing soft, melodic tunes."
    output_video = cogvideox.generate_video(prompt)
    print(f"Video generated and saved to: {output_video}")