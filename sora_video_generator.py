"""
Sora-2 Product Video Generator
Uses OpenAI's Sora-2 to generate actual video footage showcasing products
"""

import os
import replicate
from pathlib import Path
from typing import List, Optional
import requests
import logging
import time
from PIL import Image

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SoraProductVideoGenerator:
    """
    Generate product commercials using Sora-2 video generation.
    Takes product images and creates dynamic video footage with audio.
    """
    
    def __init__(self, replicate_token: str):
        self.replicate_token = replicate_token
        os.environ["REPLICATE_API_TOKEN"] = replicate_token
        
    def generate_product_video(
        self,
        product_image_path: str,
        campaign_concept: str,
        product_name: str,
        duration: int = 8,
        aspect_ratio: str = "16:9",
        output_path: str = None,
        resolution: str = "1080p",
        seed: int = -1,
        loop: bool = False,
        include_audio: bool = True
    ) -> str:
        """
        Generate a product showcase video using Sora-2 with advanced parameters.
        
        Args:
            product_image_path: Path to product mockup image
            campaign_concept: Marketing campaign description
            product_name: Name of the product
            duration: Video duration in seconds (4, 8, or 12)
            aspect_ratio: "16:9" (landscape) or "9:16" (portrait)
            output_path: Where to save the video
            resolution: Video resolution ("720p" or "1080p")
            seed: Reproducibility seed (-1 for random)
            loop: Create seamless loop if supported
            include_audio: Generate synchronized audio (Sora-2 feature)
            
        Returns:
            str: Path to generated video file
        """
        try:
            logger.info(f"🎬 Generating Sora-2 video for: {product_name[:50]}")
            logger.info(f"   Duration: {duration}s, Aspect: {aspect_ratio}")
            
            # Create prompt for product showcase
            prompt = self._create_video_prompt(campaign_concept, product_name)
            logger.info(f"📝 Prompt: {prompt[:100]}...")
            
            # Map aspect ratios to Sora-2 format
            sora_aspect = "landscape" if aspect_ratio == "16:9" else "portrait"
            
            # Ensure duration is valid (4, 8, or 12)
            valid_durations = [4, 8, 12]
            sora_duration = min(valid_durations, key=lambda x: abs(x - duration))
            
            # Step 1: Open the product mockup file
            logger.info(f"📤 Using product mockup: {product_image_path}")
            
            import replicate
            
            # Step 2: Run Sora-2 with input_reference using file object
            # Replicate handles the upload automatically when you pass a file object
            logger.info("🎥 Running Sora-2 with mockup as input_reference (image-to-video)...")
            logger.info(f"   Using seconds={sora_duration}, aspect_ratio={sora_aspect}")
            
            with open(product_image_path, 'rb') as mockup_file:
                input_data = {
                    "prompt": prompt,
                    "input_reference": mockup_file,  # KEY: Pass file object, Replicate handles upload
                    "seconds": sora_duration,
                    "aspect_ratio": sora_aspect,
                    "resolution": resolution
                }
                
                # Add optional parameters
                if seed != -1:
                    input_data["seed"] = seed
                if loop:
                    input_data["loop"] = loop
                if not include_audio:
                    input_data["include_audio"] = False
                
                logger.info(f"🎬 Calling Sora-2 (this takes 2-5 minutes)...")
                logger.info(f"   input_reference: <file object from {product_image_path}>")
                logger.info(f"   Advanced params: resolution={resolution}, seed={seed}, loop={loop}, audio={include_audio}")
                
                # Use replicate.models.predictions.create() instead of replicate.run()
                # This is the proper way to call models (same as api_service.py)
                model = replicate.models.get("openai/sora-2")
                # Sora-2 does not expose .versions.list(); use default version
                prediction = replicate.predictions.create(
                    model="openai/sora-2",
                    input=input_data
                )
                
                # Wait for completion
                prediction.wait()
                
                if prediction.status != "succeeded":
                    raise Exception(f"Sora-2 prediction failed: {prediction.error}")
                
                output = prediction.output
            
            logger.info(f"✅ Sora-2 completed! Output type: {type(output)}")
            
            # Step 3: Download the video
            if not output_path:
                output_path = str(Path.cwd() / f"sora_video_{int(time.time())}.mp4")
            
            logger.info(f"📥 Downloading video to: {output_path}")
            
            # Handle output from predictions API
            # Output can be: string URL, list of URLs, or FileOutput object
            video_url = None
            
            if isinstance(output, str):
                # Direct URL string
                video_url = output
            elif isinstance(output, list) and len(output) > 0:
                # List of URLs - take first one
                video_url = output[0] if isinstance(output[0], str) else str(output[0])
            elif hasattr(output, 'url'):
                # FileOutput object with url method
                video_url = output.url()
            elif hasattr(output, 'read'):
                # File-like object
                logger.info("   Writing video from file object...")
                with open(output_path, 'wb') as f:
                    f.write(output.read())
                logger.info(f"✅ Video saved to: {output_path}")
                return output_path
            else:
                raise Exception(f"Unexpected output format: {type(output)} - {output}")
            
            # Download from URL
            logger.info(f"   Video URL: {video_url}")
            response = requests.get(video_url, timeout=300)
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
            else:
                raise Exception(f"Failed to download video: HTTP {response.status_code}")
            
            logger.info(f"✅ Video saved to: {output_path}")
            return output_path
                
        except Exception as e:
            logger.error(f"❌ Sora-2 video generation failed: {e}")
            logger.error(f"   Product image: {product_image_path}")
            if 'prompt' in locals():
                logger.error(f"   Prompt: {prompt[:200]}")
            raise
    
    def _create_video_prompt(self, campaign_concept: str, product_name: str, framing: str = "wide establishing shot") -> str:
        """
        Create optimized prompt for Sora-2 video generation focused on wall art.
        
        Since the image parameter provides the actual product mockup, the prompt should
        describe the desired camera movement and atmosphere WITHOUT describing what the
        product looks like (Sora-2 already has the product image).
        
        Args:
            campaign_concept: Marketing campaign description
            product_name: Name of the product
            framing: Camera framing (wide, medium, close-up)
        
        Returns:
            str: Optimized prompt for Sora-2
        """
        prompt = f"""Professional lifestyle commercial showcasing this product.

Camera slowly dollies toward the product, revealing details. The scene features contemporary interior design with clean lines, natural wood accents, and tasteful furniture. Soft natural light streams through nearby windows, creating a warm, inviting atmosphere.

Camera movement: Smooth dolly-in from {framing} → closer shot focusing on the product. Movement is slow and elegant, giving viewers time to appreciate the product and the lifestyle setting.

Lighting: Golden hour natural light from windows, creating warm ambiance. The product is perfectly lit, colors vivid and true-to-life. Subtle shadows add depth to the scene.

Style: Aspirational lifestyle photography, high-end interior design aesthetic, cinematic quality. Shot on cinema camera with shallow depth of field, the product remains in sharp focus while background gently blurs.

Audio: Soft ambient sounds - gentle music, distant city sounds or nature, creating a peaceful, sophisticated mood. No dialogue."""
        
        return prompt
    
    def generate_multiple_clips(
        self,
        product_images: List[str],
        campaign_concept: str,
        product_name: str,
        output_dir: str,
        duration_per_clip: int = 6
    ) -> List[str]:
        """
        Generate multiple video clips from different product angles/mockups.
        
        Returns:
            List of paths to generated video clips
        """
        logger.info(f"🎬 Generating {len(product_images)} video clips with Sora-2...")
        
        video_clips = []
        output_path_obj = Path(output_dir)
        output_path_obj.mkdir(parents=True, exist_ok=True)
        
        for idx, img_path in enumerate(product_images, 1):
            try:
                output_path = str(output_path_obj / f"clip_{idx}.mp4")
                
                logger.info(f"\n📹 Clip {idx}/{len(product_images)}")
                video_path = self.generate_product_video(
                    product_image_path=img_path,
                    campaign_concept=campaign_concept,
                    product_name=product_name,
                    duration=duration_per_clip,
                    aspect_ratio="16:9",
                    output_path=output_path
                )
                
                video_clips.append(video_path)
                logger.info(f"✅ Clip {idx} complete")
                
            except Exception as e:
                logger.error(f"❌ Clip {idx} failed: {e}")
        
        logger.info(f"\n✅ Generated {len(video_clips)}/{len(product_images)} clips")
        return video_clips
    
    def create_social_media_video(
        self,
        product_image_path: str,
        campaign_concept: str,
        product_name: str,
        platform: str = "instagram",
        output_path: str = "social_video.mp4"
    ) -> str:
        """
        Generate short-form social media video (TikTok, Instagram Reels, etc).
        
        Args:
            platform: "instagram", "tiktok", "youtube_shorts" (all 9:16)
        """
        logger.info(f"📱 Generating {platform} video...")
        
        # Short-form video optimizations
        duration = 6  # 6 seconds for social
        aspect_ratio = "9:16"  # Vertical for mobile
        
        # Adjust prompt for social media
        social_prompt = f"""Eye-catching vertical social media video for {product_name}.

{campaign_concept}

Shot in trendy modern aesthetic perfect for {platform}. Vertical 9:16 framing optimized for mobile screens.

Dynamic camera movement: Quick dolly-in combined with slight upward tilt, creating energetic engaging motion. Product is hero element in center frame.

Vibrant colors, high contrast, punchy visuals that grab attention while scrolling. Professional studio lighting with colorful accent lights.

Fast-paced energy perfect for social media. Upbeat ambient sounds with trendy vibe.

Style: Modern commercial aesthetic, Instagram-ready, TikTok-viral quality, attention-grabbing visuals."""
        
        try:
            # Use predictions API like generate_commercial_video
            model = replicate.models.get("openai/sora-2")
            # Sora-2 does not expose .versions.list(); use default version
            with open(product_image_path, 'rb') as img_file:
                prediction = replicate.predictions.create(
                    version=model.default_version,
                    input={
                        "prompt": social_prompt,
                        "image": img_file,
                        "duration": duration,
                        "aspect_ratio": aspect_ratio,
                        "resolution": "1080p"
                    }
                )
            
            # Wait for prediction and get output
            prediction.wait()
            
            if prediction.status != "succeeded":
                raise Exception(f"Sora-2 prediction failed: {prediction.error}")
            
            output = prediction.output
            
            # Handle output (URL string or list)
            video_url = None
            if isinstance(output, str):
                video_url = output
            elif isinstance(output, list) and len(output) > 0:
                video_url = output[0] if isinstance(output[0], str) else str(output[0])
            else:
                video_url = str(output)
            
            # Download
            logger.info(f"   Downloading from: {video_url}")
            response = requests.get(video_url, timeout=300)
            
            if response.status_code == 200:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                
                logger.info(f"✅ {platform} video saved: {output_path}")
                return output_path
            else:
                raise Exception(f"Failed to download: HTTP {response.status_code}")
                    
        except Exception as e:
            logger.error(f"❌ Social video generation failed: {e}")
            raise
