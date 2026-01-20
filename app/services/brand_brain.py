"""
Brand Brain System
Centralized brand asset management and brand-aware content generation
"""

import streamlit as st
from pathlib import Path
import yaml
import json
from datetime import datetime as dt
from typing import Dict, List, Optional
import shutil
import logging

logger = logging.getLogger(__name__)


class BrandBrain:
    """Manages brand assets, guidelines, and brand-aware content generation"""
    
    def __init__(self, brand_dir='brand_brain'):
        self.brand_dir = Path(brand_dir)
        self.assets_dir = self.brand_dir / 'assets'
        self.logos_dir = self.assets_dir / 'logos'
        self.fonts_dir = self.assets_dir / 'fonts'
        self.colors_dir = self.assets_dir / 'colors'
        self.guidelines_dir = self.assets_dir / 'guidelines'
        self.embeddings_dir = self.brand_dir / 'embeddings'
        self.config_dir = self.brand_dir / 'config'
        self.config_file = self.config_dir / 'brand_profile.yaml'
        
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create brand brain directory structure"""
        for directory in [
            self.logos_dir, self.fonts_dir, self.colors_dir,
            self.guidelines_dir, self.embeddings_dir, self.config_dir
        ]:
            directory.mkdir(parents=True, exist_ok=True)
    
    # ============================================
    # ASSET MANAGEMENT
    # ============================================
    
    def save_asset(self, uploaded_file, category: str) -> str:
        """
        Save uploaded asset to appropriate folder
        
        Args:
            uploaded_file: Streamlit UploadedFile
            category: 'logo', 'font', 'guideline', etc.
        
        Returns:
            Path to saved file
        """
        category_map = {
            'logo': self.logos_dir,
            'font': self.fonts_dir,
            'guideline': self.guidelines_dir
        }
        
        target_dir = category_map.get(category, self.assets_dir)
        file_path = target_dir / uploaded_file.name
        
        with open(file_path, 'wb') as f:
            f.write(uploaded_file.getbuffer())
        
        logger.info(f"Saved {category} asset: {file_path}")
        return str(file_path)
    
    def get_assets(self, category: str) -> List[Path]:
        """Get all assets in a category"""
        category_map = {
            'logo': self.logos_dir,
            'font': self.fonts_dir,
            'guideline': self.guidelines_dir
        }
        
        target_dir = category_map.get(category, self.assets_dir)
        return list(target_dir.glob('*')) if target_dir.exists() else []
    
    def delete_asset(self, file_path: str):
        """Delete an asset"""
        Path(file_path).unlink(missing_ok=True)
        logger.info(f"Deleted asset: {file_path}")
    
    def _read_file_content(self, file_path: Path) -> str:
        """Read content from a file based on its extension."""
        suffix = file_path.suffix.lower()
        if suffix in ['.txt', '.md', '.json', '.yaml', '.yml']:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        elif suffix == '.pdf':
            try:
                import pypdf
                reader = pypdf.PdfReader(file_path)
                return "\n".join(page.extract_text() for page in reader.pages)
            except ImportError:
                return f"[PDF Processing Unavailable for {file_path.name}]"
            except Exception as e:
                return f"[Error reading PDF {file_path.name}: {str(e)}]"
        return ""

    def process_knowledge_base(self) -> Dict:
        """
        Process all files in guidelines directory and create a knowledge base
        
        Returns:
            Dict containing processed text from all documents
        """
        knowledge_base = {
            "documents": [],
            "last_updated": str(dt.now()),
            "total_docs": 0
        }
        
        guideline_files = self.get_assets('guideline')
        
        for file_path in guideline_files:
            try:
                content = self._read_file_content(file_path)
                
                if content:
                    knowledge_base["documents"].append({
                        "filename": file_path.name,
                        "content": content[:50000],  # Limit content per file to avoid context overflow
                        "type": file_path.suffix.lower()
                    })
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
        
        knowledge_base["total_docs"] = len(knowledge_base["documents"])
        
        # Save processed knowledge base
        kb_file = self.brand_dir / 'brand_knowledge.json'
        with open(kb_file, 'w') as f:
            json.dump(knowledge_base, f, indent=2)
            
        return knowledge_base

    def get_knowledge_base(self) -> Dict:
        """Get processed knowledge base"""
        kb_file = self.brand_dir / 'brand_knowledge.json'
        if kb_file.exists():
            try:
                with open(kb_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    # ============================================
    # BRAND PROFILE MANAGEMENT
    # ============================================
    
    def load_profile(self) -> Dict:
        """Load brand profile from YAML"""
        if self.config_file.exists():
            with open(self.config_file) as f:
                return yaml.safe_load(f)
        return self._get_default_profile()
    
    def save_profile(self, profile: Dict):
        """Save brand profile to YAML"""
        with open(self.config_file, 'w') as f:
            yaml.dump(profile, f, default_flow_style=False, indent=2)
        logger.info("Brand profile saved")
    
    def update_profile(self, updates: Dict):
        """Update specific fields in brand profile"""
        profile = self.load_profile()
        profile.update(updates)
        self.save_profile(profile)
    
    def _get_default_profile(self) -> Dict:
        """Default brand profile template"""
        return {
            'brand_name': 'My Brand',
            'tagline': 'Your tagline here',
            'visual_identity': {
                'primary_colors': ['#667eea', '#764ba2'],
                'fonts': {
                    'primary': 'Montserrat',
                    'secondary': 'Open Sans'
                },
                'logo_files': {
                    'main': None,
                    'video': None,
                    'audio': None
                }
            },
            'writing_style': {
                'tone': ['professional', 'friendly'],
                'avoid': ['overly casual', 'excessive punctuation'],
                'voice': 'Clear and engaging',
                'examples': []
            },
            'content_guidelines': {
                'hashtags': [],
                'keywords': [],
                'cta_phrases': []
            },
            'social_media': {
                'instagram': {
                    'posting_frequency': 'Daily',
                    'best_times': ['9am', '3pm', '7pm'],
                    'content_mix': '60% product, 30% lifestyle, 10% behind-scenes'
                }
            },
            'target_audience': {
                'demographics': [],
                'interests': [],
                'pain_points': []
            }
        }
    
    # ============================================
    # BRAND-AWARE CONTENT GENERATION
    # ============================================
    
    def get_brand_context(self) -> str:
        """Get brand context as formatted text for AI prompts"""
        profile = self.load_profile()
        
        context = f"""BRAND: {profile['brand_name']}
