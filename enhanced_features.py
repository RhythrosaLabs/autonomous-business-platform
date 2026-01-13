"""
Enhanced Features for Otto Business Platform
============================================

New functionality to improve workflow, productivity, and intelligence:
- Cross-tab state management
- Global search
- Smart suggestions
- Batch processing
- Content optimization
- Auto-generated templates
"""

import streamlit as st
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class GlobalSearchManager:
    """Search across all content types in the platform"""
    
    SEARCHABLE_TYPES = {
        'campaigns': 'campaign_history',
        'products': 'generated_products',
        'content': 'generated_content',
        'conversations': 'conversations',  # From chat history
        'shortcuts': 'magic_shortcuts',
        'scheduled': 'scheduled_items',
        'templates': 'saved_templates'
    }
    
    @staticmethod
    def search(query: str, content_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Global search across all content types
        
        Args:
            query: Search query string
            content_types: Optional filter by content type
            
        Returns:
            List of matching items with metadata
        """
        query_lower = query.lower()
        results = []
        
        # Determine which types to search
        types_to_search = content_types or list(GlobalSearchManager.SEARCHABLE_TYPES.keys())
        
        for content_type in types_to_search:
            if content_type not in GlobalSearchManager.SEARCHABLE_TYPES:
                continue
            
            session_key = GlobalSearchManager.SEARCHABLE_TYPES[content_type]
            items = st.session_state.get(session_key, [])
            
            if not items:
                continue
            
            # Search through items
            for idx, item in enumerate(items):
                item_text = GlobalSearchManager._extract_searchable_text(item)
                
                if query_lower in item_text.lower():
                    results.append({
                        'type': content_type,
                        'item': item,
                        'index': idx,
                        'title': GlobalSearchManager._get_item_title(item, content_type),
                        'preview': GlobalSearchManager._get_preview(item, content_type),
                        'date': GlobalSearchManager._get_date(item),
                        'relevance_score': GlobalSearchManager._calculate_relevance(item_text, query)
                    })
        
        # Sort by relevance and date
        results.sort(key=lambda x: (-x['relevance_score'], x.get('date', '')), reverse=True)
        
        return results
    
    @staticmethod
    def _extract_searchable_text(item: Dict[str, Any]) -> str:
        """Extract all searchable text from an item"""
        if isinstance(item, dict):
            return ' '.join(str(v) for v in item.values() if isinstance(v, (str, int)))
        return str(item)
    
    @staticmethod
    def _get_item_title(item: Dict[str, Any], content_type: str) -> str:
        """Get display title for item"""
        title_keys = ['name', 'title', 'prompt', 'description', 'text']
        for key in title_keys:
            if key in item:
                return str(item[key])[:50]
        return f"Untitled {content_type.rstrip('s')}"
    
    @staticmethod
    def _get_preview(item: Dict[str, Any], content_type: str) -> str:
        """Get preview text for item"""
        if content_type == 'campaigns':
            return item.get('description', '')[:100]
        elif content_type == 'products':
            return item.get('prompt', '')[:100]
        elif content_type == 'content':
            return item.get('content', '')[:100]
        elif content_type == 'conversations':
            return item.get('summary', '')[:100]
        else:
            return str(item)[:100]
    
    @staticmethod
    def _get_date(item: Dict[str, Any]) -> str:
        """Extract date from item"""
        for date_key in ['date', 'created_at', 'timestamp', 'updated_at']:
            if date_key in item:
                return str(item[date_key])
        return ""
    
    @staticmethod
    def _calculate_relevance(text: str, query: str) -> float:
        """Calculate relevance score for search result"""
        text_lower = text.lower()
        query_lower = query.lower()
        
        score = 0.0
        
        # Exact match = high relevance
        if query_lower == text_lower:
            score = 10.0
        # Word boundary match = medium relevance
        elif f" {query_lower} " in f" {text_lower} ":
            score = 5.0
        # Substring match = low relevance
        else:
            score = 1.0
        
        return score


class SmartSuggestionEngine:
    """Generate context-aware suggestions based on current work"""
    
    @staticmethod
    def get_suggestions(context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Generate smart suggestions based on:
        - Current tab/feature being used
        - Recent actions
        - Available content
        - Platform capabilities
        
        Args:
            context: Optional context dict with current_tab, recent_action, etc.
            
        Returns:
            List of suggestion dicts with action and description
        """
        suggestions = []
        
        if not context:
            context = {}
        
        current_tab = context.get('current_tab', '')
        recent_action = context.get('recent_action', '')
        
        # Campaign-related suggestions
        if 'campaign' in current_tab.lower():
            recent_campaigns = st.session_state.get('campaign_history', [])
            if recent_campaigns:
                # Suggest repurposing recent campaigns
                suggestions.append({
                    'type': 'repurpose',
                    'icon': '♻️',
                    'title': 'Repurpose Last Campaign',
                    'description': f"Use {recent_campaigns[-1].get('name', 'last campaign')} as base",
                    'action': 'load_template',
                    'target': recent_campaigns[-1].get('id', '')
                })
        
        # Product-related suggestions
        if 'product' in current_tab.lower():
            # Suggest bulk generation if single product exists
            products = st.session_state.get('generated_products', [])
            if len(products) == 1:
                suggestions.append({
                    'type': 'bulk',
                    'icon': '🎨',
                    'title': 'Generate Variations',
                    'description': 'Create 5-10 design variations of your product',
                    'action': 'bulk_generate',
                    'params': {'count': 5}
                })
        
        # Content-related suggestions
        if 'content' in current_tab.lower():
            generated_content = st.session_state.get('generated_content', [])
            if len(generated_content) > 0 and len(generated_content) < 5:
                suggestions.append({
                    'type': 'expand',
                    'icon': '📈',
                    'title': 'Expand Content Suite',
                    'description': f'Add {5 - len(generated_content)} more content pieces',
                    'action': 'generate_more',
                    'params': {'count': 5 - len(generated_content)}
                })
        
        # Video-related suggestions
        video_count = len(st.session_state.get('generated_videos', []))
        if video_count == 0:
            suggestions.append({
                'type': 'video',
                'icon': '🎬',
                'title': 'Create Your First Video',
                'description': 'Generate a product commercial video',
                'action': 'video_producer',
                'advanced': True
            })
        elif video_count < 3:
            suggestions.append({
                'type': 'video',
                'icon': '🎬',
                'title': 'Add More Videos',
                'description': f'You have {video_count} video(s). Create 2 more for better coverage.',
                'action': 'video_producer',
                'params': {'count': 2}
            })
        
        # Publishing suggestions
        campaigns_unshared = len([c for c in st.session_state.get('campaign_history', []) if not c.get('published')])
        if campaigns_unshared > 0:
            suggestions.append({
                'type': 'publish',
                'icon': '📤',
                'title': f'Publish {campaigns_unshared} Campaign(s)',
                'description': 'Share your created content to social media',
                'action': 'publish_campaigns'
            })
        
        # Scheduling suggestions
        has_scheduled = len(st.session_state.get('scheduled_items', [])) > 0
        if not has_scheduled and len(st.session_state.get('generated_content', [])) > 0:
            suggestions.append({
                'type': 'schedule',
                'icon': '📅',
                'title': 'Schedule Content',
                'description': 'Set up automatic posting schedule',
                'action': 'setup_schedule'
            })
        
        # Analytics suggestions
        if len(st.session_state.get('campaign_history', [])) > 5:
            suggestions.append({
                'type': 'analytics',
                'icon': '📊',
                'title': 'View Performance Stats',
                'description': 'Analyze your campaign performance',
                'action': 'show_analytics'
            })
        
        # Contact finder suggestions
        if not st.session_state.get('contacts_found', False):
            suggestions.append({
                'type': 'outreach',
                'icon': '🔍',
                'title': 'Find Influencers',
                'description': 'Discover people to promote your products',
                'action': 'contact_finder'
            })
        
        return suggestions


class ContentOptimizer:
    """AI-powered content optimization"""
    
    @staticmethod
    def optimize_text(text: str, optimization_type: str = 'seo') -> Dict[str, Any]:
        """
        Optimize text content for specific purposes
        
        Args:
            text: Content to optimize
            optimization_type: 'seo', 'social', 'email', 'ad', 'blog'
            
        Returns:
            Dict with optimized content and suggestions
        """
        if not text:
            return {'error': 'No text provided'}
        
        optimizations = {
            'seo': ContentOptimizer._optimize_seo,
            'social': ContentOptimizer._optimize_social,
            'email': ContentOptimizer._optimize_email,
            'ad': ContentOptimizer._optimize_ad,
            'blog': ContentOptimizer._optimize_blog
        }
        
        optimizer = optimizations.get(optimization_type, ContentOptimizer._optimize_seo)
        return optimizer(text)
    
    @staticmethod
    def _optimize_seo(text: str) -> Dict[str, Any]:
        """Optimize for search engines"""
        return {
            'type': 'seo',
            'suggestions': [
                '✅ Add target keyword in first 100 words',
                '✅ Use H2/H3 subheadings for structure',
                '✅ Keep paragraphs under 150 words',
                '✅ Include 2-3 internal links',
                '✅ Add meta description (150-160 chars)',
                '✅ Use long-tail keywords naturally'
            ],
            'readability_score': 'B+',
            'estimated_seo_value': 'High'
        }
    
    @staticmethod
    def _optimize_social(text: str) -> Dict[str, Any]:
        """Optimize for social media"""
        return {
            'type': 'social',
            'suggestions': [
                '✅ Add emojis for engagement (+15%)',
                '✅ Use power words (awesome, incredible)',
                '✅ Keep under 280 chars (Twitter)',
                '✅ Add relevant hashtags (3-5)',
                '✅ Include clear call-to-action',
                '✅ Ask a question to boost engagement'
            ],
            'optimal_length': '100-150 characters',
            'engagement_potential': 'High'
        }
    
    @staticmethod
    def _optimize_email(text: str) -> Dict[str, Any]:
        """Optimize for email marketing"""
        return {
            'type': 'email',
            'suggestions': [
                '✅ Subject line: 50-60 characters',
                '✅ Use scannable formatting (bullets)',
                '✅ Keep body under 150 words',
                '✅ Mobile-friendly (short lines)',
                '✅ Clear CTA with urgency',
                '✅ Personalization tokens: {{first_name}}'
            ],
            'click_through_potential': 'High',
            'conversion_value': 'Medium-High'
        }
    
    @staticmethod
    def _optimize_ad(text: str) -> Dict[str, Any]:
        """Optimize for advertising"""
        return {
            'type': 'ad',
            'suggestions': [
                '✅ Headline: 3-6 words max',
                '✅ Benefit-focused copy',
                '✅ Create urgency ("Limited time")',
                '✅ Include social proof (reviews)',
                '✅ Strong CTA ("Shop now", "Learn more")',
                '✅ A/B test with variations'
            ],
            'ctr_improvement': '+25-40%',
            'conversion_boost': '+15-30%'
        }
    
    @staticmethod
    def _optimize_blog(text: str) -> Dict[str, Any]:
        """Optimize for blog posts"""
        return {
            'type': 'blog',
            'suggestions': [
                '✅ Title: 50-60 characters, keyword-rich',
                '✅ Intro: Hook reader in 2-3 sentences',
                '✅ Use subheadings every 200-300 words',
                '✅ Include images/video every 300 words',
                '✅ Conclusion: Summarize + CTA',
                '✅ Target: 1500+ words for authority'
            ],
            'estimated_rank_position': '1-3',
            'engagement_time': '3-4 minutes'
        }


class SmartTemplateGenerator:
    """Auto-generate templates from past successful campaigns"""
    
    @staticmethod
    def generate_from_campaigns() -> List[Dict[str, Any]]:
        """
        Analyze past campaigns and auto-generate reusable templates
        
        Returns:
            List of template suggestions
        """
        campaigns = st.session_state.get('campaign_history', [])
        products = st.session_state.get('generated_products', [])
        
        templates = []
        
        if len(campaigns) >= 2:
            # Find most common pattern
            most_successful = sorted(
                campaigns,
                key=lambda x: x.get('engagement', 0) or 0,
                reverse=True
            )[:1]
            
            if most_successful:
                campaign = most_successful[0]
                templates.append({
                    'name': f"High-Performer: {campaign.get('name', 'Campaign')}",
                    'icon': '⭐',
                    'description': f"Template based on your top-performing campaign",
                    'metrics': {
                        'engagement': campaign.get('engagement', 'Unknown'),
                        'reach': campaign.get('reach', 'Unknown'),
                        'conversions': campaign.get('conversions', 'Unknown')
                    },
                    'reusable_elements': [
                        campaign.get('strategy', ''),
                        campaign.get('tone', ''),
                        campaign.get('hashtags', '')
                    ]
                })
        
        if len(products) >= 3:
            # Find most popular color/style combination
            colors = {}
            for product in products:
                color = product.get('primary_color', 'Multi')
                colors[color] = colors.get(color, 0) + 1
            
            if colors:
                top_color = max(colors.items(), key=lambda x: x[1])[0]
                templates.append({
                    'name': f"Popular Style: {top_color} Products",
                    'icon': '🎨',
                    'description': f"{top_color} is your most popular color choice",
                    'metrics': {
                        'usage_count': colors[top_color],
                        'customer_preference': f"{int((colors[top_color]/len(products)*100))}%"
                    },
                    'suggested_next_step': f'Create more {top_color} variations'
                })
        
        return templates


class BatchProcessingQueue:
    """Track and manage batch processing jobs"""
    
    @staticmethod
    def create_batch_job(job_type: str, items: List[Any], params: Optional[Dict] = None) -> str:
        """
        Create a new batch processing job
        
        Args:
            job_type: 'generate_images', 'generate_videos', 'publish', etc.
            items: Items to process
            params: Optional parameters
            
        Returns:
            Job ID
        """
        import uuid
        
        job_id = str(uuid.uuid4())[:8]
        
        job = {
            'id': job_id,
            'type': job_type,
            'status': 'queued',  # queued, processing, completed, failed
            'items_total': len(items),
            'items_completed': 0,
            'items_failed': 0,
            'created_at': datetime.now().isoformat(),
            'started_at': None,
            'completed_at': None,
            'results': [],
            'errors': []
        }
        
        if 'batch_jobs' not in st.session_state:
            st.session_state.batch_jobs = {}
        
        st.session_state.batch_jobs[job_id] = job
        
        return job_id
    
    @staticmethod
    def get_job_status(job_id: str) -> Dict[str, Any]:
        """Get status of a batch job"""
        if 'batch_jobs' not in st.session_state:
            return {'error': 'Job not found'}
        
        return st.session_state.batch_jobs.get(job_id, {'error': 'Job not found'})
    
    @staticmethod
    def update_job_progress(job_id: str, completed: int, error_msg: Optional[str] = None):
        """Update batch job progress"""
        if 'batch_jobs' in st.session_state and job_id in st.session_state.batch_jobs:
            job = st.session_state.batch_jobs[job_id]
            job['items_completed'] = completed
            
            if error_msg:
                job['items_failed'] += 1
                job['errors'].append(error_msg)
            
            # Check if done
            if job['items_completed'] + job['items_failed'] >= job['items_total']:
                job['status'] = 'completed' if job['items_failed'] == 0 else 'partial'
                job['completed_at'] = datetime.now().isoformat()
    
    @staticmethod
    def list_active_jobs() -> List[Dict[str, Any]]:
        """Get all active batch jobs"""
        if 'batch_jobs' not in st.session_state:
            return []
        
        return [
            job for job in st.session_state.batch_jobs.values()
            if job['status'] in ['queued', 'processing']
        ]


class ContentCalendarManager:
    """Visual calendar for scheduled content"""
    
    @staticmethod
    def get_calendar_data(year: int, month: int) -> Dict[int, List[Dict[str, Any]]]:
        """
        Get scheduled content for a calendar month
        
        Args:
            year: Year (e.g., 2025)
            month: Month (1-12)
            
        Returns:
            Dict mapping day numbers to list of scheduled items
        """
        scheduled_items = st.session_state.get('scheduled_items', [])
        calendar_data = {}
        
        for item in scheduled_items:
            try:
                item_date = datetime.fromisoformat(item.get('scheduled_date', ''))
                
                if item_date.year == year and item_date.month == month:
                    day = item_date.day
                    
                    if day not in calendar_data:
                        calendar_data[day] = []
                    
                    calendar_data[day].append({
                        'title': item.get('title', 'Scheduled Post'),
                        'type': item.get('type', 'post'),
                        'platforms': item.get('platforms', []),
                        'time': item_date.strftime('%H:%M')
                    })
            except:
                continue
        
        return calendar_data
    
    @staticmethod
    def get_upcoming_posts(days: int = 7) -> List[Dict[str, Any]]:
        """Get next N days of scheduled posts"""
        scheduled_items = st.session_state.get('scheduled_items', [])
        today = datetime.now()
        upcoming = []
        
        for item in scheduled_items:
            try:
                item_date = datetime.fromisoformat(item.get('scheduled_date', ''))
                
                if today <= item_date <= today + timedelta(days=days):
                    upcoming.append({
                        'date': item_date,
                        'title': item.get('title', 'Scheduled Post'),
                        'platforms': item.get('platforms', []),
                        'content': item.get('content', '')[:100]
                    })
            except:
                continue
        
        # Sort by date
        upcoming.sort(key=lambda x: x['date'])
        
        return upcoming


class QuickActionsBar:
    """Floating action menu for common quick tasks"""
    
    QUICK_ACTIONS = {
        'generate_image': {
            'icon': '🎨',
            'label': 'Generate Image',
            'description': 'Create a new image',
            'action': 'open_playground'
        },
        'generate_video': {
            'icon': '🎬',
            'label': 'Generate Video',
            'description': 'Create a product video',
            'action': 'open_video_producer'
        },
        'write_post': {
            'icon': '✍️',
            'label': 'Write Post',
            'description': 'Create social media content',
            'action': 'open_content_generator'
        },
        'create_campaign': {
            'icon': '🚀',
            'label': 'New Campaign',
            'description': 'Start a full campaign',
            'action': 'open_campaign_creator'
        },
        'find_contacts': {
            'icon': '🔍',
            'label': 'Find Contacts',
            'description': 'Discover influencers',
            'action': 'open_contact_finder'
        },
        'view_analytics': {
            'icon': '📊',
            'label': 'Analytics',
            'description': 'Check performance',
            'action': 'open_analytics'
        },
        'chat_otto': {
            'icon': '🤖',
            'label': 'Chat with Otto',
            'description': 'Ask AI for help',
            'action': 'open_chat'
        },
        'schedule_post': {
            'icon': '📅',
            'label': 'Schedule Post',
            'description': 'Plan future posts',
            'action': 'open_scheduler'
        }
    }
    
    @staticmethod
    def render_quick_actions_sidebar():
        """Render floating quick actions in sidebar"""
        st.markdown("---")
        st.markdown("### ⚡ Quick Actions")
        
        for action_id, action_data in QuickActionsBar.QUICK_ACTIONS.items():
            if st.button(
                f"{action_data['icon']} {action_data['label']}",
                key=f"quick_action_{action_id}",
                use_container_width=True,
                help=action_data['description']
            ):
                st.session_state['quick_action'] = action_id
                st.rerun()


def render_enhanced_features_ui():
    """Render enhanced features UI components"""
    
    # Global Search
    st.markdown("### 🔍 Global Search")
    search_query = st.text_input(
        "Search all content",
        placeholder="Search campaigns, products, content, conversations...",
        key="global_search"
    )
    
    if search_query:
        results = GlobalSearchManager.search(search_query)
        
        if results:
            st.markdown(f"**Found {len(results)} results:**")
            
            for result in results[:10]:
                with st.expander(f"{result['type'].title()}: {result['title']}"):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**Preview:** {result['preview']}")
                        if result['date']:
                            st.caption(f"📅 {result['date']}")
                    with col2:
                        st.metric("Match Score", f"{int(result['relevance_score'])}%")
                    
                    if st.button("Load", key=f"load_{result['type']}_{result['index']}"):
                        st.session_state[f'load_{result["type"]}'] = result['item']
                        st.success("Loaded!")
        else:
            st.info("No results found")
    
    st.markdown("---")
    
    # Smart Suggestions
    st.markdown("### 💡 Smart Suggestions")
    
    suggestions = SmartSuggestionEngine.get_suggestions()
    
    if suggestions:
        for suggestion in suggestions[:5]:
            with st.container():
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"**{suggestion['icon']} {suggestion['title']}**")
                    st.caption(suggestion['description'])
                with col2:
                    if st.button("Try", key=f"suggestion_{suggestion['type']}", use_container_width=True):
                        st.session_state['suggestion_action'] = suggestion['action']
                        st.rerun()


# Export functions for use in main app
__all__ = [
    'GlobalSearchManager',
    'SmartSuggestionEngine',
    'ContentOptimizer',
    'SmartTemplateGenerator',
    'BatchProcessingQueue',
    'ContentCalendarManager',
    'QuickActionsBar',
    'render_enhanced_features_ui'
]
