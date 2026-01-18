"""
SUPERCHARGED Intelligent Chat Assistant with Multi-Agent Orchestration
===============================================================================
Ultra-powerful AI brain that can execute extraordinarily complex workflows
by chaining together multiple specialized agents and automated pipelines.

CAPABILITIES:
- Multi-agent orchestration with parallel execution
- Complex workflow automation (design → mockup → video → publish → promote)
- Intelligent task decomposition and chaining
- Browser automation with credential management
- Full platform control via natural language
- Creative problem-solving with multiple AI models

Now integrated with:
- OttoEngine for advanced planning and execution
- EnhancedBrowserService for stable browser automation
"""

from abp_imports_common import (
    st, os, json, logging, asyncio, uuid, Path, Dict, List, Any, Optional, Tuple,
    datetime, ThreadPoolExecutor, setup_logger
)

# Import modularized components
from app.services.chat_assistant_history import (
    ChatHistoryManager, get_chat_history_manager, render_chat_history_sidebar
)
from app.services.chat_assistant_tasks import (
    TaskQueueItem, AutonomousTaskQueue
)

logger = setup_logger(__name__)

# Re-export for backward compatibility
__all__ = [
    'ChatHistoryManager',
    'get_chat_history_manager', 
    'render_chat_history_sidebar',
    'TaskQueueItem',
    'AutonomousTaskQueue',
]


# Lazy imports for heavy modules
_replicate_api = None
_chat_action_executor = None
_otto_engine_module = None
_credential_manager = None

def _get_replicate_api():
    """Lazy load ReplicateAPI."""
    global _replicate_api
    if _replicate_api is None:
        from app.services.api_service import ReplicateAPI
        _replicate_api = ReplicateAPI
    return _replicate_api

def _get_chat_action_executor():
    """Lazy load ChatActionExecutor."""
    global _chat_action_executor
    if _chat_action_executor is None:
        from chat_actions import ChatActionExecutor
        _chat_action_executor = ChatActionExecutor
    return _chat_action_executor

def _get_credential_manager():
    """Lazy load credential manager."""
    global _credential_manager
    if _credential_manager is None:
        from credential_manager import get_credential_manager
        _credential_manager = get_credential_manager
    return _credential_manager

# Import new Otto Engine - lazy loaded
OTTO_ENGINE_AVAILABLE = True  # Assume available, will check on first use
_otto_loaded = False

def _get_otto_engine():
    """Lazy load Otto Engine components."""
    global _otto_engine_module, OTTO_ENGINE_AVAILABLE, _otto_loaded
    if not _otto_loaded:
        try:
            from app.services.otto_engine import OttoEngine, TaskPlan, render_otto_chat, get_knowledge_base, OttoKnowledgeBase
            _otto_engine_module = {
                'OttoEngine': OttoEngine,
                'TaskPlan': TaskPlan,
                'render_otto_chat': render_otto_chat,
                'get_knowledge_base': get_knowledge_base,
                'OttoKnowledgeBase': OttoKnowledgeBase
            }
            OTTO_ENGINE_AVAILABLE = True
        except ImportError:
            OTTO_ENGINE_AVAILABLE = False
            _otto_engine_module = {}
        _otto_loaded = True
    return _otto_engine_module

# Import enhanced browser service - lazy
ENHANCED_BROWSER_AVAILABLE = True  # Assume available, will check on first use
_browser_loaded = False
_browser_module = None

def _get_browser_service():
    """Lazy load browser service."""
    global _browser_module, ENHANCED_BROWSER_AVAILABLE, _browser_loaded
    if not _browser_loaded:
        try:
            from automation.enhanced_browser import EnhancedBrowserService, get_browser_service, BrowserResult
            _browser_module = {
                'EnhancedBrowserService': EnhancedBrowserService,
                'get_browser_service': get_browser_service,
                'BrowserResult': BrowserResult
            }
            ENHANCED_BROWSER_AVAILABLE = True
        except ImportError:
            ENHANCED_BROWSER_AVAILABLE = False
            _browser_module = {}
        _browser_loaded = True
    return _browser_module

logger = logging.getLogger(__name__)


from modules.orchestrator import MultiAgentOrchestrator


