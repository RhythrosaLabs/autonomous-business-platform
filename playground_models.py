"""
Playground Model Configurations
Defines parameters for all image and video generation models
"""

# Image Generation Models
IMAGE_MODELS = {
    "prunaai/flux-fast": {
        "name": "Flux Fast (Fastest)",
        "description": "Ultra-fast Flux endpoint - 4 steps",
        "parameters": {
            "prompt": {"type": "text", "required": True},
            "aspect_ratio": {"type": "select", "options": ["1:1", "16:9", "9:16", "21:9", "9:21", "4:3", "3:4"], "default": "1:1"},
            "num_inference_steps": {"type": "slider", "min": 1, "max": 8, "default": 4},
            "guidance_scale": {"type": "slider", "min": 1.0, "max": 10.0, "default": 3.5, "step": 0.5},
            "seed": {"type": "number", "min": 0, "max": 999999, "default": 0, "help": "0 = random"}
        }
    },
    "stability-ai/sdxl": {
        "name": "Stable Diffusion XL",
        "description": "High-quality image generation",
        "parameters": {
            "prompt": {"type": "text", "required": True},
            "negative_prompt": {"type": "text", "default": "ugly, blurry, low quality, distorted"},
            "width": {"type": "slider", "min": 512, "max": 1536, "default": 1024, "step": 64},
            "height": {"type": "slider", "min": 512, "max": 1536, "default": 1024, "step": 64},
            "num_inference_steps": {"type": "slider", "min": 1, "max": 100, "default": 50},
            "guidance_scale": {"type": "slider", "min": 1.0, "max": 20.0, "default": 7.5, "step": 0.5},
            "scheduler": {"type": "select", "options": ["DPMSolverMultistep", "DDIM", "K_EULER", "K_EULER_ANCESTRAL", "PNDM", "KLMS"], "default": "K_EULER"},
            "seed": {"type": "number", "min": 0, "max": 999999, "default": 0}
        }
    },
    "bytedance/seedream-4": {
        "name": "SeeDream 4 (4K)",
        "description": "Unified text-to-image up to 4K resolution",
        "parameters": {
            "prompt": {"type": "text", "required": True},
            "aspect_ratio": {"type": "select", "options": ["1:1", "16:9", "9:16", "4:3", "3:4"], "default": "1:1"},
            "seed": {"type": "number", "min": 0, "max": 999999, "default": 0}
        }
    },
    "google/imagen-4-ultra": {
        "name": "Imagen 4 Ultra",
        "description": "Google's highest quality image model",
        "parameters": {
            "prompt": {"type": "text", "required": True},
            "aspect_ratio": {"type": "select", "options": ["1:1", "16:9", "9:16", "4:3", "3:4"], "default": "1:1"}
        }
    },
    "bria/image-3.2": {
        "name": "Bria Image 3.2",
        "description": "Commercial-safe image generation",
        "parameters": {
            "prompt": {"type": "text", "required": True},
            "aspect_ratio": {"type": "select", "options": ["1:1", "16:9", "9:16"], "default": "1:1"}
        }
    },
    "black-forest-labs/flux-kontext-pro": {
        "name": "Flux Kontext Pro",
        "description": "Face-aware image generation",
        "parameters": {
            "prompt": {"type": "text", "required": True},
            "image": {"type": "file", "help": "Reference image for face/style guidance"},
            "aspect_ratio": {"type": "select", "options": ["1:1", "16:9", "9:16", "21:9", "4:3"], "default": "1:1"},
            "seed": {"type": "number", "min": 0, "max": 999999, "default": 0}
        }
    }
}

