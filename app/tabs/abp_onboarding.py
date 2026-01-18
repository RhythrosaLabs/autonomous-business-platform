"""
First-Time User Onboarding Experience
Makes the app more accessible and guides new users through key features
"""

import streamlit as st
from app.services.tab_visibility_manager import apply_role_preset, ROLE_PRESETS
from abp_onboarding_content import SIDEBAR_GUIDE, DASHBOARD_GUIDE, OTTO_GUIDE
from abp_onboarding_content2 import PLAYGROUND_GUIDE, INTEGRATIONS_GUIDE, AUTOMATIONS_GUIDE

def check_and_show_onboarding():
    """Check if user is new and show onboarding if needed"""
    if 'completed_onboarding' not in st.session_state:
        st.session_state.completed_onboarding = False
    
    if not st.session_state.completed_onboarding:
        show_onboarding_modal()

def show_onboarding_modal():
    """Display an interactive onboarding guide for first-time users"""
    
    # Less intrusive - just a compact banner
    with st.expander("👋 **New here?** Complete Platform Guide", expanded=False):
        # Tabs for different learning paths
        tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
            "🚀 Quick Start", 
            "🎯 Your Role", 
            "📋 Sidebar Guide",
            "🏠 Dashboard", 
            "🤖 Otto AI",
            "🎮 Playground",
            "🔗 Integrations",
            "⚙️ Automations"
        ])
        
        with tab1:
            st.markdown("**Your Autonomous Business Platform - Complete Guide**")
            
            st.markdown("""
            ### 🎯 Core Navigation
            - **🏠 Dashboard** - Command center with metrics, campaign launcher, recent activity
            - **⚡ Shortcuts** - Quick actions, saved workflows, recent items
            - **🤖 Task Queue** - Bulk operations, background processing, automation scheduling
            
            ### 🎨 Content Creation
            - **📦 Product Studio** - AI image generation, Printify mockups (850+ products), batch creation
            - **💾 Digital Products** - eBooks, courses, templates, landing pages
            - **📝 Content Generator** - Blog posts, product descriptions, social captions, SEO content
            - **🎬 Video Producer** - Sora/Kling/RunwayML videos, Ken Burns effects, YouTube upload
            - **🎮 Playground** - Test AI models, parameter tuning, A/B testing
            
            ### 📱 Marketing & Distribution
            - **🎯 Campaign Creator** - Complete 12-step campaigns (images, videos, blog, schedule, ZIP)
            - **💌 Email Outreach** - Influencer finder, HTML editor, templates, analytics
            - **🎵 Music Platforms** - Spotify/Apple Music distribution, AI music, artwork
            
            ### 🛠️ Workflows & Organization
            - **🔧 Workflows** - Visual automation builder, templates, API integrations
            - **📅 Calendar** - Content scheduling, launches, team collaboration
            - **📓 Journal** - Business notes, retrospectives, goal tracking
            - **🔍 Contact Finder** - Influencer discovery, lead generation, enrichment
            
            ### 📊 Analytics & Management
            - **👥 Customers** - Full CRM, pipeline tracking, segmentation
            - **📊 Analytics** - Sales tracking, social metrics, YouTube analytics, ROI
            - **🎨 Brand Templates** - Colors, fonts, logos, design systems
            - **📁 File Library** - Asset management, search, versioning, cloud integration
            
            ---
            
            **⚡ Quick Start Workflow:**
            1. Go to **🏠 Dashboard** tab
            2. Click **🎲 Randomize Concept** or enter your idea
            3. Enable **Campaign Plan** checkbox
            4. Click **🚀 Launch Complete Workflow**
            5. Download complete campaign ZIP (2-5 min, ~$0.50-$2.00)
            
            **💬 Pro Tip:** Use **Chat** in sidebar for natural language: "Create 10 coffee mug designs and schedule Instagram posts"
            """)
        
        with tab2:
            st.markdown("**Customize your experience based on your role:**")
            st.caption("Selecting a role will streamline which tabs you see in the navigation")
            
            # Initialize role if not set
            if 'user_role' not in st.session_state:
                st.session_state.user_role = None
            
            # Use role presets from tab visibility manager
            roles = {
                "business_owner": {
                    "icon": "👨‍💼",
                    "name": "Business Owner",
                    "description": "Focus on campaigns, analytics, and automation",
                    "preset_key": "business_owner"
                },
                "creator": {
                    "icon": "🎨",
                    "name": "Content Creator",
                    "description": "Emphasize design, video, and content tools",
                    "preset_key": "creator"
                },
                "developer": {
                    "icon": "⚙️",
                    "name": "Developer",
                    "description": "Workflows, automation, task queue, and APIs",
                    "preset_key": "developer"
                },
                "analyst": {
                    "icon": "📊",
                    "name": "Marketing Analyst",
                    "description": "Prioritize data, reports, and insights",
                    "preset_key": "analyst"
                },
                "label_owner": {
                    "icon": "🎵",
                    "name": "Label Owner",
                    "description": "Music distribution, video production, artist management",
                    "preset_key": "label_owner"
                },
                "online_seller": {
                    "icon": "🛒",
                    "name": "Online Seller",
                    "description": "Product creation, mockups, bulk operations, sales",
                    "preset_key": "online_seller"
                },
                "youtube_bot": {
                    "icon": "📺",
                    "name": "YouTube Bot",
                    "description": "Automated video production and scheduling",
                    "preset_key": "youtube_bot"
                },
                "otto_only": {
                    "icon": "🤖",
                    "name": "Otto Only",
                    "description": "Pure chat interface - control everything through Otto",
                    "preset_key": "otto_only"
                }
            }
            
            # Display role buttons in a grid
            cols = st.columns(2)
            for idx, (role_key, role_data) in enumerate(roles.items()):
                with cols[idx % 2]:
                    is_selected = st.session_state.user_role == role_key
                    button_type = "primary" if is_selected else "secondary"
                    
                    if st.button(
                        f"{role_data['icon']} {role_data['name']}" + (" ✓" if is_selected else ""),
                        use_container_width=True,
                        type=button_type,
                        key=f"role_{role_key}"
                    ):
                        st.session_state.user_role = role_key
                        # Apply the role's tab preset
                        apply_role_preset(role_data['preset_key'])
                        st.success(f"✅ Tabs customized for {role_data['name']}!")
                        st.rerun()
            
            # Show selected role details
            if st.session_state.user_role:
                role_data = roles[st.session_state.user_role]
                preset_key = role_data['preset_key']
                
                if preset_key in ROLE_PRESETS:
                    preset = ROLE_PRESETS[preset_key]
                    st.success(f"✅ **{role_data['name']}** selected!")
                    st.info(f"📌 {role_data['description']}")
                    
                    st.markdown(f"**🎯 Your Visible Tabs ({len(preset['tabs'])} tabs):**")
                    for tab in preset['tabs']:
                        st.markdown(f"• {tab}")
                    
                    st.caption("💡 You can customize this further in Settings → Preferences → Tab Visibility")
            else:
                st.info("👆 Select your role above to customize the platform")
        
        with tab3:
            st.markdown(SIDEBAR_GUIDE)
        
        with tab4:
            st.markdown(DASHBOARD_GUIDE)
        
        with tab5:
            st.markdown(OTTO_GUIDE)
        
        with tab6:
            st.markdown(PLAYGROUND_GUIDE)
        
        with tab7:
            st.markdown(INTEGRATIONS_GUIDE)
        
        with tab8:
            st.markdown(AUTOMATIONS_GUIDE)
        
        # Action buttons - ALWAYS visible below all tabs
        st.divider()
        col_action1, col_action2 = st.columns(2)
        
        with col_action1:
            if st.button("✅ Got It! Let's Go", type="primary", use_container_width=True, key="onboarding_complete"):
                st.session_state.completed_onboarding = True
                st.session_state.minimized_onboarding = True
                st.success("🎉 You're all set!")
                st.balloons()
                st.rerun()
        
        with col_action2:
            if st.button("⏭️ Maybe Later", use_container_width=True, key="onboarding_skip"):
                st.session_state.completed_onboarding = True
                st.session_state.minimized_onboarding = True
                st.rerun()

def render_getting_started_sidebar():
    """Optional sidebar widget showing getting started tips"""
    
    if st.session_state.get('completed_onboarding') and st.session_state.get('show_tips'):
        with st.sidebar:
            with st.expander("💡 Getting Started Tips", expanded=False):
                st.markdown("""
                ### Quick Tips
                
                **🎯 Most Popular:**
                1. Dashboard for overview
                2. Shortcuts for quick actions
                3. Task Queue for automation
                
                **⚡ Productivity Boost:**
                - Use keyboard shortcuts
                - Save templates
                - Set up automations
                
                **📚 Learn More:**
                Click any ? icon for detailed help
                """)
                
                if st.button("Hide these tips", key="hide_tips"):
                    st.session_state.show_tips = False
                    st.rerun()
    else:
        if 'show_tips' not in st.session_state:
            st.session_state.show_tips = True