class ChatAssistant:
    """
    AI-powered chat assistant with knowledge of all app features,
    session state, files, campaigns, and Replicate API capabilities.
    
    NOW INCLUDES: 
    - Browser-Use integration for sophisticated web automation!
    - OttoEngine for advanced multi-step task execution
    - EnhancedBrowserService for stable browser automation
    """
    
    def __init__(self, replicate_api_key: str, printify_api=None, shopify_api=None, youtube_api=None):
        """Initialize chat assistant with all API connections."""
        self.api_key = replicate_api_key
        # Use same ReplicateAPI class as rest of platform (lazy loaded)
        ReplicateAPI = _get_replicate_api()
        self.replicate = ReplicateAPI(api_token=replicate_api_key)
        # Initialize action executor for triggering platform functions (lazy loaded)
        ChatActionExecutor = _get_chat_action_executor()
        self.action_executor = ChatActionExecutor(self.replicate)
        # Initialize credential manager for automatic login (lazy loaded)
        get_credential_manager = _get_credential_manager()
        self.credential_manager = get_credential_manager()
        
        # Store API references for service sync
        self.printify = printify_api
        self.shopify = shopify_api
        self.youtube = youtube_api
        
        # Initialize Otto Engine if available (lazy loaded)
        self.otto_engine = None
        otto_module = _get_otto_engine()
        if OTTO_ENGINE_AVAILABLE and otto_module:
            try:
                OttoEngine = otto_module['OttoEngine']
                self.otto_engine = OttoEngine(
                    replicate_api=self.replicate,
                    printify_api=printify_api,
                    shopify_api=shopify_api,
                    youtube_api=youtube_api
                )
                logger.info("✅ Otto Engine initialized")
            except Exception as e:
                logger.warning(f"⚠️ Could not initialize Otto Engine: {e}")
        
        # Initialize enhanced browser service (lazy loaded)
        self.enhanced_browser = None
        browser_module = _get_browser_service()
        if ENHANCED_BROWSER_AVAILABLE and browser_module:
            try:
                get_browser_service = browser_module['get_browser_service']
                self.enhanced_browser = get_browser_service()
                logger.info("✅ Enhanced Browser Service initialized")
            except Exception as e:
                logger.warning(f"⚠️ Could not initialize Enhanced Browser: {e}")
        
        # Initialize browser-use capabilities (legacy)
        self.browser_agent = None
        self.anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        
        # Check if browser-use is available
        try:
            from browser_use import Agent, Browser, BrowserConfig
            from langchain_anthropic import ChatAnthropic
            from pydantic import SecretStr
            self.browser_use_available = bool(self.anthropic_key)
            if self.browser_use_available:
                logger.info(f"✅ Browser-Use available: True (Anthropic key found)")
            else:
                logger.warning(f"⚠️ Browser-Use disabled: ANTHROPIC_API_KEY not found in .env")
        except ImportError as e:
            self.browser_use_available = False
            logger.warning(f"⚠️ Browser-Use not available: {e}")
            logger.warning(f"💡 Install: pip install browser-use langchain-anthropic playwright")
            logger.warning(f"💡 Then run: playwright install")
    
    def _get_default_otto_prompt(self, credential_context: str, knowledge_base: str) -> str:
        """Get the default Otto system prompt."""
        return f"""You are Otto Mate, a friendly and capable AI assistant for a marketing automation platform.

IMPORTANT RULES:
1. You are in CHAT MODE - for answering questions and having conversations
2. DO NOT pretend to generate images, videos, or execute actions
3. DO NOT make up fake download links, base64 data, or pretend outputs
4. If the user wants to CREATE something, tell them to rephrase as a command like:
   - "Create a mockup for..."
   - "Generate a design for..."
   - "Make a video about..."
5. You CAN explain how the platform works, answer questions, and provide guidance

WHAT YOU CAN DO IN CHAT MODE:
- Answer questions about campaigns, files, and platform features
- Explain how to use different features
- Provide creative suggestions and ideas
- Help with planning and strategy
- Give information about available models and capabilities

WHAT YOU CANNOT DO IN CHAT MODE:
- Generate actual images (user needs to ask with action words)
- Create real videos or content
- Make fake/hallucinated outputs
- Pretend to upload or publish things

If user asks you to create/generate/make something, respond with:
"I'd be happy to create that for you! Just say something like 'Create [your request]' or 'Generate [your request]' and I'll execute it with our AI agents."

{credential_context}

📊 PLATFORM STATUS:
{knowledge_base}
"""
        
    def build_knowledge_base(self) -> str:
        """
        Build comprehensive knowledge base from session state and filesystem.
        Returns formatted context string for the AI.
        """
        knowledge = []
        
        # Session state overview
        knowledge.append("=== CURRENT SESSION STATE ===")
        if 'campaigns' in st.session_state:
            campaigns = st.session_state.get('campaigns', [])
            knowledge.append(f"Active Campaigns: {len(campaigns)}")
            for campaign in campaigns[-5:]:  # Last 5 campaigns
                knowledge.append(f"  - {campaign.get('name', 'Unknown')}")
        
        # Available files
        knowledge.append("\n=== AVAILABLE FILES ===")
        campaigns_dir = Path("campaigns")
        if campaigns_dir.exists():
            all_campaigns = list(campaigns_dir.iterdir())
            knowledge.append(f"Total Campaigns: {len(all_campaigns)}")
            
            # Get recent campaigns
            recent_campaigns = sorted(all_campaigns, key=lambda x: x.stat().st_mtime, reverse=True)[:5]
            for campaign_path in recent_campaigns:
                if campaign_path.is_dir():
                    knowledge.append(f"\nCampaign: {campaign_path.name}")
                    
                    # List contents
                    for subdir in ['products', 'videos', 'social_media', 'blog_posts']:
                        subdir_path = campaign_path / subdir
                        if subdir_path.exists():
                            files = list(subdir_path.glob('*'))
                            knowledge.append(f"  {subdir}: {len(files)} files")
        
        # Replicate API capabilities
        knowledge.append("\n=== AVAILABLE REPLICATE MODELS ===")
        knowledge.append("Image Generation:")
        knowledge.append("  - prunaai/flux-fast: High-quality product designs")
        knowledge.append("Video Generation:")
        knowledge.append("  - kwaivgi/kling-v2.5-turbo-pro: Professional video generation")
        knowledge.append("Ad Generation:")
        knowledge.append("  - pipeline-examples/ads-for-products:latest: Static product ads")
        knowledge.append("  - pipeline-examples/video-ads:latest: Animated video ads")
        knowledge.append("  - loolau/flux-static-ads:latest: Brand-focused static ads")
        knowledge.append("  - subhash25rawat/logo-in-context:latest: Logo placement")
        knowledge.append("Audio:")
        knowledge.append("  - minimax/speech-02-hd: Text-to-speech voiceovers")
        
        # Platform features
        knowledge.append("\n=== PLATFORM FEATURES ===")
        knowledge.append("- Campaign Generation: Create full marketing campaigns")
        knowledge.append("- Printify Integration: Upload designs, create products, publish")
        knowledge.append("- Shopify Integration: Publish blog posts with images")
        knowledge.append("- YouTube Integration: Upload videos with OAuth")
        knowledge.append("- Social Media Ads: Generate static and video ads from mockups")
        knowledge.append("- Background Removal: BiRefNet and rembg models")
        knowledge.append("- Video Production: Multi-phase with voiceover and music")
        
        # Codebase structure
        knowledge.append("\n=== CODEBASE STRUCTURE ===")
        knowledge.append("Main Application:")
        knowledge.append("  - autonomous_business_platform.py: Main Streamlit app with 8 horizontal tabs")
        knowledge.append("    * Tab 0: Dashboard - Quick campaign launcher")
        knowledge.append("    * Tab 1: Campaign Creator - Full 12-step campaign generation")
        knowledge.append("    * Tab 2: Agent Builder - Visual workflow automation")
        knowledge.append("    * Tab 3: Product Studio - Design generation with mockups")
        knowledge.append("    * Tab 4: Content Generator - Blog posts and social media")
        knowledge.append("    * Tab 5: Video Producer - Commercial and educational videos")
        knowledge.append("    * Tab 6: Analytics - Performance tracking")
        knowledge.append("    * Tab 7: Settings - API keys and integrations")
        knowledge.append("  - Sidebar: 5 tabs (Chat, Session, Stats, About, Commands)")
        
        knowledge.append("\nCore Services:")
        knowledge.append("  - api_service.py: ReplicateAPI unified client")
        knowledge.append("    * generate_image(), generate_video(), generate_text()")
        knowledge.append("    * ControlNet methods: generate_canny_map(), generate_depth_map()")
        knowledge.append("    * generate_multi_controlnet_image(), apply_style_control()")
        knowledge.append("  - advanced_video_producer.py: 4-phase video production")
        knowledge.append("    * generate_product_ad_script(), generate_video_segments()")
        knowledge.append("    * generate_voiceover(), generate_background_music()")
        knowledge.append("    * assemble_final_video()")
        knowledge.append("  - campaign_generator_service.py: 12-step campaign workflow")
        knowledge.append("    * EnhancedCampaignGenerator with magic-marketer patterns")
        knowledge.append("  - chat_assistant.py: This AI assistant with knowledge base")
        knowledge.append("  - session_manager.py: Auto-save/load session persistence")
        
        knowledge.append("\nIntegration Services:")
        knowledge.append("  - printify.py: PrintifyAPI - products, blueprints, upload")
        knowledge.append("  - shopify_service.py: ShopifyAPI - blog publishing")
        knowledge.append("  - youtube_upload_service.py: YouTubeUploadService - OAuth + upload")
        knowledge.append("  - social_media_ad_service.py: SocialMediaAdService - ads generation")
        knowledge.append("  - background_removal_service.py: BackgroundRemovalService")
        
        knowledge.append("\nHelper Modules:")
        knowledge.append("  - unified_agent_builder.py: Node-based workflow builder")
        knowledge.append("  - image_manager.py: Image processing utilities")
        knowledge.append("  - blog_generator.py: Blog post generation")
        
        knowledge.append("\nKey Functions & Where to Find Them:")
        knowledge.append("  - Campaign generation: autonomous_business_platform.py Tab 0 (lines ~850-1900)")
        knowledge.append("  - Video production: autonomous_business_platform.py Tab 5 (lines ~2850-3200)")
        knowledge.append("  - Product mockups: Printify integration (lines ~1250-1400)")
        knowledge.append("  - ControlNet usage: api_service.py (lines ~407-590)")
        knowledge.append("  - Background removal: autonomous_business_platform.py (lines ~1100-1250)")
        knowledge.append("  - Session save/load: session_manager.py initialize_session_persistence()")
        
        knowledge.append("\nConfiguration:")
        knowledge.append("  - .env file: REPLICATE_API_TOKEN, PRINTIFY_API_KEY, SHOPIFY credentials")
        knowledge.append("  - client_secret.json: YouTube OAuth credentials")
        knowledge.append("  - token.pickle: Saved YouTube authentication")
        
        return "\n".join(knowledge)
    
    def parse_command(self, user_input: str) -> Optional[Dict[str, Any]]:
        """
        Parse user input for specific commands.
        Returns command dict or None if not a command.
        """
        commands = {
            '/campaign': 'create_campaign',
            '/image': 'generate_image',
            '/video': 'generate_video',
            '/ads': 'generate_ads',
            '/list': 'list_files',
            '/analyze': 'analyze_campaign',
            '/export': 'export_files',
            '/agent': 'run_agent',
            '/agents': 'list_agents',
            '/help': 'show_help',
            # Browser control commands
            '/browse': 'browser_navigate',
            '/click': 'browser_click',
            '/type': 'browser_type',
            '/gettext': 'browser_get_text',
            '/screenshot': 'browser_screenshot',
            '/find': 'browser_find_elements',
            '/closebrowser': 'browser_close'
        }
        
        for cmd, action in commands.items():
            if user_input.lower().startswith(cmd):
                args = user_input[len(cmd):].strip()
                return {'action': action, 'args': args}
        
        return None
    
    async def execute_browser_task(self, task: str) -> str:
        """
        Execute browser automation task using browser-use with Anthropic Claude.
        Automatically detects and uses stored credentials for login tasks.
        
        Args:
            task: Natural language description of what to do in the browser
            
        Returns:
            Result message from the browser automation
        """
        if not self.browser_use_available:
            return "❌ Browser automation not available. Please configure ANTHROPIC_API_KEY in .env file."
        
        try:
            from browser_use import Agent, Browser, BrowserConfig
            from langchain_anthropic import ChatAnthropic
            from pydantic import SecretStr
            
            logger.info(f"🤖 Executing browser task: {task}")
            
            # Detect if task involves a service we have credentials for
            task_lower = task.lower()
            service_detected = None
            service_keywords = {
                'twitter': ['twitter', 'tweet', 'x.com'],
                'facebook': ['facebook', 'fb'],
                'instagram': ['instagram', 'insta', 'ig'],
                'linkedin': ['linkedin'],
                'youtube': ['youtube', 'yt'],
                'google': ['google', 'gmail'],
                'tiktok': ['tiktok'],
                'reddit': ['reddit'],
                'pinterest': ['pinterest']
            }
            
            for service, keywords in service_keywords.items():
                if any(keyword in task_lower for keyword in keywords):
                    if self.credential_manager.has_credentials(service):
                        service_detected = service
                        logger.info(f"🔐 Detected {service} task - credentials available")
                        break
            
            # Build enhanced task with credential context
            enhanced_task = task
            if service_detected:
                cred_context = self.credential_manager.get_login_context(service_detected)
                enhanced_task = f"""{cred_context}

USER REQUEST: {task}

IMPORTANT: Use the credentials provided above to log in automatically. The user should NOT have to provide login information."""
            else:
                # Provide general credential context
                available_services = self.credential_manager.list_available_services()
                if available_services:
                    enhanced_task = f"""Available login credentials: {', '.join(available_services)}

USER REQUEST: {task}

If this task requires logging in to any service, check if credentials are available and use them automatically."""
            
            # Initialize LLM
            if not self.anthropic_key:
                return "❌ ANTHROPIC_API_KEY not configured"
                
            llm = ChatAnthropic(
                model_name="claude-sonnet-4-20250514",
                api_key=SecretStr(self.anthropic_key),
                temperature=0,
                timeout=100,
                stop=None
            )
            
            # Initialize browser
            browser = Browser(config=BrowserConfig(headless=False))
            
            try:
                # Create agent with enhanced task (includes credentials if detected)
                agent = Agent(
                    task=enhanced_task,
                    llm=llm,
                    browser=browser,
                )
                
                # Run the agent
                logger.info("🚀 Browser agent starting task...")
                history = await agent.run(max_steps=15)
                
                logger.info("✅ Browser task completed!")
                return f"✅ Browser automation completed successfully!\n\nTask: {task}\n\nThe browser agent has executed your request."
                
            finally:
                # Always close browser
                try:
                    await browser.close()
                except Exception as e:
                    logger.debug(f"Browser close error (non-critical): {e}")
                    
        except Exception as e:
            logger.error(f"Browser automation error: {e}")
            return f"❌ Browser automation failed: {str(e)}"
    
    async def process_message(self, user_message: str, chat_history: List[Dict]) -> str:
        """
        Process user message with full context and return AI response.
        NOW WITH:
        - Slash Command Processing for direct file/media generation
        - OttoEngine for complex multi-step task execution
        - Enhanced Browser Service for stable automation
        - Service sync (Printify, Shopify, YouTube)
        """
        try:
            msg_lower = user_message.lower()
            
            # ==========================================
            # SLASH COMMAND PROCESSING (HIGHEST PRIORITY)
            # ==========================================
            if user_message.strip().startswith('/'):
                logger.info(f"⚡ Processing slash command: {user_message[:50]}...")
                
                try:
                    from app.services.otto_engine import SlashCommandProcessor, get_slash_processor, SLASH_COMMANDS, AI_MODELS
                    
                    # Get the slash processor
                    slash_processor = get_slash_processor(self.replicate)
                    
                    # Parse the command
                    command, prompt = slash_processor.parse_command(user_message)
                    
                    # Check if it's a valid command
                    if command in SLASH_COMMANDS or command in AI_MODELS:
                        # Special handling for chain commands with progress
                        if command == 'chain':
                            st.info(f"🔗 Starting chain execution...")
                            
                            # Create progress container
                            progress_container = st.container()
                            
                            # Progress callback for real-time updates
                            def chain_progress(update):
                                with progress_container:
                                    step = update.get('step', 1)
                                    total = update.get('total', 1)
                                    name = update.get('name', 'Step')
                                    status = update.get('status', 'running')
                                    
                                    if status == 'running':
                                        st.info(f"⏳ [{step}/{total}] {name}")
                                    elif status == 'completed':
                                        st.success(f"✅ [{step}/{total}] {name}")
                                        # Show artifacts immediately
                                        result = update.get('result', {})
                                        if result.get('artifacts'):
                                            for artifact in result['artifacts']:
                                                art_type = artifact.get('type', '')
                                                url = artifact.get('url', '')
                                                if art_type == 'image' and url:
                                                    st.image(url, caption=f"Step {step} - Image", use_container_width=True)
                                                elif art_type == 'video' and url:
                                                    st.video(url)
                                                elif art_type == 'audio' and url:
                                                    st.audio(url)
                                    else:
                                        st.error(f"❌ [{step}/{total}] {name}")
                            
                            # Execute with progress callback
                            result = await slash_processor.execute(user_message, progress_callback=chain_progress)
                        else:
                            st.info(f"⚡ Executing `/{command}`...")
                            result = await slash_processor.execute(user_message)
                        
                        if result.get('success'):
                            # Format response based on result type
                            result_type = result.get('type', '')
                            
                            if result_type == 'help':
                                return result.get('message', '✅ Command executed')
                            
                            elif result_type == 'file':
                                filename = result.get('filename', 'file')
                                filepath = result.get('filepath', '')
                                content = result.get('content', '')
                                
                                response = f"✅ **Generated File:** `{filename}`\n\n"
                                
                                # Show preview for code/text files
                                if content:
                                    preview = content[:1500] + "..." if len(content) > 1500 else content
                                    ext = result.get('file_type', 'txt')
                                    response += f"```{ext}\n{preview}\n```\n\n"
                                
                                if filepath:
                                    response += f"📁 Saved to: `{filepath}`"
                                
                                return response
                            
                            elif result_type == 'media':
                                media_type = result.get('media_type', 'media')
                                artifacts = result.get('artifacts', [])
                                filepath = result.get('filepath', '')
                                
                                response = f"✅ **Generated {media_type.title()}**\n\n"
                                
                                # Display media artifacts
                                for artifact in artifacts:
                                    art_type = artifact.get('type', '')
                                    url = artifact.get('url', '')
                                    art_filepath = artifact.get('filepath', '')
                                    
                                    if art_type == 'image' and url:
                                        st.image(url, caption="Generated Image", use_container_width=True)
                                        response += f"🖼️ Image: {url}\n"
                                        if art_filepath:
                                            response += f"   📁 Saved: `{art_filepath}`\n"
                                    elif art_type == 'video' and url:
                                        st.video(url)
                                        response += f"🎬 Video: {url}\n"
                                        if art_filepath:
                                            response += f"   📁 Saved: `{art_filepath}`\n"
                                    elif art_type == 'audio' and url:
                                        st.audio(url)
                                        response += f"🎵 Audio: {url}\n"
                                        if art_filepath:
                                            response += f"   📁 Saved: `{art_filepath}`\n"
                                    elif art_type == '3d' and url:
                                        response += f"🎮 3D Model: [{url}]({url})\n"
                                        if art_filepath:
                                            response += f"   📁 Saved: `{art_filepath}`\n"
                                
                                if filepath:
                                    response += f"\n📂 Main file saved to: `{filepath}`"
                                
                                return response
                            
                            elif result_type == 'chain':
                                steps_completed = result.get('steps_completed', 0)
                                steps_total = result.get('steps_total', 0)
                                artifacts = result.get('artifacts', [])
                                chain_results = result.get('results', [])
                                
                                response = f"✅ **Chain Completed:** {steps_completed}/{steps_total} steps\n\n"
                                
                                # Show step-by-step results
                                for i, step_result in enumerate(chain_results):
                                    step_status = "✅" if step_result.get('success') else "❌"
                                    step_msg = step_result.get('message', f'Step {i+1}')
                                    response += f"{step_status} Step {i+1}: {step_msg}\n"
                                
                                response += "\n---\n\n**Generated Assets:**\n"
                                
                                # Display all artifacts with proper rendering
                                image_count = 0
                                video_count = 0
                                audio_count = 0
                                
                                for artifact in artifacts:
                                    art_type = artifact.get('type', '')
                                    url = artifact.get('url', '')
                                    art_filepath = artifact.get('filepath', '')
                                    
                                    if art_type == 'image' and url:
                                        image_count += 1
                                        st.image(url, caption=f"Generated Image {image_count}", use_container_width=True)
                                        response += f"🖼️ Image {image_count}: {url}\n"
                                        if art_filepath:
                                            response += f"   📁 Saved: `{art_filepath}`\n"
                                    elif art_type == 'video' and url:
                                        video_count += 1
                                        st.video(url)
                                        response += f"🎬 Video {video_count}: {url}\n"
                                        if art_filepath:
                                            response += f"   📁 Saved: `{art_filepath}`\n"
                                    elif art_type == 'audio' and url:
                                        audio_count += 1
                                        st.audio(url)
                                        response += f"🎵 Audio {audio_count}: {url}\n"
                                        if art_filepath:
                                            response += f"   📁 Saved: `{art_filepath}`\n"
                                    elif art_type == '3d' and url:
                                        response += f"🎮 3D Model: [{url}]({url})\n"
                                        if art_filepath:
                                            response += f"   📁 Saved: `{art_filepath}`\n"
                                
                                if not artifacts:
                                    response += "_No media artifacts generated_\n"
                                
                                return response
                            
                            else:
                                return result.get('message', '✅ Command executed successfully')
                        else:
                            error = result.get('error', 'Unknown error')
                            return f"❌ **Command failed:** {error}"
                    else:
                        # Not a recognized command, show help hint
                        return f"❓ Unknown command: `/{command}`\n\nType `/help` to see available commands."
                        
                except Exception as e:
                    logger.error(f"Slash command error: {e}")
                    import traceback
                    traceback.print_exc()
                    return f"❌ **Command error:** {str(e)}\n\nType `/help` for available commands."
            
            # Check if this is an ACTION request (user wants us to DO something)
            action_keywords = [
                # Design/Create actions
                'create', 'generate', 'make', 'design', 'build', 'produce',
                # Specific product requests
                'mockup', 'mock-up', 'mock up', 't-shirt', 'tshirt', 'hoodie', 
                'mug', 'poster', 'sticker', 'product',
                # Content requests  
                'image', 'picture', 'artwork', 'graphic', 'logo',
                'video', 'commercial', 'ad', 'advertisement',
                'write', 'blog', 'post', 'content', 'copy', 'script',
                # Workflow triggers
                'campaign', 'workflow', 'end to end', 'complete', 'full',
                # Action verbs
                'upload', 'publish', 'launch', 'start', 'run',
                # Service sync
                'sync', 'printify', 'shopify', 'youtube'
            ]
            
            # Check if user is requesting an actual action
            is_action_request = any(keyword in msg_lower for keyword in action_keywords)
            
            # Question patterns that should NOT trigger actions
            question_patterns = ['what is', 'how do', 'can you explain', 'tell me about', 
                                'what are', 'how does', 'why', 'when', '?']
            is_question = any(pattern in msg_lower for pattern in question_patterns)
            
            # ==========================================
            # USE OTTO ENGINE FOR COMPLEX ACTIONS
            # ==========================================
            if is_action_request and not is_question and self.otto_engine:
                logger.info(f"🧠 Using OttoEngine for: {user_message[:50]}...")
                
                # Show planning phase
                st.info("🧠 **Otto is analyzing your request...**")
                
                # Create execution plan
                plan = self.otto_engine.create_plan(user_message)
                
                # Show the plan
                st.markdown(f"**Plan:** {plan.summary}")
                st.markdown(f"**Steps:** {len(plan.steps)}")
                
                # Create progress display containers
                progress_container = st.empty()
                results_container = st.container()
                
                # Progress callback for real-time updates
                def progress_callback(update):
                    status_emoji = {"running": "⏳", "completed": "✅", "failed": "❌"}.get(update['status'], "⚪")
                    with progress_container:
                        st.markdown(f"{status_emoji} **Step {update['step']}/{update['total']}:** {update['name']}")
                    
                    # Show artifacts immediately
                    if update.get('result') and update['result'].get('artifacts'):
                        with results_container:
                            for artifact in update['result']['artifacts']:
                                if artifact.get('type') == 'image':
                                    st.image(artifact['url'], caption="Generated Image", use_container_width=True)
                                elif artifact.get('type') == 'video':
                                    st.video(artifact['url'])
                                elif artifact.get('type') == 'text':
                                    with st.expander("📝 Generated Content", expanded=True):
                                        st.markdown(artifact.get('content', '')[:500])
                
                # Execute the plan
                completed_plan = await self.otto_engine.execute_plan(plan, progress_callback)
                
                # Return final summary
                return completed_plan.final_result
            
            # ==========================================
            # USE ENHANCED BROWSER FOR WEB TASKS
            # ==========================================
            browser_keywords = ['browse', 'visit', 'go to', 'navigate to', 'open website', 
                              'click on', 'fill form', 'search for', 'post to twitter', 
                              'post to facebook', 'scrape', 'extract', 'tweet', 'share on']
            
            if any(keyword in msg_lower for keyword in browser_keywords):
                logger.info("🌐 Detected browser automation request")
                
                # Use enhanced browser service if available
                if self.enhanced_browser and self.enhanced_browser.is_available:
                    st.info("🌐 **Starting browser automation...**")
                    
                    result = await self.enhanced_browser.execute(
                        task=user_message,
                        max_steps=20,
                        retry_count=2
                    )
                    
                    if result.success:
                        response = f"✅ **Browser task completed!**\n\n"
                        response += f"**Steps taken:** {result.steps_taken}\n"
                        response += f"**Duration:** {result.duration_seconds:.1f}s\n\n"
                        response += f"**Result:** {result.result_text}"
                        
                        if result.downloaded_files:
                            response += f"\n\n**Downloaded files:** {', '.join(result.downloaded_files)}"
                        
                        return response
                    else:
                        return f"❌ **Browser task failed**\n\nErrors:\n" + "\n".join(result.errors)
                else:
                    # Fall back to legacy browser-use
                    return await self.execute_browser_task(user_message)
            
            # ==========================================
            # LEGACY ORCHESTRATOR FALLBACK
            # ==========================================
            if is_action_request and not is_question:
                logger.info(f"🎯 Action request (legacy orchestrator): {user_message[:50]}...")
                orchestrator = MultiAgentOrchestrator(self.replicate)
                context = {
                    'task': user_message,
                    'chat_history': [m.get('content', '') for m in chat_history[-5:]],
                }
                
                st.info(f"🚀 **Executing your request...**")
                results = await orchestrator.orchestrate(user_message, context)
                
                if results.get('final_summary'):
                    return results['final_summary']
                
                successful = sum(1 for s in results['steps'] if s['status'] == 'success')
                failed = sum(1 for s in results['steps'] if s['status'] == 'failed')
                
                if results['success']:
                    return f"✨ **Done!** {successful} steps completed successfully."
                else:
                    return f"⚠️ **Finished** with {failed} issue(s)."
            
            # Check for platform actions (campaign generation, publishing, etc.)
            action_dict = self.action_executor.parse_action_intent(user_message)
            if action_dict:
                logger.info(f"Detected action: {action_dict['action']}")
                result = await self.action_executor.execute_action(action_dict)
                return result
            
            # Check for direct commands
            command = self.parse_command(user_message)
            if command:
                return await self.execute_command(command)
            
            # Build knowledge base
            knowledge_base = self.build_knowledge_base()
            
            # Get credential context
            credential_context = self.credential_manager.get_full_context()
            
            # This is a CONVERSATIONAL response (not an action)
            # The LLM should answer questions, not pretend to execute actions
            
            # Check if a custom assistant is active
            active_assistant_id = st.session_state.get('active_assistant')
            
            if active_assistant_id and active_assistant_id != "otto_default":
                try:
                    from custom_assistants import PRESET_ASSISTANTS
                    if active_assistant_id in PRESET_ASSISTANTS:
                        preset = PRESET_ASSISTANTS[active_assistant_id]
                        # Use the custom assistant's system prompt
                        system_prompt = preset.get('system_prompt', '')
                        
                        # Add platform context
                        system_prompt += f"""

PLATFORM CONTEXT:
{credential_context}

📊 CURRENT STATUS:
{knowledge_base}
"""
                    else:
                        # Fallback to default Otto
                        system_prompt = self._get_default_otto_prompt(credential_context, knowledge_base)
                except ImportError:
                    # If custom_assistants not available, use default
                    system_prompt = self._get_default_otto_prompt(credential_context, knowledge_base)
            else:
                # Use default Otto prompt
                system_prompt = self._get_default_otto_prompt(credential_context, knowledge_base)
            
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add chat history (last 10 messages)
            for msg in chat_history[-10:]:
                messages.append(msg)
            
            # Add current message
            messages.append({"role": "user", "content": user_message})
            
            # Build conversation string
            conversation = ""
            for msg in messages[1:]:  # Skip system message, it's in system_prompt
                role = msg.get("role", "user")
                content = msg.get("content", "")
                conversation += f"{role.capitalize()}: {content}\n"
            
            # Use ReplicateAPI generate_text method (same as rest of platform)
            response_text = self.replicate.generate_text(
                prompt=conversation,
                max_tokens=500,
                temperature=0.7,
                top_p=0.9,
                system_prompt=system_prompt
            )
            
            return response_text.strip()
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return f"❌ Error: {str(e)}"
    
    async def execute_command(self, command: Dict[str, Any]) -> str:
        """Execute specific commands directly."""
        action = command['action']
        args = command['args']
        
        if action == 'show_help':
            return self.generate_help_text()
        
        elif action == 'list_files':
            return self.list_campaign_files(args)
        
        elif action == 'create_campaign':
            return "To create a campaign, please use the Campaign Generator tab or describe what you'd like to create."
        
        # Browser control commands
        elif action == 'browser_navigate':
            return self.handle_browser_navigate(args)
        
        elif action == 'browser_click':
            return self.handle_browser_click(args)
        
        elif action == 'browser_type':
            return self.handle_browser_type(args)
        
        elif action == 'browser_get_text':
            return self.handle_browser_get_text(args)
        
        elif action == 'browser_screenshot':
            return self.handle_browser_screenshot(args)
        
        elif action == 'browser_find_elements':
            return self.handle_browser_find_elements(args)
        
        elif action == 'browser_close':
            return self.handle_browser_close(args)
        
        elif action == 'generate_image':
            # Parse image request and generate
            try:
                if not args:
                    return "Please provide an image description. Example: `/image cyberpunk cityscape`"
                
                # Generate image using ReplicateAPI (use correct parameters)
                image_url = self.replicate.generate_image(
                    prompt=args,
                    width=1024,
                    height=1024,
                    aspect_ratio="1:1",
                    output_format="png",
                    output_quality=90
                )
                
                # Save reference in session state
                if 'chat_generated_images' not in st.session_state:
                    st.session_state.chat_generated_images = []
                st.session_state.chat_generated_images.append({
                    'prompt': args,
                    'url': image_url,
                    'timestamp': datetime.now().isoformat()
                })
                
                return f"✅ Image generated!\n\n![{args}]({image_url})\n\n**Prompt:** {args}"
            except Exception as e:
                logger.error(f"Image generation error: {e}")
                return f"❌ Image generation failed: {str(e)}"
        
        elif action == 'generate_video':
            return f"Video generation request: {args}\nPlease specify: concept, duration, and style."
        
        elif action == 'generate_ads':
            return f"Ad generation request: {args}\nPlease specify: product image, target audience, and ad style."
        
        elif action == 'analyze_campaign':
            return self.analyze_campaign(args)
        
        elif action == 'export_files':
            return "File export functionality - specify campaign name to export."
        
        elif action == 'run_agent':
            return self.run_agent_command(args)
        
        elif action == 'list_agents':
            return self.list_agents_command()
        
        return f"Command {action} not yet implemented."
    
    def generate_help_text(self) -> str:
        """Generate help documentation."""
        return """
### 🧠 SUPERCHARGED Chat Assistant

**🚀 MULTI-AGENT WORKFLOWS (NEW!)**
Just describe complex tasks naturally:
- "Create a complete t-shirt campaign from design to Printify listing"
- "End to end: design a poster, create video ad, and schedule social posts"
- "Full workflow: research trending pet products, design, and publish"
- "Automate everything for a new sneaker launch campaign"

Trigger words: `complete`, `end to end`, `full workflow`, `automate everything`, `start to finish`

**🤖 Specialized Agents:**
- 🎨 Designer - Images, designs, artwork
- ✍️ Writer - Copy, scripts, blog posts
- 🎬 Video Producer - Videos, animations
- 📢 Marketer - Ads, social content
- 📤 Publisher - Upload to all platforms
- 📊 Analyst - Performance insights
- 🔍 Researcher - Market trends
- ⚡ Optimizer - Quality enhancement

**Campaign Management:**
- `/campaign <concept>` - Create a new marketing campaign
- `/analyze <campaign_name>` - Analyze campaign performance
- `/list [campaign_name]` - List files in a campaign

**Content Generation:**
- `/image <description>` - Generate an image with Replicate
- `/video <description>` - Generate a video
- `/ads <product_name>` - Generate social media ads

**🌐 Browser Automation:**
Just describe what you want to do on any website!
- "Go to Twitter and post about my new product"
- "Search Amazon for competitor products"
- "Post my latest design to Instagram"
Credentials are used automatically when saved.

**Agent Builder:**
- `/agents` - List all saved agents
- `/agent <agent_name>` - Run a specific agent

**Examples:**
```
Create an entire dog-themed hoodie campaign with video
Complete workflow: design → mockup → video → publish to Shopify
End to end automation for a neon cat poster campaign
```
"""
    
    def list_campaign_files(self, campaign_name: str) -> str:
        """List files in a specific campaign or all campaigns."""
        campaigns_dir = Path("campaigns")
        
        if not campaigns_dir.exists():
            return "No campaigns found."
        
        if campaign_name:
            # List specific campaign
            matching = list(campaigns_dir.glob(f"*{campaign_name}*"))
            if not matching:
                return f"No campaign found matching '{campaign_name}'"
            
            campaign_path = matching[0]
            files_list = []
            
            for item in campaign_path.rglob('*'):
                if item.is_file():
                    files_list.append(str(item.relative_to(campaign_path)))
            
            return f"**{campaign_path.name}**\n" + "\n".join(f"  - {f}" for f in files_list[:20])
        
        else:
            # List all campaigns
            campaigns = sorted(campaigns_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)
            campaign_list = []
            
            for camp in campaigns[:10]:
                if camp.is_dir():
                    file_count = len(list(camp.rglob('*')))
                    campaign_list.append(f"  - {camp.name} ({file_count} files)")
            
            return "**Recent Campaigns:**\n" + "\n".join(campaign_list)
    
    def analyze_campaign(self, campaign_name: str) -> str:
        """Analyze a campaign's contents and performance."""
        campaigns_dir = Path("campaigns")
        
        if not campaign_name:
            return "Please specify a campaign name to analyze."
        
        matching = list(campaigns_dir.glob(f"*{campaign_name}*"))
        if not matching:
            return f"No campaign found matching '{campaign_name}'"
        
        campaign_path = matching[0]
        analysis = [f"### Campaign Analysis: {campaign_path.name}\n"]
        
        # Count assets by type
        products = len(list((campaign_path / "products").glob('*'))) if (campaign_path / "products").exists() else 0
        videos = len(list((campaign_path / "videos").glob('*.mp4'))) if (campaign_path / "videos").exists() else 0
        social = len(list((campaign_path / "social_media").glob('*'))) if (campaign_path / "social_media").exists() else 0
        blogs = len(list((campaign_path / "blog_posts").glob('*'))) if (campaign_path / "blog_posts").exists() else 0
        
        analysis.append(f"**Products:** {products}")
        analysis.append(f"**Videos:** {videos}")
        analysis.append(f"**Social Media Assets:** {social}")
        analysis.append(f"**Blog Posts:** {blogs}")
        
        # Read campaign metadata if available
        metadata_path = campaign_path / "campaign_metadata.json"
        if metadata_path.exists():
            try:
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                analysis.append(f"\n**Created:** {metadata.get('timestamp', 'Unknown')}")
                analysis.append(f"**Concept:** {metadata.get('concept', 'Unknown')}")
            except:
                pass
        
        return "\n".join(analysis)
    
    def list_agents_command(self) -> str:
        """List all saved agents."""
        from agent_builder import Agent
        
        saved_agents = Agent.list_saved()
        
        if not saved_agents:
            return "No agents found. Create one in the Agent Builder tab!"
        
        agent_list = ["### 🤖 Available Agents\n"]
        
        for agent in saved_agents:
            agent_list.append(f"**{agent.name}**")
            agent_list.append(f"  - {agent.description}")
            agent_list.append(f"  - Steps: {len(agent.workflow_steps)}")
            agent_list.append(f"  - Use: `/agent {agent.name}`\n")
        
        return "\n".join(agent_list)
    
    def run_agent_command(self, agent_name: str) -> str:
        """Run a specific agent."""
        from agent_builder import Agent
        
        if not agent_name:
            return "Please specify an agent name. Use `/agents` to see available agents."
        
        saved_agents = Agent.list_saved()
        matching_agent = None
        
        for agent in saved_agents:
            if agent_name.lower() in agent.name.lower():
                matching_agent = agent
                break
        
        if not matching_agent:
            return f"No agent found matching '{agent_name}'. Use `/agents` to see available agents."
        
        # Store in session state for Agent Builder tab to execute
        import streamlit as st
        st.session_state.running_agent = matching_agent
        
        return f"✅ Agent '{matching_agent.name}' ready to run!\n\nGo to the **Agent Builder** tab to execute it."
    
    def handle_browser_navigate(self, args: str) -> str:
        """Handle /browse command - navigate to URL using browser-use."""
        if not args:
            return "Usage: /browse <url>\nExample: /browse https://google.com"
        
        # Use browser-use instead of old browser_control
        task = f"Navigate to {args} and tell me what you see"
        result = asyncio.run(self.execute_browser_task(task))
        return result
    
    def _old_handle_browser_navigate(self, args: str) -> str:
        """OLD METHOD - DEPRECATED. Use browser-use instead."""
        if not args:
            return "Usage: /browse <url>\nExample: /browse https://google.com"
        
        # This requires old browser_control module - now using browser-use
        return "⚠️ This command has been replaced with browser-use. Try: 'browse to <url>'"
        
        if result['success']:
            return f"✅ {result['message']}\n\n**Title:** {result.get('title', 'N/A')}\n**URL:** {result.get('url')}"
        return f"❌ Error: {result.get('error')}"
    
    def handle_browser_click(self, args: str) -> str:
        """Handle /click command using browser-use."""
        if not args:
            return "Usage: /click <element description>\nExample: /click the submit button"
        
        task = f"Click on {args}"
        return asyncio.run(self.execute_browser_task(task))
    
    def handle_browser_type(self, args: str) -> str:
        """Handle /type command using browser-use."""
        if not args:
            return "Usage: /type <text> into <element>\nExample: /type hello world into search box"
        
        task = f"Type {args}"
        return asyncio.run(self.execute_browser_task(task))
    
    def handle_browser_get_text(self, args: str) -> str:
        """Handle /gettext command using browser-use."""
        if not args:
            return "Usage: /gettext <element description>\nExample: /gettext the page title"
        
        task = f"Get the text from {args}"
        return asyncio.run(self.execute_browser_task(task))
    
    def handle_browser_screenshot(self, args: str) -> str:
        """Handle /screenshot command using browser-use."""
        task = f"Take a screenshot of the current page"
        if args:
            task += f" focusing on {args}"
        return asyncio.run(self.execute_browser_task(task))
    
    def handle_browser_find_elements(self, args: str) -> str:
        """Handle /find command using browser-use."""
        if not args:
            return "Usage: /find <element description>\nExample: /find all buttons on the page"
        
        task = f"Find and list {args}"
        return asyncio.run(self.execute_browser_task(task))
    
    def handle_browser_close(self, args: str) -> str:
        """Handle /closebrowser command."""
        return "Browser sessions are automatically closed after each task when using browser-use."

