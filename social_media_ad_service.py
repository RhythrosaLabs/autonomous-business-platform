"""
Social Media Ad Enhancement Service
Integrates professional ad generation pipelines from Replicate:
- pipeline-examples/ads-for-products: Static product ads with professional styling
- pipeline-examples/video-ads: Animated video advertisements
- loolau/flux-static-ads: High-quality static ads for brands
- subhash25rawat/logo-in-context: Logo placement in contextual scenes

Enhances social media visuals and video production with advertising-grade quality.
"""

import os
import time
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import replicate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SocialMediaAdService:
    """
    Professional ad generation service using Replicate's advertising pipelines.
    
    Key Features:
    - Generate multiple ad variations from product images
    - Create animated video ads from static products
    - Professional static ads with brand styling
    - Logo placement in contextual product scenes
    - Target audience and style customization
    """
    
    def __init__(self, replicate_token: Optional[str] = None):
        """
        Initialize the social media ad service.
        
        Args:
            replicate_token: Replicate API token (optional, will use env var if not provided)
        """
        self.token = replicate_token or os.getenv('REPLICATE_API_TOKEN')
        if self.token:
            os.environ['REPLICATE_API_TOKEN'] = self.token
        
        logger.info("✅ Social Media Ad Service initialized")
    
    def generate_product_ads(
        self,
        product_image_path: str,
        num_variations: int = 3,
        product_description: str = "",
        target_audience: str = "general consumers",
        ad_style: str = "modern and clean"
    ) -> List[str]:
        """
        Generate professional static ads from a product image.
        
        Uses: pipeline-examples/ads-for-products
        
        Args:
            product_image_path: Path to product image file
            num_variations: Number of ad variations (1-10)
            product_description: Optional product description for better prompts
            target_audience: Target audience (e.g., 'young professionals', 'fitness enthusiasts')
            ad_style: Style preference (e.g., 'minimalist', 'vibrant and energetic', 'luxury and elegant')
        
        Returns:
            List of Replicate CDN URLs for generated ads
        """
        logger.info(f"🎨 Generating {num_variations} product ads (style: {ad_style})...")
        
        try:
            output = replicate.run(
                "pipeline-examples/ads-for-products:latest",
                input={
                    "product_image": open(product_image_path, 'rb'),
                    "num_prompts": min(max(num_variations, 1), 10),
                    "product_description": product_description,
                    "target_audience": target_audience,
                    "ad_style": ad_style
                }
            )
            
            # Output is an iterator of URLs
            ad_urls = list(output)
            logger.info(f"✅ Generated {len(ad_urls)} product ads")
            return ad_urls
            
        except Exception as e:
            logger.error(f"❌ Product ad generation failed: {e}")
            return []
    
    def generate_video_ads(
        self,
        product_image_path: str,
        num_variations: int = 2,
        product_description: str = "",
        target_audience: str = "general consumers",
        ad_style: str = "modern and clean",
        video_duration: int = 5
    ) -> List[str]:
        """
        Generate animated video ads from a product image.
        
        Uses: pipeline-examples/video-ads
        
        Args:
            product_image_path: Path to product image file
            num_variations: Number of video variations (1-10)
            product_description: Optional product description for better prompts
            target_audience: Target audience
            ad_style: Style preference
            video_duration: Duration in seconds (default: 5)
        
        Returns:
            List of Replicate CDN URLs for generated video ads (.mp4)
        """
        logger.info(f"🎥 Generating {num_variations} video ads ({video_duration}s each)...")
        
        try:
            output = replicate.run(
                "pipeline-examples/video-ads:latest",
                input={
                    "product_image": open(product_image_path, 'rb'),
                    "num_prompts": min(max(num_variations, 1), 10),
                    "product_description": product_description,
                    "target_audience": target_audience,
                    "ad_style": ad_style,
                    "video_duration": video_duration
                }
            )
            
            # Output is an iterator of video URLs
            video_urls = list(output)
            logger.info(f"✅ Generated {len(video_urls)} video ads")
            return video_urls
            
        except Exception as e:
            logger.error(f"❌ Video ad generation failed: {e}")
            return []
    
    def generate_static_brand_ads(
        self,
        brand_name: str,
        brand_description: str,
        ad_concept: str,
        num_variations: int = 3
    ) -> List[str]:
        """
        Generate high-quality static ads for a brand.
        
        Uses: loolau/flux-static-ads
        
        Args:
            brand_name: Name of the brand
            brand_description: Description of brand identity
            ad_concept: Concept/theme for the ad
            num_variations: Number of variations to generate
        
        Returns:
            List of Replicate CDN URLs for static brand ads
        """
        logger.info(f"🏢 Generating {num_variations} static brand ads for {brand_name}...")
        
        try:
            ad_urls = []
            
            for i in range(num_variations):
                # Flux-static-ads takes text prompts for brand ads
                prompt = f"{brand_name} advertisement: {ad_concept}. {brand_description}. Professional, high-quality, commercial ad design"
                
                output = replicate.run(
                    "loolau/flux-static-ads:latest",
                    input={
                        "prompt": prompt,
                        "num_outputs": 1
                    }
                )
                
                # Get URL from output
                result = list(output) if hasattr(output, '__iter__') else [output]
                ad_urls.extend(result)
                
                time.sleep(0.5)  # Rate limiting
            
            logger.info(f"✅ Generated {len(ad_urls)} static brand ads")
            return ad_urls
            
        except Exception as e:
            logger.error(f"❌ Static brand ad generation failed: {e}")
            return []
    
    def place_logo_in_context(
        self,
        logo_image_path: str,
        context_prompt: str,
        num_variations: int = 3
    ) -> List[str]:
        """
        Place company logo on objects in contextual scenes.
        
        Uses: subhash25rawat/logo-in-context
        Creates marketing materials with logos on products, packaging, etc.
        
        Args:
            logo_image_path: Path to logo image file
            context_prompt: Description of context (e.g., "coffee mug on office desk", "t-shirt on model")
            num_variations: Number of variations to generate
        
        Returns:
            List of Replicate CDN URLs for logo-in-context images
        """
        logger.info(f"🎯 Placing logo in context: {context_prompt}...")
        
        try:
            logo_urls = []
            
            for i in range(num_variations):
                output = replicate.run(
                    "subhash25rawat/logo-in-context:latest",
                    input={
                        "logo": open(logo_image_path, 'rb'),
                        "prompt": context_prompt,
                        "num_inference_steps": 50
                    }
                )
                
                # Get URL from output
                result = list(output) if hasattr(output, '__iter__') else [output]
                logo_urls.extend(result)
                
                time.sleep(0.5)  # Rate limiting
            
            logger.info(f"✅ Generated {len(logo_urls)} logo-in-context images")
            return logo_urls
            
        except Exception as e:
            logger.error(f"❌ Logo-in-context generation failed: {e}")
            return []
    
    def enhance_social_media_campaign(
        self,
        product_image_path: str,
        product_name: str,
        target_audience: str = "general consumers",
        include_video: bool = True,
        logo_path: Optional[str] = None
    ) -> Dict[str, List[str]]:
        """
        Generate a complete social media campaign with enhanced visuals.
        
        Args:
            product_image_path: Path to main product image
            product_name: Name/description of product
            target_audience: Target audience description
            include_video: Whether to generate video ads (default: True)
            logo_path: Optional logo for branded content
        
        Returns:
            Dictionary with 'static_ads', 'video_ads', 'brand_ads', and 'logo_content' lists
        """
        logger.info(f"🚀 Launching enhanced social media campaign for: {product_name}")
        
        results = {
            'static_ads': [],
            'video_ads': [],
            'brand_ads': [],
            'logo_content': []
        }
        
        # 1. Generate professional product ads (3 variations)
        logger.info("📸 Step 1/4: Generating static product ads...")
        results['static_ads'] = self.generate_product_ads(
            product_image_path,
            num_variations=3,
            product_description=product_name,
            target_audience=target_audience,
            ad_style="modern and clean"
        )
        
        # 2. Generate video ads if requested (2 variations, 5s each)
        if include_video:
            logger.info("🎬 Step 2/4: Generating video ads...")
            results['video_ads'] = self.generate_video_ads(
                product_image_path,
                num_variations=2,
                product_description=product_name,
                target_audience=target_audience,
                ad_style="vibrant and energetic",
                video_duration=5
            )
        
        # 3. Generate branded content with logo if provided
        if logo_path and os.path.exists(logo_path):
            logger.info("🎯 Step 3/4: Creating logo-in-context content...")
            contexts = [
                f"{product_name} on white background, studio lighting",
                f"{product_name} in lifestyle setting, natural lighting",
                f"{product_name} with elegant packaging"
            ]
            for context in contexts:
                logo_results = self.place_logo_in_context(logo_path, context, num_variations=1)
                results['logo_content'].extend(logo_results)
        
        logger.info("✅ Enhanced social media campaign complete!")
        logger.info(f"   → {len(results['static_ads'])} static ads")
        logger.info(f"   → {len(results['video_ads'])} video ads")
        logger.info(f"   → {len(results['logo_content'])} branded assets")
        
        return results


