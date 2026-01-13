"""
Store Connectors
================
Unified connectors for Etsy, Amazon, and eBay stores.
"""

import requests
import os
import json
import hmac
import hashlib
import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod
from urllib.parse import urlencode, quote

logger = logging.getLogger(__name__)


@dataclass
class StoreListing:
    """Unified listing representation across store platforms."""
    id: str
    title: str
    description: str
    price: float
    currency: str
    images: List[str]
    quantity: int
    platform: str
    platform_id: str
    status: str = "draft"
    url: Optional[str] = None


class BaseStoreConnector(ABC):
    """Abstract base class for store connectors."""
    
    @abstractmethod
    def get_listings(self) -> List[Dict]:
        pass
    
    @abstractmethod
    def create_listing(self, listing_data: Dict) -> Dict:
        pass
    
    @abstractmethod
    def update_listing(self, listing_id: str, listing_data: Dict) -> Dict:
        pass
    
    @abstractmethod
    def delete_listing(self, listing_id: str) -> bool:
        pass


class EtsyConnector(BaseStoreConnector):
    """Connector for Etsy marketplace."""
    
    BASE_URL = "https://openapi.etsy.com/v3"
    
    def __init__(self, api_key: str = None, access_token: str = None, shop_id: str = None):
        self.api_key = api_key or os.getenv("ETSY_API_KEY", "")
        self.access_token = access_token or os.getenv("ETSY_ACCESS_TOKEN", "")
        self.shop_id = shop_id or os.getenv("ETSY_SHOP_ID", "")
        self.headers = {
            "x-api-key": self.api_key,
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def _request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Make API request to Etsy."""
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        
        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers, timeout=30)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, json=data, timeout=30)
            elif method == "PUT":
                response = requests.put(url, headers=self.headers, json=data, timeout=30)
            elif method == "DELETE":
                response = requests.delete(url, headers=self.headers, timeout=30)
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Etsy API error: {e}")
            raise
    
    def get_shop_info(self) -> Dict:
        """Get shop information."""
        return self._request("GET", f"application/shops/{self.shop_id}")
    
    def get_listings(self, state: str = "active") -> List[Dict]:
        """Get shop listings."""
        result = self._request("GET", f"application/shops/{self.shop_id}/listings?state={state}")
        return result.get("results", [])
    
    def get_listing(self, listing_id: str) -> Dict:
        """Get a specific listing."""
        return self._request("GET", f"application/listings/{listing_id}")
    
    def create_listing(self, listing_data: Dict) -> Dict:
        """Create a new listing."""
        return self._request("POST", f"application/shops/{self.shop_id}/listings", listing_data)
    
    def update_listing(self, listing_id: str, listing_data: Dict) -> Dict:
        """Update an existing listing."""
        return self._request("PUT", f"application/listings/{listing_id}", listing_data)
    
    def delete_listing(self, listing_id: str) -> bool:
        """Delete a listing."""
        self._request("DELETE", f"application/listings/{listing_id}")
        return True
    
    def upload_listing_image(self, listing_id: str, image_data: bytes, filename: str) -> Dict:
        """Upload image to a listing."""
        url = f"{self.BASE_URL}/application/shops/{self.shop_id}/listings/{listing_id}/images"
        files = {"image": (filename, image_data, "image/png")}
        headers = {
            "x-api-key": self.api_key,
            "Authorization": f"Bearer {self.access_token}"
        }
        response = requests.post(url, headers=headers, files=files, timeout=60)
        response.raise_for_status()
        return response.json()
    
    def get_taxonomy(self) -> List[Dict]:
        """Get Etsy taxonomy/categories."""
        result = self._request("GET", "application/seller-taxonomy/nodes")
        return result.get("results", [])


class AmazonConnector(BaseStoreConnector):
    """Connector for Amazon Seller Central (SP-API)."""
    
    # Amazon SP-API endpoints by region
    ENDPOINTS = {
        "NA": "https://sellingpartnerapi-na.amazon.com",
        "EU": "https://sellingpartnerapi-eu.amazon.com",
        "FE": "https://sellingpartnerapi-fe.amazon.com"
    }
    
    def __init__(self, 
                 access_key: str = None,
                 secret_key: str = None,
                 refresh_token: str = None,
                 region: str = "NA",
                 marketplace_id: str = None):
        self.access_key = access_key or os.getenv("AMAZON_ACCESS_KEY", "")
        self.secret_key = secret_key or os.getenv("AMAZON_SECRET_KEY", "")
        self.refresh_token = refresh_token or os.getenv("AMAZON_REFRESH_TOKEN", "")
        self.region = region
        self.marketplace_id = marketplace_id or os.getenv("AMAZON_MARKETPLACE_ID", "ATVPDKIKX0DER")  # US default
        self.base_url = self.ENDPOINTS.get(region, self.ENDPOINTS["NA"])
        self._access_token = None
        self._token_expires = 0
    
    def _get_access_token(self) -> str:
        """Get or refresh access token."""
        if self._access_token and time.time() < self._token_expires:
            return self._access_token
        
        # Token refresh logic would go here
        # This requires LWA (Login with Amazon) OAuth flow
        logger.warning("Amazon SP-API requires OAuth token refresh implementation")
        return self._access_token or ""
    
    def _request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Make API request to Amazon SP-API."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {
            "x-amz-access-token": self._get_access_token(),
            "Content-Type": "application/json"
        }
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=30)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=30)
            elif method == "PUT":
                response = requests.put(url, headers=headers, json=data, timeout=30)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=30)
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Amazon SP-API error: {e}")
            raise
    
    def get_listings(self) -> List[Dict]:
        """Get seller listings."""
        result = self._request("GET", f"listings/2021-08-01/items?marketplaceIds={self.marketplace_id}")
        return result.get("items", [])
    
    def create_listing(self, listing_data: Dict) -> Dict:
        """Create a new listing."""
        sku = listing_data.get("sku")
        return self._request("PUT", f"listings/2021-08-01/items/{sku}", listing_data)
    
    def update_listing(self, listing_id: str, listing_data: Dict) -> Dict:
        """Update an existing listing."""
        return self._request("PATCH", f"listings/2021-08-01/items/{listing_id}", listing_data)
    
    def delete_listing(self, listing_id: str) -> bool:
        """Delete a listing."""
        self._request("DELETE", f"listings/2021-08-01/items/{listing_id}")
        return True
    
    def get_orders(self, created_after: str = None) -> List[Dict]:
        """Get orders."""
        params = f"marketplaceIds={self.marketplace_id}"
        if created_after:
            params += f"&createdAfter={created_after}"
        result = self._request("GET", f"orders/v0/orders?{params}")
        return result.get("Orders", [])


class EbayConnector(BaseStoreConnector):
    """Connector for eBay marketplace."""
    
    BASE_URL = "https://api.ebay.com"
    SANDBOX_URL = "https://api.sandbox.ebay.com"
    
    def __init__(self, 
                 client_id: str = None,
                 client_secret: str = None,
                 access_token: str = None,
                 sandbox: bool = False):
        self.client_id = client_id or os.getenv("EBAY_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("EBAY_CLIENT_SECRET", "")
        self.access_token = access_token or os.getenv("EBAY_ACCESS_TOKEN", "")
        self.base_url = self.SANDBOX_URL if sandbox else self.BASE_URL
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def _request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Make API request to eBay."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers, timeout=30)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, json=data, timeout=30)
            elif method == "PUT":
                response = requests.put(url, headers=self.headers, json=data, timeout=30)
            elif method == "DELETE":
                response = requests.delete(url, headers=self.headers, timeout=30)
            
            response.raise_for_status()
            return response.json() if response.content else {}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"eBay API error: {e}")
            raise
    
    def get_listings(self) -> List[Dict]:
        """Get active listings."""
        result = self._request("GET", "sell/inventory/v1/inventory_item")
        return result.get("inventoryItems", [])
    
    def get_listing(self, sku: str) -> Dict:
        """Get a specific inventory item."""
        return self._request("GET", f"sell/inventory/v1/inventory_item/{sku}")
    
    def create_listing(self, listing_data: Dict) -> Dict:
        """Create or replace an inventory item."""
        sku = listing_data.get("sku")
        return self._request("PUT", f"sell/inventory/v1/inventory_item/{sku}", listing_data)
    
    def update_listing(self, listing_id: str, listing_data: Dict) -> Dict:
        """Update an inventory item."""
        return self.create_listing(listing_data)  # eBay uses PUT for updates
    
    def delete_listing(self, listing_id: str) -> bool:
        """Delete an inventory item."""
        self._request("DELETE", f"sell/inventory/v1/inventory_item/{listing_id}")
        return True
    
    def create_offer(self, offer_data: Dict) -> Dict:
        """Create an offer for an inventory item."""
        return self._request("POST", "sell/inventory/v1/offer", offer_data)
    
    def publish_offer(self, offer_id: str) -> Dict:
        """Publish an offer to make it live."""
        return self._request("POST", f"sell/inventory/v1/offer/{offer_id}/publish")
    
    def get_orders(self) -> List[Dict]:
        """Get recent orders."""
        result = self._request("GET", "sell/fulfillment/v1/order")
        return result.get("orders", [])
    
    def get_categories(self, category_tree_id: str = "0") -> List[Dict]:
        """Get eBay categories."""
        result = self._request("GET", f"commerce/taxonomy/v1/category_tree/{category_tree_id}")
        return result.get("rootCategoryNode", {}).get("childCategoryTreeNodes", [])


class UnifiedStoreManager:
    """Unified manager for all store platforms."""
    
    def __init__(self):
        self.connectors: Dict[str, BaseStoreConnector] = {}
        self._initialize_connectors()
    
    def _initialize_connectors(self):
        """Initialize available connectors based on API keys."""
        if os.getenv("ETSY_API_KEY") and os.getenv("ETSY_ACCESS_TOKEN"):
            self.connectors["etsy"] = EtsyConnector()
            logger.info("Etsy connector initialized")
        
        if os.getenv("AMAZON_ACCESS_KEY"):
            self.connectors["amazon"] = AmazonConnector()
            logger.info("Amazon connector initialized")
        
        if os.getenv("EBAY_ACCESS_TOKEN"):
            self.connectors["ebay"] = EbayConnector()
            logger.info("eBay connector initialized")
    
    def get_connector(self, platform: str) -> Optional[BaseStoreConnector]:
        """Get a specific connector."""
        return self.connectors.get(platform.lower())
    
    def list_platforms(self) -> List[str]:
        """List available platforms."""
        return list(self.connectors.keys())
    
    def get_all_listings(self) -> Dict[str, List[Dict]]:
        """Get listings from all platforms."""
        listings = {}
        for platform, connector in self.connectors.items():
            try:
                listings[platform] = connector.get_listings()
            except Exception as e:
                logger.error(f"Failed to get {platform} listings: {e}")
                listings[platform] = []
        return listings
    
    def create_listing_on_platform(self, platform: str, listing_data: Dict) -> Dict:
        """Create listing on specific platform."""
        connector = self.get_connector(platform)
        if not connector:
            raise ValueError(f"Platform not configured: {platform}")
        return connector.create_listing(listing_data)


def render_store_connectors_ui():
    """Render store connectors UI in Streamlit."""
    import streamlit as st
    
    st.markdown("### 🛒 Store Connectors")
    
    manager = UnifiedStoreManager()
    available = manager.list_platforms()
    
    # Status display
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if "etsy" in available:
            st.success("✅ Etsy Connected")
        else:
            st.warning("⚠️ Etsy - Add API keys")
    
    with col2:
        if "amazon" in available:
            st.success("✅ Amazon Connected")
        else:
            st.warning("⚠️ Amazon - Add API keys")
    
    with col3:
        if "ebay" in available:
            st.success("✅ eBay Connected")
        else:
            st.warning("⚠️ eBay - Add API keys")
    
    if not available:
        st.info("Add API keys to your .env file to connect store platforms")
        
        with st.expander("Setup Instructions"):
            st.markdown("""
            **Etsy:**
            - ETSY_API_KEY - Your Etsy API key
            - ETSY_ACCESS_TOKEN - OAuth access token
            - ETSY_SHOP_ID - Your shop ID
            
            **Amazon:**
            - AMAZON_ACCESS_KEY - AWS access key
            - AMAZON_SECRET_KEY - AWS secret key
            - AMAZON_REFRESH_TOKEN - SP-API refresh token
            - AMAZON_MARKETPLACE_ID - Marketplace ID
            
            **eBay:**
            - EBAY_CLIENT_ID - eBay app client ID
            - EBAY_CLIENT_SECRET - eBay app secret
            - EBAY_ACCESS_TOKEN - OAuth access token
            """)
        return
    
    # Platform selector
    selected_platform = st.selectbox("Select Store", available)
    connector = manager.get_connector(selected_platform)
    
    # Actions
    action = st.radio("Action", ["View Listings", "Create Listing"], horizontal=True)
    
    if action == "View Listings":
        if st.button("Load Listings", use_container_width=True):
            with st.spinner("Loading..."):
                try:
                    listings = connector.get_listings()
                    st.success(f"Found {len(listings)} listings")
                    
                    for listing in listings[:20]:
                        title = listing.get("title", listing.get("sku", "Listing"))
                        with st.expander(title):
                            st.json(listing)
                except Exception as e:
                    st.error(f"Failed to load listings: {e}")
    
    elif action == "Create Listing":
        st.markdown("**Create New Listing**")
        
        title = st.text_input("Title")
        description = st.text_area("Description")
        price = st.number_input("Price", min_value=0.0, step=0.01)
        quantity = st.number_input("Quantity", min_value=1, value=1)
        
        if st.button("Create Listing", type="primary"):
            if title and description and price > 0:
                with st.spinner("Creating..."):
                    try:
                        listing_data = {
                            "title": title,
                            "description": description,
                            "price": {"amount": str(price), "currency": "USD"},
                            "quantity": quantity
                        }
                        result = connector.create_listing(listing_data)
                        st.success("Listing created!")
                        st.json(result)
                    except Exception as e:
                        st.error(f"Failed to create listing: {e}")
            else:
                st.warning("Please fill in all fields")
