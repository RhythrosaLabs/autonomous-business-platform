"""
FastAPI Backend for Autonomous Business Platform

This backend handles all long-running operations, job management, and state persistence.
Streamlit frontend communicates with this API for all operations.

Architecture:
┌─────────────────┐       ┌──────────────────┐       ┌─────────────┐
│  Streamlit UI   │──────▶│  FastAPI Backend │──────▶│ Ray Workers │
│  (Port 8501)    │◀──────│  (Port 8000)     │◀──────│             │
└─────────────────┘       └──────────────────┘       └─────────────┘
"""

import os
from app.services.secure_config import get_api_key
import sys
import json
import uuid
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict, field
from enum import Enum
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
import uvicorn

# Retry logic
try:
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
    HAS_TENACITY = True
except ImportError:
    HAS_TENACITY = False
    logger.warning("⚠️ tenacity not installed, retry logic disabled")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========================================
# JOB STATUS AND TYPES
# ========================================

class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    IMAGE_GENERATION = "image_generation"
    VIDEO_GENERATION = "video_generation"
    TEXT_GENERATION = "text_generation"
    PRODUCT_CREATION = "product_creation"
    CAMPAIGN_GENERATION = "campaign_generation"
    BLOG_GENERATION = "blog_generation"
    EMAIL_GENERATION = "email_generation"
    WORKFLOW_EXECUTION = "workflow_execution"
    BATCH_OPERATION = "batch_operation"


# ========================================
# PYDANTIC MODELS FOR API
# ========================================

class JobSubmitRequest(BaseModel):
    job_type: str
    tab_name: str
    description: str
    params: Dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=5, ge=1, le=10)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class JobResponse(BaseModel):
    job_id: str
    job_type: str
    tab_name: str
    description: str
    status: str
    progress: float = 0.0
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BatchJobRequest(BaseModel):
    job_type: str
    tab_name: str
    items: List[Dict[str, Any]]
    description_template: str = "Item {index}"
    priority: int = Field(default=5, ge=1, le=10)


class QueueStats(BaseModel):
    total: int
    queued: int
    running: int
    completed: int
    failed: int
    cancelled: int
    by_tab: Dict[str, int] = Field(default_factory=dict)
    ray_enabled: bool = False
    ray_cpus: float = 0
    ray_memory_gb: float = 0


# ========================================
# JOB STORAGE (In-Memory + Disk Persistence)
# ========================================

@dataclass
class Job:
    job_id: str
    job_type: str
    tab_name: str
    description: str
    status: JobStatus
    params: Dict[str, Any]
    priority: int
    metadata: Dict[str, Any]
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0
    result: Optional[Any] = None
    error: Optional[str] = None
    ray_task_id: Optional[str] = None

    def to_response(self) -> JobResponse:
        return JobResponse(
            job_id=self.job_id,
            job_type=self.job_type,
            tab_name=self.tab_name,
            description=self.description,
            status=self.status.value,
            progress=self.progress,
            result=self.result,
            error=self.error,
            created_at=self.created_at.isoformat(),
            started_at=self.started_at.isoformat() if self.started_at else None,
            completed_at=self.completed_at.isoformat() if self.completed_at else None,
            metadata=self.metadata
        )


