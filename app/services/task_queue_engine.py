"""
ENHANCED TASK QUEUE ENGINE
===========================
A powerful autonomous task queue system that:
1. Manages complex multi-step tasks with full planning
2. Displays results inline (images, videos, text)
3. Connects to ALL services (Printify, Shopify, YouTube, Browser/Twitter)
4. Shows real-time progress during execution
5. Supports task chaining and dependencies
6. Persists artifacts to session and filesystem
7. Enables scheduling and recurring tasks
8. Handles batch operations and parallel execution

Integrates with OttoEngine for intelligent task planning and execution.
"""

from abp_imports_common import (
    st, os, json, logging, asyncio, uuid, re, time,
    Path, Dict, List, Any, Optional, Tuple, ThreadPoolExecutor, setup_logger
)

logger = setup_logger(__name__)
import asyncio
import uuid
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import requests
import tempfile
from app.services.platform_integrations import tracked_replicate_run

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    PLANNING = "planning"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class ArtifactType(Enum):
    """Types of artifacts that can be generated."""
    IMAGE = "image"
    VIDEO = "video"
    TEXT = "text"
    FILE = "file"
    PRODUCT = "product"
    BLOG = "blog"
    SOCIAL_POST = "social_post"
    UPLOAD = "upload"


@dataclass
class Artifact:
    """Represents a generated artifact from task execution."""
    id: str
    type: ArtifactType
    name: str
    url: Optional[str] = None
    content: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    file_path: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "name": self.name,
            "url": self.url,
            "content": self.content[:500] if self.content and len(self.content) > 500 else self.content,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "file_path": self.file_path
        }