# Video Generation Models
VIDEO_MODELS = {
    "openai/sora-2": {
        "name": "Sora 2 (OpenAI)",
        "description": "Flagship video with synced audio",
        "parameters": {
            "prompt": {"type": "text", "required": True},
            "image": {"type": "file", "help": "Start image for image-to-video"},
            "duration": {"type": "slider", "min": 2, "max": 10, "default": 5},
            "quality": {"type": "select", "options": ["standard", "high"], "default": "high"},
            "remove_watermark": {"type": "checkbox", "default": True}
        }
    },
    "kwaivgi/kling-v2.5-turbo-pro": {
        "name": "Kling v2.5 Turbo Pro",
        "description": "Pro-level text-to-video and image-to-video",
        "parameters": {
            "prompt": {"type": "text", "required": True},
            "image": {"type": "file", "help": "Start image for i2v"},
            "aspect_ratio": {"type": "select", "options": ["16:9", "9:16", "1:1", "4:3"], "default": "16:9"},
            "duration": {"type": "slider", "min": 5, "max": 10, "default": 5},
            "motion_level": {"type": "slider", "min": 1, "max": 10, "default": 4, "help": "Camera motion intensity"},
            "seed": {"type": "number", "min": 0, "max": 999999, "default": 0}
        }
    },
    "pixverse/pixverse-v5": {
        "name": "Pixverse v5",
        "description": "Latest Pixverse model",
        "parameters": {
            "prompt": {"type": "text", "required": True},
            "first_frame_image": {"type": "file", "help": "Start image"},
            "aspect_ratio": {"type": "select", "options": ["16:9", "9:16", "1:1"], "default": "16:9"},
            "seed": {"type": "number", "min": 0, "max": 999999, "default": 0},
            "negative_prompt": {"type": "text", "default": ""}
        }
    },
    "pixverse/pixverse-v4.5": {
        "name": "Pixverse v4.5",
        "description": "Previous Pixverse model",
        "parameters": {
            "prompt": {"type": "text", "required": True},
            "first_frame_image": {"type": "file", "help": "Start image"},
            "aspect_ratio": {"type": "select", "options": ["16:9", "9:16", "1:1"], "default": "16:9"}
        }
    },
    "leonardoai/motion-2.0": {
        "name": "Leonardo Motion 2.0",
        "description": "Leonardo's motion engine",
        "parameters": {
            "prompt": {"type": "text", "required": True},
            "first_frame_image": {"type": "file", "required": True, "help": "Image to animate"},
            "aspect_ratio": {"type": "select", "options": ["16_9", "9_16", "1_1"], "default": "16_9"},
            "motion_strength": {"type": "slider", "min": 1, "max": 10, "default": 5}
        }
    },
    "minimax/hailuo-2.3-fast": {
        "name": "Hailuo 2.3 Fast",
        "description": "Fast image-to-video (requires image)",
        "parameters": {
            "prompt": {"type": "text", "required": True},
            "first_frame_image": {"type": "file", "required": True},
            "duration": {"type": "slider", "min": 5, "max": 10, "default": 6},
            "resolution": {"type": "select", "options": ["540p", "720p", "768p"], "default": "768p"}
        }
    },
    "google/veo-3.1-fast": {
        "name": "Veo 3.1 Fast",
        "description": "Fastest Veo 3.1 with context-aware audio",
        "parameters": {
            "prompt": {"type": "text", "required": True},
            "first_frame_image": {"type": "file", "help": "Reference image"},
            "aspect_ratio": {"type": "select", "options": ["16:9", "9:16", "1:1"], "default": "16:9"},
            "duration": {"type": "slider", "min": 2, "max": 8, "default": 5},
            "guidance_scale": {"type": "slider", "min": 1.0, "max": 10.0, "default": 3.0, "step": 0.5}
        }
    },
    "google/veo-3": {
        "name": "Veo 3",
        "description": "Google's Veo 3 model",
        "parameters": {
            "prompt": {"type": "text", "required": True},
            "first_frame_image": {"type": "file", "help": "Reference image"},
            "aspect_ratio": {"type": "select", "options": ["16:9", "9:16", "1:1"], "default": "16:9"},
            "duration": {"type": "slider", "min": 2, "max": 8, "default": 5},
            "guidance_scale": {"type": "slider", "min": 1.0, "max": 10.0, "default": 3.0, "step": 0.5}
        }
    },
    "google/veo-3-fast": {
        "name": "Veo 3 Fast",
        "description": "Faster Veo 3 variant",
        "parameters": {
            "prompt": {"type": "text", "required": True},
            "first_frame_image": {"type": "file", "help": "Reference image"},
            "aspect_ratio": {"type": "select", "options": ["16:9", "9:16", "1:1"], "default": "16:9"},
            "duration": {"type": "slider", "min": 2, "max": 8, "default": 5}
        }
    },
    "luma/ray-2-540p": {
        "name": "Luma Ray 2 (540p)",
        "description": "Luma's Ray model at 540p",
        "parameters": {
            "prompt": {"type": "text", "required": True},
            "first_frame_image": {"type": "file", "help": "Start image"},
            "aspect_ratio": {"type": "select", "options": ["16:9", "9:16", "1:1", "4:3", "3:4", "21:9", "9:21"], "default": "16:9"}
        }
    },
    "google/veo-2": {
        "name": "Veo 2",
        "description": "Google's Veo 2 model",
        "parameters": {
            "prompt": {"type": "text", "required": True},
            "first_frame_image": {"type": "file", "help": "Reference image"},
            "aspect_ratio": {"type": "select", "options": ["16:9", "9:16", "1:1"], "default": "16:9"},
            "resolution": {"type": "select", "options": ["720p", "1080p"], "default": "1080p"},
            "guidance": {"type": "slider", "min": 1.0, "max": 10.0, "default": 3.0, "step": 0.5}
        }
    },
    "wan-video/wan-2.5-t2v-fast": {
        "name": "Wan 2.5 T2V Fast",
        "description": "Fast text-to-video",
        "parameters": {
            "prompt": {"type": "text", "required": True},
            "first_frame_image": {"type": "file", "help": "Optional start image"},
            "aspect_ratio": {"type": "select", "options": ["16:9", "9:16", "1:1"], "default": "16:9"}
        }
    },
    "bytedance/seedance-1-pro-fast": {
        "name": "Seedance 1 Pro Fast",
        "description": "Cinematic-quality videos 3× faster",
        "parameters": {
            "prompt": {"type": "text", "required": True},
            "first_frame_image": {"type": "file", "help": "Start image"},
            "aspect_ratio": {"type": "select", "options": ["16:9", "9:16", "1:1"], "default": "16:9"}
        }
    },
    "pipeline-examples/video-ads": {
        "name": "Video Ads Pipeline",
        "description": "Automated video ad creation",
        "parameters": {
            "prompt": {"type": "text", "required": True},
            "product_image": {"type": "file", "help": "Product image"},
            "duration": {"type": "slider", "min": 5, "max": 30, "default": 15}
        }
    }
}

