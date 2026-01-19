"""
OTTO SUPER ENGINE - Part 2: Execution Engine
============================================
Execution engine that runs tools and displays results in real-time.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


# ============================================================================
# EXECUTION ENGINE - Runs Tools and Displays Results
# ============================================================================

@dataclass
class ExecutionResult:
    """Result from executing a tool."""
    tool_id: str
    success: bool
    output: Any = None
    output_type: str = "text"  # text, image, video, audio, file
    error: Optional[str] = None
    duration_seconds: float = 0.0
    cost_estimate: str = "$0.00"
    artifacts: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            'tool_id': self.tool_id,
            'success': self.success,
            'output': str(self.output) if self.output else None,
            'output_type': self.output_type,
            'error': self.error,
            'duration_seconds': self.duration_seconds,
            'cost_estimate': self.cost_estimate,
            'artifacts': self.artifacts
        }


class ExecutionEngine:
    """
    Executes tools and manages real-time result display.
    
    This is where Otto actually DOES things.
    """
    
    def __init__(self, tool_registry, replicate_api, printify_api=None, shopify_api=None, youtube_api=None):
        self.registry = tool_registry
        self.replicate = replicate_api
        self.printify = printify_api
        self.shopify = shopify_api
        self.youtube = youtube_api
        
        # Enhanced browser service
        try:
            from automation.enhanced_browser import get_browser_service
            self.browser = get_browser_service()
        except ImportError:
            self.browser = None
            logger.warning("⚠️ Enhanced browser service not available")
        
        # Ray integration helpers
        try:
            from ray_integration_helpers import is_ray_enabled, get_ray_manager_if_enabled
            self.ray_enabled = is_ray_enabled()
            self.ray_manager = get_ray_manager_if_enabled() if self.ray_enabled else None
        except ImportError:
            self.ray_enabled = False
            self.ray_manager = None
    
    async def execute_tool(self, tool_id: str, parameters: Dict, progress_callback=None) -> ExecutionResult:
        """
        Execute a single tool with given parameters.
        
        Args:
            tool_id: ID of tool to execute
            parameters: Parameters for the tool
            progress_callback: Optional callback for progress updates
        
        Returns:
            ExecutionResult with output
        """
        tool = self.registry.get(tool_id)
        if not tool:
            return ExecutionResult(
                tool_id=tool_id,
                success=False,
                error=f"Tool {tool_id} not found"
            )
        
        start_time = datetime.now()
        
        try:
            if progress_callback:
                progress_callback({"status": "starting", "tool": tool.name})
            
            # Route to appropriate execution method
            if tool.category.value == "image_generation":
                result = await self._execute_image_generation(tool, parameters, progress_callback)
            
            elif tool.category.value == "video_generation":
                result = await self._execute_video_generation(tool, parameters, progress_callback)
            
            elif tool.category.value == "music_generation":
                result = await self._execute_music_generation(tool, parameters, progress_callback)
            
            elif tool.category.value == "speech_generation":
                result = await self._execute_speech_generation(tool, parameters, progress_callback)
            
            elif tool.category.value == "marketing":
                result = await self._execute_marketing(tool, parameters, progress_callback)
            
            elif tool.category.value == "campaign":
                result = await self._execute_campaign(tool, parameters, progress_callback)
            
            elif tool.category.value == "publishing":
                result = await self._execute_publishing(tool, parameters, progress_callback)
            
            elif tool.category.value == "browser":
                result = await self._execute_browser(tool, parameters, progress_callback)
            
            else:
                result = ExecutionResult(
                    tool_id=tool_id,
                    success=False,
                    error=f"Tool category {tool.category.value} not implemented yet"
                )
            
            # Calculate duration
            duration = (datetime.now() - start_time).total_seconds()
            result.duration_seconds = duration
            result.cost_estimate = tool.cost_estimate
            
            if progress_callback:
                progress_callback({"status": "completed", "tool": tool.name, "result": result})
            
            return result
            
        except Exception as e:
            logger.error(f"Tool execution failed: {tool_id} - {e}")
            return ExecutionResult(
                tool_id=tool_id,
                success=False,
                error=str(e),
                duration_seconds=(datetime.now() - start_time).total_seconds()
            )
    
    async def _execute_image_generation(self, tool, params, callback) -> ExecutionResult:
        """Execute image generation tool with Ray support."""
        prompt = params.get('prompt', '')
        aspect_ratio = params.get('aspect_ratio', '1:1')
        
        if callback:
            callback({"status": "generating", "message": f"Generating image with {tool.name}..."})
        
        try:
            # Use Ray if enabled
            if self.ray_enabled and self.ray_manager:
                async def _gen():
                    if tool.model_ref:
                        return self.replicate._run_model(tool.model_ref, {"prompt": prompt, "aspect_ratio": aspect_ratio})
                    else:
                        return self.replicate.generate_image(prompt=prompt, aspect_ratio=aspect_ratio)
                
                image_url = await self.ray_manager.execute_task_distributed(
                    task_func=_gen,
                    task_type="design",
                    timeout=300
                )
            else:
                # Local execution
                if tool.model_ref:
                    image_url = self.replicate._run_model(tool.model_ref, {"prompt": prompt, "aspect_ratio": aspect_ratio})
                else:
                    image_url = self.replicate.generate_image(prompt=prompt, aspect_ratio=aspect_ratio)
            
            return ExecutionResult(
                tool_id=tool.id,
                success=True,
                output=image_url,
                output_type="image",
                artifacts=[{"type": "image", "url": image_url, "prompt": prompt}]
            )
        except Exception as e:
            return ExecutionResult(
                tool_id=tool.id,
                success=False,
                error=f"Image generation failed: {e}"
            )
    
    async def _execute_video_generation(self, tool, params, callback) -> ExecutionResult:
        """Execute video generation tool."""
        prompt = params.get('prompt', '')
        image_url = params.get('image')
        duration = params.get('duration', 5)
        
        if callback:
            callback({"status": "generating", "message": f"Generating video with {tool.name}... (1-3 min)"})
        
        try:
            if tool.model_ref:
                import replicate
                input_data = {"prompt": prompt}
                if image_url:
                    input_data["image"] = image_url
                if "duration" in tool.parameters:
                    input_data["duration"] = duration
                
                output = replicate.run(tool.model_ref, input=input_data)
                video_url = str(output) if output else None
            else:
                # Use default
                video_url = self.replicate.generate_video(
                    prompt=prompt,
                    image_url=image_url,
                    aspect_ratio="16:9"
                )
            
            if video_url:
                return ExecutionResult(
                    tool_id=tool.id,
                    success=True,
                    output=video_url,
                    output_type="video",
                    artifacts=[{"type": "video", "url": video_url, "prompt": prompt}]
                )
            else:
                return ExecutionResult(
                    tool_id=tool.id,
                    success=False,
                    error="Video generation returned no result"
                )
        except Exception as e:
            return ExecutionResult(
                tool_id=tool.id,
                success=False,
                error=f"Video generation failed: {e}"
            )
    
    async def _execute_music_generation(self, tool, params, callback) -> ExecutionResult:
        """Execute music generation tool."""
        prompt = params.get('prompt', '')
        duration = params.get('duration', 30)
        
        if callback:
            callback({"status": "generating", "message": f"Generating music with {tool.name}..."})
        
        try:
            import replicate
            input_data = {"prompt": prompt, "duration": duration}
            output = replicate.run(tool.model_ref, input=input_data)
            audio_url = str(output) if output else None
            
            if audio_url:
                return ExecutionResult(
                    tool_id=tool.id,
                    success=True,
                    output=audio_url,
                    output_type="audio",
                    artifacts=[{"type": "audio", "url": audio_url, "prompt": prompt}]
                )
            else:
                return ExecutionResult(
                    tool_id=tool.id,
                    success=False,
                    error="Music generation returned no result"
                )
        except Exception as e:
            return ExecutionResult(
                tool_id=tool.id,
                success=False,
                error=f"Music generation failed: {e}"
            )
    
    async def _execute_speech_generation(self, tool, params, callback) -> ExecutionResult:
        """Execute speech/TTS generation."""
        text = params.get('text', '')
        voice = params.get('voice', 'female-1')
        emotion = params.get('emotion', 'neutral')
        
        if callback:
            callback({"status": "generating", "message": "Generating voiceover..."})
        
        try:
            import replicate
            input_data = {"text": text, "voice": voice, "emotion": emotion, "language": "en"}
            output = replicate.run(tool.model_ref, input=input_data)
            audio_url = str(output) if output else None
            
            if audio_url:
                return ExecutionResult(
                    tool_id=tool.id,
                    success=True,
                    output=audio_url,
                    output_type="audio",
                    artifacts=[{"type": "audio", "url": audio_url, "text": text}]
                )
            else:
                return ExecutionResult(
                    tool_id=tool.id,
                    success=False,
                    error="Speech generation returned no result"
                )
        except Exception as e:
            return ExecutionResult(
                tool_id=tool.id,
                success=False,
                error=f"Speech generation failed: {e}"
            )
    
    async def _execute_marketing(self, tool, params, callback) -> ExecutionResult:
        """Execute marketing/ad generation."""
        if callback:
            callback({"status": "generating", "message": "Creating marketing ads..."})
        
        try:
            import replicate
            output = replicate.run(tool.model_ref, input=params)
            
            # Handle multiple outputs
            if isinstance(output, list):
                artifacts = [{"type": "image", "url": str(url)} for url in output]
                return ExecutionResult(
                    tool_id=tool.id,
                    success=True,
                    output=artifacts[0]["url"],
                    output_type="image",
                    artifacts=artifacts
                )
            else:
                image_url = str(output)
                return ExecutionResult(
                    tool_id=tool.id,
                    success=True,
                    output=image_url,
                    output_type="image",
                    artifacts=[{"type": "image", "url": image_url}]
                )
        except Exception as e:
            return ExecutionResult(
                tool_id=tool.id,
                success=False,
                error=f"Marketing ad generation failed: {e}"
            )
    
    async def _execute_campaign(self, tool, params, callback) -> ExecutionResult:
        """Execute full campaign generation."""
        if callback:
            callback({"status": "starting", "message": "Starting campaign generation... (5-10 min)"})
        
        try:
            concept = params.get('concept', '')
            style = params.get('style', 'lifestyle')
            
            # Try to use the campaign generator service
            try:
                from campaign_generator_service import CampaignGeneratorService
                
                generator = CampaignGeneratorService()
                
                if callback:
                    callback({"status": "generating", "message": "Generating campaign assets..."})
                
                # Generate campaign
                campaign_result = await generator.generate_campaign(
                    concept=concept,
                    style=style,
                    callback=callback
                )
                
                if campaign_result and campaign_result.get('success'):
                    return ExecutionResult(
                        tool_id=tool.id,
                        success=True,
                        output=f"✅ Campaign '{concept}' generated!\n\n"
                               f"• Images: {campaign_result.get('images_count', 0)}\n"
                               f"• Products: {campaign_result.get('products_count', 0)}\n"
                               f"• Content: {campaign_result.get('content_count', 0)}",
                        output_type="text",
                        artifacts=campaign_result.get('artifacts', [])
                    )
                else:
                    raise Exception(campaign_result.get('error', 'Unknown error'))
                    
            except ImportError:
                # Fall back to basic campaign generation via session state
                import streamlit as st
                
                # Store campaign request in session state for main app to process
                if 'campaign_requests' not in st.session_state:
                    st.session_state.campaign_requests = []
                
                st.session_state.campaign_requests.append({
                    'concept': concept,
                    'style': style,
                    'requested_at': datetime.now().isoformat(),
                    'status': 'pending'
                })
                
                return ExecutionResult(
                    tool_id=tool.id,
                    success=True,
                    output=f"📋 Campaign '{concept}' queued for generation.\n\n"
                           f"Check the **Campaign Creator** tab to monitor progress.",
                    output_type="text"
                )
                
        except Exception as e:
            return ExecutionResult(
                tool_id=tool.id,
                success=False,
                error=f"Campaign generation failed: {e}"
            )
    
    async def _execute_publishing(self, tool, params, callback) -> ExecutionResult:
        """Execute publishing to external services."""
        if tool.id == "printify_upload":
            return await self._publish_to_printify(params, callback)
        elif tool.id == "youtube_upload":
            return await self._publish_to_youtube(params, callback)
        elif tool.id == "shopify_blog":
            return await self._publish_to_shopify(params, callback)
        elif tool.id == "pinterest_pin":
            return await self._publish_to_pinterest(params, callback)
        elif tool.id == "tiktok_post":
            return await self._publish_to_tiktok(params, callback)
        elif tool.id == "twitter_post":
            return await self._publish_to_twitter(params, callback)
        elif tool.id == "instagram_post":
            return await self._publish_to_instagram(params, callback)
        else:
            return ExecutionResult(
                tool_id=tool.id,
                success=False,
                error=f"Publishing method not implemented: {tool.id}"
            )
    
    async def _publish_to_printify(self, params, callback) -> ExecutionResult:
        """Upload image to Printify."""
        if not self.printify:
            return ExecutionResult(
                tool_id="printify_upload",
                success=False,
                error="Printify API not configured"
            )
        
        image_url = params.get('image_url')
        if not image_url:
            return ExecutionResult(
                tool_id="printify_upload",
                success=False,
                error="No image_url provided"
            )
        
        if callback:
            callback({"status": "uploading", "message": "Uploading to Printify..."})
        
        try:
            import requests
            
            # Download image
            response = requests.get(image_url, timeout=60)
            response.raise_for_status()
            image_bytes = response.content
            
            # Upload to Printify
            file_name = f"otto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            printify_image_id = self.printify.upload_image(image_bytes, file_name)
            
            return ExecutionResult(
                tool_id="printify_upload",
                success=True,
                output=f"✅ Uploaded to Printify!\n\nImage ID: {printify_image_id}",
                output_type="text",
                artifacts=[{"type": "printify_upload", "id": printify_image_id}]
            )
        except Exception as e:
            return ExecutionResult(
                tool_id="printify_upload",
                success=False,
                error=f"Printify upload failed: {e}"
            )
    
    async def _publish_to_youtube(self, params, callback) -> ExecutionResult:
        """Upload video to YouTube."""
        if not self.youtube:
            return ExecutionResult(
                tool_id="youtube_upload",
                success=False,
                error="YouTube API not configured"
            )
        
        video_url = params.get('video_url')
        title = params.get('title', 'Otto Mate Creation')
        description = params.get('description', 'Created with Otto Mate AI')
        
        if not video_url:
            return ExecutionResult(
                tool_id="youtube_upload",
                success=False,
                error="No video_url provided"
            )
        
        if callback:
            callback({"status": "uploading", "message": "Uploading to YouTube..."})
        
        try:
            import requests
            import tempfile
            
            # Download video
            response = requests.get(video_url, timeout=180)
            response.raise_for_status()
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
                f.write(response.content)
                video_path = f.name
            
            # Upload to YouTube
            result = self.youtube.upload_commercial(
                video_path=video_path,
                product_name=title,
                metadata={
                    'title': title,
                    'description': description,
                    'tags': ['AI Generated', 'Otto Mate'],
                    'privacy': 'unlisted'
                }
            )
            
            # Cleanup
            import os
            try:
                os.unlink(video_path)
            except:
                pass
            
            if result:
                video_id = result.get("id")
                video_link = result.get("url", f"https://youtube.com/watch?v={video_id}")
                
                return ExecutionResult(
                    tool_id="youtube_upload",
                    success=True,
                    output=f"✅ Uploaded to YouTube!\n\nURL: {video_link}",
                    output_type="text",
                    artifacts=[{"type": "youtube_video", "id": video_id, "url": video_link}]
                )
            else:
                return ExecutionResult(
                    tool_id="youtube_upload",
                    success=False,
                    error="YouTube upload returned no result"
                )
        except Exception as e:
            return ExecutionResult(
                tool_id="youtube_upload",
                success=False,
                error=f"YouTube upload failed: {e}"
            )
    
    async def _publish_to_shopify(self, params, callback) -> ExecutionResult:
        """Publish blog post to Shopify."""
        if not self.shopify:
            return ExecutionResult(
                tool_id="shopify_blog",
                success=False,
                error="Shopify API not configured"
            )
        
        title = params.get('title', 'Otto Mate Blog Post')
        content = params.get('content', '')
        image_url = params.get('image_url')
        
        if callback:
            callback({"status": "publishing", "message": "Publishing to Shopify..."})
        
        try:
            result = self.shopify.create_blog_post(
                title=title,
                body_html=f"<p>{content}</p>",
                author="Otto Mate AI",
                tags=["AI Generated", "Otto Mate"],
                published=True,
                image_url=image_url
            )
            
            if result:
                article_id = result.get('id')
                article_url = result.get('url', f"Article ID: {article_id}")
                
                return ExecutionResult(
                    tool_id="shopify_blog",
                    success=True,
                    output=f"✅ Published to Shopify!\n\nURL: {article_url}",
                    output_type="text",
                    artifacts=[{"type": "shopify_blog", "id": article_id, "url": article_url}]
                )
            else:
                return ExecutionResult(
                    tool_id="shopify_blog",
                    success=False,
                    error="Shopify blog creation returned no result"
                )
        except Exception as e:
            return ExecutionResult(
                tool_id="shopify_blog",
                success=False,
                error=f"Shopify blog creation failed: {e}"
            )
    
    async def _publish_to_pinterest(self, params, callback) -> ExecutionResult:
        """Publish pin to Pinterest."""
        try:
            from multi_platform_poster import MultiPlatformPoster
            
            image_url = params.get('image_url')
            title = params.get('title', 'Otto Mate Creation')
            description = params.get('description', '')
            board = params.get('board', 'AI Creations')
            link = params.get('link', '')
            
            if not image_url:
                return ExecutionResult(
                    tool_id="pinterest_pin",
                    success=False,
                    error="No image_url provided"
                )
            
            if callback:
                callback({"status": "posting", "message": "Posting to Pinterest..."})
            
            # Initialize multi-platform poster
            poster = MultiPlatformPoster()
            
            # Post to Pinterest
            success = await poster.post_to_pinterest(
                image_path=image_url,
                title=title,
                description=description,
                link=link
            )
            
            if success:
                return ExecutionResult(
                    tool_id="pinterest_pin",
                    success=True,
                    output=f"✅ Posted to Pinterest!\n\nTitle: {title}\nBoard: {board}",
                    output_type="text",
                    artifacts=[{"type": "pinterest_pin", "title": title}]
                )
            else:
                return ExecutionResult(
                    tool_id="pinterest_pin",
                    success=False,
                    error="Pinterest posting failed"
                )
        except Exception as e:
            return ExecutionResult(
                tool_id="pinterest_pin",
                success=False,
                error=f"Pinterest posting failed: {e}"
            )
    
    async def _publish_to_tiktok(self, params, callback) -> ExecutionResult:
        """Publish video to TikTok."""
        try:
            from multi_platform_poster import MultiPlatformPoster
            
            video_url = params.get('video_url')
            caption = params.get('caption', '')
            hashtags = params.get('hashtags', '#AI #Generated')
            
            if not video_url:
                return ExecutionResult(
                    tool_id="tiktok_post",
                    success=False,
                    error="No video_url provided"
                )
            
            if callback:
                callback({"status": "posting", "message": "Posting to TikTok..."})
            
            # Initialize multi-platform poster
            poster = MultiPlatformPoster()
            
            # Post to TikTok
            success = await poster.post_to_tiktok(
                image_path=video_url,  # Note: multi_platform_poster uses image_path param for videos too
                caption=f"{caption} {hashtags}"
            )
            
            if success:
                return ExecutionResult(
                    tool_id="tiktok_post",
                    success=True,
                    output=f"✅ Posted to TikTok!\n\nCaption: {caption[:100]}...",
                    output_type="text",
                    artifacts=[{"type": "tiktok_post", "caption": caption}]
                )
            else:
                return ExecutionResult(
                    tool_id="tiktok_post",
                    success=False,
                    error="TikTok posting failed"
                )
        except Exception as e:
            return ExecutionResult(
                tool_id="tiktok_post",
                success=False,
                error=f"TikTok posting failed: {e}"
            )
    
    async def _publish_to_twitter(self, params, callback) -> ExecutionResult:
        """Publish tweet to Twitter."""
        try:
            from multi_platform_poster import MultiPlatformPoster
            
            text = params.get('text', '')
            image_url = params.get('image_url')
            
            if not text and not image_url:
                return ExecutionResult(
                    tool_id="twitter_post",
                    success=False,
                    error="No text or image_url provided"
                )
            
            if callback:
                callback({"status": "posting", "message": "Posting to Twitter..."})
            
            # Initialize multi-platform poster
            poster = MultiPlatformPoster()
            
            # Post to Twitter
            success = await poster.post_to_twitter(
                image_path=image_url,
                caption=text
            )
            
            if success:
                return ExecutionResult(
                    tool_id="twitter_post",
                    success=True,
                    output=f"✅ Posted to Twitter!\n\nTweet: {text[:100]}...",
                    output_type="text",
                    artifacts=[{"type": "twitter_post", "text": text}]
                )
            else:
                return ExecutionResult(
                    tool_id="twitter_post",
                    success=False,
                    error="Twitter posting failed"
                )
        except Exception as e:
            return ExecutionResult(
                tool_id="twitter_post",
                success=False,
                error=f"Twitter posting failed: {e}"
            )
    
    async def _publish_to_instagram(self, params, callback) -> ExecutionResult:
        """Publish post to Instagram."""
        try:
            from multi_platform_poster import MultiPlatformPoster
            
            image_url = params.get('image_url')
            caption = params.get('caption', '')
            
            if not image_url:
                return ExecutionResult(
                    tool_id="instagram_post",
                    success=False,
                    error="No image_url provided"
                )
            
            if callback:
                callback({"status": "posting", "message": "Posting to Instagram..."})
            
            # Initialize multi-platform poster
            poster = MultiPlatformPoster()
            
            # Post to Instagram
            success = await poster.post_to_instagram(
                image_path=image_url,
                caption=caption
            )
            
            if success:
                return ExecutionResult(
                    tool_id="instagram_post",
                    success=True,
                    output=f"✅ Posted to Instagram!\n\nCaption: {caption[:100]}...",
                    output_type="text",
                    artifacts=[{"type": "instagram_post", "caption": caption}]
                )
            else:
                return ExecutionResult(
                    tool_id="instagram_post",
                    success=False,
                    error="Instagram posting failed"
                )
        except Exception as e:
            return ExecutionResult(
                tool_id="instagram_post",
                success=False,
                error=f"Instagram posting failed: {e}"
            )
    
    async def _execute_browser(self, tool, params, callback) -> ExecutionResult:
        """Execute browser automation."""
        if not self.browser or not self.browser.is_available:
            return ExecutionResult(
                tool_id=tool.id,
                success=False,
                error="Browser automation not available. Install browser-use and set ANTHROPIC_API_KEY."
            )
        
        task = params.get('task', '')
        max_steps = params.get('max_steps', 20)
        
        if callback:
            callback({"status": "running", "message": "Running browser automation..."})
        
        try:
            result = await self.browser.execute(
                task=task,
                max_steps=max_steps,
                retry_count=2
            )
            
            if result.success:
                return ExecutionResult(
                    tool_id=tool.id,
                    success=True,
                    output=f"✅ Browser task completed!\n\nSteps: {result.steps_taken}\nDuration: {result.duration_seconds:.1f}s\n\nResult: {result.result_text}",
                    output_type="text"
                )
            else:
                return ExecutionResult(
                    tool_id=tool.id,
                    success=False,
                    error=f"Browser task failed: {', '.join(result.errors)}"
                )
        except Exception as e:
            return ExecutionResult(
                tool_id=tool.id,
                success=False,
                error=f"Browser automation failed: {e}"
            )


# ============================================================================
# Context Tracker - Maintains Cross-App Knowledge
# ============================================================================

class ContextTracker:
    """
    Tracks context across the entire app so Otto knows:
    - What campaigns exist
    - What files are available
    - What the user is currently working on
    - Recent generations
    """
    
    def __init__(self):
        self.context = {
            'last_generated_image': None,
            'last_generated_video': None,
            'last_generated_audio': None,
            'current_campaign': None,
            'available_campaigns': [],
            'recent_files': [],
            'session_info': {},
            'user_preferences': {}
        }
    
    def update(self, key: str, value: Any):
        """Update a context value."""
        self.context[key] = value
    
    def get(self, key: str, default=None) -> Any:
        """Get a context value."""
        return self.context.get(key, default)
    
    def get_all(self) -> Dict:
        """Get all context."""
        return self.context.copy()
    
    def track_generation(self, output_type: str, url: str, metadata: Dict = None):
        """Track a generated asset."""
        if output_type == "image":
            self.context['last_generated_image'] = url
        elif output_type == "video":
            self.context['last_generated_video'] = url
        elif output_type == "audio":
            self.context['last_generated_audio'] = url
        
        # Add to recent files
        if 'recent_generations' not in self.context:
            self.context['recent_generations'] = []
        
        self.context['recent_generations'].insert(0, {
            'type': output_type,
            'url': url,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        })
        
        # Keep only last 20
        self.context['recent_generations'] = self.context['recent_generations'][:20]
    
    def scan_campaigns(self):
        """Scan filesystem for available campaigns."""
        campaigns_dir = Path("campaigns")
        if campaigns_dir.exists():
            campaigns = []
            for camp_dir in campaigns_dir.iterdir():
                if camp_dir.is_dir():
                    campaigns.append({
                        'name': camp_dir.name,
                        'path': str(camp_dir),
                        'modified': datetime.fromtimestamp(camp_dir.stat().st_mtime).isoformat()
                    })
            self.context['available_campaigns'] = sorted(campaigns, key=lambda x: x['modified'], reverse=True)
    
    def build_knowledge_summary(self) -> str:
        """Build a knowledge summary for Otto."""
        lines = ["=== CURRENT CONTEXT ==="]
        
        if self.context.get('last_generated_image'):
            lines.append(f"Last Image: {self.context['last_generated_image'][:50]}...")
        
        if self.context.get('last_generated_video'):
            lines.append(f"Last Video: {self.context['last_generated_video'][:50]}...")
        
        if self.context.get('current_campaign'):
            lines.append(f"Current Campaign: {self.context['current_campaign']}")
        
        if self.context.get('available_campaigns'):
            lines.append(f"\nAvailable Campaigns: {len(self.context['available_campaigns'])}")
            for camp in self.context['available_campaigns'][:5]:
                lines.append(f"  - {camp['name']}")
        
        return "\n".join(lines)
