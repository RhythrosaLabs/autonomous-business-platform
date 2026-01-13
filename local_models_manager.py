# local_models_manager.py
import os
from pathlib import Path
import subprocess
import time
import sys

class LocalModelsManager:
    """Manages local AI model downloads and inference"""

    def __init__(self):
        self.models_dir = Path.home() / ".pod_wizard_local_models"
        self.flux_model_path = self.models_dir / "flux-schnell"
        self.text_model_path = self.models_dir / "deepseek-coder-1.3b"

    def get_installation_info(self) -> dict:
        """Get info about required downloads"""
        return {
            "total_size_gb": 28.5,
            "models": [
                {
                    "name": "FLUX.1-schnell (Image Generation)",
                    "size_gb": 23.8,
                    "description": "Fast, high-quality image generation",
                    "source": "black-forest-labs/FLUX.1-schnell"
                },
                {
                    "name": "DeepSeek-Coder-1.3B (Text Enhancement)",
                    "size_gb": 2.7,
                    "description": "Prompt enhancement and SEO optimization",
                    "source": "deepseek-ai/deepseek-coder-1.3b-instruct"
                },
                {
                    "name": "Dependencies (diffusers, transformers, torch)",
                    "size_gb": 2.0,
                    "description": "Required Python libraries"
                }
            ],
            "estimated_time": "20-40 minutes (depending on internet speed)",
            "disk_space_needed": "30 GB free recommended"
        }

    def is_installed(self) -> bool:
        """Check if models are already installed"""
        return (self.flux_model_path.exists() and
                self.text_model_path.exists() and
                self._check_dependencies())

    def _check_dependencies(self) -> bool:
        """Check if required packages are installed"""
        try:
            import torch
            import diffusers
            import transformers
            return True
        except ImportError:
            return False

    def install_models(self, progress_callback=None) -> bool:
        """Install models and dependencies"""
        try:
            # Create directory
            self.models_dir.mkdir(parents=True, exist_ok=True)

            if progress_callback:
                progress_callback("Installing Python dependencies...")

            # Install required packages
            packages = [
                "torch",
                "torchvision",
                "diffusers",
                "transformers",
                "accelerate",
                "safetensors",
                "sentencepiece"
            ]

            for pkg in packages:
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install", "-q", pkg
                ])

            # Now import after installation
            from diffusers import FluxPipeline
            from transformers import AutoTokenizer, AutoModelForCausalLM

            # Download FLUX model
            if progress_callback:
                progress_callback("Downloading FLUX model (this will take 15-30 minutes)...")

            flux_pipe = FluxPipeline.from_pretrained(
                "black-forest-labs/FLUX.1-schnell",
                torch_dtype=torch.bfloat16,
                cache_dir=str(self.models_dir)
            )
            flux_pipe.save_pretrained(str(self.flux_model_path))
            del flux_pipe

            # Download DeepSeek model
            if progress_callback:
                progress_callback("Downloading DeepSeek model (5-10 minutes)...")

            tokenizer = AutoTokenizer.from_pretrained(
                "deepseek-ai/deepseek-coder-1.3b-instruct",
                cache_dir=str(self.models_dir)
            )
            model = AutoModelForCausalLM.from_pretrained(
                "deepseek-ai/deepseek-coder-1.3b-instruct",
                torch_dtype=torch.float16,
                cache_dir=str(self.models_dir)
            )

            tokenizer.save_pretrained(str(self.text_model_path))
            model.save_pretrained(str(self.text_model_path))

            return True

        except Exception as e:
            if progress_callback:
                progress_callback(f"Installation failed: {str(e)}")
            return False

    def generate_image_local(self, prompt: str, width: int = 1024,
                             height: int = 1024) -> str:
        """Generate image using local FLUX model"""
        try:
            from diffusers import FluxPipeline
            import torch

            # Load pipeline
            pipe = FluxPipeline.from_pretrained(
                str(self.flux_model_path),
                torch_dtype=torch.bfloat16
            )

            # Move to GPU if available
            device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
            pipe = pipe.to(device)

            # Generate image
            image = pipe(
                prompt=prompt,
                width=width,
                height=height,
                num_inference_steps=4,  # Schnell is fast, only needs 4 steps
                guidance_scale=0.0  # Schnell doesn't use guidance
            ).images[0]

            # Save to temp file
            temp_path = self.models_dir / f"temp_{int(time.time())}.png"
            image.save(temp_path)

            return f"file://{temp_path}"

        except Exception as e:
            raise Exception(f"Local image generation failed: {str(e)}")

    def enhance_prompt_local(self, prompt: str) -> str:
        """Enhance prompt using local text model"""
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            import torch

            tokenizer = AutoTokenizer.from_pretrained(str(self.text_model_path))
            model = AutoModelForCausalLM.from_pretrained(
                str(self.text_model_path),
                torch_dtype=torch.float16
            )

            device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
            model = model.to(device)

            # Create enhancement prompt
            enhancement_query = f"Enhance this image generation prompt to be more detailed and artistic: {prompt}"

            inputs = tokenizer(enhancement_query, return_tensors="pt").to(device)
            outputs = model.generate(
                **inputs,
                max_new_tokens=100,
                temperature=0.7,
                do_sample=True
            )

            enhanced = tokenizer.decode(outputs[0], skip_special_tokens=True)

            return enhanced.split(":")[-1].strip() if ":" in enhanced else prompt

        except Exception as e:
            return prompt  # Fallback to original
