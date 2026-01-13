"""
Printify Mockup Service
========================

Download and cache product mockup images from Printify API.

Features:
- Fetch mockup URLs from Printify products
- Download high-resolution mockup images
- Cache mockups for reuse
- Support multiple mockup variants
- Batch download for campaigns

Author: Autonomous Business Platform
Version: 1.0
"""

import os
import requests
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import time


class PrintifyMockupService:
    """
    Service for downloading and managing Printify product mockups.
    
    Printify automatically generates mockup images when products are created.
    This service fetches those mockups and caches them locally.
    """
    
    def __init__(self, api_token: str, shop_id: str):
        """
        Initialize Printify mockup service.
        
        Args:
            api_token: Printify API token from .env
            shop_id: Printify shop ID
        """
        self.api_token = api_token
        self.shop_id = shop_id
        self.base_url = "https://api.printify.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        # Cache for mockup metadata
        self.mockup_cache: Dict[str, Dict] = {}
    
    def get_product_details(self, product_id: str) -> Optional[Dict]:
        """
        Fetch product details from Printify API.
        
        Args:
            product_id: Printify product ID
            
        Returns:
            Product data dict or None if error
        """
        try:
            url = f"{self.base_url}/shops/{self.shop_id}/products/{product_id}.json"
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Failed to fetch product {product_id}: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error fetching product details: {e}")
            return None
    
    def get_mockup_urls(self, product_id: str) -> List[Dict[str, str]]:
        """
        Extract mockup URLs from product data.
        
        Printify products include mockup images in the 'images' array.
        
        Args:
            product_id: Printify product ID
            
        Returns:
            List of mockup dicts with 'url', 'variant', 'is_default' keys
        """
        product_data = self.get_product_details(product_id)
        
        if not product_data:
            return []
        
        mockups = []
        
        # Extract images from product data
        for image in product_data.get('images', []):
            mockup_info = {
                'url': image.get('src'),
                'variant': image.get('variant_ids', []),
                'is_default': image.get('is_default', False),
                'position': image.get('position', 'front')
            }
            
            if mockup_info['url']:
                mockups.append(mockup_info)
        
        # Sort by default first, then by position
        mockups.sort(key=lambda x: (not x['is_default'], x['position']))
        
        return mockups
    
    def download_mockup(
        self, 
        mockup_url: str, 
        save_dir: Path, 
        filename: str,
        retry_count: int = 3
    ) -> Optional[str]:
        """
        Download a single mockup image with retry logic.
        
        Args:
            mockup_url: Direct URL to mockup image
            save_dir: Directory to save image
            filename: Filename for saved image
            retry_count: Number of retry attempts
            
        Returns:
            Path to saved image or None if failed
        """
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        
        save_path = save_dir / filename
        
        for attempt in range(retry_count):
            try:
                response = requests.get(mockup_url, timeout=60)
                
                if response.status_code == 200:
                    with open(save_path, 'wb') as f:
                        f.write(response.content)
                    
                    # Verify file was saved
                    if save_path.exists() and save_path.stat().st_size > 0:
                        return str(save_path)
                    else:
                        print(f"⚠️ Downloaded file is empty, retrying...")
                        continue
                else:
                    print(f"⚠️ Download failed with status {response.status_code}")
                    
            except Exception as e:
                print(f"⚠️ Download attempt {attempt+1} failed: {e}")
                
            # Wait before retry
            if attempt < retry_count - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
        
        print(f"❌ Failed to download mockup after {retry_count} attempts")
        return None
    
    def download_product_mockups(
        self, 
        product_id: str, 
        campaign_dir: Path,
        download_all: bool = False
    ) -> Dict[str, str]:
        """
        Download all mockups for a product.
        
        Args:
            product_id: Printify product ID
            campaign_dir: Campaign directory to save mockups
            download_all: If True, download all variants; if False, only default
            
        Returns:
            Dict mapping mockup type to file path
            Example: {'default': '/path/to/mockup.png', 'back': '/path/to/back.png'}
        """
        mockup_urls = self.get_mockup_urls(product_id)
        
        if not mockup_urls:
            print(f"⚠️ No mockups found for product {product_id}")
            return {}
        
        # Create mockups directory
        mockup_dir = Path(campaign_dir) / "mockups"
        mockup_dir.mkdir(parents=True, exist_ok=True)
        
        downloaded_mockups = {}
        
        for i, mockup_info in enumerate(mockup_urls):
            # Skip non-default mockups if download_all is False
            if not download_all and not mockup_info['is_default']:
                continue
            
            mockup_url = mockup_info['url']
            position = mockup_info['position']
            
            # Generate filename
            if mockup_info['is_default']:
                filename = f"product_{product_id}_mockup_default.png"
                key = 'default'
            else:
                filename = f"product_{product_id}_mockup_{position}_{i}.png"
                key = f"{position}_{i}"
            
            print(f"📥 Downloading mockup: {position}...")
            
            saved_path = self.download_mockup(
                mockup_url, 
                mockup_dir, 
                filename
            )
            
            if saved_path:
                downloaded_mockups[key] = saved_path
                print(f"✅ Saved: {filename}")
            else:
                print(f"❌ Failed: {filename}")
        
        return downloaded_mockups
    
    def batch_download_mockups(
        self, 
        product_ids: List[str], 
        campaign_dir: Path
    ) -> Dict[str, Dict[str, str]]:
        """
        Download mockups for multiple products.
        
        Args:
            product_ids: List of Printify product IDs
            campaign_dir: Campaign directory
            
        Returns:
            Dict mapping product_id to mockup paths dict
        """
        all_mockups = {}
        
        for product_id in product_ids:
            print(f"\n🎨 Processing product {product_id}...")
            mockups = self.download_product_mockups(product_id, campaign_dir)
            
            if mockups:
                all_mockups[product_id] = mockups
                print(f"✅ Downloaded {len(mockups)} mockup(s) for product {product_id}")
            else:
                print(f"⚠️ No mockups downloaded for product {product_id}")
        
        return all_mockups
    
    def cache_mockup_metadata(
        self, 
        product_id: str, 
        mockup_paths: Dict[str, str],
        campaign_dir: Path
    ) -> None:
        """
        Save mockup metadata to campaign directory for future reference.
        
        Args:
            product_id: Printify product ID
            mockup_paths: Dict of mockup type to file path
            campaign_dir: Campaign directory
        """
        try:
            cache_file = Path(campaign_dir) / "mockups" / "mockup_cache.json"
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Load existing cache
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
            else:
                cache_data = {}
            
            # Add new mockup data
            cache_data[product_id] = {
                'mockup_paths': mockup_paths,
                'downloaded_at': datetime.now().isoformat(),
                'product_id': product_id
            }
            
            # Save cache
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            print(f"💾 Cached mockup metadata for product {product_id}")
            
        except Exception as e:
            print(f"⚠️ Failed to cache mockup metadata: {e}")
    
    def get_cached_mockups(
        self, 
        product_id: str, 
        campaign_dir: Path
    ) -> Optional[Dict[str, str]]:
        """
        Retrieve cached mockup paths for a product.
        
        Args:
            product_id: Printify product ID
            campaign_dir: Campaign directory
            
        Returns:
            Dict of mockup paths or None if not cached
        """
        try:
            cache_file = Path(campaign_dir) / "mockups" / "mockup_cache.json"
            
            if not cache_file.exists():
                return None
            
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            
            product_cache = cache_data.get(product_id)
            
            if product_cache:
                # Verify files still exist
                mockup_paths = product_cache.get('mockup_paths', {})
                
                for key, path in list(mockup_paths.items()):
                    if not Path(path).exists():
                        print(f"⚠️ Cached mockup missing: {path}")
                        del mockup_paths[key]
                
                if mockup_paths:
                    return mockup_paths
            
            return None
            
        except Exception as e:
            print(f"⚠️ Error reading mockup cache: {e}")
            return None
    
    def download_or_use_cached(
        self, 
        product_id: str, 
        campaign_dir: Path
    ) -> Dict[str, str]:
        """
        Get mockups from cache or download if not available.
        
        Args:
            product_id: Printify product ID
            campaign_dir: Campaign directory
            
        Returns:
            Dict of mockup type to file path
        """
        # Check cache first
        cached_mockups = self.get_cached_mockups(product_id, campaign_dir)
        
        if cached_mockups:
            print(f"📦 Using cached mockups for product {product_id}")
            return cached_mockups
        
        # Download if not cached
        print(f"🌐 Downloading fresh mockups for product {product_id}")
        mockup_paths = self.download_product_mockups(product_id, campaign_dir)
        
        # Cache for future use
        if mockup_paths:
            self.cache_mockup_metadata(product_id, mockup_paths, campaign_dir)
        
        return mockup_paths
    
    def get_mockup_info(self, product_id: str) -> Dict:
        """
        Get information about available mockups without downloading.
        
        Args:
            product_id: Printify product ID
            
        Returns:
            Dict with mockup information
        """
        mockups = self.get_mockup_urls(product_id)
        
        return {
            'product_id': product_id,
            'total_mockups': len(mockups),
            'default_mockup': next((m for m in mockups if m['is_default']), None),
            'all_mockups': mockups
        }


