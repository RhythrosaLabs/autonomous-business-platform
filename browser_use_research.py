"""
Browser-Use Research & Intelligence Module
==========================================

Powerful automation for product research, market intelligence, and competitor analysis
using browser-use library with LLM-powered navigation.

Features:
- 🔍 Product Research: Find trending products across multiple platforms
- 💰 Competitor Pricing: Extract and compare pricing strategies
- 🎨 Design Inspiration: Collect trending designs and color palettes
- 📊 Market Trends: Analyze what's selling and popular keywords
- 🏆 Top Products: Find bestsellers and their characteristics
- 🎯 SEO Research: Extract keywords, tags, and optimization strategies

All with intelligent browser automation that can:
- Navigate complex sites
- Handle dynamic content
- Extract structured data
- Take screenshots
- Adapt to page changes
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
from dataclasses import dataclass, asdict
import os

logger = logging.getLogger(__name__)


@dataclass
class ProductResearchResult:
    """Structured product research data"""
    product_name: str
    platform: str
    price: Optional[float] = None
    currency: str = "USD"
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    description: Optional[str] = None
    tags: List[str] = None
    image_url: Optional[str] = None
    product_url: Optional[str] = None
    seller_name: Optional[str] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


@dataclass
class CompetitorPricingResult:
    """Competitor pricing analysis"""
    product_type: str
    platform: str
    min_price: float
    max_price: float
    average_price: float
    median_price: float
    sample_size: int
    price_points: List[float]
    top_sellers_avg: Optional[float] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


@dataclass
class DesignInspirationResult:
    """Design inspiration data"""
    title: str
    platform: str
    image_url: Optional[str] = None
    screenshot_path: Optional[str] = None
    colors: List[str] = None
    style_tags: List[str] = None
    engagement: Optional[Dict[str, int]] = None  # likes, saves, shares
    source_url: Optional[str] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.colors is None:
            self.colors = []
        if self.style_tags is None:
            self.style_tags = []
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class BrowserUseResearcher:
    """
    Intelligent browser automation for research and data collection.
    
    Uses browser-use library with LLM-powered navigation to:
    - Navigate complex e-commerce sites
    - Extract structured product data
    - Analyze trends and patterns
    - Collect visual inspiration
    - Compare pricing strategies
    """
    
    def __init__(
        self,
        llm_provider: str = 'browser-use',
        headless: bool = True,
        output_dir: str = './research_output'
    ):
        """
        Initialize researcher.
        
        Args:
            llm_provider: LLM to use (browser-use, anthropic, openai, google)
            headless: Run browser in headless mode
            output_dir: Directory for screenshots and data
        """
        self.llm_provider = llm_provider
        self.headless = headless
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self._llm = None
        self._browser = None
    
    def _get_llm(self):
        """Get or create LLM instance."""
        if self._llm is not None:
            return self._llm
        
        if self.llm_provider == 'browser-use':
            try:
                from browser_use import ChatBrowserUse
                self._llm = ChatBrowserUse()
                return self._llm
            except ImportError:
                logger.warning("ChatBrowserUse not available, falling back to Anthropic")
                self.llm_provider = 'anthropic'
        
        if self.llm_provider == 'anthropic':
            from langchain_anthropic import ChatAnthropic
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not found")
            self._llm = ChatAnthropic(
                model_name="claude-sonnet-4-20250514",
                api_key=api_key,
                temperature=0,
            )
        elif self.llm_provider == 'openai':
            from langchain_openai import ChatOpenAI
            api_key = os.getenv('OPENAI_API_KEY')
            self._llm = ChatOpenAI(model="gpt-4o", api_key=api_key, temperature=0)
        elif self.llm_provider == 'google':
            from browser_use import ChatGoogle
            self._llm = ChatGoogle(model='gemini-2.0-flash-exp')
        
        return self._llm
    
    async def _get_browser(self):
        """Get or create browser instance."""
        if self._browser is not None:
            return self._browser
        
        from browser_use import Browser, BrowserConfig
        
        config = BrowserConfig(
            headless=self.headless,
            disable_security=False,
        )
        
        self._browser = Browser(config=config)
        return self._browser
    
    async def close(self):
        """Clean up browser resources."""
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None
    
    async def research_etsy_trends(
        self,
        category: str,
        max_products: int = 20
    ) -> List[ProductResearchResult]:
        """
        Research trending products on Etsy.
        
        Args:
            category: Product category (e.g., "t-shirts", "mugs", "stickers")
            max_products: Maximum number of products to analyze
            
        Returns:
            List of product research results
        """
        from browser_use import Agent
        from pydantic import BaseModel, Field
        
        class EtsyProduct(BaseModel):
            name: str
            price: float
            currency: str = "USD"
            rating: Optional[float] = None
            reviews: Optional[int] = None
            tags: List[str] = Field(default_factory=list)
            seller: Optional[str] = None
            url: Optional[str] = None
        
        class EtsyResearch(BaseModel):
            products: List[EtsyProduct]
        
        task = f"""