TAGLINE: {profile['tagline']}

BRAND VOICE: {profile['writing_style']['voice']}
TONE: {', '.join(profile['writing_style']['tone'])}
AVOID: {', '.join(profile['writing_style']['avoid'])}

COLORS: {', '.join(profile['visual_identity']['primary_colors'])}
TARGET AUDIENCE: {', '.join(profile['target_audience']['demographics'])}

EXAMPLE POSTS THAT MATCH OUR STYLE:
{self._format_examples(profile['writing_style']['examples'])}

KEY HASHTAGS: {' '.join(profile['content_guidelines']['hashtags'])}
KEYWORDS: {', '.join(profile['content_guidelines']['keywords'])}
"""
        return context
    
    def _format_examples(self, examples: List[str]) -> str:
        """Format example posts"""
        if not examples:
            return "No examples provided yet"
        return '\n'.join(f"- {ex}" for ex in examples[:5])
    
    def enhance_prompt(self, base_prompt: str, content_type: str) -> str:
        """
        Enhance any prompt with brand context
        
        Args:
            base_prompt: Original prompt
            content_type: 'social_post', 'blog', 'email', 'video_script', etc.
        
        Returns:
            Enhanced prompt with brand guidelines
        """
        profile = self.load_profile()
        brand_context = self.get_brand_context()
        
        enhanced = f"""You are creating {content_type} for {profile['brand_name']}.

{brand_context}

Now generate the following, matching our brand style and tone:

{base_prompt}

