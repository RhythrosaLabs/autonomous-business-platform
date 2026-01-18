"""
ComfyUI Model Manager

Automatically detects, downloads, and manages models required for ComfyUI workflows.
Supports:
- Checkpoints (SD 1.5, SDXL, Flux, etc.)
- LoRAs
- VAEs
- ControlNets
- Upscalers
- IP-Adapters
- Custom nodes

Downloads from:
- HuggingFace
- Civitai
- Direct URLs
"""

import os
from platform_integrations import tracked_replicate_run
import json
import hashlib
import logging
import requests
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class ModelType(Enum):
    """Types of models used in ComfyUI"""
    CHECKPOINT = "checkpoints"
    LORA = "loras"
    VAE = "vae"
    CONTROLNET = "controlnet"
    UPSCALER = "upscale_models"
    CLIP = "clip"
    CLIP_VISION = "clip_vision"
    IPADAPTER = "ipadapter"
    EMBEDDINGS = "embeddings"
    HYPERNETWORK = "hypernetworks"
    UNET = "unet"
    CUSTOM_NODE = "custom_nodes"
    UNKNOWN = "unknown"


@dataclass
class ModelInfo:
    """Information about a required model"""
    name: str
    type: ModelType
    filename: str
    source_url: Optional[str] = None
    huggingface_repo: Optional[str] = None
    civitai_id: Optional[str] = None
    sha256: Optional[str] = None
    size_bytes: Optional[int] = None
    description: Optional[str] = None
    required: bool = True
    alternatives: List[str] = field(default_factory=list)


@dataclass
class DownloadProgress:
    """Track download progress"""
    model_name: str
    total_bytes: int = 0
    downloaded_bytes: int = 0
    status: str = "pending"  # pending, downloading, complete, error
    error_message: Optional[str] = None
    
    @property
    def progress_percent(self) -> float:
        if self.total_bytes == 0:
            return 0
        return (self.downloaded_bytes / self.total_bytes) * 100


