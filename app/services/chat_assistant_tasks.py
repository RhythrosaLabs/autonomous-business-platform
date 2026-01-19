"""
Task Queue System for Autonomous Task Execution
Handles task creation, analysis, planning, and execution with multi-agent orchestration.
"""

from app.tabs.abp_imports_common import (
    os, json, logging, asyncio, datetime, Dict, List, Any, Optional,
    setup_logger
)

logger = setup_logger(__name__)


class TaskQueueItem:
    """Represents a single task in the autonomous queue."""
    
    def __init__(self, task_id: str, description: str):
        self.id = task_id
        self.description = description
        self.status = "pending"  # pending, planning, executing, completed, failed
        self.plan = None  # AI-generated execution plan
        self.agents_needed = []
        self.steps = []
        self.current_step = 0
        self.results = {}
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.error = None


class AutonomousTaskQueue:
    """
    Autonomous task queue system that:
    1. Takes user tasks and analyzes them with AI
    2. Creates execution plans with required agents
    3. Executes tasks autonomously in the background
    4. Allows real-time task addition while running
    """
    
    def __init__(self, replicate_api):
        # Import here to avoid circular dependencies
        from app.services.chat_assistant import MultiAgentOrchestrator
        
        self.replicate = replicate_api
        self.orchestrator = MultiAgentOrchestrator(replicate_api)
        
    def analyze_task(self, description: str) -> Dict[str, Any]:
        """
        Use AI to analyze a task and determine:
        - What the user wants to accomplish
        - Which agents/models are needed
        - The sequence of steps required
        """
        
        analysis_prompt = f"""Analyze this task and create an execution plan.

TASK: {description}

AVAILABLE CAPABILITIES:
- Image Generation: Create product designs, artwork, thumbnails
- Text Generation: Write descriptions, scripts, blog posts, social posts
- Video Generation: Create promotional videos from images
- Marketing: Generate ad copy, social media content, hashtags
- Publishing: Upload to Printify, Shopify, YouTube (requires user confirmation)
- Browser Automation: Navigate websites, fill forms, post content
- Research: Analyze markets, trends, competitors

Respond in this JSON format:
{{
    "summary": "Brief summary of what user wants",
    "goal": "The end goal to achieve",
    "agents_needed": ["designer", "writer", "video", "marketer"],
    "steps": [
        {{"step": 1, "action": "description", "agent": "agent_name", "output_type": "image/text/video"}},
        {{"step": 2, "action": "description", "agent": "agent_name", "output_type": "image/text/video"}}
    ],
    "estimated_time": "X minutes",
    "requires_confirmation": true/false
}}
"""
        
        try:
            response = self.replicate.generate_text(
                prompt=analysis_prompt,
                max_tokens=800,
                temperature=0.3
            )
            
            # Parse JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                return json.loads(response[json_start:json_end])
        except Exception as e:
            logger.error(f"Task analysis failed: {e}")
        
        # Fallback plan
        return {
            "summary": description,
            "goal": "Complete the requested task",
            "agents_needed": ["writer"],
            "steps": [{"step": 1, "action": description, "agent": "writer", "output_type": "text"}],
            "estimated_time": "1-2 minutes",
            "requires_confirmation": False
        }
    
    async def execute_task(self, task: TaskQueueItem, progress_callback=None) -> Dict[str, Any]:
        """Execute a single task using the multi-agent orchestrator."""
        
        task.status = "executing"
        task.started_at = datetime.now()
        
        try:
            # Use the orchestrator to execute
            results = await self.orchestrator.orchestrate(
                task.description,
                context={'task_id': task.id, 'plan': task.plan}
            )
            
            task.results = results
            task.status = "completed" if results.get('success', False) else "failed"
            task.completed_at = datetime.now()
            
            return results
            
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            task.completed_at = datetime.now()
            return {'success': False, 'error': str(e)}


__all__ = [
    'TaskQueueItem',
    'AutonomousTaskQueue'
]