def get_model_config(model_ref: str, model_type: str = "image"):
    """Get configuration for a specific model"""
    models = IMAGE_MODELS if model_type == "image" else VIDEO_MODELS
    return models.get(model_ref, {})

def build_model_input(model_ref: str, model_type: str, form_data: dict):
    """Build the input dict for a model based on form data"""
    config = get_model_config(model_ref, model_type)
    if not config:
        return {}
    
    model_input = {}
    for param_name, param_config in config.get("parameters", {}).items():
        # Skip file uploads - handle separately
        if param_config["type"] == "file":
            continue
            
        # Get value from form data
        value = form_data.get(param_name)
        
        # Apply defaults if not provided
        if value is None and "default" in param_config:
            value = param_config["default"]
        
        # Add to input if not None/empty
        if value is not None and value != "" and value != 0:
            model_input[param_name] = value
    
    return model_input


# Image Editing & Utility Models
EDITING_MODELS = {
    "google/nano-banana": {
        "name": "Nano Banana (Google Gemini)",
        "description": "Google's latest image editing model in Gemini 2.5",
        "category": "editing",
        "parameters": {
            "prompt": {"type": "text", "required": True},
            "image": {"type": "file", "required": True, "help": "Image to edit"},
            "temperature": {"type": "slider", "min": 0.0, "max": 2.0, "default": 1.0, "step": 0.1},
            "max_tokens": {"type": "number", "min": 1, "max": 8192, "default": 4096}
        }
    },
    "hardikdava/flux-image-editing": {
        "name": "Flux Image Editing",
        "description": "Image editing with Flux-dev model",
        "category": "editing",
        "parameters": {
            "prompt": {"type": "text", "required": True},
            "image": {"type": "file", "required": True, "help": "Image to edit"},
            "seed": {"type": "number", "min": 0, "max": 999999, "default": 0},
            "steps": {"type": "slider", "min": 1, "max": 50, "default": 28},
            "guidance": {"type": "slider", "min": 1.0, "max": 10.0, "default": 3.5, "step": 0.5}
        }
    },
    "reve/edit-fast": {
        "name": "Edit Fast",
        "description": "Reve's fast image edit model at $0.01 per edit",
        "category": "editing",
        "parameters": {
            "prompt": {"type": "text", "required": True},
            "image": {"type": "file", "required": True, "help": "Image to edit"},
            "seed": {"type": "number", "min": 0, "max": 999999, "default": 0}
        }
    },
    "lucataco/next-scene": {
        "name": "Next Scene",
        "description": "Generate cinematic image sequences with natural visual progression",
        "category": "editing",
        "parameters": {
            "prompt": {"type": "text", "default": "Next Scene: The camera zooms in on the subject"},
            "image": {"type": "file", "required": True, "help": "Image to edit"},
            "lora_scale": {"type": "slider", "min": 0.0, "max": 4.0, "default": 0.8, "step": 0.1},
            "aspect_ratio": {"type": "select", "options": ["match_input_image", "1:1", "16:9", "9:16", "4:3", "3:4"], "default": "match_input_image"},
            "output_format": {"type": "select", "options": ["webp", "jpg", "png"], "default": "webp"},
            "output_quality": {"type": "slider", "min": 0, "max": 100, "default": 95},
            "seed": {"type": "number", "min": 0, "max": 999999, "default": 0}
        }
    },
    "cjwbw/stable-diffusion-v2-inpainting": {
        "name": "SD v2 Inpainting",
        "description": "Stable Diffusion v2 inpainting model",
        "category": "editing",
        "parameters": {
            "prompt": {"type": "text", "required": True},
            "image": {"type": "file", "required": True, "help": "Image to inpaint"},
            "mask": {"type": "file", "required": True, "help": "Mask image (white = inpaint area)"},
            "num_inference_steps": {"type": "slider", "min": 1, "max": 100, "default": 50},
            "guidance_scale": {"type": "slider", "min": 1.0, "max": 20.0, "default": 7.5, "step": 0.5},
            "seed": {"type": "number", "min": 0, "max": 999999, "default": 0}
        }
    }
}

