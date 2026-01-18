"""
Flux Static Ads Generator
Uses loolau/flux-static-ads model on Replicate to create professional static ads for social media.
This creates beautiful, branded advertising images from product mockups.
Includes PIL-based text overlay fallback for reliable text rendering.
"""
import os
import replicate
import requests
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime
import base64
import json
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

logger = logging.getLogger(__name__)


# ============ PIL TEXT OVERLAY SYSTEM ============
# Professional text overlays with modern fonts and effects

# Platform-specific emoji/symbol flare
PLATFORM_FLARE = {
    'instagram_post': {'symbols': ['✨', '🔥', '💫', '⚡'], 'use_emoji': True},
    'instagram_story': {'symbols': ['↑', '⬆️', '🔥', '✨'], 'use_emoji': True},
    'facebook_post': {'symbols': ['→', '✓', '★'], 'use_emoji': False},
    'twitter': {'symbols': ['🔥', '⚡', '✨', '💯'], 'use_emoji': True},
    'pinterest': {'symbols': ['♡', '✨', '📌'], 'use_emoji': True},
    'tiktok': {'symbols': ['🔥', '⚡', '✨', '💥'], 'use_emoji': True},
    'linkedin': {'symbols': ['→', '✓', '•'], 'use_emoji': False},
    'youtube_thumbnail': {'symbols': ['🔥', '⚡', '😱', '🎯'], 'use_emoji': True},
}

# Headline enhancers by style
HEADLINE_ENHANCERS = {
    'bold': {'prefix': '', 'suffix': ' 🔥', 'chance': 0.4},
    'minimal': {'prefix': '', 'suffix': '', 'chance': 0},
    'luxury': {'prefix': '✨ ', 'suffix': ' ✨', 'chance': 0.5},
    'playful': {'prefix': '', 'suffix': ' 💫', 'chance': 0.6},
    'tech': {'prefix': '⚡ ', 'suffix': '', 'chance': 0.4},
    'lifestyle': {'prefix': '', 'suffix': ' ✨', 'chance': 0.3},
    'nature': {'prefix': '🌿 ', 'suffix': '', 'chance': 0.3},
    'retro': {'prefix': '★ ', 'suffix': ' ★', 'chance': 0.4},
}


def get_system_font(style: str = 'bold', size: int = 48):
    """
    Get a modern, sleek system font. Prioritizes SF Pro, Avenir, and other modern fonts.
    Style can be: 'bold', 'medium', 'regular', 'light', 'thin'
    """
    # Map style aliases
    style_map = {
        'regular': 'medium',
        'normal': 'medium',
        'semibold': 'bold',
        'heavy': 'bold',
        'black': 'bold',
    }
    weight = style_map.get(style, style)
    
    # Modern font preferences - prioritize sleek, professional fonts
    font_paths = {
        'bold': [
            # SF Pro - Apple's modern system font (best choice)
            '/System/Library/Fonts/SFNS.ttf',
            '/Library/Fonts/SF-Pro-Display-Bold.otf',
            '/System/Library/Fonts/SFNSDisplay-Bold.otf',
            '/System/Library/Fonts/SFCompactDisplay-Bold.otf',
            # SF Pro Text (more legible at smaller sizes)
            '/Library/Fonts/SF-Pro-Text-Bold.otf',
            # Avenir - very clean and modern
            '/System/Library/Fonts/Avenir.ttc',
            '/Library/Fonts/Avenir-Black.ttf',
            '/Library/Fonts/Avenir Next.ttc',
            # Helvetica Neue - classic and clean
            '/System/Library/Fonts/HelveticaNeue.ttc',
            # Futura - modern geometric
            '/Library/Fonts/Futura.ttc',
            # Fallbacks
            '/System/Library/Fonts/Helvetica.ttc',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        ],
        'medium': [
            '/Library/Fonts/SF-Pro-Display-Medium.otf',
            '/Library/Fonts/SF-Pro-Text-Medium.otf',
            '/System/Library/Fonts/SFNSDisplay-Medium.otf',
            '/System/Library/Fonts/Avenir.ttc',
            '/Library/Fonts/Avenir Next.ttc',
            '/System/Library/Fonts/HelveticaNeue.ttc',
            '/System/Library/Fonts/Helvetica.ttc',
            '/System/Library/Fonts/SFNS.ttf',
        ],
        'light': [
            '/Library/Fonts/SF-Pro-Display-Light.otf',
            '/Library/Fonts/SF-Pro-Text-Light.otf',
            '/System/Library/Fonts/SFNSDisplay-Light.otf',
            '/System/Library/Fonts/Avenir.ttc',
            '/Library/Fonts/Avenir Next.ttc',
            '/System/Library/Fonts/HelveticaNeue.ttc',
            '/System/Library/Fonts/SFNS.ttf',
        ],
        'thin': [
            '/Library/Fonts/SF-Pro-Display-Thin.otf',
            '/Library/Fonts/SF-Pro-Display-Ultralight.otf',
            '/System/Library/Fonts/SFNSDisplay-Thin.otf',
            '/System/Library/Fonts/Avenir.ttc',
            '/System/Library/Fonts/HelveticaNeue.ttc',
            '/System/Library/Fonts/SFNS.ttf',
        ]
    }
    
    paths_to_try = font_paths.get(weight, font_paths['medium'])
    
    for font_path in paths_to_try:
        try:
            if os.path.exists(font_path):
                return ImageFont.truetype(font_path, size)
        except Exception:
            continue
    
    # Ultimate fallback
    try:
        return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
    except:
        return ImageFont.load_default()


def add_glow_effect(draw, text: str, position: tuple, font, color: str, glow_color: Optional[str] = None, glow_radius: int = 3):
    """
    Draw text with a subtle glow effect for that modern, premium look.
    """
    x, y = position
    
    if glow_color is None:
        # Use a lighter version of the text color for glow
        glow_color = color
    
    # Draw glow layers (multiple passes with decreasing opacity)
    for offset in range(glow_radius, 0, -1):
        alpha = int(60 / offset)  # Decreasing opacity
        glow_alpha = f"{glow_color}{alpha:02x}" if len(glow_color) == 7 else glow_color
        
        # Draw in all directions for glow effect
        for dx in [-offset, 0, offset]:
            for dy in [-offset, 0, offset]:
                if dx != 0 or dy != 0:
                    try:
                        draw.text((x + dx, y + dy), text, font=font, fill=glow_color)
                    except:
                        pass
    
    # Draw main text on top
    draw.text((x, y), text, font=font, fill=color)


