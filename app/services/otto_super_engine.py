"""
OTTO SUPER ENGINE - Hyperintelligent AI Assistant
=================================================
The ultimate AI assistant that can understand any request and execute it autonomously.

CAPABILITIES:
✓ Access to ALL playground models (50+ image/video/audio/3D models)
✓ Complete campaign generation end-to-end
✓ Real-time result display (images, videos, audio inline)
✓ Persistent chat memory with save/load
✓ Smart intent parsing and model selection
✓ External service integration (YouTube, Printify, Shopify)
✓ Cross-app knowledge (campaigns, files, session state)
✓ Complex multi-step workflow execution
✓ Browser automation with credential management

DESIGN PHILOSOPHY:
- User should only need Otto to accomplish anything
- Otto understands natural language and routes to correct tools
- Results appear in real-time as they're generated
- Otto remembers context across sessions
- Otto can execute complete workflows autonomously
"""

import os
import json
import logging
import asyncio
import uuid
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum
import streamlit as st

logger = logging.getLogger(__name__)


# ============================================================================
# TOOL REGISTRY - Every App Feature Accessible to Otto
# ============================================================================

class ToolCategory(Enum):
    """Categories of tools Otto can use."""
    IMAGE_GENERATION = "image_generation"
    VIDEO_GENERATION = "video_generation"
    AUDIO_GENERATION = "audio_generation"
    MUSIC_GENERATION = "music_generation"
    SPEECH_GENERATION = "speech_generation"
    MODEL_3D = "3d_generation"
    IMAGE_EDITING = "image_editing"
    VIDEO_EDITING = "video_editing"
    MARKETING = "marketing"
    CAMPAIGN = "campaign"
    PUBLISHING = "publishing"
    BROWSER = "browser"
    ANALYTICS = "analytics"
    FILE_MANAGEMENT = "files"
    CONTENT_WRITING = "content"


@dataclass
class Tool:
    """Represents a single tool/capability Otto can use."""
    id: str
    name: str
    description: str
    category: ToolCategory
    model_ref: Optional[str] = None  # Replicate model reference
    parameters: Dict = field(default_factory=dict)
    output_type: str = "text"  # text, image, video, audio, file
    requires_confirmation: bool = False
    cost_estimate: str = "$0.01-0.10"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category.value,
            'model_ref': self.model_ref,
            'parameters': self.parameters,
            'output_type': self.output_type,
            'requires_confirmation': self.requires_confirmation,
            'cost_estimate': self.cost_estimate
        }