Go to Etsy.com and research trending {category}.

Steps:
1. Navigate to https://www.etsy.com
2. Search for "{category}"
3. Sort by "Most Popular" or "Bestselling" if available
4. Extract information from the first {max_products} products:
   - Product name
   - Price (as number)
   - Rating (if visible)
   - Number of reviews
   - Any visible tags or keywords
   - Seller name
   - Product URL

Return structured data for each product found.
"""
        
        logger.info(f"🔍 Researching Etsy trends for: {category}")
        
        try:
            llm = self._get_llm()
            browser = await self._get_browser()
            
            agent = Agent(
                task=task,
                llm=llm,
                browser=browser,
                use_vision=True,
                output_model_schema=EtsyResearch,
            )
            
            history = await agent.run(max_steps=30)
            result = history.final_result()
            
            if result:
                try:
                    parsed = EtsyResearch.model_validate_json(result)
                    products = [
                        ProductResearchResult(
                            product_name=p.name,
                            platform="Etsy",
                            price=p.price,
                            currency=p.currency,
                            rating=p.rating,
                            reviews_count=p.reviews,
                            tags=p.tags,
                            product_url=p.url,
                            seller_name=p.seller,
                        )
                        for p in parsed.products
                    ]
                    
                    logger.info(f"✅ Found {len(products)} Etsy products")
                    return products
                except Exception as e:
                    logger.error(f"Failed to parse Etsy results: {e}")
            
            return []
            
        except Exception as e:
            logger.error(f"Etsy research failed: {e}")
            return []
    
    async def research_redbubble_trends(
        self,
        category: str = "t-shirts",
        max_products: int = 20
    ) -> List[ProductResearchResult]:
        """
        Research trending designs on Redbubble.
        
        Args:
            category: Product category
            max_products: Maximum number of products to analyze
            
        Returns:
            List of product research results
        """
        from browser_use import Agent
        
        task = f"""
Go to Redbubble.com and research trending {category}.

Steps:
1. Navigate to https://www.redbubble.com
2. Search for "{category}"
3. Look for "Trending" or "Popular" sections
4. Extract from first {max_products} products:
   - Design title/name
   - Price range
   - Artist name
   - Any visible tags or themes
   - Product URL
5. Note common design themes and styles

Return as JSON array with structure:
[{{"name": "...", "price": 20.0, "artist": "...", "tags": ["tag1", "tag2"], "url": "..."}}]
"""
        
        logger.info(f"🔍 Researching Redbubble trends for: {category}")
        
        try:
            llm = self._get_llm()
            browser = await self._get_browser()
            
            agent = Agent(
                task=task,
                llm=llm,
                browser=browser,
                use_vision=True,
            )
            
            history = await agent.run(max_steps=30)
            result = history.final_result()
            
            if result:
                try:
                    # Try to parse JSON from result
                    import re
                    json_match = re.search(r'\[.*\]', result, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group())
                        products = [
                            ProductResearchResult(
                                product_name=p.get('name', 'Unknown'),
                                platform="Redbubble",
                                price=p.get('price'),
                                tags=p.get('tags', []),
                                product_url=p.get('url'),
                                seller_name=p.get('artist'),
                            )
                            for p in data
                        ]
                        logger.info(f"✅ Found {len(products)} Redbubble products")
                        return products
                except Exception as e:
                    logger.error(f"Failed to parse Redbubble results: {e}")
            
            return []
            
        except Exception as e:
            logger.error(f"Redbubble research failed: {e}")
            return []
    
    async def analyze_competitor_pricing(
        self,
        product_type: str,
        platforms: List[str] = None
    ) -> Dict[str, CompetitorPricingResult]:
        """
        Analyze competitor pricing across platforms.
        
        Args:
            product_type: Type of product (e.g., "graphic t-shirt")
            platforms: Platforms to check (default: ['etsy', 'redbubble', 'amazon'])
            
        Returns:
            Dict mapping platform to pricing analysis
        """
        if platforms is None:
            platforms = ['etsy', 'redbubble']
        
        logger.info(f"💰 Analyzing pricing for: {product_type}")
        
        results = {}
        
        for platform in platforms:
            if platform.lower() == 'etsy':
                products = await self.research_etsy_trends(product_type, max_products=30)
            elif platform.lower() == 'redbubble':
                products = await self.research_redbubble_trends(product_type, max_products=30)
            else:
                logger.warning(f"Platform {platform} not yet supported")
                continue
            
            # Calculate pricing statistics
            prices = [p.price for p in products if p.price is not None]
            
            if prices:
                prices.sort()
                n = len(prices)
                median = prices[n//2] if n % 2 == 1 else (prices[n//2-1] + prices[n//2]) / 2
                
                results[platform] = CompetitorPricingResult(
                    product_type=product_type,
                    platform=platform,
                    min_price=min(prices),
                    max_price=max(prices),
                    average_price=sum(prices) / len(prices),
                    median_price=median,
                    sample_size=len(prices),
                    price_points=prices,
                )
                
                logger.info(f"✅ {platform}: ${results[platform].average_price:.2f} avg (n={len(prices)})")
        
        return results
    
    async def collect_pinterest_inspiration(
        self,
        query: str,
        max_pins: int = 20
    ) -> List[DesignInspirationResult]:
        """
        Collect design inspiration from Pinterest.
        
        Args:
            query: Search query (e.g., "minimalist t-shirt design")
            max_pins: Maximum pins to collect
            
        Returns:
            List of design inspiration results
        """
        from browser_use import Agent
        
        task = f"""