def add_text_with_effects(
    draw,
    text: str,
    position: tuple,
    font,
    color: str,
    effect: str = 'shadow',
    shadow_color: str = '#000000',
    shadow_offset: int = 3,
    glow_color: Optional[str] = None
):
    """
    Draw text with various effects: shadow, glow, outline, or clean.
    """
    x, y = position
    
    if effect == 'shadow':
        # Soft shadow for depth
        for i in range(shadow_offset, 0, -1):
            alpha = int(80 / i)
            draw.text((x + i, y + i), text, font=font, fill=shadow_color)
        draw.text((x, y), text, font=font, fill=color)
        
    elif effect == 'glow':
        add_glow_effect(draw, text, position, font, color, glow_color, glow_radius=4)
        
    elif effect == 'outline':
        # Outline effect
        outline_color = shadow_color
        for dx in [-2, -1, 0, 1, 2]:
            for dy in [-2, -1, 0, 1, 2]:
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
        draw.text((x, y), text, font=font, fill=color)
        
    elif effect == 'double':
        # Double shadow for dramatic effect
        draw.text((x + 4, y + 4), text, font=font, fill='#00000066')
        draw.text((x + 2, y + 2), text, font=font, fill='#000000aa')
        draw.text((x, y), text, font=font, fill=color)
        
    else:  # clean - no effects
        draw.text((x, y), text, font=font, fill=color)


def enhance_headline_with_flair(headline: str, platform: str, style: str) -> str:
    """
    Optionally add emoji/symbol flair to headlines based on platform and style.
    """
    import random
    
    platform_info = PLATFORM_FLARE.get(platform, {'symbols': [], 'use_emoji': False})
    style_info = HEADLINE_ENHANCERS.get(style, {'prefix': '', 'suffix': '', 'chance': 0})
    
    # Only add flair sometimes, not always
    if random.random() > style_info.get('chance', 0.3):
        return headline
    
    if not platform_info.get('use_emoji', False):
        return headline
    
    # Add prefix or suffix based on style
    prefix = style_info.get('prefix', '')
    suffix = style_info.get('suffix', '')
    
    return f"{prefix}{headline}{suffix}"