class ToolRegistry:
    """
    Central registry of all tools/capabilities Otto can use.
    Populated from playground_models.py and app features.
    """
    
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self._initialize_tools()
    
    def _initialize_tools(self):
        """Initialize all available tools from the platform."""
        
        # ========== IMAGE GENERATION MODELS ==========
        self.register(Tool(
            id="flux_fast",
            name="Flux Fast Image Generation",
            description="Ultra-fast high-quality image generation in 4 steps. Best for product designs, concepts, artwork.",
            category=ToolCategory.IMAGE_GENERATION,
            model_ref="prunaai/flux-fast",
            parameters={"prompt": "required", "aspect_ratio": "1:1", "steps": 4},
            output_type="image",
            cost_estimate="$0.003"
        ))
        
        self.register(Tool(
            id="flux_dev",
            name="Flux Dev Image Generation",
            description="High-quality detailed image generation. Better quality than Flux Fast, slightly slower.",
            category=ToolCategory.IMAGE_GENERATION,
            model_ref="black-forest-labs/flux-dev",
            parameters={"prompt": "required", "aspect_ratio": "1:1"},
            output_type="image",
            cost_estimate="$0.02"
        ))
        
        self.register(Tool(
            id="sdxl",
            name="Stable Diffusion XL",
            description="Versatile image generation with fine control over style and composition.",
            category=ToolCategory.IMAGE_GENERATION,
            model_ref="stability-ai/sdxl",
            parameters={"prompt": "required", "negative_prompt": "optional", "width": 1024, "height": 1024},
            output_type="image",
            cost_estimate="$0.01"
        ))
        
        self.register(Tool(
            id="seedream_4k",
            name="SeeDream 4K",
            description="Unified text-to-image up to 4K resolution for ultra-high quality.",
            category=ToolCategory.IMAGE_GENERATION,
            model_ref="bytedance/seedream-4",
            parameters={"prompt": "required", "aspect_ratio": "1:1"},
            output_type="image",
            cost_estimate="$0.05"
        ))
        
        self.register(Tool(
            id="imagen_4_ultra",
            name="Google Imagen 4 Ultra",
            description="Google's highest quality image model with photorealistic results.",
            category=ToolCategory.IMAGE_GENERATION,
            model_ref="google/imagen-4-ultra",
            parameters={"prompt": "required", "aspect_ratio": "1:1"},
            output_type="image",
            cost_estimate="$0.04"
        ))
        
        # ========== VIDEO GENERATION MODELS ==========
        self.register(Tool(
            id="sora_2",
            name="Sora 2 Video Generation",
            description="OpenAI's flagship video model with synced audio. Cinematic quality up to 10 seconds.",
            category=ToolCategory.VIDEO_GENERATION,
            model_ref="openai/sora-2",
            parameters={"prompt": "required", "image": "optional", "duration": 5},
            output_type="video",
            cost_estimate="$0.50",
            requires_confirmation=True
        ))
        
        self.register(Tool(
            id="kling_v2_5",
            name="Kling v2.5 Turbo Pro",
            description="Pro-level text-to-video and image-to-video. Great motion and quality.",
            category=ToolCategory.VIDEO_GENERATION,
            model_ref="kwaivgi/kling-v2.5-turbo-pro",
            parameters={"prompt": "required", "image": "optional", "duration": 5, "motion_level": 4},
            output_type="video",
            cost_estimate="$0.20"
        ))
        
        self.register(Tool(
            id="veo_3_1_fast",
            name="Veo 3.1 Fast",
            description="Google's fast video generation with context-aware audio.",
            category=ToolCategory.VIDEO_GENERATION,
            model_ref="google/veo-3.1-fast",
            parameters={"prompt": "required", "image": "optional", "duration": 5},
            output_type="video",
            cost_estimate="$0.15"
        ))
        
        self.register(Tool(
            id="luma_ray_2",
            name="Luma Ray 2",
            description="High-quality cinematic video generation.",
            category=ToolCategory.VIDEO_GENERATION,
            model_ref="luma/ray-2-540p",
            parameters={"prompt": "required", "image": "optional"},
            output_type="video",
            cost_estimate="$0.12"
        ))
        
        # ========== MUSIC & AUDIO MODELS ==========
        self.register(Tool(
            id="lyria_2",
            name="Google Lyria 2 Music",
            description="48kHz stereo music generation up to 2 minutes. Professional quality.",
            category=ToolCategory.MUSIC_GENERATION,
            model_ref="google/lyria-2",
            parameters={"prompt": "required", "duration": 30},
            output_type="audio",
            cost_estimate="$0.10"
        ))
        
        self.register(Tool(
            id="musicgen",
            name="Meta MusicGen",
            description="Generate music from text or melody. Good for background music.",
            category=ToolCategory.MUSIC_GENERATION,
            model_ref="meta/musicgen",
            parameters={"prompt": "required", "duration": 8, "model_version": "stereo-large"},
            output_type="audio",
            cost_estimate="$0.02"
        ))
        
        self.register(Tool(
            id="speech_hd",
            name="Minimax Speech HD",
            description="HD voice synthesis with emotion control and multilingual support.",
            category=ToolCategory.SPEECH_GENERATION,
            model_ref="minimax/speech-02-hd",
            parameters={"text": "required", "voice": "female-1", "emotion": "neutral", "language": "en"},
            output_type="audio",
            cost_estimate="$0.01"
        ))
        
        # ========== 3D GENERATION ==========
        self.register(Tool(
            id="hunyuan3d_2",
            name="Hunyuan3D-2",
            description="High-resolution textured 3D assets from text or image.",
            category=ToolCategory.MODEL_3D,
            model_ref="tencent/hunyuan3d-2",
            parameters={"prompt": "optional", "image": "optional"},
            output_type="file",
            cost_estimate="$0.20"
        ))
        
        # ========== MARKETING & ADS ==========
        self.register(Tool(
            id="flux_static_ads",
            name="Flux Static Ads",
            description="Create professional static ads for brands and products.",
            category=ToolCategory.MARKETING,
            model_ref="loolau/flux-static-ads",
            parameters={"prompt": "required", "product_image": "optional", "aspect_ratio": "1:1"},
            output_type="image",
            cost_estimate="$0.05"
        ))
        
        self.register(Tool(
            id="ads_for_products",
            name="Product Ad Generator",
            description="Create stunning ads using an image of a product. Multiple variations.",
            category=ToolCategory.MARKETING,
            model_ref="pipeline-examples/ads-for-products",
            parameters={"product_image": "required", "num_prompts": 3},
            output_type="image",
            cost_estimate="$0.10"
        ))
        
        # ========== IMAGE EDITING ==========
        self.register(Tool(
            id="flux_image_editing",
            name="Flux Image Editing",
            description="Edit existing images with text prompts using Flux model.",
            category=ToolCategory.IMAGE_EDITING,
            model_ref="hardikdava/flux-image-editing",
            parameters={"prompt": "required", "image": "required"},
            output_type="image",
            cost_estimate="$0.03"
        ))
        
        # ========== PLATFORM FEATURES ==========
        self.register(Tool(
            id="campaign_generator",
            name="Complete Campaign Generation",
            description="Generate full marketing campaign: design, mockup, description, video, social ads, blog post.",
            category=ToolCategory.CAMPAIGN,
            parameters={"concept": "required", "style": "lifestyle"},
            output_type="file",
            cost_estimate="$1-3",
            requires_confirmation=True
        ))
        
        self.register(Tool(
            id="printify_upload",
            name="Upload to Printify",
            description="Upload design image to Printify and optionally create product.",
            category=ToolCategory.PUBLISHING,
            parameters={"image_url": "required", "create_product": False},
            output_type="text",
            requires_confirmation=True
        ))
        
        self.register(Tool(
            id="youtube_upload",
            name="Upload to YouTube",
            description="Upload video to YouTube with title, description, and metadata.",
            category=ToolCategory.PUBLISHING,
            parameters={"video_url": "required", "title": "required", "description": "optional"},
            output_type="text",
            requires_confirmation=True
        ))
        
        self.register(Tool(
            id="shopify_blog",
            name="Publish Shopify Blog Post",
            description="Create and publish SEO-optimized blog post to Shopify.",
            category=ToolCategory.PUBLISHING,
            parameters={"title": "required", "content": "required", "image_url": "optional"},
            output_type="text",
            requires_confirmation=True
        ))
        
        self.register(Tool(
            id="pinterest_pin",
            name="Post to Pinterest",
            description="Create pin on Pinterest with image, title, and description.",
            category=ToolCategory.PUBLISHING,
            parameters={"image_url": "required", "title": "required", "description": "optional", "board": "optional", "link": "optional"},
            output_type="text",
            requires_confirmation=False
        ))
        
        self.register(Tool(
            id="tiktok_post",
            name="Post to TikTok",
            description="Upload video to TikTok with caption and hashtags.",
            category=ToolCategory.PUBLISHING,
            parameters={"video_url": "required", "caption": "required", "hashtags": "optional"},
            output_type="text",
            requires_confirmation=False
        ))
        
        self.register(Tool(
            id="twitter_post",
            name="Post to Twitter",
            description="Post tweet with optional image.",
            category=ToolCategory.PUBLISHING,
            parameters={"text": "required", "image_url": "optional"},
            output_type="text",
            requires_confirmation=False
        ))
        
        self.register(Tool(
            id="instagram_post",
            name="Post to Instagram",
            description="Post to Instagram feed with image and caption.",
            category=ToolCategory.PUBLISHING,
            parameters={"image_url": "required", "caption": "required"},
            output_type="text",
            requires_confirmation=False
        ))
        
        self.register(Tool(
            id="browser_automation",
            name="Browser Automation",
            description="Automate web browser tasks: navigate, click, fill forms, post to social media.",
            category=ToolCategory.BROWSER,
            parameters={"task": "required", "max_steps": 20},
            output_type="text"
        ))
        
        logger.info(f"✅ Tool Registry initialized with {len(self.tools)} tools")
    
    def register(self, tool: Tool):
        """Register a new tool."""
        self.tools[tool.id] = tool
    
    def get(self, tool_id: str) -> Optional[Tool]:
        """Get a tool by ID."""
        return self.tools.get(tool_id)
    
    def search(self, query: str, category: Optional[ToolCategory] = None) -> List[Tool]:
        """Search for tools matching query."""
        query_lower = query.lower()
        results = []
        
        for tool in self.tools.values():
            if category and tool.category != category:
                continue
            
            if (query_lower in tool.name.lower() or 
                query_lower in tool.description.lower() or
                (tool.model_ref and query_lower in tool.model_ref.lower())):
                results.append(tool)
        
        return results
    
    def list_by_category(self, category: ToolCategory) -> List[Tool]:
        """List all tools in a category."""
        return [t for t in self.tools.values() if t.category == category]
    
    def get_all_categories(self) -> List[str]:
        """Get all available categories."""
        return [cat.value for cat in ToolCategory]


