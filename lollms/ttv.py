from abc import ABC, abstractmethod
from typing import List, Optional

class LollmsTTV(ABC):
    @abstractmethod
    def generate_video(self, prompt: str, num_frames: int = 49, fps: int = 8, 
                       num_inference_steps: int = 50, guidance_scale: float = 6.0, 
                       seed: Optional[int] = None) -> str:
        pass