class JobManager:
    """Manages all jobs with Ray backend"""
    
    def __init__(self):
        self.jobs: Dict[str, Job] = {}
        self.ray_available = False
        self.ray_info = {}
        self._init_ray()
        self._load_jobs_from_disk()
        
    def _init_ray(self):
        """Initialize Ray if available"""
        try:
            import ray
            if not ray.is_initialized():
                ray.init(
                    namespace="fastapi_backend",
                    ignore_reinit_error=True,
                    logging_level=logging.WARNING
                )
            self.ray_available = True
            self.ray_info = {
                "cpus": ray.cluster_resources().get("CPU", 0),
                "memory_gb": ray.cluster_resources().get("memory", 0) / (1024**3),
                "gpus": ray.cluster_resources().get("GPU", 0),
            }
            logger.info(f"✅ Ray initialized: {self.ray_info}")
        except Exception as e:
            logger.warning(f"Ray not available: {e}")
            self.ray_available = False
            
    def _load_jobs_from_disk(self):
        """Load persisted jobs on startup"""
        jobs_file = Path("data/fastapi_jobs.json")
        if jobs_file.exists():
            try:
                with open(jobs_file) as f:
                    data = json.load(f)
                for job_data in data:
                    job = Job(
                        job_id=job_data["job_id"],
                        job_type=job_data["job_type"],
                        tab_name=job_data["tab_name"],
                        description=job_data["description"],
                        status=JobStatus(job_data["status"]),
                        params=job_data.get("params", {}),
                        priority=job_data.get("priority", 5),
                        metadata=job_data.get("metadata", {}),
                        created_at=datetime.fromisoformat(job_data["created_at"]),
                        started_at=datetime.fromisoformat(job_data["started_at"]) if job_data.get("started_at") else None,
                        completed_at=datetime.fromisoformat(job_data["completed_at"]) if job_data.get("completed_at") else None,
                        progress=job_data.get("progress", 0),
                        result=job_data.get("result"),
                        error=job_data.get("error"),
                    )
                    self.jobs[job.job_id] = job
                logger.info(f"📂 Loaded {len(self.jobs)} jobs from disk")
            except Exception as e:
                logger.error(f"Failed to load jobs: {e}")
                
    def _save_jobs_to_disk(self):
        """Persist jobs to disk"""
        jobs_file = Path("data/fastapi_jobs.json")
        jobs_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = []
            for job in self.jobs.values():
                data.append({
                    "job_id": job.job_id,
                    "job_type": job.job_type,
                    "tab_name": job.tab_name,
                    "description": job.description,
                    "status": job.status.value,
                    "params": job.params,
                    "priority": job.priority,
                    "metadata": job.metadata,
                    "created_at": job.created_at.isoformat(),
                    "started_at": job.started_at.isoformat() if job.started_at else None,
                    "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                    "progress": job.progress,
                    "result": job.result,
                    "error": job.error,
                })
            with open(jobs_file, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save jobs: {e}")
    
    def submit_job(self, request: JobSubmitRequest) -> Job:
        """Submit a new job"""
        job_id = str(uuid.uuid4())[:8]
        job = Job(
            job_id=job_id,
            job_type=request.job_type,
            tab_name=request.tab_name,
            description=request.description,
            status=JobStatus.QUEUED,
            params=request.params,
            priority=request.priority,
            metadata=request.metadata,
            created_at=datetime.now(),
        )
        self.jobs[job_id] = job
        self._save_jobs_to_disk()
        logger.info(f"📋 Job submitted: {job_id} - {request.description}")
        return job
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID"""
        return self.jobs.get(job_id)
    
    def get_all_jobs(self, tab_name: Optional[str] = None, status: Optional[str] = None) -> List[Job]:
        """Get all jobs with optional filtering"""
        jobs = list(self.jobs.values())
        if tab_name:
            jobs = [j for j in jobs if j.tab_name == tab_name]
        if status:
            jobs = [j for j in jobs if j.status.value == status]
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)
    
    def update_job_status(self, job_id: str, status: JobStatus, 
                          progress: float = None, result: Any = None, error: str = None):
        """Update job status"""
        job = self.jobs.get(job_id)
        if job:
            job.status = status
            if progress is not None:
                job.progress = progress
            if result is not None:
                job.result = result
            if error is not None:
                job.error = error
            if status == JobStatus.RUNNING and not job.started_at:
                job.started_at = datetime.now()
            if status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                job.completed_at = datetime.now()
            self._save_jobs_to_disk()
            
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job"""
        job = self.jobs.get(job_id)
        if job and job.status in [JobStatus.QUEUED, JobStatus.RUNNING]:
            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.now()
            self._save_jobs_to_disk()
            return True
        return False
    
    def delete_job(self, job_id: str) -> bool:
        """Delete a job"""
        if job_id in self.jobs:
            del self.jobs[job_id]
            self._save_jobs_to_disk()
            return True
        return False
    
    def get_stats(self) -> QueueStats:
        """Get queue statistics"""
        jobs = list(self.jobs.values())
        by_tab = {}
        for job in jobs:
            by_tab[job.tab_name] = by_tab.get(job.tab_name, 0) + 1
            
        return QueueStats(
            total=len(jobs),
            queued=len([j for j in jobs if j.status == JobStatus.QUEUED]),
            running=len([j for j in jobs if j.status == JobStatus.RUNNING]),
            completed=len([j for j in jobs if j.status == JobStatus.COMPLETED]),
            failed=len([j for j in jobs if j.status == JobStatus.FAILED]),
            cancelled=len([j for j in jobs if j.status == JobStatus.CANCELLED]),
            by_tab=by_tab,
            ray_enabled=self.ray_available,
            ray_cpus=self.ray_info.get("cpus", 0),
            ray_memory_gb=self.ray_info.get("memory_gb", 0),
        )
    
    def clear_completed(self) -> int:
        """Clear all completed/failed/cancelled jobs"""
        to_delete = [
            job_id for job_id, job in self.jobs.items()
            if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]
        ]
        for job_id in to_delete:
            del self.jobs[job_id]
        self._save_jobs_to_disk()
        return len(to_delete)