# ============================================================================
# INTELLIGENT INTENT PARSER - Routes Requests to Correct Tools - ENHANCED
# ============================================================================

# Pre-compiled keyword sets for FAST detection
_IMAGE_KEYWORDS = frozenset(['create', 'generate', 'make', 'design', 'artwork', 'picture', 'image', 'photo', 'drawing', 'illustration', 'logo', 'graphic', 'thumbnail'])
_VIDEO_KEYWORDS = frozenset(['video', 'animate', 'commercial', 'promo video', 'clip', 'movie', 'motion'])
_MUSIC_KEYWORDS = frozenset(['music', 'song', 'soundtrack', 'tune', 'melody', 'beat', 'audio track'])
_SPEECH_KEYWORDS = frozenset(['voiceover', 'voice over', 'text to speech', 'narration', 'speak', 'say', 'narrate'])
_MARKETING_KEYWORDS = frozenset(['ad', 'advertisement', 'marketing', 'social media post', 'promo', 'banner', 'flyer'])
_CAMPAIGN_KEYWORDS = frozenset(['campaign', 'end to end', 'complete', 'full workflow', 'everything', 'full campaign'])
_PUBLISHING_KEYWORDS = frozenset(['upload', 'publish', 'post to', 'share on', 'put on', 'send to'])
_BROWSER_KEYWORDS = frozenset(['browse', 'navigate', 'go to', 'click on', 'fill form', 'search on', 'open website'])

