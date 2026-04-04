"""
OTTO APP CONTROLLER
===================
Gives Otto Super complete control over the entire application.
Otto can now:
- Generate any content (campaigns, posters, videos, audio)
- Manage e-commerce (products, pricing, inventory)
- Control social media (all platforms)
- Access analytics and insights
- Setup automations and workflows
- Manage brand strategy

This extends beyond just documents and task queue - Otto has FULL platform access.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class OttoAppController:
    """
    Master controller giving Otto complete app access.
    """

    def __init__(
        self,
        replicate_api=None,
        printify_api=None,
        shopify_api=None,
        youtube_api=None,
        task_queue=None,
        multi_platform_poster=None,
    ):
        self.replicate = replicate_api
        self.printify = printify_api
        self.shopify = shopify_api
        self.youtube = youtube_api
        self.task_queue = task_queue
        self.social_poster = multi_platform_poster

        logger.info("🎮 Otto App Controller initialized - Full platform access granted")

    # ========================================================================
    # CONTENT GENERATION
    # ========================================================================

    async def generate_campaign(
        self, brand_name: str, product_type: str, style: str = "modern", platforms: list[str] = None
    ) -> dict[str, Any]:
        """
        Generate a complete marketing campaign.

        Args:
            brand_name: Brand to create campaign for
            product_type: poster, audio, merch, etc.
            style: Visual style (cyberpunk, minimalist, neon, etc.)
            platforms: Target platforms (pinterest, tiktok, instagram, etc.)
        """
        logger.info(f"🎨 Generating {brand_name} campaign for {product_type}")

        try:
            # Import campaign generator
            from app.services.campaign_generator_service import CampaignGeneratorService

            campaign_gen = CampaignGeneratorService(self.replicate)

            # Generate complete campaign
            result = await campaign_gen.generate_complete_campaign(
                brand_name=brand_name,
                product_type=product_type,
                style=style,
                target_platforms=platforms or ["pinterest", "tiktok", "instagram"],
            )

            return {
                "success": True,
                "campaign_id": result.get("id"),
                "assets": result.get("assets", []),
                "message": f"✅ Generated {brand_name} campaign with {len(result.get('assets', []))} assets",
            }

        except Exception as e:
            logger.error(f"Campaign generation error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"❌ Campaign generation failed: {e}",
            }

    async def generate_poster(
        self, prompt: str, style: str = "modern", size: str = "1024x1024"
    ) -> dict[str, Any]:
        """Generate a poster/artwork with AI."""
        logger.info(f"🎨 Generating poster: {prompt[:50]}...")

        try:
            # Use Replicate to generate image
            result = self.replicate.generate_image(
                prompt=f"{prompt}, {style} style, high quality poster art",
                model="black-forest-labs/flux-dev",
                width=int(size.split("x")[0]),
                height=int(size.split("x")[1]),
            )

            return {
                "success": True,
                "url": result,
                "message": f"✅ Poster generated: {prompt[:50]}...",
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"❌ Poster generation failed: {e}",
            }

    async def generate_video(
        self, prompt: str, duration: int = 5, model: str = "luma/ray-2"
    ) -> dict[str, Any]:
        """Generate a video with AI."""
        logger.info(f"🎬 Generating video: {prompt[:50]}...")

        try:
            result = self.replicate.generate_video(prompt=prompt, model=model, duration=duration)

            return {
                "success": True,
                "url": result,
                "message": f"✅ Video generated: {prompt[:50]}...",
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"❌ Video generation failed: {e}",
            }

    async def generate_audio(
        self, prompt: str, duration: int = 30, genre: str = "ambient"
    ) -> dict[str, Any]:
        """Generate audio/music with AI."""
        logger.info(f"🎵 Generating audio: {prompt[:50]}...")

        try:
            result = self.replicate.generate_audio(
                prompt=f"{prompt}, {genre} genre, {duration} seconds", model="meta/musicgen"
            )

            return {
                "success": True,
                "url": result,
                "message": f"✅ Audio generated: {prompt[:50]}...",
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"❌ Audio generation failed: {e}",
            }

    async def generate_mockup(
        self, product_image_url: str, mockup_type: str = "poster_on_wall"
    ) -> dict[str, Any]:
        """Generate product mockup in realistic setting."""
        logger.info(f"🖼️ Generating {mockup_type} mockup")

        try:
            # Use mockup service
            from printify_mockup_service import PrintifyMockupService

            mockup_service = PrintifyMockupService(self.printify)
            result = mockup_service.create_mockup(
                image_url=product_image_url, mockup_type=mockup_type
            )

            return {
                "success": True,
                "url": result.get("url"),
                "message": f"✅ Mockup generated: {mockup_type}",
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"❌ Mockup generation failed: {e}",
            }

    # ========================================================================
    # E-COMMERCE OPERATIONS
    # ========================================================================

    async def create_product(
        self,
        title: str,
        description: str,
        price: float,
        image_url: str,
        product_type: str = "poster",
    ) -> dict[str, Any]:
        """Create product on Shopify."""
        logger.info(f"🛍️ Creating product: {title}")

        try:
            if not self.shopify:
                return {"success": False, "message": "❌ Shopify not configured"}

            result = self.shopify.create_product(
                title=title,
                body_html=f"<p>{description}</p>",
                vendor="Aura Sky",
                product_type=product_type,
                price=price,
                images=[{"src": image_url}],
            )

            return {
                "success": True,
                "product_id": result.get("id"),
                "url": result.get("url"),
                "message": f"✅ Product created: {title} at ${price}",
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"❌ Product creation failed: {e}",
            }

    async def update_pricing(
        self, product_id: str, new_price: float, compare_at_price: float = None
    ) -> dict[str, Any]:
        """Update product pricing."""
        logger.info(f"💰 Updating pricing for product {product_id}")

        try:
            if not self.shopify:
                return {"success": False, "message": "❌ Shopify not configured"}

            result = self.shopify.update_product_price(
                product_id=product_id, price=new_price, compare_at_price=compare_at_price
            )

            return {"success": True, "message": f"✅ Price updated to ${new_price}"}

        except Exception as e:
            return {"success": False, "error": str(e), "message": f"❌ Pricing update failed: {e}"}

    async def check_inventory(self) -> dict[str, Any]:
        """Check inventory levels across products."""
        logger.info("📦 Checking inventory")

        try:
            if not self.shopify:
                return {"success": False, "message": "❌ Shopify not configured"}

            products = self.shopify.get_products()

            inventory_summary = []
            for product in products:
                inventory_summary.append(
                    {
                        "title": product.get("title"),
                        "id": product.get("id"),
                        "inventory": product.get("inventory_quantity", "N/A"),
                    }
                )

            return {
                "success": True,
                "inventory": inventory_summary,
                "message": f"✅ Checked {len(inventory_summary)} products",
            }

        except Exception as e:
            return {"success": False, "error": str(e), "message": f"❌ Inventory check failed: {e}"}

    # ========================================================================
    # SOCIAL MEDIA OPERATIONS
    # ========================================================================

    async def post_to_all_platforms(
        self, content: str, media_url: str, platforms: list[str] = None
    ) -> dict[str, Any]:
        """Post content to multiple social platforms."""
        logger.info(f"📱 Posting to platforms: {platforms}")

        if not platforms:
            platforms = ["pinterest", "tiktok", "instagram", "twitter"]

        results = {}

        for platform in platforms:
            try:
                if platform == "pinterest" and self.social_poster:
                    result = await self.social_poster.post_to_pinterest(
                        image_path=media_url, title=content[:100], description=content
                    )
                    results[platform] = {"success": result}

                elif platform == "tiktok" and self.social_poster:
                    result = await self.social_poster.post_to_tiktok(
                        image_path=media_url, caption=content
                    )
                    results[platform] = {"success": result}

                elif platform == "instagram" and self.social_poster:
                    result = await self.social_poster.post_to_instagram(
                        image_path=media_url, caption=content
                    )
                    results[platform] = {"success": result}

                elif platform == "twitter" and self.social_poster:
                    result = await self.social_poster.post_to_twitter(
                        image_path=media_url, caption=content[:280]
                    )
                    results[platform] = {"success": result}

            except Exception as e:
                results[platform] = {"success": False, "error": str(e)}

        success_count = sum(1 for r in results.values() if r.get("success"))

        return {
            "success": success_count > 0,
            "results": results,
            "message": f"✅ Posted to {success_count}/{len(platforms)} platforms",
        }

    # ========================================================================
    # ANALYTICS & INSIGHTS
    # ========================================================================

    async def show_analytics(
        self, metric_type: str = "overview", time_period: str = "7d"
    ) -> dict[str, Any]:
        """Show analytics and performance metrics."""
        logger.info(f"📊 Fetching {metric_type} analytics for {time_period}")

        try:
            analytics = {
                "shopify_sales": await self._get_shopify_analytics(time_period),
                "social_engagement": await self._get_social_analytics(time_period),
                "content_performance": await self._get_content_analytics(time_period),
            }

            return {
                "success": True,
                "analytics": analytics,
                "message": f"✅ Analytics for {time_period}",
            }

        except Exception as e:
            return {"success": False, "error": str(e), "message": f"❌ Analytics fetch failed: {e}"}

    async def _get_shopify_analytics(self, period: str) -> dict:
        """Get Shopify sales analytics."""
        if not self.shopify:
            return {"error": "Shopify not configured"}

        try:
            orders = self.shopify.get_orders(limit=100)
            return {
                "total_orders": len(orders),
                "total_revenue": sum(float(o.get("total_price", 0)) for o in orders),
            }
        except:
            return {"error": "Failed to fetch"}

    async def _get_social_analytics(self, period: str) -> dict:
        """Get social media engagement analytics from session state."""
        try:
            import streamlit as st

            # Try to get actual data from session state
            social_posts = st.session_state.get("social_posts", [])
            twitter_posts = [p for p in social_posts if "twitter" in p.get("platform", "").lower()]

            return {
                "total_posts": len(social_posts),
                "twitter_posts": len(twitter_posts),
                "pinterest_saves": st.session_state.get("pinterest_analytics", {}).get(
                    "saves", "N/A"
                ),
                "tiktok_views": st.session_state.get("tiktok_analytics", {}).get("views", "N/A"),
                "instagram_likes": st.session_state.get("instagram_analytics", {}).get(
                    "likes", "N/A"
                ),
                "note": "Connect social accounts in Settings for live analytics",
            }
        except Exception:
            return {
                "pinterest_saves": "N/A",
                "tiktok_views": "N/A",
                "instagram_likes": "N/A",
                "note": "Social analytics require active session",
            }

    async def _get_content_analytics(self, period: str) -> dict:
        """Get content performance analytics from session state."""
        try:
            import streamlit as st

            # Count generated content from session state
            campaigns = st.session_state.get("campaign_history", [])
            products = st.session_state.get("generated_products", [])
            blog_posts = st.session_state.get("blog_posts", [])
            playground_results = st.session_state.get("playground_results", [])

            return {
                "campaigns_created": len(campaigns),
                "products_generated": len(products),
                "blog_posts": len(blog_posts),
                "playground_generations": len(playground_results),
                "content_created": len(campaigns) + len(products) + len(blog_posts),
                "top_performing": campaigns[0].get("name", "N/A") if campaigns else "N/A",
            }
        except Exception:
            return {
                "content_created": 0,
                "top_performing": "N/A",
                "note": "Content analytics require active session",
            }

    # ========================================================================
    # AUTOMATION & WORKFLOWS
    # ========================================================================

    async def setup_automation(
        self, automation_type: str, schedule: str, config: dict
    ) -> dict[str, Any]:
        """Setup automated workflow."""
        logger.info(f"⚙️ Setting up {automation_type} automation")

        try:
            if not self.task_queue:
                return {"success": False, "message": "❌ Task queue not available"}

            # Add recurring task to queue
            task_description = (
                f"Automated {automation_type}: {config.get('description', 'No description')}"
            )

            # Schedule task
            result = self.task_queue.add_task(
                description=task_description,
                priority="normal",
                scheduled_for=schedule,
                recurring=True,
                config=config,
            )

            return {
                "success": True,
                "task_id": result.get("id"),
                "message": f"✅ Automation setup: {automation_type} ({schedule})",
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"❌ Automation setup failed: {e}",
            }

    async def schedule_posts(
        self, content_list: list[dict], platforms: list[str], schedule: str = "daily"
    ) -> dict[str, Any]:
        """Schedule content posts across platforms."""
        logger.info(f"📅 Scheduling {len(content_list)} posts on {schedule} basis")

        try:
            scheduled_count = 0

            for content in content_list:
                result = await self.setup_automation(
                    automation_type="social_post",
                    schedule=schedule,
                    config={
                        "content": content.get("text"),
                        "media_url": content.get("media_url"),
                        "platforms": platforms,
                    },
                )

                if result.get("success"):
                    scheduled_count += 1

            return {
                "success": scheduled_count > 0,
                "scheduled": scheduled_count,
                "message": f"✅ Scheduled {scheduled_count} posts ({schedule})",
            }

        except Exception as e:
            return {"success": False, "error": str(e), "message": f"❌ Post scheduling failed: {e}"}


# ============================================================================
# APP-WIDE INTENT KEYWORDS
# ============================================================================

APP_CONTROL_KEYWORDS = {
    # Content Generation
    "generate_campaign": ["generate campaign", "create campaign", "build campaign", "new campaign"],
    "generate_poster": ["generate poster", "create poster", "make poster", "design poster"],
    "generate_video": ["generate video", "create video", "make video", "video content"],
    "generate_audio": ["generate audio", "create audio", "make music", "audio loop"],
    "generate_mockup": ["generate mockup", "create mockup", "product mockup", "lifestyle shot"],
    # E-commerce
    "create_product": ["create product", "add product", "list product", "new product"],
    "update_pricing": ["update price", "change price", "set price", "pricing strategy"],
    "check_inventory": ["check inventory", "inventory status", "stock levels", "inventory check"],
    # Social Media
    "post_all_platforms": ["post everywhere", "post to all", "cross post", "multi platform post"],
    "schedule_posts": ["schedule posts", "schedule content", "auto post schedule"],
    # Analytics
    "show_analytics": [
        "show analytics",
        "view analytics",
        "performance metrics",
        "analytics dashboard",
    ],
    # Automation
    "setup_automation": [
        "setup automation",
        "automate this",
        "create automation",
        "automatic workflow",
    ],
}


def parse_app_control_intent(message: str) -> Optional[str]:
    """
    Parse message for app-wide control intents.

    Returns:
        Intent type if matched, None otherwise
    """
    msg_lower = message.lower()

    for intent, keywords in APP_CONTROL_KEYWORDS.items():
        if any(kw in msg_lower for kw in keywords):
            return intent

    return None