# ========================================
# JOB EXECUTION ENGINE
# ========================================

class JobExecutor:
    """Executes jobs using Ray or threading"""
    
    def __init__(self, job_manager: JobManager):
        self.job_manager = job_manager
        self.replicate_api = None
        self._init_replicate()
        
    def _init_replicate(self):
        """Initialize Replicate API"""
        try:
            from app.services.api_service import ReplicateAPI
            token = get_api_key("REPLICATE_API_TOKEN")
            if token:
                self.replicate_api = ReplicateAPI(token)
                logger.info("✅ Replicate API initialized")
        except Exception as e:
            logger.warning(f"Replicate API not available: {e}")
    
    def _create_retry_decorator(self):
        """Create retry decorator if tenacity available."""
        if HAS_TENACITY:
            return retry(
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=1, min=1, max=10),
                retry=retry_if_exception_type((ConnectionError, TimeoutError, Exception)),
                reraise=True
            )
        else:
            # No-op decorator if tenacity not available
            def no_retry(func):
                return func
            return no_retry
            
    async def execute_job(self, job_id: str):
        """Execute a single job with retry logic"""
        job = self.job_manager.get_job(job_id)
        if not job:
            return
            
        self.job_manager.update_job_status(job_id, JobStatus.RUNNING, progress=0)
        
        # Create retry decorator
        retry_decorator = self._create_retry_decorator()
        
        @retry_decorator
        async def execute_with_retry():
            """Execute job with automatic retry on failure."""
            result = None
            
            if job.job_type == JobType.IMAGE_GENERATION.value:
                result = await self._generate_image(job)
            elif job.job_type == JobType.TEXT_GENERATION.value:
                result = await self._generate_text(job)
            elif job.job_type == JobType.VIDEO_GENERATION.value:
                result = await self._generate_video(job)
            elif job.job_type == JobType.PRODUCT_CREATION.value:
                result = await self._create_product(job)
            elif job.job_type == JobType.BLOG_GENERATION.value:
                result = await self._generate_blog(job)
            elif job.job_type == JobType.EMAIL_GENERATION.value:
                result = await self._generate_email(job)
            else:
                result = {"message": f"Job type {job.job_type} executed"}
            
            return result
        
        try:
            result = await execute_with_retry()
                
            self.job_manager.update_job_status(
                job_id, JobStatus.COMPLETED, progress=100, result=result
            )
            logger.info(f"✅ Job completed: {job_id}")
            
        except Exception as e:
            logger.error(f"❌ Job failed after retries: {job_id} - {e}")
            self.job_manager.update_job_status(
                job_id, JobStatus.FAILED, error=str(e)
            )
            
    async def _generate_image(self, job: Job) -> Dict[str, Any]:
        """Generate image using Replicate"""
        if not self.replicate_api:
            raise Exception("Replicate API not configured")
            
        prompt = job.params.get("prompt", "")
        model = job.params.get("model", "flux-fast")
        width = job.params.get("width", 1024)
        height = job.params.get("height", 1024)
        
        self.job_manager.update_job_status(job.job_id, JobStatus.RUNNING, progress=10)
        
        # Run in thread pool to not block
        loop = asyncio.get_event_loop()
        image_url = await loop.run_in_executor(
            None, 
            lambda: self.replicate_api.generate_image(prompt, model=model, width=width, height=height)
        )
        
        self.job_manager.update_job_status(job.job_id, JobStatus.RUNNING, progress=80)
        
        # Download and save image
        if image_url:
            import requests
            from pathlib import Path
            
            response = requests.get(image_url)
            if response.status_code == 200:
                images_dir = Path("library/images")
                images_dir.mkdir(parents=True, exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"image_{timestamp}_{job.job_id}.png"
                filepath = images_dir / filename
                
                with open(filepath, "wb") as f:
                    f.write(response.content)
                    
                return {
                    "image_url": image_url,
                    "local_path": str(filepath),
                    "prompt": prompt,
                    "model": model,
                }
                
        return {"error": "Failed to generate image"}
    
    async def _generate_text(self, job: Job) -> Dict[str, Any]:
        """Generate text using Replicate"""
        if not self.replicate_api:
            raise Exception("Replicate API not configured")
            
        prompt = job.params.get("prompt", "")
        max_tokens = job.params.get("max_tokens", 500)
        
        self.job_manager.update_job_status(job.job_id, JobStatus.RUNNING, progress=10)
        
        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(
            None,
            lambda: self.replicate_api.generate_text(prompt, max_tokens=max_tokens)
        )
        
        return {"text": text, "prompt": prompt}
    
    async def _generate_video(self, job: Job) -> Dict[str, Any]:
        """Generate video using Replicate"""
        if not self.replicate_api:
            raise Exception("Replicate API not configured")
            
        prompt = job.params.get("prompt", "")
        model = job.params.get("model", "kling")
        
        self.job_manager.update_job_status(job.job_id, JobStatus.RUNNING, progress=10)
        
        # Video generation is typically longer
        try:
            import replicate
            
            loop = asyncio.get_event_loop()
            
            if "kling" in model.lower():
                video_url = await loop.run_in_executor(
                    None,
                    lambda: replicate.run(
                        "kwaivgi/kling-v2.5-turbo-pro",
                        input={"prompt": prompt, "aspect_ratio": "16:9"}
                    )
                )
            else:
                video_url = await loop.run_in_executor(
                    None,
                    lambda: replicate.run(
                        "luma/ray",
                        input={"prompt": prompt}
                    )
                )
                
            self.job_manager.update_job_status(job.job_id, JobStatus.RUNNING, progress=80)
            
            # Download video
            if video_url:
                import requests
                from pathlib import Path
                
                response = requests.get(video_url, stream=True)
                if response.status_code == 200:
                    videos_dir = Path("library/videos")
                    videos_dir.mkdir(parents=True, exist_ok=True)
                    
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"video_{timestamp}_{job.job_id}.mp4"
                    filepath = videos_dir / filename
                    
                    with open(filepath, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                            
                    return {
                        "video_url": video_url,
                        "local_path": str(filepath),
                        "prompt": prompt,
                        "model": model,
                    }
                    
        except Exception as e:
            raise Exception(f"Video generation failed: {e}")
            
        return {"error": "Failed to generate video"}
    
    async def _create_product(self, job: Job) -> Dict[str, Any]:
        """Create product design"""
        # Generate image first
        image_result = await self._generate_image(job)
        
        if "error" not in image_result:
            return {
                **image_result,
                "product_type": job.params.get("product_type", "t-shirt"),
                "style": job.params.get("style", "modern"),
            }
        return image_result
    
    async def _generate_blog(self, job: Job) -> Dict[str, Any]:
        """Generate blog post"""
        topic = job.params.get("topic", "")
        
        # Generate blog content
        text_job = Job(
            job_id=job.job_id,
            job_type=JobType.TEXT_GENERATION.value,
            tab_name=job.tab_name,
            description=f"Blog: {topic}",
            status=JobStatus.RUNNING,
            params={
                "prompt": f"Write a detailed blog post about: {topic}. Include an engaging introduction, main points, and conclusion.",
                "max_tokens": 2000
            },
            priority=job.priority,
            metadata=job.metadata,
            created_at=job.created_at,
        )
        
        text_result = await self._generate_text(text_job)
        
        return {
            "topic": topic,
            "content": text_result.get("text", ""),
        }
    
    async def _generate_email(self, job: Job) -> Dict[str, Any]:
        """Generate email campaign"""
        subject = job.params.get("subject", "")
        
        text_job = Job(
            job_id=job.job_id,
            job_type=JobType.TEXT_GENERATION.value,
            tab_name=job.tab_name,
            description=f"Email: {subject}",
            status=JobStatus.RUNNING,
            params={
                "prompt": f"Write a professional marketing email with subject: {subject}. Include SUBJECT: and BODY: sections.",
                "max_tokens": 800
            },
            priority=job.priority,
            metadata=job.metadata,
            created_at=job.created_at,
        )
        
        text_result = await self._generate_text(text_job)
        
        return {
            "subject": subject,
            "content": text_result.get("text", ""),
        }


# ========================================
# WEBSOCKET CONNECTION MANAGER
# ========================================

class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")
        
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")
        
    async def broadcast(self, message: dict):
        """Send message to all connected clients"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.disconnect(conn)
            
    async def send_job_update(self, job: Job):
        """Send job update to all clients"""
        await self.broadcast({
            "type": "job_update",
            "job": job.to_response().dict()
        })


# ========================================
# FASTAPI APP SETUP
# ========================================

# Global instances
job_manager: Optional[JobManager] = None
job_executor: Optional[JobExecutor] = None
ws_manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    global job_manager, job_executor
    
    # Startup
    logger.info("🚀 Starting FastAPI Backend...")
    job_manager = JobManager()
    job_executor = JobExecutor(job_manager)
    logger.info("✅ FastAPI Backend ready")
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down FastAPI Backend...")


app = FastAPI(
    title="Autonomous Business Platform API",
    description="Backend API for job management and parallel execution",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========================================
# API ENDPOINTS
# ========================================

@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "healthy",
        "service": "Autonomous Business Platform API",
        "ray_enabled": job_manager.ray_available if job_manager else False
    }


@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "ray_enabled": job_manager.ray_available if job_manager else False,
        "ray_info": job_manager.ray_info if job_manager else {},
        "jobs_count": len(job_manager.jobs) if job_manager else 0,
        "websocket_connections": len(ws_manager.active_connections),
    }


# ========================================
# JOB ENDPOINTS
# ========================================

@app.post("/jobs", response_model=JobResponse)
async def submit_job(request: JobSubmitRequest, background_tasks: BackgroundTasks):
    """Submit a new job for execution"""
    if not job_manager:
        raise HTTPException(status_code=503, detail="Service not ready")
        
    job = job_manager.submit_job(request)
    
    # Execute job in background
    background_tasks.add_task(job_executor.execute_job, job.job_id)
    
    # Notify WebSocket clients
    await ws_manager.send_job_update(job)
    
    return job.to_response()


@app.post("/jobs/batch")
async def submit_batch_jobs(request: BatchJobRequest, background_tasks: BackgroundTasks):
    """Submit multiple jobs at once"""
    if not job_manager:
        raise HTTPException(status_code=503, detail="Service not ready")
        
    job_ids = []
    for index, item in enumerate(request.items):
        job_request = JobSubmitRequest(
            job_type=request.job_type,
            tab_name=request.tab_name,
            description=request.description_template.format(index=index+1, **item),
            params=item,
            priority=request.priority,
        )
        job = job_manager.submit_job(job_request)
        job_ids.append(job.job_id)
        
        # Execute each job in background
        background_tasks.add_task(job_executor.execute_job, job.job_id)
        
    return {"job_ids": job_ids, "count": len(job_ids)}


@app.get("/jobs", response_model=List[JobResponse])
async def list_jobs(tab_name: Optional[str] = None, status: Optional[str] = None, limit: int = 100):
    """List all jobs with optional filtering"""
    if not job_manager:
        raise HTTPException(status_code=503, detail="Service not ready")
        
    jobs = job_manager.get_all_jobs(tab_name=tab_name, status=status)
    return [job.to_response() for job in jobs[:limit]]


@app.get("/jobs/stats", response_model=QueueStats)
async def get_job_stats():
    """Get queue statistics"""
    if not job_manager:
        raise HTTPException(status_code=503, detail="Service not ready")
        
    return job_manager.get_stats()


@app.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    """Get a specific job by ID"""
    if not job_manager:
        raise HTTPException(status_code=503, detail="Service not ready")
        
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    return job.to_response()


@app.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Cancel a job"""
    if not job_manager:
        raise HTTPException(status_code=503, detail="Service not ready")
        
    success = job_manager.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot cancel job")
        
    job = job_manager.get_job(job_id)
    await ws_manager.send_job_update(job)
    
    return {"status": "cancelled", "job_id": job_id}


@app.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job"""
    if not job_manager:
        raise HTTPException(status_code=503, detail="Service not ready")
        
    success = job_manager.delete_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found")
        
    await ws_manager.broadcast({
        "type": "job_deleted",
        "job_id": job_id
    })
    
    return {"status": "deleted", "job_id": job_id}


@app.post("/jobs/clear")
async def clear_completed_jobs():
    """Clear all completed/failed/cancelled jobs"""
    if not job_manager:
        raise HTTPException(status_code=503, detail="Service not ready")
        
    count = job_manager.clear_completed()
    
    await ws_manager.broadcast({
        "type": "jobs_cleared",
        "count": count
    })
    
    return {"status": "cleared", "count": count}


# ========================================
# CONVENIENCE ENDPOINTS FOR SPECIFIC OPERATIONS
# ========================================

@app.post("/generate/image")
async def generate_image(
    prompt: str,
    model: str = "flux-fast",
    width: int = 1024,
    height: int = 1024,
    tab_name: str = "Products",
    background_tasks: BackgroundTasks = None
):
    """Quick endpoint to generate an image"""
    request = JobSubmitRequest(
        job_type=JobType.IMAGE_GENERATION.value,
        tab_name=tab_name,
        description=f"Image: {prompt[:50]}...",
        params={"prompt": prompt, "model": model, "width": width, "height": height},
        priority=7
    )
    return await submit_job(request, background_tasks)


@app.post("/generate/text")
async def generate_text(
    prompt: str,
    max_tokens: int = 500,
    tab_name: str = "Content",
    background_tasks: BackgroundTasks = None
):
    """Quick endpoint to generate text"""
    request = JobSubmitRequest(
        job_type=JobType.TEXT_GENERATION.value,
        tab_name=tab_name,
        description=f"Text: {prompt[:50]}...",
        params={"prompt": prompt, "max_tokens": max_tokens},
        priority=5
    )
    return await submit_job(request, background_tasks)


@app.post("/generate/video")
async def generate_video(
    prompt: str,
    model: str = "kling",
    tab_name: str = "Video",
    background_tasks: BackgroundTasks = None
):
    """Quick endpoint to generate a video"""
    request = JobSubmitRequest(
        job_type=JobType.VIDEO_GENERATION.value,
        tab_name=tab_name,
        description=f"Video: {prompt[:50]}...",
        params={"prompt": prompt, "model": model},
        priority=8
    )
    return await submit_job(request, background_tasks)


@app.post("/generate/product")
async def generate_product(
    prompt: str,
    product_type: str = "t-shirt",
    style: str = "modern",
    model: str = "flux-fast",
    tab_name: str = "Products",
    background_tasks: BackgroundTasks = None
):
    """Quick endpoint to generate a product design"""
    request = JobSubmitRequest(
        job_type=JobType.PRODUCT_CREATION.value,
        tab_name=tab_name,
        description=f"Product: {prompt[:50]}...",
        params={
            "prompt": prompt,
            "product_type": product_type,
            "style": style,
            "model": model
        },
        priority=6
    )
    return await submit_job(request, background_tasks)


# ========================================
# WEBSOCKET ENDPOINT
# ========================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time job updates"""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and listen for client messages
            data = await websocket.receive_text()
            
            # Handle client commands
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                elif message.get("type") == "get_stats":
                    stats = job_manager.get_stats()
                    await websocket.send_json({
                        "type": "stats",
                        "data": stats.dict()
                    })
            except json.JSONDecodeError:
                pass
                
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# ========================================
# MAIN
# ========================================

if __name__ == "__main__":
    uvicorn.run(
        "fastapi_backend:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
