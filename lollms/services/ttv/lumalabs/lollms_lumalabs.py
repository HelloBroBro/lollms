import requests
from typing import Optional, Dict
from lollms.ttv import LollmsTTV

class LollmsLumaLabs(LollmsTTV):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.lumalabs.ai/dream-machine/v1/generations"
        self.headers = {
            "accept": "application/json",
            "authorization": f"Bearer {self.api_key}",
            "content-type": "application/json"
        }

    def generate_video(self, prompt: str, aspect_ratio: str = "16:9",                  
                       loop: bool = False, num_frames: int = 60, 
                       fps: int = 30, keyframes: Optional[Dict] = None)-> str:
        payload = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "loop": loop
        }
        
        if keyframes:
            payload["keyframes"] = keyframes

        response = requests.post(self.base_url, headers=self.headers, json=payload)
        response.raise_for_status()
        
        generation_data = response.json()
        video_url = generation_data['assets']['video']
        
        # Download the video
        video_response = requests.get(video_url)
        video_response.raise_for_status()
        
        output_path = "output.mp4"
        with open(output_path, 'wb') as f:
            f.write(video_response.content)
        
        return output_path

    def extend_video(self, prompt: str, generation_id: str, reverse: bool = False) -> str:
        keyframes = {
            "frame0" if not reverse else "frame1": {
                "type": "generation",
                "id": generation_id
            }
        }
        return self.generate_video(prompt, keyframes=keyframes)

    def image_to_video(self, prompt: str, image_url: str, is_end_frame: bool = False) -> str:
        keyframes = {
            "frame0" if not is_end_frame else "frame1": {
                "type": "image",
                "url": image_url
            }
        }
        return self.generate_video(prompt, keyframes=keyframes)

# Usage example:
if __name__ == "__main__":
    luma_video = LumaLabsVideo("your-api-key-here")
    prompt = "A panda, dressed in a small, red jacket and a tiny hat, sits on a wooden stool in a serene bamboo forest. The panda's fluffy paws strum a miniature acoustic guitar, producing soft, melodic tunes."
    output_video = luma_video.generate_video(prompt)
    print(f"Video generated and saved to: {output_video}")