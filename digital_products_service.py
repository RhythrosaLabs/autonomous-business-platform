"""
Digital Products Service
Handles selling digital downloads: audio files, software, graphic art, ebooks, etc.
Integrates with Shopify Digital Downloads app for automated delivery.
"""
import os
import json
import requests
import hashlib
import mimetypes
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime
import logging
import base64
from io import BytesIO

logger = logging.getLogger(__name__)

# Digital product categories and their configurations
DIGITAL_PRODUCT_TYPES = {
    'audio': {
        'name': 'Audio Files',
        'icon': '🎵',
        'extensions': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.aiff'],
        'max_size_mb': 500,
        'description_template': 'High-quality digital audio file. Instant download after purchase.',
        'tags': ['digital download', 'audio', 'music', 'sound']
    },
    'software': {
        'name': 'Software',
        'icon': '💻',
        'extensions': ['.zip', '.exe', '.dmg', '.app', '.msi', '.deb', '.rpm'],
        'max_size_mb': 2000,
        'description_template': 'Digital software download. Includes installation instructions.',
        'tags': ['digital download', 'software', 'application', 'tool']
    },
    'graphic_art': {
        'name': 'Graphic Art',
        'icon': '🎨',
        'extensions': ['.png', '.jpg', '.jpeg', '.psd', '.ai', '.svg', '.eps', '.tiff'],
        'max_size_mb': 500,
        'description_template': 'High-resolution digital artwork. Perfect for printing or digital use.',
        'tags': ['digital download', 'art', 'graphic design', 'digital art', 'printable']
    },
    'ebook': {
        'name': 'E-Books',
        'icon': '📚',
        'extensions': ['.pdf', '.epub', '.mobi', '.azw3'],
        'max_size_mb': 100,
        'description_template': 'Digital book download. Read on any device.',
        'tags': ['digital download', 'ebook', 'book', 'reading']
    },
    'video': {
        'name': 'Video Files',
        'icon': '🎬',
        'extensions': ['.mp4', '.mov', '.avi', '.mkv', '.webm'],
        'max_size_mb': 5000,
        'description_template': 'High-quality video download. Stream or download.',
        'tags': ['digital download', 'video', 'footage', 'content']
    },
    'template': {
        'name': 'Templates',
        'icon': '📋',
        'extensions': ['.psd', '.ai', '.fig', '.sketch', '.xd', '.docx', '.pptx', '.xlsx'],
        'max_size_mb': 200,
        'description_template': 'Professional template for your creative projects.',
        'tags': ['digital download', 'template', 'design', 'editable']
    },
    '3d_model': {
        'name': '3D Models',
        'icon': '🎮',
        'extensions': ['.obj', '.fbx', '.stl', '.blend', '.gltf', '.glb'],
        'max_size_mb': 1000,
        'description_template': '3D model ready for rendering, animation, or 3D printing.',
        'tags': ['digital download', '3D model', 'CGI', '3D printing']
    },
    'font': {
        'name': 'Fonts',
        'icon': '🔤',
        'extensions': ['.ttf', '.otf', '.woff', '.woff2'],
        'max_size_mb': 50,
        'description_template': 'Professional font family. Includes multiple weights and styles.',
        'tags': ['digital download', 'font', 'typography', 'typeface']
    },
    'preset': {
        'name': 'Presets & LUTs',
        'icon': '🎛️',
        'extensions': ['.xmp', '.lrtemplate', '.cube', '.3dl', '.look'],
        'max_size_mb': 50,
        'description_template': 'Professional editing presets for photo and video.',
        'tags': ['digital download', 'preset', 'LUT', 'editing', 'photography']
    },
    'course': {
        'name': 'Courses & Tutorials',
        'icon': '🎓',
        'extensions': ['.zip', '.pdf'],
        'max_size_mb': 10000,
        'description_template': 'Comprehensive digital course with video lessons and materials.',
        'tags': ['digital download', 'course', 'tutorial', 'learning', 'education']
    },
    'coloring_book': {
        'name': 'Coloring Books',
        'icon': '🖍️',
        'extensions': ['.pdf', '.png', '.zip'],
        'max_size_mb': 500,
        'description_template': 'Printable coloring book pages. Perfect for relaxation and creativity.',
        'tags': ['digital download', 'coloring book', 'printable', 'art therapy', 'kids', 'adults']
    },
    'graphic_novel': {
        'name': 'Graphic Novels',
        'icon': '📖',
        'extensions': ['.pdf', '.cbz', '.cbr', '.epub'],
        'max_size_mb': 500,
        'description_template': 'Digital graphic novel with stunning artwork and compelling storytelling.',
        'tags': ['digital download', 'graphic novel', 'comics', 'illustrated', 'fiction']
    },
    'comic_book': {
        'name': 'Comic Books',
        'icon': '💥',
        'extensions': ['.pdf', '.cbz', '.cbr'],
        'max_size_mb': 200,
        'description_template': 'Digital comic book issue. Full color, high resolution artwork.',
        'tags': ['digital download', 'comic book', 'comics', 'illustrated', 'superhero']
    },
    'sample_pack': {
        'name': 'Sample Packs',
        'icon': '🎹',
        'extensions': ['.zip', '.wav', '.mp3'],
        'max_size_mb': 2000,
        'description_template': 'Professional audio sample pack for music production. Royalty-free.',
        'tags': ['digital download', 'sample pack', 'music production', 'royalty-free', 'samples']
    },
    'drum_kit': {
        'name': 'Drum Kits',
        'icon': '🥁',
        'extensions': ['.zip', '.wav'],
        'max_size_mb': 1000,
        'description_template': 'Professional drum kit samples. Punchy kicks, snappy snares, crisp hi-hats.',
        'tags': ['digital download', 'drum kit', 'drums', 'music production', 'beats', 'royalty-free']
    },
    'music_loops': {
        'name': 'Music Loops',
        'icon': '🔁',
        'extensions': ['.zip', '.wav', '.mp3', '.aiff'],
        'max_size_mb': 1000,
        'description_template': 'Seamless music loops for production. Tempo-synced and royalty-free.',
        'tags': ['digital download', 'music loops', 'loops', 'music production', 'royalty-free']
    },
    'sound_design': {
        'name': 'Sound Design',
        'icon': '🔊',
        'extensions': ['.zip', '.wav', '.mp3'],
        'max_size_mb': 2000,
        'description_template': 'Professional sound design elements. SFX, atmospheres, textures.',
        'tags': ['digital download', 'sound design', 'SFX', 'sound effects', 'audio', 'royalty-free']
    }
}


