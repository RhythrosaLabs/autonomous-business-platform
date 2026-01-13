"""
Shopify API Service
Handles authentication, blog publishing, product syncing, and analytics fetching
"""

import requests
import os
import time
import json
from datetime import datetime
from typing import Dict, List, Optional, Any


class ShopifyAPI:
    """Shopify API wrapper for e-commerce integration"""
    
    def __init__(self, shop_url: str = None, api_key: str = None, api_secret: str = None, access_token: str = None):
        """
        Initialize Shopify API client
        
        Args:
            shop_url: Your Shopify store URL (e.g., "mystore.myshopify.com")
            api_key: Shopify API key (for private apps)
            api_secret: Shopify API secret (for private apps)
            access_token: Access token (alternative to API key/secret)
        """
        # Try loading from environment if not provided
        self.shop_url = shop_url or os.getenv('SHOPIFY_SHOP_URL', '')
        self.api_key = api_key or os.getenv('SHOPIFY_API_KEY', '')
        self.api_secret = api_secret or os.getenv('SHOPIFY_API_SECRET', '')
        self.access_token = access_token or os.getenv('SHOPIFY_ACCESS_TOKEN', '')
        
        # Remove https:// and trailing slash if present
        self.shop_url = self.shop_url.replace('https://', '').replace('http://', '').strip('/')
        
        # Set up base URL
        self.base_url = f"https://{self.shop_url}/admin/api/2024-01"
        
        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 2
        
        # Check if credentials are configured
        self._connected = None  # Lazy-loaded connection status
    
    @property
    def connected(self) -> bool:
        """Check if Shopify API is connected and credentials are valid."""
        if self._connected is None:
            # Check basic credential requirements
            if not self.shop_url:
                self._connected = False
            elif not self.api_key and not self.access_token:
                self._connected = False
            else:
                # Try a simple API call to verify
                try:
                    response = self._make_request('GET', '/shop.json')
                    self._connected = response is not None and 'shop' in response
                except Exception:
                    self._connected = False
        return self._connected
    
    def _get_headers(self) -> Dict[str, str]:
        """Get authentication headers"""
        if self.access_token:
            return {
                'X-Shopify-Access-Token': self.access_token,
                'Content-Type': 'application/json'
            }
        else:
            # Basic Auth with API key and password
            return {
                'Content-Type': 'application/json'
            }
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None, retry_count: int = 0) -> Optional[Dict]:
        """
        Make API request with retry logic
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (e.g., "/blogs.json")
            data: Request payload
            retry_count: Current retry attempt
            
        Returns:
            Response JSON or None on failure
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        
        try:
            if self.access_token:
                # Use access token
                if method == 'GET':
                    response = requests.get(url, headers=headers, timeout=30)
                elif method == 'POST':
                    response = requests.post(url, headers=headers, json=data, timeout=30)
                elif method == 'PUT':
                    response = requests.put(url, headers=headers, json=data, timeout=30)
                elif method == 'DELETE':
                    response = requests.delete(url, headers=headers, timeout=30)
            else:
                # Use API key and password (Basic Auth)
                auth = (self.api_key, self.api_secret)
                if method == 'GET':
                    response = requests.get(url, auth=auth, headers=headers, timeout=30)
                elif method == 'POST':
                    response = requests.post(url, auth=auth, headers=headers, json=data, timeout=30)
                elif method == 'PUT':
                    response = requests.put(url, auth=auth, headers=headers, json=data, timeout=30)
                elif method == 'DELETE':
                    response = requests.delete(url, auth=auth, headers=headers, timeout=30)
            
            # Check for rate limiting
            if response.status_code == 429:
                if retry_count < self.max_retries:
                    wait_time = self.retry_delay * (2 ** retry_count)
                    print(f"Rate limited. Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    return self._make_request(method, endpoint, data, retry_count + 1)
                else:
                    print(f"Max retries reached for rate limiting")
                    return None
            
            response.raise_for_status()
            
            # Return empty dict for DELETE requests
            if method == 'DELETE':
                return {}
            
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error: {e}")
            print(f"Response: {e.response.text if hasattr(e, 'response') else 'No response'}")
            
            # Retry on server errors
            if hasattr(e, 'response') and e.response.status_code >= 500 and retry_count < self.max_retries:
                wait_time = self.retry_delay * (2 ** retry_count)
                print(f"Server error. Retrying in {wait_time}s...")
                time.sleep(wait_time)
                return self._make_request(method, endpoint, data, retry_count + 1)
            
            return None
            
        except requests.exceptions.RequestException as e:
            print(f"Request Error: {e}")
            
            # Retry on network errors
            if retry_count < self.max_retries:
                wait_time = self.retry_delay * (2 ** retry_count)
                print(f"Network error. Retrying in {wait_time}s...")
                time.sleep(wait_time)
                return self._make_request(method, endpoint, data, retry_count + 1)
            
            return None
    
    def test_connection(self) -> bool:
        """
        Test Shopify API connection
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Validate credentials
            if not self.shop_url:
                print("❌ SHOPIFY_SHOP_URL not configured")
                return False
            if not self.api_key or not self.api_secret:
                if not self.access_token:
                    print("❌ Either API Key+Secret OR Access Token required")
                    return False
            
            response = self._make_request('GET', '/shop.json')
            if response and 'shop' in response:
                print(f"✅ Connected to Shopify store: {response['shop']['name']}")
                return True
            else:
                print(f"❌ Invalid response from Shopify API")
                return False
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
            return False
    
    # ========================================
    # BLOG FUNCTIONS
    # ========================================
    
    def get_blogs(self) -> List[Dict]:
        """
        Get all blogs from Shopify store
        
        Returns:
            List of blog dictionaries
        """
        response = self._make_request('GET', '/blogs.json')
        if response and 'blogs' in response:
            return response['blogs']
        return []
    
    def create_blog(self, title: str, handle: str = None) -> Optional[Dict]:
        """
        Create a new blog
        
        Args:
            title: Blog title
            handle: URL handle (auto-generated if not provided)
            
        Returns:
            Created blog dictionary or None
        """
        data = {
            'blog': {
                'title': title
            }
        }
        
        if handle:
            data['blog']['handle'] = handle
        
        response = self._make_request('POST', '/blogs.json', data)
        if response and 'blog' in response:
            return response['blog']
        return None
    
    def create_blog_post(
        self,
        title: str,
        body_html: str,
        author: str = "AI Blog Writer",
        tags: Optional[List[str]] = None,
        published: bool = True,
        handle: Optional[str] = None,
        image_url: Optional[str] = None,
        metafields: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Create a blog post in the default blog (creates blog if needed)
        
        Args:
            title: Blog post title
            body_html: HTML content of the blog post
            author: Author name
            tags: List of tags
            published: Whether to publish immediately
            handle: URL handle for the post
            image_url: Featured image URL
            metafields: Additional metafields (e.g., SEO description)
            
        Returns:
            Created blog article dictionary with 'id' and URL info
        """
        # Get or create default blog
        blogs = self.get_blogs()
        if not blogs:
            # Create default blog
            blog = self.create_blog("News", "news")
            if not blog:
                raise Exception("Failed to create blog")
            blog_id = blog['id']
        else:
            blog_id = blogs[0]['id']  # Use first blog
        
        # Prepare article data
        data = {
            'article': {
                'title': title,
                'author': author,
                'body_html': body_html,
                'published': published
            }
        }
        
        if handle:
            data['article']['handle'] = handle
        
        if tags:
            data['article']['tags'] = ', '.join(tags)
        
        if image_url:
            data['article']['image'] = {
                'src': image_url
            }
        
        # Note: Metafields require separate API call
        # This is simplified for now
        
        print(f"📤 Publishing blog post to blog ID {blog_id}...")
        print(f"   Title: {title}")
        print(f"   Author: {author}")
        print(f"   Published: {published}")
        print(f"   Tags: {tags}")
        
        response = self._make_request('POST', f'/blogs/{blog_id}/articles.json', data)
        
        if response and 'article' in response:
            article = response['article']
            # Add URL info
            blog_handle = blogs[0].get('handle', 'news') if blogs else 'news'
            article_handle = article.get('handle', article['id'])
            article['url'] = f"https://{self.shop_url}/blogs/{blog_handle}/{article_handle}"
            print(f"✅ Blog post created successfully!")
            print(f"   Article ID: {article.get('id')}")
            print(f"   URL: {article['url']}")
            return article
        else:
            print(f"❌ Failed to create blog post - API returned: {response}")
            return None
    
    def publish_blog_post(
        self,
        blog_id: int,
        title: str,
        content_html: str,
        author: str = "AI Blog Writer",
        tags: List[str] = None,
        published: bool = True,
        image_url: str = None
    ) -> Optional[Dict]:
        """
        Publish a blog post to a specific Shopify blog (legacy function)
        
        Args:
            blog_id: ID of the blog to publish to
            title: Blog post title
            content_html: HTML content of the blog post
            author: Author name
            tags: List of tags
            published: Whether to publish immediately
            image_url: Featured image URL
            
        Returns:
            Created blog article dictionary or None
        """
        data = {
            'article': {
                'title': title,
                'author': author,
                'body_html': content_html,
                'published': published
            }
        }
        
        if tags:
            data['article']['tags'] = ', '.join(tags)
        
        if image_url:
            data['article']['image'] = {
                'src': image_url
            }
        
        response = self._make_request('POST', f'/blogs/{blog_id}/articles.json', data)
        if response and 'article' in response:
            return response['article']
        return None
    
    def update_blog_post(
        self,
        blog_id: int,
        article_id: int,
        title: str = None,
        content_html: str = None,
        tags: List[str] = None,
        published: bool = None
    ) -> Optional[Dict]:
        """
        Update an existing blog post
        
        Args:
            blog_id: ID of the blog
            article_id: ID of the article to update
            title: New title (optional)
            content_html: New HTML content (optional)
            tags: New tags (optional)
            published: New published status (optional)
            
        Returns:
            Updated blog article dictionary or None
        """
        data = {'article': {}}
        
        if title is not None:
            data['article']['title'] = title
        if content_html is not None:
            data['article']['body_html'] = content_html
        if tags is not None:
            data['article']['tags'] = ', '.join(tags)
        if published is not None:
            data['article']['published'] = published
        
        response = self._make_request('PUT', f'/blogs/{blog_id}/articles/{article_id}.json', data)
        if response and 'article' in response:
            return response['article']
        return None
    
    def get_blog_posts(self, blog_id: int, limit: int = 50) -> List[Dict]:
        """
        Get all blog posts from a specific blog
        
        Args:
            blog_id: ID of the blog
            limit: Maximum number of posts to retrieve
            
        Returns:
            List of blog article dictionaries
        """
        response = self._make_request('GET', f'/blogs/{blog_id}/articles.json?limit={limit}')
        if response and 'articles' in response:
            return response['articles']
        return []
    
    # ========================================
    # PRODUCT FUNCTIONS
    # ========================================
    
    def get_products(self, limit: int = 50) -> List[Dict]:
        """
        Get products from Shopify store
        
        Args:
            limit: Maximum number of products to retrieve
            
        Returns:
            List of product dictionaries
        """
        response = self._make_request('GET', f'/products.json?limit={limit}')
        if response and 'products' in response:
            return response['products']
        return []
    
    def create_product(
        self,
        title: str,
        body_html: str,
        vendor: str = "My Store",
        product_type: str = "",
        tags: List[str] = None,
        images: List[str] = None,
        variants: List[Dict] = None
    ) -> Optional[Dict]:
        """
        Create a new product
        
        Args:
            title: Product title
            body_html: Product description (HTML)
            vendor: Vendor name
            product_type: Product type/category
            tags: List of tags
            images: List of image URLs
            variants: List of variant dictionaries
            
        Returns:
            Created product dictionary or None
        """
        data = {
            'product': {
                'title': title,
                'body_html': body_html,
                'vendor': vendor,
                'product_type': product_type
            }
        }
        
        if tags:
            data['product']['tags'] = ', '.join(tags)
        
        if images:
            data['product']['images'] = [{'src': url} for url in images]
        
        if variants:
            data['product']['variants'] = variants
        
        response = self._make_request('POST', '/products.json', data)
        if response and 'product' in response:
            return response['product']
        return None
    
    # ========================================
    # ANALYTICS FUNCTIONS
    # ========================================
    
    def get_shop_info(self) -> Optional[Dict]:
        """
        Get shop information and basic analytics
        
        Returns:
            Shop info dictionary or None
        """
        response = self._make_request('GET', '/shop.json')
        if response and 'shop' in response:
            return response['shop']
        return None
    
    def get_orders(self, status: str = "any", limit: int = 50) -> List[Dict]:
        """
        Get orders from Shopify store
        
        Args:
            status: Order status (any, open, closed, cancelled)
            limit: Maximum number of orders to retrieve
            
        Returns:
            List of order dictionaries
        """
        response = self._make_request('GET', f'/orders.json?status={status}&limit={limit}')
        if response and 'orders' in response:
            return response['orders']
        return []
    
    def get_order_count(self, status: str = "any") -> int:
        """
        Get count of orders
        
        Args:
            status: Order status (any, open, closed, cancelled)
            
        Returns:
            Number of orders
        """
        response = self._make_request('GET', f'/orders/count.json?status={status}')
        if response and 'count' in response:
            return response['count']
        return 0
    
    def get_analytics_summary(self) -> Dict[str, Any]:
        """
        Get analytics summary with key metrics
        
        Returns:
            Dictionary with analytics data
        """
        summary = {
            'total_orders': 0,
            'open_orders': 0,
            'total_revenue': 0,
            'product_count': 0,
            'blog_count': 0,
            'article_count': 0
        }
        
        try:
            # Get order counts
            summary['total_orders'] = self.get_order_count('any')
            summary['open_orders'] = self.get_order_count('open')
            
            # Get recent orders for revenue calculation
            recent_orders = self.get_orders('any', limit=250)
            summary['total_revenue'] = sum(
                float(order.get('total_price', 0)) 
                for order in recent_orders
            )
            
            # Get product count
            products = self.get_products(limit=1)
            # Note: This is approximate. For exact count, use products/count.json
            summary['product_count'] = len(products)
            
            # Get blog stats
            blogs = self.get_blogs()
            summary['blog_count'] = len(blogs)
            
            # Get article count from first blog
            if blogs:
                articles = self.get_blog_posts(blogs[0]['id'], limit=1)
                summary['article_count'] = len(articles)
            
        except Exception as e:
            print(f"Error fetching analytics: {e}")
        
        return summary
    
    # ========================================
    # ENHANCED ANALYTICS & INFO METHODS
    # ========================================
    
    def get_product_count(self) -> int:
        """Get exact count of products in shop."""
        response = self._make_request('GET', '/products/count.json')
        if response and 'count' in response:
            return response['count']
        return 0
    
    def get_customer_count(self) -> int:
        """Get total number of customers."""
        response = self._make_request('GET', '/customers/count.json')
        if response and 'count' in response:
            return response['count']
        return 0
    
    def get_customers(self, limit: int = 50) -> List[Dict]:
        """Get customer list."""
        response = self._make_request('GET', f'/customers.json?limit={limit}')
        if response and 'customers' in response:
            return response['customers']
        return []
    
    def get_all_customers(self, limit: int = 250) -> List[Dict]:
        """Get all customers with pagination."""
        all_customers = []
        page_info = None
        
        while True:
            if page_info:
                url = f'/customers.json?limit={limit}&page_info={page_info}'
            else:
                url = f'/customers.json?limit={limit}'
            
            response = self._make_request('GET', url)
            if response and 'customers' in response:
                all_customers.extend(response['customers'])
                # Check if there's more data (simplified - Shopify uses link headers)
                if len(response['customers']) < limit:
                    break
            else:
                break
            
            # Simple pagination limit to avoid infinite loops
            if len(all_customers) >= 1000:
                break
        
        return all_customers
    
    def get_customer_emails(self, limit: int = 250, marketing_only: bool = False) -> List[str]:
        """Get list of customer email addresses."""
        customers = self.get_all_customers(limit)
        emails = []
        
        for customer in customers:
            email = customer.get('email')
            if email:
                # Filter for marketing-accepted if requested
                if marketing_only:
                    if customer.get('accepts_marketing', False):
                        emails.append(email)
                else:
                    emails.append(email)
        
        return emails
    
    def create_customer(self, email: str, first_name: str = "", last_name: str = "", 
                       tags: str = "", accepts_marketing: bool = True) -> Optional[Dict]:
        """Create a new customer."""
        customer_data = {
            "customer": {
                "email": email,
                "accepts_marketing": accepts_marketing,
                "tags": tags
            }
        }
        
        if first_name:
            customer_data["customer"]["first_name"] = first_name
        if last_name:
            customer_data["customer"]["last_name"] = last_name
        
        response = self._make_request('POST', '/customers.json', customer_data)
        if response and 'customer' in response:
            return response['customer']
        return None
    
    def search_customers(self, query: str) -> List[Dict]:
        """Search customers by email, name, etc."""
        response = self._make_request('GET', f'/customers/search.json?query={query}')
        if response and 'customers' in response:
            return response['customers']
        return []
    
    def update_customer_tags(self, customer_id: int, tags: str) -> bool:
        """Update customer tags."""
        response = self._make_request('PUT', f'/customers/{customer_id}.json', 
                                      {"customer": {"id": customer_id, "tags": tags}})
        return response is not None
    
    def get_collections(self, limit: int = 50) -> List[Dict]:
        """Get product collections."""
        try:
            response = self._make_request('GET', f'/collections.json?limit={limit}')
            if response and 'collections' in response:
                return response['collections']
        except Exception:
            pass  # Scope may not be available
        return []
    
    def get_collection_count(self) -> int:
        """Get total number of collections."""
        try:
            response = self._make_request('GET', '/collections/count.json')
            if response and 'count' in response:
                return response['count']
        except Exception:
            pass  # Scope may not be available
        return 0
    
    def get_inventory_items(self, limit: int = 50) -> List[Dict]:
        """Get inventory items."""
        response = self._make_request('GET', f'/inventory_items.json?limit={limit}')
        if response and 'inventory_items' in response:
            return response['inventory_items']
        return []
    
    def get_shop_themes(self) -> List[Dict]:
        """Get shop themes."""
        response = self._make_request('GET', '/themes.json')
        if response and 'themes' in response:
            return response['themes']
        return []
    
    def get_active_theme(self) -> Optional[Dict]:
        """Get currently active theme."""
        themes = self.get_shop_themes()
        for theme in themes:
            if theme.get('role') == 'main':
                return theme
        return None
    
    def get_shop_metafields(self, namespace: str = None) -> List[Dict]:
        """Get shop-level metafields."""
        endpoint = '/metafields.json'
        if namespace:
            endpoint += f'?namespace={namespace}'
        
        response = self._make_request('GET', endpoint)
        if response and 'metafields' in response:
            return response['metafields']
        return []
    
    def get_product_by_id(self, product_id: int) -> Optional[Dict]:
        """Get specific product by ID."""
        response = self._make_request('GET', f'/products/{product_id}.json')
        if response and 'product' in response:
            return response['product']
        return None
    
    def search_products(self, query: str, limit: int = 50) -> List[Dict]:
        """Search products by title, tag, or SKU."""
        response = self._make_request('GET', f'/products.json?title={query}&limit={limit}')
        if response and 'products' in response:
            return response['products']
        return []
    
    def get_recent_orders(self, days: int = 7, limit: int = 50) -> List[Dict]:
        """Get orders from the last N days."""
        from datetime import datetime, timedelta
        
        since_date = (datetime.now() - timedelta(days=days)).isoformat()
        response = self._make_request('GET', f'/orders.json?status=any&created_at_min={since_date}&limit={limit}')
        if response and 'orders' in response:
            return response['orders']
        return []
    
    def get_order_by_id(self, order_id: int) -> Optional[Dict]:
        """Get specific order by ID."""
        response = self._make_request('GET', f'/orders/{order_id}.json')
        if response and 'order' in response:
            return response['order']
        return None
    
    def get_sales_by_product(self, days: int = 30) -> Dict[str, Any]:
        """Get sales breakdown by product for the last N days."""
        orders = self.get_recent_orders(days=days, limit=250)
        
        product_sales = {}
        total_revenue = 0
        
        for order in orders:
            for item in order.get('line_items', []):
                product_id = item.get('product_id')
                product_title = item.get('title', 'Unknown')
                quantity = item.get('quantity', 0)
                price = float(item.get('price', 0))
                
                if product_id not in product_sales:
                    product_sales[product_id] = {
                        'title': product_title,
                        'quantity_sold': 0,
                        'revenue': 0
                    }
                
                product_sales[product_id]['quantity_sold'] += quantity
                product_sales[product_id]['revenue'] += price * quantity
                total_revenue += price * quantity
        
        return {
            'period_days': days,
            'total_revenue': total_revenue,
            'products': product_sales,
            'product_count': len(product_sales)
        }
    
    def get_top_selling_products(self, days: int = 30, limit: int = 10) -> List[Dict]:
        """Get top selling products by quantity."""
        sales_data = self.get_sales_by_product(days=days)
        products = sales_data.get('products', {})
        
        # Sort by quantity
        sorted_products = sorted(
            products.items(),
            key=lambda x: x[1]['quantity_sold'],
            reverse=True
        )
        
        return [
            {
                'product_id': product_id,
                **data
            }
            for product_id, data in sorted_products[:limit]
        ]
    
    def get_comprehensive_analytics(self) -> Dict[str, Any]:
        """
        Get comprehensive shop analytics with all available metrics.
        This is the main method for chat to access shop information.
        """
        try:
            shop_info = self.get_shop_info()
            
            analytics = {
                'shop': {
                    'name': shop_info.get('name', 'N/A') if shop_info else 'N/A',
                    'email': shop_info.get('email', 'N/A') if shop_info else 'N/A',
                    'domain': shop_info.get('domain', 'N/A') if shop_info else 'N/A',
                    'currency': shop_info.get('currency', 'USD') if shop_info else 'USD',
                    'timezone': shop_info.get('iana_timezone', 'N/A') if shop_info else 'N/A',
                    'plan': shop_info.get('plan_name', 'N/A') if shop_info else 'N/A'
                },
                'products': {
                    'total_count': self.get_product_count(),
                    'published_count': len(self.get_products(limit=250))
                },
                'orders': {
                    'total_count': self.get_order_count('any'),
                    'open_count': self.get_order_count('open'),
                    'closed_count': self.get_order_count('closed')
                },
                'customers': {
                    'total_count': self.get_customer_count()
                },
                'collections': {
                    'total_count': self.get_collection_count()
                },
                'blogs': {
                    'total_count': len(self.get_blogs())
                },
                'revenue': {
                    'recent_orders_total': 0
                },
                'top_products': []
            }
            
            # Calculate revenue from recent orders
            recent_orders = self.get_orders('any', limit=250)
            analytics['revenue']['recent_orders_total'] = sum(
                float(order.get('total_price', 0)) for order in recent_orders
            )
            
            # Get top selling products
            analytics['top_products'] = self.get_top_selling_products(days=30, limit=5)
            
            return analytics
            
        except Exception as e:
            print(f"Error fetching comprehensive analytics: {e}")
            return {
                'error': str(e),
                'shop': {},
                'products': {'total_count': 0},
                'orders': {'total_count': 0},
                'customers': {'total_count': 0}
            }


# Helper function to generate blog HTML from campaign data
def generate_blog_html(
    title: str,
    content: str,
    images: List[str] = None,
    author: str = "AI Content Creator",
    date: str = None
) -> str:
    """
    Generate professional HTML blog post
    
    Args:
        title: Blog post title
        content: Main content (can include HTML)
        images: List of image URLs to embed
        author: Author name
        date: Publication date
        
    Returns:
        Complete HTML string
    """
    if date is None:
        date = datetime.now().strftime("%B %d, %Y")
    
    # Build image gallery if images provided
    image_html = ""
    if images:
        image_html = '<div class="image-gallery">'
        for img_url in images[:4]:  # Max 4 images
            image_html += f'<img src="{img_url}" alt="Blog image" class="blog-image" />'
        image_html += '</div>'
    
    html = f"""
    <div class="blog-post">
        <div class="blog-header">
            <h1 class="blog-title">{title}</h1>
            <div class="blog-meta">
                <span class="author">By {author}</span>
                <span class="date">{date}</span>
            </div>
        </div>
        
        {image_html}
        
        <div class="blog-content">
            {content}
        </div>
    </div>
    
    <style>
        .blog-post {{
            font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.8;
            color: #111827;
            max-width: 800px;
            margin: 0 auto;
        }}
        
        .blog-header {{
            margin-bottom: 2rem;
        }}
        
        .blog-title {{
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 1rem;
            color: #1f2937;
            line-height: 1.2;
        }}
        
        .blog-meta {{
            display: flex;
            gap: 1rem;
            font-size: 0.95rem;
            color: #6b7280;
        }}
        
        .blog-meta span {{
            display: flex;
            align-items: center;
        }}
        
        .image-gallery {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1rem;
            margin: 2rem 0;
        }}
        
        .blog-image {{
            width: 100%;
            height: auto;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s ease;
        }}
        
        .blog-image:hover {{
            transform: scale(1.02);
        }}
        
        .blog-content {{
            font-size: 1.1rem;
            line-height: 1.8;
        }}
        
        .blog-content h2 {{
            font-size: 1.8rem;
            margin-top: 2rem;
            margin-bottom: 1rem;
            color: #1f2937;
            border-bottom: 2px solid #4f46e5;
            padding-bottom: 0.5rem;
        }}
        
        .blog-content h3 {{
            font-size: 1.5rem;
            margin-top: 1.5rem;
            margin-bottom: 0.75rem;
            color: #374151;
        }}
        
        .blog-content p {{
            margin-bottom: 1.5rem;
        }}
        
        .blog-content ul, .blog-content ol {{
            margin-bottom: 1.5rem;
            padding-left: 2rem;
        }}
        
        .blog-content li {{
            margin-bottom: 0.5rem;
        }}
        
        .blog-content blockquote {{
            border-left: 4px solid #4f46e5;
            padding-left: 1.5rem;
            margin: 2rem 0;
            font-style: italic;
            color: #4b5563;
        }}
        
        @media (max-width: 768px) {{
            .blog-title {{
                font-size: 2rem;
            }}
            
            .blog-content {{
                font-size: 1rem;
            }}
            
            .image-gallery {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
    """
    
    return html
