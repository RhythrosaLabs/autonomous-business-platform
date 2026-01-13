"""
Brand Template Generator
Creates simple, professional branded end cards for videos with dynamic text,
animations, and platform-specific formatting.
"""

import cv2
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import os
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Brand template directory
BRAND_DIR = Path(__file__).parent
TEMPLATES_DIR = BRAND_DIR / "templates"
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)


def generate_dynamic_cta_text(
    product_name: Optional[str] = None,
    campaign_type: str = "product",
    call_to_action: Optional[str] = None
) -> tuple:
    """
    Generate dynamic CTA text based on campaign data.
    
    Args:
        product_name: Name of the product
        campaign_type: Type of campaign (product, service, announcement)
        call_to_action: Custom CTA text
        
    Returns:
        Tuple of (line1, line2) text
    """
    if call_to_action:
        # Use custom CTA if provided
        lines = call_to_action.split('\n', 1)
        line1 = lines[0].strip()
        line2 = lines[1].strip() if len(lines) > 1 else "Visit our store today."
        return (line1, line2)
    
    # Generate based on product name and campaign type
    if product_name:
        if campaign_type == "launch":
            return (f"{product_name}", "Available Now!")
        elif campaign_type == "promo":
            return (f"{product_name}", "Limited Time Offer!")
        elif campaign_type == "announcement":
            return (f"Introducing {product_name}", "Order Today!")
        else:
            return (f"{product_name}", "Shop Now!")
    
    # Default fallback
    return ("Now Available.", "Visit our store today.")


def create_cta_end_card(
    line1: str = "Now Available.",
    line2: str = "Visit our store today.",
    output_path: str = None,
    width: int = 1920,
    height: int = 1080,
    bg_color: tuple = (0, 0, 0),  # Black
    text_color: tuple = (255, 255, 255),  # White
    font_size: int = 80,
    animated: bool = False,
    button_text: str = None,
    product_name: str = None
) -> str:
    """
    Create a simple, elegant CTA end card image.
    
    Args:
        line1: First line of text
        line2: Second line of text
        output_path: Where to save (auto-generates if None)
        width: Image width
        height: Image height
        bg_color: Background RGB color
        text_color: Text RGB color
        font_size: Font size in points
        
    Returns:
        Path to generated image
    """
    # Create image with PIL (better text rendering than OpenCV)
    img = Image.new('RGB', (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Try to use a modern, sleek font
    font_paths = [
        "/System/Library/Fonts/Supplemental/Arial.ttf",  # macOS
        "/System/Library/Fonts/SFNS.ttf",  # San Francisco (macOS)
        "/System/Library/Fonts/Helvetica.ttc",  # macOS
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
        "C:\\Windows\\Fonts\\arial.ttf",  # Windows
    ]
    
    font = None
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                font = ImageFont.truetype(font_path, font_size)
                break
            except:
                continue
    
    # Fallback to default font
    if font is None:
        font = ImageFont.load_default()
    
    # Get text bounding boxes
    bbox1 = draw.textbbox((0, 0), line1, font=font)
    bbox2 = draw.textbbox((0, 0), line2, font=font)
    
    text1_width = bbox1[2] - bbox1[0]
    text1_height = bbox1[3] - bbox1[1]
    text2_width = bbox2[2] - bbox2[0]
    text2_height = bbox2[3] - bbox2[1]
    
    # Calculate centered positions
    spacing = 30  # Space between lines
    total_height = text1_height + spacing + text2_height
    
    y_start = (height - total_height) // 2
    
    x1 = (width - text1_width) // 2
    y1 = y_start
    
    x2 = (width - text2_width) // 2
    y2 = y1 + text1_height + spacing
    
    # Draw text
    draw.text((x1, y1), line1, fill=text_color, font=font)
    draw.text((x2, y2), line2, fill=text_color, font=font)
    
    # Save image
    if output_path is None:
        output_path = str(TEMPLATES_DIR / "cta_end_card.png")
    
    img.save(output_path)
    print(f"✅ Created CTA end card: {output_path}")
    
    return output_path


def create_cta_video(
    image_path: str = None,
    duration: float = 3.5,
    output_path: str = None,
    fps: int = 30
) -> str:
    """
    Convert the CTA end card image to a static video clip.
    
    Args:
        image_path: Path to end card image (auto-generates if None)
        duration: Video duration in seconds
        output_path: Where to save video (auto-generates if None)
        fps: Frames per second
        
    Returns:
        Path to generated video
    """
    # Generate image if not provided
    if image_path is None or not os.path.exists(image_path):
        image_path = create_cta_end_card()
    
    # Read image
    img = cv2.imread(image_path)
    height, width = img.shape[:2]
    
    # Set output path
    if output_path is None:
        output_path = str(TEMPLATES_DIR / "cta_end_card_3.5s.mp4")
    
    # Create video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # Write static frames for duration
    total_frames = int(duration * fps)
    for _ in range(total_frames):
        out.write(img)
    
    out.release()
    print(f"✅ Created CTA video ({duration}s): {output_path}")
    
    return output_path


def get_or_create_cta_video(force_recreate: bool = False) -> str:
    """
    Get the CTA end card video, creating it if it doesn't exist.
    
    Args:
        force_recreate: Force regeneration even if exists
        
    Returns:
        Path to CTA video
    """
    video_path = TEMPLATES_DIR / "cta_end_card_3.5s.mp4"
    image_path = TEMPLATES_DIR / "cta_end_card.png"
    
    if force_recreate or not video_path.exists():
        # Generate both image and video
        create_cta_video(output_path=str(video_path))
    
    return str(video_path)


if __name__ == "__main__":
    # Generate the templates
    print("🎨 Generating brand templates...")
    
    # Create image
    img_path = create_cta_end_card()
    
    # Create video
    vid_path = create_cta_video(image_path=img_path)
    
    print("\n✅ Brand templates created!")
    print(f"   Image: {img_path}")
    print(f"   Video: {vid_path}")
    print("\nThese can now be used in video production.")