# Advertising & Marketing Models
MARKETING_MODELS = {
    "pipeline-examples/ads-for-products": {
        "name": "Ads for Products",
        "description": "Create stunning ads using an image of a product",
        "category": "marketing",
        "parameters": {
            "product_image": {"type": "file", "required": True, "help": "Upload an image of your product"},
            "num_prompts": {"type": "slider", "min": 1, "max": 10, "default": 3, "help": "Number of ad variations"},
            "product_description": {"type": "text", "help": "Optional description of your product"},
            "target_audience": {"type": "text", "default": "general consumers"},
            "ad_style": {"type": "text", "default": "modern and clean"}
        }
    },
    "loolau/flux-static-ads": {
        "name": "Flux Static Ads",
        "description": "Create the best static ads for your brand",
        "category": "marketing",
        "parameters": {
            "prompt": {"type": "text", "required": True},
            "product_image": {"type": "file", "help": "Product image (optional)"},
            "aspect_ratio": {"type": "select", "options": ["1:1", "16:9", "9:16", "4:3", "3:4"], "default": "1:1"},
            "num_outputs": {"type": "slider", "min": 1, "max": 4, "default": 1},
            "seed": {"type": "number", "min": 0, "max": 999999, "default": 0}
        }
    },
    "subhash25rawat/logo-in-context": {
        "name": "Logo in Context",
        "description": "Create ads with your company logo on any object",
        "category": "marketing",
        "parameters": {
            "prompt": {"type": "text", "required": True},
            "logo_image": {"type": "file", "required": True, "help": "Your company logo"},
            "product_image": {"type": "file", "help": "Optional product image"},
            "seed": {"type": "number", "min": 0, "max": 999999, "default": 0}
        }
    },
    "logerzhu/ad-inpaint": {
        "name": "Ad Inpaint",
        "description": "Product advertising image generator with inpainting",
        "category": "marketing",
        "parameters": {
            "prompt": {"type": "text", "required": True},
            "image_path": {"type": "file", "required": True, "help": "Product image"},
            "image_num": {"type": "slider", "min": 1, "max": 4, "default": 1, "help": "Number of outputs"},
            "manual_seed": {"type": "number", "min": -1, "max": 999999, "default": -1}
        }
    }
}