# Convenience functions for streamlit integration
def download_mockups_for_campaign(
    product_ids: List[str],
    campaign_dir: Path,
    api_token: str,
    shop_id: str
) -> Dict[str, Dict[str, str]]:
    """
    Quick function to download mockups for a campaign.
    
    Args:
        product_ids: List of Printify product IDs
        campaign_dir: Campaign directory
        api_token: Printify API token
        shop_id: Printify shop ID
        
    Returns:
        Dict mapping product_id to mockup paths
    """
    service = PrintifyMockupService(api_token, shop_id)
    return service.batch_download_mockups(product_ids, campaign_dir)


def get_default_mockup(
    product_id: str,
    campaign_dir: Path,
    api_token: str,
    shop_id: str
) -> Optional[str]:
    """
    Get the default mockup path for a product.
    
    Args:
        product_id: Printify product ID
        campaign_dir: Campaign directory
        api_token: Printify API token
        shop_id: Printify shop ID
        
    Returns:
        Path to default mockup or None
    """
    service = PrintifyMockupService(api_token, shop_id)
    mockups = service.download_or_use_cached(product_id, campaign_dir)
    
    return mockups.get('default')


# Example usage
if __name__ == "__main__":
    """
    Example: Download mockups for a campaign
    """
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    API_TOKEN = os.getenv("PRINTIFY_API_TOKEN")
    SHOP_ID = os.getenv("PRINTIFY_SHOP_ID")
    
    if not API_TOKEN or not SHOP_ID:
        print("❌ Missing PRINTIFY_API_TOKEN or PRINTIFY_SHOP_ID in .env")
        exit(1)
    
    # Initialize service
    service = PrintifyMockupService(API_TOKEN, SHOP_ID)
    
    # Example product ID (replace with actual ID)
    product_id = "12345"
    campaign_dir = Path("./test_campaign")
    
    # Download mockups
    print(f"\n🚀 Downloading mockups for product {product_id}...")
    mockups = service.download_product_mockups(product_id, campaign_dir)
    
    if mockups:
        print(f"\n✅ Successfully downloaded {len(mockups)} mockup(s):")
        for mockup_type, path in mockups.items():
            print(f"   - {mockup_type}: {path}")
    else:
        print("\n❌ No mockups downloaded")