class DigitalProductsService:
    """
    Service for creating and managing digital product listings.
    Integrates with Shopify and handles file delivery.
    """
    
    def __init__(self):
        """Initialize the digital products service."""
        self.shopify_shop_url = os.getenv('SHOPIFY_SHOP_URL', '')
        self.shopify_access_token = os.getenv('SHOPIFY_ACCESS_TOKEN', '')
        self.shopify_api_key = os.getenv('SHOPIFY_API_KEY', '')
        self.shopify_api_secret = os.getenv('SHOPIFY_API_SECRET', '')
        
        # Set up Shopify base URL
        self.shop_url = self.shopify_shop_url.replace('https://', '').replace('http://', '').strip('/')
        self.base_url = f"https://{self.shop_url}/admin/api/2024-01"
        
        # File storage settings
        self.storage_dir = Path(os.getenv('DIGITAL_PRODUCTS_DIR', './digital_products'))
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("✅ DigitalProductsService initialized")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get authentication headers for Shopify API."""
        if self.shopify_access_token:
            return {
                'X-Shopify-Access-Token': self.shopify_access_token,
                'Content-Type': 'application/json'
            }
        return {'Content-Type': 'application/json'}
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Optional[Dict]:
        """Make a request to the Shopify API."""
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, headers=headers, json=data, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                return None
            
            if response.status_code in [200, 201]:
                return response.json()
            else:
                logger.error(f"Shopify API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return None
    
    def detect_product_type(self, file_path: str) -> str:
        """
        Detect the digital product type based on file extension.
        
        Args:
            file_path: Path to the digital file
            
        Returns:
            Product type key (e.g., 'audio', 'software', 'graphic_art')
        """
        ext = Path(file_path).suffix.lower()
        
        for product_type, config in DIGITAL_PRODUCT_TYPES.items():
            if ext in config['extensions']:
                return product_type
        
        return 'software'  # Default to software for unknown types
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        Get information about a digital file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dict with file information
        """
        path = Path(file_path)
        
        if not path.exists():
            return {'error': 'File not found'}
        
        # Get file stats
        stats = path.stat()
        size_mb = stats.st_size / (1024 * 1024)
        
        # Get MIME type
        mime_type, _ = mimetypes.guess_type(str(path))
        
        # Calculate file hash for integrity
        with open(path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        
        # Detect product type
        product_type = self.detect_product_type(str(path))
        type_config = DIGITAL_PRODUCT_TYPES.get(product_type, {})
        
        return {
            'filename': path.name,
            'extension': path.suffix.lower(),
            'size_bytes': stats.st_size,
            'size_mb': round(size_mb, 2),
            'mime_type': mime_type,
            'file_hash': file_hash,
            'product_type': product_type,
            'type_name': type_config.get('name', 'Digital Product'),
            'type_icon': type_config.get('icon', '📦'),
            'created': datetime.fromtimestamp(stats.st_ctime).isoformat(),
            'modified': datetime.fromtimestamp(stats.st_mtime).isoformat()
        }
    
    def generate_product_description(
        self,
        file_info: Dict,
        custom_description: str = "",
        features: List[str] = None
    ) -> str:
        """
        Generate an HTML product description for a digital product.
        
        Args:
            file_info: File information dict
            custom_description: Custom description text
            features: List of product features
            
        Returns:
            HTML formatted description
        """
        product_type = file_info.get('product_type', 'software')
        type_config = DIGITAL_PRODUCT_TYPES.get(product_type, {})
        
        # Start with custom or template description
        if custom_description:
            main_desc = custom_description
        else:
            main_desc = type_config.get('description_template', 'High-quality digital download.')
        
        # Build features list
        if not features:
            features = [
                f"File format: {file_info.get('extension', '').upper().replace('.', '')}",
                f"File size: {file_info.get('size_mb', 0)} MB",
                "Instant download after purchase",
                "Lifetime access to your files",
                "Download up to 5 times"
            ]
        
        features_html = '\n'.join([f'<li>{feature}</li>' for feature in features])
        
        html = f"""
<div class="digital-product-description">
    <p><strong>{type_config.get('icon', '📦')} {type_config.get('name', 'Digital Product')}</strong></p>
    
    <p>{main_desc}</p>
    
    <h4>📋 What's Included:</h4>
    <ul>
        {features_html}
    </ul>
    
    <h4>📥 How It Works:</h4>
    <ol>
        <li>Complete your purchase</li>
        <li>Receive instant download link via email</li>
        <li>Download your files immediately</li>
        <li>Access your downloads anytime from your account</li>
    </ol>
    
    <p><em>⚡ This is a digital product. No physical item will be shipped.</em></p>
</div>
"""
        return html
    
    def create_digital_product(
        self,
        file_path: str,
        title: str,
        price: float,
        description: str = "",
        compare_at_price: float = None,
        tags: List[str] = None,
        preview_image: str = None,
        license_type: str = "personal",
        features: List[str] = None
    ) -> Optional[Dict]:
        """
        Create a digital product listing on Shopify.
        
        Args:
            file_path: Path to the digital file
            title: Product title
            price: Price in dollars
            description: Product description (optional, will auto-generate)
            compare_at_price: Original price for sale display
            tags: Additional tags
            preview_image: Path or URL to preview image
            license_type: 'personal', 'commercial', or 'extended'
            features: List of product features
            
        Returns:
            Created product dict or None
        """
        try:
            # Get file information
            file_info = self.get_file_info(file_path)
            if 'error' in file_info:
                logger.error(f"File error: {file_info['error']}")
                return None
            
            product_type = file_info['product_type']
            type_config = DIGITAL_PRODUCT_TYPES.get(product_type, {})
            
            # Generate description if not provided
            if not description:
                description = self.generate_product_description(file_info, "", features)
            
            # Build tags
            all_tags = type_config.get('tags', ['digital download'])
            if tags:
                all_tags.extend(tags)
            all_tags.append(f'license-{license_type}')
            all_tags = list(set(all_tags))  # Remove duplicates
            
            # Prepare images
            images = []
            if preview_image:
                if preview_image.startswith('http'):
                    images.append({'src': preview_image})
                elif Path(preview_image).exists():
                    # Upload image to Shopify (base64 encode)
                    with open(preview_image, 'rb') as f:
                        img_data = base64.b64encode(f.read()).decode('utf-8')
                    images.append({
                        'attachment': img_data,
                        'filename': Path(preview_image).name
                    })
            
            # Create product data
            product_data = {
                'product': {
                    'title': title,
                    'body_html': description,
                    'vendor': os.getenv('SHOPIFY_VENDOR_NAME', 'Digital Store'),
                    'product_type': type_config.get('name', 'Digital Product'),
                    'tags': ', '.join(all_tags),
                    'variants': [
                        {
                            'price': str(price),
                            'compare_at_price': str(compare_at_price) if compare_at_price else None,
                            'requires_shipping': False,  # Digital product - no shipping!
                            'taxable': True,
                            'inventory_management': None,  # Unlimited inventory for digital
                            'inventory_policy': 'continue',  # Always available
                            'fulfillment_service': 'manual'
                        }
                    ]
                }
            }
            
            if images:
                product_data['product']['images'] = images
            
            # Create product on Shopify
            response = self._make_request('POST', '/products.json', product_data)
            
            if response and 'product' in response:
                product = response['product']
                logger.info(f"✅ Created digital product: {title} (ID: {product['id']})")
                
                # Store file reference for Digital Downloads app
                self._store_digital_file_reference(product['id'], file_path, file_info)
                
                return {
                    'product_id': product['id'],
                    'title': product['title'],
                    'handle': product['handle'],
                    'url': f"https://{self.shop_url}/products/{product['handle']}",
                    'admin_url': f"https://{self.shop_url}/admin/products/{product['id']}",
                    'price': price,
                    'file_info': file_info,
                    'status': 'created'
                }
            else:
                logger.error("Failed to create product on Shopify")
                return None
                
        except Exception as e:
            logger.error(f"Error creating digital product: {e}")
            return None
    
    def _store_digital_file_reference(self, product_id: int, file_path: str, file_info: Dict):
        """
        Store a reference to the digital file for later retrieval.
        This is used to link products to their downloadable files.
        
        Note: The actual Digital Downloads app integration requires 
        manual file upload through Shopify admin or using their API.
        """
        reference_file = self.storage_dir / "product_files.json"
        
        try:
            if reference_file.exists():
                with open(reference_file, 'r') as f:
                    references = json.load(f)
            else:
                references = {}
            
            references[str(product_id)] = {
                'file_path': str(file_path),
                'file_info': file_info,
                'created_at': datetime.now().isoformat()
            }
            
            with open(reference_file, 'w') as f:
                json.dump(references, f, indent=2)
                
            logger.info(f"📁 Stored file reference for product {product_id}")
            
        except Exception as e:
            logger.error(f"Failed to store file reference: {e}")
    
    def create_bundle(
        self,
        file_paths: List[str],
        title: str,
        price: float,
        description: str = "",
        preview_image: str = None
    ) -> Optional[Dict]:
        """
        Create a bundle of digital products.
        
        Args:
            file_paths: List of file paths to include
            title: Bundle title
            price: Bundle price
            description: Bundle description
            preview_image: Preview image path
            
        Returns:
            Created bundle dict or None
        """
        # Get info for all files
        files_info = []
        total_size = 0
        all_types = set()
        
        for fp in file_paths:
            info = self.get_file_info(fp)
            if 'error' not in info:
                files_info.append(info)
                total_size += info['size_mb']
                all_types.add(info['type_name'])
        
        if not files_info:
            logger.error("No valid files found for bundle")
            return None
        
        # Generate bundle description
        files_list = '\n'.join([f"<li>{info['filename']} ({info['size_mb']} MB)</li>" 
                                for info in files_info])
        
        bundle_desc = f"""
<div class="digital-bundle">
    <p><strong>📦 Digital Bundle - {len(files_info)} Files</strong></p>
    
    {description or f"Get this amazing collection of {', '.join(all_types)}!"}
    
    <h4>📋 Included Files:</h4>
    <ul>
        {files_list}
    </ul>
    
    <p><strong>Total size:</strong> {round(total_size, 2)} MB</p>
    
    <h4>📥 Instant Download</h4>
    <p>All files delivered immediately after purchase!</p>
</div>
"""
        
        # Create the bundle product
        return self.create_digital_product(
            file_path=file_paths[0],  # Primary file
            title=title,
            price=price,
            description=bundle_desc,
            preview_image=preview_image,
            tags=['bundle', f'{len(files_info)}-files'],
            features=[f"Includes {len(files_info)} digital files", f"Total {round(total_size, 2)} MB"]
        )
    
    def list_products(self, product_type: str = None, limit: int = 50) -> List[Dict]:
        """
        List digital products from Shopify.
        
        Args:
            product_type: Filter by product type
            limit: Maximum products to return
            
        Returns:
            List of product dicts
        """
        endpoint = f'/products.json?limit={limit}'
        if product_type:
            type_config = DIGITAL_PRODUCT_TYPES.get(product_type, {})
            type_name = type_config.get('name', product_type)
            endpoint += f'&product_type={type_name}'
        
        response = self._make_request('GET', endpoint)
        if response and 'products' in response:
            # Filter for digital products (no shipping required)
            digital_products = []
            for product in response['products']:
                variants = product.get('variants', [])
                if variants and not variants[0].get('requires_shipping', True):
                    digital_products.append(product)
            return digital_products
        return []

    def generate_digital_product(
        self,
        product_type: str,
        title: str,
        target_audience: str = "general",
        num_pages: int = 10,
        style: str = "",
        **kwargs
    ) -> Optional[Dict]:
        """
        Generate a digital product using the appropriate generator.
        
        Args:
            product_type: Type of product (ebook, coloring_book, course, graphic_art, etc.)
            title: Product title
            target_audience: Target audience description
            num_pages: Number of pages/chapters
            style: Style preferences
            **kwargs: Additional generator-specific options
            
        Returns:
            Dict with generated product info including file paths
        """
        try:
            # Map type names
            type_map = {
                'e-book': 'ebook',
                'coloring book': 'coloring_book',
                'online course': 'course',
                'graphic art': 'graphic_art',
            }
            product_type = type_map.get(product_type.lower(), product_type.lower())
            
            if product_type == 'ebook':
                from digital_product_generator import EBookGenerator
                generator = EBookGenerator()
                return generator.generate_ebook(
                    topic=f"{title} for {target_audience}",
                    title=title,
                    genre=kwargs.get('genre', 'non-fiction'),
                    target_audience=target_audience,
                    num_chapters=num_pages,
                    include_images=kwargs.get('include_images', True),
                    include_audio=kwargs.get('include_audio', False)
                )
            elif product_type == 'coloring_book':
                from digital_product_generator import ColoringBookGenerator
                generator = ColoringBookGenerator()
                # Map target_audience to difficulty level
                difficulty_map = {
                    'kids': 'kids',
                    'children': 'kids',
                    'teens': 'teen',
                    'adults': 'adult',
                    'general': 'adult'
                }
                difficulty = difficulty_map.get(target_audience.lower(), 'adult')
                return generator.generate_coloring_book(
                    title=title,
                    theme=f"{title} {style}",
                    num_pages=num_pages,
                    difficulty=difficulty,
                    style=kwargs.get('art_style', style or 'mandala'),
                    page_size=kwargs.get('page_size', 'letter')
                )
            elif product_type == 'course':
                from digital_product_generator import CourseGenerator
                generator = CourseGenerator()
                return generator.generate_course(
                    title=title,
                    topic=title,
                    num_modules=kwargs.get('num_modules', max(1, num_pages // 3)),
                    lessons_per_module=kwargs.get('lessons_per_module', 3),
                    target_audience=target_audience,
                    difficulty=kwargs.get('difficulty', 'intermediate'),
                    include_video=kwargs.get('include_video', False)
                )
            elif product_type == 'graphic_art':
                # Use the DigitalProductGenerator for graphics
                gen = DigitalProductGenerator()
                output_dir = Path("./generated_products") / title.replace(' ', '_')[:30]
                files = gen.generate_graphic_art(
                    prompt=title,
                    style=style or "digital art",
                    output_dir=output_dir,
                    num_variations=kwargs.get('num_variations', 1)
                )
                if files:
                    return {
                        'title': title,
                        'type': 'graphic_art',
                        'files': files,
                        'output_dir': str(output_dir)
                    }
                return None
            else:
                # Default: treat as graphic art
                gen = DigitalProductGenerator()
                output_dir = Path("./generated_products") / title.replace(' ', '_')[:30]
                files = gen.generate_graphic_art(
                    prompt=f"{title}, {style}" if style else title,
                    style="professional digital product",
                    output_dir=output_dir,
                    num_variations=1
                )
                if files:
                    return {
                        'title': title,
                        'type': product_type,
                        'files': files,
                        'output_dir': str(output_dir)
                    }
                return None
                
        except ImportError as e:
            logging.error(f"Generator not available: {e}")
            return None
        except Exception as e:
            logging.error(f"Digital product generation failed: {e}")
            return None


class DigitalProductGenerator:
    """
    AI-powered digital product generator.
    Creates digital products like graphics, audio, templates automatically.
    """
    
    def __init__(self):
        """Initialize the generator."""
        self.service = DigitalProductsService()
        self.replicate_token = os.getenv('REPLICATE_API_TOKEN')
        
    def generate_graphic_art(
        self,
        prompt: str,
        style: str = "digital art",
        output_dir: Path = None,
        num_variations: int = 1
    ) -> List[str]:
        """
        Generate graphic art using AI.
        
        Args:
            prompt: Art description
            style: Art style
            output_dir: Output directory
            num_variations: Number of variations
            
        Returns:
            List of generated file paths
        """
        import replicate
        
        if not output_dir:
            output_dir = Path("./generated_art")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        generated_files = []
        
        for i in range(num_variations):
            try:
                # Use Flux for high-quality art generation
                output = replicate.run(
                    "black-forest-labs/flux-1.1-pro",
                    input={
                        "prompt": f"{prompt}, {style}, high resolution, detailed, professional quality",
                        "aspect_ratio": "1:1",
                        "output_format": "png",
                        "output_quality": 100
                    }
                )
                
                # Download the image
                if output:
                    image_url = str(output) if not isinstance(output, list) else str(output[0])
                    response = requests.get(image_url)
                    
                    if response.status_code == 200:
                        filename = f"art_{prompt[:30].replace(' ', '_')}_{i+1}.png"
                        filepath = output_dir / filename
                        
                        with open(filepath, 'wb') as f:
                            f.write(response.content)
                        
                        generated_files.append(str(filepath))
                        logger.info(f"✅ Generated: {filename}")
                        
            except Exception as e:
                logger.error(f"Generation error: {e}")
        
        return generated_files
    
    def create_and_list_graphic_product(
        self,
        prompt: str,
        title: str,
        price: float,
        style: str = "digital art"
    ) -> Optional[Dict]:
        """
        Generate graphic art and create a product listing.
        
        Args:
            prompt: Art description
            title: Product title
            price: Price
            style: Art style
            
        Returns:
            Product dict or None
        """
        # Generate the art
        files = self.generate_graphic_art(prompt, style, num_variations=1)
        
        if not files:
            logger.error("Failed to generate art")
            return None
        
        # Create the product listing
        return self.service.create_digital_product(
            file_path=files[0],
            title=title,
            price=price,
            preview_image=files[0],
            features=[
                "High-resolution PNG (print-ready)",
                "Commercial license included",
                "Instant download",
                "Perfect for prints, merchandise, or digital use"
            ]
        )


# Convenience functions for the main app
def create_digital_product(
    file_path: str,
    title: str,
    price: float,
    description: str = "",
    preview_image: str = None,
    **kwargs
) -> Optional[Dict]:
    """
    Convenience function to create a digital product.
    """
    service = DigitalProductsService()
    return service.create_digital_product(
        file_path=file_path,
        title=title,
        price=price,
        description=description,
        preview_image=preview_image,
        **kwargs
    )


def list_digital_products(product_type: str = None) -> List[Dict]:
    """
    Convenience function to list digital products.
    """
    service = DigitalProductsService()
    return service.list_products(product_type=product_type)


# Test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("Digital Product Types:")
    for key, config in DIGITAL_PRODUCT_TYPES.items():
        print(f"  {config['icon']} {config['name']}: {', '.join(config['extensions'][:3])}...")
    
    # Test file detection
    service = DigitalProductsService()
    test_files = ['song.mp3', 'app.zip', 'design.psd', 'book.pdf']
    
    print("\nFile type detection:")
    for f in test_files:
        ptype = service.detect_product_type(f)
        config = DIGITAL_PRODUCT_TYPES.get(ptype, {})
        print(f"  {f} → {config.get('icon', '📦')} {config.get('name', ptype)}")