CHAT_INTERFACE_CSS = """
<style>
/* Make sidebar chat input sticky/floating at bottom */
[data-testid="stSidebar"] [data-testid="stChatInput"] {
    position: sticky !important;
    bottom: 0 !important;
    background: var(--background-color, #0e1117) !important;
    padding: 10px 0 !important;
    z-index: 999 !important;
    border-top: 1px solid rgba(255,255,255,0.1) !important;
}

/* Ensure the chat input container in sidebar stays at bottom */
[data-testid="stSidebar"] .stChatInputContainer {
    position: sticky !important;
    bottom: 0 !important;
    background: inherit !important;
}

/* Modern chat container */
.chat-container {
    display: flex;
    flex-direction: column;
    height: 100%;
    max-height: 70vh;
}

/* Messages area - scrollable */
.messages-area {
    flex: 1;
    overflow-y: auto;
    padding: 1rem;
    margin-bottom: 80px;
}

/* User message bubble */
.user-message {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 12px 16px;
    border-radius: 18px 18px 4px 18px;
    margin: 8px 0;
    max-width: 80%;
    margin-left: auto;
    box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

/* Assistant message bubble */
.assistant-message {
    background: #f0f2f6;
    color: #1a1a2e;
    padding: 12px 16px;
    border-radius: 18px 18px 18px 4px;
    margin: 8px 0;
    max-width: 85%;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

/* Status indicator */
.status-indicator {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    background: #e8f4fd;
    border-radius: 8px;
    margin: 8px 0;
    font-size: 0.9em;
    color: #1976d2;
}

/* Typing indicator animation */
.typing-indicator {
    display: flex;
    gap: 4px;
    padding: 12px 16px;
}
.typing-indicator span {
    width: 8px;
    height: 8px;
    background: #667eea;
    border-radius: 50%;
    animation: typing 1.4s infinite;
}
.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }
@keyframes typing {
    0%, 60%, 100% { transform: translateY(0); opacity: 0.6; }
    30% { transform: translateY(-8px); opacity: 1; }
}

/* Quick action buttons */
.quick-actions {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-bottom: 12px;
}
.quick-action-btn {
    background: #f8f9fa;
    border: 1px solid #e0e0e0;
    padding: 6px 12px;
    border-radius: 16px;
    font-size: 0.85em;
    cursor: pointer;
    transition: all 0.2s;
}
.quick-action-btn:hover {
    background: #667eea;
    color: white;
    border-color: #667eea;
}
</style>
"""

