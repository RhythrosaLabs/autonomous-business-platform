"""
Multi-Agent Orchestrator Module

Orchestrates multiple specialized AI agents to accomplish complex tasks.
Can chain workflows, parallelize operations, and creatively solve problems.

Part of the Otto platform's modular architecture.
"""

import logging
from typing import Optional, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor
import streamlit as st

logger = logging.getLogger(__name__)


class MultiAgentOrchestrator:
    """
    Orchestrates multiple specialized AI agents to accomplish complex tasks.
    Can chain workflows, parallelize operations, and creatively solve problems.
    """
    
    def __init__(self, replicate_api):
        self.replicate = replicate_api
        self.executor = ThreadPoolExecutor(max_workers=4)
        
    async def orchestrate(self, task: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Intelligently orchestrate multiple agents to accomplish a complex task.
        Uses keyword detection to build a real execution plan.
        """
        context = context or {}
        results = {'steps': [], 'outputs': {}, 'success': True, 'final_summary': ''}
        
        task_lower = task.lower()
        
        # Detect what kind of workflow this is
        workflow_type = self._detect_workflow_type(task_lower)
        
        # Build execution plan based on workflow type
        plan = self._build_execution_plan(workflow_type, task, context)
        
        st.info(f"🧠 **Multi-Agent Plan**: {len(plan['steps'])} steps detected")
        
        # Execute each step with real progress
        progress_bar = st.progress(0)
        status_container = st.empty()
        
        for i, step in enumerate(plan['steps']):
            step_name = step.get('name', f"Step {i+1}")
            status_container.markdown(f"⏳ **Executing**: {step_name}...")
            
            try:
                step_result = await self._execute_step(step, context, results)
                results['steps'].append({
                    'step': step,
                    'result': step_result,
                    'status': 'success'
                })
                # Update context with step results for chaining
                if step_result.get('context_updates'):
                    context.update(step_result['context_updates'])
                    
                status_container.markdown(f"✅ **Completed**: {step_name}")
                
            except Exception as e:
                logger.error(f"Step failed: {step_name} - {e}")
                results['steps'].append({
                    'step': step,
                    'error': str(e),
                    'status': 'failed'
                })
                status_container.markdown(f"❌ **Failed**: {step_name} - {str(e)}")
                if step.get('critical', True):
                    results['success'] = False
                    break
            
            progress_bar.progress((i + 1) / len(plan['steps']))
        
        # Generate final summary
        results['final_summary'] = self._generate_summary(results, context)
        
        return results
    
    def _detect_workflow_type(self, task: str) -> str:
        """Detect the type of workflow from the task description."""
        
        # Campaign creation workflow
        if any(kw in task for kw in ['campaign', 't-shirt', 'tshirt', 'hoodie', 'poster', 'product']):
            if any(kw in task for kw in ['video', 'commercial', 'promo']):
                return 'full_campaign_with_video'
            return 'product_campaign'
        
        # Video workflow
        if any(kw in task for kw in ['video', 'commercial', 'animation']):
            return 'video_production'
        
        # Content workflow
        if any(kw in task for kw in ['blog', 'article', 'content', 'write', 'copy']):
            return 'content_creation'
        
        # Social media workflow
        if any(kw in task for kw in ['social', 'post', 'twitter', 'instagram', 'facebook']):
            return 'social_media'
        
        # Research workflow
        if any(kw in task for kw in ['research', 'analyze', 'trend', 'market']):
            return 'research'
        
        return 'general'
    
    def _build_execution_plan(self, workflow_type: str, task: str, context: Dict) -> Dict:
        """Build a concrete execution plan based on workflow type."""
        
        if workflow_type == 'full_campaign_with_video':
            return {
                'type': workflow_type,
                'steps': [
                    {'name': '🎨 Generate Product Design', 'agent': 'designer', 'action': 'generate_design', 'params': {'task': task}},
                    {'name': '✍️ Write Product Description', 'agent': 'writer', 'action': 'product_description', 'params': {'task': task}},
                    {'name': '📝 Create Video Script', 'agent': 'writer', 'action': 'video_script', 'params': {'task': task}},
                    {'name': '🎬 Generate Promo Video', 'agent': 'video', 'action': 'generate', 'params': {'task': task}},
                    {'name': '📢 Create Social Posts', 'agent': 'marketer', 'action': 'social_posts', 'params': {'task': task}},
                    {'name': '📊 Campaign Summary', 'agent': 'analyst', 'action': 'summarize', 'params': {'task': task}},
                ]
            }
        
        elif workflow_type == 'product_campaign':
            return {
                'type': workflow_type,
                'steps': [
                    {'name': '🎨 Generate Product Design', 'agent': 'designer', 'action': 'generate_design', 'params': {'task': task}},
                    {'name': '✍️ Write Product Copy', 'agent': 'writer', 'action': 'product_description', 'params': {'task': task}},
                    {'name': '🏷️ Generate Product Tags', 'agent': 'writer', 'action': 'tags', 'params': {'task': task}},
                    {'name': '📢 Create Marketing Copy', 'agent': 'marketer', 'action': 'marketing_copy', 'params': {'task': task}},
                ]
            }
        
        elif workflow_type == 'video_production':
            return {
                'type': workflow_type,
                'steps': [
                    {'name': '📝 Write Video Script', 'agent': 'writer', 'action': 'video_script', 'params': {'task': task}},
                    {'name': '🎨 Create Video Thumbnail', 'agent': 'designer', 'action': 'thumbnail', 'params': {'task': task}},
                    {'name': '🎬 Generate Video', 'agent': 'video', 'action': 'generate', 'params': {'task': task}},
                ]
            }
        
        elif workflow_type == 'content_creation':
            return {
                'type': workflow_type,
                'steps': [
                    {'name': '🔍 Research Topic', 'agent': 'researcher', 'action': 'research', 'params': {'task': task}},
                    {'name': '📝 Write Outline', 'agent': 'writer', 'action': 'outline', 'params': {'task': task}},
                    {'name': '✍️ Write Full Content', 'agent': 'writer', 'action': 'full_content', 'params': {'task': task}},
                    {'name': '🎨 Create Header Image', 'agent': 'designer', 'action': 'header_image', 'params': {'task': task}},
                ]
            }
        
        elif workflow_type == 'social_media':
            return {
                'type': workflow_type,
                'steps': [
                    {'name': '📢 Create Social Posts', 'agent': 'marketer', 'action': 'social_posts', 'params': {'task': task}},
                    {'name': '🎨 Generate Post Images', 'agent': 'designer', 'action': 'social_images', 'params': {'task': task}},
                    {'name': '#️⃣ Generate Hashtags', 'agent': 'writer', 'action': 'hashtags', 'params': {'task': task}},
                ]
            }
        
        elif workflow_type == 'research':
            return {
                'type': workflow_type,
                'steps': [
                    {'name': '🔍 Deep Research', 'agent': 'researcher', 'action': 'deep_research', 'params': {'task': task}},
                    {'name': '📊 Analyze Findings', 'agent': 'analyst', 'action': 'analyze', 'params': {'task': task}},
                    {'name': '📝 Write Report', 'agent': 'writer', 'action': 'report', 'params': {'task': task}},
                ]
            }
        
        # General fallback
        return {
            'type': 'general',
            'steps': [
                {'name': '🤔 Analyze Request', 'agent': 'analyst', 'action': 'analyze_request', 'params': {'task': task}},
                {'name': '✍️ Generate Response', 'agent': 'writer', 'action': 'respond', 'params': {'task': task}},
            ]
        }
    
    async def _execute_step(self, step: Dict, context: Dict, results: Dict) -> Dict:
        """Execute a single step using the appropriate agent."""
        agent = step.get('agent', 'writer')
        action = step.get('action', 'respond')
        params = step.get('params', {})
        task = params.get('task', '')
        
        # Designer agent
        if agent == 'designer':
            return await self._execute_design(action, task, context)
        
        # Writer agent
        elif agent == 'writer':
            return await self._execute_writing(action, task, context)
        
        # Video agent
        elif agent == 'video':
            return await self._execute_video(action, task, context)
        
        # Marketer agent
        elif agent == 'marketer':
            return await self._execute_marketing(action, task, context)
        
        # Researcher agent
        elif agent == 'researcher':
            return await self._execute_research(action, task, context)
        
        # Analyst agent
        elif agent == 'analyst':
            return await self._execute_analysis(action, task, context)
        
        return {'output': 'Step completed', 'type': 'status'}
    
    async def _execute_design(self, action: str, task: str, context: Dict) -> Dict:
        """Execute design-related actions with model detection."""
        
        # Detect which image model to use
        task_lower = task.lower()
        image_model = None
        
        if "ideogram" in task_lower:
            image_model = "ideogram-ai/ideogram-v2"
        elif "dall-e" in task_lower or "dalle" in task_lower:
            image_model = "openai/dall-e-3"
        elif "sdxl" in task_lower or "stable diffusion" in task_lower:
            image_model = "stability-ai/sdxl"
        elif "flux schnell" in task_lower or "flux-schnell" in task_lower or "fast flux" in task_lower:
            image_model = "black-forest-labs/flux-schnell"
        elif "flux fast" in task_lower or "pruna" in task_lower:
            image_model = "prunaai/flux-fast"
        elif "flux" in task_lower:
            image_model = "black-forest-labs/flux-dev"
        # Default is flux-dev via generate_image
        
        # Build a focused design prompt
        design_prompt = f"Professional product design: {task}. High quality, commercial ready, clean background, centered composition."
        
        if action == 'thumbnail':
            design_prompt = f"YouTube thumbnail style image for: {task}. Bold, eye-catching, vibrant colors."
        elif action == 'social_images':
            design_prompt = f"Social media post image for: {task}. Square format, modern, engaging."
        elif action == 'header_image':
            design_prompt = f"Blog header image for: {task}. Wide format, professional, clean."
        
        try:
            # Use specific model if detected, otherwise default
            if image_model:
                st.info(f"🎨 Using {image_model} for image generation...")
                if "ideogram" in image_model:
                    image_url = self.replicate._run_model(
                        image_model,
                        {"prompt": design_prompt, "aspect_ratio": "1:1"}
                    )
                elif "dall-e" in image_model:
                    # DALL-E via Replicate (openai/dall-e-3 model)
                    try:
                        image_url = self.replicate._run_model(
                            "openai/dall-e-3",
                            {
                                "prompt": design_prompt,
                                "size": "1024x1024",
                                "quality": "standard"
                            }
                        )
                    except Exception as e:
                        st.warning(f"DALL-E via Replicate failed: {e}, falling back to Flux")
                        image_url = self.replicate.generate_image(prompt=design_prompt)
                else:
                    # Flux variants via Replicate
                    image_url = self.replicate._run_model(
                        image_model,
                        {"prompt": design_prompt, "width": 1024, "height": 1024}
                    )
            else:
                image_url = self.replicate.generate_image(
                    prompt=design_prompt,
                    width=1024,
                    height=1024,
                    aspect_ratio="1:1"
                )
            
            # Display the image
            st.image(image_url, caption=f"Generated: {action}", use_container_width=True)
            
            return {
                'output': image_url,
                'type': 'image',
                'context_updates': {'generated_image': image_url, 'design_prompt': design_prompt}
            }
        except Exception as e:
            return {'output': f'Design generation failed: {e}', 'type': 'error'}
    
    async def _execute_writing(self, action: str, task: str, context: Dict) -> Dict:
        """Execute writing-related actions."""
        
        prompts = {
            'product_description': f"Write a compelling product description (2-3 paragraphs) for: {task}. Focus on benefits, features, and emotional appeal. No marketing fluff, just honest and engaging copy.",
            
            'video_script': f"Write a 30-second video script for: {task}. Include: [VISUAL] cues and [VOICEOVER] text. Keep it punchy and engaging.",
            
            'tags': f"Generate 10 relevant product tags/keywords for: {task}. Format as comma-separated list.",
            
            'outline': f"Create a detailed outline for content about: {task}. Include main sections and key points.",
            
            'full_content': f"Write comprehensive content about: {task}. Use the context if available: {context.get('outline', '')}. Make it informative and engaging.",
            
            'hashtags': f"Generate 15 relevant hashtags for social media about: {task}. Mix popular and niche tags.",
            
            'report': f"Write a concise report summarizing findings about: {task}. Based on research: {context.get('research', '')}",
            
            'respond': f"Provide a helpful, detailed response to: {task}"
        }
        
        prompt = prompts.get(action, prompts['respond'])
        
        try:
            response = self.replicate.generate_text(
                prompt=prompt,
                max_tokens=800,
                temperature=0.7
            )
            
            # Clean up the response
            response = response.strip()
            
            # Display in an expander
            with st.expander(f"📝 {action.replace('_', ' ').title()}", expanded=True):
                st.markdown(response)
            
            return {
                'output': response,
                'type': 'text',
                'context_updates': {action: response}
            }
        except Exception as e:
            return {'output': f'Writing failed: {e}', 'type': 'error'}
    
    async def _execute_video(self, action: str, task: str, context: Dict) -> Dict:
        """Execute video-related actions with model selection support."""
        
        # Check if we have an image to animate
        image_url = context.get('generated_image')
        
        if not image_url:
            return {
                'output': '⚠️ Video generation requires an image first. Design step should run before video.',
                'type': 'warning',
                'context_updates': {}
            }
        
        # Detect model preference from task
        task_lower = task.lower()
        video_model = None
        video_model_name = "Kling v2.5"
        
        if any(kw in task_lower for kw in ['sora', 'openai video', 'cinematic']):
            video_model = "openai/sora-2"
            video_model_name = "Sora-2"
        elif any(kw in task_lower for kw in ['luma', 'ray flash', 'ray-flash']):
            video_model = "luma/ray-flash-2" if 'flash' in task_lower else "luma/ray-2"
            video_model_name = "Luma Ray Flash 2" if 'flash' in task_lower else "Luma Ray 2"
        elif any(kw in task_lower for kw in ['minimax', 'hailuo']):
            video_model = "minimax/video-01-live"
            video_model_name = "Minimax Hailuo"
        elif any(kw in task_lower for kw in ['ken burns', 'zoom effect']):
            video_model = "ken_burns"
            video_model_name = "Ken Burns (Free)"
        
        try:
            video_prompt = f"Gentle motion, professional product showcase: {task}"
            
            st.info(f"🎬 Generating video with {video_model_name}... (this takes 1-2 minutes)")
            
            if video_model == "ken_burns":
                # Ken Burns effect - free, instant
                from modules.video_generation import generate_ken_burns_video
                import tempfile
                import requests
                
                response = requests.get(image_url, timeout=30)
                if response.status_code != 200:
                    raise Exception("Failed to download image for Ken Burns")
                
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    tmp.write(response.content)
                    image_path = tmp.name
                
                video_output = image_path.replace(".png", "_kenburns.mp4")
                generate_ken_burns_video(image_path, video_output, duration=5)
                video_url = video_output
                
            elif video_model and video_model != "kwaivgi/kling-v2.5-turbo-pro":
                # Use specific model via replicate
                import replicate
                input_data = {"prompt": video_prompt}
                if image_url:
                    input_data["image"] = image_url
                output = replicate.run(video_model, input=input_data)
                video_url = str(output) if output else None
            else:
                # Default: Use ReplicateAPI's generate_video (Kling)
                video_url = self.replicate.generate_video(
                    prompt=video_prompt,
                    image_url=image_url,
                    aspect_ratio="16:9",
                    motion_level=3
                )
            
            if video_url:
                st.video(video_url)
                return {
                    'output': video_url,
                    'type': 'video',
                    'model': video_model_name,
                    'context_updates': {'generated_video': video_url}
                }
            else:
                return {'output': 'Video generation returned no result', 'type': 'error'}
                
        except Exception as e:
            return {'output': f'Video generation failed: {e}', 'type': 'error'}
    
    async def _execute_marketing(self, action: str, task: str, context: Dict) -> Dict:
        """Execute marketing-related actions."""
        
        prompts = {
            'social_posts': f"""Create 3 social media posts for: {task}

Format each as:
**Platform**: [Twitter/Instagram/Facebook]
**Post**: [The actual post text]
**CTA**: [Call to action]

Keep them casual, engaging, and platform-appropriate.""",
            
            'marketing_copy': f"Write compelling marketing copy for: {task}. Include a headline, subheadline, and 3 bullet points highlighting key benefits."
        }
        
        prompt = prompts.get(action, prompts['marketing_copy'])
        
        try:
            response = self.replicate.generate_text(
                prompt=prompt,
                max_tokens=600,
                temperature=0.8
            )
            
            with st.expander(f"📢 {action.replace('_', ' ').title()}", expanded=True):
                st.markdown(response)
            
            return {
                'output': response,
                'type': 'text',
                'context_updates': {action: response}
            }
        except Exception as e:
            return {'output': f'Marketing content failed: {e}', 'type': 'error'}
    
    async def _execute_research(self, action: str, task: str, context: Dict) -> Dict:
        """Execute research-related actions."""
        
        prompt = f"""Research and analyze: {task}

Provide:
1. Key insights and trends
2. Target audience analysis
3. Competitor landscape overview
4. Opportunities and recommendations

Be specific and actionable."""
        
        try:
            response = self.replicate.generate_text(
                prompt=prompt,
                max_tokens=800,
                temperature=0.5
            )
            
            with st.expander("🔍 Research Findings", expanded=True):
                st.markdown(response)
            
            return {
                'output': response,
                'type': 'text',
                'context_updates': {'research': response}
            }
        except Exception as e:
            return {'output': f'Research failed: {e}', 'type': 'error'}
    
    async def _execute_analysis(self, action: str, task: str, context: Dict) -> Dict:
        """Execute analysis-related actions."""
        
        if action == 'summarize':
            # Summarize what was created
            created_items = []
            if context.get('generated_image'):
                created_items.append("✅ Product design image")
            if context.get('product_description'):
                created_items.append("✅ Product description")
            if context.get('video_script'):
                created_items.append("✅ Video script")
            if context.get('generated_video'):
                created_items.append("✅ Promotional video")
            if context.get('social_posts'):
                created_items.append("✅ Social media posts")
            if context.get('marketing_copy'):
                created_items.append("✅ Marketing copy")
            if context.get('tags'):
                created_items.append("✅ Product tags")
            
            summary = "### 📊 Campaign Summary\n\n**Created Assets:**\n" + "\n".join(created_items)
            
            st.markdown(summary)
            
            return {
                'output': summary,
                'type': 'summary',
                'context_updates': {'campaign_summary': summary}
            }
        
        prompt = f"Analyze and provide insights on: {task}"
        
        try:
            response = self.replicate.generate_text(
                prompt=prompt,
                max_tokens=500,
                temperature=0.5
            )
            
            return {
                'output': response,
                'type': 'text',
                'context_updates': {'analysis': response}
            }
        except Exception as e:
            return {'output': f'Analysis failed: {e}', 'type': 'error'}
    
    def _generate_summary(self, results: Dict, context: Dict) -> str:
        """Generate a final summary of the orchestration with actual outputs."""
        
        successful = sum(1 for s in results['steps'] if s['status'] == 'success')
        failed = sum(1 for s in results['steps'] if s['status'] == 'failed')
        
        summary_parts = [
            f"### 🎯 Orchestration Complete",
            f"",
            f"**Results:** {successful} succeeded, {failed} failed",
            f""
        ]
        
        # Include actual generated image with markdown
        if context.get('generated_image'):
            image_url = context['generated_image']
            summary_parts.append(f"---")
            summary_parts.append(f"#### 🎨 Generated Design")
            summary_parts.append(f"![Generated Image]({image_url})")
            summary_parts.append(f"")
            # Store in session state for later use
            if 'otto_generated_images' not in st.session_state:
                st.session_state.otto_generated_images = []
            st.session_state.otto_generated_images.append(image_url)
        
        # Include generated video
        if context.get('generated_video'):
            video_url = context['generated_video']
            summary_parts.append(f"---")
            summary_parts.append(f"#### 🎬 Generated Video")
            summary_parts.append(f"[▶️ View Video]({video_url})")
            summary_parts.append(f"")
        
        # Include product description
        if context.get('product_description'):
            summary_parts.append(f"---")
            summary_parts.append(f"#### ✍️ Product Description")
            summary_parts.append(f"{context['product_description']}")
            summary_parts.append(f"")
        
        # Include marketing copy
        if context.get('marketing_copy'):
            summary_parts.append(f"---")
            summary_parts.append(f"#### 📢 Marketing Copy")
            summary_parts.append(f"{context['marketing_copy']}")
            summary_parts.append(f"")
        
        # Include tags
        if context.get('tags'):
            summary_parts.append(f"---")
            summary_parts.append(f"#### 🏷️ Tags")
            summary_parts.append(f"{context['tags']}")
            summary_parts.append(f"")
        
        # Include social posts
        if context.get('social_posts'):
            summary_parts.append(f"---")
            summary_parts.append(f"#### 📱 Social Media Posts")
            summary_parts.append(f"{context['social_posts']}")
            summary_parts.append(f"")
        
        # Include video script
        if context.get('video_script'):
            summary_parts.append(f"---")
            summary_parts.append(f"#### 🎬 Video Script")
            summary_parts.append(f"{context['video_script']}")
            summary_parts.append(f"")
        
        return "\n".join(summary_parts)