Go to Pinterest and collect design inspiration for "{query}".

Steps:
1. Navigate to https://www.pinterest.com
2. Search for "{query}"
3. Look at the first {max_pins} pins
4. For each pin, extract:
   - Title/description
   - Pin URL
   - Image URL if visible
   - Engagement metrics (saves, likes if shown)
   - Dominant colors if obvious
   - Style tags or keywords

Return as JSON array with structure:
[{{"title": "...", "url": "...", "image_url": "...", "saves": 123, "colors": ["#hexcode"], "tags": ["style1"]}}]
"""
        
        logger.info(f"🎨 Collecting Pinterest inspiration: {query}")
        
        try:
            llm = self._get_llm()
            browser = await self._get_browser()
            
            agent = Agent(
                task=task,
                llm=llm,
                browser=browser,
                use_vision=True,
            )
            
            history = await agent.run(max_steps=30)
            result = history.final_result()
            
            if result:
                try:
                    import re
                    json_match = re.search(r'\[.*\]', result, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group())
                        inspiration = [
                            DesignInspirationResult(
                                title=p.get('title', 'Untitled'),
                                platform="Pinterest",
                                image_url=p.get('image_url'),
                                colors=p.get('colors', []),
                                style_tags=p.get('tags', []),
                                engagement={'saves': p.get('saves', 0)},
                                source_url=p.get('url'),
                            )
                            for p in data
                        ]
                        logger.info(f"✅ Collected {len(inspiration)} Pinterest pins")
                        return inspiration
                except Exception as e:
                    logger.error(f"Failed to parse Pinterest results: {e}")
            
            return []
            
        except Exception as e:
            logger.error(f"Pinterest collection failed: {e}")
            return []
    
    async def research_amazon_bestsellers(
        self,
        category: str,
        max_products: int = 20
    ) -> List[ProductResearchResult]:
        """
        Research Amazon bestsellers in a category.
        
        Args:
            category: Product category
            max_products: Maximum products to analyze
            
        Returns:
            List of product research results
        """
        from browser_use import Agent
        
        task = f"""
Go to Amazon and find bestselling {category}.

Steps:
1. Navigate to https://www.amazon.com
2. Search for "{category}"
3. Filter or sort by "Best Sellers" if available
4. Extract from first {max_products} products:
   - Product title
   - Price
   - Rating (out of 5)
   - Number of reviews
   - Product URL
   - Key features or bullet points

