import os
import time
import io
import requests
from pathlib import Path
from typing import Tuple
from PIL import Image
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from rembg import remove

class ImageManager:
    """Manages image history and local storage"""
    
    def __init__(self):
        self.images_dir = Path.home() / ".pod_wizard_images"
        self.images_dir.mkdir(exist_ok=True)
    
    def _make_transparent(self, image: Image.Image, threshold: int = 240) -> Image.Image:
        """
        Convert white (or near-white) background to transparent.
        Only works for images with solid backgrounds.
        """
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        datas = image.getdata()
        newData = []
        for item in datas:
            # item is (R, G, B, A)
            if item[0] >= threshold and item[1] >= threshold and item[2] >= threshold:
                # Set alpha to 0 for near-white pixels
                newData.append((255, 255, 255, 0))
            else:
                newData.append(item)
        image.putdata(newData)
        return image

    def save_image(self, image_url: str, product_id: str) -> str:
        """Download and save image locally, ensuring transparent background"""
        try:
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            
            filename = f"{product_id}_{int(time.time())}.png"
            filepath = self.images_dir / filename
            
            image = Image.open(io.BytesIO(response.content))
            # Use rembg for robust background removal
            result = remove(image)
            # rembg may return a PIL Image, numpy array, or bytes
            if isinstance(result, Image.Image):
                result.save(filepath, "PNG")
            else:
                # Convert numpy array or bytes to PIL Image
                if hasattr(result, "shape"):
                    # numpy array
                    result = Image.fromarray(result)
                    result.save(filepath, "PNG")
                else:
                    # bytes
                    img = Image.open(io.BytesIO(result))
                    img.save(filepath, "PNG")
            
            return str(filepath)
        except Exception as e:
            print(f"Failed to save image: {e}")
            return ""
    
    def get_thumbnail(self, filepath: str, size: Tuple[int, int] = (150, 150)) -> QPixmap:
        """Get thumbnail for image"""
        try:
            pixmap = QPixmap(filepath)
            return pixmap.scaled(size[0], size[1], Qt.KeepAspectRatio, Qt.SmoothTransformation)
        except:
            return QPixmap()
