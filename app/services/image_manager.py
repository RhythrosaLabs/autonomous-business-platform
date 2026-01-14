import os
import time
import io
import requests
from pathlib import Path
from typing import Tuple, Union
from PIL import Image

# Optional PyQt5 for GUI (not needed for web deployment)
try:
    from PyQt5.QtGui import QPixmap
    from PyQt5.QtCore import Qt
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False
    QPixmap = None

# Optional rembg for advanced background removal
try:
    from rembg import remove
    HAS_REMBG = True
except ImportError:
    HAS_REMBG = False

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
            # If pixel is close to white, make it transparent
            if item[0] > threshold and item[1] > threshold and item[2] > threshold:
                newData.append((255, 255, 255, 0))
            else:
                newData.append(item)
        
        image.putdata(newData)
        return image
    
    def download_and_process(self, image_url: str, product_id: str) -> str:
        """Download and process a product mockup image (remove background)"""
        try:
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            
            filename = f"{product_id}_{int(time.time())}.png"
            filepath = self.images_dir / filename
            
            image = Image.open(io.BytesIO(response.content))
            # Use rembg for robust background removal
            if HAS_REMBG:
                result = remove(image)
            else:
                # Fallback: use simple transparency method
                result = self._make_transparent(image)
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
            print(f"Error downloading/processing image: {e}")
            return ""
    
    def get_thumbnail(self, filepath: str, size: Tuple[int, int] = (150, 150)) -> Union[Image.Image, 'QPixmap', None]:
        """Get a thumbnail of an image (returns PIL Image for web, QPixmap for GUI)"""
        try:
            if HAS_PYQT5:
                # GUI mode - return QPixmap
                pixmap = QPixmap(filepath)
                return pixmap.scaled(size[0], size[1], Qt.KeepAspectRatio, Qt.SmoothTransformation)
            else:
                # Web mode - return PIL Image
                img = Image.open(filepath)
                img.thumbnail(size, Image.Resampling.LANCZOS)
                return img
        except Exception as e:
            print(f"Error creating thumbnail: {e}")
            if HAS_PYQT5:
                return QPixmap()
            else:
                return Image.new('RGBA', size, (0, 0, 0, 0))
    
    def get_recent_images(self, limit: int = 10):
        """Get list of recent images"""
        try:
            files = sorted(
                self.images_dir.glob("*.png"),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            return [str(f) for f in files[:limit]]
        except Exception:
            return []