def download_and_save_ads(
    ad_urls: List[str],
    save_directory: Path,
    prefix: str = "ad"
) -> List[str]:
    """
    Download ads from Replicate CDN and save locally.
    
    Args:
        ad_urls: List of Replicate CDN URLs
        save_directory: Directory to save files
        prefix: Filename prefix (default: "ad")
    
    Returns:
        List of local file paths
    """
    import requests
    
    save_directory = Path(save_directory)
    save_directory.mkdir(parents=True, exist_ok=True)
    
    local_paths = []
    
    for idx, url in enumerate(ad_urls, 1):
        try:
            # Determine file extension from URL
            extension = ".mp4" if "mp4" in url.lower() else ".png"
            filename = f"{prefix}_{idx}{extension}"
            filepath = save_directory / filename
            
            # Download file
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            
            # Save to disk
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            local_paths.append(str(filepath))
            logger.info(f"✅ Saved: {filename}")
            
        except Exception as e:
            logger.error(f"❌ Failed to download {url}: {e}")
    
    return local_paths


# Example usage
if __name__ == "__main__":
    # Initialize service
    service = SocialMediaAdService()
    
    # Example: Generate product ads
    product_image = "path/to/product.png"
    
    # Generate 3 static ads
    static_ads = service.generate_product_ads(
        product_image,
        num_variations=3,
        product_description="Premium wireless headphones",
        target_audience="young professionals",
        ad_style="minimalist"
    )
    
    # Generate 2 video ads
    video_ads = service.generate_video_ads(
        product_image,
        num_variations=2,
        product_description="Premium wireless headphones",
        target_audience="young professionals",
        ad_style="vibrant and energetic"
    )
    
    print(f"Generated {len(static_ads)} static ads")
    print(f"Generated {len(video_ads)} video ads")