def _initialize_apis():
    """Initialize API connections for status display."""
    apis = {'printify': None, 'shopify': None, 'youtube': None}
    
    try:
        token = os.getenv('PRINTIFY_API_TOKEN') or st.session_state.get('printify_token')
        if token:
            from app.services.api_service import PrintifyAPI
            apis['printify'] = PrintifyAPI(token)
    except: pass
    
    try:
        token = os.getenv('SHOPIFY_ACCESS_TOKEN') or st.session_state.get('shopify_token')
        store = os.getenv('SHOPIFY_STORE_NAME') or st.session_state.get('shopify_store')
        if token and store:
            from shopify_service import ShopifyService
            apis['shopify'] = ShopifyService(store, token)
    except: pass
    
    try:
        if st.session_state.get('youtube_credentials'):
            apis['youtube'] = True
    except: pass
    
    return apis

def render_knowledge_base_ui(key_suffix: str, is_fullscreen: bool):
    """Render the Knowledge Base UI section."""
    otto_module = _get_otto_engine()
    if not (OTTO_ENGINE_AVAILABLE and otto_module):
        return

    get_knowledge_base = otto_module['get_knowledge_base']
    kb = get_knowledge_base()
    
    if is_fullscreen:
        st.caption(f"**Knowledge:** 📚 {len(kb.facts)}F | {len(kb.documents)}D | {len(kb.images)}I")
    
    with st.expander("📚 **Knowledge Base** - Teach Otto About Your Business", expanded=False):
        st.markdown("""
        **Upload images or documents to teach Otto context about your business, products, brand, or anything else.**
        Otto will analyze and remember this information for future conversations.
        """)
        
        col1, col2 = st.columns(2)
        
        # Image Analysis
        with col1:
            st.markdown("**🖼️ Image Analysis**")
            uploaded_image = st.file_uploader("Upload an image", type=['png', 'jpg', 'jpeg', 'gif', 'webp'], key=f"otto_kb_img_{key_suffix}")
            
            if uploaded_image and st.button("🔍 Analyze Image", key=f"analyze_img_{key_suffix}"):
                with st.spinner("Analyzing..."):
                    ReplicateAPI = _get_replicate_api()
                    api = ReplicateAPI(st.session_state.get('replicate_api_key', os.getenv('REPLICATE_API_TOKEN', '')))
                    result = kb.analyze_image(uploaded_image.read(), uploaded_image.name, api)
                    
                    if result.get("success"):
                        st.success(result.get("message"))
                        st.markdown(f"**📝 Analysis:**\n{result.get('analysis', '')}")
                        st.session_state.chat_history.append({
                            'role': 'assistant',
                            'content': f"📷 **Image Analyzed:** {uploaded_image.name}\n\n{result.get('analysis', '')}"
                        })
                    else:
                        st.error(f"Analysis failed: {result.get('error')}")

        # Document Reading
        with col2:
            st.markdown("**📄 Document Reading**")
            uploaded_doc = st.file_uploader("Upload a document", type=['txt', 'pdf', 'doc', 'docx', 'md', 'json', 'csv'], key=f"otto_kb_doc_{key_suffix}")
            
            if uploaded_doc and st.button("📖 Read Document", key=f"read_doc_{key_suffix}"):
                with st.spinner("Reading..."):
                    ReplicateAPI = _get_replicate_api()
                    api = ReplicateAPI(st.session_state.get('replicate_api_key', os.getenv('REPLICATE_API_TOKEN', '')))
                    result = kb.read_document(uploaded_doc.read(), uploaded_doc.name, api)
                    
                    if result.get("success"):
                        st.success(result.get("message"))
                        st.markdown(f"**📝 Summary:**\n{result.get('summary', '')}")
                        st.session_state.chat_history.append({
                            'role': 'assistant',
                            'content': f"📄 **Document Added:** {uploaded_doc.name}\n\n**Summary:**\n{result.get('summary', '')}"
                        })
                    else:
                        st.error(f"Reading failed: {result.get('error')}")
        
        # Quick Fact
        st.markdown("---")
        st.markdown("**💡 Quick Add Fact**")
        c1, c2 = st.columns([4, 1])
        with c1:
            fact = st.text_input("Teach Otto something", placeholder="e.g., Our brand color is blue...", key=f"otto_fact_{key_suffix}", label_visibility="collapsed")
        with c2:
            if st.button("➕ Add", key=f"add_fact_{key_suffix}", use_container_width=True) and fact:
                kb.add_fact(fact)
                st.success(f"✅ Learned: {fact[:50]}...")
                st.session_state.chat_history.append({'role': 'assistant', 'content': f"📚 **Learned new fact:** {fact}"})
                st.rerun()
        
        # Actions
        st.markdown("---")
        ac1, ac2, ac3, ac4 = st.columns(4)
        if ac1.button("📊 Status", key=f"kb_stat_{key_suffix}", use_container_width=True):
            st.info(kb.get_context_summary())
        if ac2.button("🧹 Clear Facts", key=f"kb_clr_f_{key_suffix}", use_container_width=True):
            kb.clear_memory("facts"); st.success("Facts cleared!")
        if ac3.button("🗑️ Clear Docs", key=f"kb_clr_d_{key_suffix}", use_container_width=True):
            kb.clear_memory("documents"); st.success("Documents cleared!")
        if ac4.button("💥 Clear All", key=f"kb_clr_a_{key_suffix}", use_container_width=True):
            kb.clear_memory("all"); st.success("All knowledge cleared!")