# Video Editing Models
VIDEO_EDITING_MODELS = {
    "luma/modify-video": {
        "name": "Luma Modify Video",
        "description": "Modify a video with style transfer and prompt-based editing",
        "category": "video_editing",
        "parameters": {
            "prompt": {"type": "text", "required": True},
            "video": {"type": "file", "required": True, "help": "Video to modify"},
            "style_strength": {"type": "slider", "min": 0.0, "max": 1.0, "default": 0.5, "step": 0.1}
        }
    },
    "wan-video/wan-2.5-v2v-fast": {
        "name": "Wan 2.5 V2V Fast",
        "description": "Fast video-to-video transformation",
        "category": "video_editing",
        "parameters": {
            "prompt": {"type": "text", "required": True},
            "video": {"type": "file", "required": True, "help": "Video to transform"},
            "strength": {"type": "slider", "min": 0.1, "max": 1.0, "default": 0.7, "step": 0.1, "help": "Transformation strength"}
        }
    },
    "lucataco/video-style-transfer": {
        "name": "Video Style Transfer",
        "description": "Apply artistic style to videos",
        "category": "video_editing",
        "parameters": {
            "video": {"type": "file", "required": True, "help": "Input video"},
            "style_image": {"type": "file", "required": True, "help": "Style reference image"},
            "strength": {"type": "slider", "min": 0.0, "max": 1.0, "default": 0.6, "step": 0.1}
        }
    },
    "google/veo-3-v2v": {
        "name": "Veo 3 V2V",
        "description": "Google Veo 3 video-to-video transformation",
        "category": "video_editing",
        "parameters": {
            "prompt": {"type": "text", "required": True},
            "video": {"type": "file", "required": True, "help": "Video to edit"},
            "guidance_scale": {"type": "slider", "min": 1.0, "max": 10.0, "default": 3.0, "step": 0.5},
            "preserve_motion": {"type": "checkbox", "default": True}
        }
    },
    "bytedance/seedance-1-pro-v2v": {
        "name": "Seedance V2V Pro",
        "description": "Professional video-to-video editing",
        "category": "video_editing",
        "parameters": {
            "prompt": {"type": "text", "required": True},
            "video": {"type": "file", "required": True, "help": "Video to edit"},
            "denoise_strength": {"type": "slider", "min": 0.0, "max": 1.0, "default": 0.5, "step": 0.1}
        }
    },
    "lucataco/video-upscaler": {
        "name": "Video Upscaler",
        "description": "Upscale videos to higher resolution",
        "category": "video_editing",
        "parameters": {
            "video": {"type": "file", "required": True, "help": "Video to upscale"},
            "scale": {"type": "select", "options": ["2x", "4x"], "default": "2x"},
            "model": {"type": "select", "options": ["realesrgan", "topaz"], "default": "realesrgan"}
        }
    },
    "lucataco/video-stabilizer": {
        "name": "Video Stabilizer",
        "description": "Stabilize shaky videos",
        "category": "video_editing",
        "parameters": {
            "video": {"type": "file", "required": True, "help": "Shaky video to stabilize"},
            "smoothness": {"type": "slider", "min": 1, "max": 100, "default": 30}
        }
    }
}

