"""
OTTO SUPER - Main Integration
==============================
The supercharged Otto that combines all components into one hyperintelligent assistant.
"""

import asyncio
import logging
import streamlit as st
from typing import Dict, List, Any, Optional
from datetime import datetime

# Import all Otto components
from .otto_super_engine import (
    ToolRegistry, Tool, ToolCategory,
    IntentParser, ParsedIntent,
    MemoryManager, ChatSession, ChatMessage
)
from .otto_super_engine_part2 import (
    ExecutionEngine, ExecutionResult,
    ContextTracker
)

# Import Otto extensions
from .otto_super_extensions import (
    OttoTaskQueueExtension,
    OttoDocumentExtension,
    OttoPinterestTikTokExtension,
    OttoWorkflowExtension,
    parse_extended_intent
)

# Import Otto App Controller for full platform access
from .otto_app_controller import (
    OttoAppController,
    parse_app_control_intent
)

logger = logging.getLogger(__name__)


class OttoSuper:
    """
    The ultimate Otto - hyperintelligent AI assistant that can:
    - Understand any request
    - Route to correct models/tools
    - Execute complex workflows
    - Display results in real-time
    - Remember conversations
    - Access all app features
    - Distribute heavy tasks with Ray
    """
    
    def __init__(self, replicate_api, printify_api=None, shopify_api=None, youtube_api=None, 
                 task_queue_engine=None, multi_platform_poster=None, enable_ray=None):
        """Initialize Otto Super with all components."""
        logger.info("🚀 Initializing Otto Super...")
        
        # Core APIs
        self.replicate = replicate_api
        self.printify = printify_api
        self.shopify = shopify_api
        self.youtube = youtube_api
        
        # Ray support (auto-detect if not specified)
        if enable_ray is None:
            try:
                from ray_integration_helpers import is_ray_enabled
                self.enable_ray = is_ray_enabled()
            except:
                self.enable_ray = False
        else:
            self.enable_ray = enable_ray
        
        # Initialize components
        self.tool_registry = ToolRegistry()
        self.intent_parser = IntentParser(self.tool_registry, replicate_api)
        self.execution_engine = ExecutionEngine(
            self.tool_registry,
            replicate_api,
            printify_api,
            shopify_api,
            youtube_api
        )
        self.memory = MemoryManager()
        self.context = ContextTracker()
        
        # Initialize extensions
        self.task_queue_ext = OttoTaskQueueExtension(task_queue_engine)
        self.document_ext = OttoDocumentExtension()
        self.social_ext = OttoPinterestTikTokExtension(multi_platform_poster)
        self.workflow_ext = OttoWorkflowExtension(
            task_queue_ext=self.task_queue_ext,
            document_ext=self.document_ext,
            social_ext=self.social_ext
        )
        
        # Initialize App Controller - gives Otto FULL platform access
        self.app_controller = OttoAppController(
            replicate_api=replicate_api,
            printify_api=printify_api,
            shopify_api=shopify_api,
            youtube_api=youtube_api,
            task_queue=task_queue_engine,
            multi_platform_poster=multi_platform_poster
        )
        
        # Scan for available campaigns
        self.context.scan_campaigns()
        
        if self.enable_ray:
            logger.info("✅ Otto Super ready with FULL platform access + Ray distributed computing!")
        else:
            logger.info("✅ Otto Super ready with FULL platform access!")
    
    def get_system_status(self) -> Dict[str, bool]:
        """Get status of all integrated systems."""
        return {
            'replicate': bool(self.replicate),
            'printify': bool(self.printify),
            'shopify': bool(self.shopify),
            'youtube': bool(self.youtube),
            'browser': self.execution_engine.browser and self.execution_engine.browser.is_available,
            'tool_count': len(self.tool_registry.tools)
        }
    
    async def process_message(
        self,
        user_message: str,
        session: Optional[ChatSession] = None,
        progress_callback=None
    ) -> tuple[str, List[ExecutionResult]]:
        """
        Process a user message end-to-end:
        1. Parse intent
        2. Execute tools
        3. Display results
        4. Update memory
        
        Returns:
            (response_text, execution_results)
        """
        
        # Get current session or create new one
        if session is None:
            session = self.memory.current_session
            if session is None:
                session = self.memory.create_session()
        
        # Add user message to session
        session.add_message("user", user_message)
        
        # Build context for parsing
        context = self.context.get_all()
        context.update(session.context)
        
        try:
            # Step 1: Check for App Control Intents (full platform access)
            app_intent_type = parse_app_control_intent(user_message)
            
            if app_intent_type:
                # Handle app-wide operations
                if progress_callback:
                    progress_callback({"step": "app_control", "message": f"🎮 {app_intent_type.replace('_', ' ').title()}..."})
                
                app_result = await self._handle_app_control(app_intent_type, user_message, context)
                response = app_result.get('message', 'Done!')
                session.add_message("assistant", response)
                return response, []
            
            # Step 2: Check for Extended Intents (task queue, documents, workflows)
            extended_intent_type = parse_extended_intent(user_message)
            
            if extended_intent_type:
                # Build extended intent dict
                extended_intent = {
                    'action': extended_intent_type,
                    'description': user_message,
                    'content': user_message
                }
                
                # Handle extended functionality
                if progress_callback:
                    progress_callback({"step": "extension", "message": f"🔧 {extended_intent_type}..."})
                
                ext_result = await self._handle_extended_intent(extended_intent, user_message, context)
                response = ext_result.get('response', 'Done!')
                session.add_message("assistant", response)
                return response, []
            
            # Step 2: Parse Standard Intent
            if progress_callback:
                progress_callback({"step": "parsing", "message": "🧠 Understanding your request..."})
            
            intent = await self.intent_parser.parse(user_message, context)
            
            logger.info(f"📊 Parsed intent: {intent.primary_goal}")
            logger.info(f"   Tools needed: {intent.tools_needed}")
            logger.info(f"   Confidence: {intent.confidence}")
            
            # Check if clarification needed
            if intent.requires_clarification:
                response = f"🤔 {intent.clarification_question}"
                session.add_message("assistant", response)
                return response, []
            
            # Step 3: Execute Tools
            results = []
            
            if not intent.tools_needed:
                # Conversational response (no actions)
                response = await self._generate_conversational_response(
                    user_message,
                    session.get_recent_messages(10),
                    context
                )
                session.add_message("assistant", response)
                return response, []
            
            # Execute each tool
            for tool_id in intent.tools_needed:
                tool = self.tool_registry.get(tool_id)
                
                if not tool:
                    continue
                
                # Check if confirmation needed
                if tool.requires_confirmation:
                    confirm_msg = f"⚠️ **Confirmation Required**\n\nAbout to execute: {tool.name}\nEstimated cost: {tool.cost_estimate}\n\nProceed?"
                    # In a real UI, this would wait for user confirmation
                    # For now, we'll proceed
                    if progress_callback:
                        progress_callback({"step": "confirming", "message": confirm_msg})
                
                # Execute tool
                if progress_callback:
                    progress_callback({"step": "executing", "tool": tool.name, "message": f"⏳ {tool.description}"})
                
                result = await self.execution_engine.execute_tool(
                    tool_id,
                    intent.parameters,
                    progress_callback
                )
                
                results.append(result)
                
                # Track generated assets
                if result.success and result.artifacts:
                    for artifact in result.artifacts:
                        self.context.track_generation(
                            artifact.get('type', 'unknown'),
                            artifact.get('url', ''),
                            artifact
                        )
            
            # Step 3: Build Response
            response = self._build_response(intent, results)
            
            # Step 4: Update Memory
            session.add_message("assistant", response, metadata={
                'intent': intent.primary_goal,
                'tools_used': intent.tools_needed,
                'results': [r.to_dict() for r in results]
            })
            
            # Update session context with new artifacts
            for result in results:
                if result.success and result.artifacts:
                    for artifact in result.artifacts:
                        artifact_type = artifact.get('type')
                        if artifact_type == 'image':
                            session.context['last_generated_image'] = artifact.get('url')
                        elif artifact_type == 'video':
                            session.context['last_generated_video'] = artifact.get('url')
                        elif artifact_type == 'audio':
                            session.context['last_generated_audio'] = artifact.get('url')
            
            # Auto-save session
            self.memory.save_session(session)
            
            return response, results
            
        except Exception as e:
            logger.error(f"❌ Message processing error: {e}", exc_info=True)
            error_msg = f"❌ Sorry, I encountered an error: {str(e)}"
            session.add_message("assistant", error_msg)
            return error_msg, []
    
    async def _generate_conversational_response(
        self,
        message: str,
        recent_messages: List[ChatMessage],
        context: Dict
    ) -> str:
        """Generate a conversational response (no actions)."""
        
        # Build conversation history
        conversation = []
        for msg in recent_messages[-10:]:
            conversation.append(f"{msg.role}: {msg.content}")
        
        # Build system prompt with context
        system_prompt = f"""You are Otto Mate, a hyperintelligent AI assistant for a marketing automation platform.

You have access to:
- 50+ AI models (image, video, audio, 3D generation)
- Complete campaign generation
- Publishing to Printify, YouTube, Shopify
- Browser automation
- And much more!

CURRENT CONTEXT:
{self.context.build_knowledge_summary()}

SYSTEM STATUS:
- Replicate: {'✅' if self.replicate else '❌'}
- Printify: {'✅' if self.printify else '❌'}
- Shopify: {'✅' if self.shopify else '❌'}
- YouTube: {'✅' if self.youtube else '❌'}
- Browser: {'✅' if self.execution_engine.browser and self.execution_engine.browser.is_available else '❌'}

Be helpful, friendly, and concise. If the user asks you to DO something, explain that they should phrase it as a command like "Create..." or "Generate...".
"""
        
        prompt = f"{system_prompt}\n\nCONVERSATION:\n" + "\n".join(conversation) + f"\nUser: {message}\nAssistant:"
        
        try:
            response = self.replicate.generate_text(
                prompt=prompt,
                max_tokens=500,
                temperature=0.7,
                system_prompt=system_prompt
            )
            return response.strip()
        except Exception as e:
            return f"I understand your question, but I encountered an error: {e}"
    
    async def _handle_app_control(self, intent_type: str, message: str, context: Dict) -> Dict[str, Any]:
        """Handle app-wide control operations (full platform access)."""
        
        try:
            # Content Generation
            if intent_type == 'generate_campaign':
                # Extract params from message
                brand_name = context.get('brand_name', 'Aura Sky')
                product_type = 'poster' if 'poster' in message.lower() else 'product'
                style = self._extract_style(message)
                
                return await self.app_controller.generate_campaign(
                    brand_name=brand_name,
                    product_type=product_type,
                    style=style
                )
            
            elif intent_type == 'generate_poster':
                prompt = message.replace('generate poster', '').replace('create poster', '').strip()
                style = self._extract_style(message)
                return await self.app_controller.generate_poster(prompt, style)
            
            elif intent_type == 'generate_video':
                prompt = message.replace('generate video', '').replace('create video', '').strip()
                return await self.app_controller.generate_video(prompt)
            
            elif intent_type == 'generate_audio':
                prompt = message.replace('generate audio', '').replace('create audio', '').strip()
                genre = self._extract_genre(message)
                return await self.app_controller.generate_audio(prompt, genre=genre)
            
            elif intent_type == 'generate_mockup':
                image_url = context.get('last_generated_image', '')
                if not image_url:
                    return {'success': False, 'message': '❌ No image available. Generate an image first.'}
                return await self.app_controller.generate_mockup(image_url)
            
            # E-commerce
            elif intent_type == 'create_product':
                # Extract product details from message
                return await self.app_controller.create_product(
                    title=context.get('product_name', 'New Product'),
                    description=message,
                    price=context.get('price', 24.99),
                    image_url=context.get('last_generated_image', '')
                )
            
            elif intent_type == 'update_pricing':
                product_id = context.get('product_id', '')
                new_price = self._extract_price(message)
                return await self.app_controller.update_pricing(product_id, new_price)
            
            elif intent_type == 'check_inventory':
                return await self.app_controller.check_inventory()
            
            # Social Media
            elif intent_type == 'post_all_platforms':
                media_url = context.get('last_generated_image') or context.get('last_generated_video', '')
                if not media_url:
                    return {'success': False, 'message': '❌ No media available. Generate content first.'}
                
                platforms = self._extract_platforms(message)
                return await self.app_controller.post_to_all_platforms(
                    content=message,
                    media_url=media_url,
                    platforms=platforms
                )
            
            # Analytics
            elif intent_type == 'show_analytics':
                metric_type = 'overview'
                if 'sales' in message.lower():
                    metric_type = 'sales'
                elif 'social' in message.lower():
                    metric_type = 'social'
                
                return await self.app_controller.show_analytics(metric_type)
            
            # Automation
            elif intent_type == 'setup_automation':
                automation_type = self._extract_automation_type(message)
                schedule = self._extract_schedule(message)
                
                return await self.app_controller.setup_automation(
                    automation_type=automation_type,
                    schedule=schedule,
                    config={'description': message}
                )
            
            elif intent_type == 'schedule_posts':
                platforms = self._extract_platforms(message)
                schedule = self._extract_schedule(message)
                
                # Use existing content or create from queue
                content_list = [{'text': message, 'media_url': context.get('last_generated_image', '')}]
                
                return await self.app_controller.schedule_posts(
                    content_list=content_list,
                    platforms=platforms,
                    schedule=schedule
                )
            
            else:
                return {
                    'success': False,
                    'message': f"❌ Unknown app control intent: {intent_type}"
                }
        
        except Exception as e:
            logger.error(f"App control error: {e}", exc_info=True)
            return {
                'success': False,
                'message': f"❌ Error: {str(e)}"
            }
    
    def _extract_style(self, message: str) -> str:
        """Extract visual style from message."""
        msg_lower = message.lower()
        styles = ['cyberpunk', 'minimalist', 'neon', 'modern', 'vintage', 'abstract', 'realistic']
        for style in styles:
            if style in msg_lower:
                return style
        return 'modern'
    
    def _extract_genre(self, message: str) -> str:
        """Extract music genre from message."""
        msg_lower = message.lower()
        genres = ['ambient', 'electronic', 'chill', 'lofi', 'cinematic', 'upbeat']
        for genre in genres:
            if genre in msg_lower:
                return genre
        return 'ambient'
    
    def _extract_price(self, message: str) -> float:
        """Extract price from message."""
        import re
        match = re.search(r'\$?(\d+\.?\d*)', message)
        return float(match.group(1)) if match else 24.99
    
    def _extract_platforms(self, message: str) -> List[str]:
        """Extract platform list from message."""
        msg_lower = message.lower()
        all_platforms = ['pinterest', 'tiktok', 'instagram', 'twitter', 'facebook']
        mentioned = [p for p in all_platforms if p in msg_lower]
        return mentioned if mentioned else ['pinterest', 'tiktok', 'instagram']
    
    def _extract_automation_type(self, message: str) -> str:
        """Extract automation type from message."""
        msg_lower = message.lower()
        if 'post' in msg_lower or 'social' in msg_lower:
            return 'social_post'
        elif 'campaign' in msg_lower:
            return 'campaign_generation'
        elif 'content' in msg_lower:
            return 'content_creation'
        return 'general'
    
    def _extract_schedule(self, message: str) -> str:
        """Extract schedule from message."""
        msg_lower = message.lower()
        if 'daily' in msg_lower:
            return 'daily'
        elif 'weekly' in msg_lower:
            return 'weekly'
        elif 'hourly' in msg_lower:
            return 'hourly'
        return 'daily'
    
    async def _handle_extended_intent(self, extended_intent: Dict[str, Any], message: str, context: Dict) -> Dict[str, Any]:
        """Handle extended Otto functionality (task queue, documents, workflows)."""
        action = extended_intent.get('action')
        
        try:
            if action == 'add_to_queue':
                # Add task to queue
                description = extended_intent.get('description', message)
                priority = extended_intent.get('priority', 'medium')
                result = self.task_queue_ext.add_task_from_otto(description, priority)
                return {
                    'success': True,
                    'response': f"✅ Added to task queue!\n\nTask ID: {result.get('task_id')}\nStatus: {result.get('status')}"
                }
            
            elif action == 'create_document':
                # Create new document
                title = extended_intent.get('title', f"Document {datetime.now().strftime('%Y%m%d_%H%M%S')}")
                content = extended_intent.get('content', message)
                doc_type = extended_intent.get('doc_type', 'text')
                result = self.document_ext.create_document(title, content, doc_type)
                return {
                    'success': True,
                    'response': f"✅ Created document!\n\nPath: {result.get('path')}"
                }
            
            elif action == 'edit_document':
                # Edit existing document
                file_path = extended_intent.get('file_path')
                new_content = extended_intent.get('content', message)
                result = self.document_ext.edit_document(file_path, new_content)
                return {
                    'success': True,
                    'response': f"✅ Updated document!\n\nLines: {result.get('lines_written')}"
                }
            
            elif action == 'list_documents':
                # List available documents
                docs = self.document_ext.list_documents()
                doc_list = "\n".join([f"- {d['name']} ({d['size']} bytes)" for d in docs[:20]])
                return {
                    'success': True,
                    'response': f"📄 Available documents ({len(docs)} total):\n\n{doc_list}"
                }
            
            elif action == 'post_pinterest':
                # Post to Pinterest
                image_path = context.get('last_generated_image', extended_intent.get('image_path', ''))
                caption = extended_intent.get('caption', message)
                if not image_path:
                    return {
                        'success': False,
                        'response': '❌ No image available. Please generate an image first.'
                    }
                result = await self.social_ext.post_to_pinterest(image_path, caption)
                return {
                    'success': result.get('success', False),
                    'response': result.get('message', 'Posted to Pinterest!')
                }
            
            elif action == 'post_tiktok':
                # Post to TikTok
                video_path = context.get('last_generated_video', extended_intent.get('video_path', ''))
                caption = extended_intent.get('caption', message)
                if not video_path:
                    return {
                        'success': False,
                        'response': '❌ No video available. Please generate a video first.'
                    }
                result = await self.social_ext.post_to_tiktok(video_path, caption)
                return {
                    'success': result.get('success', False),
                    'response': result.get('message', 'Posted to TikTok!')
                }
            
            elif action == 'run_workflow':
                # Execute workflow
                workflow_type = extended_intent.get('workflow_type', 'content_to_social')
                params = extended_intent.get('params', {})
                result = await self.workflow_ext.execute_workflow(workflow_type, params)
                return {
                    'success': result.get('success', False),
                    'response': result.get('message', 'Workflow completed!')
                }
            
            else:
                return {
                    'success': False,
                    'response': f"❌ Unknown action: {action}"
                }
        
        except Exception as e:
            logger.error(f"Extended intent error: {e}", exc_info=True)
            return {
                'success': False,
                'response': f"❌ Error: {str(e)}"
            }
    
    def _build_response(self, intent: ParsedIntent, results: List[ExecutionResult]) -> str:
        """Build a response message from intent and results."""
        
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        
        response_parts = []
        
        # Success summary
        if successful:
            response_parts.append(f"✅ **Completed:** {intent.primary_goal}")
            response_parts.append("")
        
        # Show individual results
        for result in results:
            tool = self.tool_registry.get(result.tool_id)
            tool_name = tool.name if tool else result.tool_id
            
            if result.success:
                if result.output_type == "image":
                    response_parts.append(f"🎨 **{tool_name}**")
                    response_parts.append(f"![Generated Image]({result.output})")
                    response_parts.append("")
                
                elif result.output_type == "video":
                    response_parts.append(f"🎬 **{tool_name}**")
                    response_parts.append(f"[▶️ View Video]({result.output})")
                    response_parts.append("")
                
                elif result.output_type == "audio":
                    response_parts.append(f"🎵 **{tool_name}**")
                    response_parts.append(f"[🔊 Listen]({result.output})")
                    response_parts.append("")
                
                else:
                    response_parts.append(f"✅ **{tool_name}**")
                    response_parts.append(str(result.output))
                    response_parts.append("")
            
            else:
                response_parts.append(f"❌ **{tool_name} Failed**")
                response_parts.append(f"Error: {result.error}")
                response_parts.append("")
        
        # Execution stats
        total_time = sum(r.duration_seconds for r in results)
        total_cost = sum(float(r.cost_estimate.strip('$').split('-')[0]) for r in results if r.cost_estimate)
        
        if total_time > 0:
            response_parts.append(f"⏱️ Completed in {total_time:.1f}s")
        if total_cost > 0:
            response_parts.append(f"💰 Estimated cost: ${total_cost:.3f}")
        
        return "\n".join(response_parts)
    
    def get_tool_catalog(self) -> Dict[str, List[Dict]]:
        """Get a categorized catalog of all available tools."""
        catalog = {}
        
        for category in ToolCategory:
            tools = self.tool_registry.list_by_category(category)
            if tools:
                catalog[category.value] = [
                    {
                        'id': t.id,
                        'name': t.name,
                        'description': t.description,
                        'cost': t.cost_estimate
                    }
                    for t in tools
                ]
        
        return catalog


