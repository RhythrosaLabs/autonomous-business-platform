"""
Otto Engine - Data Models and Support Classes
Contains all data models, configuration, and utility classes for the Otto Engine.

Classes:
- OttoKnowledgeBase: Persistent memory system with image/document analysis
- OttoAppAwareness: Real-time app state monitoring
- OttoPerformanceConfig: Performance tuning configuration
- RequestCache: In-memory cache for repeated requests
- TaskType, TaskStep, TaskPlan: Task workflow structures
"""

from app.tabs.abp_imports_common import (
    st, os, json, logging, asyncio, uuid, re, time, hashlib, base64, tempfile,
    Path, Dict, List, Any, Optional, Tuple, Callable, Union, datetime,
    ThreadPoolExecutor, dataclass, field, Enum, lru_cache, BytesIO, pickle,
    setup_logger
)

logger = setup_logger(__name__)


# ============================================================================
# KNOWLEDGE BASE SYSTEM - Memory, Documents, and Image Analysis
# ============================================================================
class OttoKnowledgeBase:
    """
    Otto's knowledge base for persistent memory and context.
    Supports image analysis, document reading, and memory management.
    """
    
    def __init__(self, storage_path: str = "otto_knowledge"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        self.memory_file = self.storage_path / "memory.json"
        self.documents_dir = self.storage_path / "documents"
        self.images_dir = self.storage_path / "images"
        self.documents_dir.mkdir(exist_ok=True)
        self.images_dir.mkdir(exist_ok=True)
        
        # Load existing memory
        self.memory: Dict[str, Any] = self._load_memory()
        self.documents: Dict[str, Dict] = self.memory.get("documents", {})
        self.images: Dict[str, Dict] = self.memory.get("images", {})
        self.facts: List[Dict] = self.memory.get("facts", [])
        self.context: Dict[str, Any] = self.memory.get("context", {})
    
    def _load_memory(self) -> Dict:
        """Load memory from disk."""
        if self.memory_file.exists():
            try:
                with open(self.memory_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load memory: {e}")
        return {"documents": {}, "images": {}, "facts": [], "context": {}}
    
    def _save_memory(self):
        """Persist memory to disk."""
        self.memory = {
            "documents": self.documents,
            "images": self.images,
            "facts": self.facts,
            "context": self.context,
            "last_updated": datetime.now().isoformat()
        }
        try:
            with open(self.memory_file, 'w') as f:
                json.dump(self.memory, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")

    def get_stats(self) -> Dict:
        """Get statistics about the knowledge base."""
        return {
            "documents": len(self.documents),
            "images": len(self.images),
            "facts": len(self.facts),
            "chunks": 0,
            "last_updated": self.memory.get("last_updated", "Never")
        }

    def reindex(self):
        """Re-index the knowledge base (placeholder)."""
        self._save_memory()
        return True
    
    def analyze_image(self, image_data: bytes, filename: str, replicate_api) -> Dict:
        """
        Analyze an uploaded image using vision AI.
        Returns description, objects detected, colors, and more.
        """
        try:
            # Save image
            image_id = str(uuid.uuid4())[:8]
            image_path = self.images_dir / f"{image_id}_{filename}"
            with open(image_path, 'wb') as f:
                f.write(image_data)
            
            # Encode for API
            image_b64 = base64.b64encode(image_data).decode()
            
            # Use vision model to analyze
            analysis_prompt = """Analyze this image in detail. Provide:
1. **Description**: What does the image show?
2. **Objects**: List main objects/elements visible
3. **Colors**: Dominant colors in the image
4. **Style**: Art style, photography type, or design style
5. **Text**: Any text visible in the image
6. **Mood**: The emotional feeling or atmosphere
7. **Use Cases**: What could this image be used for (marketing, product, social media, etc.)

Be specific and detailed."""

            # Call vision API
            analysis_result = replicate_api.analyze_image(image_b64, analysis_prompt)
            
            # Store in knowledge base
            image_record = {
                "id": image_id,
                "filename": filename,
                "path": str(image_path),
                "analysis": analysis_result,
                "uploaded_at": datetime.now().isoformat(),
                "size_bytes": len(image_data)
            }
            self.images[image_id] = image_record
            self._save_memory()
            
            return {
                "success": True,
                "image_id": image_id,
                "analysis": analysis_result,
                "message": f"✅ Image analyzed and saved to knowledge base with ID: {image_id}"
            }
            
        except Exception as e:
            logger.error(f"Image analysis failed: {e}")
            return {"success": False, "error": str(e)}
    
    def read_document(self, file_data: bytes, filename: str, replicate_api) -> Dict:
        """
        Read and parse a document (PDF, DOCX, TXT, etc.).
        Extracts content and adds to knowledge base.
        """
        try:
            doc_id = str(uuid.uuid4())[:8]
            doc_path = self.documents_dir / f"{doc_id}_{filename}"
            with open(doc_path, 'wb') as f:
                f.write(file_data)
            
            content = ""
            file_ext = filename.lower().split('.')[-1]
            
            # Extract text based on file type
            if file_ext == 'txt':
                content = file_data.decode('utf-8', errors='ignore')
            
            elif file_ext == 'pdf':
                try:
                    import PyPDF2
                    pdf_reader = PyPDF2.PdfReader(BytesIO(file_data))
                    for page in pdf_reader.pages:
                        content += page.extract_text() + "\n"
                except ImportError:
                    content = "[PDF content - PyPDF2 not installed]"
            
            elif file_ext in ['doc', 'docx']:
                try:
                    from docx import Document
                    doc = Document(BytesIO(file_data))
                    for para in doc.paragraphs:
                        content += para.text + "\n"
                except ImportError:
                    content = "[DOCX content - python-docx not installed]"
            
            elif file_ext in ['json']:
                content = file_data.decode('utf-8', errors='ignore')
                try:
                    parsed = json.loads(content)
                    content = json.dumps(parsed, indent=2)
                except:
                    pass
            
            elif file_ext in ['csv']:
                content = file_data.decode('utf-8', errors='ignore')
            
            elif file_ext in ['md', 'markdown']:
                content = file_data.decode('utf-8', errors='ignore')
            
            else:
                try:
                    content = file_data.decode('utf-8', errors='ignore')
                except:
                    content = f"[Binary file - cannot extract text]"
            
            # Summarize if content is long
            summary = content[:500] if len(content) > 500 else content
            if len(content) > 500:
                summary_prompt = f"""Summarize this document content in 3-5 bullet points:

{content[:3000]}

Provide a concise summary of the key information."""
                summary = replicate_api.generate_text(summary_prompt, max_tokens=500, temperature=0.3)
            
            # Store in knowledge base
            doc_record = {
                "id": doc_id,
                "filename": filename,
                "path": str(doc_path),
                "content": content[:50000],
                "summary": summary,
                "uploaded_at": datetime.now().isoformat(),
                "size_bytes": len(file_data),
                "file_type": file_ext
            }
            self.documents[doc_id] = doc_record
            self._save_memory()
            
            return {
                "success": True,
                "document_id": doc_id,
                "summary": summary,
                "content_length": len(content),
                "message": f"✅ Document read and added to knowledge base with ID: {doc_id}"
            }
            
        except Exception as e:
            logger.error(f"Document reading failed: {e}")
            return {"success": False, "error": str(e)}
    
    def add_fact(self, fact: str, category: str = "general") -> Dict:
        """Add a fact or piece of information to memory."""
        fact_record = {
            "id": str(uuid.uuid4())[:8],
            "fact": fact,
            "category": category,
            "added_at": datetime.now().isoformat()
        }
        self.facts.append(fact_record)
        self._save_memory()
        return {"success": True, "message": f"✅ Fact added to memory: {fact[:50]}..."}
    
    def recall(self, query: str, replicate_api) -> Dict:
        """Search knowledge base for relevant information."""
        results = {
            "facts": [],
            "documents": [],
            "images": []
        }
        
        query_lower = query.lower()
        
        # Search facts
        for fact in self.facts:
            if query_lower in fact.get("fact", "").lower():
                results["facts"].append(fact)
        
        # Search documents
        for doc_id, doc in self.documents.items():
            if (query_lower in doc.get("filename", "").lower() or
                query_lower in doc.get("summary", "").lower() or
                query_lower in doc.get("content", "")[:5000].lower()):
                results["documents"].append({
                    "id": doc_id,
                    "filename": doc["filename"],
                    "summary": doc.get("summary", "")[:300]
                })
        
        # Search images
        for img_id, img in self.images.items():
            analysis = img.get("analysis", "")
            if isinstance(analysis, str) and query_lower in analysis.lower():
                results["images"].append({
                    "id": img_id,
                    "filename": img["filename"],
                    "analysis": analysis[:300]
                })
        
        return {
            "success": True,
            "query": query,
            "results": results,
            "total_matches": len(results["facts"]) + len(results["documents"]) + len(results["images"])
        }
    
    def get_context_summary(self) -> str:
        """Get a summary of all knowledge for context injection."""
        summary_parts = []
        
        if self.facts:
            summary_parts.append(f"**Known Facts ({len(self.facts)}):**")
            for fact in self.facts[-5:]:
                summary_parts.append(f"- {fact['fact'][:100]}")
        
        if self.documents:
            summary_parts.append(f"\n**Documents ({len(self.documents)}):**")
            for doc_id, doc in list(self.documents.items())[-3:]:
                summary_parts.append(f"- {doc['filename']}: {doc.get('summary', '')[:100]}")
        
        if self.images:
            summary_parts.append(f"\n**Images ({len(self.images)}):**")
            for img_id, img in list(self.images.items())[-3:]:
                summary_parts.append(f"- {img['filename']}: {str(img.get('analysis', ''))[:100]}")
        
        return "\n".join(summary_parts) if summary_parts else "No knowledge stored yet."
    
    def clear_memory(self, category: str = "all") -> Dict:
        """Clear knowledge base (all or specific category)."""
        if category == "all" or category == "facts":
            self.facts = []
        if category == "all" or category == "documents":
            self.documents = {}
        if category == "all" or category == "images":
            self.images = {}
        self._save_memory()
        return {"success": True, "message": f"✅ Cleared {category} from knowledge base"}


# ============================================================================
# APP STATE AWARENESS - Real-time monitoring of app state
# ============================================================================
class OttoAppAwareness:
    """
    Monitors and tracks the current state of the app.
    Otto uses this to understand what's happening in the app.
    """
    
    @staticmethod
    def get_current_state() -> Dict[str, Any]:
        """Get comprehensive current app state."""
        state = {
            "timestamp": datetime.now().isoformat(),
            "current_page": st.session_state.get("current_page", "Unknown"),
            "user_activity": {}
        }
        
        if "nav_selection" in st.session_state:
            state["navigation"] = st.session_state.nav_selection
        
        state["sidebar_tab"] = st.session_state.get("sidebar_tab", 0)
        
        if "otto_messages" in st.session_state:
            state["chat_messages_count"] = len(st.session_state.otto_messages)
        
        state["campaigns"] = {
            "active_campaign": st.session_state.get("current_campaign_name", None),
            "generated_images_count": len(st.session_state.get("generated_images", [])),
            "generated_videos_count": len(st.session_state.get("generated_videos", []))
        }
        
        state["integrations"] = {
            "printify_connected": "printify_api_key" in st.session_state or os.getenv("PRINTIFY_API_KEY"),
            "shopify_connected": "shopify_store_url" in st.session_state or os.getenv("SHOPIFY_STORE_URL"),
            "youtube_connected": st.session_state.get("youtube_authenticated", False),
            "replicate_connected": "replicate_api_key" in st.session_state or os.getenv("REPLICATE_API_TOKEN")
        }
        
        if "brand_name" in st.session_state:
            state["brand"] = {
                "name": st.session_state.get("brand_name", ""),
                "tagline": st.session_state.get("brand_tagline", ""),
                "colors": st.session_state.get("brand_colors", []),
                "voice": st.session_state.get("brand_voice", "")
            }
        
        if "product_designs" in st.session_state:
            state["recent_designs"] = len(st.session_state.product_designs)
        
        if "printify_products" in st.session_state:
            state["printify_products_count"] = len(st.session_state.printify_products)
        
        state["content_pipeline"] = {
            "scheduled_posts": len(st.session_state.get("scheduled_posts", [])),
            "draft_content": len(st.session_state.get("draft_content", []))
        }
        
        return state
    
    @staticmethod
    def get_state_summary() -> str:
        """Get a human-readable summary of current state."""
        state = OttoAppAwareness.get_current_state()
        
        summary_parts = [
            f"📍 **Current Page:** {state.get('current_page', 'Main Dashboard')}",
            f"🔗 **Integrations:** "
        ]
        
        integrations = state.get("integrations", {})
        connected = []
        if integrations.get("printify_connected"):
            connected.append("Printify")
        if integrations.get("shopify_connected"):
            connected.append("Shopify")
        if integrations.get("youtube_connected"):
            connected.append("YouTube")
        summary_parts[-1] += ", ".join(connected) if connected else "None connected"
        
        campaigns = state.get("campaigns", {})
        if campaigns.get("active_campaign"):
            summary_parts.append(f"🎯 **Active Campaign:** {campaigns['active_campaign']}")
        
        summary_parts.append(f"🖼️ **Generated Images:** {campaigns.get('generated_images_count', 0)}")
        summary_parts.append(f"🎬 **Generated Videos:** {campaigns.get('generated_videos_count', 0)}")
        
        brand = state.get("brand", {})
        if brand.get("name"):
            summary_parts.append(f"🏷️ **Brand:** {brand['name']}")
        
        return "\n".join(summary_parts)
    
    @staticmethod
    def track_action(action: str, details: Dict = None):
        """Track user actions for context."""
        if "otto_action_history" not in st.session_state:
            st.session_state.otto_action_history = []
        
        st.session_state.otto_action_history.append({
            "action": action,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        })
        
        st.session_state.otto_action_history = st.session_state.otto_action_history[-50:]


# Global knowledge base instance
_knowledge_base: Optional[OttoKnowledgeBase] = None

def get_knowledge_base() -> OttoKnowledgeBase:
    """Get or create the global knowledge base."""
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = OttoKnowledgeBase()
    return _knowledge_base


# ============================================================================
# PERFORMANCE CONFIGURATION
# ============================================================================
@dataclass
class OttoPerformanceConfig:
    """Tunable performance settings for Otto Engine"""
    max_concurrent_tasks: int = 4
    api_timeout: int = 60
    cache_ttl: int = 3600
    
    max_retries: int = 3
    retry_base_delay: float = 1.0
    retry_max_delay: float = 30.0
    
    default_temperature: float = 0.3
    max_tokens_analysis: int = 1500
    max_tokens_content: int = 1200
    
    enable_parallel_steps: bool = True
    parallel_batch_size: int = 3


OTTO_CONFIG = OttoPerformanceConfig()


# ============================================================================
# REQUEST CACHE FOR REPEATED QUERIES
# ============================================================================
class RequestCache:
    """Simple in-memory cache for repeated requests."""
    def __init__(self, ttl: int = 3600):
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self.ttl = ttl
    
    def _hash_key(self, request: str) -> str:
        return hashlib.md5(request.lower().strip().encode()).hexdigest()
    
    def get(self, request: str) -> Optional[Any]:
        key = self._hash_key(request)
        if key in self._cache:
            value, timestamp = self._cache[key]
            if time.time() - timestamp < self.ttl:
                logger.info(f"🎯 Cache hit for request")
                return value
            del self._cache[key]
        return None
    
    def set(self, request: str, value: Any):
        key = self._hash_key(request)
        self._cache[key] = (value, time.time())
    
    def clear(self):
        self._cache.clear()


_request_cache = RequestCache(ttl=OTTO_CONFIG.cache_ttl)


# ============================================================================
# TASK WORKFLOW STRUCTURES
# ============================================================================
class TaskType(Enum):
    """Types of tasks Otto can execute"""
    IMAGE_GENERATION = "image_generation"
    VIDEO_GENERATION = "video_generation"
    MUSIC_GENERATION = "music_generation"
    CONTENT_CREATION = "content_creation"
    DESIGN_MOCKUP = "design_mockup"
    PRODUCT_UPLOAD = "product_upload"
    SOCIAL_POST = "social_post"
    EMAIL_CAMPAIGN = "email_campaign"
    RESEARCH = "research"
    ANALYSIS = "analysis"
    BATCH_OPERATION = "batch_operation"


@dataclass
class TaskStep:
    """Individual step in a task workflow"""
    step_id: str
    action: str
    parameters: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"  # pending, running, completed, failed
    result: Any = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None


@dataclass
class TaskPlan:
    """Complete task workflow plan"""
    task_id: str
    task_type: TaskType
    name: str
    description: str
    steps: List[TaskStep]
    priority: int = 1
    max_retries: int = 3
    timeout: int = 3600
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "created"  # created, queued, running, completed, failed


__all__ = [
    'OttoKnowledgeBase',
    'OttoAppAwareness',
    'OttoPerformanceConfig',
    'RequestCache',
    'TaskType',
    'TaskStep',
    'TaskPlan',
    'OTTO_CONFIG',
    'get_knowledge_base',
]