IMPORTANT: Maintain brand consistency. Match the style of our example posts above."""
        
        return enhanced
    
    # ============================================
    # WRITING STYLE ANALYSIS
    # ============================================
    
    def analyze_writing_samples(self, samples: str, api_client) -> Dict:
        """
        Analyze writing samples to extract style patterns
        
        Args:
            samples: Text samples (social posts, blog excerpts, etc.)
            api_client: Replicate API client for analysis
        
        Returns:
            Dictionary with extracted style characteristics
        """
        analysis_prompt = f"""Analyze the following writing samples and extract the brand voice characteristics:

{samples}

Extract:
1. Tone (e.g., professional, friendly, playful)
2. Common phrases and vocabulary
3. Sentence structure patterns
4. Emotional appeal (rational, emotional, inspirational)
5. Use of emojis, punctuation, formatting
6. Target audience indicators

Return as JSON:
{{
  "tone": ["word1", "word2"],
  "common_phrases": ["phrase1", "phrase2"],
  "sentence_patterns": "description",
  "emotional_appeal": "type",
  "formatting_style": "description",
  "target_audience": "description"
}}
"""
        
        try:
            result = api_client.generate_text(analysis_prompt, max_tokens=500)
            # Parse JSON from result
            import json
            import re
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {}
        except Exception as e:
            logger.error(f"Style analysis failed: {e}")
            return {}
    
    def train_from_examples(self, examples: List[str], api_client):
        """
        Train brand brain from example posts
        Updates brand profile with learned patterns
        """
        samples_text = '\n\n'.join(examples)
        analysis = self.analyze_writing_samples(samples_text, api_client)
        
        if analysis:
            # Update profile with learned patterns
            profile = self.load_profile()
            profile['writing_style']['tone'] = analysis.get('tone', profile['writing_style']['tone'])
            profile['writing_style']['examples'] = examples[:10]  # Store up to 10 examples
            self.save_profile(profile)
            
            return analysis
        return None
    
    # ============================================
    # ASSET APPLICATION
    # ============================================
    
    def apply_logo_to_video(self, video_path: str, position: str = 'bottom-right') -> str:
        """
        Add logo watermark to video
        
        Args:
            video_path: Path to video file
            position: 'top-left', 'top-right', 'bottom-left', 'bottom-right'
        
        Returns:
            Path to video with logo
        """
        profile = self.load_profile()
        logo_path = profile['visual_identity']['logo_files'].get('main')
        
        if not logo_path or not Path(logo_path).exists():
            logger.warning("No logo found, skipping watermark")
            return video_path
        
        try:
            from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip
            
            video = VideoFileClip(video_path)
            logo = ImageClip(logo_path).set_duration(video.duration)
            
            # Resize logo to 10% of video width
            logo = logo.resize(width=int(video.w * 0.1))
            
            # Position logo
            margins = 20
            positions = {
                'top-left': (margins, margins),
                'top-right': (video.w - logo.w - margins, margins),
                'bottom-left': (margins, video.h - logo.h - margins),
                'bottom-right': (video.w - logo.w - margins, video.h - logo.h - margins)
            }
            logo = logo.set_position(positions.get(position, positions['bottom-right']))
            
            # Composite
            final = CompositeVideoClip([video, logo])
            
            output_path = video_path.replace('.mp4', '_branded.mp4')
            final.write_videofile(output_path, codec='libx264', audio_codec='aac')
            
            return output_path
        except Exception as e:
            logger.error(f"Logo application failed: {e}")
            return video_path
    
    def apply_brand_colors_to_image(self, image_path: str) -> str:
        """Apply brand color filter to image"""
        try:
            from PIL import Image, ImageEnhance
            import numpy as np
            
            profile = self.load_profile()
            primary_colors = profile.get('visual_identity', {}).get('primary_colors', [])
            
            if not primary_colors:
                logger.warning("No brand colors defined, skipping color grading")
                return image_path
            
            # Load image
            img = Image.open(image_path)
            
            # Convert hex colors to RGB
            def hex_to_rgb(hex_color):
                hex_color = hex_color.lstrip('#')
                return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            
            brand_rgb = [hex_to_rgb(c) for c in primary_colors[:2]]  # Use first 2 colors
            
            # Apply subtle color overlay
            # Create a color overlay layer
            overlay = Image.new('RGB', img.size, brand_rgb[0])
            
            # Convert to RGBA for blending if needed
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            overlay = overlay.convert('RGBA')
            
            # Blend with low opacity (10-15%) to tint the image
            blended = Image.blend(img.convert('RGBA'), overlay, alpha=0.12)
            
            # Enhance saturation slightly to make brand colors pop
            enhancer = ImageEnhance.Color(blended.convert('RGB'))
            result = enhancer.enhance(1.15)
            
            # Save result
            output_path = str(Path(image_path).parent / f"{Path(image_path).stem}_branded{Path(image_path).suffix}")
            result.save(output_path, quality=95)
            
            logger.info(f"Applied brand color grading: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Color grading failed: {e}")
            return image_path
    
    # ============================================
    # CHAT INTEGRATION
    # ============================================
    
    def get_chat_system_prompt(self) -> str:
        """Get enhanced system prompt for chat assistant"""
        profile = self.load_profile()
        
        return f"""You are a Personal Assistant for {profile['brand_name']}.