@dataclass
class ParsedIntent:
    """Represents a parsed user intent."""
    primary_goal: str
    tools_needed: List[str]  # Tool IDs
    parameters: Dict[str, Any]
    confidence: float
    requires_clarification: bool = False
    clarification_question: Optional[str] = None
    estimated_cost: str = ""
    estimated_time: str = ""


class IntentParser:
    """
    Hyperintelligent intent parser that understands user requests
    and routes them to the correct tools and models.
    
    ENHANCED Features:
    - Pre-compiled keyword sets for O(1) lookup
    - Smart model selection based on quality/speed tradeoffs
    - Context-aware parameter extraction
    - Confidence scoring for routing decisions
    """
    
    def __init__(self, tool_registry: ToolRegistry, replicate_api):
        self.registry = tool_registry
        self.replicate = replicate_api
        self._parse_cache = {}  # Cache recent parses
    
    def _quick_keyword_match(self, msg_lower: str, keywords: frozenset) -> bool:
        """Fast keyword matching using word boundaries."""
        words = set(msg_lower.split())
        return bool(words & keywords)
    
    async def parse(self, user_message: str, context: Dict = None) -> ParsedIntent:
        """
        Parse user message to determine intent and required tools.
        
        This is the SMART routing logic that makes Otto hyperintelligent.
        Uses fast-path keyword detection before falling back to AI parsing.
        """
        context = context or {}
        msg_lower = user_message.lower()
        
        # Check cache first
        cache_key = hash((user_message, str(sorted(context.items()))))
        if cache_key in self._parse_cache:
            return self._parse_cache[cache_key]
        
        # ========== KEYWORD-BASED DETECTION (Fast Path) ==========
        
        # Image generation
        if any(kw in msg_lower for kw in ['create', 'generate', 'make', 'design', 'artwork', 'picture', 'image', 'photo', 'drawing', 'illustration']):
            # Check if it's NOT a video/music/other request
            if not any(kw in msg_lower for kw in ['video', 'music', 'audio', 'voice', 'speech', 'campaign']):
                return self._parse_image_generation(user_message, msg_lower)
        
        # Video generation
        if any(kw in msg_lower for kw in ['create video', 'generate video', 'make video', 'animate', 'commercial', 'promo video']):
            return self._parse_video_generation(user_message, msg_lower, context)
        
        # Music generation
        if any(kw in msg_lower for kw in ['create music', 'generate music', 'background music', 'soundtrack', 'song', 'tune']):
            return self._parse_music_generation(user_message, msg_lower)
        
        # Speech/voiceover
        if any(kw in msg_lower for kw in ['voiceover', 'voice over', 'text to speech', 'narration', 'speak', 'say']):
            return self._parse_speech_generation(user_message, msg_lower)
        
        # Marketing/Ads
        if any(kw in msg_lower for kw in ['ad', 'advertisement', 'marketing', 'social media post', 'promo']):
            return self._parse_marketing(user_message, msg_lower, context)
        
        # Campaign (complex workflow)
        if any(kw in msg_lower for kw in ['campaign', 'end to end', 'complete', 'full workflow', 'everything']):
            return self._parse_campaign(user_message, msg_lower)
        
        # Publishing
        if any(kw in msg_lower for kw in ['upload', 'publish', 'post to', 'share on']):
            return self._parse_publishing(user_message, msg_lower, context)
        
        # Browser automation
        if any(kw in msg_lower for kw in ['browse', 'navigate', 'go to', 'click on', 'fill form', 'search on']):
            return self._parse_browser(user_message, msg_lower)
        
        # ========== AI-POWERED PARSING (Smart Path) ==========
        # Use AI to understand complex/ambiguous requests
        return await self._ai_parse(user_message, context)
    
    def _parse_image_generation(self, message: str, msg_lower: str) -> ParsedIntent:
        """Parse image generation requests with smart model selection."""
        
        # Detect preferred model from message
        tool_id = "flux_fast"  # default
        
        if any(kw in msg_lower for kw in ['photorealistic', 'photo realistic', 'realistic photo', 'imagen']):
            tool_id = "imagen_4_ultra"
        elif any(kw in msg_lower for kw in ['4k', 'ultra high res', 'seedream']):
            tool_id = "seedream_4k"
        elif any(kw in msg_lower for kw in ['sdxl', 'stable diffusion']):
            tool_id = "sdxl"
        elif any(kw in msg_lower for kw in ['flux dev', 'high quality']):
            tool_id = "flux_dev"
        
        # Extract prompt
        prompt_triggers = ['create', 'generate', 'make', 'design', 'image of', 'picture of']
        prompt = message
        for trigger in prompt_triggers:
            if trigger in msg_lower:
                idx = msg_lower.index(trigger) + len(trigger)
                prompt = message[idx:].strip()
                break
        
        # Detect aspect ratio
        aspect_ratio = "1:1"
        if any(kw in msg_lower for kw in ['wide', 'landscape', '16:9', 'widescreen']):
            aspect_ratio = "16:9"
        elif any(kw in msg_lower for kw in ['tall', 'portrait', '9:16', 'vertical']):
            aspect_ratio = "9:16"
        
        tool = self.registry.get(tool_id)
        
        return ParsedIntent(
            primary_goal=f"Generate image: {prompt[:50]}...",
            tools_needed=[tool_id],
            parameters={"prompt": prompt, "aspect_ratio": aspect_ratio},
            confidence=0.9,
            estimated_cost=tool.cost_estimate if tool else "$0.01",
            estimated_time="10-30 seconds"
        )
    
    def _parse_video_generation(self, message: str, msg_lower: str, context: Dict) -> ParsedIntent:
        """Parse video generation with smart model selection."""
        
        # Check if we have an image to animate
        image_url = context.get('last_generated_image') or context.get('selected_image')
        
        # Model selection
        tool_id = "kling_v2_5"  # default
        
        if any(kw in msg_lower for kw in ['sora', 'cinematic', 'high quality', 'with audio']):
            tool_id = "sora_2"
        elif any(kw in msg_lower for kw in ['veo', 'google', 'fast']):
            tool_id = "veo_3_1_fast"
        elif any(kw in msg_lower for kw in ['luma', 'ray']):
            tool_id = "luma_ray_2"
        
        # Extract prompt
        prompt = message
        for trigger in ['create', 'generate', 'make', 'animate']:
            if trigger in msg_lower:
                idx = msg_lower.index(trigger) + len(trigger)
                prompt = message[idx:].strip()
                break
        
        # Duration
        duration = 5
        if '10 second' in msg_lower or '10s' in msg_lower:
            duration = 10
        
        tool = self.registry.get(tool_id)
        
        params = {"prompt": prompt, "duration": duration}
        if image_url:
            params["image"] = image_url
        
        return ParsedIntent(
            primary_goal=f"Generate video: {prompt[:50]}...",
            tools_needed=[tool_id],
            parameters=params,
            confidence=0.85,
            estimated_cost=tool.cost_estimate if tool else "$0.20",
            estimated_time="1-3 minutes"
        )
    
    def _parse_music_generation(self, message: str, msg_lower: str) -> ParsedIntent:
        """Parse music generation requests."""
        
        tool_id = "lyria_2"  # default - best quality
        
        if any(kw in msg_lower for kw in ['musicgen', 'meta', 'quick']):
            tool_id = "musicgen"
        
        # Extract description
        prompt = message
        for trigger in ['create', 'generate', 'make']:
            if trigger in msg_lower:
                idx = msg_lower.index(trigger) + len(trigger)
                prompt = message[idx:].strip()
                break
        
        # Duration
        duration = 30
        if '1 minute' in msg_lower or '60 second' in msg_lower:
            duration = 60
        elif '2 minute' in msg_lower or '120 second' in msg_lower:
            duration = 120
        
        tool = self.registry.get(tool_id)
        
        return ParsedIntent(
            primary_goal=f"Generate music: {prompt[:50]}...",
            tools_needed=[tool_id],
            parameters={"prompt": prompt, "duration": duration},
            confidence=0.9,
            estimated_cost=tool.cost_estimate if tool else "$0.10",
            estimated_time="30-60 seconds"
        )
    
    def _parse_speech_generation(self, message: str, msg_lower: str) -> ParsedIntent:
        """Parse speech/voiceover requests."""
        
        # Extract text to speak
        text = message
        for trigger in ['say', 'speak', 'voiceover', 'narrate']:
            if trigger in msg_lower:
                idx = msg_lower.index(trigger) + len(trigger)
                text = message[idx:].strip().strip('"').strip("'")
                break
        
        # Voice selection
        voice = "female-1"
        if any(kw in msg_lower for kw in ['male voice', 'man', 'masculine']):
            voice = "male-1"
        
        # Emotion
        emotion = "neutral"
        if 'happy' in msg_lower or 'excited' in msg_lower:
            emotion = "happy"
        elif 'sad' in msg_lower:
            emotion = "sad"
        
        return ParsedIntent(
            primary_goal=f"Generate voiceover: {text[:50]}...",
            tools_needed=["speech_hd"],
            parameters={"text": text, "voice": voice, "emotion": emotion},
            confidence=0.9,
            estimated_cost="$0.01",
            estimated_time="5-10 seconds"
        )
    
    def _parse_marketing(self, message: str, msg_lower: str, context: Dict) -> ParsedIntent:
        """Parse marketing/ad creation requests."""
        
        # Check if we have a product image
        image_url = context.get('last_generated_image') or context.get('product_image')
        
        if image_url:
            tool_id = "ads_for_products"
            params = {"product_image": image_url, "num_prompts": 3}
        else:
            tool_id = "flux_static_ads"
            prompt = message
            params = {"prompt": prompt, "aspect_ratio": "1:1"}
        
        return ParsedIntent(
            primary_goal="Create marketing ads",
            tools_needed=[tool_id],
            parameters=params,
            confidence=0.85,
            estimated_cost="$0.10",
            estimated_time="20-40 seconds"
        )
    
    def _parse_campaign(self, message: str, msg_lower: str) -> ParsedIntent:
        """Parse complete campaign requests."""
        
        # Extract concept
        concept = message
        for trigger in ['campaign for', 'campaign about', 'create campaign']:
            if trigger in msg_lower:
                idx = msg_lower.index(trigger) + len(trigger)
                concept = message[idx:].strip()
                break
        
        return ParsedIntent(
            primary_goal=f"Complete campaign: {concept[:50]}...",
            tools_needed=["campaign_generator"],
            parameters={"concept": concept, "style": "lifestyle"},
            confidence=0.9,
            estimated_cost="$1-3",
            estimated_time="5-10 minutes",
            requires_clarification=False
        )
    
    def _parse_publishing(self, message: str, msg_lower: str, context: Dict) -> ParsedIntent:
        """Parse publishing/upload requests."""
        
        tools = []
        params = {}
        
        if 'printify' in msg_lower:
            tools.append("printify_upload")
            image_url = context.get('last_generated_image')
            if image_url:
                params["image_url"] = image_url
        
        if 'youtube' in msg_lower:
            tools.append("youtube_upload")
            video_url = context.get('last_generated_video')
            if video_url:
                params["video_url"] = video_url
                params["title"] = context.get('video_title', 'Otto Mate Creation')
        
        if 'shopify' in msg_lower or 'blog' in msg_lower:
            tools.append("shopify_blog")
        
        if 'pinterest' in msg_lower or 'pin' in msg_lower:
            tools.append("pinterest_pin")
            image_url = context.get('last_generated_image')
            if image_url:
                params["image_url"] = image_url
                # Extract title from message
                title = message[:100] if len(message) < 100 else message[:97] + "..."
                params["title"] = title
                params["description"] = message
        
        if 'tiktok' in msg_lower or 'tik tok' in msg_lower:
            tools.append("tiktok_post")
            video_url = context.get('last_generated_video')
            if video_url:
                params["video_url"] = video_url
                params["caption"] = message[:300]  # TikTok caption limit
        
        if 'twitter' in msg_lower or 'tweet' in msg_lower:
            tools.append("twitter_post")
            image_url = context.get('last_generated_image')
            if image_url:
                params["image_url"] = image_url
            params["text"] = message[:280]  # Twitter limit
        
        if 'instagram' in msg_lower or 'insta' in msg_lower:
            tools.append("instagram_post")
            image_url = context.get('last_generated_image')
            if image_url:
                params["image_url"] = image_url
                params["caption"] = message
        
        if not tools:
            return ParsedIntent(
                primary_goal="Publish content",
                tools_needed=[],
                parameters={},
                confidence=0.5,
                requires_clarification=True,
                clarification_question="Where would you like to publish? (Printify/YouTube/Shopify/Pinterest/TikTok/Twitter/Instagram)"
            )
        
        return ParsedIntent(
            primary_goal="Publish to external services",
            tools_needed=tools,
            parameters=params,
            confidence=0.8,
            estimated_cost="Free",
            estimated_time="10-30 seconds"
        )
    
    def _parse_browser(self, message: str, msg_lower: str) -> ParsedIntent:
        """Parse browser automation requests."""
        
        return ParsedIntent(
            primary_goal="Browser automation task",
            tools_needed=["browser_automation"],
            parameters={"task": message, "max_steps": 20},
            confidence=0.85,
            estimated_cost="Free",
            estimated_time="30-60 seconds"
        )
    
    async def _ai_parse(self, message: str, context: Dict) -> ParsedIntent:
        """Use AI to parse complex/ambiguous requests."""
        
        # Build parsing prompt with full tool registry
        tools_desc = []
        for cat in ToolCategory:
            cat_tools = self.registry.list_by_category(cat)
            if cat_tools:
                tools_desc.append(f"\n**{cat.value}:**")
                for tool in cat_tools[:5]:  # Top 5 per category
                    tools_desc.append(f"  - {tool.id}: {tool.description}")
        
        parsing_prompt = f"""You are Otto's intent parser. Analyze this user request and determine what tools to use.

USER REQUEST: {message}

AVAILABLE TOOLS:
{''.join(tools_desc)}

CONTEXT:
- Last generated image: {context.get('last_generated_image', 'None')}
- Last generated video: {context.get('last_generated_video', 'None')}
- Current campaign: {context.get('current_campaign', 'None')}

Respond in JSON:
{{
    "primary_goal": "brief description",
    "tools_needed": ["tool_id1", "tool_id2"],
    "parameters": {{"key": "value"}},
    "confidence": 0.0-1.0,
    "estimated_time": "X minutes"
}}
"""
        
        try:
            response = self.replicate.generate_text(
                prompt=parsing_prompt,
                max_tokens=400,
                temperature=0.2
            )
            
            # Parse JSON
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
                return ParsedIntent(
                    primary_goal=data.get('primary_goal', message),
                    tools_needed=data.get('tools_needed', []),
                    parameters=data.get('parameters', {}),
                    confidence=data.get('confidence', 0.7),
                    estimated_time=data.get('estimated_time', '1-2 minutes')
                )
        except Exception as e:
            logger.error(f"AI parsing failed: {e}")
        
        # Fallback
        return ParsedIntent(
            primary_goal=message,
            tools_needed=[],
            parameters={},
            confidence=0.3,
            requires_clarification=True,
            clarification_question="I'm not sure what you'd like me to do. Could you rephrase that?"
        )