Return as JSON with product data.
"""
        
        logger.info(f"🏆 Researching Amazon bestsellers: {category}")
        
        try:
            llm = self._get_llm()
            browser = await self._get_browser()
            
            agent = Agent(
                task=task,
                llm=llm,
                browser=browser,
                use_vision=True,
            )
            
            history = await agent.run(max_steps=30)
            result = history.final_result()
            
            if result:
                try:
                    import re
                    json_match = re.search(r'\[.*\]', result, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group())
                        products = [
                            ProductResearchResult(
                                product_name=p.get('title', 'Unknown'),
                                platform="Amazon",
                                price=p.get('price'),
                                rating=p.get('rating'),
                                reviews_count=p.get('reviews'),
                                product_url=p.get('url'),
                                description=p.get('features'),
                            )
                            for p in data
                        ]
                        logger.info(f"✅ Found {len(products)} Amazon products")
                        return products
                except Exception as e:
                    logger.error(f"Failed to parse Amazon results: {e}")
            
            return []
            
        except Exception as e:
            logger.error(f"Amazon research failed: {e}")
            return []
    
    def save_research(self, data: Any, filename: str):
        """Save research data to JSON file."""
        filepath = self.output_dir / filename
        
        # Convert dataclasses to dicts
        if isinstance(data, list):
            data = [asdict(item) if hasattr(item, '__dataclass_fields__') else item for item in data]
        elif hasattr(data, '__dataclass_fields__'):
            data = asdict(data)
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        logger.info(f"💾 Saved research to: {filepath}")
        return filepath
    
    async def comprehensive_market_research(
        self,
        product_type: str,
        platforms: List[str] = None
    ) -> Dict[str, Any]:
        """
        Run comprehensive market research across multiple platforms.
        
        Args:
            product_type: Type of product to research
            platforms: Platforms to research (default: all supported)
            
        Returns:
            Dict with all research results
        """
        if platforms is None:
            platforms = ['etsy', 'redbubble', 'amazon']
        
        logger.info(f"🚀 Starting comprehensive market research for: {product_type}")
        
        results = {
            'product_type': product_type,
            'timestamp': datetime.now().isoformat(),
            'platforms': {},
            'pricing_analysis': {},
            'summary': {}
        }
        
        # Run platform-specific research
        tasks = []
        for platform in platforms:
            if platform.lower() == 'etsy':
                tasks.append(self.research_etsy_trends(product_type))
            elif platform.lower() == 'redbubble':
                tasks.append(self.research_redbubble_trends(product_type))
            elif platform.lower() == 'amazon':
                tasks.append(self.research_amazon_bestsellers(product_type))
        
        platform_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        all_products = []
        for i, platform in enumerate(platforms):
            if isinstance(platform_results[i], Exception):
                logger.error(f"❌ {platform} research failed: {platform_results[i]}")
                continue
            
            products = platform_results[i]
            results['platforms'][platform] = [asdict(p) for p in products]
            all_products.extend(products)
        
        # Pricing analysis
        results['pricing_analysis'] = await self.analyze_competitor_pricing(
            product_type,
            platforms
        )
        
        # Summary statistics
        if all_products:
            all_prices = [p.price for p in all_products if p.price]
            all_ratings = [p.rating for p in all_products if p.rating]
            
            results['summary'] = {
                'total_products_analyzed': len(all_products),
                'average_price': sum(all_prices) / len(all_prices) if all_prices else None,
                'price_range': [min(all_prices), max(all_prices)] if all_prices else None,
                'average_rating': sum(all_ratings) / len(all_ratings) if all_ratings else None,
            }
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"market_research_{product_type.replace(' ', '_')}_{timestamp}.json"
        self.save_research(results, filename)
        
        logger.info(f"""
╔══════════════════════════════════════════════════════════╗
║  📊 MARKET RESEARCH COMPLETE                             ║
╠══════════════════════════════════════════════════════════╣
║  Product: {product_type:<44} ║
║  Platforms: {len(platforms):<3}  Products: {len(all_products):<3}                        ║
║  Avg Price: ${results['summary'].get('average_price', 0):.2f}                                  ║
║  Saved to: {filename[:35]:<35} ║
╚══════════════════════════════════════════════════════════╝
""")
        
        return results


# Convenience functions
async def quick_etsy_research(category: str, max_products: int = 20):
    """Quick Etsy research - convenience function."""
    researcher = BrowserUseResearcher()
    try:
        return await researcher.research_etsy_trends(category, max_products)
    finally:
        await researcher.close()


async def quick_pricing_analysis(product_type: str):
    """Quick pricing analysis - convenience function."""
    researcher = BrowserUseResearcher()
    try:
        return await researcher.analyze_competitor_pricing(product_type)
    finally:
        await researcher.close()


async def quick_market_research(product_type: str):
    """Quick comprehensive market research - convenience function."""
    researcher = BrowserUseResearcher()
    try:
        return await researcher.comprehensive_market_research(product_type)
    finally:
        await researcher.close()


# Example usage
if __name__ == "__main__":
    async def main():
        # Example: Research t-shirt market
        researcher = BrowserUseResearcher(headless=False)  # Show browser for demo
        
        try:
            # 1. Etsy trends
            print("\n🔍 Researching Etsy trends...")
            etsy_products = await researcher.research_etsy_trends("graphic t-shirts", max_products=10)
            print(f"Found {len(etsy_products)} products")
            
            # 2. Pricing analysis
            print("\n💰 Analyzing pricing...")
            pricing = await researcher.analyze_competitor_pricing("t-shirts")
            for platform, data in pricing.items():
                print(f"{platform}: ${data.average_price:.2f} average")
            
            # 3. Pinterest inspiration
            print("\n🎨 Collecting Pinterest inspiration...")
            inspiration = await researcher.collect_pinterest_inspiration(
                "minimalist t-shirt design",
                max_pins=10
            )
            print(f"Collected {len(inspiration)} design inspirations")
            
            # 4. Comprehensive research
            print("\n📊 Running comprehensive market research...")
            report = await researcher.comprehensive_market_research("t-shirts")
            print(f"Complete! Analyzed {report['summary']['total_products_analyzed']} products")
            
        finally:
            await researcher.close()
    
    asyncio.run(main())