{self.get_brand_context()}

Always maintain brand consistency in your responses. Use the brand voice and tone described above.
When generating content, match the style of the example posts provided.
"""


# ============================================
# STREAMLIT UI FOR BRAND BRAIN
# ============================================

def render_brand_brain_page():
    """Render Brand Brain management page"""
    st.title("🧠 Brand Brain")
    st.markdown("Centralize your brand assets and train AI to maintain brand consistency")
    
    # Initialize brand brain
    brain = BrandBrain()
    
    tabs = st.tabs([
        "📁 Assets", 
        "✍️ Writing Style", 
        "🎨 Visual Identity", 
        "🤖 AI Training",
        "📊 Brand Profile"
    ])
    
    # ============================================
    # TAB 1: ASSETS
    # ============================================
    with tabs[0]:
        st.subheader("Brand Assets Library")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Logos")
            uploaded_logo = st.file_uploader(
                "Upload Main Logo", 
                type=['png', 'jpg', 'svg', 'pdf'],
                key='logo_main'
            )
            if uploaded_logo:
                path = brain.save_asset(uploaded_logo, 'logo')
                st.success(f"✅ Saved: {uploaded_logo.name}")
                st.image(path, width=200)
            
            uploaded_video_logo = st.file_uploader(
                "Upload Video Logo/Intro", 
                type=['mp4', 'mov'],
                key='logo_video'
            )
            if uploaded_video_logo:
                path = brain.save_asset(uploaded_video_logo, 'logo')
                st.success(f"✅ Saved: {uploaded_video_logo.name}")
            
            uploaded_audio_logo = st.file_uploader(
                "Upload Audio Logo/Jingle", 
                type=['mp3', 'wav'],
                key='logo_audio'
            )
            if uploaded_audio_logo:
                path = brain.save_asset(uploaded_audio_logo, 'logo')
                st.success(f"✅ Saved: {uploaded_audio_logo.name}")
        
        with col2:
            st.markdown("### Fonts")
            uploaded_fonts = st.file_uploader(
                "Upload Brand Fonts", 
                type=['ttf', 'otf'], 
                accept_multiple_files=True,
                key='fonts'
            )
            if uploaded_fonts:
                for font_file in uploaded_fonts:
                    path = brain.save_asset(font_file, 'font')
                    st.success(f"✅ Saved: {font_file.name}")
        
        st.markdown("---")
        st.markdown("### Existing Assets")
        
        logos = brain.get_assets('logo')
        fonts = brain.get_assets('font')
        
        if logos:
            st.markdown(f"**Logos**: {len(logos)} files")
            for logo in logos:
                col_a, col_b = st.columns([4, 1])
                with col_a:
                    st.text(logo.name)
                with col_b:
                    if st.button("🗑️", key=f"del_logo_{logo.name}"):
                        brain.delete_asset(str(logo))
                        st.rerun()
        
        if fonts:
            st.markdown(f"**Fonts**: {len(fonts)} files")
            for font in fonts:
                st.text(f"• {font.name}")
    
    # ============================================
    # TAB 2: WRITING STYLE
    # ============================================
    with tabs[1]:
        st.subheader("Brand Voice & Writing Style")
        
        profile = brain.load_profile()
        
        col1, col2 = st.columns(2)
        
        with col1:
            tone_options = [
                "Professional", "Friendly", "Playful", "Luxury", 
                "Casual", "Authoritative", "Inspirational", "Humorous"
            ]
            tone = st.multiselect(
                "Brand Tone",
                tone_options,
                default=profile['writing_style']['tone']
            )
            
            voice = st.text_area(
                "Brand Voice Description",
                value=profile['writing_style']['voice'],
                help="Describe your brand's unique voice"
            )
        
        with col2:
            avoid = st.text_area(
                "Avoid (comma-separated)",
                value=', '.join(profile['writing_style']['avoid']),
                help="Words, phrases, or styles to avoid"
            )
        
        st.markdown("---")
        st.subheader("Example Content")
        st.info("Paste 5-10 examples of your best social posts, emails, or blog excerpts")
        
        examples_text = st.text_area(
            "Example Posts (one per line)",
            value='\n\n'.join(profile['writing_style']['examples']),
            height=300
        )
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("🧠 Analyze Writing Style with AI"):
                if examples_text.strip():
                    # Get Replicate API
                    from performance_utils import get_replicate_api
                    import os
                    
                    token = get_api_key('REPLICATE_API_TOKEN')
                    if token:
                        api = get_replicate_api(token)
                        
                        with st.spinner("Analyzing your writing style..."):
                            examples_list = [ex.strip() for ex in examples_text.split('\n\n') if ex.strip()]
                            analysis = brain.train_from_examples(examples_list, api)
                            
                            if analysis:
                                st.success("✅ Style analysis complete!")
                                st.json(analysis)
                            else:
                                st.error("❌ Analysis failed")
                    else:
                        st.error("Replicate API token required")
                else:
                    st.warning("Please provide example content first")
        
        with col_btn2:
            if st.button("💾 Save Writing Style"):
                profile['writing_style']['tone'] = tone
                profile['writing_style']['voice'] = voice
                profile['writing_style']['avoid'] = [a.strip() for a in avoid.split(',')]
                profile['writing_style']['examples'] = [
                    ex.strip() for ex in examples_text.split('\n\n') if ex.strip()
                ]
                brain.save_profile(profile)
                st.success("✅ Writing style saved!")
                st.rerun()
    
    # ============================================
    # TAB 3: VISUAL IDENTITY
    # ============================================
    with tabs[2]:
        st.subheader("Visual Brand Identity")
        
        profile = brain.load_profile()
        
        st.markdown("### Color Palette")
        col1, col2, col3 = st.columns(3)
        
        colors = profile['visual_identity'].get('primary_colors', ['#667eea', '#764ba2', '#ffffff'])
        while len(colors) < 5:
            colors.append('#000000')
        
        with col1:
            color1 = st.color_picker("Primary Color", colors[0])
        with col2:
            color2 = st.color_picker("Secondary Color", colors[1])
        with col3:
            color3 = st.color_picker("Accent Color", colors[2])
        
        col4, col5 = st.columns(2)
        with col4:
            color4 = st.color_picker("Background Color", colors[3])
        with col5:
            color5 = st.color_picker("Text Color", colors[4])
        
        st.markdown("---")
        st.markdown("### Typography")
        
        col1, col2 = st.columns(2)
        with col1:
            primary_font = st.text_input(
                "Primary Font",
                value=profile['visual_identity']['fonts'].get('primary', 'Montserrat')
            )
        with col2:
            secondary_font = st.text_input(
                "Secondary Font",
                value=profile['visual_identity']['fonts'].get('secondary', 'Open Sans')
            )
        
        st.markdown("---")
        st.markdown("### Design Guidelines")
        
        visual_style = st.text_area(
            "Visual Style Description",
            value=profile.get('visual_style_description', ''),
            help="Describe your brand's visual aesthetic"
        )
        
        if st.button("💾 Save Visual Identity"):
            profile['visual_identity']['primary_colors'] = [color1, color2, color3, color4, color5]
            profile['visual_identity']['fonts']['primary'] = primary_font
            profile['visual_identity']['fonts']['secondary'] = secondary_font
            profile['visual_style_description'] = visual_style
            brain.save_profile(profile)
            st.success("✅ Visual identity saved!")
            st.rerun()
    
    # ============================================
    # TAB 4: AI TRAINING
    # ============================================
    with tabs[3]:
        st.subheader("Train AI Chat Assistant")
        st.info("Upload documents, FAQs, and brand info to train your AI assistant with brand knowledge")
        
        knowledge_files = st.file_uploader(
            "Upload Knowledge Base Documents",
            type=['txt', 'md', 'pdf', 'docx'],
            accept_multiple_files=True
        )
        
        if knowledge_files:
            st.success(f"✅ {len(knowledge_files)} files uploaded")
            
            if st.button("📚 Process & Train"):
                with st.spinner("Training AI assistant..."):
                    # Save files first
                    for file in knowledge_files:
                        brain.save_asset(file, 'guideline')
                    
                    # Process knowledge base
                    kb_result = brain.process_knowledge_base()
                    doc_count = kb_result.get('total_docs', 0)
                    st.success(f"✅ AI assistant trained with {doc_count} documents from your brand knowledge!")
        
        st.markdown("---")
        st.markdown("### Test Brand Context")
        
        if st.button("👁️ Preview Brand Context for AI"):
            context = brain.get_brand_context()
            st.code(context, language='text')
        
        if st.button("🧪 Test Enhanced Prompt"):
            test_prompt = "Create a social media post about our new product"
            enhanced = brain.enhance_prompt(test_prompt, "social_post")
            st.markdown("**Original Prompt:**")
            st.text(test_prompt)
            st.markdown("**Enhanced Prompt with Brand Context:**")
            st.code(enhanced, language='text')
    
    # ============================================
    # TAB 5: BRAND PROFILE
    # ============================================
    with tabs[4]:
        st.subheader("Complete Brand Profile")
        
        profile = brain.load_profile()
        
        col1, col2 = st.columns(2)
        
        with col1:
            brand_name = st.text_input("Brand Name", value=profile.get('brand_name', ''))
            tagline = st.text_input("Tagline", value=profile.get('tagline', ''))
        
        with col2:
            hashtags = st.text_input(
                "Key Hashtags (comma-separated)",
                value=', '.join(profile['content_guidelines'].get('hashtags', []))
            )
            keywords = st.text_input(
                "Keywords (comma-separated)",
                value=', '.join(profile['content_guidelines'].get('keywords', []))
            )
        
        st.markdown("---")
        st.subheader("Target Audience")
        
        demographics = st.text_input(
            "Demographics",
            value=', '.join(profile['target_audience'].get('demographics', []))
        )
        interests = st.text_input(
            "Interests",
            value=', '.join(profile['target_audience'].get('interests', []))
        )
        
        if st.button("💾 Save Brand Profile"):
            profile['brand_name'] = brand_name
            profile['tagline'] = tagline
            profile['content_guidelines']['hashtags'] = [h.strip() for h in hashtags.split(',')]
            profile['content_guidelines']['keywords'] = [k.strip() for k in keywords.split(',')]
            profile['target_audience']['demographics'] = [d.strip() for d in demographics.split(',')]
            profile['target_audience']['interests'] = [i.strip() for i in interests.split(',')]
            brain.save_profile(profile)
            st.success("✅ Brand profile saved!")
            st.rerun()
        
        st.markdown("---")
        st.markdown("### Export/Import")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📥 Export Brand Profile"):
                yaml_content = yaml.dump(profile, default_flow_style=False)
                st.download_button(
                    "Download brand_profile.yaml",
                    data=yaml_content,
                    file_name="brand_profile.yaml",
                    mime="text/yaml"
                )
        
        with col2:
            import_file = st.file_uploader("Import Brand Profile", type=['yaml', 'yml'])
            if import_file:
                imported = yaml.safe_load(import_file)
                brain.save_profile(imported)
                st.success("✅ Brand profile imported!")
                st.rerun()