# Known model mappings - maps common model names to download sources
KNOWN_MODELS = {
    # Checkpoints
    "v1-5-pruned-emaonly.safetensors": {
        "type": ModelType.CHECKPOINT,
        "huggingface": "runwayml/stable-diffusion-v1-5",
        "filename": "v1-5-pruned-emaonly.safetensors",
        "description": "Stable Diffusion 1.5 base model"
    },
    "v1-5-pruned.safetensors": {
        "type": ModelType.CHECKPOINT,
        "huggingface": "runwayml/stable-diffusion-v1-5",
        "filename": "v1-5-pruned.safetensors"
    },
    "sd_xl_base_1.0.safetensors": {
        "type": ModelType.CHECKPOINT,
        "huggingface": "stabilityai/stable-diffusion-xl-base-1.0",
        "filename": "sd_xl_base_1.0.safetensors",
        "description": "SDXL Base 1.0"
    },
    "sd_xl_refiner_1.0.safetensors": {
        "type": ModelType.CHECKPOINT,
        "huggingface": "stabilityai/stable-diffusion-xl-refiner-1.0",
        "filename": "sd_xl_refiner_1.0.safetensors",
        "description": "SDXL Refiner 1.0"
    },
    "flux1-dev.safetensors": {
        "type": ModelType.CHECKPOINT,
        "huggingface": "black-forest-labs/FLUX.1-dev",
        "filename": "flux1-dev.safetensors",
        "description": "FLUX.1 Dev model"
    },
    "flux1-schnell.safetensors": {
        "type": ModelType.CHECKPOINT,
        "huggingface": "black-forest-labs/FLUX.1-schnell",
        "filename": "flux1-schnell.safetensors",
        "description": "FLUX.1 Schnell (fast)"
    },
    
    # VAEs
    "vae-ft-mse-840000-ema-pruned.safetensors": {
        "type": ModelType.VAE,
        "huggingface": "stabilityai/sd-vae-ft-mse-original",
        "filename": "vae-ft-mse-840000-ema-pruned.safetensors"
    },
    "sdxl_vae.safetensors": {
        "type": ModelType.VAE,
        "huggingface": "stabilityai/sdxl-vae",
        "filename": "sdxl_vae.safetensors"
    },
    
    # ControlNets
    "control_v11p_sd15_canny.safetensors": {
        "type": ModelType.CONTROLNET,
        "huggingface": "lllyasviel/ControlNet-v1-1",
        "filename": "control_v11p_sd15_canny.pth"
    },
    "control_v11p_sd15_openpose.safetensors": {
        "type": ModelType.CONTROLNET,
        "huggingface": "lllyasviel/ControlNet-v1-1",
        "filename": "control_v11p_sd15_openpose.pth"
    },
    "control_v11f1p_sd15_depth.safetensors": {
        "type": ModelType.CONTROLNET,
        "huggingface": "lllyasviel/ControlNet-v1-1",
        "filename": "control_v11f1p_sd15_depth.pth"
    },
    "diffusers_xl_canny_full.safetensors": {
        "type": ModelType.CONTROLNET,
        "huggingface": "diffusers/controlnet-canny-sdxl-1.0",
        "filename": "diffusion_pytorch_model.safetensors"
    },
    
    # Upscalers
    "RealESRGAN_x4plus.pth": {
        "type": ModelType.UPSCALER,
        "url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
        "filename": "RealESRGAN_x4plus.pth"
    },
    "4x-UltraSharp.pth": {
        "type": ModelType.UPSCALER,
        "url": "https://huggingface.co/Kim2091/UltraSharp/resolve/main/4x-UltraSharp.pth",
        "filename": "4x-UltraSharp.pth"
    },
    
    # CLIP
    "clip_l.safetensors": {
        "type": ModelType.CLIP,
        "huggingface": "openai/clip-vit-large-patch14",
        "filename": "model.safetensors"
    },
    "t5xxl_fp16.safetensors": {
        "type": ModelType.CLIP,
        "huggingface": "google/t5-v1_1-xxl",
        "filename": "model.safetensors"
    },
    
    # IP-Adapters
    "ip-adapter_sd15.safetensors": {
        "type": ModelType.IPADAPTER,
        "huggingface": "h94/IP-Adapter",
        "filename": "models/ip-adapter_sd15.safetensors"
    },
    "ip-adapter-plus_sd15.safetensors": {
        "type": ModelType.IPADAPTER,
        "huggingface": "h94/IP-Adapter",
        "filename": "models/ip-adapter-plus_sd15.safetensors"
    },
    "ip-adapter_sdxl.safetensors": {
        "type": ModelType.IPADAPTER,
        "huggingface": "h94/IP-Adapter",
        "filename": "sdxl_models/ip-adapter_sdxl.safetensors"
    },
}

# Custom nodes that may be required
KNOWN_CUSTOM_NODES = {
    "ComfyUI-Manager": {
        "repo": "https://github.com/ltdrdata/ComfyUI-Manager",
        "description": "ComfyUI Manager for installing custom nodes"
    },
    "ComfyUI-Impact-Pack": {
        "repo": "https://github.com/ltdrdata/ComfyUI-Impact-Pack",
        "description": "Various impact/detection nodes"
    },
    "ComfyUI_IPAdapter_plus": {
        "repo": "https://github.com/cubiq/ComfyUI_IPAdapter_plus",
        "description": "IP-Adapter nodes"
    },
    "ComfyUI-AnimateDiff-Evolved": {
        "repo": "https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved",
        "description": "AnimateDiff video generation"
    },
    "ComfyUI_essentials": {
        "repo": "https://github.com/cubiq/ComfyUI_essentials",
        "description": "Essential utility nodes"
    },
    "ComfyUI-KJNodes": {
        "repo": "https://github.com/kijai/ComfyUI-KJNodes",
        "description": "Various utility nodes"
    },
    "ComfyUI-VideoHelperSuite": {
        "repo": "https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite",
        "description": "Video loading and processing"
    },
    "rgthree-comfy": {
        "repo": "https://github.com/rgthree/rgthree-comfy",
        "description": "Power Lora Loader and other utilities"
    },
    "was-node-suite-comfyui": {
        "repo": "https://github.com/WASasquatch/was-node-suite-comfyui",
        "description": "WAS Node Suite - many utility nodes"
    },
    "ComfyUI-Advanced-ControlNet": {
        "repo": "https://github.com/Kosinkadink/ComfyUI-Advanced-ControlNet",
        "description": "Advanced ControlNet nodes"
    },
}


