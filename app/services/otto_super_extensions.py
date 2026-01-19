"""
OTTO SUPER EXTENSIONS - Task Queue & Document Management
========================================================
Extensions to Otto Super that allow it to:
1. Add tasks to the task queue
2. Edit documents in the playground
3. Manage workflows autonomously
4. Interface with Pinterest/TikTok posting
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class OttoTaskQueueExtension:
    """
    Extension that allows Otto to interact with the task queue.
    Otto can now:
    - Add tasks to queue
    - Monitor task progress
    - Chain complex workflows
    """
    
    def __init__(self, task_queue_engine):
        """
        Initialize with reference to task queue engine.
        
        Args:
            task_queue_engine: EnhancedTaskQueue instance
        """
        self.task_queue = task_queue_engine
        logger.info("🔌 Otto Task Queue Extension loaded")
    
    def add_task_from_otto(
        self,
        description: str,
        priority: str = "NORMAL",
        scheduled_for: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Add a task to the queue from Otto's perspective.
        
        Args:
            description: What Otto wants to accomplish
            priority: Task priority (LOW, NORMAL, HIGH, URGENT)
            scheduled_for: Optional datetime to schedule for later
            
        Returns:
            Dict with task details
        """
        from task_queue_engine import TaskPriority
        
        priority_map = {
            "LOW": TaskPriority.LOW,
            "NORMAL": TaskPriority.NORMAL,
            "HIGH": TaskPriority.HIGH,
            "URGENT": TaskPriority.URGENT
        }
        
        task = self.task_queue.create_task(
            description=description,
            priority=priority_map.get(priority, TaskPriority.NORMAL),
            scheduled_for=scheduled_for
        )
        
        logger.info(f"🤖 Otto added task to queue: {task.id} - {description[:50]}...")
        
        return {
            "task_id": task.id,
            "description": task.description,
            "steps": len(task.steps),
            "status": task.status.value,
            "plan": task.plan
        }
    
    def queue_status(self) -> Dict[str, Any]:
        """Get current queue status from the task queue engine."""
        try:
            # Get actual status from task queue
            if hasattr(self.task_queue, 'get_queue_status'):
                return self.task_queue.get_queue_status()
            elif hasattr(self.task_queue, 'tasks'):
                # Count task statuses manually
                tasks = self.task_queue.tasks if hasattr(self.task_queue, 'tasks') else []
                pending = sum(1 for t in tasks if t.status.value == 'pending')
                running = sum(1 for t in tasks if t.status.value == 'running')
                completed = sum(1 for t in tasks if t.status.value == 'completed')
                failed = sum(1 for t in tasks if t.status.value == 'failed')
                return {
                    "total_tasks": len(tasks),
                    "pending": pending,
                    "running": running,
                    "completed": completed,
                    "failed": failed
                }
            else:
                return {
                    "total_tasks": 0,
                    "pending": 0,
                    "running": 0,
                    "completed": 0,
                    "failed": 0,
                    "note": "Task queue not fully initialized"
                }
        except Exception as e:
            logger.warning(f"Could not get queue status: {e}")
            return {
                "total_tasks": 0,
                "pending": 0,
                "running": 0,
                "completed": 0,
                "failed": 0,
                "error": str(e)
            }


