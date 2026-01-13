"""
UI Components Module
Reusable UI components for the platform
"""

import streamlit as st
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def render_header():
    """Render the main platform header."""
    st.markdown('<h1 class="main-header">🚀 Autonomous Business Platform Pro</h1>', unsafe_allow_html=True)


def render_sidebar_stats():
    """Render statistics in the sidebar."""
    st.markdown("## 📊 Stats")
    
    # Session stats
    if 'total_campaigns' not in st.session_state:
        st.session_state.total_campaigns = 0
    if 'total_products' not in st.session_state:
        st.session_state.total_products = 0
    if 'total_videos' not in st.session_state:
        st.session_state.total_videos = 0
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Campaigns", st.session_state.total_campaigns)
        st.metric("Products", st.session_state.total_products)
    with col2:
        st.metric("Videos", st.session_state.total_videos)


def render_about_page():
    """Render the About page content."""
    with st.expander("🌟 Platform Overview", expanded=True):
        st.markdown("""
        ### Autonomous Business Platform Pro (Otto Mate)
        
        The ultimate AI-powered automation suite for print-on-demand e-commerce.
        50+ AI models • Multi-platform publishing • Truly autonomous workflows
        
        **Core Features**:
        - 🧠 **Otto AI**: Full platform control via conversational AI
        - 🎯 **Campaign Generator**: Complete marketing campaigns in minutes (~$0.50-1.00)
        - 📦 **Product Studio**: 8 styles + 7 color palettes, Printify integration
        - 🎬 **Video Producer**: 4-phase professional pipeline with voiceover & music
        - 🔍 **Contact Finder**: AI-powered outreach discovery (real contacts)
        - 📱 **Multi-Platform**: Twitter, Pinterest, TikTok, Instagram automation
        - 🤖 **Agent Builder**: Visual workflow automation with 50+ nodes
        
        **Version**: 2.1 Pro | **December 2025**
        """)
    
    with st.expander("🧠 Otto AI Assistant"):
        st.markdown("""
        Your hyperintelligent AI assistant with complete platform control.
        
        **Slash Commands**:
        - `/image [prompt]` — Generate images with FLUX-fast
        - `/video [prompt]` — Create videos with Kling v2.5
        - `/help` — Show available commands
        
        **Natural Language Examples**:
        - "Generate a campaign for eco-friendly water bottles"
        - "Post this design to Pinterest and TikTok"
        - "Find 20 influencers in the fitness niche"
        - "Schedule this content for next Tuesday"
        
        **Performance Features**:
        - Request caching (1-hour TTL)
        - Parallel execution (up to 4 concurrent)
        - Exponential backoff retry logic
        """)
    
    with st.expander("📚 Feature Breakdown"):
        st.markdown("""
        ### 🎯 Campaign Generator
        12-step full campaign generation:
        - Marketing plan & strategy
        - 6 images (3 marketing + 3 product variations)
        - Background removal
        - SEO blog post with images
        - Video commercial (15-30s)
        - Voiceover + music
        - YouTube upload
        - ZIP package
        
        ### 🎬 Video Producer
        4-phase production pipeline:
        1. Video (Kling v2.5, Sora 2, Veo 3)
        2. Voiceover (Minimax Speech-02-HD)
        3. Music (MusicGen, Lyria 2)
        4. Assembly (MoviePy mixing)
        
        ### 🔗 Integrations
        - **E-Commerce**: Printify, Shopify
        - **Video**: YouTube
        - **Social**: Twitter, Pinterest, TikTok, Instagram, Facebook, Reddit
        - **Email**: SendGrid, Gmail OAuth, SMTP
        """)


def render_command_reference():
    """Render command reference guide."""
    with st.expander("📖 Complete Slash Command Dictionary", expanded=True):
        st.markdown("""
        ## 🎨 Design & Creation Commands
        
        **Product Design:**
        - `/design <description>` - Generate product design
        - `/design batch <count> <description>` - Create multiple designs
        - `/mockup <product_id>` - Generate product mockup
        
        **Campaign Creation:**
        - `/campaign <concept>` - Create full marketing campaign
        - `/campaign quick <product>` - Fast campaign generation
        - `/social <product>` - Generate social media posts
        
        **Video Production:**
        - `/video <concept>` - Create promotional video
        - `/video ken-burns <images>` - Ken Burns effect video
        - `/video sora <concept>` - Sora-2 cinematic video
        - `/video kling <concept>` - Kling animated video
        
        ## 📊 Analysis & Insights
        
        - `/analyze campaign <id>` - Campaign performance
        - `/analyze product <id>` - Product metrics
        - `/suggest improvements` - AI recommendations
        - `/compare campaigns` - Side-by-side comparison
        
        ## 🔧 Utility Commands
        
        - `/help` - Show all commands
        - `/status` - Platform status
        - `/export <format>` - Export data
        - `/settings` - Open settings
        
        ## 🚀 Automation
        
        - `/automate <workflow>` - Set up automation
        - `/schedule <task> <time>` - Schedule generation
        - `/batch <operation>` - Batch processing
        """)


def render_feature_card(icon: str, title: str, description: str, color: str = "blue"):
    """Render a feature card."""
    colors = {
        "blue": "#667eea",
        "purple": "#764ba2",
        "green": "#2f855a",
        "orange": "#ed8936"
    }
    
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, {colors.get(color, colors['blue'])} 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    ">
        <h3>{icon} {title}</h3>
        <p>{description}</p>
    </div>
    """, unsafe_allow_html=True)


def render_progress_indicator(current: int, total: int, label: str = "Progress"):
    """Render a progress indicator."""
    progress = current / total if total > 0 else 0
    st.progress(progress, text=f"{label}: {current}/{total} ({progress*100:.0f}%)")


def render_metric_card(label: str, value: str, delta: str = None, icon: str = "📊"):
    """Render a metric card with optional delta."""
    col1, col2 = st.columns([1, 4])
    with col1:
        st.markdown(f"<h1 style='text-align: center;'>{icon}</h1>", unsafe_allow_html=True)
    with col2:
        st.metric(label=label, value=value, delta=delta)


def render_success_message(message: str, details: str = None):
    """Render a success message with optional details."""
    st.success(f"✅ {message}")
    if details:
        st.caption(details)


def render_error_message(message: str, details: str = None, show_help: bool = True):
    """Render an error message with optional details and help."""
    st.error(f"❌ {message}")
    if details:
        with st.expander("🔍 Error Details"):
            st.code(details, language="text")
    if show_help:
        st.info("💡 Try checking your API keys in Settings, or contact support if the issue persists.")


def render_info_box(title: str, content: str, icon: str = "ℹ️"):
    """Render an info box."""
    st.info(f"{icon} **{title}**\n\n{content}")


def render_warning_box(title: str, content: str):
    """Render a warning box."""
    st.warning(f"⚠️ **{title}**\n\n{content}")