# ============================================================================
# Streamlit UI Integration
# ============================================================================

def render_otto_super_ui(replicate_api, printify_api=None, shopify_api=None, youtube_api=None):
    """
    Render the Otto Super chat interface in Streamlit.
    
    This is the main UI that users interact with.
    """
    
    # Initialize Otto Super (cached)
    if 'otto_super' not in st.session_state:
        with st.spinner("🚀 Initializing Otto Super..."):
            # Initialize task queue engine
            try:
                from app.services.task_queue_engine import TaskQueueEngine
                task_queue = TaskQueueEngine()
            except Exception as e:
                logger.warning(f"Task queue not available: {e}")
                task_queue = None
            
            # Initialize multi-platform poster
            try:
                from multi_platform_poster import MultiPlatformPoster
                multi_poster = MultiPlatformPoster()
            except Exception as e:
                logger.warning(f"Multi-platform poster not available: {e}")
                multi_poster = None
            
            st.session_state.otto_super = OttoSuper(
                replicate_api=replicate_api,
                printify_api=printify_api,
                shopify_api=shopify_api,
                youtube_api=youtube_api,
                task_queue_engine=task_queue,
                multi_platform_poster=multi_poster
            )
    
    otto = st.session_state.otto_super
    
    # Get or create current session
    if 'otto_current_session' not in st.session_state:
        st.session_state.otto_current_session = otto.memory.create_session()
    
    session = st.session_state.otto_current_session
    
    # Header with system status
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        st.markdown("### 🤖 Otto Super")
        st.caption("Hyperintelligent AI Assistant • 50+ Models • Full Platform Control")
    
    with col2:
        # System status
        status = otto.get_system_status()
        services = []
        if status['printify']:
            services.append("🛍️")
        if status['shopify']:
            services.append("🏪")
        if status['youtube']:
            services.append("📺")
        if status['browser']:
            services.append("🌐")
        
        if services:
            st.success(" ".join(services))
        else:
            st.info("💬 Chat")
    
    with col3:
        # Session management
        if st.button("💾 Save", help="Save current session"):
            otto.memory.save_session(session)
            st.toast("Session saved!")
    
    # Messages display
    message_container = st.container(height=500)
    
    with message_container:
        if len(session.messages) == 0:
            # Welcome message
            st.markdown("""
            <div style="text-align: center; padding: 40px 20px; color: #666;">
                <div style="font-size: 4em; margin-bottom: 15px;">🧠</div>
                <h3>Hey! I'm Otto Super 🚀</h3>
                <p>I'm a hyperintelligent AI assistant with access to:</p>
                <p style="font-size: 0.9em;">
                    🎨 50+ AI Models • 🎬 Video Generation • 🎵 Music & Audio<br>
                    📢 Marketing Campaigns • 🛍️ Printify • 🏪 Shopify • 📺 YouTube<br>
                    🌐 Browser Automation • 📊 Analytics • And much more!
                </p>
                <p style="margin-top: 20px;"><strong>Try saying:</strong></p>
                <p style="font-size: 0.85em; line-height: 1.6;">
                    "Create a cyberpunk cityscape image"<br>
                    "Generate a 5-second video from my last image"<br>
                    "Create background music for my video"<br>
                    "Upload my design to Printify"<br>
                    "Create a complete marketing campaign for dog hoodies"
                </p>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Display messages
            for msg in session.messages:
                with st.chat_message(msg.role, avatar="🧑" if msg.role == "user" else "🤖"):
                    # Render message content
                    content = msg.content
                    
                    # Handle images in markdown
                    if '![' in content and '](' in content:
                        import re
                        parts = re.split(r'(!\[.*?\]\(.*?\))', content)
                        
                        for part in parts:
                            if part.startswith('!['):
                                match = re.match(r'!\[.*?\]\((.*?)\)', part)
                                if match:
                                    image_url = match.group(1)
                                    try:
                                        st.image(image_url, use_container_width=True)
                                    except:
                                        st.markdown(part)
                            elif part.strip():
                                st.markdown(part)
                    else:
                        st.markdown(content)
    
    # Input area
    st.markdown("---")
    
    # Progress display
    if 'otto_processing' in st.session_state and st.session_state.otto_processing:
        progress_info = st.session_state.get('otto_progress', {})
        st.info(f"⏳ {progress_info.get('message', 'Processing...')}")
    
    # Chat input
    user_input = st.chat_input("Message Otto Super...")
    
    if user_input:
        # Set processing flag
        st.session_state.otto_processing = True
        st.session_state.otto_progress = {"message": "🧠 Thinking..."}
        
        # Process message
        def progress_callback(update):
            st.session_state.otto_progress = update
        
        # Run async processing
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        response, results = loop.run_until_complete(
            otto.process_message(user_input, session, progress_callback)
        )
        
        # Clear processing flag
        st.session_state.otto_processing = False
        
        st.rerun()


def render_otto_super_sidebar():
    """Render Otto Super controls in sidebar."""
    
    st.markdown("### 💾 Session Management")
    
    if 'otto_super' in st.session_state:
        otto = st.session_state.otto_super
        
        # List saved sessions
        sessions = otto.memory.list_sessions()
        
        if sessions:
            st.markdown(f"**Saved Sessions:** {len(sessions)}")
            
            for sess in sessions[:5]:
                col1, col2 = st.columns([3, 1])
                with col1:
                    if st.button(f"📂 {sess['title']}", key=f"load_{sess['id']}", use_container_width=True):
                        loaded = otto.memory.load_session(sess['id'])
                        st.session_state.otto_current_session = loaded
                        st.rerun()
                with col2:
                    if st.button("🗑️", key=f"del_{sess['id']}"):
                        otto.memory.delete_session(sess['id'])
                        st.rerun()
        
        # New session
        if st.button("➕ New Session", use_container_width=True):
            new_session = otto.memory.create_session()
            st.session_state.otto_current_session = new_session
            st.rerun()
        
        # Export current session
        if st.session_state.get('otto_current_session'):
            if st.button("📤 Export as Markdown", use_container_width=True):
                markdown = otto.memory.export_session_markdown(st.session_state.otto_current_session)
                st.download_button(
                    "Download",
                    markdown,
                    file_name=f"otto_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown"
                )
    
    st.markdown("---")
    st.markdown("### 🛠️ Available Tools")
    
    if 'otto_super' in st.session_state:
        otto = st.session_state.otto_super
        tool_count = len(otto.tool_registry.tools)
        st.metric("Total Tools", tool_count)
        
        # Show categories
        categories = otto.tool_registry.get_all_categories()
        for cat in categories[:5]:
            tools = otto.tool_registry.list_by_category(ToolCategory(cat))
            if tools:
                with st.expander(f"{cat.replace('_', ' ').title()} ({len(tools)})"):
                    for tool in tools[:3]:
                        st.caption(f"**{tool.name}**")
                        st.caption(tool.description[:60] + "...")