# ============================================================================
# CHAT MEMORY SYSTEM - Persistent Conversations
# ============================================================================

@dataclass
class ChatMessage:
    """A single chat message."""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)  # artifacts, tools_used, etc.
    
    def to_dict(self) -> Dict:
        return {
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ChatMessage':
        return cls(
            role=data['role'],
            content=data['content'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            metadata=data.get('metadata', {})
        )


@dataclass
class ChatSession:
    """A complete chat session with memory."""
    id: str
    title: str
    messages: List[ChatMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    context: Dict = field(default_factory=dict)  # Persistent context across messages
    
    def add_message(self, role: str, content: str, metadata: Dict = None):
        """Add a message to the session."""
        msg = ChatMessage(role=role, content=content, metadata=metadata or {})
        self.messages.append(msg)
        self.updated_at = datetime.now()
    
    def get_recent_messages(self, count: int = 10) -> List[ChatMessage]:
        """Get the last N messages."""
        return self.messages[-count:]
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'title': self.title,
            'messages': [m.to_dict() for m in self.messages],
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'context': self.context
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ChatSession':
        session = cls(
            id=data['id'],
            title=data['title'],
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            context=data.get('context', {})
        )
        session.messages = [ChatMessage.from_dict(m) for m in data.get('messages', [])]
        return session


class MemoryManager:
    """Manages persistent chat memory with save/load capabilities."""
    
    def __init__(self, storage_dir: Path = None):
        self.storage_dir = storage_dir or Path("chat_history")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.current_session: Optional[ChatSession] = None
    
    def create_session(self, title: str = None) -> ChatSession:
        """Create a new chat session."""
        session_id = str(uuid.uuid4())[:8]
        title = title or f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        self.current_session = ChatSession(id=session_id, title=title)
        return self.current_session
    
    def save_session(self, session: ChatSession = None) -> Path:
        """Save a session to disk."""
        session = session or self.current_session
        if not session:
            raise ValueError("No session to save")
        
        file_path = self.storage_dir / f"{session.id}.json"
        with open(file_path, 'w') as f:
            json.dump(session.to_dict(), f, indent=2)
        
        logger.info(f"💾 Session saved: {file_path}")
        return file_path
    
    def load_session(self, session_id: str) -> ChatSession:
        """Load a session from disk."""
        file_path = self.storage_dir / f"{session_id}.json"
        
        if not file_path.exists():
            raise FileNotFoundError(f"Session {session_id} not found")
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        session = ChatSession.from_dict(data)
        self.current_session = session
        logger.info(f"📂 Session loaded: {session.title}")
        return session
    
    def list_sessions(self) -> List[Dict]:
        """List all saved sessions."""
        sessions = []
        for file_path in self.storage_dir.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                sessions.append({
                    'id': data['id'],
                    'title': data['title'],
                    'message_count': len(data.get('messages', [])),
                    'updated_at': data.get('updated_at'),
                    'created_at': data.get('created_at')
                })
            except Exception as e:
                logger.warning(f"Could not load session {file_path}: {e}")
        
        # Sort by updated_at descending
        sessions.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
        return sessions
    
    def delete_session(self, session_id: str):
        """Delete a session."""
        file_path = self.storage_dir / f"{session_id}.json"
        if file_path.exists():
            file_path.unlink()
            logger.info(f"🗑️ Session deleted: {session_id}")
    
    def export_session_markdown(self, session: ChatSession = None) -> str:
        """Export session as markdown."""
        session = session or self.current_session
        if not session:
            return ""
        
        md_lines = [
            f"# {session.title}",
            f"",
            f"**Created:** {session.created_at.strftime('%Y-%m-%d %H:%M')}",
            f"**Messages:** {len(session.messages)}",
            f"",
            "---",
            ""
        ]
        
        for msg in session.messages:
            icon = "🧑" if msg.role == "user" else "🤖"
            md_lines.append(f"## {icon} {msg.role.title()}")
            md_lines.append(f"*{msg.timestamp.strftime('%H:%M:%S')}*")
            md_lines.append("")
            md_lines.append(msg.content)
            md_lines.append("")
            md_lines.append("---")
            md_lines.append("")
        
        return "\n".join(md_lines)


# ============================================================================
# Continue in next part...
# ============================================================================