# 3D Generation Models
MODEL_3D = {
    "tencent/hunyuan3d-2": {
        "name": "Hunyuan3D-2 (Tencent)",
        "description": "High-resolution textured 3D assets from text/image",
        "category": "3d",
        "output_type": "3d_model",
        "parameters": {
            "prompt": {"type": "text", "help": "Text description of 3D model"},
            "image": {"type": "file", "help": "Input image for 3D generation"},
            "seed": {"type": "number", "min": 0, "max": 999999, "default": 0}
        }
    },
    "ndreca/hunyuan3d-2.1": {
        "name": "Hunyuan3D-2.1 (Quality)",
        "description": "Quality mode for high-res 3D generation",
        "category": "3d",
        "output_type": "3d_model",
        "parameters": {
            "prompt": {"type": "text", "help": "Text description"},
            "image": {"type": "file", "help": "Input image"},
            "quality": {"type": "select", "options": ["standard", "high"], "default": "high"},
            "seed": {"type": "number", "min": 0, "max": 999999, "default": 0}
        }
    },
    "jd7h/luciddreamer": {
        "name": "LucidDreamer",
        "description": "High-fidelity text-to-3D via interval score matching",
        "category": "3d",
        "output_type": "3d_model",
        "parameters": {
            "prompt": {"type": "text", "required": True},
            "negative_prompt": {"type": "text", "default": "low quality, blurry"},
            "num_inference_steps": {"type": "slider", "min": 10, "max": 100, "default": 50}
        }
    },
    "vufinder/vggt-1b": {
        "name": "VGGT-1B",
        "description": "Feed-forward 3D scene generation",
        "category": "3d",
        "output_type": "3d_model",
        "parameters": {
            "image": {"type": "file", "required": True, "help": "Input image for 3D"},
            "num_views": {"type": "slider", "min": 4, "max": 16, "default": 8}
        }
    },
    "subhash25rawat/morphix3d": {
        "name": "Morphix3D",
        "description": "Transform images & text into 3D models",
        "category": "3d",
        "output_type": "3d_model",
        "parameters": {
            "prompt": {"type": "text", "help": "Text description"},
            "image": {"type": "file", "help": "Input image"},
            "seed": {"type": "number", "min": 0, "max": 999999, "default": 0}
        }
    },
    "hyper3d/rodin": {
        "name": "Rodin Gen-2",
        "description": "Complex 3D models from images",
        "category": "3d",
        "output_type": "3d_model",
        "parameters": {
            "image": {"type": "file", "required": True, "help": "Input image"},
            "prompt": {"type": "text", "help": "Optional text guidance"},
            "seed": {"type": "number", "min": 0, "max": 999999, "default": 0}
        }
    },
    "stabilityai/stable-fast-3d": {
        "name": "Stable Fast 3D",
        "description": "Fast 3D asset generation in <1 second",
        "category": "3d",
        "output_type": "3d_model",
        "parameters": {
            "image": {"type": "file", "required": True, "help": "Input image"},
            "texture_resolution": {"type": "select", "options": ["512", "1024", "2048"], "default": "1024"},
            "foreground_ratio": {"type": "slider", "min": 0.5, "max": 1.0, "default": 0.85, "step": 0.05}
        }
    },
    "cjwbw/instant-mesh": {
        "name": "InstantMesh",
        "description": "Generate textured 3D meshes from single image",
        "category": "3d",
        "output_type": "3d_model",
        "parameters": {
            "image": {"type": "file", "required": True, "help": "Input image"},
            "num_views": {"type": "slider", "min": 4, "max": 12, "default": 6},
            "seed": {"type": "number", "min": 0, "max": 999999, "default": 0}
        }
    },
    "lucataco/tripo3d": {
        "name": "Tripo3D",
        "description": "Fast image/text to 3D model generation",
        "category": "3d",
        "output_type": "3d_model",
        "parameters": {
            "prompt": {"type": "text", "help": "Text description"},
            "image": {"type": "file", "help": "Input image"},
            "model_version": {"type": "select", "options": ["v1.3", "v1.4", "v2.0"], "default": "v2.0"},
            "seed": {"type": "number", "min": 0, "max": 999999, "default": 0}
        }
    },
    "camenduru/wonder3d": {
        "name": "Wonder3D",
        "description": "Single image to 3D with consistent multi-view",
        "category": "3d",
        "output_type": "3d_model",
        "parameters": {
            "image": {"type": "file", "required": True, "help": "Input image"},
            "seed": {"type": "number", "min": 0, "max": 999999, "default": 0}
        }
    },
    "ashawkey/lgm": {
        "name": "LGM (Large Gaussian Model)",
        "description": "Fast 3D generation with Gaussian splatting",
        "category": "3d",
        "output_type": "3d_model",
        "parameters": {
            "image": {"type": "file", "required": True, "help": "Input image"},
            "elevation": {"type": "slider", "min": -90, "max": 90, "default": 0, "help": "Camera elevation angle"},
            "guidance_scale": {"type": "slider", "min": 1.0, "max": 10.0, "default": 5.0, "step": 0.5}
        }
    },
    "adirik/craftsman": {
        "name": "Craftsman",
        "description": "High-quality 3D mesh generation from text/image",
        "category": "3d",
        "output_type": "3d_model",
        "parameters": {
            "prompt": {"type": "text", "help": "Text description"},
            "image": {"type": "file", "help": "Input image"},
            "mc_resolution": {"type": "slider", "min": 128, "max": 512, "default": 256, "step": 64},
            "seed": {"type": "number", "min": 0, "max": 999999, "default": 0}
        }
    }
}