class OttoDocumentExtension:
    """
    Extension that allows Otto to edit documents in the playground.
    Otto can now:
    - Create new documents
    - Edit existing documents
    - Save documents to campaigns
    - Generate formatted content
    """
    
    def __init__(self, base_path: str = "."):
        """
        Initialize document extension.
        
        Args:
            base_path: Base path for document storage
        """
        self.base_path = Path(base_path)
        self.campaigns_dir = self.base_path / "campaigns"
        self.docs_dir = self.base_path / "docs"
        self.docs_dir.mkdir(exist_ok=True)
        
        logger.info("📝 Otto Document Extension loaded")
    
    def create_document(
        self,
        title: str,
        content: str,
        doc_type: str = "markdown",
        campaign_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new document.
        
        Args:
            title: Document title
            content: Document content
            doc_type: Type (markdown, txt, html, json)
            campaign_name: Optional campaign to associate with
            
        Returns:
            Dict with document details
        """
        # Determine save location
        if campaign_name:
            save_dir = self.campaigns_dir / campaign_name / "documents"
            save_dir.mkdir(parents=True, exist_ok=True)
        else:
            save_dir = self.docs_dir
        
        # Create filename
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_title = safe_title.replace(' ', '_')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        extensions = {
            "markdown": ".md",
            "txt": ".txt",
            "html": ".html",
            "json": ".json"
        }
        ext = extensions.get(doc_type, ".txt")
        
        filename = f"{safe_title}_{timestamp}{ext}"
        file_path = save_dir / filename
        
        # Write content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"📄 Otto created document: {file_path}")
        
        return {
            "file_path": str(file_path),
            "filename": filename,
            "title": title,
            "type": doc_type,
            "size": len(content),
            "campaign": campaign_name
        }
    
    def edit_document(
        self,
        file_path: str,
        new_content: str,
        append: bool = False
    ) -> Dict[str, Any]:
        """
        Edit an existing document.
        
        Args:
            file_path: Path to document
            new_content: New content (or content to append)
            append: If True, append instead of replace
            
        Returns:
            Dict with edit result
        """
        path = Path(file_path)
        
        if not path.exists():
            return {
                "success": False,
                "error": f"Document not found: {file_path}"
            }
        
        try:
            if append:
                with open(path, 'a', encoding='utf-8') as f:
                    f.write('\n\n' + new_content)
            else:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
            
            logger.info(f"✏️ Otto edited document: {path}")
            
            return {
                "success": True,
                "file_path": str(path),
                "operation": "append" if append else "replace",
                "new_size": path.stat().st_size
            }
        except Exception as e:
            logger.error(f"Failed to edit document: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def list_documents(
        self,
        campaign_name: Optional[str] = None,
        doc_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List available documents.
        
        Args:
            campaign_name: Filter by campaign
            doc_type: Filter by document type
            
        Returns:
            List of document info dicts
        """
        if campaign_name:
            search_dir = self.campaigns_dir / campaign_name / "documents"
        else:
            search_dir = self.docs_dir
        
        if not search_dir.exists():
            return []
        
        documents = []
        
        pattern = "*"
        if doc_type:
            extensions = {
                "markdown": "*.md",
                "txt": "*.txt",
                "html": "*.html",
                "json": "*.json"
            }
            pattern = extensions.get(doc_type, "*")
        
        for doc_path in search_dir.glob(pattern):
            if doc_path.is_file():
                documents.append({
                    "filename": doc_path.name,
                    "path": str(doc_path),
                    "size": doc_path.stat().st_size,
                    "modified": datetime.fromtimestamp(doc_path.stat().st_mtime).isoformat(),
                    "campaign": campaign_name
                })
        
        return documents
    
    def read_document(self, file_path: str) -> Dict[str, Any]:
        """
        Read a document's content.
        
        Args:
            file_path: Path to document
            
        Returns:
            Dict with content and metadata
        """
        path = Path(file_path)
        
        if not path.exists():
            return {
                "success": False,
                "error": f"Document not found: {file_path}"
            }
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                "success": True,
                "content": content,
                "filename": path.name,
                "size": len(content),
                "path": str(path)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


class OttoPinterestTikTokExtension:
    """
    Extension that allows Otto to post to Pinterest and TikTok.
    """
    
    def __init__(self, multi_platform_poster=None):
        """
        Initialize Pinterest/TikTok extension.
        
        Args:
            multi_platform_poster: MultiPlatformPoster instance
        """
        self.poster = multi_platform_poster
        logger.info("📌🎵 Otto Pinterest/TikTok Extension loaded")
    
    async def post_to_pinterest(
        self,
        image_path: str,
        caption: str,
        board: Optional[str] = None,
        link: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Post to Pinterest.
        
        Args:
            image_path: Path to image
            caption: Pin description
            board: Pinterest board name
            link: Destination link
            
        Returns:
            Result dict
        """
        if not self.poster:
            return {
                "success": False,
                "error": "Multi-platform poster not configured"
            }
        
        try:
            result = await self.poster.post_to_platform(
                platform='pinterest',
                image_path=image_path,
                caption=caption,
                board=board or "",
                link=link or ""
            )
            
            logger.info(f"📌 Otto posted to Pinterest: {result.get('message', 'Success')}")
            return result
        except Exception as e:
            logger.error(f"Pinterest posting failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def post_to_tiktok(
        self,
        video_path: str,
        caption: str,
        hashtags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Post to TikTok.
        
        Args:
            video_path: Path to video file
            caption: Video description
            hashtags: List of hashtags (without #)
            
        Returns:
            Result dict
        """
        if not self.poster:
            return {
                "success": False,
                "error": "Multi-platform poster not configured"
            }
        
        # Add hashtags to caption
        full_caption = caption
        if hashtags:
            full_caption += "\n\n" + " ".join([f"#{tag}" for tag in hashtags])
        
        try:
            result = await self.poster.post_to_platform(
                platform='tiktok',
                image_path=video_path,  # Will handle as video
                caption=full_caption
            )
            
            logger.info(f"🎵 Otto posted to TikTok: {result.get('message', 'Success')}")
            return result
        except Exception as e:
            logger.error(f"TikTok posting failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }


class OttoWorkflowExtension:
    """
    Extension for managing complex multi-step workflows.
    Combines all Otto extensions for powerful automation.
    """
    
    def __init__(
        self,
        task_queue_ext: OttoTaskQueueExtension,
        document_ext: OttoDocumentExtension,
        social_ext: OttoPinterestTikTokExtension
    ):
        """Initialize workflow extension with all sub-extensions."""
        self.tasks = task_queue_ext
        self.docs = document_ext
        self.social = social_ext
        logger.info("⚡ Otto Workflow Extension loaded - Full automation enabled")
    
    async def execute_workflow(
        self,
        workflow_type: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a predefined workflow.
        
        Workflow types:
        - content_to_social: Create document → Post to social
        - campaign_full: Generate → Document → Social → Task queue
        - pinterest_campaign: Images → Pinterest boards
        - tiktok_series: Videos → TikTok with schedule
        
        Args:
            workflow_type: Type of workflow
            parameters: Workflow-specific parameters
            
        Returns:
            Workflow execution result
        """
        results = {
            "workflow": workflow_type,
            "started_at": datetime.now().isoformat(),
            "steps": []
        }
        
        try:
            if workflow_type == "content_to_social":
                # Create content document
                doc_result = self.docs.create_document(
                    title=parameters.get("title", "Generated Content"),
                    content=parameters.get("content", ""),
                    doc_type="markdown"
                )
                results["steps"].append({"action": "create_document", "result": doc_result})
                
                # Post to Pinterest if image provided
                if parameters.get("image_path"):
                    pinterest_result = await self.social.post_to_pinterest(
                        image_path=parameters["image_path"],
                        caption=parameters.get("caption", parameters.get("title", "")),
                        board=parameters.get("pinterest_board")
                    )
                    results["steps"].append({"action": "post_pinterest", "result": pinterest_result})
            
            elif workflow_type == "pinterest_campaign":
                # Post multiple images to Pinterest
                images = parameters.get("images", [])
                board = parameters.get("board", "")
                
                for img in images:
                    pinterest_result = await self.social.post_to_pinterest(
                        image_path=img["path"],
                        caption=img.get("caption", ""),
                        board=board,
                        link=img.get("link")
                    )
                    results["steps"].append({"action": "post_pinterest", "result": pinterest_result})
            
            elif workflow_type == "tiktok_series":
                # Post multiple videos to TikTok
                videos = parameters.get("videos", [])
                
                for vid in videos:
                    tiktok_result = await self.social.post_to_tiktok(
                        video_path=vid["path"],
                        caption=vid.get("caption", ""),
                        hashtags=vid.get("hashtags", [])
                    )
                    results["steps"].append({"action": "post_tiktok", "result": tiktok_result})
                    
                    # Add delay between posts if specified
                    if parameters.get("delay_minutes"):
                        import asyncio
                        await asyncio.sleep(parameters["delay_minutes"] * 60)
            
            elif workflow_type == "campaign_full":
                # Full campaign: Generate → Document → Queue tasks
                
                # 1. Create campaign document
                doc_result = self.docs.create_document(
                    title=parameters.get("campaign_name", "Campaign Plan"),
                    content=parameters.get("plan", ""),
                    doc_type="markdown",
                    campaign_name=parameters.get("campaign_name")
                )
                results["steps"].append({"action": "create_document", "result": doc_result})
                
                # 2. Add tasks to queue for execution
                tasks_to_queue = parameters.get("tasks", [])
                for task_desc in tasks_to_queue:
                    task_result = self.tasks.add_task_from_otto(
                        description=task_desc,
                        priority="NORMAL"
                    )
                    results["steps"].append({"action": "queue_task", "result": task_result})
            
            results["success"] = True
            results["completed_at"] = datetime.now().isoformat()
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            results["success"] = False
            results["error"] = str(e)
        
        return results


# Integration functions for Otto Super
def enhance_otto_with_extensions(
    otto_super,
    task_queue_engine=None,
    multi_platform_poster=None
) -> Dict[str, Any]:
    """
    Enhance Otto Super with all extension capabilities.
    
    Args:
        otto_super: OttoSuper instance
        task_queue_engine: Optional EnhancedTaskQueue
        multi_platform_poster: Optional MultiPlatformPoster
        
    Returns:
        Dict of extension instances
    """
    extensions = {}
    
    # Task Queue Extension
    if task_queue_engine:
        extensions['tasks'] = OttoTaskQueueExtension(task_queue_engine)
    
    # Document Extension
    extensions['docs'] = OttoDocumentExtension()
    
    # Social Extension
    if multi_platform_poster:
        extensions['social'] = OttoPinterestTikTokExtension(multi_platform_poster)
    
    # Workflow Extension (if we have all pieces)
    if all(k in extensions for k in ['tasks', 'docs', 'social']):
        extensions['workflow'] = OttoWorkflowExtension(
            extensions['tasks'],
            extensions['docs'],
            extensions['social']
        )
    
    logger.info(f"🚀 Otto Super enhanced with {len(extensions)} extensions")
    
    return extensions


# Add these methods to Otto Super's intent parser
EXTENDED_INTENT_KEYWORDS = {
    'add_to_queue': ['add to queue', 'queue this', 'add task', 'schedule task'],
    'create_document': ['create document', 'write document', 'save document', 'make doc'],
    'edit_document': ['edit document', 'update document', 'modify document'],
    'post_pinterest': ['post to pinterest', 'pin this', 'create pin', 'pinterest'],
    'post_tiktok': ['post to tiktok', 'tiktok video', 'upload to tiktok'],
    'run_workflow': ['run workflow', 'execute workflow', 'start campaign workflow']
}


def parse_extended_intent(message: str) -> Optional[str]:
    """
    Parse message for extended Otto capabilities.
    
    Returns:
        Intent type if matched, None otherwise
    """
    msg_lower = message.lower()
    
    for intent, keywords in EXTENDED_INTENT_KEYWORDS.items():
        if any(kw in msg_lower for kw in keywords):
            return intent
    
    return None