def render_chat_interface(key_suffix: str = "sidebar"):
    """
    Render a modern, ChatGPT-style chat interface.
    Features:
    - Fixed input at bottom (always visible)
    - Scrollable message area
    - Real-time status updates
    - Clean, modern design
    
    Args:
        key_suffix: Unique suffix for widget keys to avoid duplicates
    """
    
    # Determine if we're in fullscreen mode for styling
    is_fullscreen = key_suffix == "fullscreen"
    
    # Custom CSS for modern chat appearance with sticky input
    st.markdown(CHAT_INTERFACE_CSS, unsafe_allow_html=True)
    
    # Initialize API connections for status display
    apis = _initialize_apis()
    printify_api = apis['printify']
    shopify_api = apis['shopify']
    youtube_api = apis['youtube']
    
    # Header with status
    if is_fullscreen:
        col_title, col_status = st.columns([3, 1])
        with col_title:
            st.markdown("### 🤖 Otto Mate")
        with col_status:
            # Show connected services
            services = []
            if printify_api: services.append("🛍️")
            if shopify_api: services.append("🏪")
            if youtube_api: services.append("📺")
            if os.getenv('ANTHROPIC_API_KEY'): services.append("🌐")
            
            if services:
                st.success(" ".join(services))
            else:
                st.info("💬 Chat Mode")
    else:
        st.markdown("### 🤖 Otto Mate")
    
    # ===========================================
    # CHAT HISTORY MANAGEMENT - Save/Load conversations
    # ===========================================
    with st.expander("💬 **Chat History** - Save & Load Conversations", expanded=False):
        render_chat_history_sidebar(key_suffix=key_suffix)
    
    # ===========================================
    # KNOWLEDGE BASE UI - Upload files to teach Otto
    # ===========================================
    render_knowledge_base_ui(key_suffix, is_fullscreen)
    
    # Initialize chat history
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # Get API key
    replicate_key = st.session_state.get('replicate_api_key', os.getenv('REPLICATE_API_TOKEN', ''))
    
    if not replicate_key:
        st.warning("⚠️ Replicate API key required")
        st.info("Add your API key in Settings → API Keys")
        return
    
    # Get API instances from session state
    shopify_api = st.session_state.get('shopify_api')
    printify_api = st.session_state.get('printify_api')
    youtube_api = st.session_state.get('youtube_service')
    
    # Initialize assistant with all APIs
    assistant = ChatAssistant(
        replicate_api_key=replicate_key,
        printify_api=printify_api,
        shopify_api=shopify_api,
        youtube_api=youtube_api
    )
    
    # Update action executor with all APIs
    assistant.action_executor.shopify = shopify_api
    assistant.action_executor.printify = printify_api
    assistant.action_executor.youtube = youtube_api
    
    # Quick actions (only in fullscreen)
    if is_fullscreen and len(st.session_state.chat_history) == 0:
        st.markdown("#### ✨ Quick Start")
        quick_cols = st.columns(4)
        
        quick_actions = [
            ("🎨 Generate Design", "Create a product design for a"),
            ("🎬 Make Video", "Create a complete video for"),
            ("📢 Marketing Campaign", "Create a full marketing campaign for"),
            ("🔍 Research", "Research market trends for")
        ]
        
        for i, (label, prompt_start) in enumerate(quick_actions):
            with quick_cols[i]:
                if st.button(label, key=f"quick_{i}_{key_suffix}", use_container_width=True):
                    st.session_state[f'quick_prompt_{key_suffix}'] = prompt_start
                    st.rerun()
        
        st.markdown("---")
    
    # Create a container for messages with fixed height for scrolling
    if is_fullscreen:
        message_container = st.container(height=500)
    else:
        message_container = st.container(height=350)
    
    with message_container:
        # Welcome message if empty
        if len(st.session_state.chat_history) == 0:
            st.markdown("""
            <div style="text-align: center; padding: 10px 15px; color: #666;">
                <div style="font-size: 2em; margin-bottom: 8px;">🧠</div>
                <h4 style="margin: 0 0 8px 0;">Hey! I'm Otto Mate 🤖</h4>
                <p style="margin: 0; font-size: 0.9em;">I can create designs, videos, marketing campaigns, and automate your workflow.</p>
                <p style="margin: 8px 0 0 0; font-size: 0.85em;"><strong>Try:</strong> "Create a coffee mug mockup"</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Display chat history with proper image rendering
            for msg in st.session_state.chat_history:
                with st.chat_message(msg['role'], avatar="🧑" if msg['role'] == 'user' else "🤖"):
                    content = msg['content']
                    
                    # Check if content contains image markdown and render it properly
                    if '![' in content and '](' in content:
                        # Parse and render images separately
                        import re
                        parts = re.split(r'(!\[.*?\]\(.*?\))', content)
                        
                        for part in parts:
                            if part.startswith('!['):
                                # Extract image URL from markdown
                                match = re.match(r'!\[.*?\]\((.*?)\)', part)
                                if match:
                                    image_url = match.group(1)
                                    try:
                                        st.image(image_url, use_container_width=True)
                                    except Exception as e:
                                        st.markdown(f"🖼️ [View Image]({image_url})")
                            elif part.strip():
                                st.markdown(part)
                    else:
                        st.markdown(content)
    
    # Separator before input
    st.markdown("---")
    
    # Status bar (shows when processing)
    if st.session_state.get('chat_processing', False):
        st.markdown("""
        <div class="status-indicator">
            <div class="typing-indicator">
                <span></span><span></span><span></span>
            </div>
            Processing your request...
        </div>
        """, unsafe_allow_html=True)
    
    # Check for pending voice command
    voice_command = st.session_state.get('process_voice_command')
    if voice_command:
        # Process voice command as if it was typed
        user_input = voice_command
        st.session_state.process_voice_command = None  # Clear it
        
        # Show notification
        st.success(f"🎤 Processing voice command: '{user_input}'")
    else:
        # Input area - always at bottom
        user_input = st.chat_input(
            "Message Otto Mate...", 
            key=f"chat_input_{key_suffix}"
        )
    
    # Chat action buttons below input
    manager = get_chat_history_manager()
    action_cols = st.columns([1, 1, 1, 6])
    
    with action_cols[0]:
        if st.button("➕", key=f"new_chat_btn_{key_suffix}", help="New conversation", use_container_width=True):
            # Save current if has messages
            if st.session_state.get('chat_history', []):
                current_id = st.session_state.get('current_conversation_id')
                manager.save_conversation(
                    st.session_state.chat_history,
                    conversation_id=current_id
                )
            # Start fresh
            st.session_state.chat_history = []
            st.session_state.current_conversation_id = None
            st.rerun()
    
    with action_cols[1]:
        if st.button("💾", key=f"save_chat_btn_{key_suffix}", help="Save conversation", use_container_width=True):
            if st.session_state.get('chat_history', []):
                current_id = st.session_state.get('current_conversation_id')
                result = manager.save_conversation(
                    st.session_state.chat_history,
                    conversation_id=current_id
                )
                if result.get("success"):
                    st.session_state.current_conversation_id = result["id"]
                    st.toast("✅ Conversation saved!")
                else:
                    st.error(f"Failed: {result.get('error')}")
            else:
                st.warning("No messages to save")
    
    with action_cols[2]:
        if st.button("🗑️", key=f"clear_chat_btn_{key_suffix}", help="Clear chat", use_container_width=True):
            # Auto-save before clearing if there are messages
            if st.session_state.get('chat_history', []):
                current_id = st.session_state.get('current_conversation_id')
                manager.save_conversation(
                    st.session_state.chat_history,
                    conversation_id=current_id
                )
            st.session_state.chat_history = []
            st.session_state.current_conversation_id = None
            st.rerun()
    
    # Handle input
    if user_input:
        import asyncio
        
        # Add user message
        st.session_state.chat_history.append({
            'role': 'user',
            'content': user_input
        })
        
        # Set processing state
        st.session_state['chat_processing'] = True
        
        # Get AI response
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response = loop.run_until_complete(
                assistant.process_message(user_input, st.session_state.chat_history)
            )
        except Exception as e:
            response = f"❌ Error: {str(e)}"
        
        # Add assistant response
        st.session_state.chat_history.append({
            'role': 'assistant',
            'content': response
        })
        
        # Clear processing state
        st.session_state['chat_processing'] = False
        
        st.rerun()


# ========================================
# AUTONOMOUS TASK QUEUE SYSTEM
# ========================================

def render_autonomous_todo():
    """Render the autonomous task queue / todo system."""
    
    st.markdown('<div class="main-header">🤖 Autonomous Task Queue</div>', unsafe_allow_html=True)
    st.markdown("### Add tasks and let AI execute them automatically")
    
    # Initialize task queue in session state
    if 'task_queue' not in st.session_state:
        st.session_state.task_queue = []
    if 'queue_running' not in st.session_state:
        st.session_state.queue_running = False
    if 'current_task_index' not in st.session_state:
        st.session_state.current_task_index = 0
    
    # Get API key
    replicate_key = st.session_state.get('replicate_api_key', os.getenv('REPLICATE_API_TOKEN', ''))
    
    if not replicate_key:
        st.warning("⚠️ Replicate API key required")
        return
    
    # Initialize queue manager (lazy loaded)
    ReplicateAPI = _get_replicate_api()
    queue_manager = AutonomousTaskQueue(ReplicateAPI(api_token=replicate_key))
    
    # Layout: Input on left, queue on right
    input_col, queue_col = st.columns([1, 1])
    
    with input_col:
        st.markdown("#### ➕ Add New Task")
        
        # Task input
        new_task = st.text_area(
            "Describe what you want to accomplish:",
            height=100,
            placeholder="e.g., Create a complete marketing campaign for a coffee mug with cat designs, including product images, video, and social media posts",
            key="new_task_input"
        )
        
        col_add, col_analyze = st.columns(2)
        
        with col_add:
            if st.button("➕ Add to Queue", use_container_width=True, type="primary"):
                if new_task.strip():
                    # Create new task
                    import uuid
                    task_id = str(uuid.uuid4())[:8]
                    task = TaskQueueItem(task_id, new_task.strip())
                    
                    # Analyze the task
                    with st.spinner("🧠 AI analyzing task..."):
                        task.plan = queue_manager.analyze_task(new_task)
                        task.agents_needed = task.plan.get('agents_needed', [])
                        task.steps = task.plan.get('steps', [])
                        task.status = "ready"
                    
                    # Add to queue
                    st.session_state.task_queue.append(task)
                    st.success(f"✅ Task added! {len(task.steps)} steps planned.")
                    st.rerun()
        
        with col_analyze:
            if st.button("🔍 Preview Plan", use_container_width=True):
                if new_task.strip():
                    with st.spinner("🧠 Analyzing..."):
                        plan = queue_manager.analyze_task(new_task)
                    
                    st.markdown("##### 📋 Execution Plan Preview")
                    st.json(plan)
        
        # Quick task templates
        st.markdown("---")
        st.markdown("##### ⚡ Quick Templates")
        
        templates = [
            ("🎨 Product Design", "Create a unique product design for a t-shirt with [theme]"),
            ("🎬 Video Campaign", "Create a complete video campaign for [product]"),
            ("📢 Social Media", "Generate social media posts and images for [product]"),
            ("📝 Blog Content", "Write a blog post about [topic] with header image"),
        ]
        
        for label, template in templates:
            if st.button(label, key=f"template_{label}", use_container_width=True):
                st.session_state['template_task'] = template
                st.rerun()
    
    with queue_col:
        st.markdown("#### 📋 Task Queue")
        
        # Queue controls
        ctrl_col1, ctrl_col2, ctrl_col3 = st.columns(3)
        
        with ctrl_col1:
            queue_running = st.session_state.get('queue_running', False)
            if queue_running:
                if st.button("⏸️ Pause", use_container_width=True):
                    st.session_state.queue_running = False
                    st.rerun()
            else:
                if st.button("▶️ Start Queue", use_container_width=True, type="primary"):
                    if st.session_state.task_queue:
                        st.session_state.queue_running = True
                        st.rerun()
        
        with ctrl_col2:
            if st.button("⏭️ Skip Current", use_container_width=True):
                if st.session_state.task_queue:
                    st.session_state.current_task_index += 1
                    st.rerun()
        
        with ctrl_col3:
            if st.button("🗑️ Clear Queue", use_container_width=True):
                st.session_state.task_queue = []
                st.session_state.current_task_index = 0
                st.session_state.queue_running = False
                st.rerun()
        
        st.markdown("---")
        
        # Display queue
        if not st.session_state.task_queue:
            st.info("📭 Queue is empty. Add tasks to get started!")
        else:
            for i, task in enumerate(st.session_state.task_queue):
                # Determine status styling
                if task.status == "completed":
                    status_icon = "✅"
                    status_color = "green"
                elif task.status == "executing":
                    status_icon = "⏳"
                    status_color = "orange"
                elif task.status == "failed":
                    status_icon = "❌"
                    status_color = "red"
                elif task.status == "ready":
                    status_icon = "🔵"
                    status_color = "blue"
                else:
                    status_icon = "⚪"
                    status_color = "gray"
                
                # Task card
                with st.expander(f"{status_icon} Task {i+1}: {task.description[:50]}...", expanded=(task.status == "executing")):
                    st.markdown(f"**Status:** :{status_color}[{task.status.upper()}]")
                    st.markdown(f"**Description:** {task.description}")
                    
                    if task.plan:
                        st.markdown(f"**Goal:** {task.plan.get('goal', 'N/A')}")
                        st.markdown(f"**Agents:** {', '.join(task.agents_needed)}")
                        st.markdown(f"**Steps:** {len(task.steps)}")
                        st.markdown(f"**Est. Time:** {task.plan.get('estimated_time', 'Unknown')}")
                    
                    if task.status == "completed" and task.results:
                        st.markdown("---")
                        st.markdown("**Results:**")
                        if task.results.get('final_summary'):
                            st.markdown(task.results['final_summary'])
                    
                    if task.error:
                        st.error(f"Error: {task.error}")
                    
                    # Task actions
                    task_cols = st.columns(3)
                    with task_cols[0]:
                        if task.status in ["ready", "pending"] and st.button("▶️ Run Now", key=f"run_{task.id}"):
                            st.session_state.current_task_index = i
                            st.session_state.queue_running = True
                            st.rerun()
                    with task_cols[1]:
                        if st.button("🔄 Retry", key=f"retry_{task.id}"):
                            task.status = "ready"
                            task.error = None
                            st.rerun()
                    with task_cols[2]:
                        if st.button("🗑️", key=f"del_{task.id}"):
                            st.session_state.task_queue.remove(task)
                            st.rerun()
    
    # Execute queue if running
    if st.session_state.queue_running and st.session_state.task_queue:
        current_idx = st.session_state.current_task_index
        
        if current_idx < len(st.session_state.task_queue):
            current_task = st.session_state.task_queue[current_idx]
            
            if current_task.status in ["ready", "pending"]:
                st.markdown("---")
                st.markdown(f"### ⚡ Executing Task {current_idx + 1}")
                st.markdown(f"**{current_task.description}**")
                
                # Execute the task
                current_task.status = "executing"
                
                try:
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    results = loop.run_until_complete(
                        queue_manager.execute_task(current_task)
                    )
                    
                    current_task.results = results
                    current_task.status = "completed" if results.get('success', False) else "failed"
                    
                except Exception as e:
                    current_task.status = "failed"
                    current_task.error = str(e)
                
                # Move to next task
                st.session_state.current_task_index += 1
                
                # Check if queue is done
                if st.session_state.current_task_index >= len(st.session_state.task_queue):
                    st.session_state.queue_running = False
                    st.success("🎉 All tasks completed!")
                
                st.rerun()
        else:
            st.session_state.queue_running = False
            st.session_state.current_task_index = 0
    
    # Queue summary
    st.markdown("---")
    total = len(st.session_state.task_queue)
    completed = sum(1 for t in st.session_state.task_queue if t.status == "completed")
    failed = sum(1 for t in st.session_state.task_queue if t.status == "failed")
    pending = total - completed - failed
    
    summary_cols = st.columns(4)
    with summary_cols[0]:
        st.metric("Total Tasks", total)
    with summary_cols[1]:
        st.metric("Completed", completed)
    with summary_cols[2]:
        st.metric("Pending", pending)
    with summary_cols[3]:
        st.metric("Failed", failed)