# Music Generation Models
MUSIC_MODELS = {
    "meta/musicgen": {
        "name": "MusicGen (Meta)",
        "description": "Generate music from text or melody",
        "category": "music",
        "output_type": "audio",
        "parameters": {
            "prompt": {"type": "text", "required": True},
            "duration": {"type": "slider", "min": 1, "max": 30, "default": 8, "help": "Duration in seconds"},
            "temperature": {"type": "slider", "min": 0.0, "max": 1.5, "default": 1.0, "step": 0.1},
            "model_version": {"type": "select", "options": ["stereo-large", "stereo-medium", "melody-large"], "default": "stereo-large"}
        }
    },
    "google/lyria-2": {
        "name": "Lyria 2 (Google)",
        "description": "48kHz stereo music generation",
        "category": "music",
        "output_type": "audio",
        "parameters": {
            "prompt": {"type": "text", "required": True},
            "duration": {"type": "slider", "min": 5, "max": 120, "default": 30, "help": "Duration in seconds"},
            "temperature": {"type": "slider", "min": 0.5, "max": 1.5, "default": 1.0, "step": 0.1}
        }
    },
    "minimax/music-1.5": {
        "name": "Music-1.5 (Minimax)",
        "description": "Full-length songs up to 4 minutes with vocals",
        "category": "music",
        "output_type": "audio",
        "parameters": {
            "prompt": {"type": "text", "required": True},
            "duration": {"type": "slider", "min": 10, "max": 240, "default": 120, "help": "Duration in seconds"},
            "style": {"type": "text", "help": "Music style/genre"}
        }
    },
    "stability-ai/stable-audio-2.5": {
        "name": "Stable Audio 2.5",
        "description": "High-quality music and sound generation",
        "category": "music",
        "output_type": "audio",
        "parameters": {
            "prompt": {"type": "text", "required": True},
            "duration": {"type": "slider", "min": 1, "max": 180, "default": 30},
            "negative_prompt": {"type": "text", "help": "What to avoid"},
            "seed": {"type": "number", "min": 0, "max": 999999, "default": 0}
        }
    },
    "andreasjansson/musicgen-looper": {
        "name": "MusicGen Looper",
        "description": "Generate seamless music loops",
        "category": "music",
        "output_type": "audio",
        "parameters": {
            "prompt": {"type": "text", "required": True},
            "duration": {"type": "slider", "min": 2, "max": 30, "default": 8},
            "model": {"type": "select", "options": ["stereo-large", "large", "medium"], "default": "stereo-large"}
        }
    },
    "zsxkib/flux-music": {
        "name": "Flux Music",
        "description": "Music generation with Flux",
        "category": "music",
        "output_type": "audio",
        "parameters": {
            "prompt": {"type": "text", "required": True},
            "duration": {"type": "slider", "min": 5, "max": 60, "default": 20}
        }
    },
    "sakemin/musicgen-fine-tuner": {
        "name": "MusicGen Fine-Tuner",
        "description": "Fine-tune MusicGen on custom data",
        "category": "music",
        "output_type": "audio",
        "parameters": {
            "prompt": {"type": "text", "required": True},
            "audio_reference": {"type": "file", "help": "Reference audio for style"},
            "duration": {"type": "slider", "min": 1, "max": 30, "default": 10}
        }
    }
}

# Speech/Voice Models
SPEECH_MODELS = {
    "minimax/speech-02-hd": {
        "name": "Speech-02-HD (Minimax)",
        "description": "HD voice synthesis with emotion & multilingual",
        "category": "speech",
        "output_type": "audio",
        "parameters": {
            "text": {"type": "text", "required": True, "help": "Text to speak"},
            "voice": {"type": "select", "options": ["male-1", "male-2", "female-1", "female-2"], "default": "female-1"},
            "emotion": {"type": "select", "options": ["neutral", "happy", "sad", "angry", "excited"], "default": "neutral"},
            "speed": {"type": "slider", "min": 0.5, "max": 2.0, "default": 1.0, "step": 0.1},
            "language": {"type": "select", "options": ["en", "zh", "es", "fr", "de", "ja"], "default": "en"}
        }
    }
}