class ComfyUIModelManager:
    """
    Manages ComfyUI models - detection, download, and organization
    """
    
    def __init__(self, comfyui_path: Optional[str] = None, models_path: Optional[str] = None):
        """
        Initialize the model manager.
        
        Args:
            comfyui_path: Path to ComfyUI installation (for local execution)
            models_path: Path to store downloaded models (defaults to ./comfyui_models)
        """
        self.comfyui_path = comfyui_path or os.environ.get("COMFYUI_PATH")
        self.models_path = models_path or os.path.join(os.getcwd(), "comfyui_models")
        
        self.required_models: List[ModelInfo] = []
        self.required_custom_nodes: List[str] = []
        self.download_progress: Dict[str, DownloadProgress] = {}
        
        # HuggingFace token for gated models
        self.hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
        
        # Civitai API key
        self.civitai_api_key = os.environ.get("CIVITAI_API_KEY")
        
        # Create model directories
        self._create_model_directories()
    
    def _create_model_directories(self):
        """Create directory structure for models"""
        subdirs = [
            "checkpoints",
            "loras", 
            "vae",
            "controlnet",
            "upscale_models",
            "clip",
            "clip_vision",
            "ipadapter",
            "embeddings",
            "hypernetworks",
            "unet"
        ]
        
        for subdir in subdirs:
            path = os.path.join(self.models_path, subdir)
            os.makedirs(path, exist_ok=True)
    
    def analyze_workflow(self, workflow_json: Dict) -> Dict[str, Any]:
        """
        Analyze a ComfyUI workflow to detect required models and custom nodes.
        
        Returns dict with:
        - models: List of ModelInfo for required models
        - custom_nodes: List of required custom node packages
        - missing_models: Models that need to be downloaded
        - available_models: Models already present locally
        """
        self.required_models = []
        self.required_custom_nodes = []
        
        # Detect format and parse nodes
        if "nodes" in workflow_json and "links" in workflow_json:
            nodes = workflow_json.get("nodes", [])
            self._analyze_ui_format(nodes)
        else:
            self._analyze_api_format(workflow_json)
        
        # Check which models are already available
        available = []
        missing = []
        
        for model in self.required_models:
            if self._is_model_available(model):
                available.append(model)
            else:
                missing.append(model)
        
        return {
            "models": self.required_models,
            "custom_nodes": self.required_custom_nodes,
            "missing_models": missing,
            "available_models": available,
            "total_download_size": sum(m.size_bytes or 0 for m in missing),
            "summary": self._generate_summary(available, missing)
        }
    
    def _analyze_ui_format(self, nodes: List[Dict]):
        """Analyze UI format workflow nodes"""
        for node in nodes:
            node_type = node.get("type", "")
            widgets = node.get("widgets_values", [])
            
            # Detect custom nodes
            if "." in node_type or any(cn in node_type for cn in KNOWN_CUSTOM_NODES.keys()):
                self._detect_custom_node(node_type)
            
            # Check for model loaders
            if "CheckpointLoader" in node_type:
                if widgets:
                    model_name = widgets[0] if isinstance(widgets[0], str) else None
                    if model_name:
                        self._add_model(model_name, ModelType.CHECKPOINT)
            
            elif "LoraLoader" in node_type or "LoRALoader" in node_type:
                if widgets:
                    lora_name = widgets[0] if isinstance(widgets[0], str) else None
                    if lora_name:
                        self._add_model(lora_name, ModelType.LORA)
            
            elif "VAELoader" in node_type:
                if widgets:
                    vae_name = widgets[0] if isinstance(widgets[0], str) else None
                    if vae_name:
                        self._add_model(vae_name, ModelType.VAE)
            
            elif "ControlNetLoader" in node_type:
                if widgets:
                    cn_name = widgets[0] if isinstance(widgets[0], str) else None
                    if cn_name:
                        self._add_model(cn_name, ModelType.CONTROLNET)
            
            elif "UpscaleModelLoader" in node_type:
                if widgets:
                    upscaler_name = widgets[0] if isinstance(widgets[0], str) else None
                    if upscaler_name:
                        self._add_model(upscaler_name, ModelType.UPSCALER)
            
            elif "CLIPLoader" in node_type:
                if widgets:
                    clip_name = widgets[0] if isinstance(widgets[0], str) else None
                    if clip_name:
                        self._add_model(clip_name, ModelType.CLIP)
            
            elif "IPAdapter" in node_type:
                self._detect_custom_node("ComfyUI_IPAdapter_plus")
                if widgets:
                    for w in widgets:
                        if isinstance(w, str) and (".safetensors" in w or ".bin" in w):
                            self._add_model(w, ModelType.IPADAPTER)
            
            elif "AnimateDiff" in node_type:
                self._detect_custom_node("ComfyUI-AnimateDiff-Evolved")
            
            elif "Impact" in node_type or "SAM" in node_type:
                self._detect_custom_node("ComfyUI-Impact-Pack")
    
    def _analyze_api_format(self, workflow: Dict):
        """Analyze API format workflow"""
        for node_id, node_data in workflow.items():
            if not isinstance(node_data, dict):
                continue
            
            class_type = node_data.get("class_type", "")
            inputs = node_data.get("inputs", {})
            
            # Detect custom nodes
            if "." in class_type or any(cn in class_type for cn in KNOWN_CUSTOM_NODES.keys()):
                self._detect_custom_node(class_type)
            
            # Check for model references in inputs
            if "CheckpointLoader" in class_type:
                ckpt_name = inputs.get("ckpt_name")
                if ckpt_name:
                    self._add_model(ckpt_name, ModelType.CHECKPOINT)
            
            elif "LoraLoader" in class_type:
                lora_name = inputs.get("lora_name")
                if lora_name:
                    self._add_model(lora_name, ModelType.LORA)
            
            elif "VAELoader" in class_type:
                vae_name = inputs.get("vae_name")
                if vae_name:
                    self._add_model(vae_name, ModelType.VAE)
            
            elif "ControlNetLoader" in class_type:
                cn_name = inputs.get("control_net_name")
                if cn_name:
                    self._add_model(cn_name, ModelType.CONTROLNET)
            
            elif "UpscaleModelLoader" in class_type:
                model_name = inputs.get("model_name")
                if model_name:
                    self._add_model(model_name, ModelType.UPSCALER)
            
            elif "CLIPLoader" in class_type:
                clip_name = inputs.get("clip_name")
                if clip_name:
                    self._add_model(clip_name, ModelType.CLIP)
            
            elif "IPAdapter" in class_type:
                self._detect_custom_node("ComfyUI_IPAdapter_plus")
                for key, value in inputs.items():
                    if isinstance(value, str) and (".safetensors" in value or ".bin" in value):
                        self._add_model(value, ModelType.IPADAPTER)
    
    def _add_model(self, model_name: str, model_type: ModelType):
        """Add a model to the required list"""
        # Check if already added
        if any(m.name == model_name for m in self.required_models):
            return
        
        # Look up known model info
        known = KNOWN_MODELS.get(model_name, {})
        
        model_info = ModelInfo(
            name=model_name,
            type=known.get("type", model_type),
            filename=known.get("filename", model_name),
            huggingface_repo=known.get("huggingface"),
            source_url=known.get("url"),
            civitai_id=known.get("civitai_id"),
            description=known.get("description")
        )
        
        self.required_models.append(model_info)
    
    def _detect_custom_node(self, node_type: str):
        """Detect and add required custom nodes"""
        for node_name, info in KNOWN_CUSTOM_NODES.items():
            if node_name.lower() in node_type.lower():
                if node_name not in self.required_custom_nodes:
                    self.required_custom_nodes.append(node_name)
                return
    
    def _is_model_available(self, model: ModelInfo) -> bool:
        """Check if a model is already downloaded"""
        model_dir = os.path.join(self.models_path, model.type.value)
        model_path = os.path.join(model_dir, model.filename)
        
        if os.path.exists(model_path):
            return True
        
        # Also check ComfyUI installation path if available
        if self.comfyui_path:
            comfy_model_path = os.path.join(self.comfyui_path, "models", model.type.value, model.filename)
            if os.path.exists(comfy_model_path):
                return True
        
        return False
    
    def _generate_summary(self, available: List[ModelInfo], missing: List[ModelInfo]) -> List[str]:
        """Generate human-readable summary"""
        summary = []
        
        if available:
            summary.append(f"✅ {len(available)} models already available")
        
        if missing:
            summary.append(f"📥 {len(missing)} models need to be downloaded")
            
            by_type = {}
            for m in missing:
                type_name = m.type.value
                if type_name not in by_type:
                    by_type[type_name] = []
                by_type[type_name].append(m.name)
            
            for type_name, models in by_type.items():
                summary.append(f"  • {type_name}: {', '.join(models)}")
        
        if self.required_custom_nodes:
            summary.append(f"🔧 {len(self.required_custom_nodes)} custom nodes required:")
            for node in self.required_custom_nodes:
                summary.append(f"  • {node}")
        
        return summary
    
    def download_model(self, model: ModelInfo, progress_callback=None) -> bool:
        """
        Download a single model.
        
        Args:
            model: ModelInfo object
            progress_callback: Optional callback(model_name, downloaded, total)
        
        Returns:
            True if successful
        """
        self.download_progress[model.name] = DownloadProgress(
            model_name=model.name,
            status="downloading"
        )
        
        try:
            # Determine download URL
            url = None
            headers = {}
            
            if model.source_url:
                url = model.source_url
            
            elif model.huggingface_repo:
                # Construct HuggingFace URL
                url = f"https://huggingface.co/{model.huggingface_repo}/resolve/main/{model.filename}"
                if self.hf_token:
                    headers["Authorization"] = f"Bearer {self.hf_token}"
            
            elif model.civitai_id:
                # Civitai download URL
                url = f"https://civitai.com/api/download/models/{model.civitai_id}"
                if self.civitai_api_key:
                    headers["Authorization"] = f"Bearer {self.civitai_api_key}"
            
            if not url:
                logger.error(f"No download source for model: {model.name}")
                self.download_progress[model.name].status = "error"
                self.download_progress[model.name].error_message = "No download source available"
                return False
            
            # Download destination
            dest_dir = os.path.join(self.models_path, model.type.value)
            dest_path = os.path.join(dest_dir, model.filename)
            
            # Stream download
            response = requests.get(url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            self.download_progress[model.name].total_bytes = total_size
            
            downloaded = 0
            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        self.download_progress[model.name].downloaded_bytes = downloaded
                        
                        if progress_callback:
                            progress_callback(model.name, downloaded, total_size)
            
            self.download_progress[model.name].status = "complete"
            logger.info(f"Downloaded: {model.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error downloading {model.name}: {e}")
            self.download_progress[model.name].status = "error"
            self.download_progress[model.name].error_message = str(e)
            return False
    
    def download_all_missing(self, models: List[ModelInfo], max_concurrent: int = 2, 
                             progress_callback=None) -> Dict[str, bool]:
        """
        Download all missing models.
        
        Args:
            models: List of ModelInfo to download
            max_concurrent: Max concurrent downloads
            progress_callback: Optional callback(model_name, downloaded, total)
        
        Returns:
            Dict mapping model names to success status
        """
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            futures = {
                executor.submit(self.download_model, model, progress_callback): model
                for model in models
            }
            
            for future in as_completed(futures):
                model = futures[future]
                try:
                    results[model.name] = future.result()
                except Exception as e:
                    logger.error(f"Download failed for {model.name}: {e}")
                    results[model.name] = False
        
        return results
    
    def install_custom_node(self, node_name: str) -> bool:
        """Install a custom node via git clone"""
        if node_name not in KNOWN_CUSTOM_NODES:
            logger.error(f"Unknown custom node: {node_name}")
            return False
        
        if not self.comfyui_path:
            logger.error("ComfyUI path not set - cannot install custom nodes")
            return False
        
        custom_nodes_dir = os.path.join(self.comfyui_path, "custom_nodes")
        node_path = os.path.join(custom_nodes_dir, node_name)
        
        if os.path.exists(node_path):
            logger.info(f"Custom node already installed: {node_name}")
            return True
        
        try:
            import subprocess
            repo_url = KNOWN_CUSTOM_NODES[node_name]["repo"]
            
            result = subprocess.run(
                ["git", "clone", repo_url, node_path],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                # Install requirements if present
                req_file = os.path.join(node_path, "requirements.txt")
                if os.path.exists(req_file):
                    subprocess.run(
                        ["pip", "install", "-r", req_file],
                        capture_output=True,
                        timeout=300
                    )
                
                logger.info(f"Installed custom node: {node_name}")
                return True
            else:
                logger.error(f"Failed to clone {node_name}: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error installing custom node {node_name}: {e}")
            return False
    
    def get_model_path(self, model: ModelInfo) -> Optional[str]:
        """Get the local path to a model"""
        # Check our models directory
        local_path = os.path.join(self.models_path, model.type.value, model.filename)
        if os.path.exists(local_path):
            return local_path
        
        # Check ComfyUI directory
        if self.comfyui_path:
            comfy_path = os.path.join(self.comfyui_path, "models", model.type.value, model.filename)
            if os.path.exists(comfy_path):
                return comfy_path
        
        return None
    
    def get_extra_model_paths_config(self) -> str:
        """Generate extra_model_paths.yaml content for ComfyUI"""
        config = f"""
# Auto-generated by ComfyUI Model Manager
comfyui_models:
    base_path: {self.models_path}
    checkpoints: checkpoints
    loras: loras
    vae: vae
    controlnet: controlnet
    upscale_models: upscale_models
    clip: clip
    clip_vision: clip_vision
    ipadapter: ipadapter
    embeddings: embeddings
"""
        return config


class ComfyUIExecutor:
    """
    Execute ComfyUI workflows locally or remotely.
    """
    
    def __init__(self, model_manager: ComfyUIModelManager):
        self.model_manager = model_manager
        self.comfyui_url = os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188")
    
    def execute_locally(self, workflow_json: Dict, wait_for_result: bool = True) -> Dict:
        """
        Execute workflow on local ComfyUI instance.
        
        Requires ComfyUI to be running.
        """
        try:
            # Queue the prompt
            response = requests.post(
                f"{self.comfyui_url}/prompt",
                json={"prompt": workflow_json},
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            prompt_id = result.get("prompt_id")
            
            if not wait_for_result:
                return {"status": "queued", "prompt_id": prompt_id}
            
            # Poll for completion
            import time
            max_wait = 600  # 10 minutes
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                history_response = requests.get(
                    f"{self.comfyui_url}/history/{prompt_id}",
                    timeout=10
                )
                
                if history_response.status_code == 200:
                    history = history_response.json()
                    if prompt_id in history:
                        return {
                            "status": "complete",
                            "outputs": history[prompt_id].get("outputs", {})
                        }
                
                time.sleep(2)
            
            return {"status": "timeout", "prompt_id": prompt_id}
            
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Cannot connect to ComfyUI. Make sure it's running."
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def execute_remotely(self, workflow_json: Dict, provider: str = "replicate") -> Dict:
        """
        Execute workflow remotely via cloud provider.
        
        Converts ComfyUI workflow to equivalent Replicate API calls.
        """
        if provider == "replicate":
            return self._execute_via_replicate(workflow_json)
        else:
            return {"status": "error", "error": f"Unknown provider: {provider}"}
    
    def _execute_via_replicate(self, workflow_json: Dict) -> Dict:
        """Convert and run workflow via Replicate"""
        try:
            import replicate
            
            # Analyze workflow to determine what model/approach to use
            analysis = self.model_manager.analyze_workflow(workflow_json)
            
            # Extract prompts and settings from workflow
            prompts = self._extract_prompts(workflow_json)
            settings = self._extract_settings(workflow_json)
            
            # Determine which Replicate model to use based on the checkpoint
            checkpoint_models = [m for m in analysis["models"] if m.type == ModelType.CHECKPOINT]
            
            if any("flux" in m.name.lower() for m in checkpoint_models):
                # Use Flux model
                model_id = "black-forest-labs/flux-schnell"
                model_input = {
                    "prompt": prompts.get("positive", ""),
                    "num_outputs": 1,
                    "aspect_ratio": "1:1"
                }
            elif any("sdxl" in m.name.lower() for m in checkpoint_models):
                # Use SDXL model
                model_id = "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b"
                model_input = {
                    "prompt": prompts.get("positive", ""),
                    "negative_prompt": prompts.get("negative", ""),
                    "width": settings.get("width", 1024),
                    "height": settings.get("height", 1024),
                    "num_inference_steps": settings.get("steps", 30)
                }
            else:
                # Default to SD 1.5
                model_id = "stability-ai/stable-diffusion:ac732df83cea7fff18b8472768c88ad041fa750ff7682a21affe81863cbe77e4"
                model_input = {
                    "prompt": prompts.get("positive", ""),
                    "negative_prompt": prompts.get("negative", ""),
                    "width": settings.get("width", 512),
                    "height": settings.get("height", 512),
                    "num_inference_steps": settings.get("steps", 50)
                }
            
            # Run the model
            output = replicate.run(model_id, input=model_input)
            
            if isinstance(output, list):
                output_url = output[0]
            else:
                output_url = output
            
            return {
                "status": "complete",
                "outputs": {"images": [str(output_url)]},
                "model_used": model_id
            }
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def _extract_prompts(self, workflow_json: Dict) -> Dict[str, str]:
        """Extract positive and negative prompts from workflow"""
        prompts = {"positive": "", "negative": ""}
        
        nodes = workflow_json if not isinstance(workflow_json, dict) or "nodes" not in workflow_json else None
        
        if nodes is None:
            # API format
            for node_id, node_data in workflow_json.items():
                if not isinstance(node_data, dict):
                    continue
                
                class_type = node_data.get("class_type", "")
                inputs = node_data.get("inputs", {})
                
                if "CLIPTextEncode" in class_type:
                    text = inputs.get("text", "")
                    # Try to determine if positive or negative based on connections
                    if not prompts["positive"]:
                        prompts["positive"] = text
                    elif not prompts["negative"] and text != prompts["positive"]:
                        prompts["negative"] = text
        else:
            # UI format
            for node in workflow_json.get("nodes", []):
                if "CLIPTextEncode" in node.get("type", ""):
                    widgets = node.get("widgets_values", [])
                    if widgets:
                        text = widgets[0] if isinstance(widgets[0], str) else ""
                        if not prompts["positive"]:
                            prompts["positive"] = text
                        elif not prompts["negative"] and text != prompts["positive"]:
                            prompts["negative"] = text
        
        return prompts
    
    def _extract_settings(self, workflow_json: Dict) -> Dict:
        """Extract generation settings from workflow"""
        settings = {
            "width": 512,
            "height": 512,
            "steps": 20,
            "cfg": 7.0,
            "sampler": "euler"
        }
        
        if "nodes" not in workflow_json:
            # API format
            for node_id, node_data in workflow_json.items():
                if not isinstance(node_data, dict):
                    continue
                
                class_type = node_data.get("class_type", "")
                inputs = node_data.get("inputs", {})
                
                if "KSampler" in class_type:
                    settings["steps"] = inputs.get("steps", settings["steps"])
                    settings["cfg"] = inputs.get("cfg", settings["cfg"])
                    settings["sampler"] = inputs.get("sampler_name", settings["sampler"])
                
                elif "EmptyLatentImage" in class_type:
                    settings["width"] = inputs.get("width", settings["width"])
                    settings["height"] = inputs.get("height", settings["height"])
        
        return settings


def analyze_comfyui_models(workflow_json: Dict, models_path: str = None) -> Dict:
    """
    Convenience function to analyze a ComfyUI workflow for required models.
    
    Returns a dict with model requirements and download status.
    """
    manager = ComfyUIModelManager(models_path=models_path)
    return manager.analyze_workflow(workflow_json)


def setup_and_run_comfyui_workflow(
    workflow_json: Dict,
    auto_download: bool = True,
    execution_mode: str = "remote",  # "local" or "remote"
    models_path: str = None
) -> Dict:
    """
    Complete setup and execution of a ComfyUI workflow.
    
    1. Analyzes workflow for required models
    2. Downloads missing models (if auto_download=True)
    3. Executes workflow locally or remotely
    
    Args:
        workflow_json: The ComfyUI workflow
        auto_download: Whether to automatically download missing models
        execution_mode: "local" (requires ComfyUI running) or "remote" (uses Replicate)
        models_path: Path to store models
    
    Returns:
        Dict with execution results
    """
    manager = ComfyUIModelManager(models_path=models_path)
    analysis = manager.analyze_workflow(workflow_json)
    
    result = {
        "analysis": analysis,
        "downloads": {},
        "execution": None
    }
    
    # Download missing models if requested
    if auto_download and analysis["missing_models"]:
        result["downloads"] = manager.download_all_missing(analysis["missing_models"])
    
    # Execute workflow
    executor = ComfyUIExecutor(manager)
    
    if execution_mode == "local":
        result["execution"] = executor.execute_locally(workflow_json)
    else:
        result["execution"] = executor.execute_remotely(workflow_json)
    
    return result