@dataclass
class TaskStep:
    """Represents a single step in task execution."""
    id: str
    name: str
    description: str
    agent: str  # designer, writer, video, publisher, browser, etc.
    action: str
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Dict] = None
    artifacts: List[Artifact] = field(default_factory=list)
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    depends_on: List[str] = field(default_factory=list)  # Step IDs this depends on
    
    def duration(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


@dataclass
class Task:
    """Represents a complete task in the queue."""
    id: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    
    # Planning
    plan: Optional[Dict] = None
    steps: List[TaskStep] = field(default_factory=list)
    current_step: int = 0
    
    # Execution context
    context: Dict = field(default_factory=dict)
    artifacts: List[Artifact] = field(default_factory=list)
    
    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    scheduled_for: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Dependencies
    depends_on: List[str] = field(default_factory=list)  # Task IDs this depends on
    
    # Results
    final_summary: str = ""
    error: Optional[str] = None
    
    # Publishing targets
    publish_to: List[str] = field(default_factory=list)  # printify, shopify, youtube, twitter, etc.
    
    # Recurrence
    recurring: bool = False
    recurrence_pattern: Optional[str] = None  # daily, weekly, etc.
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority.value,
            "steps": len(self.steps),
            "current_step": self.current_step,
            "artifacts": [a.to_dict() for a in self.artifacts],
            "created_at": self.created_at.isoformat(),
            "scheduled_for": self.scheduled_for.isoformat() if self.scheduled_for else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "publish_to": self.publish_to,
            "recurring": self.recurring
        }
    
    def duration(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    def progress(self) -> float:
        if not self.steps:
            return 0.0
        completed = sum(1 for s in self.steps if s.status == TaskStatus.COMPLETED)
        return completed / len(self.steps)


class EnhancedTaskQueue:
    """
    Advanced task queue with full service integration and real-time display.
    Now with optional Ray distributed execution support.
    """
    
    def __init__(
        self,
        replicate_api=None,
        printify_api=None,
        shopify_api=None,
        youtube_api=None,
        enable_ray=True  # Enable Ray by default
    ):
        self.replicate = replicate_api
        self.printify = printify_api
        self.shopify = shopify_api
        self.youtube = youtube_api
        
        # Browser service (lazy loaded)
        self._browser_service = None
        
        # OttoEngine for planning (lazy loaded)
        self._otto_engine = None
        
        # Ray distributed execution (lazy loaded)
        self._ray_manager = None
        self.enable_ray = enable_ray
        
        # Artifact storage
        self.artifact_dir = Path("task_artifacts")
        self.artifact_dir.mkdir(exist_ok=True)
        
        # Executor for parallel operations
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    @property
    def otto_engine(self):
        """Lazy load Otto Super (enhanced version with better routing)."""
        if self._otto_engine is None:
            try:
                # Try Otto Super first (enhanced version)
                from otto_super_main import OttoSuper
                self._otto_engine = OttoSuper(
                    replicate_api=self.replicate,
                    printify_api=self.printify,
                    shopify_api=self.shopify,
                    youtube_api=self.youtube,
                    task_queue_engine=self,  # Pass self for circular integration
                    multi_platform_poster=None  # Will be lazy-loaded if needed
                )
                logger.info("✅ Task queue using Otto Super (enhanced)")
            except ImportError:
                # Fallback to basic OttoEngine
                try:
                    from otto_engine import OttoEngine
                    self._otto_engine = OttoEngine(
                        replicate_api=self.replicate,
                        printify_api=self.printify,
                        shopify_api=self.shopify,
                        youtube_api=self.youtube
                    )
                    logger.info("✅ Task queue using basic OttoEngine")
                except ImportError:
                    logger.warning("⚠️ OttoEngine not available")
        return self._otto_engine
    
    @property
    def ray_manager(self):
        """Lazy load Ray distributed task manager."""
        if self._ray_manager is None and self.enable_ray:
            try:
                from ray_task_wrapper import get_ray_manager
                self._ray_manager = get_ray_manager(enable_ray=True)
                logger.info("✅ Ray distributed execution enabled")
            except Exception as e:
                logger.warning(f"⚠️ Ray not available: {e}")
                self._ray_manager = None
        return self._ray_manager
    
    async def get_browser_service(self):
        """Get or create browser service."""
        if self._browser_service is None:
            try:
                from automation.enhanced_browser import get_browser_service
                self._browser_service = await get_browser_service()
            except ImportError:
                logger.warning("Browser service not available")
        return self._browser_service
    
    def detect_model_preferences(self, description: str) -> Dict[str, str]:
        """
        Detect which specific AI models the user wants based on their request.
        Returns a dict of model preferences for image, video, and text generation.
        """
        desc_lower = description.lower()
        preferences = {
            "image_model": None,
            "video_model": None,
            "text_model": None,
            "speech_model": None
        }
        
        # VIDEO MODEL DETECTION
        if any(kw in desc_lower for kw in ['sora', 'openai video', 'cinematic video']):
            preferences["video_model"] = "openai/sora-2"
            preferences["video_model_name"] = "Sora-2"
        elif any(kw in desc_lower for kw in ['luma', 'ray flash', 'ray-flash', 'luma ray']):
            if 'flash' in desc_lower:
                preferences["video_model"] = "luma/ray-flash-2"
                preferences["video_model_name"] = "Luma Ray Flash 2"
            else:
                preferences["video_model"] = "luma/ray-2"
                preferences["video_model_name"] = "Luma Ray 2"
        elif any(kw in desc_lower for kw in ['minimax', 'hailuo', 'image-to-video']):
            preferences["video_model"] = "minimax/video-01-live"
            preferences["video_model_name"] = "Minimax Hailuo"
        elif any(kw in desc_lower for kw in ['kling', 'kwaivgi']):
            preferences["video_model"] = "kwaivgi/kling-v2.5-turbo-pro"
            preferences["video_model_name"] = "Kling v2.5"
        elif any(kw in desc_lower for kw in ['ken burns', 'zoom effect', 'pan effect']):
            preferences["video_model"] = "ken_burns"
            preferences["video_model_name"] = "Ken Burns (Free)"
        
        # IMAGE MODEL DETECTION
        if any(kw in desc_lower for kw in ['flux', 'fast image', 'quick image']):
            if 'dev' in desc_lower:
                preferences["image_model"] = "black-forest-labs/flux-dev"
                preferences["image_model_name"] = "Flux Dev"
            elif 'schnell' in desc_lower:
                preferences["image_model"] = "black-forest-labs/flux-schnell"
                preferences["image_model_name"] = "Flux Schnell"
            else:
                preferences["image_model"] = "prunaai/flux-fast"
                preferences["image_model_name"] = "Flux Fast"
        elif any(kw in desc_lower for kw in ['ideogram']):
            preferences["image_model"] = "ideogram-ai/ideogram-v2"
            preferences["image_model_name"] = "Ideogram v2"
        elif any(kw in desc_lower for kw in ['sdxl', 'stable diffusion']):
            preferences["image_model"] = "stability-ai/sdxl"
            preferences["image_model_name"] = "SDXL"
        elif any(kw in desc_lower for kw in ['dall-e', 'dalle']):
            preferences["image_model"] = "openai/dall-e-3"
            preferences["image_model_name"] = "DALL-E 3"
        
        # TEXT MODEL DETECTION
        if any(kw in desc_lower for kw in ['claude', 'anthropic']):
            preferences["text_model"] = "anthropic/claude-4.5-sonnet"
            preferences["text_model_name"] = "Claude 4.5"
        elif any(kw in desc_lower for kw in ['gpt', 'openai', 'chatgpt']):
            preferences["text_model"] = "openai/gpt-4o"
            preferences["text_model_name"] = "GPT-4o"
        elif any(kw in desc_lower for kw in ['llama', 'meta']):
            preferences["text_model"] = "meta/meta-llama-3-70b-instruct"
            preferences["text_model_name"] = "Llama 3 70B"
        
        # Log detected preferences
        detected = [f"{k}: {v}" for k, v in preferences.items() if v]
        if detected:
            logger.info(f"🎯 Model preferences detected: {', '.join(detected)}")
        
        return preferences
    
    def analyze_task(self, description: str) -> Dict[str, Any]:
        """
        Use AI to analyze a task and create a detailed execution plan.
        Now includes model detection for specific AI model routing.
        """
        if not self.replicate:
            return self._fallback_plan(description)
        
        # Detect model preferences first
        model_prefs = self.detect_model_preferences(description)
        
        analysis_prompt = f"""Analyze this task and create a comprehensive execution plan.

TASK: {description}

AVAILABLE SERVICES:
- Printify: Upload designs, create products, publish to shops
- Shopify: Create products, blog posts, manage store
- YouTube: Upload videos with metadata and thumbnails
- Twitter/Social: Post content via browser automation (uses Browser-Use AI)
- Image Generation: Create designs, artwork, thumbnails
- Video Generation: Create promotional videos
- Text Generation: Write descriptions, scripts, blog posts

AVAILABLE AI MODELS:
- Image: Flux Fast (default), Flux Dev, Flux Schnell, Ideogram v2, SDXL, DALL-E 3
- Video: Kling v2.5 (default), Sora-2 (premium), Luma Ray 2, Luma Ray Flash 2, Minimax Hailuo
- Text: Claude 4.5 (default), GPT-4o, Llama 3 70B

AGENTS:
- designer: Creates images, designs, artwork (can use specific image models)
- writer: Writes copy, descriptions, scripts (can use specific text models)
- video: Generates videos from images/prompts (can use specific video models)
- publisher: Uploads to Printify, Shopify, YouTube
- browser: Automates web tasks, social posting via Browser-Use AI
- marketer: Creates marketing content, hashtags

Respond in this JSON format:
{{
    "summary": "Brief 1-sentence summary of the task",
    "goal": "The end goal to achieve",
    "agents_needed": ["list", "of", "agents"],
    "publish_to": ["printify", "shopify", "youtube", "twitter"],
    "model_preferences": {{
        "image_model": "model_name or null",
        "video_model": "model_name or null",
        "text_model": "model_name or null"
    }},
    "steps": [
        {{
            "step": 1,
            "name": "Step name",
            "description": "What this step does",
            "agent": "agent_name",
            "action": "specific_action",
            "model": "specific_model_if_user_requested",
            "depends_on": []
        }}
    ],
    "estimated_time_minutes": 5,
    "requires_confirmation": false
}}"""

        try:
            response = self.replicate.generate_text(
                prompt=analysis_prompt,
                max_tokens=1200,
                temperature=0.3
            )
            
            # Extract JSON
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                plan = json.loads(response[json_start:json_end])
                
                # Merge detected model preferences
                if "model_preferences" not in plan:
                    plan["model_preferences"] = {}
                for key, value in model_prefs.items():
                    if value and not plan["model_preferences"].get(key):
                        plan["model_preferences"][key] = value
                
                return plan
        except Exception as e:
            logger.error(f"Task analysis failed: {e}")
        
        return self._fallback_plan(description)
    
    def _fallback_plan(self, description: str) -> Dict:
        """Create a simple fallback plan when AI analysis fails."""
        desc_lower = description.lower()
        
        # Detect model preferences
        model_prefs = self.detect_model_preferences(description)
        
        steps = []
        agents = ["writer"]
        publish_to = []
        
        # Detect needed agents and steps
        if any(kw in desc_lower for kw in ['design', 'image', 'create', 'art', 'logo', 'graphic']):
            agents.append("designer")
            steps.append({
                "step": len(steps) + 1,
                "name": "Generate Design",
                "description": f"Create design for: {description}",
                "agent": "designer",
                "action": "generate_design",
                "depends_on": []
            })
        
        if any(kw in desc_lower for kw in ['video', 'promo', 'commercial', 'animate']):
            agents.append("video")
            steps.append({
                "step": len(steps) + 1,
                "name": "Create Video",
                "description": f"Generate promotional video",
                "agent": "video",
                "action": "generate_video",
                "depends_on": [s["step"] for s in steps if s["agent"] == "designer"]
            })
        
        if any(kw in desc_lower for kw in ['printify', 't-shirt', 'mug', 'hoodie', 'product']):
            agents.append("publisher")
            publish_to.append("printify")
            steps.append({
                "step": len(steps) + 1,
                "name": "Upload to Printify",
                "description": "Upload design to Printify",
                "agent": "publisher",
                "action": "publish_printify",
                "depends_on": [s["step"] for s in steps if s["agent"] == "designer"]
            })
        
        if any(kw in desc_lower for kw in ['shopify', 'store', 'blog']):
            agents.append("publisher")
            publish_to.append("shopify")
            steps.append({
                "step": len(steps) + 1,
                "name": "Publish to Shopify",
                "description": "Create product or blog on Shopify",
                "agent": "publisher",
                "action": "publish_shopify",
                "depends_on": []
            })
        
        if any(kw in desc_lower for kw in ['youtube', 'upload video']):
            agents.append("publisher")
            publish_to.append("youtube")
            steps.append({
                "step": len(steps) + 1,
                "name": "Upload to YouTube",
                "description": "Upload video to YouTube",
                "agent": "publisher",
                "action": "publish_youtube",
                "depends_on": [s["step"] for s in steps if s["agent"] == "video"]
            })
        
        if any(kw in desc_lower for kw in ['twitter', 'tweet', 'post', 'social']):
            agents.append("browser")
            publish_to.append("twitter")
            steps.append({
                "step": len(steps) + 1,
                "name": "Post to Social Media",
                "description": "Post content to social media",
                "agent": "browser",
                "action": "post_social",
                "depends_on": []
            })
        
        # Always add a content step if we have anything
        if not steps:
            steps.append({
                "step": 1,
                "name": "Generate Content",
                "description": description,
                "agent": "writer",
                "action": "generate_content",
                "depends_on": []
            })
        
        return {
            "summary": description[:100],
            "goal": description,
            "agents_needed": list(set(agents)),
            "publish_to": publish_to,
            "model_preferences": model_prefs,
            "steps": steps,
            "estimated_time_minutes": len(steps) * 2,
            "requires_confirmation": bool(publish_to)
        }
    
    def create_task(self, description: str, priority: TaskPriority = TaskPriority.NORMAL,
                   scheduled_for: Optional[datetime] = None, depends_on: List[str] = None) -> Task:
        """Create a new task with AI-generated plan and model preferences."""
        task_id = str(uuid.uuid4())[:8]
        
        task = Task(
            id=task_id,
            description=description,
            priority=priority,
            scheduled_for=scheduled_for,
            depends_on=depends_on or []
        )
        
        # Analyze and plan
        task.status = TaskStatus.PLANNING
        plan = self.analyze_task(description)
        task.plan = plan
        task.publish_to = plan.get("publish_to", [])
        
        # Store model preferences in context for step execution
        model_prefs = plan.get("model_preferences", {})
        if model_prefs:
            task.context["video_model"] = model_prefs.get("video_model")
            task.context["video_model_name"] = model_prefs.get("video_model_name")
            task.context["image_model"] = model_prefs.get("image_model")
            task.context["image_model_name"] = model_prefs.get("image_model_name")
            task.context["text_model"] = model_prefs.get("text_model")
            task.context["text_model_name"] = model_prefs.get("text_model_name")
            logger.info(f"📋 Task created with model preferences: {model_prefs}")
        
        # Create steps
        for step_data in plan.get("steps", []):
            step = TaskStep(
                id=f"{task_id}-{step_data['step']}",
                name=step_data.get("name", f"Step {step_data['step']}"),
                description=step_data.get("description", ""),
                agent=step_data.get("agent", "writer"),
                action=step_data.get("action", "generate"),
                depends_on=[f"{task_id}-{d}" for d in step_data.get("depends_on", [])]
            )
            task.steps.append(step)
        
        task.status = TaskStatus.READY
        return task
    
    async def execute_task(self, task: Task, progress_callback: Optional[Callable] = None) -> Task:
        """Execute a task with real-time progress updates."""
        logger.info(f"🚀 Starting task execution: {task.id} - {task.description[:50]}...")
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        
        try:
            for i, step in enumerate(task.steps):
                logger.info(f"📍 Step {i+1}/{len(task.steps)}: {step.name}")
                task.current_step = i
                
                # Check dependencies
                for dep_id in step.depends_on:
                    dep_step = next((s for s in task.steps if s.id == dep_id), None)
                    if dep_step and dep_step.status != TaskStatus.COMPLETED:
                        step.error = f"Dependency {dep_id} not completed"
                        step.status = TaskStatus.FAILED
                        continue
                
                # Execute step
                step.status = TaskStatus.RUNNING
                step.started_at = datetime.now()
                
                if progress_callback:
                    progress_callback({
                        "task_id": task.id,
                        "step": i + 1,
                        "total": len(task.steps),
                        "name": step.name,
                        "status": "running",
                        "agent": step.agent
                    })
                
                try:
                    result = await self._execute_step(step, task.context)
                    step.result = result
                    step.status = TaskStatus.COMPLETED
                    step.completed_at = datetime.now()
                    
                    # Collect artifacts
                    if result.get("artifacts"):
                        for art_data in result["artifacts"]:
                            artifact = Artifact(
                                id=str(uuid.uuid4())[:8],
                                type=ArtifactType(art_data.get("type", "text")),
                                name=art_data.get("name", step.name),
                                url=art_data.get("url"),
                                content=art_data.get("content"),
                                metadata=art_data.get("metadata", {})
                            )
                            step.artifacts.append(artifact)
                            task.artifacts.append(artifact)
                            
                            # Save artifact to disk
                            self._save_artifact(artifact, task.id)
                    
                    # Update context for next steps
                    if result.get("context_updates"):
                        task.context.update(result["context_updates"])
                    
                    if progress_callback:
                        progress_callback({
                            "task_id": task.id,
                            "step": i + 1,
                            "total": len(task.steps),
                            "name": step.name,
                            "status": "completed",
                            "result": result,
                            "artifacts": [a.to_dict() for a in step.artifacts]
                        })
                    
                except Exception as e:
                    step.error = str(e)
                    step.status = TaskStatus.FAILED
                    step.completed_at = datetime.now()
                    logger.error(f"Step {step.name} failed: {e}")
                    
                    if progress_callback:
                        progress_callback({
                            "task_id": task.id,
                            "step": i + 1,
                            "total": len(task.steps),
                            "name": step.name,
                            "status": "failed",
                            "error": str(e)
                        })
            
            # Generate final summary
            task.final_summary = self._generate_task_summary(task)
            
            # Determine final status
            failed_steps = [s for s in task.steps if s.status == TaskStatus.FAILED]
            if failed_steps:
                if len(failed_steps) == len(task.steps):
                    task.status = TaskStatus.FAILED
                else:
                    task.status = TaskStatus.COMPLETED  # Partial success
            else:
                task.status = TaskStatus.COMPLETED
            
            task.completed_at = datetime.now()
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now()
            logger.error(f"Task {task.id} failed: {e}")
        
        return task
    
    async def _execute_step(self, step: TaskStep, context: Dict) -> Dict[str, Any]:
        """Execute a single step based on agent type."""
        agent = step.agent
        action = step.action
        
        logger.info(f"🔄 Executing step: {step.name} (agent: {agent}, action: {action})")
        
        if agent == "designer":
            return await self._execute_design(step, context)
        elif agent == "writer":
            return await self._execute_writing(step, context)
        elif agent == "video":
            return await self._execute_video(step, context)
        elif agent == "publisher":
            return await self._execute_publish(step, context)
        elif agent == "browser":
            return await self._execute_browser(step, context)
        elif agent == "marketer":
            return await self._execute_marketing(step, context)
        else:
            return await self._execute_generic(step, context)
    
    async def _execute_design(self, step: TaskStep, context: Dict) -> Dict[str, Any]:
        """Generate design/image - with optional Ray distribution."""
        if not self.replicate:
            logger.error("❌ Replicate API not configured for design")
            raise Exception("Replicate API not configured. Please set REPLICATE_API_TOKEN.")
        
        # Use Ray if available for heavy design tasks
        if self.ray_manager and step.action in ["batch_designs", "generate_design"]:
            try:
                return await self.ray_manager.execute_task_distributed(
                    task_func=self._execute_design_impl,
                    task_args=(step, context),
                    task_type="design",
                    timeout=300  # 5 minute timeout
                )
            except Exception as e:
                logger.warning(f"⚠️ Ray execution failed, using local: {e}")
        
        # Local execution (fallback or default)
        return await self._execute_design_impl(step, context)
    
    async def _execute_design_impl(self, step: TaskStep, context: Dict) -> Dict[str, Any]:
        """Implementation of design generation."""
        prompt = step.description
        
        # Enhance prompt based on action
        if step.action == "generate_design":
            prompt = f"Professional product design: {prompt}. High quality, commercial ready, clean background, centered composition, 8k quality."
        elif step.action == "thumbnail":
            prompt = f"YouTube thumbnail: {prompt}. Bold, eye-catching, vibrant colors, clear text space."
        elif step.action == "social_image":
            prompt = f"Social media image: {prompt}. Square format, modern, engaging, scroll-stopping."
        
        # Get image model preference from context
        image_model = context.get("image_model")
        image_model_name = context.get("image_model_name", "Flux Fast")
        
        try:
            # Use specific image model if requested
            if image_model:
                logger.info(f"🎨 Using {image_model_name} ({image_model})")
                import replicate
                output = replicate.run(
                    image_model,
                    input={
                        "prompt": prompt,
                        "width": 1024,
                        "height": 1024
                    }
                )
                # Extract URL from output
                if isinstance(output, list) and len(output) > 0:
                    image_url = str(output[0])
                elif isinstance(output, str):
                    image_url = output
                else:
                    image_url = str(output)
            else:
                # Use default via ReplicateAPI
                image_url = self.replicate.generate_image(
                    prompt=prompt,
                    width=1024,
                    height=1024,
                    aspect_ratio="1:1"
                )
            
            return {
                "type": "image",
                "url": image_url,
                "prompt": prompt,
                "model": image_model_name,
                "artifacts": [{
                    "type": "image",
                    "name": step.name,
                    "url": image_url,
                    "metadata": {"prompt": prompt, "model": image_model_name}
                }],
                "context_updates": {"generated_image": image_url, "design_prompt": prompt}
            }
        except Exception as e:
            raise Exception(f"Design generation failed: {e}")
    
    async def _execute_writing(self, step: TaskStep, context: Dict) -> Dict[str, Any]:
        """Generate text content."""
        if not self.replicate:
            logger.error("❌ Replicate API not configured for writing")
            raise Exception("Replicate API not configured. Please set REPLICATE_API_TOKEN.")
        
        prompts = {
            "product_description": f"Write a compelling product description (2-3 paragraphs) for: {step.description}. Focus on benefits, features, and emotional appeal.",
            "video_script": f"Write a 30-second video script for: {step.description}. Include [VISUAL] cues and [VOICEOVER] text.",
            "blog_post": f"Write a comprehensive blog post about: {step.description}. Include intro, main points, and conclusion.",
            "social_post": f"Write engaging social media posts for: {step.description}. Create versions for Twitter, Instagram, and Facebook.",
            "marketing_copy": f"Write marketing copy for: {step.description}. Include headline, subheadline, and key benefits.",
            "generate_content": f"Generate helpful content for: {step.description}"
        }
        
        prompt = prompts.get(step.action, prompts["generate_content"])
        
        # Add context if available
        if context.get("generated_image"):
            prompt += f"\n\nNote: An image has been generated for this. Reference it in your content."
        
        try:
            content = self.replicate.generate_text(
                prompt=prompt,
                max_tokens=1000,
                temperature=0.7
            )
            
            return {
                "type": "text",
                "content": content,
                "artifacts": [{
                    "type": "text",
                    "name": step.name,
                    "content": content,
                    "metadata": {"action": step.action}
                }],
                "context_updates": {step.action: content, "latest_content": content}
            }
        except Exception as e:
            raise Exception(f"Writing failed: {e}")
    
    async def _execute_video(self, step: TaskStep, context: Dict) -> Dict[str, Any]:
        """Generate video with support for multiple video models - with optional Ray distribution."""
        if not self.replicate:
            return {"error": "Replicate API not configured", "artifacts": []}
        
        # Use Ray if available for heavy video tasks
        if self.ray_manager and step.action in ["generate_video", "batch_videos"]:
            try:
                return await self.ray_manager.execute_task_distributed(
                    task_func=self._execute_video_impl,
                    task_args=(step, context),
                    task_type="video",
                    timeout=600  # 10 minute timeout for video
                )
            except Exception as e:
                logger.warning(f"⚠️ Ray execution failed, using local: {e}")
        
        # Local execution (fallback or default)
        return await self._execute_video_impl(step, context)
    
    async def _execute_video_impl(self, step: TaskStep, context: Dict) -> Dict[str, Any]:
        """Implementation of video generation."""
        image_url = context.get("generated_image")
        
        # Get model preference from context or step
        video_model = context.get("video_model") or getattr(step, 'model', None)
        video_model_name = context.get("video_model_name", "Kling v2.5")
        
        try:
            video_prompt = f"Gentle motion, professional showcase: {step.description}"
            
            # Handle different video models
            if video_model == "ken_burns":
                # Ken Burns effect - free, instant
                logger.info("🎬 Using Ken Burns effect (free, instant)")
                from modules.video_generation import generate_ken_burns_video
                
                if not image_url:
                    raise Exception("Ken Burns requires an image")
                
                # Download image
                response = requests.get(image_url, timeout=30)
                if response.status_code != 200:
                    raise Exception("Failed to download image for Ken Burns")
                
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    tmp.write(response.content)
                    image_path = tmp.name
                
                video_output = image_path.replace(".png", "_kenburns.mp4")
                generate_ken_burns_video(image_path, video_output, duration=5)
                video_url = video_output  # Local path
                
            elif video_model and "sora" in video_model.lower():
                # OpenAI Sora-2
                logger.info("🎬 Using Sora-2 (premium cinematic)")
                import replicate
                api_token = os.getenv("REPLICATE_API_TOKEN", "")

                replicate_client = replicate.Client(api_token=api_token) if hasattr(replicate, "Client") else None

                if replicate_client:

                    output = tracked_replicate_run(

                        replicate_client,

                        "openai/sora-2",

                        {
                        "prompt": video_prompt,
                        "aspect_ratio": "landscape",
                        "duration": 5
                    },

                        operation_name="API Call"

                    )

                else:

                    output = replicate.run("openai/sora-2", input={
                        "prompt": video_prompt,
                        "aspect_ratio": "landscape",
                        "duration": 5
                    })
                video_url = str(output) if output else None
                
            elif video_model and "luma" in video_model.lower():
                # Luma Ray models
                model_id = "luma/ray-flash-2" if "flash" in video_model.lower() else "luma/ray-2"
                logger.info(f"🎬 Using {model_id}")
                import replicate
                input_data = {"prompt": video_prompt}
                if image_url:
                    input_data["image"] = image_url
                output = replicate.run(model_id, input=input_data)
                video_url = str(output) if output else None
                
            elif video_model and "minimax" in video_model.lower():
                # Minimax Hailuo
                logger.info("🎬 Using Minimax Hailuo (image-to-video)")
                import replicate
                if not image_url:
                    raise Exception("Minimax requires an image input")
                api_token = os.getenv("REPLICATE_API_TOKEN", "")

                replicate_client = replicate.Client(api_token=api_token) if hasattr(replicate, "Client") else None

                if replicate_client:

                    output = tracked_replicate_run(

                        replicate_client,

                        "minimax/video-01-live",

                        {
                        "prompt": video_prompt,
                        "first_frame_image": image_url
                    },

                        operation_name="API Call"

                    )

                else:

                    output = replicate.run("minimax/video-01-live", input={
                        "prompt": video_prompt,
                        "first_frame_image": image_url
                    })
                video_url = str(output) if output else None
                
            else:
                # Default: Kling v2.5
                logger.info("🎬 Using Kling v2.5 (default)")
                video_url = self.replicate.generate_video(
                    prompt=video_prompt,
                    image_url=image_url,
                    aspect_ratio="16:9",
                    motion_level=3
                )
            
            return {
                "type": "video",
                "url": video_url,
                "model": video_model_name,
                "artifacts": [{
                    "type": "video",
                    "name": step.name,
                    "url": video_url,
                    "metadata": {"source_image": image_url, "model": video_model_name}
                }],
                "context_updates": {"generated_video": video_url}
            }
        except Exception as e:
            raise Exception(f"Video generation failed: {e}")
    
    async def _execute_publish(self, step: TaskStep, context: Dict) -> Dict[str, Any]:
        """Publish to services (Printify, Shopify, YouTube)."""
        action = step.action
        
        if action == "publish_printify" or "printify" in step.description.lower():
            return await self._publish_to_printify(step, context)
        elif action == "publish_shopify" or "shopify" in step.description.lower():
            return await self._publish_to_shopify(step, context)
        elif action == "publish_youtube" or "youtube" in step.description.lower():
            return await self._publish_to_youtube(step, context)
        else:
            return {"message": "Unknown publish action", "artifacts": []}
    
    async def _publish_to_printify(self, step: TaskStep, context: Dict) -> Dict[str, Any]:
        """Upload image to Printify."""
        if not self.printify:
            return {"error": "Printify API not configured", "artifacts": []}
        
        image_url = context.get("generated_image")
        if not image_url:
            return {"error": "No image to upload", "artifacts": []}
        
        try:
            # Download the image
            response = requests.get(image_url, timeout=30)
            if response.status_code != 200:
                raise Exception(f"Failed to download image: {response.status_code}")
            
            # Upload to Printify
            file_name = f"design_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            result = self.printify.upload_image(response.content, file_name)
            
            image_id = result.get("id") if isinstance(result, dict) else str(result)
            
            return {
                "type": "upload",
                "service": "printify",
                "image_id": image_id,
                "message": f"✅ Uploaded to Printify! Image ID: {image_id}",
                "artifacts": [{
                    "type": "upload",
                    "name": "Printify Upload",
                    "metadata": {"service": "printify", "image_id": image_id}
                }],
                "context_updates": {"printify_image_id": image_id}
            }
        except Exception as e:
            raise Exception(f"Printify upload failed: {e}")
    
    async def _publish_to_shopify(self, step: TaskStep, context: Dict) -> Dict[str, Any]:
        """Create product or blog post on Shopify."""
        if not self.shopify:
            return {"error": "Shopify API not configured", "artifacts": []}
        
        try:
            # Determine if blog or product
            is_blog = "blog" in step.description.lower()
            
            if is_blog:
                title = context.get("blog_title", f"Blog Post - {datetime.now().strftime('%Y-%m-%d')}")
                content = context.get("blog_post") or context.get("latest_content", step.description)
                image_url = context.get("generated_image")
                
                # Add image to content if available
                body_html = f"<p>{content}</p>"
                if image_url:
                    body_html = f'<img src="{image_url}" alt="{title}" style="max-width:100%;" />\n{body_html}'
                
                result = self.shopify.create_blog_post(
                    title=title,
                    body_html=body_html,
                    author="Otto AI",
                    tags=["ai-generated", "otto"],
                    published=True
                )
                
                return {
                    "type": "blog",
                    "service": "shopify",
                    "article_id": result.get("id"),
                    "url": result.get("url"),
                    "message": f"✅ Published blog post to Shopify!",
                    "artifacts": [{
                        "type": "blog",
                        "name": "Shopify Blog Post",
                        "url": result.get("url"),
                        "metadata": {"service": "shopify", "article_id": result.get("id")}
                    }],
                    "context_updates": {"shopify_article_id": result.get("id")}
                }
            else:
                # Create product
                title = context.get("product_title", step.description[:50])
                description = context.get("product_description") or context.get("latest_content", "")
                image_url = context.get("generated_image")
                
                result = self.shopify.create_product(
                    title=title,
                    body_html=f"<p>{description}</p>",
                    product_type="AI Generated",
                    tags=["ai-generated", "otto"],
                    images=[{"src": image_url}] if image_url else []
                )
                
                return {
                    "type": "product",
                    "service": "shopify",
                    "product_id": result.get("id"),
                    "message": f"✅ Created product on Shopify!",
                    "artifacts": [{
                        "type": "product",
                        "name": "Shopify Product",
                        "metadata": {"service": "shopify", "product_id": result.get("id")}
                    }],
                    "context_updates": {"shopify_product_id": result.get("id")}
                }
        except Exception as e:
            raise Exception(f"Shopify publish failed: {e}")
    
    async def _publish_to_youtube(self, step: TaskStep, context: Dict) -> Dict[str, Any]:
        """Upload video to YouTube."""
        if not self.youtube:
            return {"error": "YouTube API not configured", "artifacts": []}
        
        video_url = context.get("generated_video")
        if not video_url:
            return {"error": "No video to upload", "artifacts": []}
        
        try:
            # Download video to temp file
            response = requests.get(video_url, timeout=120)
            if response.status_code != 200:
                raise Exception(f"Failed to download video: {response.status_code}")
            
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
                tmp.write(response.content)
                video_path = tmp.name
            
            # Get metadata
            title = context.get("video_title", f"AI Generated Video - {datetime.now().strftime('%Y-%m-%d')}")
            description = context.get("video_script") or context.get("latest_content", step.description)
            thumbnail_url = context.get("generated_image")
            
            # Download thumbnail if available
            thumbnail_path = None
            if thumbnail_url:
                thumb_response = requests.get(thumbnail_url, timeout=30)
                if thumb_response.status_code == 200:
                    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as thumb_tmp:
                        thumb_tmp.write(thumb_response.content)
                        thumbnail_path = thumb_tmp.name
            
            # Upload to YouTube
            result = self.youtube.upload_commercial(
                video_path=video_path,
                product_name=title,
                metadata={
                    "title": title,
                    "description": description,
                    "tags": ["AI", "generated", "otto"],
                    "category": "22"  # People & Blogs
                },
                thumbnail_path=thumbnail_path
            )
            
            # Clean up temp files
            os.unlink(video_path)
            if thumbnail_path:
                os.unlink(thumbnail_path)
            
            video_id = result.get("id")
            video_link = f"https://youtube.com/watch?v={video_id}" if video_id else None
            
            return {
                "type": "video",
                "service": "youtube",
                "video_id": video_id,
                "url": video_link,
                "message": f"✅ Uploaded to YouTube! {video_link}",
                "artifacts": [{
                    "type": "video",
                    "name": "YouTube Video",
                    "url": video_link,
                    "metadata": {"service": "youtube", "video_id": video_id}
                }],
                "context_updates": {"youtube_video_id": video_id, "youtube_url": video_link}
            }
        except Exception as e:
            raise Exception(f"YouTube upload failed: {e}")
    
    async def _execute_browser(self, step: TaskStep, context: Dict) -> Dict[str, Any]:
        """Execute browser automation (social posting, etc.) using Browser-Use AI."""
        
        # First try the AI Twitter poster which works well
        try:
            if step.action == "post_social" or "twitter" in step.description.lower():
                # Get content to post
                content = context.get("social_post") or context.get("latest_content", step.description)
                image_url = context.get("generated_image")
                image_path = None
                
                # Download image if we have a URL
                if image_url:
                    response = requests.get(image_url, timeout=30)
                    if response.status_code == 200:
                        import tempfile
                        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                            tmp.write(response.content)
                            image_path = tmp.name
                
                # Use the AI Twitter poster
                try:
                    from ai_twitter_poster import AITwitterPoster
                    poster = AITwitterPoster()
                    
                    if not image_path:
                        logger.warning("No image for Twitter post, skipping image upload")
                    
                    logger.info("🐦 Using AI Twitter Poster (Browser-Use)")
                    success = await poster.post_to_twitter(
                        image_path=image_path or "",
                        caption=content[:280]  # Twitter limit
                    )
                    
                    return {
                        "type": "social_post",
                        "platform": "twitter",
                        "success": success,
                        "message": "✅ Posted to Twitter!" if success else "⚠️ Twitter post may have failed",
                        "artifacts": [{
                            "type": "social_post",
                            "name": "Twitter Post",
                            "content": content[:280],
                            "metadata": {"platform": "twitter", "success": success}
                        }],
                        "context_updates": {"twitter_posted": success}
                    }
                except ImportError:
                    logger.warning("AI Twitter Poster not available, trying enhanced browser")
                except Exception as e:
                    logger.warning(f"AI Twitter Poster failed: {e}")
                
                # Fallback to enhanced browser service
                browser = await self.get_browser_service()
                if browser:
                    result = await browser.post_to_twitter(
                        text=content[:280],
                        image_url=image_url
                    )
                    return {
                        "type": "social_post",
                        "platform": "twitter",
                        "success": result.get("success", False),
                        "message": "✅ Posted to Twitter!" if result.get("success") else "❌ Twitter post failed",
                        "artifacts": [{
                            "type": "social_post",
                            "name": "Twitter Post",
                            "content": content[:280],
                            "metadata": {"platform": "twitter", "success": result.get("success")}
                        }],
                        "context_updates": {"twitter_posted": result.get("success", False)}
                    }
                else:
                    return {"error": "No browser automation available for Twitter posting", "artifacts": []}
            
            else:
                # Generic browser task using Browser-Use
                browser = await self.get_browser_service()
                if not browser:
                    # Try using Browser-Use directly with Anthropic
                    try:
                        from browser_use import Agent
                        from langchain_anthropic import ChatAnthropic
                        from pydantic import SecretStr
                        
                        api_key = os.getenv('ANTHROPIC_API_KEY')
                        if not api_key:
                            return {"error": "ANTHROPIC_API_KEY not set for browser automation", "artifacts": []}
                        
                        logger.info("🌐 Using Browser-Use for web automation")
                        llm = ChatAnthropic(
                            model_name="claude-sonnet-4-20250514",
                            api_key=SecretStr(api_key),
                            temperature=0,
                            timeout=100,
                            stop=None
                        )
                        
                        agent = Agent(
                            task=step.description,
                            llm=llm
                        )
                        history = await agent.run()
                        result_text = str(history.final_result()) if hasattr(history, 'final_result') else "Task completed"
                        
                        return {
                            "type": "browser",
                            "success": True,
                            "message": result_text or "Browser task completed",
                            "artifacts": [{
                                "type": "text",
                                "name": "Browser Result",
                                "content": result_text
                            }],
                            "context_updates": {"browser_result": result_text}
                        }
                    except Exception as e:
                        logger.error(f"Browser-Use failed: {e}")
                        return {"error": f"Browser automation failed: {e}", "artifacts": []}
                
                result = await browser.execute(
                    task=step.description,
                    max_steps=20
                )
                
                return {
                    "type": "browser",
                    "success": result.get("success", False),
                    "message": result.get("result", "Browser task completed"),
                    "artifacts": [],
                    "context_updates": {}
                }
        except Exception as e:
            raise Exception(f"Browser automation failed: {e}")
    
    async def _execute_marketing(self, step: TaskStep, context: Dict) -> Dict[str, Any]:
        """Generate marketing content."""
        if not self.replicate:
            return {"error": "Replicate API not configured", "artifacts": []}
        
        prompt = f"""Create comprehensive marketing content for: {step.description}

Include:
1. Three social media posts (Twitter, Instagram, Facebook)
2. 15 relevant hashtags
3. A catchy tagline
4. Email subject line

Make it engaging and shareable."""
        
        try:
            content = self.replicate.generate_text(
                prompt=prompt,
                max_tokens=800,
                temperature=0.8
            )
            
            return {
                "type": "text",
                "content": content,
                "artifacts": [{
                    "type": "text",
                    "name": "Marketing Content",
                    "content": content,
                    "metadata": {"action": "marketing"}
                }],
                "context_updates": {"marketing_content": content, "social_posts": content}
            }
        except Exception as e:
            raise Exception(f"Marketing content failed: {e}")
    
    async def _execute_generic(self, step: TaskStep, context: Dict) -> Dict[str, Any]:
        """Fallback for unknown agent types."""
        return {
            "type": "status",
            "message": f"Completed: {step.description}",
            "artifacts": [],
            "context_updates": {}
        }
    
    def _save_artifact(self, artifact: Artifact, task_id: str):
        """Save artifact to filesystem for persistence."""
        task_dir = self.artifact_dir / task_id
        task_dir.mkdir(exist_ok=True)
        
        try:
            if artifact.url and artifact.type in [ArtifactType.IMAGE, ArtifactType.VIDEO]:
                # Download and save media
                response = requests.get(artifact.url, timeout=60)
                if response.status_code == 200:
                    ext = "mp4" if artifact.type == ArtifactType.VIDEO else "png"
                    file_path = task_dir / f"{artifact.id}.{ext}"
                    with open(file_path, "wb") as f:
                        f.write(response.content)
                    artifact.file_path = str(file_path)
            
            elif artifact.content and artifact.type == ArtifactType.TEXT:
                # Save text content
                file_path = task_dir / f"{artifact.id}.txt"
                with open(file_path, "w") as f:
                    f.write(artifact.content)
                artifact.file_path = str(file_path)
            
            # Save artifact metadata
            meta_path = task_dir / f"{artifact.id}.json"
            with open(meta_path, "w") as f:
                json.dump(artifact.to_dict(), f, indent=2)
                
        except Exception as e:
            logger.warning(f"Failed to save artifact {artifact.id}: {e}")
    
    def _generate_task_summary(self, task: Task) -> str:
        """Generate a human-readable summary of task execution."""
        completed = sum(1 for s in task.steps if s.status == TaskStatus.COMPLETED)
        failed = sum(1 for s in task.steps if s.status == TaskStatus.FAILED)
        
        lines = [
            f"## 🎯 Task Complete",
            f"",
            f"**Request:** {task.description[:100]}...",
            f"**Status:** {'✅ Success' if task.status == TaskStatus.COMPLETED else '⚠️ Partial' if completed > 0 else '❌ Failed'}",
            f"**Steps:** {completed}/{len(task.steps)} completed",
            f""
        ]
        
        if task.artifacts:
            lines.append("### 📦 Generated Assets")
            for artifact in task.artifacts:
                if artifact.type == ArtifactType.IMAGE:
                    lines.append(f"- 🖼️ **Image:** {artifact.name}")
                elif artifact.type == ArtifactType.VIDEO:
                    lines.append(f"- 🎬 **Video:** {artifact.name}")
                elif artifact.type == ArtifactType.TEXT:
                    lines.append(f"- 📝 **Content:** {artifact.name}")
                elif artifact.type == ArtifactType.UPLOAD:
                    lines.append(f"- ☁️ **Upload:** {artifact.name} ({artifact.metadata.get('service', 'unknown')})")
                elif artifact.type == ArtifactType.PRODUCT:
                    lines.append(f"- 🛍️ **Product:** {artifact.name}")
                elif artifact.type == ArtifactType.BLOG:
                    lines.append(f"- 📰 **Blog:** {artifact.name}")
                elif artifact.type == ArtifactType.SOCIAL_POST:
                    lines.append(f"- 📢 **Social:** {artifact.name}")
        
        if failed > 0:
            lines.append("")
            lines.append("### ⚠️ Issues")
            for step in task.steps:
                if step.status == TaskStatus.FAILED:
                    lines.append(f"- {step.name}: {step.error}")
        
        if task.duration():
            lines.append("")
            lines.append(f"⏱️ *Completed in {task.duration():.1f} seconds*")
        
        return "\n".join(lines)


def render_enhanced_task_queue(replicate_api=None, printify_api=None, shopify_api=None, youtube_api=None):
    """
    Render the enhanced task queue UI with full functionality.
    """
    
    # Custom CSS
    st.markdown("""
    <style>
    .task-card {
        background: white;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 15px;
        margin: 10px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .task-card-running {
        border-left: 4px solid #ffc107;
        background: #fffbeb;
    }
    .task-card-completed {
        border-left: 4px solid #28a745;
        background: #f0fff4;
    }
    .task-card-failed {
        border-left: 4px solid #dc3545;
        background: #fff5f5;
    }
    .artifact-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: 15px;
        margin-top: 15px;
    }
    .artifact-item {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 10px;
        text-align: center;
    }
    .service-badge {
        display: inline-block;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 12px;
        margin: 2px;
    }
    .badge-printify { background: #00a86b; color: white; }
    .badge-shopify { background: #96bf48; color: white; }
    .badge-youtube { background: #ff0000; color: white; }
    .badge-twitter { background: #1da1f2; color: white; }
    .priority-urgent { color: #dc3545; font-weight: bold; }
    .priority-high { color: #fd7e14; }
    .priority-normal { color: #6c757d; }
    .priority-low { color: #adb5bd; }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("## 🤖 Autonomous Task Queue")
    st.markdown("Add tasks and let AI execute them automatically with full service integration.")
    
    # Initialize session state
    if 'enhanced_task_queue' not in st.session_state:
        st.session_state.enhanced_task_queue = []
    if 'queue_running' not in st.session_state:
        st.session_state.queue_running = False
    if 'current_task_index' not in st.session_state:
        st.session_state.current_task_index = 0
    
    # Ensure we have a ReplicateAPI instance
    if replicate_api is None:
        # Try to create one from environment or session
        replicate_token = os.getenv('REPLICATE_API_TOKEN') or st.session_state.get('replicate_api_key', '')
        if replicate_token:
            try:
                from api_service import ReplicateAPI
                replicate_api = ReplicateAPI(api_token=replicate_token)
                logger.info("✅ Created ReplicateAPI from token")
            except Exception as e:
                logger.warning(f"Failed to create ReplicateAPI: {e}")
    
    # Initialize queue manager
    queue = EnhancedTaskQueue(
        replicate_api=replicate_api,
        printify_api=printify_api,
        shopify_api=shopify_api,
        youtube_api=youtube_api
    )
    
    # Service status indicators
    st.markdown("### 🔌 Connected Services")
    svc_cols = st.columns(5)
    with svc_cols[0]:
        st.markdown(f"{'✅' if replicate_api else '❌'} **Replicate**")
    with svc_cols[1]:
        st.markdown(f"{'✅' if printify_api else '❌'} **Printify**")
    with svc_cols[2]:
        st.markdown(f"{'✅' if shopify_api else '❌'} **Shopify**")
    with svc_cols[3]:
        st.markdown(f"{'✅' if youtube_api else '❌'} **YouTube**")
    with svc_cols[4]:
        st.markdown(f"{'✅' if os.getenv('ANTHROPIC_API_KEY') else '❌'} **Browser**")
    
    st.markdown("---")
    
    # Layout: Input and Queue
    input_col, queue_col = st.columns([1, 1.2])
    
    with input_col:
        st.markdown("### ➕ Add New Task")
        
        # Get default value from template selection
        default_task = st.session_state.get('selected_template', '')
        
        new_task = st.text_area(
            "Describe what you want to accomplish:",
            value=default_task,
            height=120,
            placeholder="e.g., Create a coffee mug design, upload to Printify, generate a promo video, and post to Twitter",
            key="new_task_input"
        ) or ""
        
        # Clear template after use
        if 'selected_template' in st.session_state:
            del st.session_state['selected_template']
        
        # Advanced options
        with st.expander("⚙️ Advanced Options"):
            priority = st.selectbox("Priority", ["Normal", "Low", "High", "Urgent"], index=0)
            schedule = st.checkbox("Schedule for later")
            if schedule:
                schedule_date = st.date_input("Date")
                schedule_time = st.time_input("Time")
            
            # Publishing targets
            st.markdown("**Publish To:**")
            pub_cols = st.columns(4)
            with pub_cols[0]:
                pub_printify = st.checkbox("Printify", value=False)
            with pub_cols[1]:
                pub_shopify = st.checkbox("Shopify", value=False)
            with pub_cols[2]:
                pub_youtube = st.checkbox("YouTube", value=False)
            with pub_cols[3]:
                pub_twitter = st.checkbox("Twitter", value=False)
        
        btn_cols = st.columns(2)
        
        with btn_cols[0]:
            if st.button("➕ Add Task", use_container_width=True, type="primary"):
                if new_task.strip():
                    with st.spinner("🧠 AI analyzing task..."):
                        task = queue.create_task(
                            description=new_task.strip(),
                            priority=TaskPriority[priority.upper()]
                        )
                    
                    st.session_state.enhanced_task_queue.append(task)
                    st.success(f"✅ Added! {len(task.steps)} steps planned")
                    st.rerun()
        
        with btn_cols[1]:
            if st.button("🔍 Preview Plan", use_container_width=True):
                if new_task.strip():
                    with st.spinner("Analyzing..."):
                        plan = queue.analyze_task(new_task.strip())
                    st.json(plan)
        
        # Quick templates
        st.markdown("---")
        st.markdown("### ⚡ Quick Templates")
        
        templates = {
            "🎨 Full Product Campaign": "Create a unique t-shirt design, write product description, generate promo video, upload to Printify, post to Twitter",
            "📝 Blog + Social": "Write a blog post about [topic], create header image, publish to Shopify, create social posts",
            "🎬 Video Marketing": "Generate product video, create thumbnail, write description, upload to YouTube",
            "📢 Social Blitz": "Create promotional image, write posts for Twitter, Instagram, Facebook, and schedule them",
        }
        
        for label, template in templates.items():
            if st.button(label, key=f"tpl_{label}", use_container_width=True):
                st.session_state['selected_template'] = template
                st.rerun()
    
    with queue_col:
        st.markdown("### 📋 Task Queue")
        
        # Queue controls
        ctrl_cols = st.columns(4)
        
        with ctrl_cols[0]:
            if st.session_state.queue_running:
                if st.button("⏸️ Pause", use_container_width=True):
                    st.session_state.queue_running = False
                    st.rerun()
            else:
                if st.button("▶️ Start", use_container_width=True, type="primary"):
                    if st.session_state.enhanced_task_queue:
                        st.session_state.queue_running = True
                        st.rerun()
        
        with ctrl_cols[1]:
            if st.button("⏭️ Skip", use_container_width=True):
                st.session_state.current_task_index += 1
                st.rerun()
        
        with ctrl_cols[2]:
            if st.button("🔄 Retry Failed", use_container_width=True):
                for task in st.session_state.enhanced_task_queue:
                    if task.status == TaskStatus.FAILED:
                        task.status = TaskStatus.READY
                        task.error = None
                st.rerun()
        
        with ctrl_cols[3]:
            if st.button("🗑️ Clear", use_container_width=True):
                st.session_state.enhanced_task_queue = []
                st.session_state.current_task_index = 0
                st.session_state.queue_running = False
                st.rerun()
        
        st.markdown("---")
        
        # Display tasks
        if not st.session_state.enhanced_task_queue:
            st.info("📭 Queue is empty. Add tasks to get started!")
        else:
            for i, task in enumerate(st.session_state.enhanced_task_queue):
                # Status styling
                status_class = ""
                status_icon = "⚪"
                is_expanded = False
                if task.status == TaskStatus.COMPLETED:
                    status_class = "task-card-completed"
                    status_icon = "✅"
                    is_expanded = True  # Show completed tasks expanded so users see results
                elif task.status == TaskStatus.RUNNING:
                    status_class = "task-card-running"
                    status_icon = "⏳"
                    is_expanded = True
                elif task.status == TaskStatus.FAILED:
                    status_class = "task-card-failed"
                    status_icon = "❌"
                    is_expanded = True  # Show failed tasks expanded so users see errors
                elif task.status == TaskStatus.READY:
                    status_icon = "🔵"
                
                # Build status text
                status_text = task.status.value.upper()
                if task.status == TaskStatus.COMPLETED and task.duration():
                    status_text = f"COMPLETED in {task.duration():.1f}s"
                
                with st.expander(f"{status_icon} Task {i+1}: {task.description[:40]}... [{status_text}]", 
                               expanded=is_expanded):
                    
                    # Task header
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**{task.description}**")
                    with col2:
                        priority_class = f"priority-{task.priority.name.lower()}"
                        st.markdown(f"<span class='{priority_class}'>{task.priority.name}</span>", 
                                  unsafe_allow_html=True)
                    
                    # Progress bar
                    if task.steps:
                        st.progress(task.progress())
                        st.caption(f"Step {task.current_step + 1}/{len(task.steps)}")
                    
                    # Publishing targets
                    if task.publish_to:
                        badges = ""
                        for svc in task.publish_to:
                            badges += f"<span class='service-badge badge-{svc}'>{svc.title()}</span>"
                        st.markdown(f"**Publish to:** {badges}", unsafe_allow_html=True)
                    
                    # Steps with results
                    if task.plan and task.steps:
                        st.markdown("**Steps:**")
                        for step in task.steps:
                            step_icon = "⚪"
                            step_info = ""
                            if step.status == TaskStatus.COMPLETED:
                                step_icon = "✅"
                                # Show what was produced
                                if step.artifacts:
                                    artifact_types = [a.type.value for a in step.artifacts]
                                    step_info = f" → {', '.join(artifact_types)}"
                                if step.duration():
                                    step_info += f" ({step.duration():.1f}s)"
                            elif step.status == TaskStatus.RUNNING:
                                step_icon = "⏳"
                            elif step.status == TaskStatus.FAILED:
                                step_icon = "❌"
                                if step.error:
                                    step_info = f" - {step.error[:50]}"
                            st.markdown(f"{step_icon} {step.name}{step_info}")
                    
                    # DISPLAY ARTIFACTS - THE KEY FIX
                    if task.artifacts:
                        st.markdown("---")
                        st.markdown("### 📦 Results")
                        
                        for artifact in task.artifacts:
                            if artifact.type == ArtifactType.IMAGE and artifact.url:
                                st.image(artifact.url, caption=artifact.name, use_container_width=True)
                            
                            elif artifact.type == ArtifactType.VIDEO and artifact.url:
                                st.video(artifact.url)
                                st.caption(artifact.name)
                            
                            elif artifact.type == ArtifactType.TEXT and artifact.content:
                                # Can't nest expander, use a styled container instead
                                st.markdown(f"**📝 {artifact.name}:**")
                                st.markdown(f"> {artifact.content[:500]}..." if len(artifact.content) > 500 else f"> {artifact.content}")
                            
                            elif artifact.type == ArtifactType.UPLOAD:
                                svc = artifact.metadata.get("service", "unknown")
                                st.success(f"☁️ **{artifact.name}** - Uploaded to {svc.title()}")
                            
                            elif artifact.type == ArtifactType.PRODUCT:
                                st.success(f"🛍️ **{artifact.name}** - Product created!")
                            
                            elif artifact.type == ArtifactType.BLOG:
                                url = artifact.url
                                st.success(f"📰 **{artifact.name}**")
                                if url:
                                    st.markdown(f"[View Blog Post]({url})")
                            
                            elif artifact.type == ArtifactType.SOCIAL_POST:
                                platform = artifact.metadata.get("platform", "social")
                                success = artifact.metadata.get("success", False)
                                if success:
                                    st.success(f"📢 Posted to {platform.title()}!")
                                else:
                                    st.warning(f"📢 {platform.title()} post may have failed")
                    
                    # Error display
                    if task.error:
                        st.error(f"❌ Error: {task.error}")
                    
                    # Task actions
                    act_cols = st.columns(4)
                    with act_cols[0]:
                        if task.status in [TaskStatus.READY, TaskStatus.PENDING]:
                            if st.button("▶️ Run", key=f"run_{task.id}"):
                                st.session_state.current_task_index = i
                                st.session_state.queue_running = True
                                st.rerun()
                    with act_cols[1]:
                        if task.status == TaskStatus.FAILED:
                            if st.button("🔄 Retry", key=f"retry_{task.id}"):
                                task.status = TaskStatus.READY
                                task.error = None
                                for step in task.steps:
                                    step.status = TaskStatus.PENDING
                                    step.error = None
                                st.rerun()
                    with act_cols[2]:
                        if st.button("📋 Copy", key=f"copy_{task.id}"):
                            # Duplicate task
                            new_task = queue.create_task(task.description)
                            st.session_state.enhanced_task_queue.append(new_task)
                            st.rerun()
                    with act_cols[3]:
                        if st.button("🗑️", key=f"del_{task.id}"):
                            st.session_state.enhanced_task_queue.remove(task)
                            st.rerun()
    
    # Execute queue
    if st.session_state.queue_running and st.session_state.enhanced_task_queue:
        idx = st.session_state.current_task_index
        
        if idx < len(st.session_state.enhanced_task_queue):
            current_task = st.session_state.enhanced_task_queue[idx]
            
            if current_task.status in [TaskStatus.READY, TaskStatus.PENDING]:
                st.markdown("---")
                st.markdown(f"### ⚡ Executing Task {idx + 1}")
                st.markdown(f"**{current_task.description}**")
                
                progress_container = st.empty()
                results_container = st.container()
                
                def progress_callback(update):
                    with progress_container:
                        status = update.get("status", "running")
                        icon = {"running": "⏳", "completed": "✅", "failed": "❌"}.get(status, "⚪")
                        st.markdown(f"{icon} Step {update['step']}/{update['total']}: {update['name']}")
                    
                    # Display artifacts immediately
                    if update.get("artifacts"):
                        with results_container:
                            for art in update["artifacts"]:
                                art_type = art.get("type", "")
                                if art_type == "image" and art.get("url"):
                                    st.image(art["url"], caption=art.get("name"), use_container_width=True)
                                elif art_type == "video" and art.get("url"):
                                    st.video(art["url"])
                                elif art_type == "text" and art.get("content"):
                                    st.markdown(f"**{art.get('name', 'Content')}:**")
                                    content = art["content"]
                                    st.markdown(f"> {content[:500]}..." if len(content) > 500 else f"> {content}")
                
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    completed_task = loop.run_until_complete(
                        queue.execute_task(current_task, progress_callback)
                    )
                    
                    st.session_state.enhanced_task_queue[idx] = completed_task
                    
                    # Show completion summary before rerun
                    if completed_task.status == TaskStatus.COMPLETED:
                        st.success(f"✅ Task completed! Generated {len(completed_task.artifacts)} artifacts")
                        # Display final artifacts
                        for artifact in completed_task.artifacts:
                            if artifact.type == ArtifactType.IMAGE and artifact.url:
                                st.image(artifact.url, caption=artifact.name, use_container_width=True)
                            elif artifact.type == ArtifactType.VIDEO and artifact.url:
                                st.video(artifact.url)
                    elif completed_task.status == TaskStatus.FAILED:
                        st.error(f"❌ Task failed: {completed_task.error}")
                    
                except Exception as e:
                    current_task.status = TaskStatus.FAILED
                    current_task.error = str(e)
                    st.error(f"❌ Execution error: {e}")
                
                # Move to next
                st.session_state.current_task_index += 1
                
                if st.session_state.current_task_index >= len(st.session_state.enhanced_task_queue):
                    st.session_state.queue_running = False
                    st.success("🎉 All tasks completed!")
                
                st.rerun()
        else:
            st.session_state.queue_running = False
            st.session_state.current_task_index = 0
    
    # Summary stats
    st.markdown("---")
    total = len(st.session_state.enhanced_task_queue)
    completed = sum(1 for t in st.session_state.enhanced_task_queue if t.status == TaskStatus.COMPLETED)
    failed = sum(1 for t in st.session_state.enhanced_task_queue if t.status == TaskStatus.FAILED)
    pending = total - completed - failed
    
    stat_cols = st.columns(4)
    with stat_cols[0]:
        st.metric("Total", total)
    with stat_cols[1]:
        st.metric("Completed", completed)
    with stat_cols[2]:
        st.metric("Pending", pending)
    with stat_cols[3]:
        st.metric("Failed", failed)
    
    # Show execution log / history
    if st.session_state.enhanced_task_queue:
        st.markdown("---")
        st.markdown("### 📜 Execution Log")
        
        for task in reversed(st.session_state.enhanced_task_queue):
            if task.status == TaskStatus.COMPLETED:
                with st.container():
                    st.markdown(f"**✅ {task.description[:60]}**")
                    if task.completed_at:
                        st.caption(f"Completed at {task.completed_at.strftime('%H:%M:%S')} • {len(task.artifacts)} artifacts")
                    
                    # Show all artifacts inline in the log
                    if task.artifacts:
                        cols = st.columns(min(len(task.artifacts), 4))
                        for idx, artifact in enumerate(task.artifacts[:4]):
                            with cols[idx % 4]:
                                if artifact.type == ArtifactType.IMAGE and artifact.url:
                                    st.image(artifact.url, caption=artifact.name, use_container_width=True)
                                elif artifact.type == ArtifactType.VIDEO and artifact.url:
                                    st.video(artifact.url)
                                elif artifact.type == ArtifactType.TEXT:
                                    st.info(f"📝 {artifact.name}")
                                elif artifact.type == ArtifactType.UPLOAD:
                                    st.success(f"☁️ {artifact.metadata.get('service', 'upload')}")
                    st.markdown("---")
            
            elif task.status == TaskStatus.FAILED:
                st.error(f"❌ **{task.description[:60]}** - {task.error or 'Unknown error'}")
