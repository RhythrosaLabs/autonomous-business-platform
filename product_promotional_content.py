"""
Product Promotional Content Generator
======================================

Generate professional promotional images and videos featuring real product mockups.

Features:
- Lifestyle scene generation (coffee shop, outdoor, studio, etc.)
- Product video creation (rotation, zoom, floating)
- Social media optimized content
- Platform-specific dimensions
- AI-powered scene compositing

Uses:
- Replicate Flux for image generation
- Replicate video models for animations
- Transparent mockups from background removal

Author: Autonomous Business Platform
Version: 1.0
"""

import os
import requests
import replicate
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from PIL import Image
import json
from datetime import datetime


class ProductPromotionalContent:
    """
    Generate promotional content featuring real product mockups.
    
    Creates lifestyle scenes, product videos, and social media assets
    using transparent product mockups.
    """
    
    # Scene templates for lifestyle photography
    LIFESTYLE_SCENES = [
        {
            'name': 'minimalist_studio',
            'prompt': 'on minimalist white table, soft natural lighting, clean professional e-commerce photography, studio setup, shadows beneath product',
            'style': 'professional'
        },
        {
            'name': 'coffee_shop',
            'prompt': 'in modern coffee shop interior, wooden table, warm ambient lighting, lifestyle product photography, cozy atmosphere, soft focus background',
            'style': 'lifestyle'
        },
        {
            'name': 'outdoor_natural',
            'prompt': 'outdoor park setting, natural daylight, golden hour, lifestyle advertisement, bokeh background, green nature',
            'style': 'lifestyle'
        },
        {
            'name': 'home_office',
            'prompt': 'on modern home office desk with laptop and plants, organized workspace, aspirational lifestyle, soft window light',
            'style': 'lifestyle'
        },
        {
            'name': 'creative_abstract',
            'prompt': 'floating in abstract colorful space, vibrant gradient background, creative modern advertisement, dynamic composition',
            'style': 'creative'
        }
    ]
    
    # Platform-specific dimensions
    PLATFORM_DIMENSIONS = {
        'instagram_post': (1080, 1080),
        'instagram_story': (1080, 1920),
        'instagram_reel': (1080, 1920),
        'facebook_post': (1200, 630),
        'facebook_story': (1080, 1920),
        'tiktok': (1080, 1920),
        'youtube_thumbnail': (1280, 720),
        'pinterest': (1000, 1500),
        'twitter_post': (1200, 675),
        'linkedin_post': (1200, 627)
    }
    
    def __init__(self, replicate_token: Optional[str] = None):
        """
        Initialize promotional content generator.
        
        Args:
            replicate_token: Replicate API token (optional if in env)
        """
        self.replicate_token = replicate_token or os.getenv("REPLICATE_API_TOKEN")
        
        if self.replicate_token:
            os.environ["REPLICATE_API_TOKEN"] = self.replicate_token
    
    def generate_lifestyle_scene(
        self,
        transparent_mockup_path: str,
        concept: str,
        scene_template: Dict,
        output_path: Optional[str] = None,
        width: int = 1024,
        height: int = 1024
    ) -> Optional[str]:
        """
        Generate a lifestyle scene featuring the product mockup.
        
        Uses Flux img2img to composite transparent mockup into a styled scene.
        
        Args:
            transparent_mockup_path: Path to transparent PNG mockup
            concept: Product concept/description
            scene_template: Scene template dict with name and prompt
            output_path: Path to save output (optional)
            width: Output width
            height: Output height
            
        Returns:
            Path to generated scene or None if failed
        """
        try:
            scene_name = scene_template['name']
            scene_prompt = scene_template['prompt']
            
            print(f"🎨 Generating {scene_name} scene...")
            
            # Build complete prompt
            full_prompt = f"{concept}, {scene_prompt}, high quality, professional photography, 4k"
            
            # Generate scene with Flux using ReplicateAPI
            from api_service import ReplicateAPI
            api = ReplicateAPI(self.replicate_token)
            
            # Use flux-fast for lifestyle scenes (faster and works)
            output_url = api.generate_image(
                prompt=full_prompt,
                width=width,
                height=height,
                aspect_ratio="custom",
                output_format="png"
            )
            
            output = output_url
            
            # Download result
            if output:
                # Handle FileOutput type
                if hasattr(output, 'read'):
                    image_data = output.read()
                    image_url = None
                elif isinstance(output, str):
                    image_url = output
                    response = requests.get(output, timeout=60)
                    if response.status_code == 200:
                        image_data = response.content
                    else:
                        print(f"❌ Failed to download scene: {response.status_code}")
                        return None
                else:
                    print(f"❌ Unexpected output type: {type(output)}")
                    return None
                
                # Save image
                if not output_path:
                    mockup_name = Path(transparent_mockup_path).stem
                    output_path = str(Path(transparent_mockup_path).parent.parent / "product_scenes" / f"{mockup_name}_{scene_name}.png")
                
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_path, 'wb') as f:
                    f.write(image_data)
                
                # Verify file
                if Path(output_path).exists() and Path(output_path).stat().st_size > 0:
                    print(f"✅ Scene generated: {Path(output_path).name}")
                    return output_path
            
            print(f"❌ Failed to generate {scene_name} scene")
            return None
            
        except Exception as e:
            print(f"❌ Error generating scene: {e}")
            return None
    
    def generate_all_lifestyle_scenes(
        self,
        transparent_mockup_path: str,
        concept: str,
        campaign_dir: Path,
        num_scenes: int = 5
    ) -> List[Dict[str, str]]:
        """
        Generate multiple lifestyle scenes for a product.
        
        Args:
            transparent_mockup_path: Path to transparent PNG mockup
            concept: Product concept/description
            campaign_dir: Campaign directory
            num_scenes: Number of scenes to generate (max 5)
            
        Returns:
            List of dicts with 'name', 'path', 'style' keys
        """
        scenes = []
        
        # Ensure scenes directory exists
        scenes_dir = Path(campaign_dir) / "product_scenes"
        scenes_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate scenes
        for i, scene_template in enumerate(self.LIFESTYLE_SCENES[:num_scenes]):
            scene_name = scene_template['name']
            
            output_path = str(scenes_dir / f"{Path(transparent_mockup_path).stem}_{scene_name}.png")
            
            result = self.generate_lifestyle_scene(
                transparent_mockup_path,
                concept,
                scene_template,
                output_path
            )
            
            if result:
                scenes.append({
                    'name': scene_name,
                    'path': result,
                    'style': scene_template['style']
                })
        
        print(f"\n✅ Generated {len(scenes)}/{num_scenes} lifestyle scenes")
        return scenes
    
    def generate_product_video_text(
        self,
        concept: str,
        motion_type: str = "rotation",
        duration: int = 5
    ) -> Optional[str]:
        """
        Generate product video from text description.
        
        Note: Currently using Minimax which doesn't support img2img.
        This generates a text-based video description of the product.
        
        Args:
            concept: Product concept/description
            motion_type: Type of motion (rotation, zoom, float)
            duration: Video duration in seconds
            
        Returns:
            URL to generated video or None if failed
        """
        try:
            motion_prompts = {
                'rotation': f"{concept} product slowly rotating 360 degrees on white background, smooth professional motion, studio lighting, e-commerce video",
                'zoom': f"{concept} product zoom in reveal, starting wide then close up on details, professional product video, clean background",
                'float': f"{concept} product floating and gently rotating in colorful abstract space, smooth motion, creative advertisement video"
            }
            
            prompt = motion_prompts.get(motion_type, motion_prompts['rotation'])
            
            print(f"🎬 Generating {motion_type} video...")
            
            # Generate video with Minimax
            output = replicate.run(
                "minimax/video-01",
                input={
                    "prompt": prompt,
                    "prompt_optimizer": True
                }
            )
            
            if output:
                print(f"✅ Video generated: {motion_type}")
                return output
            else:
                print(f"❌ Video generation failed")
                return None
                
        except Exception as e:
            print(f"❌ Error generating video: {e}")
            return None
    
    def generate_platform_specific_asset(
        self,
        transparent_mockup_path: str,
        concept: str,
        platform: str,
        output_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate social media asset optimized for specific platform.
        
        Args:
            transparent_mockup_path: Path to transparent PNG mockup
            concept: Product concept/description
            platform: Platform key (e.g., 'instagram_post', 'tiktok')
            output_path: Path to save output (optional)
            
        Returns:
            Path to generated asset or None if failed
        """
        if platform not in self.PLATFORM_DIMENSIONS:
            print(f"❌ Unknown platform: {platform}")
            print(f"   Available: {', '.join(self.PLATFORM_DIMENSIONS.keys())}")
            return None
        
        try:
            width, height = self.PLATFORM_DIMENSIONS[platform]
            
            print(f"📱 Generating {platform} asset ({width}x{height})...")
            
            # Platform-specific prompt adjustments
            platform_styles = {
                'instagram_post': 'modern instagram aesthetic, vibrant colors, eye-catching',
                'instagram_story': 'vertical story format, text space at top and bottom, bold design',
                'tiktok': 'vertical video style, dynamic composition, trending aesthetic',
                'youtube_thumbnail': 'bold text overlay space, attention-grabbing, high contrast',
                'pinterest': 'vertical pin format, inspirational mood, lifestyle aesthetic',
                'linkedin_post': 'professional business aesthetic, clean and corporate'
            }
            
            platform_style = platform_styles.get(platform, 'social media ready, modern, eye-catching')
            
            # Check if mockup exists
            if not Path(transparent_mockup_path).exists():
                print(f"⚠️ Mockup not found: {transparent_mockup_path}")
                return None
            
            # Load product mockup
            from io import BytesIO
            from PIL import ImageFilter, ImageDraw
            
            product = Image.open(transparent_mockup_path).convert('RGBA')
            
            # Create background by heavily blurring the product image
            # First, create a filled version (no transparency) for better blur effect
            background = Image.new('RGBA', (width, height), (255, 255, 255, 255))
            
            # Resize product to fill background (zoom in slightly for interesting crop)
            bg_product = product.copy()
            bg_product = bg_product.resize((width, height), Image.Resampling.LANCZOS)
            
            # Create a white background and paste the product
            bg_white = Image.new('RGB', (width, height), (255, 255, 255))
            bg_white.paste(bg_product, (0, 0), bg_product)
            
            # Apply heavy blur (40-60 radius for dreamy bokeh effect)
            background_blurred = bg_white.filter(ImageFilter.GaussianBlur(radius=50))
            
            # Convert back to RGBA
            background = background_blurred.convert('RGBA')
            
            # Prepare product for center placement
            # Resize product to fit nicely (60% of smallest dimension)
            max_product_size = int(min(width, height) * 0.6)
            product_display = product.copy()
            product_display.thumbnail((max_product_size, max_product_size), Image.Resampling.LANCZOS)
            
            # Create a shadow/frame effect around the product
            # Make a slightly larger version for the shadow
            shadow_size = 20  # pixels of shadow blur
            shadow_offset = (10, 10)  # slight offset for depth
            
            # Create shadow layer
            shadow = Image.new('RGBA', 
                             (product_display.width + shadow_size * 2, 
                              product_display.height + shadow_size * 2), 
                             (0, 0, 0, 0))
            
            # Draw a dark shape for shadow (using product alpha as mask)
            shadow_mask = product_display.split()[3]  # Get alpha channel
            shadow_layer = Image.new('RGBA', product_display.size, (0, 0, 0, 180))
            shadow_temp = Image.new('RGBA', shadow.size, (0, 0, 0, 0))
            shadow_temp.paste(shadow_layer, 
                            (shadow_size + shadow_offset[0], shadow_size + shadow_offset[1]), 
                            shadow_mask)
            
            # Blur the shadow
            shadow = shadow_temp.filter(ImageFilter.GaussianBlur(radius=15))
            
            # Calculate center positions
            shadow_x = (width - shadow.width) // 2
            shadow_y = (height - shadow.height) // 2
            product_x = (width - product_display.width) // 2
            product_y = (height - product_display.height) // 2
            
            # Composite layers: background -> shadow -> product
            background.paste(shadow, (shadow_x, shadow_y), shadow)
            background.paste(product_display, (product_x, product_y), product_display)
            
            # Convert to bytes
            output_buffer = BytesIO()
            background.save(output_buffer, format='PNG')
            image_data = output_buffer.getvalue()
            
            # Save final composite
            if not output_path:
                mockup_name = Path(transparent_mockup_path).stem
                output_path = str(Path(transparent_mockup_path).parent.parent / "social_media" / f"{mockup_name}_{platform}.png")
            
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'wb') as f:
                f.write(image_data)
            
            if Path(output_path).exists() and Path(output_path).stat().st_size > 0:
                print(f"✅ {platform} asset generated with product composite")
                return output_path
            
            return None
            
        except Exception as e:
            print(f"❌ Error generating {platform} asset: {e}")
            return None
    
    def generate_all_social_assets(
        self,
        transparent_mockup_path: str,
        concept: str,
        campaign_dir: Path,
        platforms: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        Generate social media assets for multiple platforms.
        
        Args:
            transparent_mockup_path: Path to transparent PNG mockup
            concept: Product concept/description
            campaign_dir: Campaign directory
            platforms: List of platform keys (None = all major platforms)
            
        Returns:
            Dict mapping platform to asset path
        """
        if platforms is None:
            platforms = [
                'instagram_post',
                'instagram_story',
                'tiktok',
                'facebook_post',
                'pinterest'
            ]
        
        # Ensure social media directory exists
        social_dir = Path(campaign_dir) / "social_media"
        social_dir.mkdir(parents=True, exist_ok=True)
        
        assets = {}
        
        for platform in platforms:
            output_path = str(social_dir / f"{Path(transparent_mockup_path).stem}_{platform}.png")
            
            result = self.generate_platform_specific_asset(
                transparent_mockup_path,
                concept,
                platform,
                output_path
            )
            
            if result:
                assets[platform] = result
        
        print(f"\n✅ Generated {len(assets)}/{len(platforms)} social media assets")
        return assets
    
    def generate_complete_campaign_content(
        self,
        transparent_mockup_path: str,
        concept: str,
        campaign_dir: Path,
        include_videos: bool = True,
        include_social: bool = True,
        num_scenes: int = 5
    ) -> Dict:
        """
        Generate all promotional content for a product campaign.
        
        Args:
            transparent_mockup_path: Path to transparent PNG mockup
            concept: Product concept/description
            campaign_dir: Campaign directory
            include_videos: Generate product videos
            include_social: Generate social media assets
            num_scenes: Number of lifestyle scenes
            
        Returns:
            Dict with 'scenes', 'videos', 'social_assets' keys
        """
        results = {
            'scenes': [],
            'videos': [],
            'social_assets': {}
        }
        
        print(f"\n🚀 Generating complete promotional content for: {concept}")
        
        # 1. Generate lifestyle scenes
        print(f"\n📸 Step 1/3: Generating {num_scenes} lifestyle scenes...")
        results['scenes'] = self.generate_all_lifestyle_scenes(
            transparent_mockup_path,
            concept,
            campaign_dir,
            num_scenes
        )
        
        # 2. Generate videos (if enabled)
        if include_videos:
            print(f"\n🎬 Step 2/3: Generating product videos...")
            for motion_type in ['rotation', 'zoom', 'float']:
                video_url = self.generate_product_video_text(concept, motion_type)
                if video_url:
                    results['videos'].append({
                        'type': motion_type,
                        'url': video_url
                    })
        else:
            print(f"\n⏭️  Step 2/3: Skipping videos")
        
        # 3. Generate social media assets (if enabled)
        if include_social:
            print(f"\n📱 Step 3/3: Generating social media assets...")
            results['social_assets'] = self.generate_all_social_assets(
                transparent_mockup_path,
                concept,
                campaign_dir
            )
        else:
            print(f"\n⏭️  Step 3/3: Skipping social media assets")
        
        # Save campaign content metadata
        self._save_content_metadata(campaign_dir, results)
        
        print(f"\n✅ Campaign content generation complete!")
        print(f"   - {len(results['scenes'])} lifestyle scenes")
        print(f"   - {len(results['videos'])} videos")
        print(f"   - {len(results['social_assets'])} social media assets")
        
        return results
    
    def _save_content_metadata(self, campaign_dir: Path, results: Dict) -> None:
        """Save content generation metadata to campaign directory."""
        try:
            metadata_file = Path(campaign_dir) / "promotional_content_metadata.json"
            
            metadata = {
                'generated_at': datetime.now().isoformat(),
                'total_scenes': len(results['scenes']),
                'total_videos': len(results['videos']),
                'total_social_assets': len(results['social_assets']),
                'scenes': results['scenes'],
                'videos': results['videos'],
                'social_assets': results['social_assets']
            }
            
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            print(f"💾 Saved content metadata")
            
        except Exception as e:
            print(f"⚠️ Failed to save metadata: {e}")


# Convenience functions
def generate_lifestyle_scenes(
    transparent_mockup_path: str,
    concept: str,
    campaign_dir: Path,
    num_scenes: int = 5
) -> List[Dict]:
    """
    Quick function to generate lifestyle scenes.
    
    Args:
        transparent_mockup_path: Path to transparent mockup
        concept: Product concept
        campaign_dir: Campaign directory
        num_scenes: Number of scenes to generate
        
    Returns:
        List of scene dicts
    """
    generator = ProductPromotionalContent()
    return generator.generate_all_lifestyle_scenes(
        transparent_mockup_path,
        concept,
        campaign_dir,
        num_scenes
    )


def generate_social_media_assets(
    transparent_mockup_path: str,
    concept: str,
    campaign_dir: Path,
    platforms: Optional[List[str]] = None
) -> Dict[str, str]:
    """
    Quick function to generate social media assets.
    
    Args:
        transparent_mockup_path: Path to transparent mockup
        concept: Product concept
        campaign_dir: Campaign directory
        platforms: List of platform keys
        
    Returns:
        Dict of platform to asset path
    """
    generator = ProductPromotionalContent()
    return generator.generate_all_social_assets(
        transparent_mockup_path,
        concept,
        campaign_dir,
        platforms
    )


# Example usage
if __name__ == "__main__":
    """
    Example: Generate promotional content for a product
    """
    
    from dotenv import load_dotenv
    load_dotenv()
    
    # Test parameters
    transparent_mockup = "test_mockup_transparent.png"
    concept = "Cute panda design t-shirt"
    campaign_dir = Path("./test_campaign")
    
    if Path(transparent_mockup).exists():
        print(f"🚀 Generating promotional content...")
        
        generator = ProductPromotionalContent()
        
        results = generator.generate_complete_campaign_content(
            transparent_mockup,
            concept,
            campaign_dir,
            include_videos=True,
            include_social=True,
            num_scenes=3  # Start with 3 for testing
        )
        
        print(f"\n✅ Complete!")
    else:
        print(f"❌ Test mockup not found: {transparent_mockup}")
        print("   Run background removal first to create a transparent mockup")
