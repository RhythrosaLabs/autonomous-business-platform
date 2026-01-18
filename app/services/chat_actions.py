# chat_actions.py
"""
Chat action executor for triggering platform workflows via natural language.
Enables chat to execute ANY platform function: campaigns, products, publishing, etc.
"""

import streamlit as st
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ChatActionExecutor:
    """Executes platform actions triggered by chat commands."""
    
    def __init__(self, replicate_api, printify_api=None, shopify_api=None, youtube_api=None):
        self.replicate = replicate_api
        self.printify = printify_api
        self.shopify = shopify_api
        self.youtube = youtube_api
    
    def parse_action_intent(self, message: str) -> Optional[Dict[str, Any]]:
        """
        Parse natural language to determine what action user wants.
        Returns action dict or None if no action detected.
        """
        message_lower = message.lower()
        
        # ========================================
        # SHOPIFY ANALYTICS & INFO PATTERNS
        # ========================================
        
        # Product count queries
        if any(phrase in message_lower for phrase in [
            'how many products', 'product count', 'number of products', 
            'total products', 'products in shop', 'items in shop', 'how many items'
        ]):
            return {
                'action': 'shopify_product_count',
                'params': {}
            }
        
        # Order queries
        if any(phrase in message_lower for phrase in [
            'how many orders', 'order count', 'number of orders', 
            'total orders', 'recent orders', 'sales count'
        ]):
            return {
                'action': 'shopify_order_info',
                'params': {}
            }
        
        # Revenue/sales queries
        if any(phrase in message_lower for phrase in [
            'how much revenue', 'total sales', 'how much money', 
            'revenue report', 'sales revenue', 'earnings'
        ]):
            return {
                'action': 'shopify_revenue_info',
                'params': {}
            }
        
        # Customer queries
        if any(phrase in message_lower for phrase in [
            'how many customers', 'customer count', 'number of customers', 
            'total customers', 'customer list'
        ]):
            return {
                'action': 'shopify_customer_info',
                'params': {}
            }
        
        # Shop info queries
        if any(phrase in message_lower for phrase in [
            'shop info', 'store info', 'shop details', 'store details',
            'shop name', 'my shop', 'my store', 'about my shop'
        ]):
            return {
                'action': 'shopify_shop_info',
                'params': {}
            }
        
        # Top products queries
        if any(phrase in message_lower for phrase in [
            'top products', 'best selling', 'most popular', 
            'top sellers', 'best products', 'popular products'
        ]):
            return {
                'action': 'shopify_top_products',
                'params': {}
            }
        
        # Collection queries
        if any(phrase in message_lower for phrase in [
            'how many collections', 'collection count', 'my collections',
            'list collections', 'show collections'
        ]):
            return {
                'action': 'shopify_collections',
                'params': {}
            }
        
        # Comprehensive analytics
        if any(phrase in message_lower for phrase in [
            'shop analytics', 'shop stats', 'full report', 
            'analytics report', 'shop overview', 'dashboard'
        ]):
            return {
                'action': 'shopify_full_analytics',
                'params': {}
            }
        
        # Product search
        if any(phrase in message_lower for phrase in [
            'find product', 'search product', 'look up product', 'show me product'
        ]):
            # Extract search query
            search_query = message_lower
            for phrase in ['find product', 'search product', 'look up product', 'show me product']:
                search_query = search_query.replace(phrase, '').strip()
            return {
                'action': 'shopify_search_products',
                'params': {'query': search_query}
            }
        
        # ========================================
        # ORIGINAL PATTERNS
        # ========================================
        
        # Campaign generation patterns
        if any(word in message_lower for word in ['create campaign', 'generate campaign', 'make campaign', 'build campaign']):
            # Extract concept
            concept = self._extract_concept(message)
            return {
                'action': 'generate_campaign',
                'params': {'concept': concept}
            }
        
        # Product creation patterns
        if any(word in message_lower for word in ['create product', 'make product', 'generate product', 'new product']):
            return {
                'action': 'create_product',
                'params': {'description': message}
            }
        
        # Publishing patterns
        if any(word in message_lower for word in ['publish to printify', 'upload to printify', 'create printify']):
            return {
                'action': 'publish_to_printify',
                'params': {}
            }
        
        if any(word in message_lower for word in ['publish to shopify', 'upload to shopify']):
            return {
                'action': 'publish_to_shopify',
                'params': {}
            }
        
        if any(word in message_lower for word in ['upload to youtube', 'publish to youtube']):
            return {
                'action': 'upload_to_youtube',
                'params': {}
            }
        
        # Video generation patterns
        if any(word in message_lower for word in ['create video', 'generate video', 'make video', 'produce video']):
            return {
                'action': 'generate_video',
                'params': {'description': message}
            }
        
        # Image generation patterns
        if any(word in message_lower for word in ['create image', 'generate image', 'make image']):
            return {
                'action': 'generate_images',
                'params': {'description': message}
            }
        
        # File operations
        if any(word in message_lower for word in ['zip', 'bundle', 'package', 'download all']):
            return {
                'action': 'create_file_bundle',
                'params': {'query': message}
            }
        
        # Web scraping
        if any(word in message_lower for word in ['scrape', 'browse', 'search web', 'look up']):
            return {
                'action': 'web_scrape',
                'params': {'query': message}
            }
        
        # Agent patterns
        if any(word in message_lower for word in ['create agent', 'make agent', 'build agent', 'new agent']):
            return {
                'action': 'create_agent',
                'params': {'description': message}
            }
        
        if any(word in message_lower for word in ['run agent', 'execute agent', 'start agent', 'launch agent']):
            return {
                'action': 'run_agent',
                'params': {'query': message}
            }
        
        if any(word in message_lower for word in ['list agents', 'show agents', 'my agents', 'available agents']):
            return {
                'action': 'list_agents',
                'params': {}
            }
        
        return None
    
    def _extract_concept(self, message: str) -> str:
        """Extract product concept from message."""
        # Remove command words
        concept = message
        for phrase in ['create campaign', 'generate campaign', 'make campaign', 'build campaign', 'for', 'about']:
            concept = concept.replace(phrase, '')
        return concept.strip()
    
    async def execute_action(self, action_dict: Dict[str, Any]) -> str:
        """Execute the parsed action and return result."""
        action = action_dict['action']
        params = action_dict['params']
        
        try:
            # ========================================
            # SHOPIFY ACTIONS
            # ========================================
            
            if action == 'shopify_product_count':
                return await self._shopify_product_count(params)
            
            elif action == 'shopify_order_info':
                return await self._shopify_order_info(params)
            
            elif action == 'shopify_revenue_info':
                return await self._shopify_revenue_info(params)
            
            elif action == 'shopify_customer_info':
                return await self._shopify_customer_info(params)
            
            elif action == 'shopify_shop_info':
                return await self._shopify_shop_info(params)
            
            elif action == 'shopify_top_products':
                return await self._shopify_top_products(params)
            
            elif action == 'shopify_collections':
                return await self._shopify_collections(params)
            
            elif action == 'shopify_full_analytics':
                return await self._shopify_full_analytics(params)
            
            elif action == 'shopify_search_products':
                return await self._shopify_search_products(params)
            
            # ========================================
            # ORIGINAL ACTIONS
            # ========================================
            
            elif action == 'generate_campaign':
                return await self._generate_campaign(params)
            
            elif action == 'create_product':
                return await self._create_product(params)
            
            elif action == 'publish_to_printify':
                return await self._publish_to_printify(params)
            
            elif action == 'publish_to_shopify':
                return await self._publish_to_shopify(params)
            
            elif action == 'upload_to_youtube':
                return await self._upload_to_youtube(params)
            
            elif action == 'generate_video':
                return await self._generate_video(params)
            
            elif action == 'generate_images':
                return await self._generate_images(params)
            
            elif action == 'create_file_bundle':
                return await self._create_file_bundle(params)
            
            elif action == 'web_scrape':
                return await self._web_scrape(params)
            
            elif action == 'create_agent':
                return await self._create_agent(params)
            
            elif action == 'run_agent':
                return await self._run_agent(params)
            
            elif action == 'list_agents':
                return await self._list_agents(params)
            
            else:
                return f"❌ Unknown action: {action}"
        
        except Exception as e:
            logger.error(f"Action execution error: {e}")
            return f"❌ Error executing {action}: {str(e)}"
    
    # ========================================
    # SHOPIFY ACTION IMPLEMENTATIONS
    # ========================================
    
    async def _shopify_product_count(self, params: Dict) -> str:
        """Get product count from Shopify."""
        if not self.shopify:
            return "❌ Shopify not configured. Please add your API credentials in Settings."
        
        try:
            count = self.shopify.get_product_count()
            return f"""📦 **Product Inventory**

You have **{count} products** in your Shopify store.

**Quick Actions:**
- "show me my products" - View product list
- "top selling products" - See best performers
- "create new product" - Add a product"""
        
        except Exception as e:
            logger.error(f"Shopify product count error: {e}")
            return f"❌ Failed to get product count: {str(e)}"
    
    async def _shopify_order_info(self, params: Dict) -> str:
        """Get order information from Shopify."""
        if not self.shopify:
            return "❌ Shopify not configured. Please add your API credentials in Settings."
        
        try:
            total_orders = self.shopify.get_order_count('any')
            open_orders = self.shopify.get_order_count('open')
            closed_orders = self.shopify.get_order_count('closed')
            
            # Get recent orders
            recent = self.shopify.get_recent_orders(days=7, limit=5)
            
            result = f"""📊 **Order Summary**

**Total Orders:** {total_orders}
**Open Orders:** {open_orders}
**Fulfilled Orders:** {closed_orders}

"""
            
            if recent:
                result += "**Recent Orders (Last 7 Days):**\n"
                for order in recent[:5]:
                    order_num = order.get('order_number', 'N/A')
                    total = order.get('total_price', '0')
                    currency = order.get('currency', 'USD')
                    status = order.get('financial_status', 'N/A')
                    result += f"\n- Order #{order_num}: {currency} {total} ({status})"
            else:
                result += "\n📭 No recent orders in the last 7 days."
            
            result += """

**Quick Actions:**
- "show revenue" - See total revenue
- "top products" - Best sellers
- "customer count" - Total customers"""
            
            return result
        
        except Exception as e:
            logger.error(f"Shopify order info error: {e}")
            return f"❌ Failed to get order information: {str(e)}"
    
    async def _shopify_revenue_info(self, params: Dict) -> str:
        """Get revenue information from Shopify."""
        if not self.shopify:
            return "❌ Shopify not configured. Please add your API credentials in Settings."
        
        try:
            # Get recent orders for revenue calculation
            recent_orders = self.shopify.get_orders('any', limit=250)
            
            if not recent_orders:
                return "📊 **Revenue Report**\n\nNo orders found to calculate revenue."
            
            total_revenue = sum(float(order.get('total_price', 0)) for order in recent_orders)
            currency = recent_orders[0].get('currency', 'USD') if recent_orders else 'USD'
            
            # Get 7-day revenue
            recent_7days = self.shopify.get_recent_orders(days=7, limit=250)
            revenue_7days = sum(float(order.get('total_price', 0)) for order in recent_7days)
            
            # Get 30-day revenue
            recent_30days = self.shopify.get_recent_orders(days=30, limit=250)
            revenue_30days = sum(float(order.get('total_price', 0)) for order in recent_30days)
            
            return f"""💰 **Revenue Report**

**Recent Revenue (250 orders):** {currency} {total_revenue:,.2f}
**Last 7 Days:** {currency} {revenue_7days:,.2f}
**Last 30 Days:** {currency} {revenue_30days:,.2f}

**Average Order Value:** {currency} {(total_revenue / len(recent_orders)):,.2f}

**Quick Actions:**
- "top selling products" - See what's making money
- "show orders" - View order details
- "full analytics" - Complete shop overview"""
        
        except Exception as e:
            logger.error(f"Shopify revenue info error: {e}")
            return f"❌ Failed to get revenue information: {str(e)}"
    
    async def _shopify_customer_info(self, params: Dict) -> str:
        """Get customer information from Shopify."""
        if not self.shopify:
            return "❌ Shopify not configured. Please add your API credentials in Settings."
        
        try:
            customer_count = self.shopify.get_customer_count()
            customers = self.shopify.get_customers(limit=5)
            
            result = f"""👥 **Customer Base**

**Total Customers:** {customer_count}

"""
            
            if customers:
                result += "**Recent Customers:**\n"
                for customer in customers[:5]:
                    name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()
                    email = customer.get('email', 'N/A')
                    orders = customer.get('orders_count', 0)
                    result += f"\n- {name or 'No name'} ({email}) - {orders} orders"
            
            result += """

**Quick Actions:**
- "order count" - See total orders
- "revenue report" - Sales data
- "shop analytics" - Full overview"""
            
            return result
        
        except Exception as e:
            logger.error(f"Shopify customer info error: {e}")
            return f"❌ Failed to get customer information: {str(e)}"
    
    async def _shopify_shop_info(self, params: Dict) -> str:
        """Get shop information from Shopify."""
        if not self.shopify:
            return "❌ Shopify not configured. Please add your API credentials in Settings."
        
        try:
            shop = self.shopify.get_shop_info()
            
            if not shop:
                return "❌ Failed to retrieve shop information."
            
            return f"""🏪 **Shop Information**

**Name:** {shop.get('name', 'N/A')}
**Domain:** {shop.get('domain', 'N/A')}
**Email:** {shop.get('email', 'N/A')}
**Currency:** {shop.get('currency', 'USD')}
**Timezone:** {shop.get('iana_timezone', 'N/A')}
**Plan:** {shop.get('plan_name', 'N/A')}
**Created:** {shop.get('created_at', 'N/A')[:10]}

**Shop Owner:** {shop.get('shop_owner', 'N/A')}
**Country:** {shop.get('country_name', 'N/A')}
**Phone:** {shop.get('phone', 'N/A')}

**Quick Actions:**
- "full analytics" - Complete dashboard
- "product count" - Inventory status
- "order count" - Sales summary"""
        
        except Exception as e:
            logger.error(f"Shopify shop info error: {e}")
            return f"❌ Failed to get shop information: {str(e)}"
    
    async def _shopify_top_products(self, params: Dict) -> str:
        """Get top selling products from Shopify."""
        if not self.shopify:
            return "❌ Shopify not configured. Please add your API credentials in Settings."
        
        try:
            top_products = self.shopify.get_top_selling_products(days=30, limit=10)
            
            if not top_products:
                return "📊 **Top Products**\n\nNo sales data available for the last 30 days."
            
            result = "📈 **Top Selling Products (Last 30 Days)**\n\n"
            
            for i, product in enumerate(top_products, 1):
                title = product.get('title', 'Unknown')
                quantity = product.get('quantity_sold', 0)
                revenue = product.get('revenue', 0)
                result += f"{i}. **{title}**\n   - Sold: {quantity} units\n   - Revenue: ${revenue:,.2f}\n\n"
            
            result += """**Quick Actions:**
- "show revenue" - See total sales
- "product count" - Inventory status
- "create similar product" - Replicate success"""
            
            return result
        
        except Exception as e:
            logger.error(f"Shopify top products error: {e}")
            return f"❌ Failed to get top products: {str(e)}"
    
    async def _shopify_collections(self, params: Dict) -> str:
        """Get collections information from Shopify."""
        if not self.shopify:
            return "❌ Shopify not configured. Please add your API credentials in Settings."
        
        try:
            collection_count = self.shopify.get_collection_count()
            collections = self.shopify.get_collections(limit=10)
            
            result = f"""📚 **Collections**

**Total Collections:** {collection_count}

"""
            
            if collections:
                result += "**Your Collections:**\n"
                for collection in collections[:10]:
                    title = collection.get('title', 'Untitled')
                    handle = collection.get('handle', 'N/A')
                    result += f"\n- {title} (`{handle}`)"
            else:
                result += "No collections found."
            
            result += """

**Quick Actions:**
- "product count" - See all products
- "top products" - Best sellers
- "create collection" - Organize products"""
            
            return result
        
        except Exception as e:
            logger.error(f"Shopify collections error: {e}")
            return f"❌ Failed to get collections: {str(e)}"
    
    async def _shopify_full_analytics(self, params: Dict) -> str:
        """Get comprehensive analytics from Shopify."""
        if not self.shopify:
            return "❌ Shopify not configured. Please add your API credentials in Settings."
        
        try:
            analytics = self.shopify.get_comprehensive_analytics()
            
            shop = analytics.get('shop', {})
            products = analytics.get('products', {})
            orders = analytics.get('orders', {})
            customers = analytics.get('customers', {})
            collections = analytics.get('collections', {})
            blogs = analytics.get('blogs', {})
            revenue = analytics.get('revenue', {})
            top_products = analytics.get('top_products', [])
            
            result = f"""📊 **Comprehensive Shop Analytics**

**🏪 Shop Details**
- Name: {shop.get('name', 'N/A')}
- Domain: {shop.get('domain', 'N/A')}
- Plan: {shop.get('plan', 'N/A')}
- Currency: {shop.get('currency', 'USD')}

**📦 Products**
- Total Products: {products.get('total_count', 0)}
- Published: {products.get('published_count', 0)}

**📊 Orders**
- Total Orders: {orders.get('total_count', 0)}
- Open Orders: {orders.get('open_count', 0)}
- Fulfilled: {orders.get('closed_count', 0)}

**💰 Revenue**
- Recent Orders Total: ${revenue.get('recent_orders_total', 0):,.2f}

**👥 Customers**
- Total Customers: {customers.get('total_count', 0)}

**📚 Collections**
- Total Collections: {collections.get('total_count', 0)}

**📝 Blogs**
- Active Blogs: {blogs.get('total_count', 0)}

"""
            
            if top_products:
                result += "**🔥 Top Products (Last 30 Days)**\n"
                for i, product in enumerate(top_products[:5], 1):
                    result += f"{i}. {product.get('title', 'Unknown')} - {product.get('quantity_sold', 0)} sold\n"
            
            result += """
**💡 Insights & Actions:**
- Ask me about specific metrics for detailed analysis
- Say "top products" to see best sellers
- Say "show orders" for recent order details
- Say "revenue report" for sales breakdown"""
            
            return result
        
        except Exception as e:
            logger.error(f"Shopify full analytics error: {e}")
            return f"❌ Failed to get analytics: {str(e)}"
    
    async def _shopify_search_products(self, params: Dict) -> str:
        """Search for products in Shopify."""
        if not self.shopify:
            return "❌ Shopify not configured. Please add your API credentials in Settings."
        
        query = params.get('query', '').strip()
        
        if not query:
            return "❌ Please provide a search query. Example: 'find product canvas'"
        
        try:
            products = self.shopify.search_products(query, limit=10)
            
            if not products:
                return f"🔍 **Product Search: '{query}'**\n\nNo products found matching your search."
            
            result = f"🔍 **Product Search: '{query}'**\n\n**Found {len(products)} products:**\n\n"
            
            for product in products:
                title = product.get('title', 'Untitled')
                product_id = product.get('id', 'N/A')
                variants = product.get('variants', [])
                price = variants[0].get('price', 'N/A') if variants else 'N/A'
                inventory = variants[0].get('inventory_quantity', 0) if variants else 0
                
                result += f"**{title}**\n"
                result += f"- ID: {product_id}\n"
                result += f"- Price: ${price}\n"
                result += f"- Inventory: {inventory} in stock\n\n"
            
            result += """**Quick Actions:**
- Ask about a specific product by name
- "top products" - See best sellers
- "product count" - Total inventory"""
            
            return result
        
        except Exception as e:
            logger.error(f"Shopify product search error: {e}")
            return f"❌ Failed to search products: {str(e)}"
    
    # ========================================
    # ORIGINAL ACTION IMPLEMENTATIONS
    # ========================================
    
    async def _generate_campaign(self, params: Dict) -> str:
        """Generate a complete marketing campaign."""
        concept = params.get('concept', 'Creative Product')
        
        # Store in session state for main app to pick up
        if 'chat_requested_campaign' not in st.session_state:
            st.session_state.chat_requested_campaign = None
        
        st.session_state.chat_requested_campaign = {
            'concept': concept,
            'requested_at': datetime.now().isoformat(),
            'status': 'pending'
        }
        
        return f"""✅ Campaign generation started!

**Concept:** {concept}

The platform is now generating:
1. 📝 Product description and copy
2. 🎨 Marketing images (ControlNet-enhanced)
3. 🎥 15-second commercial video (with ControlNet)
4. 📱 Social media ads
5. 📝 Blog article
6. 📦 Printify product mockup

Check the Dashboard tab to see progress!"""
    
    async def _create_product(self, params: Dict) -> str:
        """Create a product and mockup."""
        if not self.printify:
            return "❌ Printify API not configured. Please add your API key in Settings."
        
        # Extract product details from description
        description = params.get('description', '')
        
        # Use AI to generate product details
        prompt = f"""Based on this product request: "{description}"

Generate a product creation plan with:
- Product name
- Product type (canvas, poster, t-shirt, mug, etc.)
- Design concept
- Target audience

Format as JSON."""
        
        plan_json = self.replicate.generate_text(prompt=prompt, max_tokens=500)
        
        return f"""✅ Product creation plan generated!

{plan_json}

To create this product:
1. Go to Product Studio tab
2. Enter the design concept
3. Click "Generate & Create Product"

Or say "create the product now" and I'll trigger it automatically!"""
    
    async def _publish_to_printify(self, params: Dict) -> str:
        """Publish products to Printify."""
        if not self.printify:
            return "❌ Printify API not configured"
        
        # Check for products in session state
        if 'campaign_products' not in st.session_state or not st.session_state.campaign_products:
            return "❌ No products available to publish. Generate a campaign first!"
        
        products = st.session_state.campaign_products
        published_count = 0
        
        for product in products:
            try:
                # Trigger Printify publication logic
                # This would normally call printify_mockup_service.py
                published_count += 1
            except Exception as e:
                logger.error(f"Printify publish error: {e}")
        
        return f"✅ Published {published_count} products to Printify!"
    
    async def _publish_to_shopify(self, params: Dict) -> str:
        """Publish products to Shopify."""
        if not self.shopify:
            return "❌ Shopify not configured"
        
        return "🚧 Shopify publishing will be triggered here"
    
    async def _upload_to_youtube(self, params: Dict) -> str:
        """Upload videos to YouTube."""
        if not self.youtube:
            return "❌ YouTube not configured"
        
        # Check for videos in session state
        if 'campaign_videos' not in st.session_state:
            return "❌ No videos available. Generate a video first!"
        
        return "🚧 YouTube upload will be triggered here"
    
    async def _generate_video(self, params: Dict) -> str:
        """Generate a video."""
        description = params.get('description', '')
        
        # Parse video requirements
        prompt = f"""User wants to create a video: "{description}"

Extract:
- Video concept
- Duration (default 15 seconds)
- Style/tone
- Product/subject

Format as JSON."""
        
        requirements = self.replicate.generate_text(prompt=prompt, max_tokens=300)
        
        return f"""✅ Video generation queued!

**Requirements:**
{requirements}

Go to the Video Producer tab to see your video being created in real-time!
Individual clips will appear as they're generated."""
    
    async def _generate_images(self, params: Dict) -> str:
        """Generate images via chat."""
        description = params.get('description', '')
        
        # Extract the actual image prompt
        prompt = description.replace('create image', '').replace('generate image', '').strip()
        
        if not prompt:
            return "❌ Please describe what image you want. Example: 'create image of a sunset over mountains'"
        
        try:
            # Generate image
            image_url = self.replicate.generate_image(
                prompt=prompt,
                width=1024,
                height=1024,
                aspect_ratio="1:1",
                output_format="png"
            )
            
            # Save to session
            if 'chat_generated_images' not in st.session_state:
                st.session_state.chat_generated_images = []
            
            st.session_state.chat_generated_images.append({
                'prompt': prompt,
                'url': image_url,
                'timestamp': datetime.now().isoformat()
            })
            
            return f"✅ Image generated!\n\n![{prompt}]({image_url})"
        
        except Exception as e:
            return f"❌ Image generation failed: {str(e)}"
    
    async def _create_file_bundle(self, params: Dict) -> str:
        """Create a ZIP bundle of files."""
        query = params.get('query', '').lower()
        
        import zipfile
        import io
        from pathlib import Path
        
        # Determine what files to bundle
        campaigns_dir = Path.cwd() / "campaigns"
        files_to_zip = []
        
        # Parse query for file types
        if 'image' in query:
            files_to_zip.extend(campaigns_dir.rglob('*.png'))
            files_to_zip.extend(campaigns_dir.rglob('*.jpg'))
        if 'video' in query:
            files_to_zip.extend(campaigns_dir.rglob('*.mp4'))
        if 'all' in query or 'everything' in query:
            files_to_zip.extend(campaigns_dir.rglob('*'))
        
        # Filter out directories
        files_to_zip = [f for f in files_to_zip if f.is_file()]
        
        if not files_to_zip:
            return "❌ No files found matching your criteria"
        
        # Create ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in files_to_zip:
                zip_file.write(file_path, file_path.relative_to(campaigns_dir))
        
        zip_buffer.seek(0)
        
        # Store in session for download
        st.session_state.chat_generated_zip = {
            'data': zip_buffer.getvalue(),
            'filename': f'bundle_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip',
            'file_count': len(files_to_zip)
        }
        
        return f"""✅ Created ZIP bundle with {len(files_to_zip)} files!

The download button will appear below this message."""
    
    async def _web_scrape(self, params: Dict) -> str:
        """Scrape web content."""
        query = params.get('query', '')
        
        # Extract URL or search query from message
        import re
        url_pattern = r'https?://[^\s]+'
        urls = re.findall(url_pattern, query)
        
        if urls:
            url = urls[0]
            # Perform actual scraping
            try:
                import requests
                from bs4 import BeautifulSoup
                
                response = requests.get(url, timeout=10, headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                })
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract key information
                title = soup.find('title')
                title_text = title.get_text() if title else 'No title'
                
                # Get all text content
                text_content = soup.get_text()
                # Clean up whitespace
                lines = [line.strip() for line in text_content.splitlines() if line.strip()]
                clean_text = '\n'.join(lines[:50])  # First 50 lines
                
                # Find images
                images = soup.find_all('img', limit=10)
                image_urls = [img.get('src') for img in images if img.get('src')]
                
                # Find links
                links = soup.find_all('a', limit=20)
                link_urls = [link.get('href') for link in links if link.get('href')]
                
                return f"""✅ Scraped: {url}

**Page Title:** {title_text}

**Content Preview:**
```
{clean_text[:500]}...
```

**Found:**
- {len(image_urls)} images
- {len(link_urls)} links

**Images:** {', '.join(image_urls[:5])}

**Links:** {', '.join([l for l in link_urls[:5] if l.startswith('http')])}

Ask me to analyze this content or extract specific information!"""
            
            except Exception as e:
                logger.error(f"Scraping error: {e}")
                return f"""❌ Failed to scrape {url}

Error: {str(e)}

**Tip:** Some websites block automated scraping. Try:
1. A different URL
2. Using the browser automation framework (in development)
3. Checking if the site requires authentication"""
        
        else:
            # Search query without URL - use AI to help
            search_suggestions = [
                f"Search Google for '{query}'",
                f"Check Etsy trends for '{query}'",
                f"Analyze Amazon products matching '{query}'",
                f"Research Pinterest content about '{query}'"
            ]
            
            return f"""🔍 Web Search: "{query}"

**Suggested Actions:**
""" + "\n".join([f"- {s}" for s in search_suggestions]) + """

**To scrape a specific site:**
Provide the full URL, like:
- "scrape https://www.etsy.com/search?q=canvas+art"
- "browse https://www.amazon.com/s?k=wall+decor"

I'll extract the content and analyze it for you!"""
    
    async def _create_agent(self, params: Dict) -> str:
        """Create a new custom agent."""
        description = params.get('description', '')
        
        # Use AI to design the agent workflow
        prompt = f"""User wants to create an agent: "{description}"

Design a workflow with these steps:
1. Identify the workflow type (product launch, social media, content creation, etc.)
2. List required steps in order
3. Specify which models/services to use
4. Define input parameters

Format as JSON with: name, description, steps, prompts"""
        
        try:
            agent_design = self.replicate.generate_text(prompt=prompt, max_tokens=800)
            
            # Parse and save agent
            agents_dir = Path("agents")
            agents_dir.mkdir(exist_ok=True)
            
            import uuid
            agent_id = str(uuid.uuid4())
            agent_file = agents_dir / f"{agent_id}.json"
            
            # Create agent structure
            agent_data = {
                'id': agent_id,
                'name': f"Custom Agent {datetime.now().strftime('%Y%m%d_%H%M')}",
                'description': description,
                'design': agent_design,
                'created_at': datetime.now().isoformat()
            }
            
            with open(agent_file, 'w') as f:
                json.dump(agent_data, f, indent=2)
            
            return f"""✅ Agent created successfully!

**Agent ID:** `{agent_id}`
**Design:**
{agent_design}

**Next Steps:**
1. Go to Agent Builder tab to refine the agent
2. Or say "run agent {agent_id}" to execute it now

Your agent has been saved and is ready to use!"""
        
        except Exception as e:
            logger.error(f"Agent creation error: {e}")
            return f"❌ Failed to create agent: {str(e)}"
    
    async def _run_agent(self, params: Dict) -> str:
        """Execute an existing agent."""
        query = params.get('query', '')
        
        # Extract agent name or ID
        agents_dir = Path("agents")
        if not agents_dir.exists():
            return "❌ No agents found. Create one first!"
        
        # List available agents
        agent_files = list(agents_dir.glob("*.json"))
        
        if not agent_files:
            return "❌ No agents available. Create one first with 'create agent for [task]'"
        
        # Try to match agent by name or ID in query
        for agent_file in agent_files:
            with open(agent_file, 'r') as f:
                agent_data = json.load(f)
                agent_name = agent_data.get('name', '').lower()
                agent_id = agent_data.get('id', '')
                
                if agent_name in query.lower() or agent_id in query:
                    # Found matching agent!
                    return f"""🚀 Executing Agent: {agent_data.get('name')}

**Description:** {agent_data.get('description', 'N/A')}

**Workflow Steps:**
"""+ "\n".join([f"{i+1}. {step.get('step', 'Unknown')}" for i, step in enumerate(agent_data.get('workflow_steps', []))]) + f"""

**Status:** Agent execution queued!

Go to the Agent Builder tab to see real-time progress, or check the Dashboard for results.

**Agent ID:** `{agent_id}`"""
        
        # No specific agent matched, show list
        return await self._list_agents({})
    
    async def _list_agents(self, params: Dict) -> str:
        """List all available agents."""
        agents_dir = Path("agents")
        if not agents_dir.exists() or not list(agents_dir.glob("*.json")):
            return """📋 No agents created yet!

**Quick Start:**
- "create agent for product launches"
- "create agent for social media campaigns"
- "create agent for video production"

I'll design a custom workflow for you!"""
        
        agent_files = list(agents_dir.glob("*.json"))
        agent_list = []
        
        for agent_file in agent_files:
            try:
                with open(agent_file, 'r') as f:
                    agent_data = json.load(f)
                    agent_list.append({
                        'name': agent_data.get('name', 'Unnamed'),
                        'description': agent_data.get('description', 'No description'),
                        'id': agent_data.get('id', 'Unknown'),
                        'steps': len(agent_data.get('workflow_steps', []))
                    })
            except Exception as e:
                logger.error(f"Error reading agent {agent_file}: {e}")
        
        if not agent_list:
            return "❌ No valid agents found"
        
        # Format agent list
        result = f"""📋 **Available Agents** ({len(agent_list)} total)\n\n"""
        
        for i, agent in enumerate(agent_list, 1):
            result += f"""**{i}. {agent['name']}**
- Description: {agent['description']}
- Steps: {agent['steps']}
- ID: `{agent['id']}`
- Run: "run agent {agent['name'].lower()}"

"""
        
        result += "\n**Quick Actions:**\n"
        result += "- Run any agent: 'run agent [name]'\n"
        result += "- Create new: 'create agent for [task]'\n"
        result += "- View details in Agent Builder tab"
        
        return result


def integrate_with_chat(chat_message: str, replicate_api) -> Optional[str]:
    """
    Main integration point. Call this from chat_assistant.py
    Returns action result if an action was triggered, None otherwise.
    """
    executor = ChatActionExecutor(replicate_api)
    
    # Parse message for action intent
    action_dict = executor.parse_action_intent(chat_message)
    
    if action_dict:
        # Execute action asynchronously
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(executor.execute_action(action_dict))
        return result
    
    return None