def add_text_overlay_to_image(
    image_path: str,
    output_path: str,
    headline: str,
    tagline: str = "",
    cta: str = "",
    price: str = "",
    brand_name: str = "",
    platform: str = "instagram_post",
    style: str = "bold",
    brand_colors: Optional[Dict[str, str]] = None
) -> Optional[str]:
    """
    Add professional text overlay to an image with modern fonts and effects.
    
    Features:
    - Modern, sleek fonts (SF Pro, Avenir, etc.)
    - Subtle glow and shadow effects
    - Optional emoji/symbol flair
    - Platform-optimized layouts
    - Brand color integration
    
    Args:
        image_path: Path to the base image
        output_path: Where to save the result
        headline: Main headline text
        tagline: Secondary tagline
        cta: Call-to-action text
        price: Price text (e.g., "$24.99")
        brand_name: Brand name to display
        platform: Target platform for layout optimization
        style: Visual style (bold, minimal, luxury, playful)
        brand_colors: Optional dict with 'primary', 'secondary', 'accent' colors
        
    Returns:
        Path to the output image, or None if failed
    """
    try:
        # Load the image
        img = Image.open(image_path).convert('RGBA')
        width, height = img.size
        
        # Create a drawing context
        draw = ImageDraw.Draw(img)
        
        # Default brand colors if not provided
        if brand_colors is None:
            brand_colors = {
                'primary': '#ffffff',      # White text
                'secondary': '#f0f0f0',    # Light gray
                'accent': '#ff6b35',       # Orange accent for CTA
                'background': '#000000',   # Black for overlays
            }
        
        # Parse colors
        text_color = brand_colors.get('primary', '#ffffff')
        accent_color = brand_colors.get('accent', '#ff6b35')
        bg_color = brand_colors.get('background', '#000000')
        
        # Calculate text sizes based on image dimensions
        headline_size = int(min(width, height) * 0.08)  # 8% of smallest dimension
        tagline_size = int(headline_size * 0.5)
        cta_size = int(headline_size * 0.6)
        price_size = int(headline_size * 0.7)
        brand_size = int(headline_size * 0.4)
        
        # Get fonts
        headline_font = get_system_font('bold', headline_size)
        tagline_font = get_system_font('regular', tagline_size)
        cta_font = get_system_font('bold', cta_size)
        price_font = get_system_font('bold', price_size)
        brand_font = get_system_font('light', brand_size)
        
        # Platform-specific layouts
        layouts = {
            'instagram_post': {
                'headline_y': 0.12,      # 12% from top
                'tagline_y': 0.22,       # Below headline
                'price_y': 0.75,         # 75% down
                'cta_y': 0.85,           # 85% down
                'brand_y': 0.95,         # Bottom
                'align': 'center'
            },
            'instagram_story': {
                'headline_y': 0.15,
                'tagline_y': 0.22,
                'price_y': 0.78,
                'cta_y': 0.85,
                'brand_y': 0.93,
                'align': 'center'
            },
            'facebook_post': {
                'headline_y': 0.08,
                'tagline_y': 0.16,
                'price_y': 0.80,
                'cta_y': 0.88,
                'brand_y': 0.95,
                'align': 'center'
            },
            'twitter': {
                'headline_y': 0.10,
                'tagline_y': 0.20,
                'price_y': 0.78,
                'cta_y': 0.88,
                'brand_y': 0.95,
                'align': 'center'
            },
            'pinterest': {
                'headline_y': 0.08,
                'tagline_y': 0.14,
                'price_y': 0.85,
                'cta_y': 0.90,
                'brand_y': 0.96,
                'align': 'center'
            },
            'tiktok': {
                'headline_y': 0.10,
                'tagline_y': 0.16,
                'price_y': 0.82,
                'cta_y': 0.88,
                'brand_y': 0.94,
                'align': 'center'
            }
        }
        
        layout = layouts.get(platform, layouts['instagram_post'])
        
        # Add semi-transparent overlays for text readability
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # Top gradient overlay for headline
        if headline:
            gradient_height = int(height * 0.35)
            for i in range(gradient_height):
                alpha = int(180 * (1 - i / gradient_height))  # Fade from 180 to 0
                overlay_draw.line([(0, i), (width, i)], fill=(0, 0, 0, alpha))
        
        # Bottom gradient overlay for CTA/price
        if cta or price:
            gradient_height = int(height * 0.30)
            for i in range(gradient_height):
                y = height - gradient_height + i
                alpha = int(180 * (i / gradient_height))  # Fade from 0 to 180
                overlay_draw.line([(0, y), (width, y)], fill=(0, 0, 0, alpha))
        
        # Composite the overlay
        img = Image.alpha_composite(img, overlay)
        draw = ImageDraw.Draw(img)
        
        # Determine visual effect style based on platform
        effect_map = {
            'instagram_post': 'glow',
            'instagram_story': 'glow',
            'facebook_post': 'shadow',
            'twitter': 'glow',
            'pinterest': 'glow',
            'tiktok': 'glow',
            'linkedin': 'shadow',
            'youtube_thumbnail': 'double'
        }
        text_effect = effect_map.get(platform, 'shadow')
        
        def draw_text_centered(text: str, font, y_ratio: float, color: str, effect: str = 'shadow'):
            """Draw text centered with modern effects (glow, shadow, etc). Auto-wraps if text exceeds 85% of image width."""
            if not text:
                return
            
            # Get text bounding box
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Smart text wrapping: if text exceeds 85% of width, wrap to multiple lines
            max_width = int(width * 0.85)  # Use 85% of image width as max
            
            if text_width > max_width:
                # Split text into words and wrap
                words = text.split()
                lines = []
                current_line = []
                
                for word in words:
                    test_line = ' '.join(current_line + [word])
                    test_bbox = draw.textbbox((0, 0), test_line, font=font)
                    test_width = test_bbox[2] - test_bbox[0]
                    
                    if test_width <= max_width:
                        current_line.append(word)
                    else:
                        if current_line:
                            lines.append(' '.join(current_line))
                            current_line = [word]
                        else:
                            # Single word is too long - add it anyway
                            lines.append(word)
                
                if current_line:
                    lines.append(' '.join(current_line))
                
                # Draw each line centered
                total_height = len(lines) * text_height + (len(lines) - 1) * int(text_height * 0.2)  # 20% line spacing
                start_y = int(height * y_ratio) - total_height // 2
                
                for i, line in enumerate(lines):
                    line_bbox = draw.textbbox((0, 0), line, font=font)
                    line_width = line_bbox[2] - line_bbox[0]
                    x = (width - line_width) // 2
                    y = start_y + i * int(text_height * 1.2)
                    
                    add_text_with_effects(
                        draw, 
                        line, 
                        (x, y), 
                        font, 
                        color, 
                        effect=effect,
                        shadow_color='#000000',
                        shadow_offset=max(2, int(text_height * 0.06)),
                        glow_color=color
                    )
            else:
                # Text fits - draw normally
                x = (width - text_width) // 2
                y = int(height * y_ratio)
                
                add_text_with_effects(
                    draw, 
                    text, 
                    (x, y), 
                    font, 
                    color, 
                    effect=effect,
                    shadow_color='#000000',
                    shadow_offset=max(2, int(text_height * 0.06)),
                    glow_color=color
                )
        
        def draw_cta_button(text: str, y_ratio: float):
            """Draw a modern CTA button with glow effect."""
            if not text:
                return
            
            bbox = draw.textbbox((0, 0), text, font=cta_font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            padding_x = int(text_width * 0.5)
            padding_y = int(text_height * 0.6)
            
            button_width = text_width + padding_x * 2
            button_height = text_height + padding_y * 2
            
            x = (width - button_width) // 2
            y = int(height * y_ratio)
            
            # Draw subtle button shadow for depth
            shadow_offset = 4
            shadow_rect = [x + shadow_offset, y + shadow_offset, x + button_width + shadow_offset, y + button_height + shadow_offset]
            draw.rounded_rectangle(shadow_rect, radius=int(button_height * 0.35), fill='#00000066')
            
            # Draw button background with rounded corners
            button_rect = [x, y, x + button_width, y + button_height]
            draw.rounded_rectangle(button_rect, radius=int(button_height * 0.35), fill=accent_color)
            
            # Draw button text (white with subtle shadow)
            text_x = x + padding_x
            text_y = y + padding_y
            draw.text((text_x + 1, text_y + 1), text, font=cta_font, fill='#00000044')
            draw.text((text_x, text_y), text, font=cta_font, fill='#ffffff')
        
        # Enhance headline with optional flair based on style/platform
        enhanced_headline = headline
        if headline:
            enhanced_headline = enhance_headline_with_flair(headline, platform, style)
        
        # Draw all text elements with modern effects
        if enhanced_headline:
            draw_text_centered(enhanced_headline.upper(), headline_font, layout['headline_y'], text_color, effect=text_effect)
        
        if tagline:
            # Tagline gets a softer effect
            tagline_effect = 'shadow' if text_effect == 'double' else text_effect
            draw_text_centered(tagline, tagline_font, layout['tagline_y'], brand_colors.get('secondary', '#e0e0e0'), effect=tagline_effect)
        
        if price:
            # Price with glow effect to make it pop
            draw_text_centered(price, price_font, layout['price_y'], accent_color, effect='glow')
        
        if cta:
            draw_cta_button(cta, layout['cta_y'])
        
        if brand_name:
            # Brand name - subtle, clean appearance
            draw_text_centered(brand_name, brand_font, layout['brand_y'], brand_colors.get('secondary', '#a0a0a0'), effect='clean')
        
        # Save the result
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        img.convert('RGB').save(output_path, 'PNG', quality=95)
        
        if Path(output_path).exists():
            logger.info(f"✅ PIL text overlay applied: {output_path}")
            return output_path
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Failed to add text overlay: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def create_social_ad_with_text(
    product_image_path: str,
    output_path: str,
    platform: str,
    product_concept: str,
    price: Optional[float] = None,
    brand_name: Optional[str] = None,
    style: str = "bold",
    brand_colors: Optional[Dict[str, str]] = None
) -> Optional[str]:
    """
    Create a complete social media ad with text overlay.
    
    This crops/resizes the product image to the platform dimensions,
    then adds professional text overlays.
    """
    try:
        # Get platform config
        platform_config = PLATFORM_CONFIGS.get(platform, PLATFORM_CONFIGS['instagram_post'])
        target_width = platform_config['width']
        target_height = platform_config['height']
        
        # Load and resize/crop the product image
        img = Image.open(product_image_path).convert('RGBA')
        
        # Calculate crop/resize to fill the target dimensions
        img_ratio = img.width / img.height
        target_ratio = target_width / target_height
        
        if img_ratio > target_ratio:
            # Image is wider - crop width
            new_height = img.height
            new_width = int(new_height * target_ratio)
            left = (img.width - new_width) // 2
            img = img.crop((left, 0, left + new_width, new_height))
        else:
            # Image is taller - crop height
            new_width = img.width
            new_height = int(new_width / target_ratio)
            top = (img.height - new_height) // 2
            img = img.crop((0, top, new_width, top + new_height))
        
        # Resize to target dimensions
        img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
        
        # Save the resized image temporarily
        temp_path = output_path.replace('.png', '_temp.png')
        img.convert('RGB').save(temp_path, 'PNG')
        
        # Generate ad copy
        ad_copy = generate_ad_copy_with_ai(
            product_description=product_concept,
            platform=platform,
            style=style,
            price=price,
            brand_name=brand_name
        )
        
        # Add text overlay
        result = add_text_overlay_to_image(
            image_path=temp_path,
            output_path=output_path,
            headline=ad_copy.get('headline', 'Shop Now'),
            tagline=ad_copy.get('tagline', ''),
            cta=ad_copy.get('cta', 'Get Yours'),
            price=ad_copy.get('price_text', ''),
            brand_name=brand_name or '',
            platform=platform,
            style=style,
            brand_colors=brand_colors
        )
        
        # Clean up temp file
        try:
            os.remove(temp_path)
        except:
            pass
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Failed to create social ad: {e}")
        return None

# Platform-specific configurations for static ads
PLATFORM_CONFIGS = {
    'instagram_post': {
        'aspect_ratio': '1:1',
        'width': 1080,
        'height': 1080,
        'style_hint': 'Instagram feed post, modern lifestyle aesthetic, vibrant colors, scroll-stopping visual, clean composition, professional product photography',
        'megapixels': '1'
    },
    'instagram_story': {
        'aspect_ratio': '9:16',
        'width': 1080,
        'height': 1920,
        'style_hint': 'Instagram story, vertical format with text space, bold and eye-catching, swipe-up friendly, trendy aesthetic',
        'megapixels': '1'
    },
    'facebook_post': {
        'aspect_ratio': '4:5',
        'width': 1080,
        'height': 1350,
        'style_hint': 'Facebook ad, engaging lifestyle scene, professional lighting, clean product placement, shareable content',
        'megapixels': '1'
    },
    'pinterest': {
        'aspect_ratio': '2:3',
        'width': 1000,
        'height': 1500,
        'style_hint': 'Pinterest pin, inspirational mood board aesthetic, vertical lifestyle image, pinnable quality, dreamy atmosphere',
        'megapixels': '1'
    },
    'tiktok': {
        'aspect_ratio': '9:16',
        'width': 1080,
        'height': 1920,
        'style_hint': 'TikTok video thumbnail, vertical dynamic composition, trending Gen-Z aesthetic, bold colors, attention-grabbing',
        'megapixels': '1'
    },
    'twitter': {
        'aspect_ratio': '16:9',
        'width': 1200,
        'height': 675,
        'style_hint': 'Twitter/X post image, horizontal format, clean and shareable, professional brand image, eye-catching design',
        'megapixels': '1'
    },
    'linkedin': {
        'aspect_ratio': '4:3',
        'width': 1200,
        'height': 900,
        'style_hint': 'LinkedIn professional post, corporate aesthetic, clean business imagery, thought leadership visual, polished look',
        'megapixels': '1'
    },
    'youtube_thumbnail': {
        'aspect_ratio': '16:9',
        'width': 1280,
        'height': 720,
        'style_hint': 'YouTube thumbnail, high contrast, attention-grabbing, bold composition, click-worthy visual, dramatic lighting',
        'megapixels': '1'
    }
}

# Ad style templates for different vibes
AD_STYLE_TEMPLATES = {
    'minimal': 'minimalist clean design, lots of white space, subtle shadows, elegant typography space, premium feel',
    'bold': 'bold vibrant colors, high contrast, dynamic composition, energetic and exciting, eye-catching design',
    'lifestyle': 'lifestyle photography style, natural lighting, authentic scene, product in use, aspirational mood',
    'luxury': 'luxury premium aesthetic, dark moody background, elegant lighting, sophisticated, high-end feel',
    'playful': 'fun colorful design, playful composition, bright cheerful colors, friendly and approachable',
    'tech': 'sleek tech aesthetic, futuristic vibes, clean lines, modern minimalist, innovative feel',
    'nature': 'natural organic aesthetic, earth tones, sustainable vibes, eco-friendly feel, botanical elements',
    'retro': 'retro vintage aesthetic, nostalgic colors, 70s/80s inspired, warm tones, throwback design'
}

# Ad copy templates for different platforms and styles
AD_COPY_TEMPLATES = {
    'instagram_post': {
        'headlines': [
            "New Drop 🔥", "Must Have ✨", "Shop Now 💫", "Trending 📈", 
            "Limited Edition 🎯", "Best Seller 🏆", "Fan Favorite ❤️"
        ],
        'ctas': ["Shop Now →", "Get Yours", "Link in Bio", "Tap to Shop", "Order Today"]
    },
    'instagram_story': {
        'headlines': ["SWIPE UP ↑", "NEW!", "HOT DROP", "LIMITED TIME", "JUST DROPPED"],
        'ctas': ["Swipe Up", "Shop Now", "See More", "Tap Here"]
    },
    'facebook_post': {
        'headlines': ["Now Available!", "Introducing:", "New Arrival", "Just In", "Don't Miss Out"],
        'ctas': ["Shop Now", "Learn More", "Order Today", "Get Started"]
    },
    'pinterest': {
        'headlines': ["Pin-Worthy ✨", "Dream Item", "Add to Cart", "Wishlist Worthy", "Style Goals"],
        'ctas': ["Shop the Look", "Get the Details", "Find It Here"]
    },
    'tiktok': {
        'headlines': ["VIRAL 🔥", "POV:", "That Girl Era", "Main Character Energy", "Core Aesthetic"],
        'ctas': ["Link in Bio", "Comment for Link", "Shop TikTok"]
    },
    'twitter': {
        'headlines': ["Just dropped:", "NEW:", "PSA:", "Hot take:", "Finally:"],
        'ctas': ["Shop now 🔗", "Link below ⬇️", "Get yours →"]
    },
    'linkedin': {
        'headlines': ["Launching Today", "Introducing Our Latest", "Innovation Spotlight", "New Release"],
        'ctas': ["Learn More", "Explore Now", "Visit Our Site"]
    },
    'youtube_thumbnail': {
        'headlines': ["UNBOXING", "REVIEW", "MUST SEE", "HONEST TAKE", "BEST PRODUCT"],
        'ctas': ["Watch Now", "Full Review", "Subscribe"]
    }
}

# Pricing display templates
PRICE_DISPLAY_TEMPLATES = [
    "Only ${price}",
    "${price}",
    "Starting at ${price}",
    "Now ${price}",
    "Just ${price}",
    "From ${price}"
]


def generate_ad_copy_with_ai(
    product_description: str,
    platform: str,
    style: str,
    price: Optional[float] = None,
    brand_name: Optional[str] = None
) -> Dict[str, str]:
    """
    Generate compelling ad copy using AI for the specific platform and style.
    
    Returns dict with: headline, tagline, cta, price_text
    """
    import random
    
    # Get platform-specific templates
    platform_templates = AD_COPY_TEMPLATES.get(platform, AD_COPY_TEMPLATES['instagram_post'])
    
    # Try to use Replicate for smart copy generation
    try:
        import replicate
        
        copy_prompt = f"""Generate compelling advertising copy for this product:
Product: {product_description}
Platform: {platform}
Style: {style}
{"Brand: " + brand_name if brand_name else ""}

Create SHORT, punchy ad copy that would work overlaid on an image. Be creative and platform-appropriate.
Return ONLY a JSON object (no other text):
{{
    "headline": "5 words max, attention-grabbing",
    "tagline": "8 words max, benefit-focused",
    "cta": "3 words max, action word"
}}"""

        output = replicate.run(
            "meta/meta-llama-3-8b-instruct",
            input={
                "prompt": copy_prompt,
                "max_tokens": 150,
                "temperature": 0.8
            }
        )
        
        response_text = "".join(output) if hasattr(output, '__iter__') else str(output)
        
        # Try to parse JSON from response
        import re
        json_match = re.search(r'\{[^}]+\}', response_text)
        if json_match:
            import json
            ad_copy = json.loads(json_match.group())
            
            # Add price if provided
            if price:
                price_template = random.choice(PRICE_DISPLAY_TEMPLATES)
                ad_copy['price_text'] = price_template.replace("${price}", f"${price:.2f}")
            else:
                ad_copy['price_text'] = ""
            
            return ad_copy
            
    except Exception as e:
        logger.warning(f"AI copy generation failed, using templates: {e}")
    
    # Fallback to template-based copy
    headline = random.choice(platform_templates['headlines'])
    cta = random.choice(platform_templates['ctas'])
    
    # Generate a simple tagline from the product description
    words = product_description.split()[:6]
    tagline = " ".join(words) if len(words) > 2 else product_description[:30]
    
    price_text = ""
    if price:
        price_template = random.choice(PRICE_DISPLAY_TEMPLATES)
        price_text = price_template.replace("${price}", f"${price:.2f}")
    
    return {
        'headline': headline,
        'tagline': tagline,
        'cta': cta,
        'price_text': price_text
    }


class FluxStaticAdsGenerator:
    """
    Generate professional static ads using Flux AI model.
    
    This replaces basic PIL compositing with AI-generated professional advertising images
    that are platform-optimized and brand-ready.
    """
    
    def __init__(self, api_token: Optional[str] = None):
        """
        Initialize the generator.
        
        Args:
            api_token: Replicate API token. Falls back to REPLICATE_API_TOKEN env var.
        """
        self.api_token = api_token or os.getenv('REPLICATE_API_TOKEN')
        if not self.api_token:
            raise ValueError("Replicate API token required. Set REPLICATE_API_TOKEN env var.")
        
        self.model = "loolau/flux-static-ads"
        self.model_version = "573274c01eb4b21b17c1c04b79e8f4b25932206e0404f17cf0e45001edf68bc5"
        
        # Set up replicate client
        os.environ['REPLICATE_API_TOKEN'] = self.api_token
        
        logger.info("✅ FluxStaticAdsGenerator initialized")
    
    def _build_text_overlay_prompt(
        self,
        headline: str,
        tagline: str,
        cta: str,
        price_text: str,
        brand_name: Optional[str],
        platform: str,
        style: str
    ) -> str:
        """
        Build prompt instructions for FLUX to render text on the advertisement.
        
        FLUX can render text when given explicit instructions about what text to display,
        where to place it, and what style to use.
        """
        import random
        
        # Text positioning based on platform
        position_styles = {
            'instagram_post': 'centered text layout, headline at top, CTA button at bottom',
            'instagram_story': 'vertical layout, large headline in upper third, swipe-up CTA at bottom',
            'facebook_post': 'headline prominently displayed, text on left or right side',
            'pinterest': 'vertical pin layout, text overlay on lower portion',
            'tiktok': 'bold centered text, TikTok-style captions, vertical format',
            'twitter': 'clean horizontal layout, text on one side',
            'linkedin': 'professional centered text, corporate style typography',
            'youtube_thumbnail': 'large bold text, high contrast, thumbnail style'
        }
        
        # Font style based on ad style
        font_styles = {
            'minimal': 'clean sans-serif typography, thin elegant fonts, subtle text',
            'bold': 'bold heavy fonts, uppercase text, high contrast letters, impactful typography',
            'lifestyle': 'modern sans-serif, clean readable fonts, lifestyle magazine style',
            'luxury': 'elegant serif fonts, gold or white text, premium typography',
            'playful': 'fun rounded fonts, colorful text, friendly typography',
            'tech': 'futuristic fonts, sleek modern typography, tech-style text',
            'nature': 'organic handwritten style, natural earth-toned text',
            'retro': 'vintage typography, retro fonts, nostalgic lettering style'
        }
        
        position = position_styles.get(platform, position_styles['instagram_post'])
        font_style = font_styles.get(style, font_styles['lifestyle'])
        
        # Build the text overlay instructions
        text_elements = []
        
        if headline:
            text_elements.append(f'Large headline text reading exactly "{headline}"')
        
        if tagline:
            text_elements.append(f'Tagline text reading "{tagline}"')
        
        if price_text:
            text_elements.append(f'Price displayed as "{price_text}" in prominent text')
        
        if cta:
            text_elements.append(f'Call-to-action button or text saying "{cta}"')
        
        if brand_name:
            text_elements.append(f'Brand name "{brand_name}" displayed elegantly')
        
        text_list = ". ".join(text_elements)
        
        return f"""TEXT OVERLAY REQUIREMENTS:
{text_list}.

Typography: {font_style}
Layout: {position}

The text must be clearly legible, professionally styled, and integrated beautifully into the advertisement design. Text should have good contrast against the background. This is a professional marketing advertisement with visible promotional text."""
    
    def _encode_image_to_uri(self, image_path: str) -> str:
        """Convert local image to data URI for Replicate API."""
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        # Determine mime type
        suffix = Path(image_path).suffix.lower()
        mime_type = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.webp': 'image/webp'
        }.get(suffix, 'image/png')
        
        encoded = base64.b64encode(image_data).decode('utf-8')
        return f"data:{mime_type};base64,{encoded}"
    
    def _upload_image_to_replicate(self, image_path: str) -> str:
        """
        Upload image to a temporary hosting service for Replicate.
        Uses Replicate's file upload endpoint.
        """
        try:
            # Read the image
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # Upload to Replicate's file hosting
            response = requests.post(
                "https://api.replicate.com/v1/files",
                headers={
                    "Authorization": f"Token {self.api_token}"
                },
                files={
                    "file": (Path(image_path).name, image_data)
                }
            )
            
            if response.status_code == 201:
                result = response.json()
                return result.get('urls', {}).get('get', '')
            else:
                logger.warning(f"File upload failed, using data URI fallback: {response.status_code}")
                return self._encode_image_to_uri(image_path)
                
        except Exception as e:
            logger.warning(f"Upload failed, using data URI: {e}")
            return self._encode_image_to_uri(image_path)
    
    def generate_static_ad(
        self,
        product_image_path: str,
        prompt: str,
        platform: str = 'instagram_post',
        ad_style: str = 'lifestyle',
        output_path: Optional[str] = None,
        guidance_scale: float = 3.5,
        num_inference_steps: int = 28,
        seed: Optional[int] = None,
        prompt_strength: float = 0.75,
        ad_copy: Optional[Dict[str, str]] = None,
        price: Optional[float] = None,
        brand_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate a professional static ad image WITH text overlays.
        
        Args:
            product_image_path: Path to the product mockup/image
            prompt: Description of the ad (product name, features, vibe)
            platform: Target platform (instagram_post, facebook_post, etc.)
            ad_style: Style template (minimal, bold, lifestyle, luxury, etc.)
            output_path: Where to save the generated ad
            guidance_scale: How closely to follow the prompt (1-10, default 3.5)
            num_inference_steps: Quality vs speed tradeoff (1-50, default 28)
            seed: Random seed for reproducibility
            prompt_strength: How much to transform the input image (0-1, default 0.75)
            ad_copy: Optional dict with 'headline', 'tagline', 'cta' text to render
            price: Optional price to display on ad
            brand_name: Optional brand name
            
        Returns:
            Path to generated ad image, or None if failed
        """
        try:
            # Get platform config
            platform_config = PLATFORM_CONFIGS.get(platform, PLATFORM_CONFIGS['instagram_post'])
            style_template = AD_STYLE_TEMPLATES.get(ad_style, AD_STYLE_TEMPLATES['lifestyle'])
            
            # Generate ad copy if not provided
            if ad_copy is None:
                ad_copy = generate_ad_copy_with_ai(
                    product_description=prompt,
                    platform=platform,
                    style=ad_style,
                    price=price,
                    brand_name=brand_name
                )
            
            # Extract copy elements
            headline = ad_copy.get('headline', 'Shop Now')
            tagline = ad_copy.get('tagline', '')
            cta = ad_copy.get('cta', 'Get Yours')
            price_text = ad_copy.get('price_text', '')
            if price and not price_text:
                price_text = f"${price:.2f}"
            
            # Build text overlay instructions for FLUX
            # FLUX can render text when explicitly told to include it
            text_instructions = self._build_text_overlay_prompt(
                headline=headline,
                tagline=tagline,
                cta=cta,
                price_text=price_text,
                brand_name=brand_name,
                platform=platform,
                style=ad_style
            )
            
            # Build the full prompt with text rendering instructions
            full_prompt = f"""Professional social media advertisement design.

{text_instructions}

Product: {prompt}
Style: {style_template}
Platform: {platform_config['style_hint']}

The advertisement should have bold, readable text overlaid on the image. The text should be clearly visible with good contrast. Professional advertising layout with the product as the focal point and promotional text positioned elegantly. High-end marketing material quality."""

            logger.info(f"📸 Generating {platform} static ad with {ad_style} style...")
            logger.info(f"   Headline: {headline}")
            logger.info(f"   CTA: {cta}")
            if price_text:
                logger.info(f"   Price: {price_text}")
            
            # Prepare the product image
            if not Path(product_image_path).exists():
                logger.error(f"Product image not found: {product_image_path}")
                return None
            
            # Upload image or convert to data URI
            image_uri = self._upload_image_to_replicate(product_image_path)
            
            # Build input parameters
            input_params = {
                "prompt": full_prompt,
                "image": image_uri,
                "aspect_ratio": platform_config['aspect_ratio'],
                "guidance_scale": guidance_scale,
                "num_inference_steps": num_inference_steps,
                "prompt_strength": prompt_strength,
                "output_format": "png",
                "output_quality": 95,
                "model": "dev",
                "megapixels": platform_config['megapixels'],
                "go_fast": False,
                "disable_safety_checker": True
            }
            
            if seed is not None:
                input_params["seed"] = seed
            
            # Run the model
            logger.info(f"🚀 Running flux-static-ads model...")
            output = replicate.run(
                f"{self.model}:{self.model_version}",
                input=input_params
            )
            
            # Handle output (could be list or single URL)
            if isinstance(output, list):
                image_url = str(output[0]) if output else None
            else:
                image_url = str(output) if output else None
            
            if not image_url:
                logger.error("No output received from model")
                return None
            
            # Download the generated image
            logger.info(f"📥 Downloading generated ad...")
            response = requests.get(image_url)
            
            if response.status_code != 200:
                logger.error(f"Failed to download image: {response.status_code}")
                return None
            
            # Determine output path
            if not output_path:
                input_stem = Path(product_image_path).stem
                output_path = str(Path(product_image_path).parent / f"{input_stem}_{platform}_ad.png")
            
            # Ensure directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Save the image
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            if Path(output_path).exists() and Path(output_path).stat().st_size > 0:
                logger.info(f"✅ Static ad generated: {output_path}")
                return output_path
            else:
                logger.error("Generated file is empty or missing")
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to generate static ad: {e}")
            return None
    
    def generate_all_platform_ads(
        self,
        product_image_path: str,
        product_description: str,
        campaign_dir: Path,
        platforms: Optional[List[str]] = None,
        ad_style: str = 'lifestyle',
        brand_name: Optional[str] = None,
        price: Optional[float] = None
    ) -> Dict[str, str]:
        """
        Generate static ads for multiple platforms with unique ad copy for each.
        
        Args:
            product_image_path: Path to product mockup
            product_description: Product concept/description
            campaign_dir: Campaign directory for output
            platforms: List of platforms (None = all major platforms)
            ad_style: Visual style for all ads
            brand_name: Optional brand name to include in prompts
            price: Optional product price to display on ads
            
        Returns:
            Dict mapping platform to generated ad path
        """
        import random
        
        if platforms is None:
            platforms = ['instagram_post', 'instagram_story', 'facebook_post', 
                        'pinterest', 'tiktok', 'twitter']
        
        # Create social media directory
        social_dir = Path(campaign_dir) / "social_media_ads"
        social_dir.mkdir(parents=True, exist_ok=True)
        
        # Build base prompt
        if brand_name:
            base_prompt = f"{brand_name} - {product_description}"
        else:
            base_prompt = product_description
        
        # If no price provided, generate a reasonable one based on product type
        if price is None:
            # Try to infer price from product description
            desc_lower = product_description.lower()
            if 'poster' in desc_lower or 'print' in desc_lower:
                price = random.choice([18.99, 19.99, 24.99, 29.99])
            elif 'canvas' in desc_lower:
                price = random.choice([39.99, 49.99, 59.99])
            elif 'mug' in desc_lower or 'cup' in desc_lower:
                price = random.choice([14.99, 16.99, 19.99])
            elif 't-shirt' in desc_lower or 'tee' in desc_lower or 'shirt' in desc_lower:
                price = random.choice([24.99, 29.99, 34.99])
            elif 'hoodie' in desc_lower or 'sweatshirt' in desc_lower:
                price = random.choice([44.99, 49.99, 54.99])
            else:
                price = random.choice([19.99, 24.99, 29.99])
        
        generated_ads = {}
        total = len(platforms)
        
        for idx, platform in enumerate(platforms, 1):
            logger.info(f"\n📱 [{idx}/{total}] Generating {platform} ad with text overlay...")
            
            # Generate unique ad copy for this platform
            ad_copy = generate_ad_copy_with_ai(
                product_description=product_description,
                platform=platform,
                style=ad_style,
                price=price,
                brand_name=brand_name
            )
            
            output_path = str(social_dir / f"{Path(product_image_path).stem}_{platform}_ad.png")
            
            # Use different seeds for variety
            seed = (idx * 1234) + hash(platform) % 10000
            
            result = self.generate_static_ad(
                product_image_path=product_image_path,
                prompt=base_prompt,
                platform=platform,
                ad_style=ad_style,
                output_path=output_path,
                ad_copy=ad_copy,
                price=price,
                brand_name=brand_name,
                seed=seed
            )
            
            if result:
                generated_ads[platform] = result
                logger.info(f"   ✅ {platform} ad saved with text: {ad_copy.get('headline', '')}")
            else:
                logger.warning(f"   ⚠️ {platform} ad generation failed")
        
        logger.info(f"\n🎉 Generated {len(generated_ads)}/{total} platform ads with promotional text")
        return generated_ads
    
    def generate_ad_variations(
        self,
        product_image_path: str,
        product_description: str,
        output_dir: Path,
        num_variations: int = 3,
        platform: str = 'instagram_post',
        styles: Optional[List[str]] = None
    ) -> List[str]:
        """
        Generate multiple variations of an ad for A/B testing.
        
        Args:
            product_image_path: Path to product mockup
            product_description: Product description
            output_dir: Directory for output
            num_variations: Number of variations to generate
            platform: Target platform
            styles: List of styles to use (cycles through if fewer than num_variations)
            
        Returns:
            List of paths to generated variations
        """
        if styles is None:
            styles = ['lifestyle', 'minimal', 'bold', 'luxury']
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        variations = []
        
        for i in range(num_variations):
            style = styles[i % len(styles)]
            
            logger.info(f"\n🎨 Generating variation {i+1}/{num_variations} ({style} style)...")
            
            output_path = str(output_dir / f"ad_variation_{i+1}_{style}.png")
            
            result = self.generate_static_ad(
                product_image_path=product_image_path,
                prompt=product_description,
                platform=platform,
                ad_style=style,
                output_path=output_path,
                seed=i * 1000 + 42  # Different seed for each variation
            )
            
            if result:
                variations.append(result)
        
        logger.info(f"\n✅ Generated {len(variations)}/{num_variations} ad variations")
        return variations


def generate_social_ads_for_product(
    product_mockup_path: str,
    product_concept: str,
    campaign_dir: Path,
    platforms: Optional[List[str]] = None,
    style: str = 'lifestyle',
    brand_name: Optional[str] = None,
    price: Optional[float] = None,
    brand_colors: Optional[Dict[str, str]] = None,
    use_flux: bool = False  # Default to PIL for reliability
) -> Dict[str, str]:
    """
    Generate social media ads for a product WITH professional text overlays.
    
    Uses PIL-based text rendering for reliable, clean typography.
    Flux AI is available as an optional enhancement.
    
    Args:
        product_mockup_path: Path to the product mockup image
        product_concept: Description of the product
        campaign_dir: Campaign output directory
        platforms: List of platforms (None = default set)
        style: Visual style (minimal, bold, lifestyle, luxury, playful, tech, nature, retro)
        brand_name: Optional brand name
        price: Optional product price to display on ads
        brand_colors: Optional dict with 'primary', 'secondary', 'accent' colors
        use_flux: Whether to use Flux AI (default False for reliability)
        
    Returns:
        Dict mapping platform names to generated ad file paths
    """
    import random
    
    if platforms is None:
        platforms = ['instagram_post', 'instagram_story', 'facebook_post', 
                    'pinterest', 'tiktok', 'twitter']
    
    # Create social media directory
    social_dir = Path(campaign_dir) / "social_media_ads"
    social_dir.mkdir(parents=True, exist_ok=True)
    
    # If no price provided, generate a reasonable one
    if price is None:
        desc_lower = product_concept.lower()
        if 'poster' in desc_lower or 'print' in desc_lower:
            price = random.choice([18.99, 19.99, 24.99, 29.99])
        elif 'canvas' in desc_lower:
            price = random.choice([39.99, 49.99, 59.99])
        elif 'mug' in desc_lower or 'cup' in desc_lower:
            price = random.choice([14.99, 16.99, 19.99])
        elif 't-shirt' in desc_lower or 'tee' in desc_lower or 'shirt' in desc_lower:
            price = random.choice([24.99, 29.99, 34.99])
        elif 'hoodie' in desc_lower or 'sweatshirt' in desc_lower:
            price = random.choice([44.99, 49.99, 54.99])
        else:
            price = random.choice([19.99, 24.99, 29.99])
    
    generated_ads = {}
    total = len(platforms)
    
    for idx, platform in enumerate(platforms, 1):
        logger.info(f"\n📱 [{idx}/{total}] Creating {platform} ad with text overlay...")
        
        output_path = str(social_dir / f"{Path(product_mockup_path).stem}_{platform}_ad.png")
        
        # Use PIL-based text overlay (reliable and clean)
        result = create_social_ad_with_text(
            product_image_path=product_mockup_path,
            output_path=output_path,
            platform=platform,
            product_concept=product_concept,
            price=price,
            brand_name=brand_name,
            style=style,
            brand_colors=brand_colors
        )
        
        if result:
            generated_ads[platform] = result
            logger.info(f"   ✅ {platform} ad created with professional text overlay")
        else:
            logger.warning(f"   ⚠️ {platform} ad creation failed")
    
    logger.info(f"\n🎉 Generated {len(generated_ads)}/{total} professional social media ads")
    return generated_ads


# Quick test
if __name__ == "__main__":
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) < 3:
        print("Usage: python flux_static_ads_generator.py <product_image> <concept>")
        print("Example: python flux_static_ads_generator.py mockup.png 'Husky dog t-shirt design'")
        sys.exit(1)
    
    image_path = sys.argv[1]
    concept = sys.argv[2]
    
    generator = FluxStaticAdsGenerator()
    
    # Generate a single test ad
    result = generator.generate_static_ad(
        product_image_path=image_path,
        prompt=concept,
        platform='instagram_post',
        ad_style='lifestyle'
    )
    
    if result:
        print(f"\n✅ Generated ad: {result}")
    else:
        print("\n❌ Failed to generate ad")


# ============ INTELLIGENT PRICING ============

def calculate_smart_price(
    product_type: str,
    base_cost: float = 0.0,
    complexity: str = "medium",
    is_digital: bool = False,
) -> tuple:
    """
    Calculate intelligent pricing for products.
    
    Args:
        product_type: Type of product (poster, mug, t-shirt, ebook, course, etc.)
        base_cost: Base production cost if known
        complexity: Complexity level (low, medium, high, premium)
        is_digital: Whether this is a digital product
        
    Returns:
        Tuple of (price, pricing_rationale)
    """
    # Base price multipliers by complexity
    complexity_multipliers = {
        'low': 1.0,
        'medium': 1.3,
        'high': 1.6,
        'premium': 2.0,
    }
    
    # Digital product pricing
    digital_prices = {
        'ebook': {'base': 9.99, 'range': (4.99, 24.99)},
        'coloring_book': {'base': 7.99, 'range': (3.99, 14.99)},
        'coloring': {'base': 7.99, 'range': (3.99, 14.99)},
        'course': {'base': 29.99, 'range': (19.99, 99.99)},
        'comic': {'base': 4.99, 'range': (2.99, 12.99)},
        'template': {'base': 14.99, 'range': (9.99, 49.99)},
        'printable': {'base': 5.99, 'range': (2.99, 12.99)},
        'guide': {'base': 12.99, 'range': (7.99, 29.99)},
        'workbook': {'base': 11.99, 'range': (6.99, 24.99)},
    }
    
    # Physical product pricing (with typical margins)
    physical_prices = {
        'poster': {'base': 18.99, 'range': (12.99, 34.99)},
        'canvas': {'base': 39.99, 'range': (29.99, 79.99)},
        'framed': {'base': 34.99, 'range': (24.99, 59.99)},
        'mug': {'base': 14.99, 'range': (11.99, 19.99)},
        'shirt': {'base': 24.99, 'range': (19.99, 34.99)},
        't-shirt': {'base': 24.99, 'range': (19.99, 34.99)},
        'tshirt': {'base': 24.99, 'range': (19.99, 34.99)},
        'hoodie': {'base': 44.99, 'range': (39.99, 59.99)},
        'tote': {'base': 16.99, 'range': (14.99, 24.99)},
        'bag': {'base': 16.99, 'range': (14.99, 24.99)},
        'phone': {'base': 19.99, 'range': (14.99, 29.99)},
        'case': {'base': 19.99, 'range': (14.99, 29.99)},
        'notebook': {'base': 12.99, 'range': (9.99, 19.99)},
        'journal': {'base': 14.99, 'range': (11.99, 22.99)},
        'sticker': {'base': 4.99, 'range': (2.99, 7.99)},
        'pillow': {'base': 29.99, 'range': (24.99, 44.99)},
        'blanket': {'base': 49.99, 'range': (39.99, 79.99)},
        'print': {'base': 16.99, 'range': (9.99, 29.99)},
        'art': {'base': 24.99, 'range': (14.99, 49.99)},
        'wall': {'base': 29.99, 'range': (19.99, 59.99)},
    }
    
    # Determine pricing table
    pricing_table = digital_prices if is_digital else physical_prices
    
    # Normalize product type
    product_key = product_type.lower().replace(' ', '_').replace('-', '_')
    
    # Find matching product or use default
    price_info = None
    for key in pricing_table:
        if key in product_key or product_key in key:
            price_info = pricing_table[key]
            break
    
    if not price_info:
        # Default pricing
        if is_digital:
            price_info = {'base': 12.99, 'range': (4.99, 29.99)}
        else:
            price_info = {'base': 24.99, 'range': (14.99, 49.99)}
    
    # Calculate final price
    multiplier = complexity_multipliers.get(complexity, 1.3)
    calculated_price = price_info['base'] * multiplier
    
    # If we have a base cost, ensure margin
    if base_cost > 0:
        min_margin = 1.4  # 40% minimum margin
        cost_based_price = base_cost * min_margin * multiplier
        calculated_price = max(calculated_price, cost_based_price)
    
    # Clamp to range
    min_price, max_price = price_info['range']
    final_price = max(min_price, min(max_price, calculated_price))
    
    # Round to .99
    final_price = round(final_price) - 0.01
    if final_price < min_price:
        final_price = min_price
    
    # Generate rationale
    if is_digital:
        rationale = f"Digital product priced competitively for the {product_type} market"
    else:
        rationale = f"Physical product with healthy margin, positioned for the {complexity} tier"
    
    return final_price, rationale


# ============ HUMAN-LIKE DESCRIPTIONS ============

def generate_human_description(
    product_name: str,
    product_type: str,
    concept: str,
    target_audience: str = "",
    brand_voice: str = "friendly",
) -> dict:
    """
    Generate human-sounding product descriptions.
    Never mentions AI. Sounds like a small passionate startup.
    
    Returns dict with: title, short_description, full_description, tagline
    """
    import random
    
    # Voice adjustments
    voices = {
        'friendly': {
            'opener': ["We're so excited to share", "Here's something special", "You're going to love this"],
            'closer': ["Thanks for checking this out!", "We can't wait for you to try it.", "Made with love."],
            'tone': 'warm and approachable',
        },
        'professional': {
            'opener': ["Introducing", "Discover", "Presenting"],
            'closer': ["Quality you can trust.", "Excellence in every detail.", "Crafted for you."],
            'tone': 'polished and confident',
        },
        'playful': {
            'opener': ["Okay, hear us out...", "Ready for this?", "Warning: you might fall in love"],
            'closer': ["Go ahead, treat yourself!", "You deserve nice things.", "No regrets."],
            'tone': 'fun and energetic',
        },
        'minimal': {
            'opener': ["", "Simply", ""],
            'closer': ["", "That's it. That's the product.", ""],
            'tone': 'understated and elegant',
        },
        'chill': {
            'opener': ["Hey, so we made this thing", "Check this out", "Something cool for you"],
            'closer': ["Hope you like it.", "Let us know what you think.", "Enjoy!"],
            'tone': 'relaxed and casual',
        },
    }
    
    voice = voices.get(brand_voice, voices['friendly'])
    
    opener = random.choice(voice['opener'])
    closer = random.choice(voice['closer'])
    
    # Clean up concept for display
    concept_clean = concept.strip().rstrip('.')
    
    # Generate components
    title = f"{concept_clean.title()} {product_type.title()}"
    if len(title) > 60:
        # Shorten if too long
        words = concept_clean.split()
        if len(words) > 4:
            concept_short = ' '.join(words[:4])
        else:
            concept_short = concept_clean[:40]
        title = f"{concept_short.title()} {product_type.title()}"
    
    tagline_templates = [
        f"Where creativity meets style",
        f"Your new favorite {product_type.lower()}",
        f"Something different. Something special.",
        f"For those who appreciate the unique",
        f"Stand out from the crowd",
    ]
    tagline = random.choice(tagline_templates)
    
    # Short description - concise but warm
    audience_text = f"for {target_audience.lower()}" if target_audience else "for anyone who appreciates unique style"
    short_desc = f"{opener if opener else 'Introducing'} our {concept_clean.lower()} {product_type.lower()}. Perfect {audience_text}."
    
    # Full description - personable, NOT salesy
    full_desc_parts = []
    
    if opener:
        full_desc_parts.append(f"{opener} - this {product_type.lower()} featuring our {concept_clean.lower()} design.")
    else:
        full_desc_parts.append(f"A {product_type.lower()} featuring our {concept_clean.lower()} design.")
    
    full_desc_parts.append("")
    full_desc_parts.append(f"We put a lot of thought into this one. The design captures something special - it's the kind of thing that makes people ask 'where'd you get that?'")
    full_desc_parts.append("")
    
    if target_audience:
        full_desc_parts.append(f"Perfect for {target_audience.lower()}.")
    else:
        full_desc_parts.append("Whether you're treating yourself or looking for a thoughtful gift, this is it.")
    
    full_desc_parts.append("")
    if closer:
        full_desc_parts.append(closer)
    
    full_desc = '\n'.join(full_desc_parts)
    
    return {
        'title': title,
        'tagline': tagline,
        'short_description': short_desc,
        'full_description': full_desc,
    }


def generate_youtube_description(
    product_name: str,
    concept: str,
    shop_url: str = "",
    brand_name: str = "",
) -> str:
    """
    Generate a human, non-AI-sounding YouTube video description.
    """
    brand_text = brand_name if brand_name else "we"
    shop_text = f"\n\n🛒 Shop: {shop_url}" if shop_url else ""
    
    description = f"""Hey! Thanks for watching.

In this video, {brand_text}'re showing off our {concept.lower()} design. We're really proud of how this one turned out.

If you're vibing with it, the link's below. No pressure though - we just appreciate you taking the time to check it out.

Drop a comment if you have any questions or just want to say hi!
{shop_text}

---
#design #art #creative #shopsmall #supportsmallbusiness"""
    
    return description


def get_product_context_for_research(
    concept: str,
    product_type: str,
    brand_name: str = "",
) -> str:
    """
    Generate proper context string for AI research that includes both concept AND product.
    
    Example: Instead of "husky made of stars", returns "a poster featuring a husky made of stars design"
    
    Args:
        concept: The design concept (e.g., "husky made of stars")
        product_type: The product type (e.g., "poster", "t-shirt", "mug")
        brand_name: Optional brand name
        
    Returns:
        Full product context string for AI research
    """
    concept_clean = concept.strip().lower()
    product_clean = product_type.strip().lower()
    
    # Build the context
    if brand_name:
        context = f"a {product_clean} from {brand_name} featuring a {concept_clean} design"
    else:
        context = f"a {product_clean} featuring a {concept_clean} design"
    
    return context
